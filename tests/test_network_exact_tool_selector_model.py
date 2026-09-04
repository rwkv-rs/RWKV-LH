from __future__ import annotations

import pytest

from rwkv_lh.exact_tool_selector.head import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.model_io import canonical_digest


def _artifact_value() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
        "feature_dim": 2,
        "hidden_dim": 2,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "feature_mean": [0.0, 0.0],
        "feature_std": [1.0, 1.0],
        "shared_weight": [[1.0, 0.0], [0.0, 1.0]],
        "shared_bias": [0.0, 0.0],
        "layer_norm_weight": [1.0, 1.0],
        "layer_norm_bias": [0.0, 0.0],
        "head_weight": [[float(index), -float(index)] for index in range(25)],
        "head_bias": [0.0] * 25,
        "temperature": 0.8,
        "model_hash": "1" * 64,
        "metadata": {"fixture": True},
    }
    value["head_hash"] = canonical_digest(value)
    return value


def test_network_selector_mlp_preserves_all_raw_logits_and_argmax() -> None:
    artifact = NetworkSelectorMLPArtifact.from_dict(_artifact_value())

    logits = artifact.raw_logits([2.0, -1.0])

    assert len(logits) == 25
    assert artifact.select([2.0, -1.0]) == NETWORK_EXACT_TOOL_LABELS[-1]
    assert sum(artifact.probabilities([2.0, -1.0])) == pytest.approx(1.0)


def test_network_selector_mlp_rejects_artifact_mutation() -> None:
    value = _artifact_value()
    value["temperature"] = 1.2

    with pytest.raises(ValueError, match="digest mismatch"):
        NetworkSelectorMLPArtifact.from_dict(value)


def test_network_selector_mlp_registers_same_forward_fusion_protocol() -> None:
    value = _artifact_value()
    value["feature_protocol"] = NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL
    value["head_hash"] = canonical_digest(
        {key: item for key, item in value.items() if key != "head_hash"}
    )

    artifact = NetworkSelectorMLPArtifact.from_dict(value)

    assert artifact.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL
