from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_model_command, parse_tool_selection
from scripts.generate_rwkv_action_state_tuning_round1_2k_v1 import (
    DEV_COUNTS,
    TRAIN_COUNTS,
    VERSION,
    validate_existing,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"


def rows(name: str) -> list[dict]:
    return [
        json.loads(line)
        for line in (DATASET / name).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_round1_2k_is_failure_grounded_and_training_ready() -> None:
    manifest = validate_existing()
    assert manifest["dataset_version"] == VERSION
    assert manifest["artifact_kind"] == "failure_grounded_controller_verified_action_state_tuning"
    assert manifest["training_ready"] is True
    assert manifest["remote_tokenizer_validated"] is True
    assert manifest["controller_replay"] is True
    assert manifest["strong_model_as_label_source"] is False
    assert manifest["live_network_used"] is False
    assert manifest["tool_disclosure_mode"] == "progressive"
    assert manifest["loss_mask"] == "target_suffix"
    assert manifest["training_file"] == "rwkv_state_tuning.train.requires_target_suffix.jsonl"
    assert manifest["counts"] == {
        "trajectories": 1321,
        "train_stage_sft": 2000,
        "dev_stage_sft": 200,
        "failure_signatures": 13,
        "train_semantic_families": 240,
        "dev_semantic_families": 25,
        "protocol_rejected_attempts": 440,
    }
    assert manifest["cluster_counts"] == {"train": TRAIN_COUNTS, "dev": DEV_COUNTS}
    assert manifest["validation"]["privacy_backend_execution_count"] == 0
    assert manifest["validation"]["contamination"]["maximum_holdout_similarity"] < 0.75


def test_round1_2k_targets_and_target_suffix_exports_are_exact() -> None:
    train = rows("stage_sft.train.jsonl")
    dev = rows("stage_sft.dev.jsonl")
    train_export = rows("rwkv_state_tuning.train.requires_target_suffix.jsonl")
    dev_export = rows("rwkv_state_tuning.dev.requires_target_suffix.jsonl")
    assert len(train) == len(train_export) == 2000
    assert len(dev) == len(dev_export) == 200
    assert Counter(row["failure_cluster"] for row in train) == TRAIN_COUNTS
    assert Counter(row["failure_cluster"] for row in dev) == DEV_COUNTS

    for stage, export in zip(train + dev, train_export + dev_export):
        assert export == {
            "prompt": stage["prompt"],
            "target": stage["target"],
            "text": stage["text"],
            "tier": 1,
        }
        assert stage["text"] == stage["prompt"] + stage["target"]
        assert stage["prompt"].endswith("Assistant: ```json\n")
        assert stage["training_intent"] == "next_state_transition_not_generic_task_sft"
        assert stage["state_cells"]
        assert "action-result-decision-state.v1" in stage["prompt"]
        assert '"event_type":"action_result"' not in stage["prompt"]
        if stage["stage"] == "selector":
            assert parse_tool_selection(stage["target"]) == stage["target_operation"]
        else:
            assert parse_model_command(stage["target"]).name == stage["target_operation"]


def test_round1_2k_remote_training_contract_is_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads(
        (DATASET / "remote_training_contract_validation.json").read_text(encoding="utf-8")
    )
    assert report["overall"]["rows"] == 2200
    assert report["overall"]["maximum_tokens"] == 2457
    assert report["overall"]["failure_count"] == 0
    assert report["target_suffix_audit"] == {
        "authoritative_mydataset_exercised": True,
        "rows": 2200,
        "total_supervised_tokens": 53342,
        "expected_target_tokens": 53342,
        "historical_assistant_tokens_supervised": 0,
        "exact_label_match_rate": 1.0,
    }
    assert manifest["validation"]["remote_training_contract"] == report
    assert manifest["validation"]["remote_training_contract_report_sha256"] == sha256(
        DATASET / "remote_training_contract_validation.json"
    )
    assert manifest["remote"]["source_sha256"] == report["source_sha256"]


def test_round1_2k_manifest_hashes_cover_every_dataset_artifact() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    actual = {
        str(path.relative_to(DATASET))
        for path in DATASET.rglob("*")
        if path.is_file() and path.name != "manifest.json"
    }
    assert set(manifest["files"]) == actual
    for relative, metadata in manifest["files"].items():
        path = DATASET / relative
        assert sha256(path) == metadata["sha256"]
        assert path.stat().st_size == metadata["bytes"]
