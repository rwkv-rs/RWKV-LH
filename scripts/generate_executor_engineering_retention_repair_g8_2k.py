#!/usr/bin/env python3
"""Generate preregistered EXE-G8 train2000 and disjoint holdout240."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import math
import sys
import tempfile
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import (
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
PREREGISTRATION = EXPERIMENT / "EXE_G8_ENGINEERING_RETENTION_REPAIR_PREREGISTRATION.md"
G4_GENERATOR = ROOT / "scripts/generate_dual_lane_true_workflow_s55_g4.py"
G4 = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k"
G6 = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k"
G4_EVAL = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2"
G6_EVAL = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2"
G7_RESULT = EXPERIMENT / "run_exe_g7_network_retention_repair_ablation/ABLATION_RESULT.json"
G7_ANALYSIS = EXPERIMENT / "run_exe_g7_network_retention_repair_ablation/FAILURE_ANALYSIS.json"
LIVE_CASES = (
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl",
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v2/cases.jsonl",
)
TRAIN_OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_engineering_retention_repair_g8_2k"
HOLDOUT_OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_engineering_retention_g8_holdout_v1"

PREREGISTRATION_SHA256 = "84e46ccb2571c963efda78d1be325d832ed9ed8c6965b18f595c249deb7c29e4"
SOURCE_HASHES = {
    G4_GENERATOR: "c15f3947069ea1fd01efa7cf772b479cf53a8e2b6289424355a9cc6f3dbf89a6",
    G4 / "stage_sft.train.jsonl": "f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93",
    G4 / "manifest.json": "ad0781511f2ebc57b30a44dc7cb82daccf43f9871de7d36bcdbd58aeae9c831f",
    G6 / "stage_sft.train.jsonl": "ea3f62b22a6269e8b7d43b71386909532945085ff206d5fa0d530c4fc37519e6",
    G6 / "manifest.json": "b5f960a51a418d45b246bf454a3df8b9c326c0ded66af0e05cb05700a04f3c17",
    G4_EVAL / "stage_sft.dev.eval.jsonl": "f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d",
    G4_EVAL / "manifest.json": "d8dad84b355df504a5162017fedf3fd97036f91485869314187a513b6e71d5cf",
    G6_EVAL / "stage_sft.dev.eval.jsonl": "f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee",
    G6_EVAL / "manifest.json": "ba3bb05085c9055b3230fdb79ed859146ddf46d586c8d0f0f3c30b40c810eb3e",
    G7_RESULT: "18f00ac2bcd5bb18983ad5e569ae173141a65f68b7bbf2e4c186fc7414900133",
    G7_ANALYSIS: "474094c81175377dcfceb243af667b6278755f365adf9a5426a978c1d8451a3d",
    LIVE_CASES[0]: "971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708",
    LIVE_CASES[1]: "d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31",
}
TRAIN_DATASET_VERSION = "rwkv-lh.executor-state-tuning.g8-engineering-retention-repair-2k.v1"
TRAIN_SCHEMA_VERSION = "rwkv-lh.executor-stage-sft.g8.v1"
HOLDOUT_DATASET_VERSION = "rwkv-lh.executor-engineering-retention-g8-holdout.v1"
HOLDOUT_SCHEMA_VERSION = "rwkv-lh.executor-stage-eval.g8-holdout.v1"
CTX_LEN = 2496
FAMILIES = (
    "discount_ledger_release",
    "failed_check_dual_output_recovery",
    "implementation_bundle",
    "public_evidence_bundle",
    "connector_record_bundle",
)
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
    "fresh_targeted_full_workflow": 1200,
    "fresh_broad_full_workflow": 240,
    "balanced_direct_replay": 240,
    "network_clean_replay": 80,
    "network_protocol_recovery_replay": 80,
    "fresh_critical_position_supervision": 155,
    "direct_web_query_critical_replay": 5,
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


def load_frozen_g4_generator() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rwkv_lh_frozen_g4_generator", G4_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen G4 generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


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
    if list(payload)[-1] != "current_requirement":
        raise RuntimeError("current_requirement is not the literal final field")
    requirement = str(payload["current_requirement"])
    validate_independent_executor_generation_input(prompt, requirement)
    return requirement


def validate_target(harness: ActionHarness, row: Mapping[str, Any]) -> None:
    command = parse_model_command(str(row["target"]))
    if command.name != row["selected_operation"] or command.name == "select_tool":
        raise RuntimeError(f"G8 target operation mismatch: {row['sample_id']}")
    if command.name == "final_answer":
        validate_final_answer(command)
    else:
        harness.validate_action_contract(TaskAction(command.name, command.arguments))


def transform_generated(
    source: Mapping[str, Any],
    *,
    source_kind: str,
    selection_rule: str,
    holdout: bool = False,
) -> dict[str, Any]:
    row = deepcopy(dict(source))
    prompt = str(source["prompt"])
    target = str(source["target"])
    identity = str(source["sample_id"])
    row.update(
        {
            "schema_version": HOLDOUT_SCHEMA_VERSION if holdout else TRAIN_SCHEMA_VERSION,
            "dataset_version": HOLDOUT_DATASET_VERSION if holdout else TRAIN_DATASET_VERSION,
            "sample_id": ("EXEG8-H-" if holdout else "EXEG8-")
            + stable_hex(source_kind, identity)[:28],
            "split": "holdout" if holdout else "train",
            "source_kind": source_kind,
            "source_original_kind": source.get("source_kind"),
            "source_dataset": "frozen_g4_deterministic_generator",
            "source_dataset_version": source.get("dataset_version"),
            "source_sample_id": identity,
            "source_family_id": f"g8-generated:{source.get('family')}:{source.get('trajectory_id')}",
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
    if holdout:
        row["cluster"] = "g8_disjoint_true_workflow_holdout"
    return row


def transform_replay(
    source: Mapping[str, Any],
    *,
    source_dataset: str,
    source_kind: str,
    selection_rule: str,
) -> dict[str, Any]:
    row = deepcopy(dict(source))
    prompt = str(source["prompt"])
    target = str(source["target"])
    identity = str(source["sample_id"])
    row.update(
        {
            "schema_version": TRAIN_SCHEMA_VERSION,
            "dataset_version": TRAIN_DATASET_VERSION,
            "sample_id": "EXEG8-" + stable_hex(source_dataset, source_kind, identity)[:28],
            "split": "train",
            "source_kind": source_kind,
            "source_original_kind": source.get("source_kind"),
            "source_dataset": source_dataset,
            "source_dataset_version": source.get("dataset_version"),
            "source_sample_id": identity,
            "source_family_id": f"g8-replay:{source_dataset}:{identity}",
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


def select_by_operation(
    rows: Iterable[dict[str, Any]],
    *,
    original_kind: str,
    counts: Mapping[str, int],
    offsets: Mapping[str, int] | None = None,
) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row.get("source_kind") == original_kind:
            grouped[str(row["selected_operation"])].append(row)
    if set(grouped) != set(counts):
        raise RuntimeError(f"operation surface changed for {original_kind}: {sorted(grouped)}")
    selected: list[dict[str, Any]] = []
    for operation, count in counts.items():
        candidates = sorted(grouped[operation], key=lambda item: str(item["sample_id"]))
        offset = int((offsets or {}).get(operation, 0))
        chosen = candidates[offset : offset + count]
        if len(chosen) != count:
            raise RuntimeError(f"insufficient {original_kind}:{operation} rows")
        selected.extend(chosen)
    return selected


def generated_trajectory(
    generator: ModuleType,
    harness: ActionHarness,
    tool_definitions: dict[str, dict[str, Any]],
    *,
    family: str,
    split: str,
    index: int,
) -> list[dict[str, Any]]:
    _, executor_rows = generator.trajectory_rows(
        family=family,
        split=split,
        index=index,
        harness=harness,
        tool_definitions=tool_definitions,
    )
    if len(executor_rows) != 8:
        raise RuntimeError("generated G8 trajectory length changed")
    return executor_rows


def stage_dataset(
    output: Path,
    rows: list[dict[str, Any]],
    manifest: dict[str, Any],
    *,
    tuning: bool,
    title: str,
) -> Path:
    staging = Path(tempfile.mkdtemp(prefix=f".{output.name}.", dir=output.parent))
    filename = "stage_sft.train.jsonl" if tuning else "stage_sft.holdout.eval.jsonl"
    stage_path = staging / filename
    write_jsonl(stage_path, rows)
    files = {
        stage_path.name: {
            "rows": len(rows),
            "bytes": stage_path.stat().st_size,
            "sha256": sha256_file(stage_path),
        }
    }
    if tuning:
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
        files[tuning_path.name] = {
            "rows": len(rows),
            "bytes": tuning_path.stat().st_size,
            "sha256": sha256_file(tuning_path),
        }
    manifest["files"] = files
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(f"# {title}\n", encoding="utf-8")
    return staging


def main() -> None:
    if TRAIN_OUTPUT.exists() or HOLDOUT_OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen G8 datasets")
    if sha256_file(PREREGISTRATION) != PREREGISTRATION_SHA256:
        raise RuntimeError("G8 preregistration changed")
    for path, expected in SOURCE_HASHES.items():
        if sha256_file(path) != expected:
            raise RuntimeError(f"frozen G8 source changed: {path}")

    generator = load_frozen_g4_generator()
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=ROOT / "temp/executor-g8-unused-snapshots",
        sandbox_commands=False,
    )
    tool_definitions = generator.definitions(harness)
    g4_rows = read_jsonl(G4 / "stage_sft.train.jsonl")
    g6_rows = read_jsonl(G6 / "stage_sft.train.jsonl")

    train_rows: list[dict[str, Any]] = []
    for family in ("discount_ledger_release", "failed_check_dual_output_recovery"):
        for index in range(20, 95):
            train_rows.extend(
                transform_generated(
                    row,
                    source_kind="fresh_targeted_full_workflow",
                    selection_rule=f"full_train_trajectory_{family}_index20_94",
                )
                for row in generated_trajectory(
                    generator,
                    harness,
                    tool_definitions,
                    family=family,
                    split="train",
                    index=index,
                )
            )
    for family in ("implementation_bundle", "public_evidence_bundle", "connector_record_bundle"):
        for index in range(20, 30):
            train_rows.extend(
                transform_generated(
                    row,
                    source_kind="fresh_broad_full_workflow",
                    selection_rule=f"full_train_trajectory_{family}_index20_29",
                )
                for row in generated_trajectory(
                    generator,
                    harness,
                    tool_definitions,
                    family=family,
                    split="train",
                    index=index,
                )
            )

    direct_operations = sorted(
        {
            str(row["selected_operation"])
            for row in g4_rows
            if row.get("source_kind") == "g3_frozen_direct_retention"
        }
    )
    if len(direct_operations) != 24:
        raise RuntimeError("G8 direct operation surface changed")
    direct = select_by_operation(
        g4_rows,
        original_kind="g3_frozen_direct_retention",
        counts={operation: 10 for operation in direct_operations},
    )
    train_rows.extend(
        transform_replay(
            row,
            source_dataset="g4_train",
            source_kind="balanced_direct_replay",
            selection_rule="first_10_sample_ids_per_24_operations",
        )
        for row in direct
    )
    clean = select_by_operation(
        g6_rows,
        original_kind="clean_network_stage",
        counts=CLEAN_COUNTS,
    )
    recovery = select_by_operation(
        g6_rows,
        original_kind="protocol_rejection_recovery",
        counts=RECOVERY_COUNTS,
    )
    train_rows.extend(
        transform_replay(
            row,
            source_dataset="g6_train",
            source_kind="network_clean_replay",
            selection_rule="frozen_g7_clean_operation_quota",
        )
        for row in clean
    )
    train_rows.extend(
        transform_replay(
            row,
            source_dataset="g6_train",
            source_kind="network_protocol_recovery_replay",
            selection_rule="frozen_g7_recovery_operation_quota",
        )
        for row in recovery
    )

    critical_specs = (
        ("failed_check_dual_output_recovery", range(95, 155), 2, "recovery_write_json_60"),
        ("discount_ledger_release", range(95, 125), 4, "discount_write_json_30"),
        ("discount_ledger_release", range(125, 145), 5, "discount_write_file_20"),
        ("discount_ledger_release", range(145, 160), 7, "discount_final_answer_15"),
        ("failed_check_dual_output_recovery", range(155, 170), 7, "recovery_final_answer_15"),
        ("discount_ledger_release", range(160, 170), 3, "discount_verifier_read_file_10"),
        ("discount_ledger_release", range(170, 175), 2, "discount_read_json_5"),
    )
    for family, indices, position, rule in critical_specs:
        for index in indices:
            trajectory = generated_trajectory(
                generator,
                harness,
                tool_definitions,
                family=family,
                split="train",
                index=index,
            )
            train_rows.append(
                transform_generated(
                    trajectory[position],
                    source_kind="fresh_critical_position_supervision",
                    selection_rule=rule,
                )
            )
    extra_web = select_by_operation(
        g4_rows,
        original_kind="g3_frozen_direct_retention",
        counts={operation: (5 if operation == "web_search" else 0) for operation in direct_operations},
        offsets={"web_search": 10},
    )
    train_rows.extend(
        transform_replay(
            row,
            source_dataset="g4_train",
            source_kind="direct_web_query_critical_replay",
            selection_rule="web_search_sample_ids_rank_11_to_15",
        )
        for row in extra_web
    )

    source_counts = dict(sorted(Counter(str(row["source_kind"]) for row in train_rows).items()))
    if len(train_rows) != 2000 or source_counts != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(f"G8 train distribution changed: {len(train_rows)} {source_counts}")

    holdout_rows: list[dict[str, Any]] = []
    for family in FAMILIES:
        for index in range(6):
            holdout_rows.extend(
                transform_generated(
                    row,
                    source_kind="g8_disjoint_true_workflow_holdout",
                    selection_rule=f"frozen_test_split_{family}_index0_5",
                    holdout=True,
                )
                for row in generated_trajectory(
                    generator,
                    harness,
                    tool_definitions,
                    family=family,
                    split="test",
                    index=index,
                )
            )
    if len(holdout_rows) != 240:
        raise RuntimeError("G8 holdout count changed")

    all_rows = train_rows + holdout_rows
    if len({str(row["sample_id"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("G8 sample ID duplicate detected")
    if len({str(row["prompt_sha256"]) for row in all_rows}) != len(all_rows):
        raise RuntimeError("G8 exact prompt duplicate detected")
    train_sources = {str(row["source_sample_id"]) for row in train_rows}
    holdout_sources = {str(row["source_sample_id"]) for row in holdout_rows}
    eval_sources: set[str] = set()
    for dataset in (G4_EVAL, G6_EVAL):
        for row in read_jsonl(dataset / "stage_sft.dev.eval.jsonl"):
            eval_sources.add(str(row["sample_id"]))
            if row.get("source_sample_id"):
                eval_sources.add(str(row["source_sample_id"]))
    if train_sources & (holdout_sources | eval_sources):
        raise RuntimeError("G8 train/eval source identity overlap")

    train_sample_ids = {str(row["sample_id"]) for row in train_rows}
    maximum_tokens = 0
    requests: list[tuple[str, str]] = []
    for row in all_rows:
        prompt = str(row["prompt"])
        target = str(row["target"])
        requirement = current_requirement(prompt)
        if row["text"] != prompt + target:
            raise RuntimeError(f"G8 text composition changed: {row['sample_id']}")
        if row["source_prompt_sha256"] != row["prompt_sha256"]:
            raise RuntimeError(f"G8 generated/replay prompt changed: {row['sample_id']}")
        if row["source_target_sha256"] != row["target_sha256"]:
            raise RuntimeError(f"G8 generated/replay target changed: {row['sample_id']}")
        validate_target(harness, row)
        total_tokens = int(row["prompt_tokens_local"]) + get_token_count(target)
        maximum_tokens = max(maximum_tokens, total_tokens)
        if total_tokens > CTX_LEN:
            raise RuntimeError(f"G8 target truncation: {row['sample_id']}")
        if str(row["sample_id"]) in train_sample_ids:
            requests.append((str(row["sample_id"]), requirement))

    references = [
        (str(item["case_id"]), byte_ngrams(str(item["request"])))
        for path in LIVE_CASES
        for item in read_jsonl(path)
    ]
    maximum_similarity: dict[str, Any] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
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
        raise RuntimeError(f"G8 live holdout similarity failed: {maximum_similarity}")

    common_sources = {
        str(path.relative_to(ROOT)): digest for path, digest in SOURCE_HASHES.items()
    }
    generation = {
        "path": str(Path(__file__).resolve().relative_to(ROOT)),
        "sha256": sha256_file(Path(__file__).resolve()),
        "frozen_workflow_generator_path": str(G4_GENERATOR.relative_to(ROOT)),
        "frozen_workflow_generator_sha256": SOURCE_HASHES[G4_GENERATOR],
    }
    validation = {
        "exact_prompt_duplicates_train_and_holdout": 0,
        "train_eval_source_identity_overlap": 0,
        "current_requirement_literal_last": True,
        "target_truncation_count": 0,
        "maximum_tokens_without_bos": maximum_tokens,
        "all_targets_current_contract_valid": True,
        "generated_rwkv_text": False,
        "raw_output_modified": False,
        "maximum_live_holdout_byte_5gram_cosine": maximum_similarity,
        "similarity_algorithm": "byte-5-gram cosine",
        "similarity_threshold_exclusive": 0.75,
    }
    train_manifest: dict[str, Any] = {
        "schema_version": "rwkv-lh.executor-dataset-manifest.g8.v1",
        "dataset_version": TRAIN_DATASET_VERSION,
        "purpose": "repair stable engineering retention failures while preserving network behavior",
        "counts": {"train": len(train_rows)},
        "source_counts": source_counts,
        "family_counts": dict(sorted(Counter(str(row.get("family")) for row in train_rows).items())),
        "operation_counts": dict(sorted(Counter(str(row["selected_operation"]) for row in train_rows).items())),
        "trajectory_position_counts": dict(sorted(Counter(str(row.get("trajectory_position")) for row in train_rows).items())),
        "network_replay_operation_counts": {"clean": CLEAN_COUNTS, "protocol_recovery": RECOVERY_COUNTS},
        "sources": common_sources,
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "training_contract": {
            "ctx_len": CTX_LEN,
            "steps": 2000,
            "seed": 1079,
            "parent_training_state_sha256": "648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78",
            "parent_vllm_state_sha256": "611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b",
            "physical_gpu": 0,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "lr_init": "2e-6",
            "lr_final": "2e-7",
            "save_steps": list(range(250, 2001, 250)),
        },
        "validation": validation,
        "generation": generation,
    }
    holdout_manifest: dict[str, Any] = {
        "schema_version": "rwkv-lh.executor-eval-manifest.g8-holdout.v1",
        "dataset_version": HOLDOUT_DATASET_VERSION,
        "purpose": "disjoint complete-workflow generalization holdout for G8 selection",
        "counts": {"holdout": len(holdout_rows)},
        "family_counts": dict(sorted(Counter(str(row["family"]) for row in holdout_rows).items())),
        "operation_counts": dict(sorted(Counter(str(row["selected_operation"]) for row in holdout_rows).items())),
        "sources": common_sources,
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "validation": {
            **validation,
            "holdout_entered_state_tuning": False,
            "split": "frozen_generator_test_index0_5",
        },
        "generation": generation,
    }

    train_staging = stage_dataset(
        TRAIN_OUTPUT,
        train_rows,
        train_manifest,
        tuning=True,
        title="EXE-G8 engineering retention repair train2000",
    )
    holdout_staging = stage_dataset(
        HOLDOUT_OUTPUT,
        holdout_rows,
        holdout_manifest,
        tuning=False,
        title="EXE-G8 disjoint complete-workflow holdout240",
    )
    train_staging.rename(TRAIN_OUTPUT)
    holdout_staging.rename(HOLDOUT_OUTPUT)
    print(
        json.dumps(
            {
                "event": "executor_g8_datasets_finalized",
                "train_rows": len(train_rows),
                "holdout_rows": len(holdout_rows),
                "source_counts": source_counts,
                "maximum_tokens_without_bos": maximum_tokens,
                "maximum_holdout_similarity": maximum_similarity,
                "train_manifest_sha256": sha256_file(TRAIN_OUTPUT / "manifest.json"),
                "holdout_manifest_sha256": sha256_file(HOLDOUT_OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
