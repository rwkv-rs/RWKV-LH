from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage2_route_boundary_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_stage2_route_boundary_manifest_and_files_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == "rwkv-lh.state-tuning.stage2-route-boundary.v1"
    assert manifest["counts"] == {
        "train": 640,
        "dev": 96,
        "train_semantic_families": 160,
        "dev_semantic_families": 24,
    }
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage2_route_boundary_targets_are_selector_only_and_exact() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert len(train) == 640
    assert len(dev) == 96
    for row in train + dev:
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["prompt_sha256"] for row in train + dev}) == 736


def test_stage2_route_boundary_quota_and_family_isolation() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert Counter(row["failure_cluster"] for row in train) == {
        "structured_connector": 320,
        "general_web": 160,
        "mixed_local_first": 80,
        "privacy_local_first": 80,
    }
    assert Counter(row["target_operation"] for row in train) == {
        "connector_lookup": 320,
        "web_search": 160,
        "read_file": 120,
        "read_json": 40,
    }
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    assert not train_families.intersection(dev_families)
    assert set(Counter(row["semantic_family_id"] for row in train).values()) == {4}
    assert set(Counter(row["semantic_family_id"] for row in dev).values()) == {4}


def test_stage2_route_boundary_has_no_holdout_contamination() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    contamination = manifest["validation"]["contamination"]
    assert contamination["similarity_version"] == "utf8-byte-ngram-cosine.v1"
    assert contamination["exact_holdout_overlap_count"] == 0
    assert contamination["maximum_holdout_similarity"] < contamination["threshold_exclusive"]
