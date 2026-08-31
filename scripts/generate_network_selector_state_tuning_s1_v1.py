#!/usr/bin/env python3
"""Export the frozen Selector v2.4 train/dev rows for 2.9B state tuning."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
SOURCE_SHA256 = "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_state_tuning_s1_v1"
PROTOCOL = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
    / "STATE_TUNING_S1_PREREGISTRATION.md"
)
VERSION = "rwkv-lh.network-selector-state-tuning.s1.v1"
TARGET_PREFIX = "\nSelectorLabelV2: "


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
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("frozen Selector v2.4 source SHA-256 changed")
    if not PROTOCOL.is_file():
        raise FileNotFoundError(PROTOCOL)
    if OUTPUT.exists():
        raise RuntimeError(f"refusing to replace existing dataset: {OUTPUT}")
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(source_rows) != 7500:
        raise RuntimeError("frozen Selector v2.4 source row count changed")
    exports: dict[str, list[dict[str, object]]] = {"train": [], "dev": []}
    for row in source_rows:
        split = str(row["split"])
        if split == "test":
            continue
        if split not in exports:
            raise RuntimeError(f"unknown frozen split: {split}")
        label = str(row["label"])
        if label not in NETWORK_EXACT_TOOL_LABELS:
            raise RuntimeError(f"unknown frozen label: {label}")
        prompt = str(row["rendered_input"])
        target = TARGET_PREFIX + label
        exports[split].append(
            {
                "schema_version": "rwkv-lh.network-selector-state-tuning-row.s1.v1",
                "dataset_version": VERSION,
                "source_sample_id": row["sample_id"],
                "source_split": split,
                "label": label,
                "prompt": prompt,
                "target": target,
                "text": prompt + target,
                "loss_mask": "target_suffix",
                "jsonl_bos_token_id": 0,
                "generated_rwkv_text": False,
            }
        )
    expected_counts = {"train": 6000, "dev": 750}
    if {name: len(rows) for name, rows in exports.items()} != expected_counts:
        raise RuntimeError("state-tuning export split counts changed")
    for split, rows in exports.items():
        counts = Counter(str(row["label"]) for row in rows)
        expected_per_label = 240 if split == "train" else 30
        if counts != Counter({label: expected_per_label for label in NETWORK_EXACT_TOOL_LABELS}):
            raise RuntimeError(f"state-tuning {split} label balance changed")

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(
            prefix=".rwkv_lh_network_selector_state_tuning_s1_v1.",
            dir=OUTPUT.parent,
        )
    )
    paths = {
        split: staging / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        for split in exports
    }
    for split, path in paths.items():
        write_jsonl(path, exports[split])
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "rows": len(source_rows),
        },
        "purpose": "single-profile 2.9B Selector state-tuning S1 ablation",
        "generation": f"uv run python {ROOT / 'scripts/generate_network_selector_state_tuning_s1_v1.py'}",
        "generator_sha256": sha256_file(Path(__file__)),
        "protocol": str(PROTOCOL.relative_to(ROOT)),
        "protocol_sha256": sha256_file(PROTOCOL),
        "counts": expected_counts,
        "per_label": {"train": 240, "dev": 30},
        "test_source_rows_excluded": 750,
        "target_prefix": TARGET_PREFIX,
        "loss_mask": "target_suffix",
        "jsonl_bos_token_id": 0,
        "generated_rwkv_text_count": 0,
        "files": {
            path.name: {"rows": len(exports[split]), "sha256": sha256_file(path)}
            for split, path in paths.items()
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
