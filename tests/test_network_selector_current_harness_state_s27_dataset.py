from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_state_s27_v1"
EXPECTED = {
    "rwkv_state_tuning.train.requires_target_suffix.jsonl": (2000, "4f73700ea8a87901b6f6bc99118a15ae84b78615ad005882d2b124ca89d94d8a"),
    "rwkv_state_tuning.dev.requires_target_suffix.jsonl": (500, "19959ee3b9abb895966b4669d2cc0557ae5be876bcad0e780d7d9662e619a8bc"),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s27_state_rows_are_exact_persistent_target_suffix_examples() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test_excluded": 500}
    assert manifest["s26_test_used"] is False
    assert manifest["s23_used"] is False
    assert manifest["training_contract"] == {
        "ctx_len": 1536, "epoch_count": 1, "epoch_steps": 2000,
        "jsonl_bos_token_id": 0, "loss_mask": "target_suffix",
        "persistent_history_replayed": True, "seed": 887, "step_save": 500,
    }
    tokenizer = RWKVTokenizer()
    families: dict[str, set[str]] = {}
    for filename, (expected_rows, expected_sha) in EXPECTED.items():
        path = DATASET / filename
        assert sha256_file(path) == expected_sha
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        assert len(rows) == expected_rows
        per_label = 80 if ".train." in filename else 20
        assert Counter(row["label"] for row in rows) == Counter(
            {label: per_label for label in NETWORK_EXACT_TOOL_LABELS}
        )
        assert all(row["persistent_history_replayed"] is True for row in rows)
        assert all(row["generated_rwkv_text"] is False for row in rows)
        assert all(row["loss_mask"] == "target_suffix" for row in rows)
        for row in rows:
            assert row["text"] == row["prompt"] + row["target"]
            assert row["target"] == "\nSelectorLabelV2: " + row["label"]
            assert tokenizer.encode(row["text"]) == tokenizer.encode(row["prompt"]) + tokenizer.encode(row["target"])
            assert row["text_tokens_including_bos"] <= 1537
        split = "train" if ".train." in filename else "dev"
        families[split] = {row["semantic_family_id"] for row in rows}
    assert not families["train"] & families["dev"]
