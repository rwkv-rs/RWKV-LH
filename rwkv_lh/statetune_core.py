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


def target_cross_entropy(logits, labels, *, reduction: str = "mean"):
    """No L2Wrap: prompt/pad logits have no direct loss or regularizer gradient."""
    import torch
    require(reduction in ("mean", "sum"), "reduction must be mean or sum")
    require(tuple(logits.shape[:-1]) == tuple(labels.shape), "logit/label shape differs")
    require(bool(labels.ne(-100).any()), "batch contains no supervised target tokens")
    selected = labels.ne(-100)
    # Prompt logits have no direct loss. Select before the FP32 conversion so
    # long bootstraps do not allocate another full [T,V] floating point buffer.
    values = logits[selected]
    return torch.nn.functional.cross_entropy(values if values.dtype == torch.float64 else values.float(),
                                             labels[selected], reduction=reduction)










def max_logit_difference(actual, reference) -> float:
    """Exact maximum over all logits, with at most 64 positions of scratch.

    A 24K-by-64K vocabulary matrix contains over 1.6 billion values. Keeping
    subtraction, finiteness checks and reduction bounded avoids allocating
    several additional full-size matrices during numerical admission.
    """
    import torch
    require(actual.ndim == 3 and actual.shape == reference.shape
            and actual.shape[0] == 1 and actual.shape[1] > 0 and actual.shape[2] > 0
            and actual.is_floating_point() and reference.is_floating_point()
            and actual.device == reference.device,
            'alignment logit geometry differs')
    largest = 0.0
    for begin in range(0, actual.shape[1], 64):
        left, right = actual[:, begin:begin + 64], reference[:, begin:begin + 64]
        require(bool(torch.isfinite(left).all()) and bool(torch.isfinite(right).all()),
                'alignment logit finiteness differs')
        largest = max(largest, float((left - right).abs().max()))
    return largest
