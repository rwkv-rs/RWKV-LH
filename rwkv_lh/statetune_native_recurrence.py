"""Sealed FP32 State recurrence; independent bias stays FP32 through raw merge."""
from pathlib import Path
import importlib.util
import sys
import torch
from rwkv_lh import statetune_core as adapter

EXTENSION_NAME = "rwkv_lh_r26_decay_fp32"
_EXTENSION = None
_EXTENSION_IDENTITY = None


def load_extension(path, expected_sha256):
    """Load one explicit binary; training never compiles or selects a fallback."""
    global _EXTENSION, _EXTENSION_IDENTITY
    path = adapter.verify_file(path, expected_sha256).resolve()
    identity = (str(path), expected_sha256)
    if _EXTENSION is not None:
        adapter.require(_EXTENSION_IDENTITY == identity, "a different native training binary is already loaded")
        return _EXTENSION
    adapter.require(EXTENSION_NAME not in sys.modules, "unsealed native extension was imported before admission")
    spec = importlib.util.spec_from_file_location(EXTENSION_NAME, path)
    adapter.require(spec is not None and spec.loader is not None, "native extension loader is unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    adapter.require(Path(module.__file__).resolve() == path, "loaded native extension path differs")
    adapter.verify_file(path, expected_sha256)
    _EXTENSION, _EXTENSION_IDENTITY = module, identity
    return module


def extension():
    adapter.require(_EXTENSION is not None, "a sealed native training binary must be explicitly loaded")
    return _EXTENSION

class Recurrent(torch.autograd.Function):

    @staticmethod
    def forward(ctx, r, raw, k, v, a, b, initial_state):
        batch, tokens, heads, size = r.shape
        flat = [x.reshape(-1, heads, size).contiguous() for x in (r, raw, k, v, a, b)]
        per_sequence = (tokens + 15) // 16
        offsets = torch.arange(batch + 1, device=r.device, dtype=torch.int32) * per_sequence
        starts = (torch.arange(per_sequence, device=r.device, dtype=torch.int32)[None] * 16 + torch.arange(batch, device=r.device, dtype=torch.int32)[:, None] * tokens).flatten()
        ends = torch.minimum(starts + 16, torch.arange(1, batch + 1, device=r.device, dtype=torch.int32).repeat_interleave(per_sequence) * tokens)
        final = initial_state.contiguous().clone()
        boundary = torch.empty(batch * per_sequence, heads, size, size, device=r.device, dtype=torch.float32)
        state_dot_a = torch.empty_like(flat[0], dtype=torch.float32)
        out = torch.empty_like(flat[3])
        extension().forward(offsets, starts, ends, final, *flat, out, boundary, state_dot_a, 1.0)
        ctx.set_materialize_grads(False)
        ctx.save_for_backward(offsets, starts, ends, *flat, boundary, state_dot_a, final)
        ctx.shape = r.shape
        return (out.reshape_as(v), final)

    @staticmethod
    def backward(ctx, grad_output, grad_final):
        offsets, starts, ends, r, raw, k, v, a, b, boundary, state_dot_a, final = ctx.saved_tensors
        inputs = (r, raw, k, v, a, b)
        grads = [torch.empty_like(x) if ctx.needs_input_grad[i] else None for i, x in enumerate(inputs)]
        state_grad = torch.empty_like(final) if ctx.needs_input_grad[6] else None
        extension().backward(offsets, starts, ends, final, *inputs, state_dot_a, None if grad_output is None else grad_output.reshape_as(v).contiguous(), None if grad_final is None else grad_final.contiguous(), boundary, *grads, state_grad, 1.0)
        return (*(None if x is None else x.reshape(ctx.shape) for x in grads), state_grad)


def recurrent(r, delta, k, v, a, b, *, initial_state, decay_bias):
    adapter.require(r.ndim == 4 and r.shape[0] == 1 and r.shape[1] > 0 and r.shape[-1] == 64,
                    "native training recurrence requires one nonempty fixed-length sample and head64")
    adapter.require(r.is_cuda and r.dtype == torch.float16 and not decay_bias.requires_grad,
                    "native recurrence requires CUDA FP16 tokens and frozen decay bias")
    adapter.require(initial_state.dtype == torch.float32
                    and tuple(initial_state.shape) == (r.shape[0], r.shape[2], 64, 64),
                    "native recurrence requires FP32 [B,H,K,V] initial State")
    adapter.require(all(x.shape == r.shape and x.dtype == r.dtype and x.device == r.device
                        for x in (delta, k, v, a, b))
                    and decay_bias.shape == r.shape[-2:] and decay_bias.dtype == r.dtype
                    and decay_bias.device == initial_state.device == r.device,
                    "native recurrence tensor shape, dtype or device differs")
    raw = delta.float() + decay_bias.float()
    return Recurrent.apply(r, raw, k, v, a, b, initial_state)
