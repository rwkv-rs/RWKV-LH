"""Production/data-shared G1J Selector-Intent renderer and parser."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields,
    _nonempty,
    _render,
    _strings,
)


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v2"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION

_SUBTASK_FIELDS = (
    "objective",
    "phase",
    "read_roots",
    "write_roots",
    "success_evidence",
    "constraints",
)
_PROMPT_FIELDS = ("current_subtask", "eligible_labels")
_SOURCE_FIELDS = (
    *_PROMPT_FIELDS,
    "selected_operation",
    "selection_authority",
    "selection_verifier_id",
)
_AUTHORITIES = {"planner_contract", "executed_fixture", "human_double_review"}
_PHASES = {"observe", "mutate", "execute", "derive_evidence"}


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "selector prompt source")
    subtask = _exact_fields(
        selected["current_subtask"], _SUBTASK_FIELDS, "current_subtask"
    )
    _nonempty(subtask["objective"], "current_subtask.objective")
    if subtask["phase"] not in _PHASES:
        raise ValueError("current_subtask.phase is invalid")
    for name in ("read_roots", "write_roots", "constraints"):
        _strings(subtask[name], f"current_subtask.{name}")
    _strings(
        subtask["success_evidence"],
        "current_subtask.success_evidence",
        nonempty=True,
    )
    _strings(selected["eligible_labels"], "eligible_labels", nonempty=True)
    return selected


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "selector source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    operation = _nonempty(selected["selected_operation"], "selected_operation")
    eligible = tuple(selected["eligible_labels"])
    if operation not in eligible:
        raise ValueError("selected_operation must be eligible")
    authority = _nonempty(selected["selection_authority"], "selection_authority")
    if authority not in _AUTHORITIES:
        raise ValueError("selection_authority is invalid")
    _nonempty(selected["selection_verifier_id"], "selection_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "selector render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "selector_intent",
        "eligible_labels": list(prompt["eligible_labels"]),
        "current_subtask": dict(prompt["current_subtask"]),
        "current_question": (
            "Choose exactly one eligible operation label for this current subtask; "
            "do not use prior calls, fill parameters, audit, plan, or answer the user."
        ),
    }
    return _render("SelectorIntentPromptV2: ", payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return "\nSelectorIntentV2: " + str(source["selected_operation"])


def parse_target(target: str) -> str:
    prefix = "\nSelectorIntentV2: "
    if not isinstance(target, str) or not target.startswith(prefix):
        raise ValueError("selector target prefix is invalid")
    operation = target[len(prefix) :]
    if not operation or operation.strip() != operation or "\n" in operation:
        raise ValueError("selector target must contain one exact operation label")
    return operation


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
