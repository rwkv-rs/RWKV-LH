"""Production/data-shared G1J Step-Auditor renderer and parser."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _audit_decision,
    _audit_target,
    _exact_fields,
    _nonempty,
    _objects,
    _render,
    _strings,
)
from rwkv_lh.model_io import ModelCommand


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.auditor-step.v1"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION

_PROMPT_FIELDS = (
    "boundary",
    "active_step",
    "available_evidence_refs",
    "evidence_records",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "decision", "completion_verifier_id")
_BOUNDARIES = {
    "observation_complete",
    "mutation_transaction_complete",
    "tool_failure",
    "stagnation",
}
_STEP_FIELDS = (
    "step_id",
    "objective",
    "stage",
    "depends_on",
    "success_evidence",
    "obligation_ids",
    "read_roots",
    "write_roots",
    "allowed_operations",
    "constraints",
)


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "step auditor prompt source")
    if selected["boundary"] not in _BOUNDARIES:
        raise ValueError("step auditor boundary is invalid")
    step = _exact_fields(selected["active_step"], _STEP_FIELDS, "active_step")
    _nonempty(step["step_id"], "active_step.step_id")
    _nonempty(step["objective"], "active_step.objective")
    refs = _strings(
        selected["available_evidence_refs"],
        "available_evidence_refs",
        sorted_unique=True,
    )
    _objects(selected["evidence_records"], "evidence_records")
    if refs and not selected["evidence_records"]:
        raise ValueError("evidence_records must resolve available evidence")
    return selected


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "step auditor source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    decision = _audit_decision(selected["decision"], allowed_verdicts=("continue", "repair"))
    step_id = str(selected["active_step"]["step_id"])
    if decision["step_id"] != step_id:
        raise ValueError("step audit decision must bind the active step")
    refs = set(selected["available_evidence_refs"])
    if not set(decision["evidence_refs"]) <= refs:
        raise ValueError("step audit evidence_refs must be available")
    if decision["verdict"] == "continue":
        if not decision["step_complete"] or not decision["evidence_refs"] or decision["gaps"]:
            raise ValueError("continue requires completion evidence and no gaps")
    elif decision["step_complete"] or not decision["gaps"]:
        raise ValueError("repair requires an incomplete step and non-empty gaps")
    _nonempty(selected["completion_verifier_id"], "completion_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "step auditor render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "auditor_step",
        "boundary": prompt["boundary"],
        "active_step": dict(prompt["active_step"]),
        "available_evidence_refs": list(prompt["available_evidence_refs"]),
        "evidence_records": [dict(item) for item in prompt["evidence_records"]],
        "current_question": (
            "Return audit_decision with exactly these six fields: verdict, step_id, "
            "step_complete, evidence_refs, gaps, reason. Always include both "
            "evidence_refs and gaps arrays, even when an array is empty. Use continue "
            "only when this active step is evidence-complete; otherwise use repair "
            "with exact gaps."
        ),
    }
    return _render("AuditorStepPromptV1: ", payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return ModelCommand("audit_decision", dict(source["decision"])).canonical


def parse_target(target: str) -> ModelCommand:
    return _audit_target(target, allowed_verdicts=("continue", "repair"))


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
