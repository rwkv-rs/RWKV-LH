"""Production/data-shared G1J Selector-Intent renderer and parser."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields,
    _nonempty,
    _nonnegative_int,
    _render,
    _strings,
)


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v1"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION

_PROMPT_FIELDS = ("stage_objective", "stage_role", "progress", "eligible_labels")
_SOURCE_FIELDS = (
    *_PROMPT_FIELDS,
    "selected_operation",
    "selection_authority",
    "selection_verifier_id",
)
_PROGRESS_FIELDS = (
    "completed_stage_count",
    "action_index",
    "succeeded_operations",
    "failed_operations",
    "protocol_rejection_count",
)
_AUTHORITIES = {"planner_contract", "executed_fixture", "human_double_review"}


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "selector prompt source")
    _nonempty(selected["stage_objective"], "stage_objective")
    _nonempty(selected["stage_role"], "stage_role")
    progress = _exact_fields(selected["progress"], _PROGRESS_FIELDS, "progress")
    for name in ("completed_stage_count", "action_index", "protocol_rejection_count"):
        _nonnegative_int(progress[name], f"progress.{name}")
    _strings(progress["succeeded_operations"], "progress.succeeded_operations")
    _strings(progress["failed_operations"], "progress.failed_operations")
    _strings(selected["eligible_labels"], "eligible_labels", nonempty=True)
    return selected


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "selector source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    operation = _nonempty(selected["selected_operation"], "selected_operation")
    eligible = tuple(selected["eligible_labels"])
    if operation not in eligible:
        raise ValueError("selected_operation must be eligible")
    if "final_answer" in eligible and eligible != ("final_answer",):
        raise ValueError("final_answer eligibility must be the completed singleton menu")
    if operation == "final_answer" and eligible != ("final_answer",):
        raise ValueError("final_answer may only be selected at completion")
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
        "stage_objective": prompt["stage_objective"],
        "stage_role": prompt["stage_role"],
        "progress": dict(prompt["progress"]),
        "eligible_labels": list(prompt["eligible_labels"]),
        "current_question": (
            "Choose exactly one eligible operation label for this current frontier; "
            "do not fill parameters, audit, plan, or answer the user."
        ),
    }
    return _render("SelectorIntentPromptV1: ", payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return "\nSelectorIntentV1: " + str(source["selected_operation"])


def parse_target(target: str) -> str:
    prefix = "\nSelectorIntentV1: "
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
