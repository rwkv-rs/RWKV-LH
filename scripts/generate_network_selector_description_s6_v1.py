#!/usr/bin/env python3
"""Combine full v2.4 coverage with natural residual rows for S6."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    network_selector_menu_digest,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
S3 = ROOT / "data/datasets/rwkv_lh_network_selector_role_normalized_s3_v1/cases.jsonl"
TOOLS = ROOT / "data/datasets/rwkv_lh_network_selector_description_s5_v1/tool_descriptions.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_description_s6_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S6_PREREGISTRATION.md"
SHA = {
    "coverage": "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc",
    "s3": "34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c",
    "tools": "97218a227f31623136962a6506cc52a01638c98986d4089f52dca2b97a60dfca",
    "ecra": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
}
VERSION = "rwkv-lh.network-selector.description-conditioned-s6.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    data = text.encode("utf-8")
    return Counter(data[index : index + n] for index in range(max(0, len(data) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(value * right.get(key, 0) for key, value in left.items())
    return dot / math.sqrt(sum(value * value for value in left.values()) * sum(value * value for value in right.values()))


def compact(row: dict[str, object], source_kind: str) -> dict[str, object]:
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
    prefix = "COV" if source_kind == "v2_4_full_coverage" else "NAT"
    result = dict(row)
    result.update(
        {
            "schema_version": "rwkv-lh.network-selector-description-query-row.s6.v1",
            "dataset_version": VERSION,
            "sample_id": f"NETSEL-S6-{prefix}-{row['sample_id']}",
            "rendered_input": "SelectorQueryV3: " + canonical_json(payload),
            "selector_input_sha256": canonical_digest(payload),
            "query_projection": payload,
            "stage_objective": objective,
            "source_kind": source_kind,
            "source_sample_id": row["sample_id"],
            "failure_cluster": str(row.get("failure_cluster") or "full_coverage"),
        }
    )
    return result


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    paths = {"coverage": COVERAGE, "s3": S3, "tools": TOOLS, "ecra": ECRA}
    if any(sha256_file(path) != SHA[name] for name, path in paths.items()) or not PROTOCOL.is_file() or OUTPUT.exists():
        raise RuntimeError("S6 source/protocol/output contract failed")
    coverage_rows = [compact(json.loads(line), "v2_4_full_coverage") for line in COVERAGE.read_text(encoding="utf-8").splitlines()]
    s3_source = [json.loads(line) for line in S3.read_text(encoding="utf-8").splitlines()]
    natural_rows = [compact(row, "stage3_natural") for row in s3_source if row["failure_cluster"] != "class_retention"]
    rows = coverage_rows + natural_rows
    counts = Counter(str(row["split"]) for row in rows)
    if counts != Counter({"train": 7400, "dev": 926, "test": 750}):
        raise RuntimeError(f"S6 split counts changed: {counts}")
    if len({row["sample_id"] for row in rows}) != len(rows) or len({row["rendered_input"] for row in rows}) != len(rows):
        raise RuntimeError("S6 sample/query duplicates exist")
    families = {
        split: {(row["source_kind"], row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S6 semantic families cross splits")
    labels = {split: Counter(str(row["label"]) for row in rows if row["split"] == split) for split in ("train", "dev", "test")}
    if any(set(value) != set(NETWORK_EXACT_TOOL_LABELS) for value in labels.values()):
        raise RuntimeError("S6 label coverage changed")
    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(case["case_id"], byte_ngrams(case["instruction"])) for case in holdout]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    for row in rows:
        grams = byte_ngrams(str(row["stage_objective"]))
        for holdout_id, reference in holdout_grams:
            score = cosine(grams, reference)
            if score > maximum["score"]:
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if maximum["score"] >= 0.75:
        raise RuntimeError(f"S6 ECRA similarity gate failed: {maximum}")
    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s6.", dir=OUTPUT.parent))
    query_path = staging / "queries.jsonl"
    write_jsonl(query_path, rows)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S6 full coverage description-conditioned head",
        "counts": dict(sorted(counts.items())),
        "source_counts": dict(sorted(Counter(row["source_kind"] for row in rows).items())),
        "label_counts": {split: dict(sorted(value.items())) for split, value in labels.items()},
        "class_order": list(NETWORK_EXACT_TOOL_LABELS),
        "menu_digest": network_selector_menu_digest(),
        "generated_rwkv_text_count": 0,
        "sources": {name: {"path": str(path.relative_to(ROOT)), "sha256": SHA[name]} for name, path in paths.items()},
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generator_sha256": sha256_file(Path(__file__)),
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "files": {"queries.jsonl": {"rows": len(rows), "sha256": sha256_file(query_path)}},
        "validation": {
            "exact_query_duplicates": 0,
            "cross_split_family_overlap": 0,
            "all_labels_in_every_split": True,
            "holdout_similarity": {"algorithm": "utf8-byte-5gram-cosine.v1", "threshold_exclusive": 0.75, "maximum": maximum, "holdout_sha256": SHA["ecra"]},
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
