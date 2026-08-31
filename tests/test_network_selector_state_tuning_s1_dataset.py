from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_network_selector_state_tuning_s1_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_selector_s1_state_tuning_export_is_frozen_balanced_and_target_only() -> None:
    manifest = json.loads((DATA / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_version"] == "rwkv-lh.network-selector-state-tuning.s1.v1"
    assert manifest["source"]["sha256"] == "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
    assert manifest["counts"] == {"train": 6000, "dev": 750}
    assert manifest["test_source_rows_excluded"] == 750
    assert manifest["generated_rwkv_text_count"] == 0
    for split, per_label in (("train", 240), ("dev", 30)):
        path = DATA / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        rows = _rows(path)
        assert len(rows) == manifest["counts"][split]
        assert _sha256(path) == manifest["files"][path.name]["sha256"]
        assert Counter(row["label"] for row in rows) == Counter(
            {label: per_label for label in NETWORK_EXACT_TOOL_LABELS}
        )
        assert all(row["text"] == row["prompt"] + row["target"] for row in rows)
        assert all(
            row["target"] == f"\nSelectorLabelV2: {row['label']}" for row in rows
        )
        assert all(row["loss_mask"] == "target_suffix" for row in rows)
        assert all(row["jsonl_bos_token_id"] == 0 for row in rows)
        assert all(row["generated_rwkv_text"] is False for row in rows)
