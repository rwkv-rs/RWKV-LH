"""Frozen, schema-free input contract for the 2.9B exact-tool Selector."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from rwkv_lh.harness import ActionHarness
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION

SELECTOR_INPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-input.v1"
SELECTOR_MENU_SCHEMA_VERSION = "rwkv-lh.exact-tool-menu.v1"
SELECTOR_OUTPUT_SCHEMA_VERSION = "rwkv-lh.exact-tool-selector-output.v1"
ABSTAIN_LABEL = "ABSTAIN"

EXACT_TOOL_LABELS = (
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
    "final_answer",
    ABSTAIN_LABEL,
)

_ABSTAIN_DESCRIPTION = (
    "Select no operation because the current stage is ambiguous, unsupported, "
    "unsafe, or lacks enough observable information to choose exactly one tool."
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def selector_tool_menu(
    harness: ActionHarness | None = None,
) -> tuple[dict[str, str], ...]:
    """Return exactly 20 names and brief descriptions, never parameter schemas."""

    selected_harness = harness or ActionHarness()
    definitions = {
        str(item.get("name") or ""): item
        for item in selected_harness.g1i_tool_definitions()
    }
    expected_actions = set(EXACT_TOOL_LABELS) - {"final_answer", ABSTAIN_LABEL}
    if set(definitions) != expected_actions:
        raise ValueError(
            "Harness operation registry differs from the frozen Selector labels: "
            f"missing={sorted(expected_actions - set(definitions))}, "
            f"extra={sorted(set(definitions) - expected_actions)}"
        )
    descriptions = {
        name: str(definitions[name].get("description") or "").strip()
        for name in expected_actions
    }
    descriptions["final_answer"] = str(FINAL_ANSWER_DEFINITION["description"]).strip()
    descriptions[ABSTAIN_LABEL] = _ABSTAIN_DESCRIPTION
    if any(not description for description in descriptions.values()):
        raise ValueError("every frozen Selector label requires a description")
    return tuple(
        {"name": name, "description": descriptions[name]} for name in EXACT_TOOL_LABELS
    )


def selector_menu_digest(
    menu: Sequence[Mapping[str, str]] | None = None,
) -> str:
    selected = selector_tool_menu() if menu is None else menu
    return canonical_digest(
        {
            "schema_version": SELECTOR_MENU_SCHEMA_VERSION,
            "tools": [dict(item) for item in selected],
        }
    )


@dataclass(frozen=True)
class SelectorProgress:
    """Compact controller facts; executor text and tool results are excluded."""

    completed_stage_count: int = 0
    action_index: int = 0
    succeeded_operations: tuple[str, ...] = ()
    failed_operations: tuple[str, ...] = ()
    protocol_rejection_count: int = 0

    def __post_init__(self) -> None:
        if self.completed_stage_count < 0 or self.action_index < 0:
            raise ValueError("Selector progress counters must be non-negative")
        if self.protocol_rejection_count < 0:
            raise ValueError("protocol_rejection_count must be non-negative")
        known = set(EXACT_TOOL_LABELS) - {ABSTAIN_LABEL, "final_answer"}
        observed = {*self.succeeded_operations, *self.failed_operations}
        if not observed <= known:
            raise ValueError(
                f"Selector progress contains unknown operations: {sorted(observed - known)}"
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
class SelectorInput:
    """One deterministic input to the 2.9B feature extractor and MLP head."""

    task_request: str
    stage_objective: str
    stage_role: str
    progress: SelectorProgress
    menu: tuple[Mapping[str, str], ...]
    schema_version: str = SELECTOR_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SELECTOR_INPUT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported Selector input schema: {self.schema_version}"
            )
        if not self.task_request.strip() or not self.stage_objective.strip():
            raise ValueError("Selector input requires task request and stage objective")
        if not self.stage_role.strip():
            raise ValueError("Selector input requires a stage role")
        if any(set(item) != {"name", "description"} for item in self.menu):
            raise ValueError("Selector menu may contain only name and description")
        normalized = tuple(
            {
                "name": str(item.get("name") or ""),
                "description": str(item.get("description") or ""),
            }
            for item in self.menu
        )
        if tuple(item["name"] for item in normalized) != EXACT_TOOL_LABELS:
            raise ValueError(
                "Selector menu labels/order differ from the frozen protocol"
            )
        if any(not item["description"].strip() for item in normalized):
            raise ValueError("Selector menu descriptions must be non-empty")
        object.__setattr__(self, "menu", normalized)

    @property
    def menu_digest(self) -> str:
        return selector_menu_digest(self.menu)

    def bootstrap_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SELECTOR_INPUT_SCHEMA_VERSION,
            "task_request": self.task_request,
            "menu_schema_version": SELECTOR_MENU_SCHEMA_VERSION,
            "menu_digest": self.menu_digest,
            "tools": [dict(item) for item in self.menu],
        }

    def step_payload(self) -> dict[str, Any]:
        return {
            "schema_version": SELECTOR_INPUT_SCHEMA_VERSION,
            "stage_objective": self.stage_objective,
            "stage_role": self.stage_role,
            "progress": self.progress.to_dict(),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task_request": self.task_request,
            "stage_objective": self.stage_objective,
            "stage_role": self.stage_role,
            "progress": self.progress.to_dict(),
            "menu_schema_version": SELECTOR_MENU_SCHEMA_VERSION,
            "menu_digest": self.menu_digest,
            "tools": [dict(item) for item in self.menu],
        }

    def render(self) -> str:
        """Render a stateless replay equivalent to bootstrap then one append."""

        return self.render_bootstrap() + "\n" + self.render_step()

    def render_bootstrap(self) -> str:
        """Render bytes consumed once when a Selector lane is created."""

        return "SelectorBootstrap: " + canonical_json(self.bootstrap_payload())

    def render_step(self) -> str:
        """Render only the causal delta appended before one classification."""

        return "SelectorStep: " + canonical_json(self.step_payload())

    @classmethod
    def create(
        cls,
        *,
        task_request: str,
        stage_objective: str,
        stage_role: str,
        progress: SelectorProgress,
        harness: ActionHarness | None = None,
    ) -> SelectorInput:
        return cls(
            task_request=str(task_request),
            stage_objective=str(stage_objective),
            stage_role=str(stage_role),
            progress=progress,
            menu=selector_tool_menu(harness),
        )


def validate_label(label: str) -> str:
    selected = str(label or "")
    if selected not in EXACT_TOOL_LABELS:
        raise ValueError(f"unknown exact-tool Selector label: {selected!r}")
    return selected


@dataclass(frozen=True)
class ExactToolSelection:
    """Immutable raw MLP classification result; no generated call text exists."""

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
    schema_version: str = SELECTOR_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SELECTOR_OUTPUT_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported Selector output schema: {self.schema_version}"
            )
        identities = {
            "selection_id": self.selection_id,
            "trace_id": self.trace_id,
            "input_digest": self.input_digest,
            "menu_digest": self.menu_digest,
            "selector_checkpoint_id": self.selector_checkpoint_id,
            "selector_state_ref": self.selector_state_ref,
            "selector_state_digest": self.selector_state_digest,
            "model": self.model,
            "model_sha256": self.model_sha256,
            "head_sha256": self.head_sha256,
            "profile_id": self.profile_id,
            "profile_sha256": self.profile_sha256,
        }
        if any(not str(value).strip() for value in identities.values()):
            raise ValueError("Selector output identity fields must be non-empty")
        for name in (
            "input_digest",
            "menu_digest",
            "selector_state_digest",
            "model_sha256",
            "head_sha256",
            "profile_sha256",
        ):
            value = str(identities[name])
            if len(value) != 64 or any(
                item not in "0123456789abcdef" for item in value
            ):
                raise ValueError(f"Selector output {name} must be lowercase SHA-256")
        if self.selector_parent_state_digest and (
            len(self.selector_parent_state_digest) != 64
            or any(
                item not in "0123456789abcdef"
                for item in self.selector_parent_state_digest
            )
        ):
            raise ValueError(
                "Selector output selector_parent_state_digest must be empty or SHA-256"
            )
        if len(self.logits) != len(EXACT_TOOL_LABELS) or any(
            not math.isfinite(float(value)) for value in self.logits
        ):
            raise ValueError(
                "Selector output requires one finite logit per frozen label"
            )
        if not math.isfinite(self.temperature) or self.temperature <= 0.0:
            raise ValueError("Selector temperature must be positive and finite")
        if self.token_position < 1:
            raise ValueError("Selector token_position must be positive")
        selected = validate_label(self.selected_operation)
        expected_index = max(
            range(len(self.logits)),
            key=lambda index: (self.logits[index], -index),
        )
        if selected != EXACT_TOOL_LABELS[expected_index]:
            raise ValueError("selected operation differs from the raw-logit argmax")

    @property
    def probabilities(self) -> tuple[float, ...]:
        scaled = [float(value) / self.temperature for value in self.logits]
        offset = max(scaled)
        exponents = [math.exp(value - offset) for value in scaled]
        total = sum(exponents)
        return tuple(value / total for value in exponents)

    @property
    def confidence(self) -> float:
        return self.probabilities[EXACT_TOOL_LABELS.index(self.selected_operation)]

    @property
    def logits_sha256(self) -> str:
        return canonical_digest(list(self.logits))

    def raw_record(self) -> dict[str, Any]:
        """Return the complete unmodified classifier output for causal storage."""

        return {
            "schema_version": self.schema_version,
            "selection_id": self.selection_id,
            "trace_id": self.trace_id,
            "class_order": list(EXACT_TOOL_LABELS),
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
    def from_dict(cls, value: Mapping[str, Any]) -> ExactToolSelection:
        raw_logits = value.get("logits")
        if not isinstance(raw_logits, list):
            raise TypeError("Selector output logits must be an array")
        return cls(
            schema_version=str(value.get("schema_version") or ""),
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
        )


def menu_names(menu: Sequence[Mapping[str, str]]) -> tuple[str, ...]:
    return tuple(str(item.get("name") or "") for item in menu)


__all__ = [
    "ABSTAIN_LABEL",
    "EXACT_TOOL_LABELS",
    "SELECTOR_INPUT_SCHEMA_VERSION",
    "SELECTOR_MENU_SCHEMA_VERSION",
    "SELECTOR_OUTPUT_SCHEMA_VERSION",
    "ExactToolSelection",
    "SelectorInput",
    "SelectorProgress",
    "canonical_digest",
    "canonical_json",
    "menu_names",
    "selector_menu_digest",
    "selector_tool_menu",
    "validate_label",
]
