from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.model_io import parse_tool_selection


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_tuning_stage4_balanced_boundary_v1"


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


def test_stage4_manifest_counts_digests_and_contamination_are_frozen() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == (
        "rwkv-lh.state-tuning.stage4-balanced-boundary.v1"
    )
    assert manifest["counts"] == {
        "train": 1140,
        "dev": 240,
        "train_semantic_families": 260,
        "dev_semantic_families": 60,
        "train_clusters": {
            "stable_selector_replay": 500,
            "natural_connector_paired": 80,
            "ordinary_web_hard_negative": 160,
            "local_only_network_hard_negative": 160,
            "mixed_local_first_natural": 160,
            "privacy_local_first_natural": 80,
        },
        "dev_clusters": {
            "natural_connector_paired": 48,
            "ordinary_web_hard_negative": 48,
            "local_only_network_hard_negative": 48,
            "mixed_local_first_natural": 64,
            "privacy_local_first_natural": 32,
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


def test_stage4_is_selector_only_target_suffix_and_family_isolated() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    dev = read_jsonl(DATA / "stage_sft.dev.jsonl")
    assert len(train) == 1140
    assert len(dev) == 240
    for row in train + dev:
        assert row["stage"] == "selector"
        assert row["prompt"].endswith("Assistant: ```json\n")
        assert row["text"] == row["prompt"] + row["target"]
        assert parse_tool_selection(row["target"]) == row["target_operation"]
    assert len({row["prompt_sha256"] for row in train + dev}) == 1380
    train_families = {row["semantic_family_id"] for row in train}
    dev_families = {row["semantic_family_id"] for row in dev}
    assert not train_families.intersection(dev_families)


def test_stage4_balances_connector_with_web_and_local_first_counterexamples() -> None:
    rows = read_jsonl(DATA / "stage_sft.train.jsonl")
    clustered = Counter(row["failure_cluster"] for row in rows)
    assert clustered["natural_connector_paired"] == 80
    assert clustered["ordinary_web_hard_negative"] == 160
    assert clustered["local_only_network_hard_negative"] == 160
    assert clustered["mixed_local_first_natural"] == 160
    assert clustered["privacy_local_first_natural"] == 80

    operations = Counter(
        row["target_operation"]
        for row in rows
        if row["failure_cluster"] != "stable_selector_replay"
    )
    assert operations["connector_lookup"] == 80
    assert operations["web_search"] == 160
    assert operations["read_file"] > 0
    assert operations["read_json"] > 0
    assert operations["patch_json"] > 0
    assert operations["check_command"] > 0
    assert operations["run_command"] > 0
    assert operations["file_digest"] > 0


def test_stage4_requests_do_not_disclose_route_labels_and_replays_stage1() -> None:
    train = read_jsonl(DATA / "stage_sft.train.jsonl")
    for row in train:
        if row["failure_cluster"] not in {
            "natural_connector_paired",
            "ordinary_web_hard_negative",
        }:
            continue
        request = immutable_request(row["prompt"]).casefold()
        assert "select connector" not in request
        assert "选择 connector" not in request
        assert "rather than general web" not in request
        assert "不要改用普通网页" not in request

    source_train = read_jsonl(
        ROOT
        / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.train.jsonl"
    )
    source_dev = read_jsonl(
        ROOT
        / "data/datasets/rwkv_lh_state_tuning_stage1_selector_v1/stage_sft.dev.jsonl"
    )
    stable = [
        row for row in train if row["failure_cluster"] == "stable_selector_replay"
    ]
    assert {row["prompt_sha256"] for row in stable} == {
        row["prompt_sha256"] for row in source_train
    }
    assert not {row["prompt_sha256"] for row in stable}.intersection(
        row["prompt_sha256"] for row in source_dev
    )
