#!/usr/bin/env python3
"""Derive the preregistered three-way network takeover dataset for S10."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import network_selector_tool_menu
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl"
SOURCE_MANIFEST = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/manifest.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s10_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S10_GATE_PREREGISTRATION.md"
SOURCE_SHA256 = "b345e98f0e58fe291767218f7c27da6c766a100145193f0e4be46051896de29f"
VERSION = "rwkv-lh.network-takeover-selector.s10.v1"
LABELS = ("web_search", "connector_lookup", "DEFER")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def tool_menu() -> tuple[dict[str, str], ...]:
    by_name = {item["name"]: item["description"] for item in network_selector_tool_menu()}
    return (
        {"name": "web_search", "description": by_name["web_search"]},
        {"name": "connector_lookup", "description": by_name["connector_lookup"]},
        {
            "name": "DEFER",
            "description": (
                "Do not take over this stage; leave local, deterministic, final, "
                "ambiguous, or unsupported tool selection to the existing Executor."
            ),
        },
    )


def main() -> None:
    if (
        sha256_file(SOURCE) != SOURCE_SHA256
        or not SOURCE_MANIFEST.is_file()
        or not PROTOCOL.is_file()
        or OUTPUT.exists()
    ):
        raise RuntimeError("S10 source/protocol/output contract failed")
    source_manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    contamination = source_manifest["validation"]["contamination"]
    if (
        contamination["similarity_version"] != "utf8-byte-ngram-cosine.v1"
        or contamination["threshold_exclusive"] != 0.75
        or contamination["maximum_holdout_similarity"] >= 0.75
    ):
        raise RuntimeError("S10 inherited contamination contract changed")
    menu = tool_menu()
    projected: list[dict[str, object]] = []
    seen: dict[str, str] = {}
    duplicate_count = 0
    for source_index, line in enumerate(SOURCE.read_text(encoding="utf-8").splitlines()):
        source = json.loads(line)
        input_value = source["input"]
        route = str(source["labels"]["route_family"])
        label = {
            "web": "web_search",
            "connector": "connector_lookup",
        }.get(route, "DEFER")
        payload = {
            "schema_version": "rwkv-lh.network-takeover-query.v1",
            "objective": str(input_value["request"]),
            "progress": {
                "mode": str(input_value["mode"]),
                "evidence_state": str(input_value["evidence_state"]),
                "policy_state": str(input_value["policy_state"]),
            },
            "tools": [dict(item) for item in menu],
        }
        rendered = "NetworkTakeoverQueryV1: " + canonical_json(payload)
        prior = seen.get(rendered)
        if prior is not None:
            if prior != label:
                raise RuntimeError("S10 contains a contradictory rendered duplicate")
            duplicate_count += 1
            continue
        seen[rendered] = label
        projected.append(
            {
                "schema_version": "rwkv-lh.network-takeover-selector-row.s10.v1",
                "dataset_version": VERSION,
                "sample_id": f"NETTAKE-S10-{len(projected):04d}",
                "source_sample_id": source["sample_id"],
                "source_index": source_index,
                "semantic_family_id": source["semantic_family_id"],
                "split": source["split"],
                "label": label,
                "rendered_input": rendered,
                "selector_input_sha256": canonical_digest(payload),
                "generated_rwkv_text": False,
            }
        )
    if len(projected) != 1354 or duplicate_count != 646:
        raise RuntimeError("S10 deterministic deduplication count changed")
    if len({row["rendered_input"] for row in projected}) != len(projected):
        raise RuntimeError("S10 rendered duplicates remain")
    families = {
        split: {row["semantic_family_id"] for row in projected if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S10 semantic families cross splits")
    split_counts = Counter(str(row["split"]) for row in projected)
    label_counts = Counter(str(row["label"]) for row in projected)
    expected_splits = Counter({"train": 946, "dev": 203, "test": 205})
    expected_labels = Counter({"DEFER": 879, "web_search": 250, "connector_lookup": 225})
    if split_counts != expected_splits or label_counts != expected_labels:
        raise RuntimeError("S10 split/label counts changed")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_takeover_s10.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    with cases.open("w", encoding="utf-8") as stream:
        for row in projected:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S10-GATE function-scoped network takeover",
        "class_order": list(LABELS),
        "counts": {
            "rows": len(projected),
            "deduplicated_source_rows": duplicate_count,
            "splits": dict(sorted(split_counts.items())),
            "labels": dict(sorted(label_counts.items())),
        },
        "sources": {
            "samples": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "manifest": {"path": str(SOURCE_MANIFEST.relative_to(ROOT)), "sha256": sha256_file(SOURCE_MANIFEST)},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {"cases.jsonl": {"rows": len(projected), "sha256": sha256_file(cases)}},
        "validation": {
            "exact_rendered_input_duplicate_count": 0,
            "contradictory_duplicate_count": 0,
            "family_split_overlap_count": 0,
            "rendered_fields": ["objective", "progress.mode", "progress.evidence_state", "progress.policy_state", "tools.name", "tools.description"],
            "excluded_fields": ["summary", "result", "history", "rationale", "source", "expected_label", "parameter_schema", "executor_state", "executor_text"],
            "contamination": contamination,
            "generated_rwkv_text_count": 0,
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
