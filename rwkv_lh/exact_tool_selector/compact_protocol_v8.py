"""Frontier-only Selector protocol with one question at the byte tail."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    compact_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


COMPACT_SELECTOR_INPUT_SCHEMA_VERSION = (
    "rwkv-lh.exact-tool-selector-input.v8-frontier-question-tail"
)
COMPACT_SELECTOR_MENU_SCHEMA_VERSION = (
    "rwkv-lh.exact-tool-menu.v8-frontier-question-tail"
)


def compact_selector_menu_digest() -> str:
    return canonical_digest(
        {
            "schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in compact_selector_tool_menu()],
        }
    )


def _input_values(value: Any) -> dict[str, Any]:
    source = value.to_dict() if hasattr(value, "to_dict") else dict(value)
    current_requirement = str(source.get("stage_objective") or "").strip()
    stage_role = str(source.get("stage_role") or "").strip()
    progress = source.get("progress")
    if not current_requirement or not stage_role:
        raise ValueError("Selector v8 requires one current frontier and role")
    if not isinstance(progress, Mapping):
        raise ValueError("Selector v8 requires bounded progress materials")
    expected_progress = {
        "completed_stage_count",
        "action_index",
        "succeeded_operations",
        "failed_operations",
        "protocol_rejection_count",
    }
    if set(progress) != expected_progress:
        raise ValueError("Selector v8 progress fields changed")
    return {
        "current_requirement": current_requirement,
        "stage_role": stage_role,
        "progress": dict(progress),
    }


def compact_selector_bootstrap_payload(value: Any) -> dict[str, Any]:
    _input_values(value)
    return {
        "menu_digest": compact_selector_menu_digest(),
        "menu_schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "tools": [dict(item) for item in compact_selector_tool_menu()],
    }


def compact_selector_step_payload(value: Any) -> dict[str, Any]:
    source = _input_values(value)
    return {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "progress": source["progress"],
        "stage_role": source["stage_role"],
        # One role-pure question is the final semantic field. It contains only
        # the current frontier, never the complete Goal or another plan step.
        "current_question": (
            "For this current requirement only, rank the next tool intent and "
            "do not plan, fill parameters, audit, or answer the user.\n"
            f"Current requirement: {source['current_requirement']}"
        ),
    }


def compact_selector_input_payload(value: Any) -> dict[str, Any]:
    return {
        **compact_selector_bootstrap_payload(value),
        **compact_selector_step_payload(value),
    }


def compact_selector_input_digest(value: Any) -> str:
    return canonical_digest(compact_selector_input_payload(value))


def render_compact_selector_bootstrap(value: Any) -> str:
    payload = compact_selector_bootstrap_payload(value)
    return (
        "SelectorMenuV8: "
        + canonical_json(payload)
        + "\nSelectorRoleV8: "
        + json.dumps(
            {"schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION},
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        )
    )


def render_compact_selector_step(value: Any) -> str:
    payload = compact_selector_step_payload(value)
    if list(payload)[-1:] != ["current_question"]:
        raise RuntimeError("Selector v8 current question is not the final field")
    return "SelectorStepV8: " + json.dumps(
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
