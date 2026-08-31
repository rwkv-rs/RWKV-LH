"""Dependency-light inference for a frozen two-expert Selector Soft-MoE head."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_FEATURE_PROTOCOLS,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION = (
    "rwkv-lh.network-selector-soft-moe-head.v1"
)
NETWORK_SELECTOR_SOFT_MOE_RAW_LOGIT_FORMULA = (
    "old_logits + sigmoid(gate_logit) * (continuation_logits - old_logits)"
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: Any, *, name: str) -> str:
    result = str(value or "")
    if len(result) != 64 or any(
        character not in "0123456789abcdef" for character in result
    ):
        raise ValueError(f"network Selector Soft-MoE {name} must be lowercase SHA-256")
    return result


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
class NetworkSelectorHeadReference:
    path: str
    sha256: str
    head_hash: str

    @classmethod
    def from_dict(
        cls, value: Any, *, name: str
    ) -> "NetworkSelectorHeadReference":
        if not isinstance(value, Mapping) or set(value) != {
            "path",
            "sha256",
            "head_hash",
        }:
            raise ValueError(
                f"network Selector Soft-MoE {name} reference fields changed"
            )
        path = str(value.get("path") or "")
        reference = Path(path)
        if (
            not path
            or reference.is_absolute()
            or "\\" in path
            or any(part in {"", ".", ".."} for part in reference.parts)
        ):
            raise ValueError(
                f"network Selector Soft-MoE {name} path must be a safe relative path"
            )
        return cls(
            path=path,
            sha256=_digest(value.get("sha256"), name=f"{name} sha256"),
            head_hash=_digest(
                value.get("head_hash"), name=f"{name} head_hash"
            ),
        )


def _resolve_reference(artifact_path: Path, reference: NetworkSelectorHeadReference) -> Path:
    relative = Path(reference.path)
    checked: list[Path] = []
    for root in (artifact_path.parent, *artifact_path.parents):
        resolved_root = root.resolve()
        candidate = (resolved_root / relative).resolve()
        if not candidate.is_relative_to(resolved_root):
            continue
        checked.append(candidate)
        if candidate.is_file():
            return candidate
    raise ValueError(
        "network Selector Soft-MoE expert artifact is missing: "
        f"{reference.path} (searched {len(checked)} roots)"
    )


@dataclass(frozen=True)
class NetworkSelectorSoftMoEArtifact:
    feature_dim: int
    gate_hidden_dim: int
    labels: tuple[str, ...]
    feature_protocol: str
    feature_mean: tuple[float, ...]
    feature_std: tuple[float, ...]
    old_head: NetworkSelectorHeadReference
    continuation_head: NetworkSelectorHeadReference
    gate_shared_weight: tuple[tuple[float, ...], ...]
    gate_shared_bias: tuple[float, ...]
    gate_layer_norm_weight: tuple[float, ...]
    gate_layer_norm_bias: tuple[float, ...]
    gate_head_weight: tuple[tuple[float, ...], ...]
    gate_head_bias: tuple[float, ...]
    temperature: float
    raw_logit_formula: str
    model_hash: str
    head_hash: str
    metadata: Mapping[str, Any]
    old_artifact: NetworkSelectorMLPArtifact
    continuation_artifact: NetworkSelectorMLPArtifact

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        old_artifact: NetworkSelectorMLPArtifact,
        continuation_artifact: NetworkSelectorMLPArtifact,
    ) -> "NetworkSelectorSoftMoEArtifact":
        if value.get("schema_version") != NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION:
            raise ValueError("unsupported network Selector Soft-MoE head schema")
        feature_dim = int(value.get("feature_dim") or 0)
        gate_hidden_dim = int(value.get("gate_hidden_dim") or 0)
        if feature_dim < 1 or gate_hidden_dim < 1:
            raise ValueError(
                "network Selector Soft-MoE artifact dimensions must be positive"
            )
        labels = tuple(str(item) for item in value.get("labels") or ())
        if labels != NETWORK_EXACT_TOOL_LABELS:
            raise ValueError(
                "network Selector Soft-MoE artifact labels/order differ from v2"
            )
        feature_protocol = str(value.get("feature_protocol") or "")
        if feature_protocol not in NETWORK_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError(
                "unsupported network Selector Soft-MoE feature protocol"
            )
        temperature = float(value.get("temperature") or 0.0)
        if not math.isfinite(temperature) or temperature <= 0.0:
            raise ValueError(
                "network Selector Soft-MoE temperature must be positive and finite"
            )
        raw_logit_formula = str(value.get("raw_logit_formula") or "")
        if raw_logit_formula != NETWORK_SELECTOR_SOFT_MOE_RAW_LOGIT_FORMULA:
            raise ValueError("network Selector Soft-MoE raw-logit formula changed")
        model_hash = _digest(value.get("model_hash"), name="model_hash")
        claimed_hash = _digest(value.get("head_hash"), name="head_hash")
        unhashed = dict(value)
        unhashed.pop("head_hash", None)
        if canonical_digest(unhashed) != claimed_hash:
            raise ValueError("network Selector Soft-MoE head artifact digest mismatch")
        metadata = value.get("metadata")
        if not isinstance(metadata, Mapping):
            raise ValueError(
                "network Selector Soft-MoE artifact metadata must be an object"
            )
        old_head = NetworkSelectorHeadReference.from_dict(
            value.get("old_head"), name="old_head"
        )
        continuation_head = NetworkSelectorHeadReference.from_dict(
            value.get("continuation_head"), name="continuation_head"
        )
        for name, reference, artifact in (
            ("old_head", old_head, old_artifact),
            ("continuation_head", continuation_head, continuation_artifact),
        ):
            if artifact.head_hash != reference.head_hash:
                raise ValueError(
                    f"network Selector Soft-MoE {name} logical identity mismatch"
                )
            if (
                artifact.feature_dim != feature_dim
                or artifact.labels != labels
                or artifact.feature_protocol != feature_protocol
            ):
                raise ValueError(
                    f"network Selector Soft-MoE {name} feature identity mismatch"
                )
        feature_mean = _vector(
            value.get("feature_mean"), name="feature_mean", length=feature_dim
        )
        feature_std = _vector(
            value.get("feature_std"), name="feature_std", length=feature_dim
        )
        if any(item <= 0.0 for item in feature_std):
            raise ValueError(
                "network Selector Soft-MoE feature_std must be positive"
            )
        if (
            old_artifact.feature_mean != feature_mean
            or continuation_artifact.feature_mean != feature_mean
            or old_artifact.feature_std != feature_std
            or continuation_artifact.feature_std != feature_std
        ):
            raise ValueError(
                "network Selector Soft-MoE expert normalization identity mismatch"
            )
        return cls(
            feature_dim=feature_dim,
            gate_hidden_dim=gate_hidden_dim,
            labels=labels,
            feature_protocol=feature_protocol,
            feature_mean=feature_mean,
            feature_std=feature_std,
            old_head=old_head,
            continuation_head=continuation_head,
            gate_shared_weight=_matrix(
                value.get("gate_shared_weight"),
                name="gate_shared_weight",
                rows=gate_hidden_dim,
                columns=feature_dim,
            ),
            gate_shared_bias=_vector(
                value.get("gate_shared_bias"),
                name="gate_shared_bias",
                length=gate_hidden_dim,
            ),
            gate_layer_norm_weight=_vector(
                value.get("gate_layer_norm_weight"),
                name="gate_layer_norm_weight",
                length=gate_hidden_dim,
            ),
            gate_layer_norm_bias=_vector(
                value.get("gate_layer_norm_bias"),
                name="gate_layer_norm_bias",
                length=gate_hidden_dim,
            ),
            gate_head_weight=_matrix(
                value.get("gate_head_weight"),
                name="gate_head_weight",
                rows=1,
                columns=gate_hidden_dim,
            ),
            gate_head_bias=_vector(
                value.get("gate_head_bias"), name="gate_head_bias", length=1
            ),
            temperature=temperature,
            raw_logit_formula=raw_logit_formula,
            model_hash=model_hash,
            head_hash=claimed_hash,
            metadata=dict(metadata),
            old_artifact=old_artifact,
            continuation_artifact=continuation_artifact,
        )

    @classmethod
    def load(cls, path: str | Path) -> "NetworkSelectorSoftMoEArtifact":
        artifact_path = Path(path).resolve()
        value = json.loads(artifact_path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ValueError(
                "network Selector Soft-MoE head artifact must be a JSON object"
            )
        old_reference = NetworkSelectorHeadReference.from_dict(
            value.get("old_head"), name="old_head"
        )
        continuation_reference = NetworkSelectorHeadReference.from_dict(
            value.get("continuation_head"), name="continuation_head"
        )
        resolved: list[tuple[str, NetworkSelectorHeadReference, Path]] = []
        for name, reference in (
            ("old_head", old_reference),
            ("continuation_head", continuation_reference),
        ):
            reference_path = _resolve_reference(artifact_path, reference)
            if _sha256_file(reference_path) != reference.sha256:
                raise ValueError(
                    f"network Selector Soft-MoE {name} file SHA-256 mismatch"
                )
            resolved.append((name, reference, reference_path))
        return cls.from_dict(
            value,
            old_artifact=NetworkSelectorMLPArtifact.load(resolved[0][2]),
            continuation_artifact=NetworkSelectorMLPArtifact.load(resolved[1][2]),
        )

    @staticmethod
    def _gelu(value: float) -> float:
        return NetworkSelectorMLPArtifact._gelu(value)

    @staticmethod
    def _linear(
        values: Sequence[float],
        weight: Sequence[Sequence[float]],
        bias: Sequence[float],
    ) -> list[float]:
        return NetworkSelectorMLPArtifact._linear(values, weight, bias)

    @staticmethod
    def _sigmoid(value: float) -> float:
        if value >= 0.0:
            return 1.0 / (1.0 + math.exp(-value))
        exponent = math.exp(value)
        return exponent / (1.0 + exponent)

    def gate(self, features: Sequence[float]) -> float:
        if len(features) != self.feature_dim:
            raise ValueError(
                "network Selector Soft-MoE feature dimension mismatch: "
                f"expected {self.feature_dim}, got {len(features)}"
            )
        values = [float(item) for item in features]
        if any(not math.isfinite(item) for item in values):
            raise ValueError(
                "network Selector Soft-MoE features contain non-finite values"
            )
        normalized = [
            (item - mean) / std
            for item, mean, std in zip(
                values, self.feature_mean, self.feature_std
            )
        ]
        hidden = [
            self._gelu(item)
            for item in self._linear(
                normalized, self.gate_shared_weight, self.gate_shared_bias
            )
        ]
        mean = sum(hidden) / len(hidden)
        variance = sum((item - mean) ** 2 for item in hidden) / len(hidden)
        inverse_std = 1.0 / math.sqrt(variance + 1e-5)
        normalized_hidden = [
            (item - mean) * inverse_std * weight + bias
            for item, weight, bias in zip(
                hidden,
                self.gate_layer_norm_weight,
                self.gate_layer_norm_bias,
            )
        ]
        gate_logit = self._linear(
            normalized_hidden, self.gate_head_weight, self.gate_head_bias
        )[0]
        gate = self._sigmoid(gate_logit)
        if not math.isfinite(gate):
            raise RuntimeError(
                "network Selector Soft-MoE gate produced a non-finite value"
            )
        return gate

    def raw_logits(self, features: Sequence[float]) -> tuple[float, ...]:
        """Return the complete architecture logits without postprocessing."""

        gate = self.gate(features)
        old_logits = self.old_artifact.raw_logits(features)
        continuation_logits = self.continuation_artifact.raw_logits(features)
        logits = tuple(
            old + gate * (continuation - old)
            for old, continuation in zip(old_logits, continuation_logits)
        )
        if any(not math.isfinite(item) for item in logits):
            raise RuntimeError(
                "network Selector Soft-MoE head produced non-finite logits"
            )
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
    "NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION",
    "NETWORK_SELECTOR_SOFT_MOE_RAW_LOGIT_FORMULA",
    "NetworkSelectorHeadReference",
    "NetworkSelectorSoftMoEArtifact",
]
