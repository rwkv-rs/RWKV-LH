from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ROUND2 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_adaptive_round2_v1"
ROUND3 = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_adaptive_round3_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_round2_adaptive_curriculum_is_trace_selected_and_training_ready() -> None:
    manifest = json.loads((ROUND2 / "manifest.json").read_text())
    assert manifest["training_ready"] is True
    assert manifest["remote_tokenizer_validated"] is True
    assert manifest["strong_model_as_label_source"] is False
    assert manifest["counts"] == {
        "train": 1800,
        "dev": 400,
        "residual_rows": 600,
        "matched_contrast_rows": 400,
        "safety_anchor_rows": 800,
        "train_clusters": manifest["counts"]["train_clusters"],
    }
    selection = manifest["selection"]
    assert selection["no_oversampling"] is True
    assert selection["exact_stage_duplicate_count"] == 0
    assert selection["train_dev_family_overlap_count"] == 0
    assert "mutation_success_stop/changed-required-value" in selection["weak_lanes"]
    for relative, metadata in manifest["files"].items():
        path = ROUND2 / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_round2_mixed_targets_are_single_commands_and_family_disjoint() -> None:
    train = read_jsonl(ROUND2 / "stage_sft.train.jsonl")
    dev = read_jsonl(ROUND2 / "stage_sft.dev.jsonl")
    functions = set()
    for row in [*train, *dev]:
        assert row["text"] == row["prompt"] + row["target"]
        command = json.loads(row["target"])
        assert isinstance(command["function"], str) and command["function"]
        assert isinstance(command["params"], dict)
        functions.add(command["function"])
    assert "select_tool" in functions
    assert "read_json" in functions
    assert "final_answer" in functions
    assert not {row["semantic_family_id"] for row in train}.intersection(
        row["semantic_family_id"] for row in dev
    )


def test_round3_is_selector_only_and_excludes_direct_tool_anchors() -> None:
    manifest = json.loads((ROUND3 / "manifest.json").read_text())
    assert manifest["training_ready"] is True
    assert manifest["remote_tokenizer_validated"] is True
    assert manifest["counts"]["train"] == 1700
    assert manifest["counts"]["dev"] == 400
    assert manifest["counts"]["residual_rows"] == 800
    assert manifest["counts"]["matched_contrast_rows"] == 500
    assert manifest["counts"]["safety_anchor_rows"] == 400
    assert manifest["selection"]["anchor_sources"] == ["stage7"]
    assert manifest["source"]["round1_manifest_sha256"] == ""
    train = read_jsonl(ROUND3 / "stage_sft.train.jsonl")
    dev = read_jsonl(ROUND3 / "stage_sft.dev.jsonl")
    assert {
        json.loads(row["target"])["function"] for row in [*train, *dev]
    } == {"select_tool"}
    assert len({row["text"] for row in [*train, *dev]}) == 2100
    assert not {row["semantic_family_id"] for row in train}.intersection(
        row["semantic_family_id"] for row in dev
    )
    for relative, metadata in manifest["files"].items():
        path = ROUND3 / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]
