from __future__ import annotations

import json

from rwkv_lh.exact_tool_selector.compact_protocol_v4 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
    compact_selector_bootstrap_payload,
    compact_selector_input_digest,
    compact_selector_input_payload,
    compact_selector_menu_digest,
    compact_selector_step_payload,
    compact_selector_tool_menu,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


def selector_input() -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        task_request="Search the public web for the current release status.",
        stage_objective="Choose the next operation from current evidence.",
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=1,
            action_index=1,
            succeeded_operations=("web_search",),
        ),
    )


def test_v4_keeps_only_names_and_descriptions_before_the_task() -> None:
    value = selector_input()
    bootstrap = render_compact_selector_bootstrap(value)
    menu_text, task_text = bootstrap.split("\nSelectorTaskV4: ", 1)
    menu = json.loads(menu_text.removeprefix("SelectorMenuV4: "))
    task = json.loads(task_text)

    assert menu["schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
    assert menu["menu_schema_version"] == COMPACT_SELECTOR_MENU_SCHEMA_VERSION
    assert menu["menu_digest"] == compact_selector_menu_digest()
    assert tuple(item["name"] for item in menu["tools"]) == NETWORK_EXACT_TOOL_LABELS
    assert all(set(item) == {"name", "description"} for item in compact_selector_tool_menu())
    assert list(task)[-1] == "task_request"
    assert task["task_request"] == value.task_request
    assert "parameters" not in bootstrap
    assert "arguments" not in bootstrap


def test_v4_places_the_live_selector_question_in_the_final_step_field() -> None:
    value = selector_input()
    rendered = render_compact_selector_step(value)
    payload = json.loads(rendered.removeprefix("SelectorStepV4: "))

    assert list(payload) == [
        "schema_version",
        "progress",
        "stage_role",
        "stage_objective",
    ]
    assert payload["stage_objective"] == value.stage_objective
    assert rendered.count(value.stage_objective) == 1
    assert value.task_request not in rendered


def test_v4_payload_digest_covers_the_request_last_identity() -> None:
    value = selector_input()
    payload = compact_selector_input_payload(value)

    assert payload == {
        **compact_selector_bootstrap_payload(value),
        **compact_selector_step_payload(value),
    }
    assert list(compact_selector_step_payload(value))[-1] == "stage_objective"
    assert compact_selector_input_digest(value) == canonical_digest(payload)
