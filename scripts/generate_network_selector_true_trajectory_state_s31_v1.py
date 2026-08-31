#!/usr/bin/env python3
"""Export frozen S30 true trajectories for S31 2.9B Selector state tuning."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1/cases.jsonl"
SOURCE_MANIFEST = SOURCE.parent / "manifest.json"
PREREGISTRATION = ROOT / (
    "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/"
    "SEL_2P9_S31_TRUE_TRAJECTORY_STATE_TUNING_PREREGISTRATION.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_state_s31_v1"
SOURCE_SHA256 = "5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305"
PREREGISTRATION_SHA256 = "4a3a2d5f91c0e9b71f491d0697b71ec79d3ddbee52f3823394dde255e87149b3"
VERSION = "rwkv-lh.network-selector.true-trajectory-state-s31.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-state-tuning-row.s31.v1"
TARGET_PREFIX = "\nSelectorLabelV3: "
CTX_LEN = 1536


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
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


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S31 state dataset")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("S31 source identity changed")
    if sha256_file(PREREGISTRATION) != PREREGISTRATION_SHA256:
        raise RuntimeError("S31 preregistration identity changed")

    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(source_rows) != 3000:
        raise RuntimeError("S31 source row count changed")

    tokenizer = RWKVTokenizer()
    exports: dict[str, list[dict[str, object]]] = {"train": [], "dev": []}
    excluded_test = 0
    prompt_digests: set[str] = set()
    for source_row in source_rows:
        split = str(source_row["split"])
        if split == "test":
            excluded_test += 1
            continue
        if split not in exports:
            raise RuntimeError(f"unknown S30 split: {split}")
        label = str(source_row["label"])
        if label not in NETWORK_EXACT_TOOL_LABELS:
            raise RuntimeError(f"unknown S30 label: {label}")

        prompt = str(source_row["bootstrap"]) + "".join(
            "\n" + str(step)
            for step in [*source_row["history_steps"], source_row["step"]]
        )
        if prompt != str(source_row["trajectory_rendered_input"]):
            raise RuntimeError(
                f"S31 persistent trajectory mismatch: {source_row['sample_id']}"
            )
        prompt_sha256 = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        if prompt_sha256 != str(source_row["trajectory_rendered_input_sha256"]):
            raise RuntimeError(
                f"S31 trajectory digest mismatch: {source_row['sample_id']}"
            )
        if prompt_sha256 in prompt_digests:
            raise RuntimeError(f"S31 duplicate trajectory: {source_row['sample_id']}")
        prompt_digests.add(prompt_sha256)

        target = TARGET_PREFIX + label
        prompt_tokens = tokenizer.encode(prompt)
        target_tokens = tokenizer.encode(target)
        text_tokens = tokenizer.encode(prompt + target)
        if text_tokens != prompt_tokens + target_tokens:
            raise RuntimeError(
                f"S31 target boundary is not additive: {source_row['sample_id']}"
            )
        if 1 + len(text_tokens) > CTX_LEN + 1:
            raise RuntimeError(
                f"S31 target would be truncated: {source_row['sample_id']}"
            )

        exports[split].append(
            {
                "schema_version": ROW_SCHEMA,
                "dataset_version": VERSION,
                "sample_id": str(source_row["sample_id"]).replace(
                    "NETSEL-S30-", "NETSEL-S31-STATE-", 1
                ),
                "source_sample_id": source_row["sample_id"],
                "source_split": split,
                "semantic_family_id": source_row["semantic_family_id"],
                "lexical_family_id": source_row["lexical_family_id"],
                "trajectory_family_id": source_row["trajectory_family_id"],
                "entity_family_id": source_row["entity_family_id"],
                "label": label,
                "language": source_row["language"],
                "phase": source_row["phase"],
                "stage_group": source_row["stage_group"],
                "decision_index": source_row["decision_index"],
                "has_future_tool_distractor": source_row[
                    "has_future_tool_distractor"
                ],
                "prompt": prompt,
                "prompt_sha256": prompt_sha256,
                "target": target,
                "text": prompt + target,
                "prompt_tokens_including_bos": 1 + len(prompt_tokens),
                "target_tokens": len(target_tokens),
                "text_tokens_including_bos": 1 + len(text_tokens),
                "loss_mask": "target_suffix",
                "jsonl_bos_token_id": 0,
                "persistent_history_replayed": True,
                "contains_parameter_schemas": False,
                "contains_full_tool_results": False,
                "contains_executor_text": False,
                "generated_rwkv_text": False,
            }
        )

    expected_counts = {"train": 2000, "dev": 500}
    if {split: len(rows) for split, rows in exports.items()} != expected_counts:
        raise RuntimeError("S31 frozen split counts changed")
    if excluded_test != 500:
        raise RuntimeError("S31 blind exclusion count changed")
    expected_label_counts = {
        "train": Counter({label: 80 for label in NETWORK_EXACT_TOOL_LABELS}),
        "dev": Counter({label: 20 for label in NETWORK_EXACT_TOOL_LABELS}),
    }
    label_counts = {
        split: Counter(str(row["label"]) for row in rows)
        for split, rows in exports.items()
    }
    if label_counts != expected_label_counts:
        raise RuntimeError("S31 label balance changed")
    language_counts = {
        split: Counter(str(row["language"]) for row in rows)
        for split, rows in exports.items()
    }
    if language_counts != {
        "train": Counter({"en": 1000, "zh": 1000}),
        "dev": Counter({"en": 250, "zh": 250}),
    }:
        raise RuntimeError("S31 language balance changed")
    train_families = {
        str(row["semantic_family_id"]) for row in exports["train"]
    }
    dev_families = {str(row["semantic_family_id"]) for row in exports["dev"]}
    if train_families & dev_families:
        raise RuntimeError("S31 semantic families cross train/dev")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=".rwkv_lh_network_selector_s31.", dir=OUTPUT.parent
        )
    )
    paths = {
        split: staging
        / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in exports
    }
    for split, path in paths.items():
        write_jsonl(path, exports[split])

    all_rows = [row for rows in exports.values() for row in rows]
    prompt_lengths = [
        int(row["prompt_tokens_including_bos"]) for row in all_rows
    ]
    text_lengths = [int(row["text_tokens_including_bos"]) for row in all_rows]
    target_lengths = [int(row["target_tokens"]) for row in all_rows]
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": (
            "S31 production-shaped true-trajectory 2.9B Selector initial-WKV "
            "state tuning"
        ),
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "manifest_sha256": sha256_file(SOURCE_MANIFEST),
            "rows": len(source_rows),
            "version": source_manifest["dataset_version"],
        },
        "counts": {
            "train": 2000,
            "dev": 500,
            "test_excluded": excluded_test,
        },
        "label_counts": {
            split: dict(sorted(counts.items()))
            for split, counts in label_counts.items()
        },
        "language_counts": {
            split: dict(sorted(counts.items()))
            for split, counts in language_counts.items()
        },
        "target_prefix": TARGET_PREFIX,
        "training_contract": {
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN,
            "epoch_steps": 2000,
            "epoch_count": 1,
            "step_save": 500,
            "seed": 1031,
            "persistent_history_replayed": True,
            "parent_state": "zero",
        },
        "validation": {
            "exact_prompt_duplicates": 0,
            "train_dev_semantic_family_overlap": 0,
            "all_25_labels_balanced_in_train_dev": True,
            "languages_balanced_in_train_dev": True,
            "minimum_prompt_tokens_including_bos": min(prompt_lengths),
            "maximum_prompt_tokens_including_bos": max(prompt_lengths),
            "minimum_target_tokens": min(target_lengths),
            "maximum_target_tokens": max(target_lengths),
            "minimum_text_tokens_including_bos": min(text_lengths),
            "maximum_text_tokens_including_bos": max(text_lengths),
            "tokenization_boundary_additive": True,
            "target_truncation_count": 0,
            "generated_rwkv_text_count": 0,
            "contains_parameter_schemas_count": 0,
            "contains_full_tool_results_count": 0,
            "contains_executor_text_count": 0,
            "source_holdout_similarity": source_manifest["validation"][
                "holdout_similarity"
            ],
        },
        "optimizer_rows": "train_only",
        "dev_optimizer_use": False,
        "s30_test_used": False,
        "s28_used_for_state_training": False,
        "s23_ecra_used": False,
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "files": {
            path.name: {
                "rows": len(exports[split]),
                "sha256": sha256_file(path),
            }
            for split, path in paths.items()
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# True-trajectory Selector state S31 v1\n\n"
        "- 仅使用冻结 S30 train 的 2000 条全 25 类均衡真实轨迹优化 2.9B "
        "Selector 初始 WKV state。\n"
        "- S30 dev 只用于本地开发消融，S30 test、S28、S23/ECRA、13.3B "
        "Executor 与 Harness 均未进入 state 训练。\n"
        "- target 只监督精确类别后缀；未生成、修改、过滤或删除任何 RWKV "
        "原始输出。\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
