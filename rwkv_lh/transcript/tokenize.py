"""Complete incremental-turn tokens and unshifted assistant-only supervision."""
import hashlib

from .render import PROTOCOL, render_turns


def tokenize_transcript(messages, *, tokenizer, max_tokens=None):
    """Return complete input_ids/loss_mask, or reject a capacity overflow.

    Each turn is encoded as the same append used by incremental serving. Token
    merges cannot cross a role boundary and accidentally supervise User/tool
    bytes. No BOS/EOS is added, no target is shifted, and no tail is dropped.
    This in-memory codec neither writes data nor authorizes training.
    """
    if max_tokens is not None and (type(max_tokens) is not int or max_tokens < 1):
        raise ValueError('positive token capacity required')
    ids, mask, spans = [], [], []
    rendered = render_turns(messages)
    for message, text in zip(messages, rendered):
        tokens = list(tokenizer.encode(text))
        if (any(type(token) is not int or token <= 0 for token in tokens)
                or tokenizer.decode_bytes(tokens) != text.encode('utf-8')):
            raise ValueError('tokenizer must preserve exact UTF-8 bytes without added special tokens')
        start = len(ids)
        ids.extend(tokens)
        mask.extend([int(message['role'] == 'assistant')] * len(tokens))
        spans.append({'role': message['role'], 'start': start, 'end': len(ids)})
    if max_tokens is not None and len(ids) > max_tokens:
        raise ValueError(f'transcript requires {len(ids)} tokens; capacity is {max_tokens}; no truncation')
    return {'protocol': PROTOCOL, 'input_ids': ids, 'loss_mask': mask, 'turn_spans': spans,
            'rendered_sha256': hashlib.sha256(''.join(rendered).encode('utf-8')).hexdigest()}
