from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage3_natural_route_stop_v1"


def read_jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def immutable_request(prompt: str) -> str:
    marker = "User: Task state: "
    start = prompt.index(marker) + len(marker)
    state, _end = json.JSONDecoder().raw_decode(prompt[start:])
    return state["immutable_request"]


def test_stage3_manifest_counts_digests_and_contamination_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == (
        "rwkv-lh.state-tuning.stage3-natural-route-stop.v1"
    )
    assert manifest["counts"] == {
        "train": 1400,
        "dev": 176,
        "train_semantic_families": 325,
        "dev_semantic_families": 44,
        "train_clusters": {
            "stable_selector_replay": 500,
            "natural_connector": 400,
            "ordinary_web": 100,
            "mixed_local_first": 200,
            "privacy_local_first": 200,
        },
        "dev_clusters": {
            "natural_connector": 64,
            "ordinary_web": 16,
            "mixed_local_first": 48,
            "privacy_local_first": 48,
        },
    }
    contamination = manifest["contamination"]
    assert contamination["similarity_version"] == "utf8-byte-ngram-cosine.v1"
    assert contamination["exact_holdout_overlap_count"] == 0
    assert contamination["maximum_holdout_similarity"] < 0.75
    for relative, metadata in manifest["files"].items():
        path = DATA / relative
        assert path.stat().st_size == metadata["bytes"]
        assert sha256(path) == metadata["sha256"]


def test_stage3_is_selector_only_target_suffix_and_family_isolated() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert len(train) == 1400
    assert len(dev) == 176
    assert Counter(row["failure_cluster"] for row in train) == {
        "stable_selector_replay": 500,
        "natural_connector": 400,
        "ordinary_web": 100,
        "mixed_local_first": 200,
        "privacy_local_first": 200,
    }
    for row in train + dev:
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["prompt_sha256"] for row in train + dev}) == 1576
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    assert not train_families.intersection(dev_families)


def test_stage3_natural_connector_requests_do_not_disclose_route_answer() -> None:
    rows = [
        row
        for row in read_jsonl(DATA / "stage_sft.train.jsonl")
        if row["failure_cluster"] == "natural_connector"
    ]
    assert len(rows) == 400
    for row in rows:
        request = immutable_request(row["prompt"]).casefold()
        assert row["target_operation"] == "connector_lookup"
        assert "select connector" not in request
        assert "选择 connector" not in request
        assert "选择connector" not in request
        assert "structured connector" not in request
        assert "rather than general web" not in request
        assert "不要改用普通网页" not in request


def test_stage3_replays_all_stage1_train_selectors_without_dev_leakage() -> None:
    source_train = read_jsonl(
        ROOT
        / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.train.jsonl"
    )
    source_dev = read_jsonl(
        ROOT
        / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.dev.jsonl"
    )
    stable = [
        row
        for row in read_jsonl(DATA / "stage_sft.train.jsonl")
        if row["failure_cluster"] == "stable_selector_replay"
    ]
    assert {row["prompt_sha256"] for row in stable} == {
        row["prompt_sha256"] for row in source_train
    }
    assert not {row["prompt_sha256"] for row in stable}.intersection(
        row["prompt_sha256"] for row in source_dev
    )
