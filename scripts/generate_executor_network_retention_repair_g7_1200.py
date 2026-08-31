#!/usr/bin/env python3
"""Generate the preregistered EXE-G7 retention-repair replay dataset."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import (
    FINAL_ANSWER_DEFINITION,
    INDEPENDENT_EXECUTOR_CONTINUATION_ANCHOR,
    INDEPENDENT_EXECUTOR_DISCLOSURE_MARKER,
    parse_model_command,
    validate_final_answer,
    validate_independent_executor_generation_input,
)
from rwkv_lh.retrieval import RetrievalRuntimeConfig, build_product_harness
from rwkv_lh.retrieval.policy import NetworkPolicyMode
from rwkv_lh.schema import TaskAction
from rwkv_lh.token_budget import get_token_count


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
PREREGISTRATION = EXPERIMENT / "EXE_G7_NETWORK_RETENTION_REPAIR_PREREGISTRATION.md"
G4 = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k"
G6 = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k"
G4_EVAL = (
    ROOT
    / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2/stage_sft.dev.eval.jsonl"
)
G6_EVAL = (
    ROOT
    / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl"
)
HOLDOUTS = (
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl",
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v2/cases.jsonl",
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_network_retention_repair_g7_1200"

DATASET_VERSION = "rwkv-lh.executor-state-tuning.g7-network-retention-repair-1200.v1"
SCHEMA_VERSION = "rwkv-lh.executor-stage-sft.g7.v1"
CTX_LEN = 2496
PREREGISTRATION_SHA256 = (
    "a6796579429506033e73e49491cc494e11f680b3ad025cc50ff831a1b8e7a346"
)
SOURCE_HASHES = {
    G4 / "stage_sft.train.jsonl": "f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93",
    G4 / "manifest.json": "ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f",
    G6 / "stage_sft.train.jsonl": "ea3f62b22a6269e8b7d43b71386909532945085ff206d5fa0d530c4fc37519e6",
    G6 / "manifest.json": "b5f960a51a418d45b246bf454a3df8b9c326c0ded66af0e05cb05700a04f3c17",
    G4_EVAL: "f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d",
    G6_EVAL: "f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee",
    HOLDOUTS[0]: "971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708",
    HOLDOUTS[1]: "d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31",
}
CLEAN_COUNTS = {
    "web_search": 8,
    "connector_lookup": 8,
    "write_file": 20,
    "write_json": 20,
    "read_file": 6,
    "read_json": 6,
    "bind_evidence": 4,
    "file_digest": 4,
    "final_answer": 4,
}
RECOVERY_COUNTS = {
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
}
EXPECTED_SOURCE_COUNTS = {
    "g4_all_workflow_rehearsal": 800,
    "g4_balanced_direct_rehearsal": 240,
    "g6_clean_network_rehearsal": 80,
    "g6_protocol_recovery_rehearsal": 80,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def stable_hex(*parts: object) -> str:
    return hashlib.sha256(
        "|".join(str(part) for part in parts).encode("utf-8")
    ).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    return Counter(raw[index : index + n] for index in range(max(0, len(raw) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(
        sum(value * value for value in left.values())
        * sum(value * value for value in right.values())
    )


def current_requirement(prompt: str) -> str:
    start = prompt.index(INDEPENDENT_EXECUTOR_DISCLOSURE_MARKER) + len(
        INDEPENDENT_EXECUTOR_DISCLOSURE_MARKER
    )
    end = prompt.index(INDEPENDENT_EXECUTOR_CONTINUATION_ANCHOR, start)
    payload = json.loads(prompt[start:end])
    requirement = str(payload["current_requirement"])
    validate_independent_executor_generation_input(prompt, requirement)
    return requirement


def select_by_operation(
    rows: Iterable[dict[str, Any]],
    *,
    source_kind: str,
    counts: Mapping[str, int],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("source_kind") == source_kind:
            grouped[str(row["selected_operation"])].append(row)
    if set(grouped) != set(counts):
        raise RuntimeError(
            f"operation surface changed for {source_kind}: {sorted(grouped)}"
        )
    selected: list[dict[str, Any]] = []
    for operation, count in counts.items():
        candidates = sorted(grouped[operation], key=lambda item: str(item["sample_id"]))
        if len(candidates) < count:
            raise RuntimeError(f"insufficient {source_kind}:{operation} rows")
        selected.extend(candidates[:count])
    return selected


def replay_row(
    source: Mapping[str, Any],
    *,
    source_dataset: str,
    source_kind: str,
    selection_rule: str,
) -> dict[str, Any]:
    row = deepcopy(dict(source))
    source_sample_id = str(source["sample_id"])
    prompt = str(source["prompt"])
    target = str(source["target"])
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "dataset_version": DATASET_VERSION,
            "sample_id": "EXEG7-"
            + stable_hex(source_dataset, source_kind, source_sample_id)[:28],
            "split": "train",
            "source_kind": source_kind,
            "source_original_kind": source.get("source_kind"),
            "source_dataset": source_dataset,
            "source_dataset_version": source.get("dataset_version"),
            "source_sample_id": source_sample_id,
            "source_family_id": f"g7:{source_dataset}:{source_sample_id}",
            "selection_rule": selection_rule,
            "source_prompt_sha256": source.get("prompt_sha256"),
            "source_target_sha256": source.get("target_sha256"),
            "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
            "target_sha256": hashlib.sha256(target.encode()).hexdigest(),
            "text": prompt + target,
            "text_sha256": hashlib.sha256((prompt + target).encode()).hexdigest(),
            "generated_rwkv_text": False,
            "raw_output_modified": False,
        }
    )
    return row


def validate_target(harness: ActionHarness, row: Mapping[str, Any]) -> None:
    command = parse_model_command(str(row["target"]))
    if command.name != row["selected_operation"] or command.name == "select_tool":
        raise RuntimeError(f"G7 target operation mismatch: {row['sample_id']}")
    if command.name == "final_answer":
        validate_final_answer(command)
    else:
        harness.validate_action_contract(TaskAction(command.name, command.arguments))


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to replace frozen G7 dataset: {OUTPUT}")
    if sha256_file(PREREGISTRATION) != PREREGISTRATION_SHA256:
        raise RuntimeError("G7 preregistration changed")
    for path, expected in SOURCE_HASHES.items():
        if sha256_file(path) != expected:
            raise RuntimeError(f"frozen G7 source changed: {path}")

    g4_rows = read_jsonl(G4 / "stage_sft.train.jsonl")
    g6_rows = read_jsonl(G6 / "stage_sft.train.jsonl")
    workflow = [
        row
        for row in g4_rows
        if row.get("source_kind") == "synthetic_true_workflow_request_last"
    ]
    if len(workflow) != 800:
        raise RuntimeError("G4 train workflow count changed")
    direct = select_by_operation(
        g4_rows,
        source_kind="g3_frozen_direct_retention",
        counts={operation: 10 for operation in sorted({str(row["selected_operation"]) for row in g4_rows if row.get("source_kind") == "g3_frozen_direct_retention"})},
    )
    if len(direct) != 240:
        raise RuntimeError("G7 balanced direct count changed")
    clean = select_by_operation(
        g6_rows,
        source_kind="clean_network_stage",
        counts=CLEAN_COUNTS,
    )
    recovery = select_by_operation(
        g6_rows,
        source_kind="protocol_rejection_recovery",
        counts=RECOVERY_COUNTS,
    )

    rows: list[dict[str, Any]] = []
    rows.extend(
        replay_row(
            row,
            source_dataset="g4_train",
            source_kind="g4_all_workflow_rehearsal",
            selection_rule="all_800_frozen_train_workflow_rows",
        )
        for row in workflow
    )
    rows.extend(
        replay_row(
            row,
            source_dataset="g4_train",
            source_kind="g4_balanced_direct_rehearsal",
            selection_rule="first_10_sample_ids_per_24_operations",
        )
        for row in direct
    )
    rows.extend(
        replay_row(
            row,
            source_dataset="g6_train",
            source_kind="g6_clean_network_rehearsal",
            selection_rule="preregistered_operation_quota",
        )
        for row in clean
    )
    rows.extend(
        replay_row(
            row,
            source_dataset="g6_train",
            source_kind="g6_protocol_recovery_rehearsal",
            selection_rule="preregistered_operation_quota",
        )
        for row in recovery
    )
    if len(rows) != 1200:
        raise RuntimeError(f"G7 row count changed: {len(rows)}")
    source_counts = dict(sorted(Counter(str(row["source_kind"]) for row in rows).items()))
    if source_counts != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(f"G7 source counts changed: {source_counts}")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("G7 sample IDs are not unique")
    if len({str(row["prompt_sha256"]) for row in rows}) != len(rows):
        raise RuntimeError("G7 exact prompt duplicate detected")

    eval_source_ids: set[str] = set()
    for path in (G4_EVAL, G6_EVAL):
        for row in read_jsonl(path):
            eval_source_ids.add(str(row["sample_id"]))
            if row.get("source_sample_id"):
                eval_source_ids.add(str(row["source_sample_id"]))
    train_source_ids = {str(row["source_sample_id"]) for row in rows}
    overlap = train_source_ids & eval_source_ids
    if overlap:
        raise RuntimeError(f"G7 train/eval source overlap: {sorted(overlap)[:3]}")

    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=ROOT / "temp/executor-g7-unused-snapshots",
        sandbox_commands=False,
    )
    maximum_tokens = 0
    requests: list[tuple[str, str]] = []
    for row in rows:
        prompt = str(row["prompt"])
        target = str(row["target"])
        requirement = current_requirement(prompt)
        if row.get("request") is not None and str(row["request"]) != requirement:
            raise RuntimeError(f"G7 immutable request changed: {row['sample_id']}")
        if row["text"] != prompt + target:
            raise RuntimeError(f"G7 text composition changed: {row['sample_id']}")
        if row["source_prompt_sha256"] != row["prompt_sha256"]:
            raise RuntimeError(f"G7 source prompt changed: {row['sample_id']}")
        if row["source_target_sha256"] != row["target_sha256"]:
            raise RuntimeError(f"G7 source target changed: {row['sample_id']}")
        validate_target(harness, row)
        total_tokens = int(row["prompt_tokens_local"]) + get_token_count(target)
        maximum_tokens = max(maximum_tokens, total_tokens)
        if total_tokens > CTX_LEN:
            raise RuntimeError(f"G7 target truncation: {row['sample_id']}")
        requests.append((str(row["sample_id"]), requirement))

    references = [
        (str(item["case_id"]), byte_ngrams(str(item["request"])))
        for path in HOLDOUTS
        for item in read_jsonl(path)
    ]
    maximum_similarity: dict[str, Any] = {
        "score": -1.0,
        "sample_id": "",
        "holdout_id": "",
    }
    for sample_id, request in requests:
        grams = byte_ngrams(request)
        for holdout_id, reference in references:
            score = cosine(grams, reference)
            if score > maximum_similarity["score"]:
                maximum_similarity = {
                    "score": score,
                    "sample_id": sample_id,
                    "holdout_id": holdout_id,
                }
    if maximum_similarity["score"] >= 0.75:
        raise RuntimeError(f"G7 visible holdout similarity failed: {maximum_similarity}")

    operation_counts = dict(
        sorted(Counter(str(row["selected_operation"]) for row in rows).items())
    )
    family_counts = dict(sorted(Counter(str(row.get("family")) for row in rows).items()))
    position_counts = dict(
        sorted(Counter(str(row.get("trajectory_position")) for row in rows).items())
    )
    manifest: dict[str, Any] = {
        "schema_version": "rwkv-lh.executor-dataset-manifest.g7.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "repair network-profile workflow retention while preserving perfect network behavior",
        "counts": {"train": len(rows)},
        "source_counts": source_counts,
        "operation_counts": operation_counts,
        "family_counts": family_counts,
        "trajectory_position_counts": position_counts,
        "network_replay_operation_counts": {
            "clean": CLEAN_COUNTS,
            "protocol_recovery": RECOVERY_COUNTS,
        },
        "sources": {
            str(path.relative_to(ROOT)): digest
            for path, digest in SOURCE_HASHES.items()
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "training_contract": {
            "ctx_len": CTX_LEN,
            "steps": 1200,
            "seed": 1071,
            "parent_training_state_sha256": "648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78",
            "parent_vllm_state_sha256": "611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b",
            "physical_gpu": 0,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "lr_init": "1e-6",
            "lr_final": "1e-7",
            "save_steps": [150, 300, 450, 600, 750, 900, 1050, 1200],
        },
        "validation": {
            "exact_prompt_duplicates": 0,
            "train_eval_source_sample_id_overlap": 0,
            "source_prompt_bytes_preserved": True,
            "source_target_bytes_preserved": True,
            "request_or_question_at_literal_tail": True,
            "target_truncation_count": 0,
            "maximum_tokens_without_bos": maximum_tokens,
            "all_targets_current_contract_valid": True,
            "generated_rwkv_text": False,
            "raw_output_modified": False,
            "maximum_visible_holdout_byte_5gram_cosine": maximum_similarity,
            "similarity_algorithm": "byte-5-gram cosine",
            "similarity_threshold_exclusive": 0.75,
        },
        "generation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
    }

    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    stage_path = staging / "stage_sft.train.jsonl"
    write_jsonl(stage_path, rows)
    tuning_path = staging / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
    write_jsonl(
        tuning_path,
        (
            {
                "prompt": row["prompt"],
                "target": row["target"],
                "text": row["text"],
                "tier": 1,
            }
            for row in rows
        ),
    )
    manifest["files"] = {
        path.name: {
            "rows": len(rows),
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        for path in (stage_path, tuning_path)
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# EXE-G7 network retention repair 1200\n\n"
        "Frozen target-suffix replay data; train sources only.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "executor_g7_dataset_finalized",
                "rows": len(rows),
                "source_counts": source_counts,
                "maximum_tokens_without_bos": maximum_tokens,
                "maximum_holdout_similarity": maximum_similarity,
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
