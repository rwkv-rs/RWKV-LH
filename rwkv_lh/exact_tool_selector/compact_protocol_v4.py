"""Request-last compact 25-class Selector input protocol.

V3 remains immutable for prior artifacts.  V4 keeps the same role-pure
name/description menu and causal state layout, while making the current stage
objective the final field immediately before the RWKV continuation point.
"""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    compact_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


COMPACT_SELECTOR_INPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-input.v4-request-last"
COMPACT_SELECTOR_MENU_SCHEMA_VERSION = "rwkv-lh.exact-tool-menu.v4-request-last"


def compact_selector_menu_digest() -> str:
    return canonical_digest(
        {
            "schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in compact_selector_tool_menu()],
        }
    )


def _input_values(value: Any) -> dict[str, Any]:
    source = value.to_dict() if hasattr(value, "to_dict") else dict(value)
    task_request = str(source.get("task_request") or "")
    stage_objective = str(source.get("stage_objective") or "")
    stage_role = str(source.get("stage_role") or "")
    progress = source.get("progress")
    if not task_request.strip() or not stage_objective.strip() or not stage_role.strip():
        raise ValueError("compact Selector input requires task, stage, and role")
    if not isinstance(progress, Mapping):
        raise ValueError("compact Selector input requires progress")
    expected_progress = {
        "completed_stage_count",
        "action_index",
        "succeeded_operations",
        "failed_operations",
        "protocol_rejection_count",
    }
    if set(progress) != expected_progress:
        raise ValueError("compact Selector progress fields changed")
    return {
        "task_request": task_request,
        "stage_objective": stage_objective,
        "stage_role": stage_role,
        "progress": dict(progress),
    }


def compact_selector_bootstrap_payload(value: Any) -> dict[str, Any]:
    source = _input_values(value)
    return {
        "menu_digest": compact_selector_menu_digest(),
        "menu_schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "task_request": source["task_request"],
        "tools": [dict(item) for item in compact_selector_tool_menu()],
    }


def compact_selector_step_payload(value: Any) -> dict[str, Any]:
    """Return an insertion-ordered step with the live question last."""

    source = _input_values(value)
    return {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "progress": source["progress"],
        "stage_role": source["stage_role"],
        # Keep this field last.  Its byte position is part of the V4 protocol.
        "stage_objective": source["stage_objective"],
    }


def compact_selector_input_payload(value: Any) -> dict[str, Any]:
    return {
        **compact_selector_bootstrap_payload(value),
        **compact_selector_step_payload(value),
    }


def compact_selector_input_digest(value: Any) -> str:
    return canonical_digest(compact_selector_input_payload(value))


def render_compact_selector_bootstrap(value: Any) -> str:
    """Render the fixed menu first and immutable task at the bootstrap tail."""

    payload = compact_selector_bootstrap_payload(value)
    menu = {
        key: payload[key]
        for key in (
            "menu_digest",
            "menu_schema_version",
            "schema_version",
            "tools",
        )
    }
    task = {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        # Keep the immutable request closest to the end of the bootstrap.
        "task_request": payload["task_request"],
    }
    return (
        "SelectorMenuV4: "
        + canonical_json(menu)
        + "\nSelectorTaskV4: "
        + json.dumps(
            task,
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        )
    )


def render_compact_selector_step(value: Any) -> str:
    """Render context first and the current operation question last."""

    payload = compact_selector_step_payload(value)
    if list(payload)[-1] != "stage_objective":
        raise RuntimeError("Selector V4 current question is not the final field")
    return "SelectorStepV4: " + json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


__all__ = [
    "COMPACT_SELECTOR_INPUT_SCHEMA_VERSION",
    "COMPACT_SELECTOR_MENU_SCHEMA_VERSION",
    "compact_selector_bootstrap_payload",
    "compact_selector_input_digest",
    "compact_selector_input_payload",
    "compact_selector_menu_digest",
    "compact_selector_step_payload",
    "compact_selector_tool_menu",
    "render_compact_selector_bootstrap",
    "render_compact_selector_step",
]
