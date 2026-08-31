from __future__ import annotations

import hashlib
import json
from collections import Counter
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
from scripts.generate_executor_network_retention_repair_g7_1200 import (
    byte_ngrams,
    cosine,
    current_requirement,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_executor_network_retention_repair_g7_1200"
G4 = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k"
G6 = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k"
EVALS = (
    ROOT
    / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2/stage_sft.dev.eval.jsonl",
    ROOT
    / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl",
)
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


def test_g7_manifest_files_and_preregistered_distribution_are_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["schema_version"] == "rwkv-lh.executor-dataset-manifest.g7.v1"
    assert manifest["counts"] == {"train": 1200}
    assert manifest["source_counts"] == {
        "g4_all_workflow_rehearsal": 800,
        "g4_balanced_direct_rehearsal": 240,
        "g6_clean_network_rehearsal": 80,
        "g6_protocol_recovery_rehearsal": 80,
    }
    assert manifest["network_replay_operation_counts"] == {
        "clean": {
            "web_search": 8,
            "connector_lookup": 8,
            "write_file": 20,
            "write_json": 20,
            "read_file": 6,
            "read_json": 6,
            "bind_evidence": 4,
            "file_digest": 4,
            "final_answer": 4,
        },
        "protocol_recovery": {
            "write_file": 24,
            "write_json": 20,
            "read_file": 6,
            "read_json": 6,
            "append_file": 4,
            "copy_file": 4,
            "move_file": 4,
            "file_digest": 4,
            "web_search": 2,
            "connector_lookup": 2,
            "bind_evidence": 2,
            "final_answer": 2,
        },
    }
    for name, contract in manifest["files"].items():
        path = DATASET / name
        assert path.is_file()
        assert path.stat().st_size == contract["bytes"]
        assert len(_rows(path)) == contract["rows"] == 1200
        assert _sha256(path) == contract["sha256"]


def test_g7_replay_preserves_source_bytes_and_has_no_eval_source_overlap() -> None:
    rows = _rows(DATASET / "stage_sft.train.jsonl")
    sources = {
        "g4_train": {
            str(row["sample_id"]): row
            for row in _rows(G4 / "stage_sft.train.jsonl")
        },
        "g6_train": {
            str(row["sample_id"]): row
            for row in _rows(G6 / "stage_sft.train.jsonl")
        },
    }
    assert len({row["sample_id"] for row in rows}) == 1200
    assert len({row["prompt_sha256"] for row in rows}) == 1200
    for row in rows:
        source = sources[str(row["source_dataset"])][str(row["source_sample_id"])]
        assert row["prompt"] == source["prompt"]
        assert row["target"] == source["target"]
        assert row["text"] == source["prompt"] + source["target"]
        assert row["source_prompt_sha256"] == source["prompt_sha256"]
        assert row["source_target_sha256"] == source["target_sha256"]
        assert row["generated_rwkv_text"] is False
        assert row["raw_output_modified"] is False

    eval_ids: set[str] = set()
    for path in EVALS:
        for row in _rows(path):
            eval_ids.add(str(row["sample_id"]))
            if row.get("source_sample_id"):
                eval_ids.add(str(row["source_sample_id"]))
    assert not ({str(row["source_sample_id"]) for row in rows} & eval_ids)


def test_g7_all_prompts_targets_and_harness_contracts_are_valid(tmp_path: Path) -> None:
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )
    rows = _rows(DATASET / "stage_sft.train.jsonl")
    assert Counter(str(row["selected_operation"]) for row in rows) == Counter(
        json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))[
            "operation_counts"
        ]
    )
    for row in rows:
        prompt = str(row["prompt"])
        target = str(row["target"])
        requirement = current_requirement(prompt)
        validate_independent_executor_generation_input(prompt, requirement)
        assert int(row["prompt_tokens_local"]) > 0
        command = parse_model_command(target)
        assert command.name == row["selected_operation"]
        assert command.name != "select_tool"
        if command.name == "final_answer":
            validate_final_answer(command)
        else:
            harness.validate_action_contract(TaskAction(command.name, command.arguments))


def test_g7_visible_requests_use_the_frozen_similarity_metric() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    references = [
        (str(row["case_id"]), byte_ngrams(str(row["request"])))
        for path in HOLDOUTS
        for row in _rows(path)
    ]
    maximum = (-1.0, "", "")
    for row in _rows(DATASET / "stage_sft.train.jsonl"):
        grams = byte_ngrams(current_requirement(str(row["prompt"])))
        for holdout_id, reference in references:
            score = cosine(grams, reference)
            if score > maximum[0]:
                maximum = (score, str(row["sample_id"]), holdout_id)
    frozen = manifest["validation"]["maximum_visible_holdout_byte_5gram_cosine"]
    assert maximum == (frozen["score"], frozen["sample_id"], frozen["holdout_id"])
    assert maximum[0] < manifest["validation"]["similarity_threshold_exclusive"]
