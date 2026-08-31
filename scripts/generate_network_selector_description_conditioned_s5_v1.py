#!/usr/bin/env python3
"""Freeze compact queries and tool descriptions for NET-SEL-2P9-S5."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    network_selector_menu_digest,
    network_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_role_normalized_s3_v1/cases.jsonl"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_description_s5_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S5_PREREGISTRATION.md"
SOURCE_SHA256 = "34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c"
VERSION = "rwkv-lh.network-selector.description-conditioned-s5.v1"


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


def compact_query(row: dict[str, object]) -> dict[str, object]:
    rendered = str(row["rendered_input"])
    bootstrap_text, step_text = rendered.split("\nSelectorStepV2: ", 1)
    bootstrap = json.loads(bootstrap_text[len("SelectorBootstrapV2: ") :])
    step = json.loads(step_text)
    task = str(bootstrap["task_request"])
    objective = str(step["stage_objective"])
    payload: dict[str, object] = {
        "schema_version": "rwkv-lh.exact-tool-selector-query.v3",
        "objective": objective,
        "role": "work",
        "progress": step["progress"],
    }
    if task != objective:
        payload["task"] = task
    rendered_query = "SelectorQueryV3: " + canonical_json(payload)
    result = dict(row)
    result.update(
        {
            "schema_version": "rwkv-lh.network-selector-description-query-row.s5.v1",
            "dataset_version": VERSION,
            "sample_id": str(row["sample_id"]).replace("NETSEL-S3-", "NETSEL-S5-", 1),
            "rendered_input": rendered_query,
            "selector_input_sha256": canonical_digest(payload),
            "query_projection": payload,
            "source_s3_sample_id": row["sample_id"],
        }
    )
    return result


def main() -> None:
    if sha256_file(SOURCE) != SOURCE_SHA256 or not PROTOCOL.is_file() or OUTPUT.exists():
        raise RuntimeError("S5 source/protocol/output contract failed")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    queries = [compact_query(row) for row in source_rows]
    if Counter(str(row["split"]) for row in queries) != Counter({"train": 2000, "dev": 276, "test": 250}):
        raise RuntimeError("S5 split counts changed")
    if len({row["rendered_input"] for row in queries}) != len(queries):
        raise RuntimeError("S5 contains exact query duplicates")
    families = {
        split: {row["semantic_family_id"] for row in queries if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S5 semantic families cross splits")
    if any(
        set(row["query_projection"]) & {"failure_cluster", "tools", "description"}
        for row in queries
    ):
        raise RuntimeError("S5 per-request query leaks menu or provenance")

    menu = network_selector_tool_menu()
    descriptions = []
    for index, item in enumerate(menu):
        payload = {
            "schema_version": "rwkv-lh.exact-tool-description.v3",
            "name": item["name"],
            "description": item["description"],
        }
        descriptions.append(
            {
                "schema_version": "rwkv-lh.network-selector-tool-description-row.s5.v1",
                "dataset_version": VERSION,
                "sample_id": f"NETSEL-S5-TOOL-{index:02d}-{item['name'].upper()}",
                "label": item["name"],
                "rendered_input": "ToolDescriptionV3: " + canonical_json(payload),
                "description_sha256": canonical_digest(payload),
                "generated_rwkv_text": False,
            }
        )
    if tuple(row["label"] for row in descriptions) != NETWORK_EXACT_TOOL_LABELS:
        raise RuntimeError("S5 description class order changed")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s5.", dir=OUTPUT.parent))
    query_path = staging / "queries.jsonl"
    description_path = staging / "tool_descriptions.jsonl"
    write_jsonl(query_path, queries)
    write_jsonl(description_path, descriptions)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S5 compact query and description-conditioned scoring",
        "counts": {"queries": len(queries), "tools": len(descriptions), "train": 2000, "dev": 276, "test": 250},
        "class_order": list(NETWORK_EXACT_TOOL_LABELS),
        "menu_digest": network_selector_menu_digest(menu),
        "generated_rwkv_text_count": 0,
        "sources": {"s3_cases": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256}},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {
            "queries.jsonl": {"rows": len(queries), "sha256": sha256_file(query_path)},
            "tool_descriptions.jsonl": {"rows": len(descriptions), "sha256": sha256_file(description_path)},
        },
        "validation": {
            "exact_query_duplicates": 0,
            "cross_split_family_overlap": 0,
            "failure_cluster_in_query": False,
            "menu_in_query": False,
            "description_order_exact": True,
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
