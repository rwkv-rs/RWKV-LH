#!/usr/bin/env python3
"""Build the failure-grounded 2K corpus for NET-SEL-2P9-S2."""

from __future__ import annotations

import hashlib
import json
import math
import re
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


ROOT = Path(__file__).resolve().parents[1]
LEGACY = ROOT / "data/datasets/rwkv_lh_state_tuning_stage3_natural_route_stop_v1"
RETENTION = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_residual_s2_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S2_PREREGISTRATION.md"
VERSION = "rwkv-lh.network-selector.residual-s2.v1"
TARGET_PREFIX = "\nSelectorLabelV2: "
TASK_STATE_PATTERN = re.compile(
    r"User: Task state: (\{.*?\})\n\nAvailable operation menu", re.DOTALL
)
EXPECTED_SOURCE_SHA = {
    "legacy_train": "d09e7129781d15187785ca0740108884b263a5a185a9f53cab763f6449525a41",
    "legacy_dev": "8d7e8c41d7ae18a1fd3cf7cd776a97d98304270dddfc2e62407805d75f50c76f",
    "retention": "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc",
    "ecra": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    value = text.encode("utf-8")
    return Counter(value[index : index + n] for index in range(max(0, len(value) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return dot / (left_norm * right_norm)


def parse_legacy(row: dict[str, Any], split: str, index: int) -> dict[str, Any]:
    match = TASK_STATE_PATTERN.search(str(row["prompt"]))
    if match is None:
        raise RuntimeError(f"legacy task state is missing: {row['trajectory_id']}")
    state = json.loads(match.group(1))
    request = str(state.get("immutable_request") or "").strip()
    if not request:
        raise RuntimeError(f"legacy immutable request is missing: {row['trajectory_id']}")
    succeeded: list[str] = []
    failed: list[str] = []
    for action in list(state.get("recent_exact_action_records") or ())[-8:]:
        operation = str(action.get("operation") or "")
        if operation not in NETWORK_EXACT_TOOL_LABELS or operation in {"ABSTAIN", "final_answer"}:
            continue
        result = action.get("result") or {}
        (succeeded if result.get("success") is True else failed).append(operation)
    progress = NetworkSelectorProgress(
        completed_stage_count=max(0, int(row.get("turn_index") or 0)),
        action_index=len(succeeded) + len(failed),
        succeeded_operations=tuple(succeeded),
        failed_operations=tuple(failed),
        protocol_rejection_count=0,
    )
    selector_input = NetworkSelectorInput.create(
        task_request=request,
        stage_objective=request,
        stage_role=str(row["failure_cluster"]),
        progress=progress,
    )
    label = str(row["target_operation"])
    if label not in NETWORK_EXACT_TOOL_LABELS:
        raise RuntimeError(f"legacy target is outside v2 labels: {label}")
    return {
        "schema_version": "rwkv-lh.network-selector-residual-row.s2.v1",
        "dataset_version": VERSION,
        "sample_id": f"NETSEL-S2-LEGACY-{split.upper()}-{index:04d}",
        "semantic_family_id": str(row["semantic_family_id"]),
        "split": split,
        "label": label,
        "failure_cluster": str(row["failure_cluster"]),
        "language": str(row.get("language") or "unknown"),
        "stage_objective": request,
        "rendered_input": selector_input.render(),
        "selector_input_sha256": canonical_digest(selector_input.to_dict()),
        "source": {
            "kind": "stage3_failure_grounded_projection",
            "trajectory_id": str(row["trajectory_id"]),
            "source_seed_id": str(row["source_seed_id"]),
            "controller_rendered": row.get("controller_rendered") is True,
        },
        "generated_rwkv_text": False,
    }


def retention_rows(source: list[dict[str, Any]], split: str, count: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in source:
        if row["split"] == split:
            by_label[str(row["label"])].append(row)
    for label in NETWORK_EXACT_TOOL_LABELS:
        candidates = by_label[label]
        if len(candidates) < count:
            raise RuntimeError(f"not enough retention rows for {split}/{label}")
        for index, row in enumerate(candidates[:count]):
            rendered = str(row["rendered_input"])
            step = json.loads(rendered.split("\nSelectorStepV2: ", 1)[1])
            selected.append(
                {
                    "schema_version": "rwkv-lh.network-selector-residual-row.s2.v1",
                    "dataset_version": VERSION,
                    "sample_id": f"NETSEL-S2-RET-{split.upper()}-{label.upper()}-{index:03d}",
                    "semantic_family_id": f"RET-{row['semantic_family_id']}",
                    "split": split,
                    "label": label,
                    "failure_cluster": "class_retention",
                    "language": "en",
                    "stage_objective": str(step["stage_objective"]),
                    "rendered_input": rendered,
                    "selector_input_sha256": str(row["selector_input_sha256"]),
                    "source": {
                        "kind": "v2_4_class_retention",
                        "sample_id": str(row["sample_id"]),
                    },
                    "generated_rwkv_text": False,
                }
            )
    return selected


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    paths = {
        "legacy_train": LEGACY / "stage_sft.train.jsonl",
        "legacy_dev": LEGACY / "stage_sft.dev.jsonl",
        "retention": RETENTION,
        "ecra": ECRA,
    }
    for name, path in paths.items():
        actual = sha256_file(path)
        if actual != EXPECTED_SOURCE_SHA[name]:
            raise RuntimeError(f"source SHA mismatch for {name}: {actual}")
    if not PROTOCOL.is_file():
        raise FileNotFoundError(PROTOCOL)
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to replace existing dataset: {OUTPUT}")

    legacy_train = [json.loads(line) for line in paths["legacy_train"].read_text(encoding="utf-8").splitlines()]
    legacy_dev = [json.loads(line) for line in paths["legacy_dev"].read_text(encoding="utf-8").splitlines()]
    retention = [json.loads(line) for line in RETENTION.read_text(encoding="utf-8").splitlines()]
    rows = {
        "train": [parse_legacy(row, "train", index) for index, row in enumerate(legacy_train)],
        "dev": [parse_legacy(row, "dev", index) for index, row in enumerate(legacy_dev)],
        "test": [],
    }
    rows["train"].extend(retention_rows(retention, "train", 24))
    rows["dev"].extend(retention_rows(retention, "dev", 4))
    rows["test"].extend(retention_rows(retention, "test", 10))
    expected_counts = {"train": 2000, "dev": 276, "test": 250}
    if {split: len(value) for split, value in rows.items()} != expected_counts:
        raise RuntimeError("S2 split counts changed")

    all_rows = [row for split in ("train", "dev", "test") for row in rows[split]]
    if len({row["sample_id"] for row in all_rows}) != len(all_rows):
        raise RuntimeError("S2 sample IDs are not unique")
    if len({row["rendered_input"] for row in all_rows}) != len(all_rows):
        raise RuntimeError("S2 contains exact rendered-input duplicates")
    families = {split: {row["semantic_family_id"] for row in values} for split, values in rows.items()}
    if any(families[left] & families[right] for left, right in (("train", "dev"), ("train", "test"), ("dev", "test"))):
        raise RuntimeError("S2 semantic families cross splits")
    label_counts = {split: Counter(row["label"] for row in values) for split, values in rows.items()}
    if any(set(counts) != set(NETWORK_EXACT_TOOL_LABELS) for counts in label_counts.values()):
        raise RuntimeError("S2 does not retain all 25 labels in every split")
    clusters = Counter(row["failure_cluster"] for row in rows["train"])
    expected_clusters = Counter({
        "stable_selector_replay": 500,
        "natural_connector": 400,
        "ordinary_web": 100,
        "mixed_local_first": 200,
        "privacy_local_first": 200,
        "class_retention": 600,
    })
    if clusters != expected_clusters:
        raise RuntimeError(f"S2 train cluster counts changed: {clusters}")

    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(case["case_id"], byte_ngrams(case["instruction"])) for case in holdout]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in all_rows:
        grams = byte_ngrams(row["stage_objective"])
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > maximum["score"]:
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if maximum["score"] >= 0.75:
        raise RuntimeError(f"S2 holdout similarity gate failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_residual_s2_v1.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, all_rows)
    state_files = {}
    for split in ("train", "dev"):
        state_rows = []
        for row in rows[split]:
            target = TARGET_PREFIX + row["label"]
            state_rows.append({
                "schema_version": "rwkv-lh.network-selector-state-tuning-row.s2.v1",
                "dataset_version": VERSION,
                "source_sample_id": row["sample_id"],
                "source_split": split,
                "label": row["label"],
                "prompt": row["rendered_input"],
                "target": target,
                "text": row["rendered_input"] + target,
                "loss_mask": "target_suffix",
                "jsonl_bos_token_id": 0,
                "generated_rwkv_text": False,
            })
        path = staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        write_jsonl(path, state_rows)
        state_files[path.name] = {"rows": len(state_rows), "sha256": sha256_file(path)}

    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S2 failure-grounded residual state/head training",
        "counts": expected_counts,
        "train_cluster_counts": dict(sorted(clusters.items())),
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "language_counts": {split: dict(sorted(Counter(row["language"] for row in values).items())) for split, values in rows.items()},
        "natural_connector_cluster_to_other_train": "400:1600",
        "connector_label_to_other_train": "474:1526",
        "loss_mask": "target_suffix",
        "jsonl_bos_token_id": 0,
        "generated_rwkv_text_count": 0,
        "validation": {
            "exact_rendered_input_duplicates": 0,
            "train_dev_family_overlap": 0,
            "all_labels_in_every_split": True,
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": EXPECTED_SOURCE_SHA["ecra"],
            },
        },
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": EXPECTED_SOURCE_SHA[name]} for name, path in paths.items()},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {
            "cases.jsonl": {"rows": len(all_rows), "sha256": sha256_file(cases_path)},
            **state_files,
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
