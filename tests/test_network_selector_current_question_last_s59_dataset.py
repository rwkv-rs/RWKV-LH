from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v6 import SELECTOR_CURRENT_QUESTION


ROOT = Path(__file__).resolve().parents[1]
S58 = ROOT / "data/datasets/rwkv_lh_network_selector_identifiable_s58_v1/cases.jsonl"
S59 = ROOT / "data/datasets/rwkv_lh_network_selector_current_question_last_s59_v1/cases.jsonl"
MANIFEST = S59.with_name("manifest.json")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s59_preserves_labels_and_places_the_live_question_at_the_tail() -> None:
    assert sha256_file(S59) == "b2f9367a1d4707d74ccb511d3bf2a3ad99cf56ee18691e91200260ccd3ec3654"
    assert sha256_file(MANIFEST) == "483dc9f750e948d8a42c575714a4c177681d55b74f9606d718a8838a856daede"
    source_rows = [json.loads(line) for line in S58.read_text(encoding="utf-8").splitlines()]
    rows = [json.loads(line) for line in S59.read_text(encoding="utf-8").splitlines()]
    assert len(source_rows) == len(rows) == 18293

    for source, row in zip(source_rows, rows, strict=True):
        assert row["source_sample_id"] == source["sample_id"]
        assert row["label"] == source["label"]
        assert row["split"] == source["split"]
        payload = json.loads(row["step"].removeprefix("SelectorStepV6: "))
        assert list(payload)[-1] == "current_question"
        assert list(payload["current_question"])[-1] == "question"
        assert payload["current_question"]["question"] == SELECTOR_CURRENT_QUESTION
        assert row["rendered_input"].endswith(
            json.dumps(SELECTOR_CURRENT_QUESTION) + "}}"
        )
