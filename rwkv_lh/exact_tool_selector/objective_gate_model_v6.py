"""Validated objective-aware Gate head for one-forward network takeover."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.protocol import canonical_digest


OBJECTIVE_GATE_SCHEMA = "rwkv-lh.objective-network-gate-head.v1"
GATE_LABELS = ("NETWORK", "DEFER")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_digest(value: Any) -> str:
    return hashlib.sha256(value.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


class ObjectiveGateNetwork:
    @staticmethod
    def create(input_dim: int) -> Any:
        import torch

        if input_dim not in {2560, 5120}:
            raise ValueError("objective Gate input dimension is unsupported")

        class Network(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.shared = torch.nn.Linear(input_dim, 256)
                self.layer_norm = torch.nn.LayerNorm(256, eps=1e-5)
                self.dropout = torch.nn.Dropout(0.2)
                self.head = torch.nn.Linear(256, 2)

            def forward(self, features: Any) -> Any:
                if features.ndim != 2 or features.shape[-1] != input_dim:
                    raise ValueError("objective Gate feature shape mismatch")
                hidden = torch.nn.functional.gelu(self.shared(features), approximate="tanh")
                return self.head(self.dropout(self.layer_norm(hidden)))

        return Network()


class ObjectiveGateHead:
    def __init__(self, path: Path, expected_sha256: str | None = None) -> None:
        import torch

        self.path = path.resolve()
        self.file_sha256 = sha256_file(self.path)
        if expected_sha256 is not None and self.file_sha256 != expected_sha256:
            raise ValueError("objective Gate artifact SHA-256 mismatch")
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != OBJECTIVE_GATE_SCHEMA:
            raise ValueError("unsupported objective Gate artifact schema")
        if tuple(payload.get("labels") or ()) != GATE_LABELS:
            raise ValueError("objective Gate label order changed")
        self.feature_name = str(payload.get("feature_name") or "")
        self.input_dim = int(payload.get("input_dim") or 0)
        if (self.feature_name, self.input_dim) not in {("prefix_mean", 2560), ("prefix_full_concat", 5120)}:
            raise ValueError("objective Gate feature identity changed")
        self.feature_mean = payload.get("normalizer", {}).get("mean")
        self.feature_std = payload.get("normalizer", {}).get("std")
        if (
            not isinstance(self.feature_mean, torch.Tensor)
            or not isinstance(self.feature_std, torch.Tensor)
            or tuple(self.feature_mean.shape) != (self.input_dim,)
            or tuple(self.feature_std.shape) != (self.input_dim,)
            or not bool(torch.isfinite(self.feature_mean).all() and torch.isfinite(self.feature_std).all())
            or not bool((self.feature_std > 0).all())
        ):
            raise ValueError("objective Gate normalizer is invalid")
        state = payload.get("state_dict")
        metadata = payload.get("metadata")
        if not isinstance(state, Mapping) or not isinstance(metadata, Mapping):
            raise ValueError("objective Gate artifact sections are incomplete")
        self.model = ObjectiveGateNetwork.create(self.input_dim).cpu().eval()
        self.model.load_state_dict(dict(state), strict=True)
        self.metadata = dict(metadata)
        tensor_digests = {
            "normalizer.mean": _tensor_digest(self.feature_mean),
            "normalizer.std": _tensor_digest(self.feature_std),
            **{f"state_dict.{name}": _tensor_digest(value) for name, value in sorted(self.model.state_dict().items())},
        }
        identity = {
            "schema_version": OBJECTIVE_GATE_SCHEMA,
            "labels": list(GATE_LABELS),
            "feature_name": self.feature_name,
            "input_dim": self.input_dim,
            "tensor_digests": tensor_digests,
            "metadata": self.metadata,
        }
        self.head_hash = str(payload.get("head_hash") or "")
        if canonical_digest(identity) != self.head_hash:
            raise ValueError("objective Gate tensor identity mismatch")

    def raw_logits(self, features: Sequence[float] | Any) -> tuple[float, float]:
        import torch

        values = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(values.shape) != (self.input_dim,) or not bool(torch.isfinite(values).all()):
            raise ValueError("objective Gate input feature is invalid")
        with torch.no_grad():
            logits = self.model(((values - self.feature_mean) / self.feature_std).unsqueeze(0))[0]
        return tuple(float(value) for value in logits.tolist())

    def select(self, features: Sequence[float] | Any) -> str:
        logits = self.raw_logits(features)
        return GATE_LABELS[max(range(2), key=lambda index: (logits[index], -index))]


__all__ = ["GATE_LABELS", "OBJECTIVE_GATE_SCHEMA", "ObjectiveGateHead", "ObjectiveGateNetwork", "sha256_file"]
