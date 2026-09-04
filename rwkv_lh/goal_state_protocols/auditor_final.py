"""Production/data-shared G1J Final-Auditor renderer and parser."""

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
from rwkv_lh.goal_state_protocols.finalizer_answer import (
    _validate_completed_steps,
    _validate_facts,
)
from rwkv_lh.model_io import ModelCommand, validate_final_answer


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.auditor-final.v1"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION

_PROMPT_FIELDS = (
    "immutable_goal",
    "completed_steps",
    "committed_facts",
    "available_evidence_refs",
    "evidence_records",
    "final_candidate",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "decision", "final_verifier_id")


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "final auditor prompt source")
    _nonempty(selected["immutable_goal"], "immutable_goal")
    _validate_completed_steps(selected["completed_steps"])
    _validate_facts(selected["committed_facts"])
    _strings(
        selected["available_evidence_refs"],
        "available_evidence_refs",
        nonempty=True,
        sorted_unique=True,
    )
    _objects(selected["evidence_records"], "evidence_records", nonempty=True)
    candidate = _exact_fields(
        selected["final_candidate"], ("function", "params"), "final_candidate"
    )
    if candidate["function"] != "final_answer" or not isinstance(candidate["params"], Mapping):
        raise ValueError("final_candidate must call final_answer")
    validate_final_answer(ModelCommand("final_answer", dict(candidate["params"])))
    return selected


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "final auditor source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    decision = _audit_decision(
        selected["decision"], allowed_verdicts=("ready_for_final", "repair")
    )
    if decision["step_id"] != "" or decision["step_complete"]:
        raise ValueError("final audit decision cannot complete a plan step")
    if not set(decision["evidence_refs"]) <= set(selected["available_evidence_refs"]):
        raise ValueError("final audit evidence_refs must be available")
    if decision["verdict"] == "ready_for_final":
        if decision["gaps"]:
            raise ValueError("ready_for_final cannot retain gaps")
    elif not decision["gaps"]:
        raise ValueError("final repair requires non-empty gaps")
    _nonempty(selected["final_verifier_id"], "final_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "final auditor render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "auditor_final",
        "immutable_goal": prompt["immutable_goal"],
        "completed_steps": [dict(item) for item in prompt["completed_steps"]],
        "committed_facts": [dict(item) for item in prompt["committed_facts"]],
        "available_evidence_refs": list(prompt["available_evidence_refs"]),
        "evidence_records": [dict(item) for item in prompt["evidence_records"]],
        "final_candidate": dict(prompt["final_candidate"]),
        "current_question": (
            "Return audit_decision with exactly these six fields: verdict, step_id, "
            "step_complete, evidence_refs, gaps, reason. Always include both "
            "evidence_refs and gaps arrays, even when an array is empty. Use "
            "ready_for_final only when the candidate is fully evidence-bound; "
            "otherwise use repair with exact gaps."
        ),
    }
    return _render("AuditorFinalPromptV1: ", payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return ModelCommand("audit_decision", dict(source["decision"])).canonical


def parse_target(target: str) -> ModelCommand:
    return _audit_target(target, allowed_verdicts=("ready_for_final", "repair"))


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
