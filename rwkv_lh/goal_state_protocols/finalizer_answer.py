"""Production/data-shared G1J Finalizer renderer and parser."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields,
    _nonempty,
    _objects,
    _render,
    _strict_command,
    _strings,
)
from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.model_io import ModelCommand, validate_final_answer


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.finalizer-answer.v2"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION
PROMPT_PREFIX = "FinalizerAnswerPromptV2: "

_PROMPT_FIELDS = (
    "immutable_goal",
    "completed_steps",
    "committed_facts",
    "evidence_records",
    "format_contract",
    "feedback",
    "retry_feedback",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "final_text", "fact_verifier_id")
_FACT_FIELDS = ("fact_id", "value", "evidence_refs")
_FORMAT_FIELDS = ("format_id", "language", "required_sections")


def _validate_completed_steps(value: Any) -> tuple[Mapping[str, Any], ...]:
    steps = _objects(value, "completed_steps", nonempty=True)
    for step in steps:
        _nonempty(step.get("step_id"), "completed_steps.step_id")
        _strings(
            step.get("evidence_refs"),
            "completed_steps.evidence_refs",
            nonempty=True,
            sorted_unique=True,
        )
    return steps


def _validate_facts(value: Any) -> tuple[Mapping[str, Any], ...]:
    facts = _objects(value, "committed_facts", nonempty=True)
    for fact in facts:
        selected = _exact_fields(fact, _FACT_FIELDS, "committed fact")
        _nonempty(selected["fact_id"], "committed_facts.fact_id")
        _strings(
            selected["evidence_refs"],
            "committed_facts.evidence_refs",
            nonempty=True,
            sorted_unique=True,
        )
    return facts


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "finalizer prompt source")
    validate_feedback(selected["feedback"], recipient="finalizer_answer")
    validate_feedback(selected["retry_feedback"], recipient="finalizer_answer")
    if selected["feedback"] is not None and selected["feedback"]["kind"] != "semantic":
        raise ValueError("Finalizer semantic feedback must retain its audit source")
    if selected["retry_feedback"] is not None and selected["retry_feedback"]["kind"] != "protocol":
        raise ValueError("Finalizer retry feedback cannot grant semantic authority")
    _nonempty(selected["immutable_goal"], "immutable_goal")
    _validate_completed_steps(selected["completed_steps"])
    _validate_facts(selected["committed_facts"])
    _objects(selected["evidence_records"], "evidence_records", nonempty=True)
    contract = _exact_fields(selected["format_contract"], _FORMAT_FIELDS, "format_contract")
    _nonempty(contract["format_id"], "format_contract.format_id")
    _nonempty(contract["language"], "format_contract.language")
    _strings(contract["required_sections"], "format_contract.required_sections")
    return selected


def build_prompt_source(
    *,
    immutable_goal: str,
    completed_steps: Sequence[Mapping[str, Any]],
    committed_facts: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
    format_contract: Mapping[str, Any] | None = None,
    feedback: Mapping[str, Any] | None = None,
    retry_feedback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the one Finalizer input without adding completion authority."""

    source = {
        "immutable_goal": immutable_goal,
        "completed_steps": [dict(step) for step in completed_steps],
        "committed_facts": [dict(fact) for fact in committed_facts],
        "evidence_records": [dict(record) for record in evidence_records],
        "format_contract": dict(format_contract) if format_contract is not None else {
            "format_id": "goal-user-response-v1",
            "language": "match_immutable_goal",
            "required_sections": [],
        },
    }
    source["feedback"] = dict(feedback) if feedback is not None else None
    source["retry_feedback"] = dict(retry_feedback) if retry_feedback is not None else None
    _validate_prompt_source(source)
    return source


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "finalizer source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    _nonempty(selected["final_text"], "final_text")
    _nonempty(selected["fact_verifier_id"], "fact_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "finalizer render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "finalizer_answer",
        "immutable_goal": prompt["immutable_goal"],
        "completed_steps": [dict(item) for item in prompt["completed_steps"]],
        "committed_facts": [dict(item) for item in prompt["committed_facts"]],
        "evidence_records": [dict(item) for item in prompt["evidence_records"]],
        "format_contract": dict(prompt["format_contract"]),
        "feedback": prompt["feedback"],
        "retry_feedback": prompt["retry_feedback"],
        "current_question": (
            "Return exactly one final_answer candidate grounded only in committed facts; "
            "do not claim completion authority or emit an audit verdict."
        ),
    }
    return _render(PROMPT_PREFIX, payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return ModelCommand("final_answer", {"text": source["final_text"]}).canonical


def parse_target(target: str) -> ModelCommand:
    command = _strict_command(target, "final_answer")
    validate_final_answer(command)
    return command


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_PREFIX",
    "build_prompt_source",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
