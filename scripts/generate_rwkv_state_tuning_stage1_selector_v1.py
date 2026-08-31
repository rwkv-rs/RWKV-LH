"""Build the Stage-1 selector-identity continuation corpus from Round1 residuals."""

from __future__ import annotations

import hashlib
import json
import shutil
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_action_state_tuning_round1_2k_v1"
SOURCE_EVAL = (
    ROOT
    / "data/experiments/RWKV_ACTION_STATE_TUNING_ROUND1_2K_V1_20260826"
    / "tuned_live_dev200_repeat.json"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1"
PREREGISTRATION = (
    ROOT
    / "data/experiments/RWKV_STATE_TUNING_THREE_STAGE_V1_20260826"
    / "PREREGISTRATION.md"
)
VERSION = "rwkv-lh.state-tuning.stage1-selector.v1"
FAMILY_QUOTAS = {
    "no_progress_recovery": 28,
    "observation_binding": 25,
    "coverage_focus": 22,
    "completion_evidence": 19,
    "privacy_gate": 6,
}
OBSERVED_WRONG_OUTER_FUNCTIONS = {
    "list_directory": 41,
    "read_file": 18,
    "read_json": 15,
    "connector_lookup": 3,
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def write_json(path: Path, value: Any) -> None:
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    path.write_text(
        "".join(
            json.dumps(dict(row), ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
    )


def evenly_spaced(values: list[str], count: int) -> list[str]:
    if count < 1 or count > len(values):
        raise ValueError("invalid deterministic family quota")
    selected = [values[((2 * index + 1) * len(values)) // (2 * count)] for index in range(count)]
    if len(set(selected)) != count:
        raise RuntimeError("even family selection produced a duplicate")
    return selected


def selector_rows(split: str) -> list[dict[str, Any]]:
    rows = read_jsonl(SOURCE / f"stage_sft.{split}.jsonl")
    selected = [row for row in rows if row.get("stage") == "selector"]
    for row in selected:
        if parse_tool_selection(str(row["target"])) != row["target_operation"]:
            raise RuntimeError(f"selector target contract failed: {row['trajectory_id']}")
        if not str(row["prompt"]).endswith("Assistant: ```json\n"):
            raise RuntimeError(f"selector prompt boundary changed: {row['trajectory_id']}")
        if "Controller-selected operation contract" in str(row["prompt"]):
            raise RuntimeError(f"direct disclosure leaked into selector: {row['trajectory_id']}")
    return selected


def select_train(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    family_cluster: dict[str, str] = {}
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        family = str(row["semantic_family_id"])
        cluster = str(row["failure_cluster"])
        existing = family_cluster.setdefault(family, cluster)
        if existing != cluster:
            raise RuntimeError("one semantic family crosses failure clusters")
        by_family[family].append(row)
    if any(len(value) != 5 for value in by_family.values()):
        raise RuntimeError("Stage 1 requires complete five-variant train families")

    selected_families: set[str] = set()
    for cluster, quota in FAMILY_QUOTAS.items():
        candidates = sorted(
            family for family, value in family_cluster.items() if value == cluster
        )
        selected_families.update(evenly_spaced(candidates, quota))
    if len(selected_families) != 100:
        raise RuntimeError("Stage 1 must select exactly 100 semantic families")
    selected = [
        row for row in rows if str(row["semantic_family_id"]) in selected_families
    ]
    if len(selected) != 500:
        raise RuntimeError("Stage 1 must select exactly 500 training rows")
    return selected


def training_row(row: Mapping[str, Any]) -> dict[str, str]:
    prompt = str(row["prompt"])
    target = str(row["target"])
    return {"prompt": prompt, "target": target, "text": prompt + target}


def main() -> int:
    if OUTPUT.exists():
        shutil.rmtree(OUTPUT)
    OUTPUT.mkdir(parents=True)

    source_manifest = json.loads((SOURCE / "manifest.json").read_text(encoding="utf-8"))
    if not source_manifest.get("training_ready"):
        raise RuntimeError("Round1 source dataset is not training-ready")
    if not source_manifest.get("remote_tokenizer_validated"):
        raise RuntimeError("Round1 source dataset lacks remote tokenizer validation")

    train = select_train(selector_rows("train"))
    dev = selector_rows("dev")
    if len(dev) != 79:
        raise RuntimeError("frozen selector dev must contain 79 rows")
    train_families = {str(row["semantic_family_id"]) for row in train}
    dev_families = {str(row["semantic_family_id"]) for row in dev}
    if train_families & dev_families:
        raise RuntimeError("train/dev semantic family overlap")
    prompt_hashes = [hashlib.sha256(str(row["prompt"]).encode()).hexdigest() for row in train + dev]
    if len(prompt_hashes) != len(set(prompt_hashes)):
        raise RuntimeError("exact prompt duplicate detected")

    parent_eval = json.loads(SOURCE_EVAL.read_text(encoding="utf-8"))
    parent_selector = [row for row in parent_eval["results"] if row["stage"] == "selector"]
    if len(parent_selector) != 79:
        raise RuntimeError("parent selector residual count changed")
    observed_counts = Counter()
    residual_rows = []
    for row in parent_selector:
        raw = str(row.get("raw_output") or "")
        actual_function = ""
        try:
            payload = json.loads(raw.strip().removeprefix("```json").removesuffix("```").strip())
            if isinstance(payload, dict):
                actual_function = str(payload.get("function") or "")
        except json.JSONDecodeError:
            pass
        if actual_function and actual_function != "select_tool":
            observed_counts[actual_function] += 1
        residual_rows.append(
            {
                "trajectory_id": row["trajectory_id"],
                "expected_inner_operation": row["expected_operation"],
                "actual_outer_function": actual_function,
                "error": row.get("error", ""),
                "raw_output_sha256": hashlib.sha256(raw.encode()).hexdigest(),
            }
        )
    if dict(observed_counts) != OBSERVED_WRONG_OUTER_FUNCTIONS:
        raise RuntimeError(
            "observed parent selector failures changed: "
            f"expected={OBSERVED_WRONG_OUTER_FUNCTIONS} actual={dict(observed_counts)}"
        )

    write_jsonl(OUTPUT / "stage_sft.train.jsonl", train)
    write_jsonl(OUTPUT / "stage_sft.dev.jsonl", dev)
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.train.requires_target_suffix.jsonl",
        (training_row(row) for row in train),
    )
    write_jsonl(
        OUTPUT / "rwkv_state_tuning.dev.requires_target_suffix.jsonl",
        (training_row(row) for row in dev),
    )
    write_jsonl(OUTPUT / "observed_parent_selector_residuals.jsonl", residual_rows)
    write_json(
        OUTPUT / "hard_negative_registry.json",
        {
            "schema_version": "rwkv-lh.selector-outer-hard-negative-registry.v1",
            "source": str(SOURCE_EVAL.relative_to(ROOT)),
            "wrong_outer_function_counts": OBSERVED_WRONG_OUTER_FUNCTIONS,
            "rule": "A direct concrete operation at a selector boundary is negative even when its inner operation would have been correct.",
        },
    )
    readme = (
        "# RWKV-LH Stage 1 selector state tuning\n\n"
        "This is a 500-row selector-only continuation corpus derived from the frozen "
        "Round1 residual. It teaches outer protocol identity (`select_tool`), not generic "
        "task execution. The 79-row dev split is frozen and disjoint. Training requires "
        "RWKV-PEFT `loss_mask=target_suffix`.\n"
    )
    (OUTPUT / "README.md").write_text(readme, encoding="utf-8")

    files = {}
    for path in sorted(OUTPUT.iterdir()):
        if path.name == "manifest.json" or not path.is_file():
            continue
        files[path.name] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "artifact_kind": "residual_selector_protocol_identity_state_tuning",
        "purpose": "Continue Round1 state only on the observed selector outer-function failure.",
        "training_ready": True,
        "local_validation_complete": True,
        "remote_tokenizer_validated": False,
        "strong_model_as_label_source": False,
        "live_network_used": False,
        "loss_mask": "target_suffix",
        "counts": {
            "train": len(train),
            "dev": len(dev),
            "train_semantic_families": len(train_families),
            "dev_semantic_families": len(dev_families),
            "observed_parent_selector_rows": len(parent_selector),
            "observed_wrong_outer_calls": sum(OBSERVED_WRONG_OUTER_FUNCTIONS.values()),
        },
        "train_cluster_counts": dict(sorted(Counter(row["failure_cluster"] for row in train).items())),
        "train_target_operation_counts": dict(sorted(Counter(row["target_operation"] for row in train).items())),
        "dev_target_operation_counts": dict(sorted(Counter(row["target_operation"] for row in dev).items())),
        "validation": {
            "target_outer_function": "select_tool",
            "target_parse_rate": 1.0,
            "exact_prompt_duplicate_count": 0,
            "train_dev_family_overlap_count": 0,
            "complete_train_family_size": 5,
            "inherited_holdout_contamination": source_manifest["validation"]["contamination"],
        },
        "parent": {
            "dataset_manifest": str((SOURCE / "manifest.json").relative_to(ROOT)),
            "dataset_manifest_sha256": sha256(SOURCE / "manifest.json"),
            "residual_eval": str(SOURCE_EVAL.relative_to(ROOT)),
            "residual_eval_sha256": sha256(SOURCE_EVAL),
            "state_checkpoint_sha256": "601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5",
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": sha256(PREREGISTRATION),
        },
        "generation": "uv run python scripts/generate_rwkv_state_tuning_stage1_selector_v1.py",
        "files": files,
    }
    write_json(OUTPUT / "manifest.json", manifest)
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
