"""Current 23-operation protocol for the fresh current-subtask Selector."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rwkv_lh.goal_state_protocols import selector_intent_v7
from rwkv_lh.model_io import canonical_digest, canonical_json

NETWORK_SELECTOR_INPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-input.v5"
NETWORK_SELECTOR_MENU_SCHEMA_VERSION = "rwkv-lh.exact-tool-menu.v3"

NETWORK_EXACT_TOOL_LABELS = (
    "list_directory",
    "search_text",
    "read_file",
    "read_json",
    "file_digest",
    "write_file",
    "write_json",
    "patch_json",
    "replace_text",
    "remove_line",
    "append_file",
    "make_directory",
    "copy_file",
    "move_file",
    "delete_file",
    "bind_evidence",
    "check_command",
    "run_command",
    "web_search",
    "connector_lookup",
    "calculator",
    "date_diff",
    "current_time",
)
NETWORK_SELECTOR_MENU_ORDER_IDS = ("canonical", "rotate_8", "rotate_17")
_NETWORK_SELECTOR_MENU_ROTATIONS = {
    "canonical": 0,
    "rotate_8": 8,
    "rotate_17": 17,
}

# These mutually contrastive descriptions are the frozen G1J Selector-Intent
# menu. They identify operation semantics without exposing parameter schemas.
_NETWORK_TOOL_DESCRIPTIONS = {
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
}


def network_selector_label_order(
    menu_order_id: str = "canonical",
) -> tuple[str, ...]:
    """Return one of the three pre-registered deterministic menu orders."""

    selected_id = str(menu_order_id or "").strip()
    if selected_id not in _NETWORK_SELECTOR_MENU_ROTATIONS:
        raise ValueError(f"unknown network Selector menu order: {selected_id!r}")
    offset = _NETWORK_SELECTOR_MENU_ROTATIONS[selected_id]
    return NETWORK_EXACT_TOOL_LABELS[offset:] + NETWORK_EXACT_TOOL_LABELS[:offset]


def network_selector_tool_menu(
    menu_order_id: str = "canonical",
) -> tuple[dict[str, str], ...]:
    """Return one fixed 23-name permutation and no parameter schemas."""

    if set(_NETWORK_TOOL_DESCRIPTIONS) != set(NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("network Selector descriptions differ from class order")
    return tuple(
        {"name": name, "description": _NETWORK_TOOL_DESCRIPTIONS[name]}
        for name in network_selector_label_order(menu_order_id)
    )


def network_selector_menu_digest(
    menu: Sequence[Mapping[str, str]] | None = None,
) -> str:
    selected = network_selector_tool_menu() if menu is None else menu
    return canonical_digest(
        {
            "schema_version": NETWORK_SELECTOR_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in selected],
        }
    )


@dataclass(frozen=True)
class NetworkSelectorInput:
    """One independent current subtask consumed from the learned initial State."""

    current_subtask: Mapping[str, Any]
    menu: tuple[Mapping[str, str], ...]
    current_progress: Mapping[str, Any] | None = None
    eligible_labels: tuple[str, ...] = NETWORK_EXACT_TOOL_LABELS
    menu_order_id: str = "canonical"
    schema_version: str = NETWORK_SELECTOR_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != NETWORK_SELECTOR_INPUT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported network Selector input schema: {self.schema_version}"
            )
        subtask = dict(self.current_subtask)
        expected_subtask_fields = {
            "objective",
            "phase",
            "read_roots",
            "write_roots",
            "success_evidence",
            "constraints",
        }
        if set(subtask) != expected_subtask_fields:
            raise ValueError("network Selector current subtask fields mismatch")
        if not str(subtask["objective"] or "").strip():
            raise ValueError("network Selector current subtask requires an objective")
        if subtask["phase"] not in {
            "observe",
            "mutate",
            "execute",
            "derive_evidence",
        }:
            raise ValueError("network Selector current subtask phase is invalid")
        for name in ("read_roots", "write_roots", "success_evidence", "constraints"):
            values = subtask[name]
            if not isinstance(values, list) or any(
                not isinstance(item, str) or not item.strip() for item in values
            ):
                raise ValueError(f"network Selector current subtask {name} is invalid")
        if not subtask["success_evidence"]:
            raise ValueError("network Selector current subtask requires success evidence")
        progress = (
            None
            if self.current_progress is None
            else dict(self.current_progress)
        )
        if progress is not None:
            # The single production Selector input contract.  Production,
            # StateTune data generation, and acceptance evaluation share this
            # current role validator; older progress shapes are rejected.
            progress = dict(
                selector_intent_v7.validate_progress(
                    progress,
                    read_roots=subtask["read_roots"],
                    write_roots=subtask["write_roots"],
                )
            )
            progress["last_action"] = (
                None
                if progress["last_action"] is None
                else dict(progress["last_action"])
            )
        if any(set(item) != {"name", "description"} for item in self.menu):
            raise ValueError(
                "network Selector menu may contain only name and description"
            )
        normalized = tuple(
            {
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
            }
            for item in self.menu
        )
        expected_menu_order = network_selector_label_order(self.menu_order_id)
        if tuple(item["name"] for item in normalized) != expected_menu_order:
            raise ValueError(
                "network Selector menu labels/order differ from the declared order"
            )
        if any(not item["description"].strip() for item in normalized):
            raise ValueError("network Selector menu descriptions must be non-empty")
        eligible = tuple(str(item) for item in self.eligible_labels)
        if not eligible or len(set(eligible)) != len(eligible):
            raise ValueError("network Selector eligible labels must be non-empty and unique")
        unknown = set(eligible) - set(NETWORK_EXACT_TOOL_LABELS)
        if unknown:
            raise ValueError(
                f"network Selector eligibility contains unknown labels: {sorted(unknown)}"
            )
        expected_order = tuple(
            label for label in NETWORK_EXACT_TOOL_LABELS if label in set(eligible)
        )
        if eligible != expected_order:
            raise ValueError("network Selector eligible labels differ from class order")
        object.__setattr__(self, "menu", normalized)
        object.__setattr__(self, "eligible_labels", eligible)
        object.__setattr__(self, "current_subtask", subtask)
        object.__setattr__(self, "current_progress", progress)

    @classmethod
    def create(
        cls,
        *,
        current_subtask: Mapping[str, Any],
        current_progress: Mapping[str, Any] | None = None,
        eligible_labels: Sequence[str] = NETWORK_EXACT_TOOL_LABELS,
        menu_order_id: str = "canonical",
    ) -> NetworkSelectorInput:
        return cls(
            current_subtask=dict(current_subtask),
            menu=network_selector_tool_menu(menu_order_id),
            current_progress=(
                None if current_progress is None else dict(current_progress)
            ),
            eligible_labels=tuple(str(item) for item in eligible_labels),
            menu_order_id=str(menu_order_id),
        )

    @property
    def menu_digest(self) -> str:
        return network_selector_menu_digest(self.menu)

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "schema_version": NETWORK_SELECTOR_INPUT_SCHEMA_VERSION,
            "menu_schema_version": NETWORK_SELECTOR_MENU_SCHEMA_VERSION,
            "menu_digest": self.menu_digest,
            "tools": [dict(item) for item in self.menu],
        }

    def step_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": NETWORK_SELECTOR_INPUT_SCHEMA_VERSION,
            "current_subtask": dict(self.current_subtask),
        }
        if self.current_progress is not None:
            payload["current_progress"] = dict(self.current_progress)
        return payload

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.bootstrap_payload(),
            **self.step_payload(),
            "eligible_labels": list(self.eligible_labels),
            "menu_order_id": self.menu_order_id,
        }

    def render_bootstrap(self) -> str:
        return "SelectorBootstrapV2: " + canonical_json(self.bootstrap_payload())

    def render_step(self) -> str:
        return "SelectorStepV2: " + canonical_json(self.step_payload())

    def render(self) -> str:
        return self.render_bootstrap() + "\n" + self.render_step()


def validate_network_label(label: str) -> str:
    selected = str(label or "")
    if selected not in NETWORK_EXACT_TOOL_LABELS:
        raise ValueError(f"unknown network Selector label: {selected!r}")
    return selected


__all__ = [
    "NETWORK_EXACT_TOOL_LABELS",
    "NETWORK_SELECTOR_INPUT_SCHEMA_VERSION",
    "NETWORK_SELECTOR_MENU_ORDER_IDS",
    "NETWORK_SELECTOR_MENU_SCHEMA_VERSION",
    "NetworkSelectorInput",
    "network_selector_label_order",
    "network_selector_menu_digest",
    "network_selector_tool_menu",
    "validate_network_label",
]
