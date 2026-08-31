#!/usr/bin/env python3
"""Build the preregistered S11 hierarchical network-takeover dataset."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.takeover_protocol_v4 import NetworkTakeoverInput


ROOT = Path(__file__).resolve().parents[1]
S10 = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s10_v1/cases.jsonl"
S3 = ROOT / "data/datasets/rwkv_lh_network_selector_role_normalized_s3_v1/cases.jsonl"
COVERAGE = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s11_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S11_HIERARCHICAL_PREREGISTRATION.md"
VERSION = "rwkv-lh.network-takeover-selector.s11.v1"
SHA = {
    "s10": "eeea9abeef9cdcbf0328286d8c950aed137594f1f3545500c0066fc466deaf59",
    "s3": "34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c",
    "coverage": "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc",
    "ecra": "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a",
}
S3_COUNTS = {
    ("train", "natural_connector"): 280,
    ("train", "ordinary_web"): 70,
    ("train", "mixed_local_first"): 100,
    ("train", "privacy_local_first"): 70,
    ("dev", "natural_connector"): 32,
    ("dev", "ordinary_web"): 8,
    ("dev", "mixed_local_first"): 20,
    ("dev", "privacy_local_first"): 20,
}
COVERAGE_COUNTS = {
    ("train", "calculator"): 14,
    ("train", "date_diff"): 13,
    ("train", "current_time"): 13,
    ("dev", "calculator"): 2,
    ("dev", "date_diff"): 2,
    ("dev", "current_time"): 2,
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def byte_ngrams(value: str, n: int = 5) -> Counter[bytes]:
    data = value.encode("utf-8")
    return Counter(data[index : index + n] for index in range(max(0, len(data) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    if not dot:
        return 0.0
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return dot / (left_norm * right_norm)


def projected_row(
    source: dict[str, Any], *, source_kind: str, source_id: str, label: str,
) -> dict[str, Any]:
    objective = str(source["stage_objective"] if source_kind == "stage3" else source["selector_projection"]["stage_objective"])
    rendered = NetworkTakeoverInput(objective).render()
    return {
        "schema_version": "rwkv-lh.network-takeover-selector-row.s11.v1",
        "dataset_version": VERSION,
        "sample_id": f"NETTAKE-S11-{source_kind.upper()}-{source_id}",
        "source_kind": source_kind,
        "source_sample_id": source_id,
        "semantic_family_id": str(source["semantic_family_id"]),
        "failure_cluster": str(source.get("failure_cluster") or "deterministic_retention"),
        "split": str(source["split"]),
        "label": label,
        "rendered_input": rendered,
        "selector_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "generated_rwkv_text": False,
    }


def rendered_objective(rendered: str) -> str:
    prefix = "NetworkTakeoverQueryV1: "
    if not rendered.startswith(prefix):
        raise RuntimeError("S11 rendered input prefix changed")
    value = json.loads(rendered[len(prefix) :])
    objective = str(value.get("objective") or "")
    if not objective:
        raise RuntimeError("S11 rendered objective is empty")
    return objective


def main() -> None:
    for key, path in (("s10", S10), ("s3", S3), ("coverage", COVERAGE), ("ecra", ECRA)):
        if sha256_file(path) != SHA[key]:
            raise RuntimeError(f"S11 frozen source changed: {key}")
    if OUTPUT.exists() or not PROTOCOL.is_file():
        raise RuntimeError("S11 output exists or preregistration is missing")

    rows = []
    for source in read_jsonl(S10):
        value = dict(source)
        value["dataset_version"] = VERSION
        value["schema_version"] = "rwkv-lh.network-takeover-selector-row.s11.v1"
        value["source_kind"] = "s10"
        rows.append(value)

    s3_rows = read_jsonl(S3)
    selected_s3: Counter[tuple[str, str]] = Counter()
    for source in s3_rows:
        key = (str(source["split"]), str(source["failure_cluster"]))
        limit = S3_COUNTS.get(key, 0)
        if selected_s3[key] >= limit:
            continue
        label = str(source["label"])
        if key[1] == "natural_connector" and label != "connector_lookup":
            raise RuntimeError("S11 connector source label changed")
        if key[1] == "ordinary_web" and label != "web_search":
            raise RuntimeError("S11 web source label changed")
        projected_label = label if label in {"web_search", "connector_lookup"} else "DEFER"
        rows.append(projected_row(source, source_kind="stage3", source_id=str(source["sample_id"]), label=projected_label))
        selected_s3[key] += 1
    if dict(selected_s3) != S3_COUNTS:
        raise RuntimeError(f"S11 Stage3 source counts changed: {selected_s3}")

    coverage_rows = read_jsonl(COVERAGE)
    selected_coverage: Counter[tuple[str, str]] = Counter()
    for source in coverage_rows:
        key = (str(source["split"]), str(source["label"]))
        limit = COVERAGE_COUNTS.get(key, 0)
        if selected_coverage[key] >= limit:
            continue
        rows.append(projected_row(source, source_kind="coverage", source_id=str(source["sample_id"]), label="DEFER"))
        selected_coverage[key] += 1
    if dict(selected_coverage) != COVERAGE_COUNTS:
        raise RuntimeError(f"S11 coverage source counts changed: {selected_coverage}")

    if len(rows) != 2000 or len({row["sample_id"] for row in rows}) != 2000:
        raise RuntimeError("S11 row/sample count changed")
    rendered_labels: dict[str, str] = {}
    for row in rows:
        previous = rendered_labels.setdefault(str(row["rendered_input"]), str(row["label"]))
        if previous != row["label"]:
            raise RuntimeError("S11 contradictory rendered input")
    if len(rendered_labels) != len(rows):
        raise RuntimeError("S11 exact rendered duplicates remain")
    families = {
        split: {str(row["semantic_family_id"]) for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S11 semantic family crosses splits")
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter({"train": 1506, "dev": 289, "test": 205}):
        raise RuntimeError(f"S11 split counts changed: {split_counts}")

    holdout = json.loads(ECRA.read_text(encoding="utf-8"))["cases"]
    holdout_grams = [(str(case["case_id"]), byte_ngrams(str(case["instruction"]))) for case in holdout]
    maximum = {"score": -1.0, "sample_id": "", "holdout_id": ""}
    exact_overlap = 0
    holdout_text = {str(case["instruction"]) for case in holdout}
    for row in rows:
        objective = rendered_objective(str(row["rendered_input"]))
        if objective in holdout_text:
            exact_overlap += 1
        grams = byte_ngrams(objective)
        for holdout_id, target in holdout_grams:
            score = cosine(grams, target)
            if score > maximum["score"]:
                maximum = {"score": score, "sample_id": row["sample_id"], "holdout_id": holdout_id}
    if exact_overlap or maximum["score"] >= 0.75:
        raise RuntimeError(f"S11 contamination gate failed: {exact_overlap=} {maximum=}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s11.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S11 one-forward hierarchical network takeover",
        "counts": {
            "rows": len(rows),
            "splits": dict(sorted(split_counts.items())),
            "labels": dict(sorted(Counter(str(row["label"]) for row in rows).items())),
            "sources": dict(sorted(Counter(str(row["source_kind"]) for row in rows).items())),
            "supplement_clusters": dict(sorted(Counter(str(row["failure_cluster"]) for row in rows if row["source_kind"] != "s10").items())),
        },
        "sources": {
            "s10": {"path": str(S10.relative_to(ROOT)), "sha256": SHA["s10"]},
            "stage3": {"path": str(S3.relative_to(ROOT)), "sha256": SHA["s3"]},
            "coverage": {"path": str(COVERAGE.relative_to(ROOT)), "sha256": SHA["coverage"]},
            "ecra_contamination_only": {"path": str(ECRA.relative_to(ROOT)), "sha256": SHA["ecra"]},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}},
        "validation": {
            "exact_rendered_input_duplicate_count": 0,
            "contradictory_duplicate_count": 0,
            "family_split_overlap_count": 0,
            "generated_rwkv_text_count": 0,
            "contamination": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "threshold_exclusive": 0.75,
                "exact_overlap_count": exact_overlap,
                "maximum": maximum,
            },
        },
    }
    (staging / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
