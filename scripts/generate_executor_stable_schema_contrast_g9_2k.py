#!/usr/bin/env python3
"""Generate the preregistered EXE-G9 stable-schema contrast train2000."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
from collections import Counter
from copy import deepcopy
from pathlib import Path
from types import ModuleType
from typing import Any, Mapping

from rwkv_lh.retrieval import RetrievalRuntimeConfig, build_product_harness
from rwkv_lh.retrieval.policy import NetworkPolicyMode


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
PREREGISTRATION = EXPERIMENT / "EXE_G9_STABLE_SCHEMA_CONTRAST_PREREGISTRATION.md"
G8_GENERATOR = ROOT / "scripts/generate_executor_engineering_retention_repair_g8_2k.py"
G4_GENERATOR = ROOT / "scripts/generate_dual_lane_true_workflow_s55_g4.py"
G4_TRAIN = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k/stage_sft.train.jsonl"
G6_TRAIN = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k/stage_sft.train.jsonl"
G4_EVAL = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2/stage_sft.dev.eval.jsonl"
G6_EVAL = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2/stage_sft.dev.eval.jsonl"
G8_HOLDOUT = (
    ROOT
    / "data/datasets/rwkv_lh_executor_engineering_retention_g8_holdout_v1/"
    "stage_sft.holdout.eval.metadata_v2.jsonl"
)
G8_RESULT = EXPERIMENT / "run_exe_g8_engineering_retention_repair_ablation/ABLATION_RESULT.json"
G8_ANALYSIS = EXPERIMENT / "run_exe_g8_engineering_retention_repair_ablation/FAILURE_ANALYSIS.json"
LIVE_CASES = (
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v1/cases.jsonl",
    ROOT / "data/datasets/rwkv_lh_live_network_rwkv_e2e_v2/cases.jsonl",
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_stable_schema_contrast_g9_2k"

PREREGISTRATION_SHA256 = "0c50e9d185ffe5732fffb9eeba3e3affd535e59b425eb619f9646f9f3678c54a"
G8_GENERATOR_SHA256 = "52383b182e14617f812faf00c6276bcce4f3b19009124db2023454e44dd3c321"
SOURCE_HASHES = {
    G4_GENERATOR: "c15f3947069ea1fd01efa7cf772b479cf53a8e2b6289424355a9cc6f3dbf89a6",
    G4_TRAIN: "f5a1e2d3a06c4877bf589001ae988fe4fe7a6a4540e8ca0b5121a8af40890e93",
    G6_TRAIN: "ea3f62b22a6269e8b7d43b71386909532945085ff206d5fa0d530c4fc37519e6",
    G4_EVAL: "f89ff7828dfa298eedfab6c2cef531708fac7e812e9c309530086a5192770e5d",
    G6_EVAL: "f80f7452f5dcc38b8932de50eb391e6b8cbd0f494cbab40b4b8d4b8db6d072ee",
    G8_HOLDOUT: "0b7bc953b40eedb4f0d6169e88e85ad615180ca34d75abf02023e7d14399c48d",
    G8_RESULT: "a4c3f57e807dd9e2f6adfea7dbb1436c5e99d0e98bbcb62883dce6f656a1b9b2",
    G8_ANALYSIS: "51ba6667061d497d1f577fc7e2085a13deecebaf6a59725f7e372b8f79bff999",
    LIVE_CASES[0]: "971c89f2def921498b664e069f4af281857aac377bec881ce04d2c57fbb66708",
    LIVE_CASES[1]: "d8ad5bd999d26b6b16292fae7503534dcb01d3f8ae0c7a1d9c78c93d1d1deb31",
}
DATASET_VERSION = "rwkv-lh.executor-state-tuning.g9-stable-schema-contrast-2k.v1"
SCHEMA_VERSION = "rwkv-lh.executor-stage-sft.g9.v1"
CTX_LEN = 2496
EXPECTED_SOURCE_COUNTS = {
    "critical_recovery_write_json": 960,
    "critical_recovery_final": 160,
    "critical_discount_final": 160,
    "critical_discount_write_file": 80,
    "critical_discount_read_json": 80,
    "critical_implementation_manifest": 80,
    "balanced_direct_anchor": 240,
    "network_clean_anchor": 120,
    "network_recovery_anchor": 120,
}
CLEAN_COUNTS = {
    "web_search": 12,
    "connector_lookup": 12,
    "write_file": 30,
    "write_json": 30,
    "read_file": 9,
    "read_json": 9,
    "bind_evidence": 6,
    "file_digest": 6,
    "final_answer": 6,
}
RECOVERY_COUNTS = {
    "write_file": 24,
    "write_json": 20,
    "read_file": 8,
    "read_json": 8,
    "append_file": 20,
    "copy_file": 6,
    "move_file": 6,
    "file_digest": 6,
    "web_search": 4,
    "connector_lookup": 4,
    "bind_evidence": 4,
    "final_answer": 10,
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


def load_g8_helpers() -> ModuleType:
    if sha256_file(G8_GENERATOR) != G8_GENERATOR_SHA256:
        raise RuntimeError("frozen G8 generator changed")
    spec = importlib.util.spec_from_file_location("rwkv_lh_g9_g8_helpers", G8_GENERATOR)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen G8 helpers")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def transform_generated(
    source: Mapping[str, Any],
    *,
    source_kind: str,
    selection_rule: str,
) -> dict[str, Any]:
    row = deepcopy(dict(source))
    prompt = str(source["prompt"])
    target = str(source["target"])
    identity = str(source["sample_id"])
    row.update(
        {
            "schema_version": SCHEMA_VERSION,
            "dataset_version": DATASET_VERSION,
            "sample_id": "EXEG9-" + stable_hex(source_kind, identity)[:28],
            "split": "train",
            "source_kind": source_kind,
            "source_original_kind": source.get("source_kind"),
            "source_dataset": "frozen_g4_deterministic_generator",
            "source_dataset_version": source.get("dataset_version"),
            "source_sample_id": identity,
            "source_family_id": f"g9-generated:{source.get('family')}:{source.get('trajectory_id')}",
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


def transform_replay(
    source: Mapping[str, Any],
    *,
    source_dataset: str,
    source_kind: str,
    selection_rule: str,
) -> dict[str, Any]:
    row = transform_generated(
        source,
        source_kind=source_kind,
        selection_rule=selection_rule,
    )
    row["source_dataset"] = source_dataset
    row["source_family_id"] = f"g9-anchor:{source_dataset}:{source['sample_id']}"
    row["sample_id"] = "EXEG9-" + stable_hex(
        source_dataset,
        source_kind,
        source["sample_id"],
    )[:28]
    return row


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen G9 dataset")
    if sha256_file(PREREGISTRATION) != PREREGISTRATION_SHA256:
        raise RuntimeError("G9 preregistration changed")
    for path, expected in SOURCE_HASHES.items():
        if sha256_file(path) != expected:
            raise RuntimeError(f"frozen G9 source changed: {path}")
    analysis = json.loads(G8_ANALYSIS.read_text(encoding="utf-8"))
    if not (
        analysis.get("status") == "analysis_complete_no_training_leakage"
        and analysis.get("eval_rows_or_targets_authorized_for_training") is False
        and analysis.get("g6_dev", {}).get("oracle_exact") == 466
        and analysis.get("g8_holdout", {}).get("oracle_exact") == 231
    ):
        raise RuntimeError("G8 failure-analysis contract changed")

    base = load_g8_helpers()
    generator = base.load_frozen_g4_generator()
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=ROOT / "temp/executor-g9-unused-snapshots",
        sandbox_commands=False,
    )
    definitions = generator.definitions(harness)

    def generated(family: str, index: int, position: int) -> dict[str, Any]:
        trajectory = base.generated_trajectory(
            generator,
            harness,
            definitions,
            family=family,
            split="train",
            index=index,
        )
        return trajectory[position]

    train_rows: list[dict[str, Any]] = []
    targeted = (
        (
            "failed_check_dual_output_recovery",
            range(500, 1460),
            2,
            "critical_recovery_write_json",
        ),
        (
            "failed_check_dual_output_recovery",
            range(1460, 1620),
            7,
            "critical_recovery_final",
        ),
        (
            "discount_ledger_release",
            range(500, 660),
            7,
            "critical_discount_final",
        ),
        (
            "discount_ledger_release",
            range(660, 740),
            5,
            "critical_discount_write_file",
        ),
        (
            "discount_ledger_release",
            range(740, 820),
            2,
            "critical_discount_read_json",
        ),
        (
            "implementation_bundle",
            range(500, 580),
            5,
            "critical_implementation_manifest",
        ),
    )
    for family, indices, position, kind in targeted:
        for index in indices:
            train_rows.append(
                transform_generated(
                    generated(family, index, position),
                    source_kind=kind,
                    selection_rule=(
                        f"fresh_train_{family}_position{position}_index"
                        f"{indices.start}_{indices.stop - 1}"
                    ),
                )
            )

    g4_rows = base.read_jsonl(G4_TRAIN)
    g6_rows = base.read_jsonl(G6_TRAIN)
    operations = sorted(
        {
            str(row["selected_operation"])
            for row in g4_rows
            if row.get("source_kind") == "g3_frozen_direct_retention"
        }
    )
    if len(operations) != 24:
        raise RuntimeError("G9 direct operation surface changed")
    direct = base.select_by_operation(
        g4_rows,
        original_kind="g3_frozen_direct_retention",
        counts={operation: 10 for operation in operations},
    )
    clean = base.select_by_operation(
        g6_rows,
        original_kind="clean_network_stage",
        counts=CLEAN_COUNTS,
    )
    recovery = base.select_by_operation(
        g6_rows,
        original_kind="protocol_rejection_recovery",
        counts=RECOVERY_COUNTS,
    )
    for row in direct:
        train_rows.append(
            transform_replay(
                row,
                source_dataset="g4_train",
                source_kind="balanced_direct_anchor",
                selection_rule="first_10_sample_ids_per_24_operations",
            )
        )
    for row in clean:
        train_rows.append(
            transform_replay(
                row,
                source_dataset="g6_train",
                source_kind="network_clean_anchor",
                selection_rule="fixed_g9_clean_operation_quota",
            )
        )
    for row in recovery:
        train_rows.append(
            transform_replay(
                row,
                source_dataset="g6_train",
                source_kind="network_recovery_anchor",
                selection_rule="fixed_g9_recovery_operation_quota_all_append_file",
            )
        )

    source_counts = Counter(str(row["source_kind"]) for row in train_rows)
    if len(train_rows) != 2000 or dict(source_counts) != EXPECTED_SOURCE_COUNTS:
        raise RuntimeError(f"G9 distribution changed: {len(train_rows)} {source_counts}")
    if len({str(row["sample_id"]) for row in train_rows}) != len(train_rows):
        raise RuntimeError("G9 sample ID duplicate")
    if len({str(row["prompt_sha256"]) for row in train_rows}) != len(train_rows):
        raise RuntimeError("G9 exact prompt duplicate")

    eval_source_ids: set[str] = set()
    for path in (G4_EVAL, G6_EVAL, G8_HOLDOUT):
        for row in base.read_jsonl(path):
            eval_source_ids.add(str(row["sample_id"]))
            if row.get("source_sample_id"):
                eval_source_ids.add(str(row["source_sample_id"]))
    train_source_ids = {str(row["source_sample_id"]) for row in train_rows}
    if train_source_ids & eval_source_ids:
        raise RuntimeError("G9 train/eval source identity overlap")

    maximum_tokens = 0
    generated_rwkv_text = False
    raw_output_modified = False
    requests: list[tuple[str, str]] = []
    for row in train_rows:
        prompt = str(row["prompt"])
        target = str(row["target"])
        requirement = base.current_requirement(prompt)
        base.validate_target(harness, row)
        if row["text"] != prompt + target:
            raise RuntimeError(f"G9 text composition changed: {row['sample_id']}")
        if row["source_prompt_sha256"] != row["prompt_sha256"]:
            raise RuntimeError(f"G9 source prompt changed: {row['sample_id']}")
        if row["source_target_sha256"] != row["target_sha256"]:
            raise RuntimeError(f"G9 source target changed: {row['sample_id']}")
        total_tokens = int(row["prompt_tokens_local"]) + base.get_token_count(target)
        maximum_tokens = max(maximum_tokens, total_tokens)
        if total_tokens > CTX_LEN:
            raise RuntimeError(f"G9 target truncation: {row['sample_id']}")
        generated_rwkv_text = generated_rwkv_text or bool(row["generated_rwkv_text"])
        raw_output_modified = raw_output_modified or bool(row["raw_output_modified"])
        requests.append((str(row["sample_id"]), requirement))

    references = [
        (str(item["case_id"]), base.byte_ngrams(str(item["request"])))
        for path in LIVE_CASES
        for item in base.read_jsonl(path)
    ]
    maximum_similarity: dict[str, Any] = {
        "score": -1.0,
        "sample_id": "",
        "holdout_id": "",
    }
    for sample_id, request in requests:
        grams = base.byte_ngrams(request)
        for holdout_id, reference in references:
            score = base.cosine(grams, reference)
            if score > maximum_similarity["score"]:
                maximum_similarity = {
                    "score": score,
                    "sample_id": sample_id,
                    "holdout_id": holdout_id,
                }
    if maximum_similarity["score"] >= 0.75:
        raise RuntimeError(f"G9 live-holdout similarity failed: {maximum_similarity}")
    if generated_rwkv_text or raw_output_modified:
        raise RuntimeError("G9 source provenance changed")

    manifest: dict[str, Any] = {
        "schema_version": "rwkv-lh.executor-dataset-manifest.g9.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "stable schema contrast repair with correct-row anchors",
        "counts": {"train": len(train_rows)},
        "source_counts": dict(sorted(source_counts.items())),
        "family_counts": dict(
            sorted(Counter(str(row.get("family")) for row in train_rows).items())
        ),
        "operation_counts": dict(
            sorted(Counter(str(row["selected_operation"]) for row in train_rows).items())
        ),
        "trajectory_position_counts": dict(
            sorted(
                Counter(str(row.get("trajectory_position")) for row in train_rows).items()
            )
        ),
        "network_anchor_operation_counts": {
            "clean": CLEAN_COUNTS,
            "recovery": RECOVERY_COUNTS,
        },
        "sources": {
            str(path.relative_to(ROOT)): expected
            for path, expected in SOURCE_HASHES.items()
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "training_contract": {
            "ctx_len": CTX_LEN,
            "steps": 2000,
            "seed": 1091,
            "parent_training_state_sha256": (
                "648dcdc665ddae69f519718d9b1b6033d354255bfbeeaf9eed6d6a07088c1b78"
            ),
            "parent_vllm_state_sha256": (
                "611d9e5564ef47413c1bd1536500e987270c8303b2c87d5d54bca256d57dd68b"
            ),
            "physical_gpu": 0,
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "lr_init": "5e-7",
            "lr_final": "5e-8",
            "save_steps": list(range(250, 2001, 250)),
        },
        "validation": {
            "exact_prompt_duplicates": 0,
            "train_eval_source_identity_overlap": 0,
            "current_requirement_literal_last": True,
            "target_truncation_count": 0,
            "maximum_tokens_without_bos": maximum_tokens,
            "all_targets_current_contract_valid": True,
            "generated_rwkv_text": False,
            "raw_output_modified": False,
            "eval_prompts_or_targets_copied_into_training": False,
            "maximum_live_holdout_byte_5gram_cosine": maximum_similarity,
            "similarity_algorithm": "byte-5-gram cosine",
            "similarity_threshold_exclusive": 0.75,
        },
        "generation": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
            "frozen_g8_helper_path": str(G8_GENERATOR.relative_to(ROOT)),
            "frozen_g8_helper_sha256": G8_GENERATOR_SHA256,
            "frozen_workflow_generator_path": str(G4_GENERATOR.relative_to(ROOT)),
            "frozen_workflow_generator_sha256": SOURCE_HASHES[G4_GENERATOR],
        },
    }
    staging = base.stage_dataset(
        OUTPUT,
        train_rows,
        manifest,
        tuning=True,
        title="EXE-G9 stable schema contrast train2000",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "executor_g9_dataset_finalized",
                "train_rows": len(train_rows),
                "source_counts": dict(sorted(source_counts.items())),
                "maximum_tokens_without_bos": maximum_tokens,
                "maximum_holdout_similarity": maximum_similarity,
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
