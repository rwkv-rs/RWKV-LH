"""Dependency-light multi-head MLP inference for State Router artifacts."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.state_router.protocol import (
    HEAD_LABELS,
    AbstainThresholds,
    RouterInput,
    RouterOutput,
    canonical_digest,
    resolve_router_output,
)


ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION = "rwkv-lh.state-router-head.v1"
HIDDEN_FEATURE_PROTOCOL_VERSION = "rwkv-lh.final-hidden-mean.v1"


@dataclass(frozen=True)
class HiddenFeatures:
    values: tuple[float, ...]
    model_hash: str
    token_count: int
    ood_score: float = 0.0
    protocol_version: str = HIDDEN_FEATURE_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        if self.protocol_version != HIDDEN_FEATURE_PROTOCOL_VERSION:
            raise ValueError(
                f"unsupported hidden feature protocol: {self.protocol_version}"
            )
        if not self.values or any(not math.isfinite(value) for value in self.values):
            raise ValueError("hidden features must be a non-empty finite vector")
        if not self.model_hash or self.token_count < 1:
            raise ValueError("hidden features require model hash and positive token count")
        if not math.isfinite(self.ood_score) or self.ood_score < 0.0:
            raise ValueError("hidden feature ood_score must be finite and non-negative")


class HiddenFeatureExtractor(Protocol):
    def extract(self, texts: Sequence[str]) -> Sequence[HiddenFeatures]: ...


def _vector(value: Any, *, name: str, length: int | None = None) -> tuple[float, ...]:
    if not isinstance(value, list):
        raise ValueError(f"{name} must be an array")
    result = tuple(float(item) for item in value)
    if length is not None and len(result) != length:
        raise ValueError(f"{name} must contain {length} values")
    if any(not math.isfinite(item) for item in result):
        raise ValueError(f"{name} must contain finite values")
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
class LinearLayer:
    weight: tuple[tuple[float, ...], ...]
    bias: tuple[float, ...]

    def apply(self, values: Sequence[float]) -> list[float]:
        return [
            sum(coefficient * value for coefficient, value in zip(row, values))
            + bias
            for row, bias in zip(self.weight, self.bias)
        ]


@dataclass(frozen=True)
class MultiHeadMLPArtifact:
    feature_dim: int
    hidden_dim: int
    feature_mean: tuple[float, ...]
    feature_std: tuple[float, ...]
    shared: LinearLayer
    layer_norm_weight: tuple[float, ...]
    layer_norm_bias: tuple[float, ...]
    heads: Mapping[str, LinearLayer]
    temperatures: Mapping[str, float]
    thresholds: AbstainThresholds
    model_hash: str
    head_hash: str
    metadata: Mapping[str, Any]
    schema_version: str = ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "MultiHeadMLPArtifact":
        if str(value.get("schema_version") or "") != ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION:
            raise ValueError("unsupported State Router head artifact schema")
        feature_dim = int(value.get("feature_dim") or 0)
        hidden_dim = int(value.get("hidden_dim") or 0)
        if feature_dim < 1 or hidden_dim < 1:
            raise ValueError("State Router dimensions must be positive")
        normalizer = value.get("normalizer")
        shared_value = value.get("shared")
        layer_norm = value.get("layer_norm")
        heads_value = value.get("heads")
        if not all(
            isinstance(item, Mapping)
            for item in (normalizer, shared_value, layer_norm, heads_value)
        ):
            raise ValueError("State Router artifact sections must be objects")
        feature_mean = _vector(
            normalizer.get("mean"), name="normalizer.mean", length=feature_dim
        )
        feature_std = _vector(
            normalizer.get("std"), name="normalizer.std", length=feature_dim
        )
        if any(item <= 0.0 for item in feature_std):
            raise ValueError("normalizer.std values must be positive")
        shared = LinearLayer(
            weight=_matrix(
                shared_value.get("weight"),
                name="shared.weight",
                rows=hidden_dim,
                columns=feature_dim,
            ),
            bias=_vector(
                shared_value.get("bias"), name="shared.bias", length=hidden_dim
            ),
        )
        layer_norm_weight = _vector(
            layer_norm.get("weight"), name="layer_norm.weight", length=hidden_dim
        )
        layer_norm_bias = _vector(
            layer_norm.get("bias"), name="layer_norm.bias", length=hidden_dim
        )
        if float(layer_norm.get("eps", 0.0)) != 1e-5:
            raise ValueError("State Router v1 requires layer_norm.eps=1e-5")
        if set(heads_value) != set(HEAD_LABELS):
            raise ValueError("artifact must contain exactly the four Router heads")
        heads: dict[str, LinearLayer] = {}
        for name, labels in HEAD_LABELS.items():
            item = heads_value[name]
            if not isinstance(item, Mapping):
                raise ValueError(f"heads.{name} must be an object")
            if item.get("labels") != list(labels):
                raise ValueError(f"heads.{name}.labels do not match the v1 protocol")
            heads[name] = LinearLayer(
                weight=_matrix(
                    item.get("weight"),
                    name=f"heads.{name}.weight",
                    rows=len(labels),
                    columns=hidden_dim,
                ),
                bias=_vector(
                    item.get("bias"),
                    name=f"heads.{name}.bias",
                    length=len(labels),
                ),
            )
        temperatures_value = value.get("temperatures")
        if not isinstance(temperatures_value, Mapping):
            raise ValueError("temperatures must be an object")
        temperatures = {
            name: float(temperatures_value.get(name) or 0.0) for name in HEAD_LABELS
        }
        if any(
            not math.isfinite(item) or item <= 0.0 for item in temperatures.values()
        ):
            raise ValueError("all head temperatures must be positive and finite")
        thresholds_value = value.get("thresholds")
        if not isinstance(thresholds_value, Mapping):
            raise ValueError("thresholds must be an object")
        thresholds = AbstainThresholds(
            route_confidence=float(thresholds_value.get("route_confidence")),
            route_margin=float(thresholds_value.get("route_margin")),
            ood_score=float(thresholds_value.get("ood_score")),
        )
        if thresholds != AbstainThresholds():
            raise ValueError("State Router v1 artifact changed the frozen thresholds")
        model_hash = str(value.get("model_hash") or "")
        if not model_hash:
            raise ValueError("State Router artifact requires a model hash")
        metadata_value = value.get("metadata")
        if not isinstance(metadata_value, Mapping):
            raise ValueError("State Router artifact metadata must be an object")
        artifact_without_hash = dict(value)
        claimed_head_hash = str(artifact_without_hash.pop("head_hash", ""))
        actual_head_hash = canonical_digest(artifact_without_hash)
        if claimed_head_hash != actual_head_hash:
            raise ValueError("State Router head artifact digest mismatch")
        return cls(
            feature_dim=feature_dim,
            hidden_dim=hidden_dim,
            feature_mean=feature_mean,
            feature_std=feature_std,
            shared=shared,
            layer_norm_weight=layer_norm_weight,
            layer_norm_bias=layer_norm_bias,
            heads=heads,
            temperatures=temperatures,
            thresholds=thresholds,
            model_hash=model_hash,
            head_hash=claimed_head_hash,
            metadata=dict(metadata_value),
        )

    @classmethod
    def load(cls, path: str | Path) -> "MultiHeadMLPArtifact":
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError("State Router head artifact must be a JSON object")
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
    def _softmax(logits: Sequence[float], temperature: float) -> list[float]:
        scaled = [float(value) / temperature for value in logits]
        offset = max(scaled)
        values = [math.exp(value - offset) for value in scaled]
        total = sum(values)
        return [value / total for value in values]

    def predict_probabilities(
        self, features: Sequence[float]
    ) -> dict[str, dict[str, float]]:
        if len(features) != self.feature_dim:
            raise ValueError(
                f"feature dimension mismatch: expected {self.feature_dim}, got {len(features)}"
            )
        normalized = [
            (float(value) - mean) / std
            for value, mean, std in zip(
                features, self.feature_mean, self.feature_std
            )
        ]
        hidden = [self._gelu(value) for value in self.shared.apply(normalized)]
        mean = sum(hidden) / len(hidden)
        variance = sum((value - mean) ** 2 for value in hidden) / len(hidden)
        inverse_std = 1.0 / math.sqrt(variance + 1e-5)
        hidden = [
            (value - mean) * inverse_std * weight + bias
            for value, weight, bias in zip(
                hidden, self.layer_norm_weight, self.layer_norm_bias
            )
        ]
        result: dict[str, dict[str, float]] = {}
        for name, labels in HEAD_LABELS.items():
            probabilities = self._softmax(
                self.heads[name].apply(hidden), self.temperatures[name]
            )
            result[name] = dict(zip(labels, probabilities))
        return result


class StateRouter:
    """Local feature extractor + calibrated MLP advisory router."""

    def __init__(
        self,
        extractor: HiddenFeatureExtractor,
        artifact: MultiHeadMLPArtifact,
    ) -> None:
        self.extractor = extractor
        self.artifact = artifact

    def route_many(self, inputs: Sequence[RouterInput]) -> list[RouterOutput]:
        features = list(self.extractor.extract([item.render() for item in inputs]))
        if len(features) != len(inputs):
            raise RuntimeError("hidden extractor returned the wrong number of rows")
        outputs: list[RouterOutput] = []
        for router_input, hidden in zip(inputs, features):
            if hidden.model_hash != self.artifact.model_hash:
                raise RuntimeError(
                    "hidden extractor model hash does not match trained Router head"
                )
            outputs.append(
                resolve_router_output(
                    router_input,
                    self.artifact.predict_probabilities(hidden.values),
                    model_hash=hidden.model_hash,
                    head_hash=self.artifact.head_hash,
                    thresholds=self.artifact.thresholds,
                    ood_score=hidden.ood_score,
                )
            )
        return outputs

    def route(self, router_input: RouterInput) -> RouterOutput:
        return self.route_many([router_input])[0]


__all__ = [
    "HIDDEN_FEATURE_PROTOCOL_VERSION",
    "ROUTER_HEAD_ARTIFACT_SCHEMA_VERSION",
    "HiddenFeatureExtractor",
    "HiddenFeatures",
    "MultiHeadMLPArtifact",
    "StateRouter",
]
