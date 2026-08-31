#!/usr/bin/env python3
"""Add missing language metadata to the frozen G4 dev evaluation view."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_2k/stage_sft.dev.jsonl"
ADDENDUM = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/EXE_G4_EVALUATION_METADATA_COMPLETENESS_ADDENDUM.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_executor_true_workflow_g4_eval_v2"
SOURCE_SHA256 = "a81f3805535649ae75148e0d7debdb3be60e00ba36837b67d0f80fb8113bb50d"
ADDENDUM_SHA256 = "832100ed15f50661ff2f0f048479484a855f59a27aa70d45cd12feeb6ffcc175"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen G4 eval metadata view")
    for path, expected in {SOURCE: SOURCE_SHA256, ADDENDUM: ADDENDUM_SHA256}.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"G4 eval metadata frozen input changed: {path}")
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    if len(source_rows) != 480:
        raise RuntimeError("G4 eval source count changed")
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
        if hashlib.sha256(str(row["prompt"]).encode("utf-8")).hexdigest() != row[
            "prompt_sha256"
        ]:
            raise RuntimeError("G4 eval prompt bytes changed")
        if hashlib.sha256(str(row["target"]).encode("utf-8")).hexdigest() != row[
            "target_sha256"
        ]:
            raise RuntimeError("G4 eval target bytes changed")
        rows.append(row)
    if sum(additions.values()) != 240 or dict(additions) != {"en": 240}:
        raise RuntimeError(f"G4 eval language completion changed: {additions}")
    if any(
        any(
            row.get(key) != source.get(key)
            for key in source
        )
        for row, source in zip(rows, source_rows, strict=True)
    ):
        raise RuntimeError("G4 eval metadata view changed an existing field")

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
        "schema_version": "rwkv-lh.executor-g4-eval-metadata-view.v2",
        "purpose": "metadata-complete evaluator input without prompt or target mutation",
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "rows": 480,
        },
        "language": {
            "added_rows": sum(additions.values()),
            "added_counts": dict(sorted(additions.items())),
            "existing_rows": 240,
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
            "sha256": ADDENDUM_SHA256,
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
        "# G4 metadata-complete dev evaluation view\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "g4_eval_metadata_view_complete",
                "rows": 480,
                "language_added": dict(additions),
                "view_sha256": sha256_file(OUTPUT / view.name),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
