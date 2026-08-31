from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_STAGE_PROJECTION_VERSION,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_s23_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_s23_is_fixed_current_harness_projection_without_executor_content() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "decision_points.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert manifest["rows"] == len(rows) == 245
    assert manifest["case_count"] == 120
    assert manifest["selector_projection_version"] == (
        SELECTOR_STAGE_PROJECTION_VERSION
    )
    assert _sha256(DATASET / "decision_points.jsonl") == (
        manifest["records"]["sha256"]
    )
    assert _sha256(ROOT / manifest["generator"]["path"]) == (
        manifest["generator"]["sha256"]
    )
    assert Counter(row["phase"] for row in rows) == {
        "first": 120,
        "continuation": 125,
    }
    assert sum(bool(row["historical_exact"]) for row in rows) == 182
    assert {row["label"] for row in rows} <= set(NETWORK_EXACT_TOOL_LABELS)
    assert len({row["sample_id"] for row in rows}) == len(rows)

    for row in rows:
        selector_input = row["selector_input"]
        assert row["selector_input_digest"] == canonical_digest(selector_input)
        assert all(set(tool) == {"name", "description"} for tool in selector_input["tools"])
        assert "parameters" not in row["bootstrap"]
        assert "arguments" not in row["step"]
        assert "result" not in row["step"]
        assert row["full_result_content_in_selector_input"] is False
        assert row["tool_schema_in_selector_input"] is False
        assert row["executor_text_in_selector_input"] is False
        step = json.loads(row["step"].removeprefix("SelectorStepV2: "))
        stage = json.loads(
            step["stage_objective"].removeprefix("CurrentDirectStageV1: ")
        )
        assert stage["schema_version"] == SELECTOR_STAGE_PROJECTION_VERSION
        latest = stage["latest_action"]
        if row["selection_index"] == 0:
            assert latest is None
            assert row["source_action_result_digest"] == ""
        else:
            assert set(latest) <= {
                "sequence",
                "operation",
                "success",
                "outcome_type",
                "complete",
                "truncated",
            }
            assert len(row["source_action_result_digest"]) == 64
