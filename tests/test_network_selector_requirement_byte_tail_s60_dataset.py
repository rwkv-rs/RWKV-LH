from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v7 import SELECTOR_CURRENT_QUESTION


ROOT = Path(__file__).resolve().parents[1]
S58 = ROOT / "data/datasets/rwkv_lh_network_selector_identifiable_s58_v1/cases.jsonl"
S60 = ROOT / "data/datasets/rwkv_lh_network_selector_requirement_byte_tail_s60_v1/cases.jsonl"
MANIFEST = S60.with_name("manifest.json")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s60_preserves_labels_and_places_the_literal_requirement_at_the_tail() -> None:
    assert sha256_file(S60) == "3b60bf7fd69a2d085480ffcac4b31eca0655e38a3a67bf2f308660f629ea3faf"
    assert sha256_file(MANIFEST) == "16d05f9a7e4e5c94f3f314ec5848384b96b95045609fde25d92cfb3d497be76f"
    source_rows = [json.loads(line) for line in S58.read_text(encoding="utf-8").splitlines()]
    rows = [json.loads(line) for line in S60.read_text(encoding="utf-8").splitlines()]
    assert len(source_rows) == len(rows) == 18293

    for source, row in zip(source_rows, rows, strict=True):
        assert row["source_sample_id"] == source["sample_id"]
        assert row["label"] == source["label"]
        assert row["split"] == source["split"]
        payload = json.loads(row["step"].removeprefix("SelectorStepV7: "))
        question = payload["current_question"]
        assert list(payload)[-1] == "current_question"
        assert list(question) == ["question", "current_stage", "complete_requirement"]
        assert question["question"] == SELECTOR_CURRENT_QUESTION
        assert question["complete_requirement"] == source["step_payload"]["current_requirement"]
        assert row["rendered_input"].endswith(
            json.dumps(question["complete_requirement"], ensure_ascii=False) + "}}"
        )
