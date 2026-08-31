#!/usr/bin/env python3
"""Remove failure-cluster leakage from the NET-SEL-2P9-S3 input projection."""

from __future__ import annotations

import hashlib
import json
import math
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_residual_s2_v1/cases.jsonl"
ECRA = ROOT / "data/datasets/rwkv_lh_ecra_route_v1/cases.json"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_role_normalized_s3_v1"
PROTOCOL = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S3_PREREGISTRATION.md"
SOURCE_SHA256 = "b9f0601499790611de23322f8066f09deb8ba9fa6d5071fba78ee36930551922"
ECRA_SHA256 = "7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a"
VERSION = "rwkv-lh.network-selector.role-normalized-s3.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    value = text.encode("utf-8")
    return Counter(value[index : index + n] for index in range(max(0, len(value) - n + 1)))


def cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(count * right.get(key, 0) for key, count in left.items())
    left_norm = math.sqrt(sum(count * count for count in left.values()))
    right_norm = math.sqrt(sum(count * count for count in right.values()))
    return dot / (left_norm * right_norm)


def normalize(row: dict[str, object]) -> dict[str, object]:
    rendered = str(row["rendered_input"])
    bootstrap_text, step_text = rendered.split("\nSelectorStepV2: ", 1)
    if not bootstrap_text.startswith("SelectorBootstrapV2: "):
        raise RuntimeError(f"invalid S2 bootstrap: {row['sample_id']}")
    bootstrap = json.loads(bootstrap_text[len("SelectorBootstrapV2: ") :])
    step = json.loads(step_text)
    if step.get("stage_role") not in {
        "work", "finish", "boundary", "stable_selector_replay",
        "natural_connector", "ordinary_web", "mixed_local_first",
        "privacy_local_first",
    }:
        raise RuntimeError(f"unknown S2 stage role: {row['sample_id']}")
    step["stage_role"] = "work"
    normalized_input = (
        "SelectorBootstrapV2: " + canonical_json(bootstrap)
        + "\nSelectorStepV2: " + canonical_json(step)
    )
    merged = {**bootstrap, **step}
    result = dict(row)
    result.update(
        {
            "schema_version": "rwkv-lh.network-selector-role-normalized-row.s3.v1",
            "dataset_version": VERSION,
            "sample_id": str(row["sample_id"]).replace("NETSEL-S2-", "NETSEL-S3-", 1),
            "rendered_input": normalized_input,
            "selector_input_sha256": canonical_digest(merged),
            "role_projection": "work",
            "source_s2_sample_id": row["sample_id"],
        }
    )
    return result


def write_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")


def main() -> None:
    if sha256_file(SOURCE) != SOURCE_SHA256 or sha256_file(ECRA) != ECRA_SHA256:
        raise RuntimeError("S3 frozen source identity changed")
    if not PROTOCOL.is_file() or OUTPUT.exists():
        raise RuntimeError("S3 protocol missing or output already exists")
    source_rows = [json.loads(line) for line in SOURCE.read_text(encoding="utf-8").splitlines()]
    rows = [normalize(row) for row in source_rows]
    split_counts = Counter(str(row["split"]) for row in rows)
    if split_counts != Counter({"train": 2000, "dev": 276, "test": 250}):
        raise RuntimeError("S3 split counts changed")
    if len({row["sample_id"] for row in rows}) != 2526:
        raise RuntimeError("S3 sample IDs are not unique")
    if len({row["rendered_input"] for row in rows}) != 2526:
        raise RuntimeError("S3 contains exact rendered-input duplicates")
    families = {
        split: {row["semantic_family_id"] for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    if families["train"] & families["dev"] or families["train"] & families["test"] or families["dev"] & families["test"]:
        raise RuntimeError("S3 semantic families cross splits")
    label_counts = {
        split: Counter(str(row["label"]) for row in rows if row["split"] == split)
        for split in ("train", "dev", "test")
    }
    if any(set(counts) != set(NETWORK_EXACT_TOOL_LABELS) for counts in label_counts.values()):
        raise RuntimeError("S3 does not retain all labels in every split")
    if any('"stage_role":"work"' not in str(row["rendered_input"]) for row in rows):
        raise RuntimeError("S3 role normalization is incomplete")
    forbidden = {"stable_selector_replay", "natural_connector", "ordinary_web", "mixed_local_first", "privacy_local_first"}
    if any(any(value in str(row["rendered_input"]) for value in forbidden) for row in rows):
        raise RuntimeError("S3 rendered input leaks a failure cluster")

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
        raise RuntimeError(f"S3 ECRA similarity gate failed: {maximum}")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_network_selector_s3.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    write_jsonl(cases_path, rows)
    manifest = {
        "schema_version": "rwkv-lh.dataset-manifest.v1",
        "dataset_version": VERSION,
        "purpose": "NET-SEL-2P9-S3 failure-cluster leakage remediation",
        "counts": dict(sorted(split_counts.items())),
        "label_counts": {split: dict(sorted(counts.items())) for split, counts in label_counts.items()},
        "projection": {"stage_role": "work", "failure_cluster_in_rendered_input": False},
        "generated_rwkv_text_count": 0,
        "validation": {
            "exact_rendered_input_duplicates": 0,
            "cross_split_family_overlap": 0,
            "all_labels_in_every_split": True,
            "holdout_similarity": {
                "algorithm": "utf8-byte-5gram-cosine.v1",
                "threshold_exclusive": 0.75,
                "maximum": maximum,
                "holdout_sha256": ECRA_SHA256,
            },
        },
        "sources": {
            "s2_cases": {"path": str(SOURCE.relative_to(ROOT)), "sha256": SOURCE_SHA256},
            "ecra120": {"path": str(ECRA.relative_to(ROOT)), "sha256": ECRA_SHA256},
        },
        "protocol": {"path": str(PROTOCOL.relative_to(ROOT)), "sha256": sha256_file(PROTOCOL)},
        "generation": f"uv run --no-sync python {Path(__file__).resolve()}",
        "generator_sha256": sha256_file(Path(__file__)),
        "files": {"cases.jsonl": {"rows": len(rows), "sha256": sha256_file(cases_path)}},
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
