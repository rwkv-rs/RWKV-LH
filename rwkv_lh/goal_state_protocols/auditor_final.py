"""Shared Final-Auditor v4: candidate conditions are not established findings.

RWKV decides whether the actual answer and execution evidence satisfy the goal.
The catalog provides stable condition references and explicit repair ownership.
"""

from __future__ import annotations

import hashlib
from collections.abc import Mapping, Sequence
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
)
from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.model_io import ModelCommand, validate_final_answer


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.auditor-final.v4"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION
PROMPT_PREFIX = "AuditorFinalPromptV4: "
REASON_READY = "final_evidence_complete"
REASON_REPAIR = "final_evidence_incomplete"

_PROMPT_FIELDS = (
    "immutable_goal",
    "completed_steps",
    "available_evidence_refs",
    "evidence_records",
    "final_candidate",
    "gap_catalog",
    "feedback",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "decision", "final_verifier_id")
_GAP_ENTRY_FIELDS = ("code", "criterion", "repair_scope")


def _gap_code(prefix: str, value: str) -> str:
    return f"{prefix}:{value}"


def _short_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def build_gap_catalog(
    immutable_goal: str,
    completed_steps: Sequence[Mapping[str, Any]],
    evidence_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Build possible, not pre-judged, gaps from facts visible to the model."""

    entries: dict[str, str] = {
        _gap_code("goal_requirement_unproved", _short_digest(immutable_goal)): (
            immutable_goal
        ),
        "candidate_omits_required_result": (
            "The final candidate must include the results required by the immutable goal."
        ),
        "candidate_unsupported_claim": (
            "The final candidate's claims must be supported by committed evidence."
        ),
    }
    for step in completed_steps:
        step_id = str(step.get("step_id") or "").strip()
        if not step_id:
            continue
        criteria = step.get("success_evidence")
        if isinstance(criteria, Sequence) and not isinstance(criteria, (str, bytes)):
            for criterion in criteria:
                text = str(criterion or "").strip()
                if not text:
                    continue
                code = _gap_code(
                    "completed_step_criterion_unproved",
                    f"{step_id}:{_short_digest(text)}",
                )
                entries[code] = text
    for record in evidence_records:
        evidence_ref = str(record.get("evidence_ref") or "").strip()
        action = record.get("action")
        action = action if isinstance(action, Mapping) else {}
        result = action.get("result")
        result = result if isinstance(result, Mapping) else {}
        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        if evidence_ref and (
            action.get("status") == "failed"
            or result.get("success") is False
            or metadata.get("complete") is False
            or metadata.get("truncated") is True
        ):
            entries[_gap_code("evidence_unusable", evidence_ref)] = (
                f"Evidence {evidence_ref} is failed, incomplete, or truncated."
            )
    return [
        {"code": code, "criterion": entries[code],
         "repair_scope": "answer" if code in {"candidate_omits_required_result", "candidate_unsupported_claim"} else "execution"}
        for code in sorted(entries)
    ]


def _validate_gap_catalog(value: Any) -> tuple[Mapping[str, Any], ...]:
    entries = _objects(value, "gap_catalog", nonempty=True)
    codes: list[str] = []
    for entry in entries:
        selected = _exact_fields(entry, _GAP_ENTRY_FIELDS, "gap_catalog item")
        codes.append(_nonempty(selected["code"], "gap_catalog item.code"))
        _nonempty(selected["criterion"], "gap_catalog item.criterion")
    if len(set(codes)) != len(codes) or codes != sorted(codes):
        raise ValueError("gap_catalog codes must be sorted and unique")
    return entries


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "final auditor prompt source")
    validate_feedback(selected["feedback"], recipient="auditor_final")
    _nonempty(selected["immutable_goal"], "immutable_goal")
    completed_steps = _validate_completed_steps(selected["completed_steps"])
    _strings(
        selected["available_evidence_refs"],
        "available_evidence_refs",
        nonempty=True,
        sorted_unique=True,
    )
    evidence_records = _objects(
        selected["evidence_records"], "evidence_records", nonempty=True
    )
    candidate = _exact_fields(
        selected["final_candidate"], ("function", "params"), "final_candidate"
    )
    if candidate["function"] != "final_answer" or not isinstance(candidate["params"], Mapping):
        raise ValueError("final_candidate must call final_answer")
    validate_final_answer(ModelCommand("final_answer", dict(candidate["params"])))
    catalog = _validate_gap_catalog(selected["gap_catalog"])
    expected_catalog = build_gap_catalog(
        str(selected["immutable_goal"]),
        completed_steps,
        evidence_records,
    )
    if [dict(item) for item in catalog] != expected_catalog:
        raise ValueError("gap_catalog must equal the deterministic visible-criteria catalog")
    return selected


def build_prompt_source(
    *,
    immutable_goal: str,
    completed_steps: Sequence[Mapping[str, Any]],
    available_evidence_refs: Sequence[str],
    evidence_records: Sequence[Mapping[str, Any]],
    final_candidate: Mapping[str, Any],
    feedback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Bind the Finalizer candidate to the one visible-evidence audit input."""

    source = {
        "immutable_goal": immutable_goal,
        "completed_steps": [dict(step) for step in completed_steps],
        "available_evidence_refs": list(available_evidence_refs),
        "evidence_records": [dict(record) for record in evidence_records],
        "final_candidate": dict(final_candidate),
        "gap_catalog": build_gap_catalog(immutable_goal, completed_steps, evidence_records),
    }
    source["feedback"] = dict(feedback) if feedback is not None else None
    _validate_prompt_source(source)
    return source


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "final auditor source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    decision = _audit_decision(
        selected["decision"], allowed_verdicts=("ready_for_final", "repair")
    )
    _strings(decision["evidence_refs"], "decision.evidence_refs", sorted_unique=True)
    _strings(decision["gaps"], "decision.gaps", sorted_unique=True)
    if decision["step_id"] != "" or decision["step_complete"]:
        raise ValueError("final audit decision cannot complete a plan step")
    if not set(decision["evidence_refs"]) <= set(selected["available_evidence_refs"]):
        raise ValueError("final audit evidence_refs must be available")
    if decision["verdict"] == "ready_for_final":
        if decision["gaps"] or not decision["evidence_refs"]:
            raise ValueError("ready_for_final requires evidence refs and no gaps")
        if decision["reason"] != REASON_READY:
            raise ValueError(f"ready_for_final reason must be {REASON_READY!r}")
    elif not decision["gaps"]:
        raise ValueError("final repair requires non-empty gaps")
    else:
        if decision["reason"] != REASON_REPAIR:
            raise ValueError(f"repair reason must be {REASON_REPAIR!r}")
        catalog_codes = {str(item["code"]) for item in selected["gap_catalog"]}
        if not set(decision["gaps"]) <= catalog_codes:
            raise ValueError("final repair gaps must be selected from gap_catalog codes")
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
        "available_evidence_refs": list(prompt["available_evidence_refs"]),
        "evidence_records": [dict(item) for item in prompt["evidence_records"]],
        "final_candidate": dict(prompt["final_candidate"]),
        "catalog_semantics": "possible_unmet_conditions",
        "gap_catalog": [dict(item) for item in prompt["gap_catalog"]],
        "feedback": prompt["feedback"],
        "current_question": (
            "Return audit_decision with exactly these six fields: verdict, step_id, "
            "step_complete, evidence_refs, gaps, reason. gap_catalog lists possible "
            "unmet conditions, not established findings. Decide whether each condition "
            "is unmet from the actual final_candidate and evidence_records; catalog "
            "membership does not prove a gap. At this final boundary "
            "step_id is always the empty string and step_complete is always false; "
            "all listed completed_steps are already complete. Always include both "
            "evidence_refs and gaps arrays. Use ready_for_final only when the candidate "
            "fully answers immutable_goal using committed evidence; otherwise use "
            "repair and copy only exact gap codes from gap_catalog. Use reason exactly "
            f"{REASON_READY!r} for ready_for_final or {REASON_REPAIR!r} for repair."
        ),
    }
    return _render(PROMPT_PREFIX, payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return ModelCommand("audit_decision", dict(source["decision"])).canonical


def parse_target(target: str) -> ModelCommand:
    command = _audit_target(target, allowed_verdicts=("ready_for_final", "repair"))
    if command.arguments["step_id"] != "" or command.arguments["step_complete"]:
        raise ValueError("Final Auditor target cannot complete a plan step")
    expected_reason = (
        REASON_READY
        if command.arguments["verdict"] == "ready_for_final"
        else REASON_REPAIR
    )
    if command.arguments["reason"] != expected_reason:
        raise ValueError("Final Auditor target reason is not canonical for its verdict")
    return command


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_PREFIX",
    "REASON_READY",
    "REASON_REPAIR",
    "build_gap_catalog",
    "build_prompt_source",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
