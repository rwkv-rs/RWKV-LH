from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / (
    "data/datasets/rwkv_lh_network_selector_true_trajectory_state_s31_v1"
)
EXPECTED = {
    "rwkv_state_tuning.train.requires_target_suffix.jsonl": (
        2000,
        "c3587e3f713705f3c5d9e36bf8ba099fcf5d73f31164dd9b5d88a2381580e48c",
    ),
    "rwkv_state_tuning.dev.requires_target_suffix.jsonl": (
        500,
        "05b32c12ecc83e03d8ea2c877b70f15e80796197b8ddb90c6545703fe35cba4c",
    ),
}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_s31_manifest_freezes_true_trajectory_state_contract() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["counts"] == {
        "train": 2000,
        "dev": 500,
        "test_excluded": 500,
    }
    assert manifest["training_contract"] == {
        "ctx_len": 1536,
        "epoch_count": 1,
        "epoch_steps": 2000,
        "jsonl_bos_token_id": 0,
        "loss_mask": "target_suffix",
        "parent_state": "zero",
        "persistent_history_replayed": True,
        "seed": 1031,
        "step_save": 500,
    }
    assert manifest["dev_optimizer_use"] is False
    assert manifest["s30_test_used"] is False
    assert manifest["s28_used_for_state_training"] is False
    assert manifest["s23_ecra_used"] is False
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest[
        "generator"
    ]["sha256"]
    assert sha256_file(ROOT / manifest["preregistration"]["path"]) == manifest[
        "preregistration"
    ]["sha256"]


def test_s31_rows_are_balanced_exact_persistent_target_suffix_examples() -> None:
    tokenizer = RWKVTokenizer()
    families: dict[str, set[str]] = {}
    prompts: set[str] = set()
    for filename, (expected_rows, expected_sha) in EXPECTED.items():
        path = DATASET / filename
        assert sha256_file(path) == expected_sha
        rows = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
        ]
        assert len(rows) == expected_rows
        split = "train" if ".train." in filename else "dev"
        per_label = 80 if split == "train" else 20
        per_language = 1000 if split == "train" else 250
        assert Counter(row["label"] for row in rows) == Counter(
            {label: per_label for label in NETWORK_EXACT_TOOL_LABELS}
        )
        assert Counter(row["language"] for row in rows) == {
            "en": per_language,
            "zh": per_language,
        }
        for row in rows:
            assert row["source_split"] == split
            assert row["persistent_history_replayed"] is True
            assert row["generated_rwkv_text"] is False
            assert row["contains_parameter_schemas"] is False
            assert row["contains_full_tool_results"] is False
            assert row["contains_executor_text"] is False
            assert row["loss_mask"] == "target_suffix"
            assert row["jsonl_bos_token_id"] == 0
            assert row["target"] == "\nSelectorLabelV3: " + row["label"]
            assert row["text"] == row["prompt"] + row["target"]
            assert hashlib.sha256(row["prompt"].encode("utf-8")).hexdigest() == row[
                "prompt_sha256"
            ]
            assert tokenizer.encode(row["text"]) == tokenizer.encode(
                row["prompt"]
            ) + tokenizer.encode(row["target"])
            assert row["text_tokens_including_bos"] <= 1537
            assert row["prompt_sha256"] not in prompts
            prompts.add(row["prompt_sha256"])
        families[split] = {row["semantic_family_id"] for row in rows}
    assert len(prompts) == 2500
    assert not families["train"] & families["dev"]
