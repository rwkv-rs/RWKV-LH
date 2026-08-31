from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage7_factory_contrast_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage7_manifest_counts_digests_and_contamination_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == (
        "rwkv-lh.state-tuning.stage7-factory-contrast.v1"
    )
    assert manifest["strong_model_as_label_source"] is False
    assert manifest["local_validation_complete"] is True
    assert manifest["counts"] == {
        "train": 2000,
        "dev": 400,
        "factory_surface_families": 500,
        "contrast_groups": 500,
        "train_clusters": {
            "phase_evidence_contrast": 400,
            "web_connector_role_contrast": 400,
            "mixed_privacy_local_first": 400,
            "no_progress_success_stop": 400,
            "stage1_safety_anchor": 400,
        },
        "dev_clusters": {
            "phase_evidence_contrast": 100,
            "web_connector_role_contrast": 100,
            "mixed_privacy_local_first": 100,
            "no_progress_success_stop": 100,
        },
        "train_semantic_families": 500,
        "dev_semantic_families": 100,
    }
    validation = manifest["validation"]
    assert validation["controller_replay_rate"] == 1.0
    assert validation["target_parse_rate"] == 1.0
    assert validation["privacy_backend_execution_count"] == 0
    assert validation["exact_stage_duplicate_count"] == 0
    assert validation["train_dev_family_overlap_count"] == 0
    contamination = validation["contamination"]
    assert contamination["similarity_version"] == "utf8-byte-ngram-cosine.v1"
    assert contamination["exact_holdout_overlap_count"] == 0
    assert contamination["maximum_holdout_similarity"] < 0.75
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage7_is_selector_only_target_suffix_and_family_isolated() -> None:
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
        assert exported == {
            "prompt": row["prompt"],
            "target": row["target"],
            "text": row["text"],
        }
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["text"] for row in train + dev}) == 2400
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    assert not train_families.intersection(dev_families)


def test_stage7_contrast_groups_and_replays_preserve_registered_semantics() -> None:
    rows = read_jsonl(DATA / "stage_sft.train.jsonl") + read_jsonl(
        DATA / "stage_sft.dev.jsonl"
    )
    contrast = [
        row for row in rows if row["failure_cluster"] != "stage1_safety_anchor"
    ]
    group_counts = Counter(row["contrast_group"] for row in contrast)
    assert len(group_counts) == 500
    assert set(group_counts.values()) == {4}
    expected_operations = {
        "phase_evidence_contrast": {"read_file": 2, "final_answer": 2},
        "web_connector_role_contrast": {"web_search": 2, "connector_lookup": 2},
        "mixed_privacy_local_first": {"read_file": 2, "web_search": 2},
    }
    grouped: dict[str, list[dict]] = {}
    for row in contrast:
        grouped.setdefault(row["contrast_group"], []).append(row)
    for group in grouped.values():
        cluster = group[0]["failure_cluster"]
        assert {row["failure_cluster"] for row in group} == {cluster}
        operations = Counter(row["target_operation"] for row in group)
        if cluster == "no_progress_success_stop":
            assert operations["read_file"] == 1
            assert operations["final_answer"] == 2
            assert operations["web_search"] + operations["connector_lookup"] == 1
        else:
            assert operations == expected_operations[cluster]

    validations = read_jsonl(DATA / "controller_replay_validation.jsonl")
    assert len(validations) == 1375
    assert all(row["accepted"] and row["controller_replay_verified"] for row in validations)
    assert all(row["literal_bindings_verified"] for row in validations)
    privacy = [row for row in validations if "privacy" in row["trajectory_id"]]
    assert len(privacy) == 125
    assert sum(row["backend_execution_count"] for row in privacy) == 0
