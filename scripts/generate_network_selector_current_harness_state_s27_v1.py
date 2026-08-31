#!/usr/bin/env python3
"""Export exact S26 persistent trajectories for 2.9B Selector state tuning."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_identifiable_s26_v1/cases.jsonl"
SOURCE_MANIFEST = SOURCE.parent / "manifest.json"
PROTOCOL = ROOT / (
    "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/"
    "SEL_2P9_S27_CURRENT_HARNESS_IDENTIFIABLE_STATE_TUNING_PREREGISTRATION.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_state_s27_v1"
SOURCE_SHA256 = "4a01c16a2e320e7754529544ea0299e5abdd6015b0b079c78c1f7d9ab24e4465"
VERSION = "rwkv-lh.network-selector.current-harness-state-s27.v1"
TARGET_PREFIX = "\nSelectorLabelV2: "
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
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S27 state dataset")
    if sha256_file(SOURCE) != SOURCE_SHA256 or not PROTOCOL.is_file():
        raise RuntimeError("S27 source identity changed or preregistration is missing")
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
            raise RuntimeError(f"unknown S26 split: {split}")
        label = str(row["label"])
        if label not in NETWORK_EXACT_TOOL_LABELS:
            raise RuntimeError(f"unknown S26 label: {label}")
        prompt = str(row["trajectory_rendered_input"])
        expected_prompt = str(row["bootstrap"]) + "".join(
            "\n" + str(step) for step in [*row["history_steps"], row["step"]]
        )
        if prompt != expected_prompt:
            raise RuntimeError(f"S27 persistent trajectory mismatch: {row['sample_id']}")
        target = TARGET_PREFIX + label
        prompt_tokens = tokenizer.encode(prompt)
        target_tokens = tokenizer.encode(target)
        text_tokens = tokenizer.encode(prompt + target)
        if text_tokens != prompt_tokens + target_tokens:
            raise RuntimeError(f"S27 target boundary is not additive: {row['sample_id']}")
        if 1 + len(text_tokens) > CTX_LEN + 1:
            raise RuntimeError(f"S27 target would be truncated: {row['sample_id']}")
        exports[split].append({
            "schema_version": "rwkv-lh.network-selector-state-tuning-row.s27.v1",
            "dataset_version": VERSION,
            "sample_id": str(row["sample_id"]).replace("NETSEL-S26-", "NETSEL-S27-STATE-", 1),
            "source_sample_id": row["sample_id"],
            "source_split": split,
            "semantic_family_id": row["semantic_family_id"],
            "label": label,
            "language": row["language"],
            "phase": row["phase"],
            "decision_index": row["decision_index"],
            "prompt": prompt,
            "target": target,
            "text": prompt + target,
            "prompt_tokens_including_bos": 1 + len(prompt_tokens),
            "target_tokens": len(target_tokens),
            "text_tokens_including_bos": 1 + len(text_tokens),
            "loss_mask": "target_suffix",
            "jsonl_bos_token_id": 0,
            "persistent_history_replayed": True,
            "generated_rwkv_text": False,
        })
    if {split: len(rows) for split, rows in exports.items()} != {"train": 2000, "dev": 500} or excluded_test != 500:
        raise RuntimeError("S27 frozen split counts changed")
    label_counts = {split: Counter(str(row["label"]) for row in rows) for split, rows in exports.items()}
    if label_counts != {
        "train": Counter({label: 80 for label in NETWORK_EXACT_TOOL_LABELS}),
        "dev": Counter({label: 20 for label in NETWORK_EXACT_TOOL_LABELS}),
    }:
        raise RuntimeError("S27 label balance changed")
    if len({str(row["prompt"]) for rows in exports.values() for row in rows}) != 2500:
        raise RuntimeError("S27 train/dev contains exact prompt duplicates")
    families = {split: {str(row["semantic_family_id"]) for row in rows} for split, rows in exports.items()}
    if families["train"] & families["dev"]:
        raise RuntimeError("S27 semantic families cross train/dev")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s27.", dir=OUTPUT.parent))
    paths = {split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl" for split in exports}
    for split, path in paths.items():
        write_jsonl(path, exports[split])
    lengths = [int(row["text_tokens_including_bos"]) for rows in exports.values() for row in rows]
    prompt_lengths = [int(row["prompt_tokens_including_bos"]) for rows in exports.values() for row in rows]
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "S27 current-Harness persistent-trajectory 2.9B Selector initial-WKV state tuning",
        "architecture": "current-direct-LongHorizonModel-dual-state",
        "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256, "rows": len(source_rows)},
        "counts": {"train": 2000, "dev": 500, "test_excluded": 500},
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "target_prefix": TARGET_PREFIX,
        "training_contract": {
            "loss_mask": "target_suffix", "jsonl_bos_token_id": 0,
            "ctx_len": CTX_LEN, "epoch_steps": 2000, "epoch_count": 1,
            "step_save": 500, "seed": 887, "persistent_history_replayed": True,
        },
        "validation": {
            "exact_prompt_duplicates": 0, "train_dev_family_overlap": 0,
            "all_labels_balanced_in_train_dev": True,
            "minimum_prompt_tokens_including_bos": min(prompt_lengths),
            "maximum_prompt_tokens_including_bos": max(prompt_lengths),
            "minimum_text_tokens_including_bos": min(lengths),
            "maximum_text_tokens_including_bos": max(lengths),
            "tokenization_boundary_additive": True, "target_truncation_count": 0,
            "holdout_similarity": source_manifest["validation"]["holdout_similarity"],
            "generated_rwkv_text_count": 0,
        },
        "s26_test_used": False, "s23_used": False,
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run python {Path(__file__).resolve()}",
        "generator": {"path": str(Path(__file__).resolve().relative_to(ROOT)), "sha256": sha256_file(Path(__file__).resolve())},
        "files": {path.name: {"rows": len(exports[split]), "sha256": sha256_file(path)} for split, path in paths.items()},
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (staging / "README.md").write_text(
        "# Current-Harness persistent Selector state S27 v1\n\n"
        "- 仅使用 S26 train 2000 条做 2.9B Selector 初始 WKV state tuning；dev 500 只验证，test 500 与 S23 全排除。\n"
        "- prompt 按线上顺序包含一次 Bootstrap、0–2 个历史 Step 和当前 Step，target 只监督标签后缀。\n"
        "- 不训练 13.3B Executor，不含 schema、完整结果或 Executor 文本；摘要与 token 上限见 manifest。\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
