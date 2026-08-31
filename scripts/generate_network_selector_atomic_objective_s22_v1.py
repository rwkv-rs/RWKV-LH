#!/usr/bin/env python3
"""Project frozen S6 stage objectives into the S21 ObjectiveV4 protocol."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_description_s6_v1/queries.jsonl"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S22_ATOMIC_OBJECTIVE_REGRESSION_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_atomic_objective_s22_v1"
SOURCE_SHA256 = "d60ad4a2404fda0f9401a5858070bb5e3063d408be68c9f88e1c0431eed1313c"
VERSION = "rwkv-lh.network-selector.atomic-objective-s22.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    if OUTPUT.exists() or not PROTOCOL.is_file() or sha256_file(SOURCE) != SOURCE_SHA256:
        raise RuntimeError("S22 output/protocol/source identity contract failed")
    tokenizer = RWKVTokenizer()
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    if len(source_rows) != 9076 or len({str(row["sample_id"]) for row in source_rows}) != 9076:
        raise RuntimeError("S22 source cardinality changed")
    rows = []
    for row in source_rows:
        objective = str(row["stage_objective"])
        payload = {
            "schema_version": "rwkv-lh.selector-objective.s20.v1",
            "objective": objective,
        }
        rendered = "SelectorObjectiveV4: " + canonical_json(payload)
        projected = {
            "schema_version": "rwkv-lh.network-selector-atomic-objective-row.s22.v1",
            "dataset_version": VERSION,
            "sample_id": f"S22-{row['sample_id']}",
            "source_sample_id": row["sample_id"],
            "source_kind": row.get("source_kind"),
            "failure_cluster": row.get("failure_cluster"),
            "semantic_family_id": row.get("semantic_family_id"),
            "split": row["split"],
            "label": row["label"],
            "stage_objective": objective,
            "rendered_input": rendered,
            "selector_input_sha256": canonical_digest(payload),
            "prompt_tokens_including_bos": 1 + len(tokenizer.encode(rendered)),
            "generated_rwkv_text": False,
        }
        rows.append(projected)
    splits = Counter(str(row["split"]) for row in rows)
    if splits != Counter({"train": 7400, "dev": 926, "test": 750}):
        raise RuntimeError(f"S22 split counts changed: {splits}")
    natural = [row for row in rows if row["split"] == "dev" and row["source_kind"] == "stage3_natural"]
    if len(natural) != 176:
        raise RuntimeError("S22 natural dev cardinality changed")
    maximum = max(int(row["prompt_tokens_including_bos"]) for row in rows)
    if maximum > 384:
        raise RuntimeError(f"S22 compact input exceeds 384 tokens: {maximum}")
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s22.", dir=OUTPUT.parent))
    try:
        query_path = staging / "queries.jsonl"
        with query_path.open("w", encoding="utf-8") as stream:
            for row in rows:
                stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        readme = (
            "# RWKV-LH network Selector atomic ObjectiveV4 S22 v1\n\n"
            f"- source: `{SOURCE.relative_to(ROOT)}`, SHA-256 `{SOURCE_SHA256}`;\n"
            "- purpose: frozen post-Planner atomic-objective regression for S21;\n"
            f"- rows: {len(rows)}; splits: {dict(sorted(splits.items()))};\n"
            f"- natural dev: {len(natural)}; maximum prompt tokens including BOS: {maximum};\n"
            "- generation: mechanical ObjectiveV4 projection by the adjacent registered script;\n"
            "- RWKV generation/sampling: none.\n"
        )
        (staging / "README.md").write_text(readme, encoding="utf-8")
        manifest = {
            "schema_version": "rwkv-lh.dataset-manifest.v1",
            "dataset_version": VERSION,
            "source": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "purpose": "post-Planner atomic ObjectiveV4 external regression for frozen S21",
            "generation": str(Path(__file__).resolve().relative_to(ROOT)),
            "rows": len(rows),
            "split_counts": dict(sorted(splits.items())),
            "natural_dev_rows": len(natural),
            "maximum_prompt_tokens_including_bos": maximum,
            "files": {
                "queries.jsonl": {"sha256": sha256_file(query_path)},
                "README.md": {"sha256": sha256_file(staging / "README.md")},
            },
        }
        (staging / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.replace(OUTPUT)
    except BaseException:
        for path in sorted(staging.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
        if staging.exists():
            staging.rmdir()
        raise
    print(json.dumps({
        "rows": len(rows),
        "splits": dict(sorted(splits.items())),
        "natural_dev": len(natural),
        "maximum_tokens": maximum,
        "queries_sha256": sha256_file(OUTPUT / "queries.jsonl"),
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
