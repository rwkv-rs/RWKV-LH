#!/usr/bin/env python3
"""Project frozen S3 rows onto the exact current direct-Harness Selector input."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_STAGE_PROJECTION_VERSION,
    render_selector_stage_objective,
)


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_role_normalized_s3_v1/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S24_CURRENT_HARNESS_2K_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_training_s24_v1"
SOURCE_SHA256 = "34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
VERSION = "rwkv-lh.network-selector.current-harness-training-s24.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-current-harness-training-row.s24.v1"


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


def parse_source_input(row: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    rendered = str(row["rendered_input"])
    bootstrap_text, step_text = rendered.split("\nSelectorStepV2: ", 1)
    if not bootstrap_text.startswith("SelectorBootstrapV2: "):
        raise RuntimeError(f"invalid S3 bootstrap: {row['sample_id']}")
    return (
        json.loads(bootstrap_text.removeprefix("SelectorBootstrapV2: ")),
        json.loads(step_text),
    )


def current_projection(row: dict[str, object]) -> dict[str, object]:
    bootstrap, source_step = parse_source_input(row)
    source_progress = dict(source_step["progress"])
    succeeded = [str(item) for item in source_progress["succeeded_operations"]]
    failed = [str(item) for item in source_progress["failed_operations"]]
    source_action_index = int(source_progress["action_index"])

    latest_operation = failed[-1] if failed else (succeeded[-1] if succeeded else "")
    if source_action_index > 0 and latest_operation:
        action_index = source_action_index
        latest_failed = bool(failed)
        projected_succeeded = () if latest_failed else (latest_operation,)
        projected_failed = (latest_operation,) if latest_failed else ()
        latest_fact: dict[str, object] | None = {
            "sequence": action_index,
            "operation": latest_operation,
            "success": not latest_failed,
            "outcome_type": "failed" if latest_failed else "success",
        }
        normalization = "latest_failed" if latest_failed else "latest_succeeded"
    else:
        action_index = 0
        projected_succeeded = ()
        projected_failed = ()
        latest_fact = None
        normalization = (
            "unobservable_continuation_reset_to_first"
            if source_action_index > 0
            else "first"
        )

    selector_input = NetworkSelectorInput.create(
        task_request=str(bootstrap["task_request"]),
        stage_objective=render_selector_stage_objective(latest_fact),
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=action_index,
            action_index=action_index,
            succeeded_operations=projected_succeeded,
            failed_operations=projected_failed,
            protocol_rejection_count=int(source_progress["protocol_rejection_count"]),
        ),
    )
    value = selector_input.to_dict()
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": VERSION,
        "sample_id": str(row["sample_id"]).replace("NETSEL-S3-", "NETSEL-S24-", 1),
        "split": str(row["split"]),
        "label": str(row["label"]),
        "language": str(row["language"]),
        "semantic_family_id": str(row["semantic_family_id"]),
        "selector_input": value,
        "selector_input_sha256": canonical_digest(value),
        "bootstrap": selector_input.render_bootstrap(),
        "step": selector_input.render_step(),
        "rendered_input": selector_input.render(),
        "projection_version": SELECTOR_STAGE_PROJECTION_VERSION,
        "progress_normalization": normalization,
        "source_s3_sample_id": str(row["sample_id"]),
        "source_progress_sha256": canonical_digest(source_progress),
        "generated_rwkv_text": False,
        "contains_full_tool_results": False,
        "contains_tool_schemas": False,
        "contains_executor_text": False,
    }


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S24 current-Harness dataset")
    if sha256_file(SOURCE) != SOURCE_SHA256 or sha256_file(ECRA) != ECRA_SHA256:
        raise RuntimeError("S24 frozen source identity changed")
    if not PROTOCOL.is_file():
        raise RuntimeError("S24 preregistration is missing")

    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    rows = [current_projection(row) for row in source_rows]
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter({"train": 2000, "dev": 276, "test": 250}):
        raise RuntimeError("S24 split counts changed")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("S24 sample IDs are not unique")
    if len({str(row["rendered_input"]) for row in rows}) != len(rows):
        raise RuntimeError("S24 contains exact rendered-input duplicates")
    families = {
        split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if any(families[left] & families[right] for left, right in (("train", "dev"), ("train", "test"), ("dev", "test"))):
        raise RuntimeError("S24 semantic families cross splits")
    label_counts = {
        split: Counter(str(row["label"]) for row in rows if row["split"] == split)
        for split in ("train", "dev", "test")
    }
    if any(set(counts) != set(NETWORK_EXACT_TOOL_LABELS) for counts in label_counts.values()):
        raise RuntimeError("S24 does not retain all labels in every split")

    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(str(case["case_id"]), byte_ngrams(str(case["instruction"]))) for case in holdout]
    maximum: dict[str, object] = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        grams = byte_ngrams(str(row["selector_input"]["task_request"]))
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > float(maximum["score"]):
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if float(maximum["score"]) >= 0.75:
        raise RuntimeError(f"S24 ECRA similarity gate failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s24.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, rows)
    normalizations = Counter(str(row["progress_normalization"]) for row in rows)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "2.9B exact-tool Selector training at the current direct-Harness boundary",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "counts": dict(sorted(split_counts.items())),
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "projection": {
            "version": SELECTOR_STAGE_PROJECTION_VERSION,
            "stage_role": "work",
            "normalization_counts": dict(sorted(normalizations.items())),
            "maximum_delta_operations": 1,
            "completed_stage_count_equals_action_index": True,
        },
        "generated_rwkv_text_count": 0,
        "contains_full_tool_results": False,
        "contains_tool_schemas": False,
        "contains_executor_text": False,
        "validation": {
            "exact_rendered_input_duplicates": 0,
            "cross_split_family_overlap": 0,
            "all_labels_in_every_split": True,
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "compared_field": "selector_input.task_request",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": ECRA_SHA256,
            },
        },
        "sources": {
            "s3_cases": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "ecra120_evaluation_only": {"path": str(ECRA.relative_to(ROOT)), "sha256": ECRA_SHA256},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run python {Path(__file__).resolve()}",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve())},
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}},
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# Current direct-Harness Selector training S24 v1\n\n"
        "- 训练/开发/测试分别为 2000/276/250，沿用 S3 冻结标签与语义族拆分。\n"
        "- 输入严格使用当前 `LongHorizonModel` 的 SelectorBootstrapV2 + CurrentDirectStageV1 紧凑投影。\n"
        "- 每次 continuation 至多投影一个最新动作；不含工具参数 schema、完整结果或 Executor 文本。\n"
        "- S23/ECRA 只用于冻结后外部评估，未进入训练。来源摘要、生成命令与验证指标见 manifest。\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
