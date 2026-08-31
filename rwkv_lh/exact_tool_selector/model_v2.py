"""Dependency-light inference for the frozen 25-class Selector MLP head."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest

NETWORK_SELECTOR_HEAD_SCHEMA_VERSION = "rwkv-lh.network-exact-tool-selector-head.v1"
NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL = (
    "rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1"
)
NETWORK_SELECTOR_FEATURE_PROTOCOLS = frozenset(
    {
        "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    }
)


def _vector(value: Any, *, name: str, length: int) -> tuple[float, ...]:
    if not isinstance(value, list) or len(value) != length:
        raise ValueError(f"{name} must contain {length} values")
    result = tuple(float(item) for item in value)
    if any(not math.isfinite(item) for item in result):
        raise ValueError(f"{name} contains non-finite values")
    return result


def _matrix(
    value: Any,
    *,
    name: str,
    rows: int,
    columns: int,
) -> tuple[tuple[float, ...], ...]:
    if not isinstance(value, list) or len(value) != rows:
        raise ValueError(f"{name} must contain {rows} rows")
    return tuple(
        _vector(row, name=f"{name}[{index}]", length=columns)
        for index, row in enumerate(value)
    )


@dataclass(frozen=True)
class NetworkSelectorMLPArtifact:
    feature_dim: int
    hidden_dim: int
    labels: tuple[str, ...]
    feature_protocol: str
    feature_mean: tuple[float, ...]
    feature_std: tuple[float, ...]
    shared_weight: tuple[tuple[float, ...], ...]
    shared_bias: tuple[float, ...]
    layer_norm_weight: tuple[float, ...]
    layer_norm_bias: tuple[float, ...]
    head_weight: tuple[tuple[float, ...], ...]
    head_bias: tuple[float, ...]
    temperature: float
    model_hash: str
    head_hash: str
    metadata: Mapping[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "NetworkSelectorMLPArtifact":
        if value.get("schema_version") != NETWORK_SELECTOR_HEAD_SCHEMA_VERSION:
            raise ValueError("unsupported network Selector head schema")
        feature_dim = int(value.get("feature_dim") or 0)
        hidden_dim = int(value.get("hidden_dim") or 0)
        if feature_dim < 1 or hidden_dim < 1:
            raise ValueError("network Selector artifact dimensions must be positive")
        labels = tuple(str(item) for item in value.get("labels") or ())
        if labels != NETWORK_EXACT_TOOL_LABELS:
            raise ValueError("network Selector artifact labels/order differ from v2")
        feature_protocol = str(value.get("feature_protocol") or "")
        if feature_protocol not in NETWORK_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError("unsupported network Selector feature protocol")
        temperature = float(value.get("temperature") or 0.0)
        if not math.isfinite(temperature) or temperature <= 0.0:
            raise ValueError("network Selector temperature must be positive and finite")
        model_hash = str(value.get("model_hash") or "")
        claimed_hash = str(value.get("head_hash") or "")
        for name, digest in (("model_hash", model_hash), ("head_hash", claimed_hash)):
            if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
                raise ValueError(f"network Selector {name} must be lowercase SHA-256")
        unhashed = dict(value)
        unhashed.pop("head_hash", None)
        if canonical_digest(unhashed) != claimed_hash:
            raise ValueError("network Selector head artifact digest mismatch")
        metadata = value.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError("network Selector artifact metadata must be an object")
        feature_std = _vector(value.get("feature_std"), name="feature_std", length=feature_dim)
        if any(item <= 0.0 for item in feature_std):
            raise ValueError("network Selector feature_std must be positive")
        return cls(
            feature_dim=feature_dim,
            hidden_dim=hidden_dim,
            labels=labels,
            feature_protocol=feature_protocol,
            feature_mean=_vector(value.get("feature_mean"), name="feature_mean", length=feature_dim),
            feature_std=feature_std,
            shared_weight=_matrix(value.get("shared_weight"), name="shared_weight", rows=hidden_dim, columns=feature_dim),
            shared_bias=_vector(value.get("shared_bias"), name="shared_bias", length=hidden_dim),
            layer_norm_weight=_vector(value.get("layer_norm_weight"), name="layer_norm_weight", length=hidden_dim),
            layer_norm_bias=_vector(value.get("layer_norm_bias"), name="layer_norm_bias", length=hidden_dim),
            head_weight=_matrix(value.get("head_weight"), name="head_weight", rows=len(labels), columns=hidden_dim),
            head_bias=_vector(value.get("head_bias"), name="head_bias", length=len(labels)),
            temperature=temperature,
            model_hash=model_hash,
            head_hash=claimed_hash,
            metadata=dict(metadata),
        )

    @classmethod
    def load(cls, path: str | Path) -> "NetworkSelectorMLPArtifact":
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("network Selector head artifact must be a JSON object")
        return cls.from_dict(value)

    @staticmethod
    def _gelu(value: float) -> float:
        return 0.5 * value * (
            1.0
            + math.tanh(
                math.sqrt(2.0 / math.pi) * (value + 0.044715 * value**3)
            )
        )

    @staticmethod
    def _linear(
        values: Sequence[float],
        weight: Sequence[Sequence[float]],
        bias: Sequence[float],
    ) -> list[float]:
        return [
            sum(float(source) * coefficient for source, coefficient in zip(values, row)) + offset
            for row, offset in zip(weight, bias)
        ]

    def raw_logits(self, features: Sequence[float]) -> tuple[float, ...]:
        """Return the complete unmodified logits used by the argmax handoff."""

        if len(features) != self.feature_dim:
            raise ValueError(
                f"network Selector feature dimension mismatch: expected {self.feature_dim}, got {len(features)}"
            )
        values = [float(item) for item in features]
        if any(not math.isfinite(item) for item in values):
            raise ValueError("network Selector features contain non-finite values")
        normalized = [
            (item - mean) / std
            for item, mean, std in zip(values, self.feature_mean, self.feature_std)
        ]
        hidden = [
            self._gelu(item)
            for item in self._linear(normalized, self.shared_weight, self.shared_bias)
        ]
        mean = sum(hidden) / len(hidden)
        variance = sum((item - mean) ** 2 for item in hidden) / len(hidden)
        inverse_std = 1.0 / math.sqrt(variance + 1e-5)
        normalized_hidden = [
            (item - mean) * inverse_std * weight + bias
            for item, weight, bias in zip(
                hidden, self.layer_norm_weight, self.layer_norm_bias
            )
        ]
        logits = tuple(
            self._linear(normalized_hidden, self.head_weight, self.head_bias)
        )
        if any(not math.isfinite(item) for item in logits):
            raise RuntimeError("network Selector head produced non-finite logits")
        return logits

    def probabilities(self, features: Sequence[float]) -> tuple[float, ...]:
        logits = [item / self.temperature for item in self.raw_logits(features)]
        offset = max(logits)
        values = [math.exp(item - offset) for item in logits]
        total = sum(values)
        return tuple(item / total for item in values)

    def select(self, features: Sequence[float]) -> str:
        logits = self.raw_logits(features)
        index = max(range(len(logits)), key=lambda item: (logits[item], -item))
        return self.labels[index]


__all__ = [
    "NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL",
    "NETWORK_SELECTOR_FEATURE_PROTOCOLS",
    "NETWORK_SELECTOR_HEAD_SCHEMA_VERSION",
    "NetworkSelectorMLPArtifact",
]
