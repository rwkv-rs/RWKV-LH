from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage8_mutation_stop_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage8_manifest_and_controller_replay_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == (
        "rwkv-lh.state-tuning.stage8-mutation-stop.v1"
    )
    assert manifest["strong_model_as_label_source"] is False
    assert manifest["controller_replay"] is True
    assert manifest["counts"]["train"] == 2000
    assert manifest["counts"]["dev"] == 400
    assert manifest["counts"]["factory_surface_families"] == 500
    assert manifest["counts"]["contrast_groups"] == 500
    assert manifest["counts"]["controller_replayed_trajectories"] == 2000
    validation = manifest["validation"]
    assert validation["controller_replay_rate"] == 1.0
    assert validation["target_parse_rate"] == 1.0
    assert validation["exact_stage_duplicate_count"] == 0
    assert validation["train_dev_family_overlap_count"] == 0
    assert validation["contamination"]["exact_holdout_overlap_count"] == 0
    assert validation["contamination"]["maximum_holdout_similarity"] < 0.75
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage8_targets_are_selector_only_and_family_disjoint() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    train_export = read_jsonl(
        DATA / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
    )
    dev_export = read_jsonl(
        DATA / "rwkv_state_tuning.dev.requires_target_suffix.jsonl"
    )
    assert len(train) == len(train_export) == 2000
    assert len(dev) == len(dev_export) == 400
    for row, exported in zip(train + dev, train_export + dev_export, strict=True):
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
        assert exported == {
            "prompt": row["prompt"],
            "target": row["target"],
            "text": row["text"],
        }
    assert len({row["text"] for row in train + dev}) == 2400
    assert not {
        row["semantic_family_id"] for row in train
    }.intersection(row["semantic_family_id"] for row in dev)


def test_stage8_four_state_contrasts_match_failure_contract() -> None:
    rows = read_jsonl(DATA / "stage_sft.train.jsonl") + read_jsonl(
        DATA / "stage_sft.dev.jsonl"
    )
    contrasts = [
        row for row in rows if row["failure_cluster"] != "stage7_safety_anchor"
    ]
    grouped: dict[str, list[dict]] = {}
    for row in contrasts:
        grouped.setdefault(row["contrast_group"], []).append(row)
    assert len(grouped) == 500
    assert {len(group) for group in grouped.values()} == {4}
    expected = {
        "mutation_success_stop": Counter(
            {"write_json": 2, "final_answer": 2}
        ),
        "investigate_scope_stop": Counter(
            {"read_file": 2, "final_answer": 2}
        ),
        "verify_evidence_stop": Counter(
            {"read_json": 3, "final_answer": 1}
        ),
        "idempotent_repeat_stop": Counter(
            {"write_file": 2, "final_answer": 2}
        ),
    }
    for group in grouped.values():
        cluster = group[0]["failure_cluster"]
        assert {row["failure_cluster"] for row in group} == {cluster}
        assert Counter(row["target_operation"] for row in group) == expected[cluster]
        assert len({row["state_lane"] for row in group}) == 4

    validations = read_jsonl(DATA / "controller_replay_validation.jsonl")
    assert len(validations) == 2000
    assert all(row["accepted"] for row in validations)
    assert all(row["controller_replay_verified"] for row in validations)
    repeated = [
        row
        for row in validations
        if row["state_lane"] in {"after-identical-repeat", "identical-count-two"}
    ]
    assert len(repeated) == 250
    assert all(row["action_count"] == 3 for row in repeated)
