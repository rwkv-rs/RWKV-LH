from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_state_s25_v1"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s25_uses_only_current_harness_train_dev_and_exact_target_suffix() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    tokenizer = RWKVTokenizer()
    by_split = {
        split: [json.loads(line) for line in (DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl").read_text(encoding="utf-8").splitlines()]
        for split in ("train", "dev")
    }
    assert {split: len(rows) for split, rows in by_split.items()} == {"train": 2000, "dev": 276}
    assert manifest["counts"] == {"train": 2000, "dev": 276, "test_excluded": 250}
    assert manifest["s24_test_used"] is False
    assert manifest["s23_used"] is False
    assert manifest["validation"]["maximum_text_tokens_including_bos"] <= 1217
    for split, rows in by_split.items():
        path = DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        assert sha256_file(path) == manifest["files"][path.name]["sha256"]
        assert set(row["label"] for row in rows) == set(NETWORK_EXACT_TOOL_LABELS)
        assert Counter(row["label"] for row in rows) == Counter(manifest["label_counts"][split])
        for row in rows:
            assert row["text"] == row["prompt"] + row["target"]
            assert row["target"] == "\nSelectorLabelV2: " + row["label"]
            assert row["prompt"].startswith("SelectorBootstrapV2: ")
            assert "\nSelectorStepV2: " in row["prompt"]
            assert tokenizer.encode(row["text"]) == tokenizer.encode(row["prompt"]) + tokenizer.encode(row["target"])
            assert row["loss_mask"] == "target_suffix"
            assert row["jsonl_bos_token_id"] == 0
            assert row["generated_rwkv_text"] is False
