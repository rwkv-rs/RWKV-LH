"""Validated train-only PCA boundary for the selected WKV State Router."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Mapping, Sequence

from rwkv_lh.state_router.local_backend import LocalVLLMRWKVExtractor
from rwkv_lh.state_router.model import HiddenFeatures
from rwkv_lh.state_router.protocol import canonical_digest, canonical_json


WKV_PCA_SCHEMA_VERSION = "rwkv-lh.state-router-wkv-pca.v1"
WKV_FEATURE_PROTOCOL_VERSION = "rwkv-lh.vllm-rwkv-final-wkv-statistics.v1"
PROJECTED_WKV_PROTOCOL_VERSION = "rwkv-lh.vllm-rwkv-wkv-pca.v1"


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _projection_digest(metadata: Mapping[str, Any], tensors: Sequence[Any]) -> str:
    digest = hashlib.sha256(canonical_json(metadata).encode("utf-8"))
    for tensor in tensors:
        value = tensor.detach().float().cpu().contiguous()
        tensor_identity = {"shape": list(value.shape), "dtype": "float32"}
        digest.update(canonical_json(tensor_identity).encode("utf-8"))
        digest.update(value.numpy().tobytes(order="C"))
    return digest.hexdigest()


class ProjectedWKVExtractor:
    """Extract vllm-rwkv WKV state and apply a frozen train-only PCA."""

    def __init__(
        self,
        base: LocalVLLMRWKVExtractor,
        projection_path: str | Path,
        *,
        expected_model_hash: str,
        expected_projection_digest: str,
        expected_projection_sha256: str,
    ) -> None:
        import torch

        self.base = base
        self.projection_path = Path(projection_path).expanduser().resolve()
        if not self.projection_path.is_file():
            raise RuntimeError(f"missing WKV PCA artifact: {self.projection_path}")
        actual_sha256 = _file_sha256(self.projection_path)
        if actual_sha256 != expected_projection_sha256:
            raise RuntimeError("WKV PCA artifact checksum mismatch")
        value = torch.load(
            self.projection_path,
            map_location="cpu",
            weights_only=True,
        )
        required_keys = {
            "schema_version",
            "source_model_hash",
            "dataset_sha256",
            "fit_split",
            "seed",
            "pca_dim",
            "projection_digest",
            "mean",
            "components",
            "singular_values",
        }
        if not isinstance(value, Mapping) or set(value) != required_keys:
            raise RuntimeError("unsupported WKV PCA artifact structure")
        if value["schema_version"] != WKV_PCA_SCHEMA_VERSION:
            raise RuntimeError("unsupported WKV PCA artifact schema")
        if value["fit_split"] != "train":
            raise RuntimeError("WKV PCA must be fitted on the train split only")
        if value["source_model_hash"] != base.model_hash:
            raise RuntimeError("WKV PCA source model does not match local vllm-rwkv")
        mean = value["mean"]
        components = value["components"]
        singular_values = value["singular_values"]
        pca_dim = int(value["pca_dim"])
        if not all(
            isinstance(item, torch.Tensor)
            for item in (mean, components, singular_values)
        ):
            raise RuntimeError("WKV PCA arrays must be tensors")
        if (
            mean.ndim != 1
            or components.ndim != 2
            or singular_values.ndim != 1
            or components.shape[0] != mean.shape[0]
            or components.shape[1] != pca_dim
            or singular_values.shape[0] != pca_dim
        ):
            raise RuntimeError("WKV PCA tensor shape mismatch")
        if not all(
            bool(torch.isfinite(item).all())
            for item in (mean, components, singular_values)
        ):
            raise RuntimeError("WKV PCA tensors must be finite")
        metadata = {
            "schema_version": value["schema_version"],
            "source_model_hash": value["source_model_hash"],
            "dataset_sha256": value["dataset_sha256"],
            "fit_split": value["fit_split"],
            "seed": value["seed"],
            "pca_dim": value["pca_dim"],
        }
        actual_digest = _projection_digest(
            metadata,
            [mean, components, singular_values],
        )
        if actual_digest != value["projection_digest"]:
            raise RuntimeError("WKV PCA projection digest mismatch")
        if actual_digest != expected_projection_digest:
            raise RuntimeError("WKV PCA does not match the trained Router head")
        model_hash = canonical_digest(
            {
                "source_model_hash": base.model_hash,
                "projection_schema": WKV_PCA_SCHEMA_VERSION,
                "projection_digest": actual_digest,
            }
        )
        if model_hash != expected_model_hash:
            raise RuntimeError("projected WKV model hash does not match Router head")
        self._mean = mean.detach().float().cpu().contiguous()
        self._components = components.detach().float().cpu().contiguous()
        self._model_hash = model_hash
        self._projection_digest = actual_digest
        self._projection_sha256 = actual_sha256
        self._dataset_sha256 = str(value["dataset_sha256"])

    @property
    def model_hash(self) -> str:
        return self._model_hash

    @property
    def feature_dim(self) -> int:
        return int(self._components.shape[1])

    def identity(self) -> dict[str, Any]:
        return {
            **self.base.identity(),
            "feature_protocol": PROJECTED_WKV_PROTOCOL_VERSION,
            "source_feature_protocol": WKV_FEATURE_PROTOCOL_VERSION,
            "projection": {
                "path": str(self.projection_path),
                "schema_version": WKV_PCA_SCHEMA_VERSION,
                "sha256": self._projection_sha256,
                "digest": self._projection_digest,
                "dataset_sha256": self._dataset_sha256,
                "fit_split": "train",
                "input_dim": int(self._components.shape[0]),
                "output_dim": self.feature_dim,
            },
            "model_hash": self.model_hash,
        }

    def extract(self, texts: Sequence[str]) -> list[HiddenFeatures]:
        import torch

        statistics, token_counts, identity = self.base.extract_wkv_statistics(texts)
        if identity.get("feature_protocol") != WKV_FEATURE_PROTOCOL_VERSION:
            raise RuntimeError("unexpected local vllm-rwkv WKV feature protocol")
        if statistics.ndim != 2 or statistics.shape[1] != self._mean.shape[0]:
            raise RuntimeError("local vllm-rwkv WKV feature dimension mismatch")
        projected = (statistics.detach().float().cpu() - self._mean) @ self._components
        if not bool(torch.isfinite(projected).all()):
            raise RuntimeError("projected WKV features must be finite")
        return [
            HiddenFeatures(
                values=tuple(float(item) for item in row.tolist()),
                model_hash=self.model_hash,
                token_count=token_count,
            )
            for row, token_count in zip(projected, token_counts, strict=True)
        ]


__all__ = [
    "PROJECTED_WKV_PROTOCOL_VERSION",
    "ProjectedWKVExtractor",
    "WKV_FEATURE_PROTOCOL_VERSION",
    "WKV_PCA_SCHEMA_VERSION",
]
