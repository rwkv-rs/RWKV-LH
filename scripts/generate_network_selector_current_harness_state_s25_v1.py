#!/usr/bin/env python3
"""Export exact S24 current-Harness rows for 2.9B Selector state tuning."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_training_s24_v1/cases.jsonl"
SOURCE_MANIFEST = SOURCE.parent / "manifest.json"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S25_CURRENT_HARNESS_STATE_TUNING_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_state_s25_v1"
SOURCE_SHA256 = "0349d9df08dd3e28418b5bc15415646d50a7d38c4c3d29e489c633392dba7601"
VERSION = "rwkv-lh.network-selector.current-harness-state-s25.v1"
TARGET_PREFIX = "\nSelectorLabelV2: "
CTX_LEN = 1216


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S25 state dataset")
    if sha256_file(SOURCE) != SOURCE_SHA256 or not PROTOCOL.is_file():
        raise RuntimeError("S25 source identity changed or preregistration is missing")
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    tokenizer = RWKVTokenizer()
    exports: dict[str, list[dict[str, object]]] = {"train": [], "dev": []}
    excluded_test = 0
    for row in source_rows:
        split = str(row["split"])
        if split == "test":
            excluded_test += 1
            continue
        if split not in exports:
            raise RuntimeError(f"unknown S24 split: {split}")
        label = str(row["label"])
        if label not in NETWORK_EXACT_TOOL_LABELS:
            raise RuntimeError(f"unknown S24 label: {label}")
        prompt = str(row["rendered_input"])
        target = TARGET_PREFIX + label
        prompt_tokens = tokenizer.encode(prompt)
        target_tokens = tokenizer.encode(target)
        text_tokens = tokenizer.encode(prompt + target)
        if text_tokens != prompt_tokens + target_tokens:
            raise RuntimeError(f"S25 target boundary is not additive: {row['sample_id']}")
        if 1 + len(text_tokens) > CTX_LEN + 1:
            raise RuntimeError(f"S25 target would be truncated: {row['sample_id']}")
        exports[split].append({
            "schema_version": "rwkv-lh.network-selector-state-tuning-row.s25.v1",
            "dataset_version": VERSION,
            "sample_id": str(row["sample_id"]).replace("NETSEL-S24-", "NETSEL-S25-STATE-", 1),
            "source_sample_id": row["sample_id"],
            "source_split": split,
            "semantic_family_id": row["semantic_family_id"],
            "label": label,
            "prompt": prompt,
            "target": target,
            "text": prompt + target,
            "prompt_tokens_including_bos": 1 + len(prompt_tokens),
            "target_tokens": len(target_tokens),
            "text_tokens_including_bos": 1 + len(text_tokens),
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "generated_rwkv_text": False,
        })
    if {split: len(rows) for split, rows in exports.items()} != {"train": 2000, "dev": 276} or excluded_test != 250:
        raise RuntimeError("S25 frozen split counts changed")
    label_counts = {split: Counter(str(row["label"]) for row in rows) for split, rows in exports.items()}
    if any(set(counts) != set(NETWORK_EXACT_TOOL_LABELS) for counts in label_counts.values()):
        raise RuntimeError("S25 does not retain all labels in train/dev")
    if len({str(row["prompt"]) for rows in exports.values() for row in rows}) != 2276:
        raise RuntimeError("S25 train/dev contains exact prompt duplicates")
    families = {split: {str(row["semantic_family_id"]) for row in rows} for split, rows in exports.items()}
    if families["train"] & families["dev"]:
        raise RuntimeError("S25 semantic families cross train/dev")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s25.", dir=OUTPUT.parent))
    paths = {split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl" for split in exports}
    for split, path in paths.items():
        write_jsonl(path, exports[split])
    lengths = [int(row["text_tokens_including_bos"]) for rows in exports.values() for row in rows]
    prompt_lengths = [int(row["prompt_tokens_including_bos"]) for rows in exports.values() for row in rows]
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "S25 current-Harness 2.9B Selector initial-WKV state ablation",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256, "rows": len(source_rows)},
        "counts": {"train": 2000, "dev": 276, "test_excluded": 250},
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "target_prefix": TARGET_PREFIX,
        "training_contract": {
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN,
            "epoch_steps": 2000,
            "epoch_count": 1,
            "step_save": 500,
            "seed": 863,
        },
        "validation": {
            "exact_prompt_duplicates": 0,
            "train_dev_family_overlap": 0,
            "all_labels_in_train_dev": True,
            "minimum_prompt_tokens_including_bos": min(prompt_lengths),
            "maximum_prompt_tokens_including_bos": max(prompt_lengths),
            "minimum_text_tokens_including_bos": min(lengths),
            "maximum_text_tokens_including_bos": max(lengths),
            "tokenization_boundary_additive": True,
            "target_truncation_count": 0,
            "holdout_similarity": source_manifest["validation"]["holdout_similarity"],
            "generated_rwkv_text_count": 0,
        },
        "s24_test_used": False,
        "s23_used": False,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run python {Path(__file__).resolve()}",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve())},
        "files": {path.name: {"rows": len(exports[split]), "sha256": sha256_file(path)} for split, path in paths.items()},
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (staging / "README.md").write_text(
        "# Current-Harness Selector state S25 v1\n\n"
        "- 仅使用 S24 train 2000 条做 2.9B Selector 初始 WKV state tuning；dev 276 只验证，test 250 与 S23 全部排除。\n"
        "- prompt 是线上同字节 BootstrapV2 + StepV2，target 仅监督标签后缀。\n"
        "- 不训练 13.3B Executor，不含 schema、完整结果或 Executor 文本。来源、摘要、token 上限与命令见 manifest。\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
