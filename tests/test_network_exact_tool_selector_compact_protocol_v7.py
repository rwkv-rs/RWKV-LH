from __future__ import annotations

import hashlib
import json

from rwkv_lh.exact_tool_selector.compact_protocol_v7 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    SELECTOR_CURRENT_QUESTION,
    compact_selector_step_payload,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


def selector_input(action_index: int = 2) -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        task_request=(
            "Replace the complete JSON value and remove every obsolete field."
        ),
        stage_objective=(
            'CurrentDirectStageV1: {"latest_action":{"operation":"read_json",'
            '"success":true},"instruction":"Choose the next operation."}'
        ),
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=action_index,
            action_index=action_index,
            succeeded_operations=("read_json",),
        ),
    )


def test_v7_bootstrap_contains_menu_and_only_request_identity() -> None:
    value = selector_input()
    rendered = render_compact_selector_bootstrap(value)
    _, identity_text = rendered.split("\nSelectorTaskIdentityV7: ", 1)
    identity = json.loads(identity_text)

    assert identity == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "task_request_sha256": hashlib.sha256(
            value.task_request.encode("utf-8")
        ).hexdigest(),
    }
    assert value.task_request not in rendered
    assert "parameters" not in rendered


def test_v7_places_the_literal_requirement_at_the_byte_tail() -> None:
    value = selector_input()
    payload = compact_selector_step_payload(value)
    rendered = render_compact_selector_step(value)

    assert list(payload) == [
        "schema_version",
        "progress",
        "stage_role",
        "current_question",
    ]
    assert list(payload["current_question"]) == [
        "question",
        "current_stage",
        "complete_requirement",
    ]
    assert payload["current_question"] == {
        "question": SELECTOR_CURRENT_QUESTION,
        "current_stage": value.stage_objective,
        "complete_requirement": value.task_request,
    }
    assert rendered.count(value.task_request) == 1
    assert rendered.count(json.dumps(value.stage_objective)[1:-1]) == 1
    assert rendered.endswith(json.dumps(value.task_request) + "}}")
