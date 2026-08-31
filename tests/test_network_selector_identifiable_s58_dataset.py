from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
S56 = ROOT / "data/datasets/rwkv_lh_network_selector_full_request_last_s56_v1/cases.jsonl"
S58 = ROOT / "data/datasets/rwkv_lh_network_selector_identifiable_s58_v1/cases.jsonl"
MANIFEST = S58.with_name("manifest.json")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s58_only_changes_the_unidentifiable_family_wide_labels() -> None:
    assert sha256_file(S58) == "d49f938eb67858f3f17cf7e47672f5ec1b1d01918bd6e0b48e3dd1212399ebf0"
    assert sha256_file(MANIFEST) == "681d6cf2e5cf1a017933912bb0b92ee8aa77bda445d3ec0a78880a6f4be4fa4f"
    source_rows = [json.loads(line) for line in S56.read_text(encoding="utf-8").splitlines()]
    rows = [json.loads(line) for line in S58.read_text(encoding="utf-8").splitlines()]
    assert len(source_rows) == len(rows) == 18293

    corrections: Counter[str] = Counter()
    for source, row in zip(source_rows, rows, strict=True):
        assert row["sample_id"] == source["sample_id"]
        assert row["split"] == source["split"]
        assert row["rendered_input"] == source["rendered_input"]
        assert row["rendered_input_sha256"] == source["rendered_input_sha256"]
        assert row["source_label"] == source["label"]
        if row["label_corrected"]:
            corrections[row["split"]] += 1
            assert row["source_dataset"] == "s55"
            assert row["source_family"] == "discount_ledger_release"
            assert row["trajectory_position"] == 0
            assert source["label"] == "list_directory"
            assert row["label"] == "read_file"
        else:
            assert row["label"] == source["label"]
    assert corrections == {"train": 20, "dev": 6, "test": 6}
