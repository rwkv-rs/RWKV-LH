from __future__ import annotations

import json

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
    compact_selector_bootstrap_payload,
    compact_selector_input_digest,
    compact_selector_input_payload,
    compact_selector_menu_digest,
    compact_selector_tool_menu,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


def selector_input() -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        task_request="Search the public web for the current release status.",
        stage_objective="CurrentDirectStageV1: choose one operation.",
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=1,
            action_index=1,
            succeeded_operations=("read_file",),
        ),
    )


def test_compact_menu_keeps_all_tools_without_parameter_schemas() -> None:
    menu = compact_selector_tool_menu()
    assert tuple(item["name"] for item in menu) == NETWORK_EXACT_TOOL_LABELS
    assert all(set(item) == {"name", "description"} for item in menu)
    assert all(item["description"].strip() for item in menu)
    assert max(len(item["description"].encode("utf-8")) for item in menu) <= 100
    assert compact_selector_menu_digest() == compact_selector_menu_digest()


def test_compact_protocol_places_literal_task_after_the_fixed_menu() -> None:
    value = selector_input()
    bootstrap = render_compact_selector_bootstrap(value)
    menu_prefix, task_prefix = bootstrap.split("\nSelectorTaskV3: ", 1)
    menu = json.loads(menu_prefix.removeprefix("SelectorMenuV3: "))
    task = json.loads(task_prefix)
    assert menu["schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
    assert menu["menu_schema_version"] == COMPACT_SELECTOR_MENU_SCHEMA_VERSION
    assert menu["menu_digest"] == compact_selector_menu_digest()
    assert tuple(item["name"] for item in menu["tools"]) == NETWORK_EXACT_TOOL_LABELS
    assert task == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "task_request": value.task_request,
    }
    assert bootstrap.rindex(value.task_request) > bootstrap.rindex("ABSTAIN")
    assert "parameters" not in bootstrap
    assert "arguments" not in bootstrap
    assert "executor" not in bootstrap.lower()


def test_compact_step_contains_only_current_stage_and_bounded_progress() -> None:
    value = selector_input()
    rendered = render_compact_selector_step(value)
    payload = json.loads(rendered.removeprefix("SelectorStepV3: "))
    assert payload == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "stage_objective": value.stage_objective,
        "stage_role": "work",
        "progress": value.progress.to_dict(),
    }
    assert value.task_request not in rendered
    assert "result" not in rendered.lower()


def test_compact_payload_and_digest_are_shared_canonical_v3_identity() -> None:
    value = selector_input()
    payload = compact_selector_input_payload(value)

    assert payload == {
        **compact_selector_bootstrap_payload(value),
        "progress": value.progress.to_dict(),
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "stage_objective": value.stage_objective,
        "stage_role": value.stage_role,
    }
    assert payload["menu_digest"] == compact_selector_menu_digest()
    assert compact_selector_input_digest(value) == canonical_digest(payload)
