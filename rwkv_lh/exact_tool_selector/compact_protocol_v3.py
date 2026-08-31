"""Compact, contrastive 25-class Selector input protocol.

V2 remains immutable for prior experiments. V3 preserves the same class set
and Selector/Executor boundary, but places the fixed menu before the literal
task so a recurrent model sees the current task most recently.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json


COMPACT_SELECTOR_INPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-input.v3"
COMPACT_SELECTOR_MENU_SCHEMA_VERSION = "rwkv-lh.exact-tool-menu.v3"

_COMPACT_DESCRIPTIONS = {
    "list_directory": "Local metadata only: list bounded paths, types, and sizes; never file contents.",
    "search_text": "Local text only: find regex or literal lines; never search the public web.",
    "read_file": "Read a bounded byte range from one local non-JSON UTF-8 file.",
    "read_json": "Parse one local JSON file and read bounded canonical JSON.",
    "file_digest": "Observe one local file's SHA-256 and byte size without reading or changing it.",
    "write_file": "Create or replace one complete local non-JSON UTF-8 file.",
    "write_json": "Create or replace one complete local JSON value.",
    "patch_json": "Update named top-level JSON keys while preserving all unspecified keys.",
    "replace_text": "Replace one exact text occurrence inside a local UTF-8 file.",
    "remove_line": "Remove one complete exact line from a local UTF-8 file.",
    "append_file": "Append text after the existing bytes of a local file.",
    "make_directory": "Create one local workspace directory, not a file.",
    "copy_file": "Copy exact file bytes to a new path and keep the source.",
    "move_file": "Move or rename a file so the old source path disappears.",
    "delete_file": "Delete one explicitly scoped local workspace path.",
    "bind_evidence": "Bind an already observed local line span with its locator and exact quote.",
    "check_command": "Run a read-only local test, linter, status, or inspection argv.",
    "run_command": "Run a local argv that may intentionally modify workspace contents.",
    "web_search": "Search or fetch the public web; never search local workspace files.",
    "connector_lookup": "Query a structured public repository, package, paper, weather, or alert record.",
    "calculator": "Evaluate arithmetic using operands that are already known.",
    "date_diff": "Compute calendar-day distance between two already known ISO dates.",
    "current_time": "Observe the current clock time for one IANA timezone.",
    "final_answer": "Return the user-facing result only when no further tool call is needed.",
    "ABSTAIN": "Choose no tool when the next operation is ambiguous, unsupported, unsafe, or unknowable.",
}


def compact_selector_tool_menu() -> tuple[dict[str, str], ...]:
    """Return all 25 names with compact mutually contrastive descriptions."""

    if set(_COMPACT_DESCRIPTIONS) != set(NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("compact Selector descriptions differ from class order")
    return tuple(
        {"name": name, "description": _COMPACT_DESCRIPTIONS[name]}
        for name in NETWORK_EXACT_TOOL_LABELS
    )


def compact_selector_menu_digest() -> str:
    return canonical_digest(
        {
            "schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in compact_selector_tool_menu()],
        }
    )


def compact_selector_bootstrap_payload(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the canonical persisted V3 menu/task payload."""

    source = _input_values(value)
    return {
        "menu_digest": compact_selector_menu_digest(),
        "menu_schema_version": COMPACT_SELECTOR_MENU_SCHEMA_VERSION,
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "task_request": source["task_request"],
        "tools": [dict(item) for item in compact_selector_tool_menu()],
    }


def compact_selector_step_payload(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> dict[str, Any]:
    source = _input_values(value)
    return {
        "progress": source["progress"],
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "stage_objective": source["stage_objective"],
        "stage_role": source["stage_role"],
    }


def compact_selector_input_payload(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> dict[str, Any]:
    """Return the complete canonical V3 identity without changing rendering."""

    return {
        **compact_selector_bootstrap_payload(value),
        **compact_selector_step_payload(value),
    }


def compact_selector_input_digest(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> str:
    return canonical_digest(compact_selector_input_payload(value))


def _input_values(value: NetworkSelectorInput | Mapping[str, Any]) -> dict[str, Any]:
    source = value.to_dict() if isinstance(value, NetworkSelectorInput) else dict(value)
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


def render_compact_selector_bootstrap(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> str:
    """Render menu first and immutable literal task last, without schemas/args."""

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
        "task_request": payload["task_request"],
    }
    return (
        "SelectorMenuV3: "
        + canonical_json(menu)
        + "\nSelectorTaskV3: "
        + canonical_json(task)
    )


def render_compact_selector_step(
    value: NetworkSelectorInput | Mapping[str, Any],
) -> str:
    return "SelectorStepV3: " + canonical_json(
        compact_selector_step_payload(value)
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
