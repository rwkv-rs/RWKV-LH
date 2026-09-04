from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
)
from rwkv_lh.exact_tool_selector.model_v3 import (
    NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION,
    NETWORK_SELECTOR_SOFT_MOE_RAW_LOGIT_FORMULA,
    NetworkSelectorSoftMoEArtifact,
)
from rwkv_lh.exact_tool_selector.input_protocol import (
    DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.exact_tool_selector.network_service import (
    NetworkSelectorService,
    NetworkSelectorStateStore,
    TorchNetworkSelectorSoftMoEHead,
    load_torch_network_selector_head,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


def _write_json(path: Path, value: object) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _expert_value(*, winner: int, winning_bias: float) -> dict[str, object]:
    bias = [0.0] * len(NETWORK_EXACT_TOOL_LABELS)
    bias[winner] = winning_bias
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
        "head_weight": [[0.0, 0.0] for _ in NETWORK_EXACT_TOOL_LABELS],
        "head_bias": bias,
        "temperature": 1.0,
        "model_hash": "1" * 64,
        "metadata": {"fixture": True},
    }
    value["head_hash"] = canonical_digest(value)
    return value


def _bundle(tmp_path: Path) -> tuple[Path, str, dict[str, object]]:
    bundle = tmp_path / "bundle"
    old_value = _expert_value(winner=0, winning_bias=2.0)
    continuation_value = _expert_value(winner=1, winning_bias=4.0)
    old_path = bundle / "old.json"
    continuation_path = bundle / "continuation.json"
    old_sha = _write_json(old_path, old_value)
    continuation_sha = _write_json(continuation_path, continuation_value)
    value: dict[str, object] = {
        "schema_version": NETWORK_SELECTOR_SOFT_MOE_HEAD_SCHEMA_VERSION,
        "feature_dim": 2,
        "gate_hidden_dim": 2,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "feature_mean": [0.0, 0.0],
        "feature_std": [1.0, 1.0],
        "old_head": {
            "path": "old.json",
            "sha256": old_sha,
            "head_hash": old_value["head_hash"],
        },
        "continuation_head": {
            "path": "continuation.json",
            "sha256": continuation_sha,
            "head_hash": continuation_value["head_hash"],
        },
        "gate_shared_weight": [[0.0, 0.0], [0.0, 0.0]],
        "gate_shared_bias": [0.0, 0.0],
        "gate_layer_norm_weight": [1.0, 1.0],
        "gate_layer_norm_bias": [0.0, 0.0],
        "gate_head_weight": [[0.0, 0.0]],
        "gate_head_bias": [0.0],
        "temperature": 1.0,
        "raw_logit_formula": NETWORK_SELECTOR_SOFT_MOE_RAW_LOGIT_FORMULA,
        "model_hash": "2" * 64,
        "metadata": {"fixture": True},
    }
    value["head_hash"] = canonical_digest(value)
    head_path = bundle / "soft-moe.json"
    head_sha = _write_json(head_path, value)
    return head_path, head_sha, value


def test_soft_moe_preserves_architecture_raw_logits_and_torch_replay(
    tmp_path: Path,
) -> None:
    path, sha256, _ = _bundle(tmp_path)
    artifact = NetworkSelectorSoftMoEArtifact.load(path)
    torch_head = load_torch_network_selector_head(path, sha256)

    logits = artifact.raw_logits([3.0, -2.0])
    torch_logits = torch_head.raw_logits([3.0, -2.0])

    assert isinstance(torch_head, TorchNetworkSelectorSoftMoEHead)
    assert artifact.gate([3.0, -2.0]) == pytest.approx(0.5)
    assert logits[0] == pytest.approx(1.0)
    assert logits[1] == pytest.approx(2.0)
    assert artifact.select([3.0, -2.0]) == NETWORK_EXACT_TOOL_LABELS[1]
    assert max(abs(left - right) for left, right in zip(logits, torch_logits)) < 1e-6
    assert sum(artifact.probabilities([3.0, -2.0])) == pytest.approx(1.0)


def test_soft_moe_rejects_formula_change_even_with_recomputed_digest(
    tmp_path: Path,
) -> None:
    path, _, value = _bundle(tmp_path)
    value["raw_logit_formula"] = "continuation_logits"
    value.pop("head_hash")
    value["head_hash"] = canonical_digest(value)
    changed_sha = _write_json(path, value)

    with pytest.raises(ValueError, match="raw-logit formula changed"):
        load_torch_network_selector_head(path, changed_sha)


def test_soft_moe_rejects_referenced_expert_file_mutation(tmp_path: Path) -> None:
    path, _, value = _bundle(tmp_path)
    old = value["old_head"]
    assert isinstance(old, dict)
    old["sha256"] = "0" * 64
    value.pop("head_hash")
    value["head_hash"] = canonical_digest(value)
    changed_sha = _write_json(path, value)

    with pytest.raises(ValueError, match="old_head file SHA-256 mismatch"):
        load_torch_network_selector_head(path, changed_sha)


def test_soft_moe_service_accepts_exact_frozen_identity(tmp_path: Path) -> None:
    path, sha256, _ = _bundle(tmp_path)
    head = load_torch_network_selector_head(path, sha256)
    settings = NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="fixture-rwkv",
        model_sha256="3" * 64,
        head_sha256=sha256,
        head_hash=head.head_hash,
        feature_protocol=head.feature_protocol,
        state_profile_id="zero",
        state_profile_sha256="0" * 64,
        state_profile_manifest_sha256="4" * 64,
        input_protocol=DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL,
    )

    service = NetworkSelectorService(
        settings,
        object(),  # type: ignore[arg-type]
        head,
        NetworkSelectorStateStore(tmp_path / "state"),
    )

    assert service.head is head


def test_soft_moe_rejects_non_finite_features(tmp_path: Path) -> None:
    path, sha256, _ = _bundle(tmp_path)
    head = load_torch_network_selector_head(path, sha256)

    with pytest.raises(ValueError, match="non-finite"):
        head.raw_logits([float("nan"), 0.0])
