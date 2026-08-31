"""Validated three-way Hidden+MLP network-function takeover head."""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.model_v2 import NETWORK_SELECTOR_FEATURE_PROTOCOLS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


NETWORK_TAKEOVER_LABELS = ("web_search", "connector_lookup", "DEFER")
NETWORK_TAKEOVER_HEAD_SCHEMA = "rwkv-lh.network-function-takeover-head.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _tensor_digest(value: Any) -> str:
    return hashlib.sha256(value.detach().cpu().contiguous().numpy().tobytes()).hexdigest()


class NetworkTakeoverHeadNetwork:
    """Factory for the frozen S10 MLP topology."""

    @staticmethod
    def create() -> Any:
        import torch

        class Network(torch.nn.Module):
            def __init__(self) -> None:
                super().__init__()
                self.shared = torch.nn.Linear(2560, 256)
                self.layer_norm = torch.nn.LayerNorm(256, eps=1e-5)
                self.dropout = torch.nn.Dropout(0.2)
                self.head = torch.nn.Linear(256, 3)

            def forward(self, features: Any) -> Any:
                if features.ndim != 2 or features.shape[-1] != 2560:
                    raise ValueError("network takeover feature shape mismatch")
                hidden = torch.nn.functional.gelu(
                    self.shared(features), approximate="tanh"
                )
                return self.head(self.dropout(self.layer_norm(hidden)))

        return Network()


class NetworkTakeoverHead:
    """Load a pinned artifact and expose its complete unmodified raw logits."""

    def __init__(self, path: Path, expected_sha256: str | None = None) -> None:
        import torch

        self.path = path.resolve()
        self.file_sha256 = sha256_file(self.path)
        if expected_sha256 is not None and self.file_sha256 != expected_sha256:
            raise ValueError("network takeover head file SHA-256 mismatch")
        payload = torch.load(self.path, map_location="cpu", weights_only=True)
        if not isinstance(payload, Mapping) or payload.get("schema_version") != NETWORK_TAKEOVER_HEAD_SCHEMA:
            raise ValueError("unsupported network takeover head schema")
        if tuple(payload.get("labels") or ()) != NETWORK_TAKEOVER_LABELS:
            raise ValueError("network takeover labels/order changed")
        self.feature_protocol = str(payload.get("feature_protocol") or "")
        if self.feature_protocol not in NETWORK_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError("unsupported network takeover feature protocol")
        self.model_hash = str(payload.get("model_hash") or "")
        self.head_hash = str(payload.get("head_hash") or "")
        for name, digest in (("model", self.model_hash), ("head", self.head_hash)):
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError(f"network takeover {name} hash is invalid")
        normalizer = payload.get("normalizer")
        state_dict = payload.get("state_dict")
        metadata = payload.get("metadata")
        if not isinstance(normalizer, Mapping) or not isinstance(state_dict, Mapping) or not isinstance(metadata, Mapping):
            raise ValueError("network takeover artifact sections are incomplete")
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
            raise ValueError("network takeover normalizer is invalid")
        self.model = NetworkTakeoverHeadNetwork.create().cpu().eval()
        self.model.load_state_dict(dict(state_dict), strict=True)
        if any(not bool(torch.isfinite(value).all()) for value in self.model.state_dict().values()):
            raise ValueError("network takeover head contains non-finite tensors")
        tensor_digests = {
            "normalizer.mean": _tensor_digest(self.feature_mean),
            "normalizer.std": _tensor_digest(self.feature_std),
            **{
                f"state_dict.{name}": _tensor_digest(value)
                for name, value in sorted(self.model.state_dict().items())
            },
        }
        identity = {
            "schema_version": NETWORK_TAKEOVER_HEAD_SCHEMA,
            "labels": list(NETWORK_TAKEOVER_LABELS),
            "feature_protocol": self.feature_protocol,
            "model_hash": self.model_hash,
            "tensor_digests": tensor_digests,
            "metadata": dict(metadata),
        }
        if canonical_digest(identity) != self.head_hash:
            raise ValueError("network takeover head tensor identity mismatch")
        self.labels = NETWORK_TAKEOVER_LABELS
        self.metadata = dict(metadata)

    def raw_logits(self, features: Sequence[float] | Any) -> tuple[float, ...]:
        import torch

        values = torch.as_tensor(features, dtype=torch.float32, device="cpu")
        if tuple(values.shape) != (2560,) or not bool(torch.isfinite(values).all()):
            raise ValueError("network takeover input feature is invalid")
        normalized = (values - self.feature_mean) / self.feature_std
        with torch.no_grad():
            logits = self.model(normalized.unsqueeze(0))[0]
        if tuple(logits.shape) != (3,) or not bool(torch.isfinite(logits).all()):
            raise RuntimeError("network takeover head produced invalid logits")
        return tuple(float(value) for value in logits.tolist())

    def select(self, features: Sequence[float] | Any) -> str:
        logits = self.raw_logits(features)
        index = max(range(3), key=lambda item: (logits[item], -item))
        return self.labels[index]


__all__ = [
    "NETWORK_TAKEOVER_HEAD_SCHEMA",
    "NETWORK_TAKEOVER_LABELS",
    "NetworkTakeoverHead",
    "NetworkTakeoverHeadNetwork",
    "sha256_file",
]
