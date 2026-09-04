"""Frozen 25-class protocol for the independent network-capable Selector.

The v1 protocol remains immutable for its recorded 20-class experiments.  This
v2 contract adds the five product operations introduced by the retrieval
kernel.  It deliberately contains names and descriptions only: parameter
schemas, Executor text, tool results, workspace listings, and reasoning are
outside the Selector boundary.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rwkv_lh.exact_tool_selector.protocol import canonical_digest, canonical_json

NETWORK_SELECTOR_INPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-input.v2"
NETWORK_SELECTOR_MENU_SCHEMA_VERSION = "rwkv-lh.exact-tool-menu.v2"
NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2 = "rwkv-lh.exact-tool-selector-output.v2"
NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-output.v3"
NETWORK_ABSTAIN_LABEL = "ABSTAIN"

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
    "final_answer",
    NETWORK_ABSTAIN_LABEL,
)

# These strings are frozen model inputs, copied from the authoritative product
# ActionDefinition registry at protocol registration time.  Keeping the menu
# here makes online/offline policy affect execution authorization, not the MLP
# class order or feature shape.
_NETWORK_TOOL_DESCRIPTIONS = {
    "list_directory": (
        "List bounded path, type, and size metadata only; never read file "
        "contents and never create or copy files."
    ),
    "search_text": (
        "Search workspace UTF-8 lines with regex or literal matching and "
        "return bounded ordered locators; never search the public web."
    ),
    "read_file": (
        "Observe one exact tokenizer-bounded UTF-8 byte range from an existing "
        "workspace file."
    ),
    "read_json": (
        "Parse an existing JSON file and observe a tokenizer-bounded range of "
        "its canonical JSON representation."
    ),
    "file_digest": (
        "Observe the SHA-256 digest and byte size of one existing workspace "
        "file without modifying it."
    ),
    "write_file": "Atomically create or replace one workspace UTF-8 text file.",
    "write_json": (
        "Atomically create or replace one complete JSON value; the Executor "
        "must provide the entire value."
    ),
    "patch_json": (
        "Update explicit top-level keys in an existing JSON object while "
        "preserving unspecified keys."
    ),
    "replace_text": (
        "Replace one exact text occurrence in an existing workspace UTF-8 file."
    ),
    "remove_line": "Remove one complete UTF-8 text line from an existing file.",
    "append_file": "Append UTF-8 text to an existing or new workspace file.",
    "make_directory": "Create one directory inside the workspace.",
    "copy_file": (
        "Copy one existing scoped file's exact bytes to a destination path."
    ),
    "move_file": (
        "Move or rename one existing scoped file to a destination path."
    ),
    "delete_file": "Delete one explicitly scoped workspace path.",
    "bind_evidence": (
        "Read an exact workspace line span and retain its source locator and quote."
    ),
    "check_command": (
        "Run a read-only test, linter, or inspection command using argv with "
        "shell disabled."
    ),
    "run_command": (
        "Run a potentially mutating local command using argv with shell disabled."
    ),
    "web_search": (
        "Search or fetch a public exact URL or the general web and return "
        "content-addressed evidence records."
    ),
    "connector_lookup": (
        "Query one structured public source for an exact repository, package, "
        "scholarly record, weather observation, or alert."
    ),
    "calculator": (
        "Evaluate one complete arithmetic expression whose operands are already known."
    ),
    "date_diff": (
        "Calculate the absolute calendar-day distance between two already known ISO dates."
    ),
    "current_time": "Observe the current clock reading for one IANA timezone.",
    "final_answer": (
        "End the run with a non-empty user-facing answer only when no further "
        "tool call is needed."
    ),
    NETWORK_ABSTAIN_LABEL: (
        "Select no operation because the current stage is ambiguous, unsupported, "
        "unsafe, or lacks enough observable information to choose exactly one tool."
    ),
}


def network_selector_tool_menu() -> tuple[dict[str, str], ...]:
    """Return the frozen 25 names/descriptions and no parameter schemas."""

    if set(_NETWORK_TOOL_DESCRIPTIONS) != set(NETWORK_EXACT_TOOL_LABELS):
        raise RuntimeError("network Selector descriptions differ from class order")
    return tuple(
        {"name": name, "description": _NETWORK_TOOL_DESCRIPTIONS[name]}
        for name in NETWORK_EXACT_TOOL_LABELS
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
class NetworkSelectorProgress:
    """Compact controller facts; no Executor text or tool result is allowed."""

    completed_stage_count: int = 0
    action_index: int = 0
    succeeded_operations: tuple[str, ...] = ()
    failed_operations: tuple[str, ...] = ()
    protocol_rejection_count: int = 0

    def __post_init__(self) -> None:
        counters = (
            self.completed_stage_count,
            self.action_index,
            self.protocol_rejection_count,
        )
        if any(value < 0 for value in counters):
            raise ValueError("network Selector progress counters must be non-negative")
        if len(set(self.succeeded_operations)) != len(self.succeeded_operations):
            raise ValueError("network Selector succeeded operations must be unique")
        if len(set(self.failed_operations)) != len(self.failed_operations):
            raise ValueError("network Selector failed operations must be unique")
        known = set(NETWORK_EXACT_TOOL_LABELS) - {
            NETWORK_ABSTAIN_LABEL,
            "final_answer",
        }
        observed = {*self.succeeded_operations, *self.failed_operations}
        if not observed <= known:
            raise ValueError(
                "network Selector progress contains unknown operations: "
                f"{sorted(observed - known)}"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "completed_stage_count": self.completed_stage_count,
            "action_index": self.action_index,
            "succeeded_operations": list(self.succeeded_operations),
            "failed_operations": list(self.failed_operations),
            "protocol_rejection_count": self.protocol_rejection_count,
        }


@dataclass(frozen=True)
class NetworkSelectorInput:
    """Minimal input consumed by the 2.9B hidden extractor and MLP head."""

    task_request: str
    stage_objective: str
    stage_role: str
    progress: NetworkSelectorProgress
    menu: tuple[Mapping[str, str], ...]
    eligible_labels: tuple[str, ...] = NETWORK_EXACT_TOOL_LABELS
    schema_version: str = NETWORK_SELECTOR_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != NETWORK_SELECTOR_INPUT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported network Selector input schema: {self.schema_version}"
            )
        if not self.task_request.strip() or not self.stage_objective.strip():
            raise ValueError("network Selector input requires task and stage objective")
        if not self.stage_role.strip():
            raise ValueError("network Selector input requires a stage role")
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
        if tuple(item["name"] for item in normalized) != NETWORK_EXACT_TOOL_LABELS:
            raise ValueError("network Selector menu labels/order differ from v2")
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

    @classmethod
    def create(
        cls,
        *,
        task_request: str,
        stage_objective: str,
        stage_role: str,
        progress: NetworkSelectorProgress,
        eligible_labels: Sequence[str] = NETWORK_EXACT_TOOL_LABELS,
    ) -> "NetworkSelectorInput":
        return cls(
            task_request=str(task_request),
            stage_objective=str(stage_objective),
            stage_role=str(stage_role),
            progress=progress,
            menu=network_selector_tool_menu(),
            eligible_labels=tuple(str(item) for item in eligible_labels),
        )

    @property
    def menu_digest(self) -> str:
        return network_selector_menu_digest(self.menu)

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "schema_version": NETWORK_SELECTOR_INPUT_SCHEMA_VERSION,
            "task_request": self.task_request,
            "menu_schema_version": NETWORK_SELECTOR_MENU_SCHEMA_VERSION,
            "menu_digest": self.menu_digest,
            "tools": [dict(item) for item in self.menu],
        }

    def step_payload(self) -> dict[str, Any]:
        return {
            "schema_version": NETWORK_SELECTOR_INPUT_SCHEMA_VERSION,
            "stage_objective": self.stage_objective,
            "stage_role": self.stage_role,
            "progress": self.progress.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            **self.bootstrap_payload(),
            **self.step_payload(),
            "eligible_labels": list(self.eligible_labels),
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


@dataclass(frozen=True)
class NetworkExactToolSelection:
    """Immutable raw 25-logit result; generated RWKV text is never involved."""

    selection_id: str
    trace_id: str
    selected_operation: str
    logits: tuple[float, ...]
    temperature: float
    input_digest: str
    menu_digest: str
    selector_checkpoint_id: str
    selector_state_ref: str
    selector_state_digest: str
    selector_parent_state_digest: str
    token_position: int
    model: str
    model_sha256: str
    head_sha256: str
    profile_id: str
    profile_sha256: str
    eligible_labels: tuple[str, ...] = NETWORK_EXACT_TOOL_LABELS
    schema_version: str = NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version not in {
            NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2,
            NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION,
        }:
            raise ValueError(
                f"unsupported network Selector output schema: {self.schema_version}"
            )
        identity_values = (
            self.selection_id,
            self.trace_id,
            self.input_digest,
            self.menu_digest,
            self.selector_checkpoint_id,
            self.selector_state_ref,
            self.selector_state_digest,
            self.model,
            self.model_sha256,
            self.head_sha256,
            self.profile_id,
            self.profile_sha256,
        )
        if any(not str(value).strip() for value in identity_values):
            raise ValueError("network Selector output identity fields must be non-empty")
        digests = (
            self.input_digest,
            self.menu_digest,
            self.selector_state_digest,
            self.model_sha256,
            self.head_sha256,
            self.profile_sha256,
        )
        if any(
            len(value) != 64
            or any(character not in "0123456789abcdef" for character in value)
            for value in digests
        ):
            raise ValueError("network Selector output digests must be lowercase SHA-256")
        if self.selector_parent_state_digest and (
            len(self.selector_parent_state_digest) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.selector_parent_state_digest
            )
        ):
            raise ValueError("network Selector parent digest must be empty or SHA-256")
        if len(self.logits) != len(NETWORK_EXACT_TOOL_LABELS) or any(
            not math.isfinite(float(value)) for value in self.logits
        ):
            raise ValueError("network Selector requires one finite raw logit per label")
        if not math.isfinite(self.temperature) or self.temperature <= 0.0:
            raise ValueError("network Selector temperature must be positive and finite")
        if self.token_position < 1:
            raise ValueError("network Selector token_position must be positive")
        eligible = tuple(str(item) for item in self.eligible_labels)
        if self.schema_version == NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2:
            if eligible != NETWORK_EXACT_TOOL_LABELS:
                raise ValueError("v2 network Selector output requires the full class domain")
        else:
            if not eligible or len(set(eligible)) != len(eligible):
                raise ValueError(
                    "network Selector eligible labels must be non-empty and unique"
                )
            if set(eligible) - set(NETWORK_EXACT_TOOL_LABELS):
                raise ValueError("network Selector eligible labels contain unknown classes")
            if eligible != tuple(
                label
                for label in NETWORK_EXACT_TOOL_LABELS
                if label in set(eligible)
            ):
                raise ValueError(
                    "network Selector eligible labels differ from class order"
                )
        object.__setattr__(self, "eligible_labels", eligible)
        selected = validate_network_label(self.selected_operation)
        expected_index = max(
            (
                index
                for index, label in enumerate(NETWORK_EXACT_TOOL_LABELS)
                if label in set(eligible)
            ),
            key=lambda index: (self.logits[index], -index),
        )
        if selected != NETWORK_EXACT_TOOL_LABELS[expected_index]:
            raise ValueError(
                "selected operation differs from eligible raw-logit argmax"
            )

    @property
    def probabilities(self) -> tuple[float, ...]:
        scaled = [float(value) / self.temperature for value in self.logits]
        offset = max(scaled)
        values = [math.exp(value - offset) for value in scaled]
        total = sum(values)
        return tuple(value / total for value in values)

    @property
    def confidence(self) -> float:
        return self.probabilities[
            NETWORK_EXACT_TOOL_LABELS.index(self.selected_operation)
        ]

    def ranked_operations(
        self,
        k: int,
        *,
        exclude: Sequence[str] = (),
    ) -> tuple[tuple[str, float, float], ...]:
        """Return deterministic eligible Top-K labels with raw logit/probability.

        This is a projection of the already frozen 25 logits.  It performs no
        second model call and does not grant any candidate execution authority.
        """

        if isinstance(k, bool) or not isinstance(k, int) or k < 1:
            raise ValueError("network Selector Top-K must be a positive integer")
        excluded = {str(item) for item in exclude}
        eligible = set(self.eligible_labels) - excluded
        if not eligible:
            raise ValueError("network Selector Top-K has no eligible labels")
        probabilities = self.probabilities
        indices = sorted(
            (
                index
                for index, label in enumerate(NETWORK_EXACT_TOOL_LABELS)
                if label in eligible
            ),
            key=lambda index: (-self.logits[index], index),
        )[:k]
        return tuple(
            (
                NETWORK_EXACT_TOOL_LABELS[index],
                float(self.logits[index]),
                float(probabilities[index]),
            )
            for index in indices
        )

    @property
    def logits_sha256(self) -> str:
        return canonical_digest(list(self.logits))

    def raw_record(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "selection_id": self.selection_id,
            "trace_id": self.trace_id,
            "class_order": list(NETWORK_EXACT_TOOL_LABELS),
            "eligible_labels": list(self.eligible_labels),
            "selection_rule": "eligible_raw_logit_argmax",
            "logits": list(self.logits),
            "logits_sha256": self.logits_sha256,
            "temperature": self.temperature,
            "selected_operation": self.selected_operation,
            "confidence": self.confidence,
            "input_digest": self.input_digest,
            "menu_digest": self.menu_digest,
            "selector_checkpoint_id": self.selector_checkpoint_id,
            "selector_state_ref": self.selector_state_ref,
            "selector_state_digest": self.selector_state_digest,
            "selector_parent_state_digest": self.selector_parent_state_digest,
            "token_position": self.token_position,
            "model": self.model,
            "model_sha256": self.model_sha256,
            "head_sha256": self.head_sha256,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
            "postprocessed": False,
            "generated_text": False,
        }

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any]
    ) -> "NetworkExactToolSelection":
        raw_logits = value.get("logits")
        if not isinstance(raw_logits, list):
            raise TypeError("network Selector output logits must be an array")
        class_order = value.get("class_order")
        if class_order is not None and tuple(str(item) for item in class_order) != (
            NETWORK_EXACT_TOOL_LABELS
        ):
            raise ValueError("network Selector output class order differs from v2")
        schema_version = str(value.get("schema_version") or "")
        raw_eligible = value.get("eligible_labels")
        eligible_labels = (
            NETWORK_EXACT_TOOL_LABELS
            if schema_version == NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2
            and raw_eligible is None
            else tuple(str(item) for item in raw_eligible or ())
        )
        return cls(
            schema_version=schema_version,
            selection_id=str(value.get("selection_id") or ""),
            trace_id=str(value.get("trace_id") or ""),
            selected_operation=str(value.get("selected_operation") or ""),
            logits=tuple(float(item) for item in raw_logits),
            temperature=float(value.get("temperature") or 0.0),
            input_digest=str(value.get("input_digest") or ""),
            menu_digest=str(value.get("menu_digest") or ""),
            selector_checkpoint_id=str(value.get("selector_checkpoint_id") or ""),
            selector_state_ref=str(value.get("selector_state_ref") or ""),
            selector_state_digest=str(value.get("selector_state_digest") or ""),
            selector_parent_state_digest=str(
                value.get("selector_parent_state_digest") or ""
            ),
            token_position=int(value.get("token_position") or 0),
            model=str(value.get("model") or ""),
            model_sha256=str(value.get("model_sha256") or ""),
            head_sha256=str(value.get("head_sha256") or ""),
            profile_id=str(value.get("profile_id") or ""),
            profile_sha256=str(value.get("profile_sha256") or ""),
            eligible_labels=eligible_labels,
        )


__all__ = [
    "NETWORK_ABSTAIN_LABEL",
    "NETWORK_EXACT_TOOL_LABELS",
    "NETWORK_SELECTOR_INPUT_SCHEMA_VERSION",
    "NETWORK_SELECTOR_MENU_SCHEMA_VERSION",
    "NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION",
    "NETWORK_SELECTOR_OUTPUT_SCHEMA_VERSION_V2",
    "NetworkExactToolSelection",
    "NetworkSelectorInput",
    "NetworkSelectorProgress",
    "network_selector_menu_digest",
    "network_selector_tool_menu",
    "validate_network_label",
]
