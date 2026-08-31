#!/usr/bin/env python3
"""Add evaluator-only language metadata to the frozen G6 dev rows."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_2k/stage_sft.dev.jsonl"
ADDENDUM = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
    / "EXE_G6_EVALUATION_METADATA_COMPLETENESS_ADDENDUM.md"
)
OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_network_recovery_g6_eval_v2"
SOURCE_SHA256 = "bb22c9cd50a17b3cc4e8cd96e3c13e5bd62cd6e8c12312dcc423aa5db8b7827e"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen G6 eval metadata view")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("G6 frozen dev source changed")
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(source_rows) != 480:
        raise RuntimeError("G6 eval source count changed")
    rows = []
    additions: Counter[str] = Counter()
    for source in source_rows:
        row = dict(source)
        if "language" not in row:
            language = (
                "zh"
                if any("\u4e00" <= char <= "\u9fff" for char in str(row["prompt"]))
                else "en"
            )
            row["language"] = language
            additions[language] += 1
        if hashlib.sha256(str(row["prompt"]).encode()).hexdigest() != row["prompt_sha256"]:
            raise RuntimeError("G6 eval prompt bytes changed")
        if hashlib.sha256(str(row["target"]).encode()).hexdigest() != row["target_sha256"]:
            raise RuntimeError("G6 eval target bytes changed")
        if any(row.get(key) != source.get(key) for key in source):
            raise RuntimeError("G6 eval projection changed an existing field")
        rows.append(row)
    if sum(additions.values()) != 384:
        raise RuntimeError(f"G6 missing-language count changed: {additions}")
    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    view = staging / "stage_sft.dev.eval.jsonl"
    with view.open("x", encoding="utf-8") as stream:
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
    manifest = {
        "schema_version": "rwkv-lh.executor-g6-eval-metadata-view.v2",
        "purpose": "metadata-complete evaluator input without prompt or target mutation",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "rows": 480,
        },
        "language": {
            "added_rows": sum(additions.values()),
            "added_counts": dict(sorted(additions.items())),
            "existing_rows": 480 - sum(additions.values()),
            "derivation": "cjk-character-present-then-zh-else-en",
        },
        "validation": {
            "sample_ids_unchanged": True,
            "line_order_unchanged": True,
            "prompt_bytes_unchanged": True,
            "target_bytes_unchanged": True,
            "selected_operations_unchanged": True,
            "only_missing_language_added": True,
            "raw_rwkv_output_modified": False,
        },
        "addendum": {
            "path": str(ADDENDUM.relative_to(ROOT)),
            "sha256": sha256_file(ADDENDUM),
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "file": {
            "path": view.name,
            "rows": len(rows),
            "bytes": view.stat().st_size,
            "sha256": sha256_file(view),
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# G6 metadata-complete dev evaluation view\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "g6_eval_metadata_view_complete",
                "rows": 480,
                "language_added": dict(additions),
                "view_sha256": sha256_file(OUTPUT / view.name),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
