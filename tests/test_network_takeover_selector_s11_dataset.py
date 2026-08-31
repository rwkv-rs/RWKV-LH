from __future__ import annotations

import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s11_v1"


def test_s11_dataset_is_fixed_hierarchical_and_non_generative() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [json.loads(line) for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    assert manifest["dataset_version"] == "rwkv-lh.network-takeover-selector.s11.v1"
    assert len(rows) == 2000
    assert Counter(row["split"] for row in rows) == Counter(train=1506, dev=289, test=205)
    assert set(row["label"] for row in rows) == {"web_search", "connector_lookup", "DEFER"}
    assert all(row["generated_rwkv_text"] is False for row in rows)
    assert len({row["sample_id"] for row in rows}) == len(rows)
    assert len({row["rendered_input"] for row in rows}) == len(rows)
    assert manifest["validation"]["contamination"]["maximum"]["score"] < 0.75


def test_s11_selector_input_excludes_executor_and_provider_payloads() -> None:
    rows = [json.loads(line) for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()]
    for row in rows:
        rendered = row["rendered_input"]
        assert rendered.startswith("NetworkTakeoverQueryV1: ")
        for forbidden in (
            '"parameter_schema"', '"result"', '"history"', '"rationale"',
            '"executor_state"', '"executor_text"', '"expected_label"',
        ):
            assert forbidden not in rendered
