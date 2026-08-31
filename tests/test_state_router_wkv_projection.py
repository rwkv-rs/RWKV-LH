from __future__ import annotations

import hashlib
from pathlib import Path

import pytest


torch = pytest.importorskip("torch")

from rwkv_lh.state_router.protocol import canonical_digest
from rwkv_lh.state_router.wkv_projection import (
    WKV_FEATURE_PROTOCOL_VERSION,
    WKV_PCA_SCHEMA_VERSION,
    ProjectedWKVExtractor,
    _projection_digest,
)


class FakeWKVExtractor:
    model_hash = "source-model-hash"

    def identity(self) -> dict:
        return {"model_hash": self.model_hash, "feature_protocol": "base"}

    def extract_wkv_statistics(self, texts: list[str]):
        assert texts == ["first", "second"]
        return (
            torch.tensor([[2.0, 4.0, 6.0], [0.0, 1.0, 2.0]]),
            [3, 5],
            {
                "model_hash": self.model_hash,
                "feature_protocol": WKV_FEATURE_PROTOCOL_VERSION,
            },
        )


def projection_value() -> dict:
    mean = torch.tensor([1.0, 1.0, 1.0])
    components = torch.tensor([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]])
    singular_values = torch.tensor([3.0, 2.0])
    metadata = {
        "schema_version": WKV_PCA_SCHEMA_VERSION,
        "source_model_hash": "source-model-hash",
        "dataset_sha256": "dataset-hash",
        "fit_split": "train",
        "seed": 829,
        "pca_dim": 2,
    }
    return {
        **metadata,
        "projection_digest": _projection_digest(
            metadata,
            [mean, components, singular_values],
        ),
        "mean": mean,
        "components": components,
        "singular_values": singular_values,
    }


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_projected_wkv_extractor_validates_and_projects(tmp_path: Path) -> None:
    value = projection_value()
    path = tmp_path / "projection.pt"
    torch.save(value, path)
    expected_model_hash = canonical_digest(
        {
            "source_model_hash": "source-model-hash",
            "projection_schema": WKV_PCA_SCHEMA_VERSION,
            "projection_digest": value["projection_digest"],
        }
    )
    extractor = ProjectedWKVExtractor(
        FakeWKVExtractor(),
        path,
        expected_model_hash=expected_model_hash,
        expected_projection_digest=value["projection_digest"],
        expected_projection_sha256=file_sha256(path),
    )

    features = extractor.extract(["first", "second"])

    assert extractor.feature_dim == 2
    assert features[0].values == pytest.approx((6.0, 8.0))
    assert features[1].values == pytest.approx((0.0, 1.0))
    assert [item.token_count for item in features] == [3, 5]
    assert all(item.model_hash == expected_model_hash for item in features)
    assert extractor.identity()["projection"]["fit_split"] == "train"


def test_projected_wkv_extractor_rejects_tensor_digest_drift(tmp_path: Path) -> None:
    value = projection_value()
    value["components"][0, 0] += 0.25
    path = tmp_path / "projection.pt"
    torch.save(value, path)

    with pytest.raises(RuntimeError, match="projection digest mismatch"):
        ProjectedWKVExtractor(
            FakeWKVExtractor(),
            path,
            expected_model_hash="irrelevant",
            expected_projection_digest=value["projection_digest"],
            expected_projection_sha256=file_sha256(path),
        )
