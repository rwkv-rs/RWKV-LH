"""Role-independent StateTune tensors and target-only loss; no dataset generator."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence
from uuid import UUID

_STATE = re.compile(r"blocks\.[0-9]+\.att\.time_state")
_SHA = re.compile(r"[0-9a-f]{64}")

def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def device_uuid_matches(actual: str, registered: str) -> bool:
    """PyTorch exposes the UUID without nvidia-smi's GPU- display prefix."""
    try:
        return registered.startswith("GPU-") and UUID(str(actual).removeprefix("GPU-")) == UUID(registered[4:])
    except (ValueError, AttributeError, TypeError):
        return False


def sha256_file(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_file(path: str | Path, expected_sha256: str) -> Path:
    path = Path(path)
    require(bool(_SHA.fullmatch(str(expected_sha256))), "explicit SHA-256 is required")
    require(path.is_file() and not path.is_symlink(), "identity requires a regular non-symlink file")
    require(sha256_file(path) == expected_sha256, f"file SHA-256 differs: {path}")
    return path


def read_sealed_json(path: str | Path, expected_sha256: str) -> dict[str, Any]:
    path = verify_file(path, expected_sha256)
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            require(key not in result, "duplicate JSON field")
            result[key] = value
        return result
    value = json.loads(path.read_text(), object_pairs_hook=object_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite JSON")))
    require(isinstance(value, dict), "sealed record must be an object")
    return value


def collate_samples(samples: Sequence[Mapping[str, Any]], *, context_tokens: int) -> dict[str, Any]:
    import torch
    require(bool(samples) and type(context_tokens) is int and context_tokens > 0, "empty batch or invalid context")
    sizes = [len(row["input_token_ids"]) + len(row["target_token_ids"]) - 1 for row in samples]
    require(all(0 < size <= context_tokens for size in sizes), "sample exceeds context; truncation is forbidden")
    tokens = torch.zeros((len(samples), max(sizes)), dtype=torch.long)
    labels = torch.full_like(tokens, -100)
    for index, (row, size) in enumerate(zip(samples, sizes)):
        source, target = list(row["input_token_ids"]), list(row["target_token_ids"])
        require(bool(source) and bool(target), "empty input or target")
        tokens[index, :size] = torch.tensor((source + target)[:-1], dtype=torch.long)
        labels[index, len(source) - 1:size] = torch.tensor(target, dtype=torch.long)
    return {"input_ids": tokens, "labels": labels, "sample_ids": [row["sample_id"] for row in samples]}


def target_cross_entropy(logits, labels):
    """No L2Wrap: prompt/pad logits have no direct loss or regularizer gradient."""
    import torch
    require(tuple(logits.shape[:-1]) == tuple(labels.shape), "logit/label shape differs")
    require(bool(labels.ne(-100).any()), "batch contains no supervised target tokens")
    selected = labels.ne(-100)
    # Prompt logits have no direct loss. Select before the FP32 conversion so
    # long bootstraps do not allocate another full [T,V] floating point buffer.
    return torch.nn.functional.cross_entropy(logits[selected].float(), labels[selected])


def state_parameters(model, *, layers: int) -> dict[str, Any]:
    require(type(layers) is int and layers > 0, "positive layer count is required")
    expected = {f"blocks.{i}.att.time_state" for i in range(layers)}
    parameters = {name: p for name, p in model.named_parameters() if _STATE.fullmatch(name)}
    require(set(parameters) == expected, "exact one time_state per layer is required")
    return parameters


def freeze_for_state_tuning(model, *, layers: int) -> dict[str, Any]:
    parameters = state_parameters(model, layers=layers)
    model.requires_grad_(False)
    for parameter in parameters.values():
        parameter.requires_grad_(True)
    require({name for name, p in model.named_parameters() if p.requires_grad} == set(parameters),
            "optimizer trainable set is not exactly time_state")
    return parameters


def load_frozen_base(model, path: str | Path, expected_sha256: str, *, layers: int) -> None:
    import torch
    verify_file(path, expected_sha256)
    candidate = state_parameters(model, layers=layers)
    weights = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    expected = model.state_dict()
    require(isinstance(weights, dict) and set(weights) == set(expected) - set(candidate),
            "base key set differs; only newly initialized time_state may be absent")
    for name, value in weights.items():
        require(isinstance(value, torch.Tensor) and value.shape == expected[name].shape,
                f"base tensor shape differs: {name}")
        require(value.is_floating_point() and bool(torch.isfinite(value).all()), f"invalid base tensor: {name}")
    # Validate everything before copying anything into the model.
    result = model.load_state_dict(weights, strict=False, assign=True)
    require(set(result.missing_keys) == set(candidate) and not result.unexpected_keys, "base loading keys differ")


def portable_state(model, *, layers: int, heads: int, head_size: int) -> dict[str, Any]:
    import torch
    result = {}
    for name, value in state_parameters(model, layers=layers).items():
        require(tuple(value.shape) == (heads, head_size, head_size), f"state shape differs: {name}")
        tensor = value.detach().to(device="cpu", dtype=torch.bfloat16).contiguous().clone()
        require(bool(torch.isfinite(tensor).all()) and bool(torch.count_nonzero(tensor)),
                f"published state must be finite and nonzero in every layer: {name}")
        result[name] = tensor
    # Portable PEFT [H,V,K] stays unchanged; the runtime loader transposes once.
    return result
