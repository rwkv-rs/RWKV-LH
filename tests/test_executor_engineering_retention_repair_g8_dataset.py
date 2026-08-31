from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_model_command, validate_final_answer
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    build_product_harness,
)
from rwkv_lh.schema import TaskAction
from scripts.generate_executor_engineering_retention_repair_g8_2k import (
    byte_ngrams,
    cosine,
    current_requirement,
)


ROOT = Path(__file__).resolve().parents[1]
TRAIN = ROOT / "data/datasets/rwkv_lh_executor_engineering_retention_repair_g8_2k"
HOLDOUT = ROOT / "data/datasets/rwkv_lh_executor_engineering_retention_g8_holdout_v1"
FROZEN_EVALS = (
    ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2/stage_sft.dev.eval.jsonl",
    ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl",
)
LIVE_CASES = (
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl",
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v2/cases.jsonl",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_g8_manifests_files_and_preregistered_distributions_are_frozen() -> None:
    train_manifest = json.loads((TRAIN / "manifest.json").read_text(encoding="utf-8"))
    holdout_manifest = json.loads((HOLDOUT / "manifest.json").read_text(encoding="utf-8"))
    assert train_manifest["schema_version"] == "rwkv-lh.executor-dataset-manifest.g8.v1"
    assert train_manifest["counts"] == {"train": 2000}
    assert train_manifest["source_counts"] == {
        "balanced_direct_replay": 240,
        "direct_web_query_critical_replay": 5,
        "fresh_broad_full_workflow": 240,
        "fresh_critical_position_supervision": 155,
        "fresh_targeted_full_workflow": 1200,
        "network_clean_replay": 80,
        "network_protocol_recovery_replay": 80,
    }
    assert train_manifest["training_contract"] == {
        "ctx_len": 2496,
        "jsonl_bos_token_id": 0,
        "loss_mask": "target_suffix",
        "lr_final": "2e-7",
        "lr_init": "2e-6",
        "parent_training_state_sha256": "648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78",
        "parent_vllm_state_sha256": "611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b",
        "physical_gpu": 0,
        "save_steps": [250, 500, 750, 1000, 1250, 1500, 1750, 2000],
        "seed": 1079,
        "steps": 2000,
    }
    assert holdout_manifest["schema_version"] == "rwkv-lh.executor-eval-manifest.g8-holdout.v1"
    assert holdout_manifest["counts"] == {"holdout": 240}
    assert holdout_manifest["family_counts"] == {
        "connector_record_bundle": 48,
        "discount_ledger_release": 48,
        "failed_check_dual_output_recovery": 48,
        "implementation_bundle": 48,
        "public_evidence_bundle": 48,
    }
    assert holdout_manifest["validation"]["holdout_entered_state_tuning"] is False
    for root, manifest in ((TRAIN, train_manifest), (HOLDOUT, holdout_manifest)):
        for name, contract in manifest["files"].items():
            path = root / name
            assert path.is_file()
            assert path.stat().st_size == contract["bytes"]
            assert len(_rows(path)) == contract["rows"]
            assert _sha256(path) == contract["sha256"]


def test_g8_train_and_holdout_are_unique_and_source_disjoint() -> None:
    train = _rows(TRAIN / "stage_sft.train.jsonl")
    holdout = _rows(HOLDOUT / "stage_sft.holdout.eval.jsonl")
    all_rows = train + holdout
    assert len(train) == 2000
    assert len(holdout) == 240
    assert len({str(row["sample_id"]) for row in all_rows}) == 2240
    assert len({str(row["prompt_sha256"]) for row in all_rows}) == 2240
    assert {str(row["source_sample_id"]) for row in train}.isdisjoint(
        {str(row["source_sample_id"]) for row in holdout}
    )
    frozen_eval_ids: set[str] = set()
    for path in FROZEN_EVALS:
        for row in _rows(path):
            frozen_eval_ids.add(str(row["sample_id"]))
            if row.get("source_sample_id"):
                frozen_eval_ids.add(str(row["source_sample_id"]))
    assert {str(row["source_sample_id"]) for row in train}.isdisjoint(frozen_eval_ids)
    for row in all_rows:
        assert row["text"] == str(row["prompt"]) + str(row["target"])
        assert row["prompt_sha256"] == hashlib.sha256(str(row["prompt"]).encode()).hexdigest()
        assert row["target_sha256"] == hashlib.sha256(str(row["target"]).encode()).hexdigest()
        assert row["source_prompt_sha256"] == row["prompt_sha256"]
        assert row["source_target_sha256"] == row["target_sha256"]
        assert row["generated_rwkv_text"] is False
        assert row["raw_output_modified"] is False


def test_g8_holdout_metadata_projection_only_adds_language() -> None:
    source = _rows(HOLDOUT / "stage_sft.holdout.eval.jsonl")
    projected = _rows(HOLDOUT / "stage_sft.holdout.eval.metadata_v2.jsonl")
    manifest = json.loads(
        (HOLDOUT / "metadata_v2_manifest.json").read_text(encoding="utf-8")
    )
    assert manifest["status"] == "valid"
    assert manifest["rows"] == 240
    assert manifest["only_added_field"] == "language"
    assert manifest["language_counts"] == {"en": 240, "zh": 0}
    assert manifest["projection"]["sha256"] == _sha256(
        HOLDOUT / "stage_sft.holdout.eval.metadata_v2.jsonl"
    )
    for original, value in zip(source, projected, strict=True):
        copied = dict(value)
        assert copied.pop("language") == "en"
        assert copied == original


def test_g8_critical_positions_and_complete_trajectory_counts_are_exact() -> None:
    rows = _rows(TRAIN / "stage_sft.train.jsonl")
    critical = [
        row for row in rows if row["source_kind"] == "fresh_critical_position_supervision"
    ]
    assert Counter(str(row["selection_rule"]) for row in critical) == Counter(
        {
            "recovery_write_json_60": 60,
            "discount_write_json_30": 30,
            "discount_write_file_20": 20,
            "discount_final_answer_15": 15,
            "recovery_final_answer_15": 15,
            "discount_verifier_read_file_10": 10,
            "discount_read_json_5": 5,
        }
    )
    assert Counter(str(row["selected_operation"]) for row in critical) == Counter(
        {"write_json": 90, "write_file": 20, "final_answer": 30, "read_file": 10, "read_json": 5}
    )
    full = [row for row in rows if str(row["source_kind"]).startswith("fresh_") and "full_workflow" in str(row["source_kind"])]
    trajectories = Counter(str(row["trajectory_id"]) for row in full)
    assert len(trajectories) == 180
    assert set(trajectories.values()) == {8}


def test_g8_all_prompts_targets_and_harness_contracts_are_valid(tmp_path: Path) -> None:
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )
    for path in (
        TRAIN / "stage_sft.train.jsonl",
        HOLDOUT / "stage_sft.holdout.eval.jsonl",
    ):
        for row in _rows(path):
            prompt = str(row["prompt"])
            target = str(row["target"])
            assert current_requirement(prompt)
            command = parse_model_command(target)
            assert command.name == row["selected_operation"]
            assert command.name != "select_tool"
            if command.name == "final_answer":
                validate_final_answer(command)
            else:
                harness.validate_action_contract(TaskAction(command.name, command.arguments))


def test_g8_live_requests_use_the_frozen_similarity_metric() -> None:
    manifest = json.loads((TRAIN / "manifest.json").read_text(encoding="utf-8"))
    references = [
        (str(row["case_id"]), byte_ngrams(str(row["request"])))
        for path in LIVE_CASES
        for row in _rows(path)
    ]
    maximum = (-1.0, "", "")
    for row in _rows(TRAIN / "stage_sft.train.jsonl"):
        grams = byte_ngrams(current_requirement(str(row["prompt"])))
        for holdout_id, reference in references:
            score = cosine(grams, reference)
            if score > maximum[0]:
                maximum = (score, str(row["sample_id"]), holdout_id)
    frozen = manifest["validation"]["maximum_live_holdout_byte_5gram_cosine"]
    assert maximum == (frozen["score"], frozen["sample_id"], frozen["holdout_id"])
    assert maximum[0] < manifest["validation"]["similarity_threshold_exclusive"]
