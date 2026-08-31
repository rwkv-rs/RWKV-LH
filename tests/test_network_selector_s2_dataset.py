from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_residual_s2_v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_network_selector_s2_manifest_and_files_are_bound() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == "rwkv-lh.network-selector.residual-s2.v1"
    assert manifest["counts"] == {"train": 2000, "dev": 276, "test": 250}
    assert manifest["connector_label_to_other_train"] == "474:1526"
    assert manifest["natural_connector_cluster_to_other_train"] == "400:1600"
    assert manifest["validation"]["holdout_similarity"]["maximum"]["score"] < 0.75
    for name, record in manifest["files"].items():
        assert sha256_file(DATASET / name) == record["sha256"]
    for record in manifest["sources"].values():
        assert sha256_file(ROOT / record["path"]) == record["sha256"]
    assert sha256_file(ROOT / manifest["protocol"]["path"]) == manifest["protocol"]["sha256"]


def test_network_selector_s2_rows_preserve_splits_labels_and_boundaries() -> None:
    rows = [json.loads(line) for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert Counter(row["split"] for row in rows) == Counter(train=2000, dev=276, test=250)
    assert len({row["sample_id"] for row in rows}) == len(rows)
    assert len({row["rendered_input"] for row in rows}) == len(rows)
    families = {
        split: {row["semantic_family_id"] for row in rows if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert not families["train"] & families["dev"]
    assert not families["train"] & families["test"]
    assert not families["dev"] & families["test"]
    for split in families:
        assert {row["label"] for row in rows if row["split"] == split} == set(NETWORK_EXACT_TOOL_LABELS)
    train = [row for row in rows if row["split"] == "train"]
    assert Counter(row["failure_cluster"] for row in train) == Counter(
        stable_selector_replay=500,
        natural_connector=400,
        ordinary_web=100,
        mixed_local_first=200,
        privacy_local_first=200,
        class_retention=600,
    )
    assert Counter(row["label"] for row in train)["connector_lookup"] == 474
    assert all(row["generated_rwkv_text"] is False for row in rows)
    assert all("SelectorBootstrapV2: " in row["rendered_input"] for row in rows)
    assert all("\nSelectorStepV2: " in row["rendered_input"] for row in rows)


def test_network_selector_s2_state_exports_are_exact_target_suffixes() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    for split in ("train", "dev"):
        path = DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == manifest["counts"][split]
        assert Counter(row["label"] for row in rows) == Counter(manifest["label_counts"][split])
        for row in rows:
            assert row["target"] == f"\nSelectorLabelV2: {row['label']}"
            assert row["text"] == row["prompt"] + row["target"]
            assert row["loss_mask"] == "target_suffix"
            assert row["jsonl_bos_token_id"] == 0
            assert row["generated_rwkv_text"] is False
