"""Chunked StateTune of one long episode with an exactly carried serving State.

An episode longer than the verified training context is split into chunks.
Chunk k starts from the final State of chunk k-1 (chunk 0 from the trainable
time_state with zero token shifts), exactly as Native serving carries State
between incremental inputs. Nothing is truncated and every chunk sees the
same prefix State that inference would.

Gradients are exact across chunks. A no-grad pass stores each boundary State;
chunks are then recomputed in reverse order with the boundary as a leaf, and
one backward per chunk sends its own target loss plus the gradient arriving
at its final State from the next chunk. Activation memory is bounded by one
chunk; stored boundary States additionally grow with the number of chunks.
"""
import torch

from rwkv_lh.statetune_core import require, target_cross_entropy


def episode_chunks(token_ids, target_spans, chunk_starts, *, context_tokens, supervised=None):
    """Next-token inputs and labels of an executor episode, split at chunk_starts.

    token_ids is the full episode (BOS first); target_spans are unshifted
    [start, length] spans of token_ids. Inputs are token_ids[:-1] and the label
    at input position p is token_ids[p+1] when p+1 lies in a supervised span.
    supervised optionally marks each span; unsupervised spans stay as input.
    """
    tokens = list(token_ids)
    size = len(tokens) - 1
    require(type(context_tokens) is int and context_tokens > 0 and size > 0, "invalid episode or context")
    spans = [tuple(span) for span in target_spans]
    previous_end = 1
    for start, count in spans:
        require(type(start) is int and type(count) is int and count > 0 and start >= previous_end
                and start + count <= len(tokens), "target span is outside the episode or overlaps")
        previous_end = start + count
    require(supervised is None or len(supervised) == len(spans), "supervised marks must match target spans")
    starts = list(chunk_starts)
    require(bool(starts) and starts[0] == 0, "chunks must start at 0")
    require(all(type(a) is int and a < b for a, b in zip(starts, starts[1:])), "chunk starts must increase")
    require(starts[-1] < size, "chunk starts must lie inside the episode inputs")
    ends = [*starts[1:], size]
    require(all(end - start <= context_tokens for start, end in zip(starts, ends)),
            "chunk exceeds context; truncation is forbidden")
    labels = [-100] * size
    for index, (start, count) in enumerate(spans):
        if supervised is None or supervised[index]:
            labels[start - 1:start - 1 + count] = tokens[start:start + count]
    return [{"input_ids": torch.tensor([tokens[start:end]], dtype=torch.long),
             "labels": torch.tensor([labels[start:end]], dtype=torch.long)}
            for start, end in zip(starts, ends)]


def _flatten(state):
    return [value for layer in state for value in layer if value is not None]


def _leaf(state):
    return tuple(tuple(value.detach().requires_grad_() for value in layer) for layer in state)


def state_carry_backward(model, chunks, *, weight, record=None):
    """Accumulate weight * mean target loss of the whole episode into time_state.grad.

    model(input_ids, state, return_state=True) returns (logits, final State);
    state=None means the episode start. Chunks after the last supervised one
    cannot influence the loss and are not computed. recompute_equal records
    whether every recomputed final State matched the stored boundary bitwise.
    """
    device = next(iter(model.parameters())).device
    counts = [int(chunk["labels"].ne(-100).sum()) for chunk in chunks]
    total = sum(counts)
    require(total > 0, "episode contains no supervised target tokens")
    last = max(index for index, count in enumerate(counts) if count)
    used = chunks[:last + 1]
    boundaries = [None]
    def event(name,index,stage,**fields):
        if record is not None:
            record(dict(event=name,chunk_index=index,stage=stage,input_tokens=chunks[index]['input_ids'].numel(),**fields))
    with torch.no_grad():
        state = None
        for index,chunk in enumerate(used[:-1]):
            event('chunk_started',index,'boundary_forward')
            unused_logits, state = model(chunk["input_ids"].to(device), state, return_state=True)
            # Even `_` is a strong reference. A [24576, 65536] FP32 tensor
            # would otherwise stay live throughout every reverse chunk.
            del unused_logits
            boundaries.append(state)
    scale = weight / total
    loss_sum = 0.0
    recompute_equal = True
    upstream = None
    for index in reversed(range(len(used))):
        event('chunk_started',index,'recompute_forward')
        initial = None if boundaries[index] is None else _leaf(boundaries[index])
        logits, final = model(used[index]["input_ids"].to(device), initial, return_state=True)
        roots, grads = [], []
        if counts[index]:
            try:
                loss = target_cross_entropy(logits, used[index]["labels"].to(device), reduction="sum")
                require(bool(torch.isfinite(loss)), 'nonfinite target loss')
            except Exception as error:
                finite=torch.isfinite(logits)
                values=logits.detach()[finite]
                event('chunk_failed',index,'loss',error=repr(error),logits=dict(
                    shape=list(logits.shape),dtype=str(logits.dtype),nonfinite=int((~finite).sum()),
                    minimum=float(values.min()) if values.numel() else None,
                    maximum=float(values.max()) if values.numel() else None))
                raise
            loss_sum += float(loss.detach())
            roots.append(loss * scale)
            grads.append(torch.ones_like(loss))
        del logits
        if upstream is not None:
            stored = _flatten(boundaries[index + 1])
            finals = _flatten(final)
            recompute_equal &= len(stored) == len(finals) and all(
                torch.equal(a, b.detach()) for a, b in zip(stored, finals))
            for value, gradient in zip(finals, upstream):
                if value.requires_grad and gradient is not None:
                    roots.append(value)
                    grads.append(gradient)
        del final
        if roots:
            event('chunk_started',index,'backward')
            torch.autograd.backward(roots, grads)
        upstream = None
        if initial is not None:
            upstream = []
            for value in _flatten(initial):
                # A contiguous [B,C] shift gradient can still be a view into
                # an entire [B,T,C] allocation. `contiguous()` will not copy
                # that view. Carry only its actual values into the next block,
                # and clear the leaf's original gradient even if an autograd
                # node still holds the leaf alive.
                upstream.append(None if value.grad is None else value.grad.detach().clone())
                value.grad = None
        if counts[index]:
            del loss
        del roots, grads, initial
    return {"loss": loss_sum / total, "targets": total, "chunks": len(used),
            "recompute_equal": bool(recompute_equal)}
