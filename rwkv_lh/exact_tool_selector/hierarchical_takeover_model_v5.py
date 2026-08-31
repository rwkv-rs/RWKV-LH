"""Validated one-forward hierarchical network takeover head."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.model_v2 import NETWORK_SELECTOR_FEATURE_PROTOCOLS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


GATE_LABELS = ("NETWORK", "DEFER")
TOOL_LABELS = ("web_search", "connector_lookup")
HIERARCHICAL_TAKEOVER_HEAD_SCHEMA = "rwkv-lh.hierarchical-network-takeover-head.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_digest(value: Any) -> str:
    return hashlib.sha256(value.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


class BinaryTakeoverHeadNetwork:
    """Factory for each frozen S11 binary MLP."""

    @staticmethod
    def create() -> Any:
        import torch

        class Network(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.shared = torch.nn.Linear(2560, 256)
                self.layer_norm = torch.nn.LayerNorm(256, eps=1e-5)
                self.dropout = torch.nn.Dropout(0.2)
                self.head = torch.nn.Linear(256, 2)

            def forward(self, features: Any) -> Any:
                if features.ndim != 2 or features.shape[-1] != 2560:
                    raise ValueError("hierarchical takeover feature shape mismatch")
                hidden = torch.nn.functional.gelu(self.shared(features), approximate="tanh")
                return self.head(self.dropout(self.layer_norm(hidden)))

        return Network()


class HierarchicalNetworkTakeoverHead:
    """Load two pinned binary heads and expose all unmodified raw logits."""

    def __init__(self, path: Path, expected_sha256: str | None = None) -> None:
        import torch

        self.path = path.resolve()
        self.file_sha256 = sha256_file(self.path)
        if expected_sha256 is not None and self.file_sha256 != expected_sha256:
            raise ValueError("hierarchical takeover head file SHA-256 mismatch")
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != HIERARCHICAL_TAKEOVER_HEAD_SCHEMA:
            raise ValueError("unsupported hierarchical takeover head schema")
        if tuple(payload.get("gate_labels") or ()) != GATE_LABELS or tuple(payload.get("tool_labels") or ()) != TOOL_LABELS:
            raise ValueError("hierarchical takeover labels/order changed")
        self.feature_protocol = str(payload.get("feature_protocol") or "")
        if self.feature_protocol not in NETWORK_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError("unsupported hierarchical takeover feature protocol")
        self.model_hash = str(payload.get("model_hash") or "")
        self.head_hash = str(payload.get("head_hash") or "")
        for name, digest in (("model", self.model_hash), ("head", self.head_hash)):
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError(f"hierarchical takeover {name} hash is invalid")
        normalizer = payload.get("normalizer")
        metadata = payload.get("metadata")
        gate_state = payload.get("gate_state_dict")
        tool_state = payload.get("tool_state_dict")
        if not all(isinstance(item, Mapping) for item in (normalizer, metadata, gate_state, tool_state)):
            raise ValueError("hierarchical takeover artifact sections are incomplete")
        self.feature_mean = normalizer.get("mean")
        self.feature_std = normalizer.get("std")
        if (
            not isinstance(self.feature_mean, torch.Tensor)
            or not isinstance(self.feature_std, torch.Tensor)
            or tuple(self.feature_mean.shape) != (2560,)
            or tuple(self.feature_std.shape) != (2560,)
            or self.feature_mean.dtype != torch.float32
            or self.feature_std.dtype != torch.float32
            or not bool(torch.isfinite(self.feature_mean).all() and torch.isfinite(self.feature_std).all())
            or not bool((self.feature_std > 0).all())
        ):
            raise ValueError("hierarchical takeover normalizer is invalid")
        self.gate = BinaryTakeoverHeadNetwork.create().cpu().eval()
        self.tool = BinaryTakeoverHeadNetwork.create().cpu().eval()
        self.gate.load_state_dict(dict(gate_state), strict=True)
        self.tool.load_state_dict(dict(tool_state), strict=True)
        if any(not bool(torch.isfinite(value).all()) for model in (self.gate, self.tool) for value in model.state_dict().values()):
            raise ValueError("hierarchical takeover head contains non-finite tensors")
        tensor_digests = {
            "normalizer.mean": _tensor_digest(self.feature_mean),
            "normalizer.std": _tensor_digest(self.feature_std),
            **{f"gate_state_dict.{name}": _tensor_digest(value) for name, value in sorted(self.gate.state_dict().items())},
            **{f"tool_state_dict.{name}": _tensor_digest(value) for name, value in sorted(self.tool.state_dict().items())},
        }
        identity = {
            "schema_version": HIERARCHICAL_TAKEOVER_HEAD_SCHEMA,
            "gate_labels": list(GATE_LABELS),
            "tool_labels": list(TOOL_LABELS),
            "feature_protocol": self.feature_protocol,
            "model_hash": self.model_hash,
            "tensor_digests": tensor_digests,
            "metadata": dict(metadata),
        }
        if canonical_digest(identity) != self.head_hash:
            raise ValueError("hierarchical takeover head tensor identity mismatch")
        self.metadata = dict(metadata)

    def raw_logits(self, features: Sequence[float] | Any) -> dict[str, tuple[float, float]]:
        import torch

        values = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(values.shape) != (2560,) or not bool(torch.isfinite(values).all()):
            raise ValueError("hierarchical takeover input feature is invalid")
        normalized = (values - self.feature_mean) / self.feature_std
        with torch.no_grad():
            gate = self.gate(normalized.unsqueeze(0))[0]
            tool = self.tool(normalized.unsqueeze(0))[0]
        if tuple(gate.shape) != (2,) or tuple(tool.shape) != (2,) or not bool(torch.isfinite(gate).all() and torch.isfinite(tool).all()):
            raise RuntimeError("hierarchical takeover head produced invalid logits")
        return {
            "gate": tuple(float(value) for value in gate.tolist()),
            "tool": tuple(float(value) for value in tool.tolist()),
        }

    def select(self, features: Sequence[float] | Any) -> str:
        logits = self.raw_logits(features)
        gate_index = max(range(2), key=lambda item: (logits["gate"][item], -item))
        if GATE_LABELS[gate_index] == "DEFER":
            return "DEFER"
        tool_index = max(range(2), key=lambda item: (logits["tool"][item], -item))
        return TOOL_LABELS[tool_index]


__all__ = [
    "BinaryTakeoverHeadNetwork",
    "GATE_LABELS",
    "HIERARCHICAL_TAKEOVER_HEAD_SCHEMA",
    "HierarchicalNetworkTakeoverHead",
    "TOOL_LABELS",
    "sha256_file",
]
