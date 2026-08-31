from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rwkv_lh.model_io import (
    parse_model_command,
    validate_final_answer,
    validate_independent_executor_generation_input,
)
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    build_product_harness,
)
from rwkv_lh.schema import TaskAction
from scripts.generate_executor_network_recovery_g6_2k import (
    byte_ngrams,
    cosine,
    extract_requirement,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k"
HOLDOUTS = (
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


def test_g6_manifest_and_all_frozen_files_are_content_addressed() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "rwkv-lh.executor-dataset-manifest.g6.v1"
    assert manifest["counts"] == {"train": 2000, "dev": 480}
    assert manifest["source_counts"] == {
        "train": {
            "clean_network_stage": 400,
            "g4_frozen_direct_retention": 400,
            "g4_frozen_workflow_retention": 800,
            "protocol_rejection_recovery": 400,
        },
        "dev": {
            "clean_network_stage": 72,
            "g4_frozen_direct_retention": 96,
            "g4_frozen_workflow_retention": 240,
            "protocol_rejection_recovery": 72,
        },
    }
    for name, contract in manifest["files"].items():
        path = DATASET / name
        assert path.is_file()
        assert path.stat().st_size == contract["bytes"]
        assert len(_rows(path)) == contract["rows"]
        assert _sha256(path) == contract["sha256"]


def test_g6_all_prompts_targets_and_harness_contracts_are_valid(tmp_path: Path) -> None:
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )
    rows_by_split = {
        split: _rows(DATASET / f"stage_sft.{split}.jsonl")
        for split in ("train", "dev")
    }
    assert not (
        {row["source_family_id"] for row in rows_by_split["train"]}
        & {row["source_family_id"] for row in rows_by_split["dev"]}
    )
    all_rows = rows_by_split["train"] + rows_by_split["dev"]
    assert len({row["prompt_sha256"] for row in all_rows}) == len(all_rows)
    for row in all_rows:
        prompt = str(row["prompt"])
        target = str(row["target"])
        request = str(row.get("request") or extract_requirement(prompt))
        assert row["text"] == prompt + target
        assert hashlib.sha256(prompt.encode()).hexdigest() == row["prompt_sha256"]
        assert hashlib.sha256(target.encode()).hexdigest() == row["target_sha256"]
        assert row["generated_rwkv_text"] is False
        assert row["raw_output_modified"] is False
        validate_independent_executor_generation_input(prompt, request)
        command = parse_model_command(target)
        assert command.name == row["selected_operation"]
        assert command.name != "select_tool"
        if command.name == "final_answer":
            validate_final_answer(command)
        else:
            harness.validate_action_contract(TaskAction(command.name, command.arguments))
        if row["source_kind"] == "protocol_rejection_recovery":
            assert '"event_type":"protocol_rejection"' in prompt
            assert row["retry_question_last"] is True
            assert row["action_executed_before_rejection"] is False


def test_g6_visible_requests_remain_below_frozen_holdout_similarity_threshold() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    holdout_rows = [row for path in HOLDOUTS for row in _rows(path)]
    references = [
        (str(row["case_id"]), byte_ngrams(str(row["request"])))
        for row in holdout_rows
    ]
    maximum = (-1.0, "", "")
    for split in ("train", "dev"):
        for row in _rows(DATASET / f"stage_sft.{split}.jsonl"):
            if row["source_kind"] not in {
                "clean_network_stage",
                "protocol_rejection_recovery",
            }:
                continue
            grams = byte_ngrams(str(row["request"]))
            for holdout_id, reference in references:
                score = cosine(grams, reference)
                if score > maximum[0]:
                    maximum = (score, str(row["sample_id"]), holdout_id)
    frozen = manifest["validation"]["maximum_visible_holdout_byte_5gram_cosine"]
    assert maximum == (frozen["score"], frozen["sample_id"], frozen["holdout_id"])
    assert maximum[0] < manifest["validation"]["similarity_threshold_exclusive"]
