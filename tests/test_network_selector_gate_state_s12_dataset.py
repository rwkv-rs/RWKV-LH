from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_gate_state_s12_v1"


def test_s12_gate_state_export_is_small_exact_and_serving_parity() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"] == {"dev": 275, "train": 1467}
    assert manifest["validation"]["maximum_prompt_tokens_including_bos"] <= 384
    assert manifest["training_contract"] == {
        "ctx_len": 512, "epoch_steps": 1467, "jsonl_bos_token_id": 0,
        "loss_mask": "target_suffix", "seed": 843, "step_save": 489,
    }
    for split, expected in (("train", 1467), ("dev", 275)):
        path = DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == expected
        assert Counter(row["label"] for row in rows) == Counter(manifest["label_counts"][split])
        assert all(row["text"] == row["prompt"] + row["target"] for row in rows)
        assert all(row["target"] == f"\nGateLabelV1: {row['label']}" for row in rows)
        assert all(row["generated_rwkv_text"] is False for row in rows)
