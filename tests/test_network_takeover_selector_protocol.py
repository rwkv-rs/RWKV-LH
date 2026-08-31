from __future__ import annotations

import json
from pathlib import Path

import pytest

from rwkv_lh.exact_tool_selector.takeover_protocol_v4 import (
    NetworkTakeoverInput,
    NetworkTakeoverProgress,
    network_takeover_tool_menu,
)


ROOT = Path(__file__).resolve().parents[1]


def test_takeover_protocol_matches_frozen_s10_dataset() -> None:
    source = json.loads(
        (ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/samples.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    frozen = json.loads(
        (ROOT / "data/datasets/rwkv_lh_network_takeover_selector_s10_v1/cases.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()[0]
    )
    value = source["input"]
    selector_input = NetworkTakeoverInput(
        str(value["request"]),
        NetworkTakeoverProgress(
            mode=str(value["mode"]),
            evidence_state=str(value["evidence_state"]),
            policy_state=str(value["policy_state"]),
        ),
    )
    assert selector_input.render() == frozen["rendered_input"]
    assert selector_input.digest == frozen["selector_input_sha256"]


def test_takeover_menu_has_only_three_names_and_descriptions() -> None:
    menu = network_takeover_tool_menu()
    assert tuple(item["name"] for item in menu) == (
        "web_search",
        "connector_lookup",
        "DEFER",
    )
    assert all(set(item) == {"name", "description"} for item in menu)


def test_fresh_takeover_cannot_claim_existing_evidence() -> None:
    with pytest.raises(ValueError, match="evidence_state=none"):
        NetworkTakeoverProgress(mode="fresh", evidence_state="evidence_partial")
