from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage5_route_stop_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage5_manifest_counts_digests_and_contamination() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == "rwkv-lh.state-tuning.stage5-route-stop.v1"
    assert manifest["counts"]["train"] == 1220
    assert manifest["counts"]["dev"] == 240
    assert manifest["counts"]["train_clusters"] == {
        "stable_selector_replay": 500,
        "connector_anchor": 80,
        "github_connector_residual": 40,
        "ordinary_web_counterfactual": 160,
        "local_safety_anchor": 80,
        "mixed_local_first_anchor": 80,
        "privacy_local_first_anchor": 40,
        "completion_after_success": 240,
    }
    assert manifest["contamination"]["exact_holdout_overlap_count"] == 0
    assert manifest["contamination"]["maximum_holdout_similarity"] < 0.75
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage5_selector_contract_and_family_isolation() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert len(train) == 1220
    assert len(dev) == 240
    for row in train + dev:
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["prompt_sha256"] for row in train + dev}) == 1460
    assert not {row["semantic_family_id"] for row in train}.intersection(
        row["semantic_family_id"] for row in dev
    )


def test_stage5_completion_rows_are_post_observation_final_selectors() -> None:
    rows = [
        row
        for row in read_jsonl(DATA / "stage_sft.train.jsonl")
        if row["failure_cluster"] == "completion_after_success"
    ]
    assert len(rows) == 240
    assert Counter(row["target_operation"] for row in rows) == {"final_answer": 240}
    assert all(int(row["turn_index"]) >= 1 for row in rows)
    assert all("action_result" in row["prompt"] for row in rows)


def test_stage5_replays_complete_stage1_anchor_without_dev_leakage() -> None:
    source_train = read_jsonl(
        ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.train.jsonl"
    )
    source_dev = read_jsonl(
        ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.dev.jsonl"
    )
    stable = [
        row
        for row in read_jsonl(DATA / "stage_sft.train.jsonl")
        if row["failure_cluster"] == "stable_selector_replay"
    ]
    assert {row["prompt_sha256"] for row in stable} == {
        row["prompt_sha256"] for row in source_train
    }
    assert not {row["prompt_sha256"] for row in stable}.intersection(
        row["prompt_sha256"] for row in source_dev
    )
