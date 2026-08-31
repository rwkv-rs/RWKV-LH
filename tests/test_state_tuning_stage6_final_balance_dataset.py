from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage6_final_balance_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage6_manifest_counts_digests_and_contamination() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == "rwkv-lh.state-tuning.stage6-final-balance.v1"
    assert manifest["counts"]["train"] == 1300
    assert manifest["counts"]["dev"] == 240
    assert manifest["counts"]["train_clusters"] == {
        "stable_selector_replay": 500,
        "connector_boundary": 120,
        "ordinary_web_boundary": 200,
        "local_safety_boundary": 160,
        "mixed_local_first_boundary": 160,
        "privacy_local_first_boundary": 80,
        "completion_after_success": 80,
    }
    assert manifest["contamination"]["exact_holdout_overlap_count"] == 0
    assert manifest["contamination"]["maximum_holdout_similarity"] < 0.75
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage6_selector_contract_and_family_isolation() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert len(train) == 1300
    assert len(dev) == 240
    for row in train + dev:
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["prompt_sha256"] for row in train + dev}) == 1540
    assert not {row["semantic_family_id"] for row in train}.intersection(
        row["semantic_family_id"] for row in dev
    )


def test_stage6_completion_weight_and_boundary_targets() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    completion = [row for row in train if row["failure_cluster"] == "completion_after_success"]
    assert len(completion) == 80
    assert Counter(row["target_operation"] for row in completion) == {"final_answer": 80}
    assert all(int(row["turn_index"]) >= 1 and "action_result" in row["prompt"] for row in completion)
    pre_evidence = [
        row
        for row in train
        if row["failure_cluster"]
        not in {"stable_selector_replay", "completion_after_success"}
    ]
    assert all(int(row["turn_index"]) == 0 for row in pre_evidence)


def test_stage6_preserves_complete_stage1_and_stage4_boundary_anchors() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    stage1 = read_jsonl(ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.train.jsonl")
    stage4 = [
        row
        for row in read_jsonl(ROOT / "data/datasets/rwkv_lh_state_tuning_stage4_balanced_boundary_v1/stage_sft.train.jsonl")
        if row["failure_cluster"] != "stable_selector_replay"
    ]
    stable = [row for row in train if row["failure_cluster"] == "stable_selector_replay"]
    boundary = [row for row in train if row["training_intent"] == "retain_complete_stage4_balanced_boundary_anchor"]
    assert {row["prompt_sha256"] for row in stable} == {row["prompt_sha256"] for row in stage1}
    assert {row["prompt_sha256"] for row in boundary} == {row["prompt_sha256"] for row in stage4}
