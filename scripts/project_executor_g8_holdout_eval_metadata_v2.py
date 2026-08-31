#!/usr/bin/env python3
"""Add evaluator-only language metadata without changing frozen G8 holdout rows."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from scripts.generate_executor_engineering_retention_repair_g8_2k import current_requirement


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATA = ROOT / "data/datasets/rwkv_lh_executor_engineering_retention_g8_holdout_v1"
SOURCE = DATA / "stage_sft.holdout.eval.jsonl"
OUTPUT = DATA / "stage_sft.holdout.eval.metadata_v2.jsonl"
MANIFEST = DATA / "metadata_v2_manifest.json"
AMENDMENT = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
    / "EXE_G8_HOLDOUT_METADATA_PROJECTION_AMENDMENT.md"
)
SOURCE_SHA256 = "9ca538ed6bf48fcb42b9c78ad59f59178217dd5d5073b9423eac0b222954e54a"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def main() -> None:
    if OUTPUT.exists() or MANIFEST.exists():
        raise RuntimeError("refusing to replace G8 holdout metadata projection")
    if sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("frozen G8 holdout source changed")
    source = read_jsonl(SOURCE)
    if len(source) != 240 or any("language" in row for row in source):
        raise RuntimeError("G8 holdout source metadata contract changed")
    projected: list[dict[str, Any]] = []
    for row in source:
        requirement = current_requirement(str(row["prompt"]))
        language = "zh" if any("\u4e00" <= char <= "\u9fff" for char in requirement) else "en"
        projected.append({**row, "language": language})
    with OUTPUT.open("x", encoding="utf-8") as stream:
        for row in projected:
            stream.write(
                json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                + "\n"
            )
    reread = read_jsonl(OUTPUT)
    if len(reread) != len(source):
        raise RuntimeError("G8 holdout projection row count changed")
    for original, value in zip(source, reread, strict=True):
        without_language = dict(value)
        language = without_language.pop("language")
        if without_language != original or language not in {"en", "zh"}:
            raise RuntimeError("G8 holdout projection changed a source field")
    language_counts = {
        key: sum(row["language"] == key for row in reread) for key in ("en", "zh")
    }
    if language_counts != {"en": 240, "zh": 0}:
        raise RuntimeError(f"G8 holdout language counts changed: {language_counts}")
    report = {
        "schema_version": "rwkv-lh.executor-g8-holdout-metadata-projection.v2",
        "status": "valid",
        "rows": len(reread),
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
        },
        "projection": {
            "path": str(OUTPUT.relative_to(ROOT)),
            "sha256": sha256_file(OUTPUT),
        },
        "language_counts": language_counts,
        "only_added_field": "language",
        "source_objects_equal_after_removing_language": True,
        "entered_state_tuning": False,
        "raw_output_modified": False,
        "amendment": {
            "path": str(AMENDMENT.relative_to(ROOT)),
            "sha256": sha256_file(AMENDMENT),
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
    }
    MANIFEST.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
