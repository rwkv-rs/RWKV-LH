from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_model_command, parse_tool_selection
from scripts.generate_rwkv_action_state_tuning_v1 import (
    VERSION,
    _contamination,
    validate_existing,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_action_state_tuning_v1"


def _rows(name: str):
    with (DATASET / name).open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_action_state_tuning_v1_is_training_ready_and_replay_verified() -> None:
    manifest = validate_existing()
    assert manifest["dataset_version"] == VERSION
    assert manifest["training_ready"] is True
    assert manifest["candidate_generation"] == "deterministic_private_oracle_bootstrap"
    assert manifest["strong_model_as_label_source"] is False
    assert manifest["controller_replay"] is True
    assert manifest["live_network_used"] is False
    assert manifest["counts"] == {
        "trajectories": 480,
        "train_trajectories": 400,
        "dev_trajectories": 80,
        "stage_sft": 1464,
        "train_stage_sft": 1220,
        "dev_stage_sft": 244,
        "seeds": 20,
        "semantic_families": 120,
        "rejected_attempts": 24,
    }
    validation = manifest["validation"]
    assert validation["accepted_trajectories"] == 480
    assert validation["rejected_trajectories"] == 0
    assert validation["positive_stage_parse_rate"] == 1.0
    assert validation["literal_binding_rate"] == 1.0
    assert validation["controller_replay_rate"] == 1.0
    assert validation["privacy_backend_execution_count"] == 0


def test_action_state_tuning_v1_split_and_oracle_isolation() -> None:
    candidates = list(_rows("semantic_candidates.jsonl"))
    oracles = list(_rows("private/oracle_trajectories.jsonl"))
    validations = list(_rows("validation.jsonl"))
    rejected = list(_rows("rejected_attempts.jsonl"))
    assert len(candidates) == len(oracles) == len(validations) == 480
    assert len(rejected) == 24
    assert all(row["accepted"] for row in validations)
    assert all(row["positive_use"] is False for row in rejected)
    assert all("prelude" not in row for row in candidates)
    assert all("expected_backend_executions" not in row for row in candidates)

    seed_counts = Counter(row["source_seed_id"] for row in candidates)
    family_counts = Counter(row["semantic_family_id"] for row in candidates)
    assert set(seed_counts) == {f"ST-ACT-{index:03d}" for index in range(1, 21)}
    assert set(seed_counts.values()) == {24}
    assert len(family_counts) == 120
    assert set(family_counts.values()) == {4}
    train_families = {
        row["semantic_family_id"] for row in candidates if row["split"] == "train"
    }
    dev_families = {
        row["semantic_family_id"] for row in candidates if row["split"] == "dev"
    }
    assert len(train_families) == 100
    assert len(dev_families) == 20
    assert train_families.isdisjoint(dev_families)
    assert Counter(row["language"] for row in candidates) == {"zh": 240, "en": 240}


def test_action_state_tuning_v1_targets_are_exact_progressive_generations() -> None:
    train = list(_rows("stage_sft.train.jsonl"))
    dev = list(_rows("stage_sft.dev.jsonl"))
    stages = train + dev
    assert len(train) == 1220
    assert len(dev) == 244
    assert len(stages) == 1464
    assert all(row["controller_rendered"] is True for row in stages)
    assert all(row["prompt"].endswith("Assistant: ```json\n") for row in stages)
    assert all(row["text"] == row["prompt"] + row["target"] for row in stages)
    assert all(
        row["prompt_sha256"]
        == hashlib.sha256(row["prompt"].encode("utf-8")).hexdigest()
        for row in stages
    )
    assert all(
        row["target_sha256"]
        == hashlib.sha256(row["target"].encode("utf-8")).hexdigest()
        for row in stages
    )
    for row in stages:
        if row["stage"] == "selector":
            assert parse_tool_selection(row["target"]) == row["target_operation"]
            assert '"selected_tool_contract"' not in row["prompt"].rsplit(
                "Assistant: ```json\n", 1
            )[-1]
        else:
            assert parse_model_command(row["target"]).name == row["target_operation"]
            assert '"selected_operation"' in row["prompt"]

    correction = [row for row in stages if row["source_seed_id"] == "ST-ACT-016"]
    assert len(correction) == 24
    assert {row["stage"] for row in correction} == {"direct"}
    assert all(row["target_operation"] == "read_file" for row in correction)
    assert all("protocol_rejection" in row["prompt"] for row in correction)


def test_action_state_tuning_v1_contamination_metrics_recompute() -> None:
    candidates = list(_rows("semantic_candidates.jsonl"))
    computed = _contamination(candidates)
    recorded = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))[
        "validation"
    ]["contamination"]
    assert computed == recorded
    assert computed["holdout_request_count"] == 210
    assert computed["exact_holdout_overlap_count"] == 0
    assert computed["internal_exact_request_duplicate_count"] == 0
    assert computed["maximum_holdout_similarity"] < 0.75
    assert computed["maximum_cross_semantic_family_similarity"] < 0.75


def test_action_state_tuning_v1_manifest_hashes_cover_training_artifacts() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    expected = {
        "README.md",
        "semantic_candidates.jsonl",
        "private/oracle_trajectories.jsonl",
        "validation.jsonl",
        "rejected_attempts.jsonl",
        "stage_sft.train.jsonl",
        "stage_sft.dev.jsonl",
        "rwkv_state_tuning.train.jsonl",
        "rwkv_state_tuning.dev.jsonl",
        "scripts/generate_rwkv_action_state_tuning_v1.py",
    }
    assert set(manifest["files"]) == expected
    for relative, metadata in manifest["files"].items():
        path = ROOT / relative if relative.startswith("scripts/") else DATASET / relative
        assert _sha256(path) == metadata["sha256"]
        assert path.stat().st_size == metadata["bytes"]
