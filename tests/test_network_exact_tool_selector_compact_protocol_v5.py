from __future__ import annotations

import hashlib
import json

from rwkv_lh.exact_tool_selector.compact_protocol_v5 import (
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
        stage_objective="Choose exactly one next direct operation.",
        stage_role="work",
        progress=NetworkSelectorProgress(
            completed_stage_count=1,
            action_index=1,
            succeeded_operations=("web_search",),
        ),
    )


def test_v5_bootstrap_contains_only_menu_and_request_identity() -> None:
    value = selector_input()
    rendered = render_compact_selector_bootstrap(value)
    menu_text, identity_text = rendered.split("\nSelectorTaskIdentityV5: ", 1)
    menu = json.loads(menu_text.removeprefix("SelectorMenuV5: "))
    identity = json.loads(identity_text)

    assert menu["schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
    assert menu["menu_schema_version"] == COMPACT_SELECTOR_MENU_SCHEMA_VERSION
    assert menu["menu_digest"] == compact_selector_menu_digest()
    assert tuple(item["name"] for item in menu["tools"]) == NETWORK_EXACT_TOOL_LABELS
    assert all(set(item) == {"name", "description"} for item in compact_selector_tool_menu())
    assert identity == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "task_request_sha256": hashlib.sha256(
            value.task_request.encode("utf-8")
        ).hexdigest(),
    }
    assert value.task_request not in rendered
    assert "parameters" not in rendered
    assert "arguments" not in rendered


def test_v5_places_complete_requirement_at_the_continuation_edge() -> None:
    value = selector_input()
    rendered = render_compact_selector_step(value)
    payload = json.loads(rendered.removeprefix("SelectorStepV5: "))

    assert list(payload) == [
        "schema_version",
        "progress",
        "stage_role",
        "stage_objective",
        "current_requirement",
    ]
    assert payload["current_requirement"] == value.task_request
    assert rendered.count(value.task_request) == 1
    assert rendered.endswith(json.dumps(value.task_request, ensure_ascii=False) + "}")


def test_v5_digest_covers_bootstrap_and_full_request_last_step() -> None:
    value = selector_input()
    payload = compact_selector_input_payload(value)

    assert payload == {
        **compact_selector_bootstrap_payload(value),
        **compact_selector_step_payload(value),
    }
    assert list(compact_selector_step_payload(value))[-1] == "current_requirement"
    assert compact_selector_input_digest(value) == canonical_digest(payload)
