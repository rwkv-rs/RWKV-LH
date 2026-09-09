"""Shared Step-Auditor v6 conditions, visible facts and verdict validation.

Mechanical evidence rules apply equally to production and role data.  Possible
semantic gaps remain questions for RWKV, never pre-established failure facts.
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
from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.goal_loop_protocol import action_mutates_root, action_observes_root
from rwkv_lh.schema import ActionRecord, ActionStatus


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.auditor-step.v6"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION
PROMPT_PREFIX = "AuditorStepPromptV6: "
REASON_COMPLETE = "evidence_complete"
REASON_INCOMPLETE = "evidence_incomplete"

_PROMPT_FIELDS = (
    "immutable_goal",
    "boundary",
    "active_step",
    "gap_catalog",
    "available_evidence_refs",
    "evidence_records",
    "feedback",
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
    "phase",
    "stage",
    "depends_on",
    "success_evidence",
    "obligation_ids",
    "read_roots",
    "write_roots",
    "allowed_operations",
    "constraints",
)
_GAP_ENTRY_FIELDS = ("code", "criterion")


def _gap_code(prefix: str, value: str) -> str:
    return f"{prefix}:{value}"


def _contradicted_root_gaps(
    active_step: Mapping[str, Any], evidence_records: Sequence[Mapping[str, Any]],
) -> frozenset[str]:
    """Prove only scope facts present in this exact visible evidence projection.

    Command success is not proof that an arbitrary file was read.  Incomplete or
    truncated projections likewise cannot disprove a missing complete observation.
    The natural-language success criteria always remain the Auditor's decision.
    """
    proved: set[str] = set()
    for record in _objects(evidence_records, "evidence_records"):
        raw = record.get("action")
        if not isinstance(raw, Mapping):
            continue
        action = ActionRecord.from_dict({**raw, "action_type": raw.get("operation")})
        result = action.result or {}
        if action.status is not ActionStatus.SUCCEEDED or result.get("success") is not True:
            continue
        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        observation = result.get("observation")
        observation = observation if isinstance(observation, Mapping) else {}
        complete_read = (
            action.action_type != "check_command"
            and metadata.get("complete") is True
            and metadata.get("truncated") is not True
            and observation.get("projection_complete") is not False
        )
        for root in active_step["read_roots"]:
            if complete_read and action_observes_root(action, root):
                proved.add(_gap_code("read_root_unproved", root))
        for root in active_step["write_roots"]:
            if action_mutates_root(action, root):
                proved.add(_gap_code("write_root_unproved", root))
    return frozenset(proved)


def build_gap_catalog(
    active_step: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Offer unmet-condition labels consistent with the visible scope facts."""

    step = _exact_fields(active_step, _STEP_FIELDS, "active_step")
    phase = str(step["phase"])
    entries: dict[str, str] = {
        _gap_code("phase_evidence_unproved", phase): (
            f"The declared {phase} phase must meet this step's success criteria "
            "using the available evidence."
        )
    }
    for root in _strings(step["read_roots"], "active_step.read_roots"):
        entries[_gap_code("read_root_unproved", root)] = (
            f"The active read root {root!r} must have a successful complete observation."
        )
    for root in _strings(step["write_roots"], "active_step.write_roots"):
        entries[_gap_code("write_root_unproved", root)] = (
            f"The active write root {root!r} must have a successful mutation."
        )
    for criterion in _strings(
        step["success_evidence"], "active_step.success_evidence"
    ):
        digest = hashlib.sha256(criterion.encode("utf-8")).hexdigest()[:12]
        entries[_gap_code("success_criterion_unproved", digest)] = criterion
    for record in _objects(evidence_records, "evidence_records"):
        action = record.get("action")
        if not isinstance(action, Mapping):
            continue
        action_id = str(action.get("action_id") or "").strip()
        if not action_id:
            continue
        result = action.get("result")
        result = result if isinstance(result, Mapping) else {}
        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        failed = action.get("status") == "failed" or result.get("success") is False
        incomplete = metadata.get("complete") is False or metadata.get("truncated") is True
        if failed:
            entries[_gap_code("action_failed", action_id)] = (
                f"Action {action_id} failed and cannot prove completion."
            )
        if incomplete:
            entries[_gap_code("action_incomplete", action_id)] = (
                f"Action {action_id} returned incomplete or truncated evidence."
            )
    contradicted = _contradicted_root_gaps(step, evidence_records)
    return [
        {"code": code, "criterion": entries[code]}
        for code in sorted(entries)
        if code not in contradicted
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
    selected = _exact_fields(source, _PROMPT_FIELDS, "step auditor prompt source")
    _nonempty(selected["immutable_goal"], "immutable_goal")
    validate_feedback(selected["feedback"], recipient="auditor_step")
    if selected["boundary"] not in _BOUNDARIES:
        raise ValueError("step auditor boundary is invalid")
    step = _exact_fields(selected["active_step"], _STEP_FIELDS, "active_step")
    _nonempty(step["step_id"], "active_step.step_id")
    _nonempty(step["objective"], "active_step.objective")
    if step["phase"] not in {"observe", "mutate", "execute", "derive_evidence"}:
        raise ValueError("active_step.phase is invalid")
    catalog = _validate_gap_catalog(selected["gap_catalog"])
    expected_catalog = build_gap_catalog(step, selected["evidence_records"])
    if [dict(item) for item in catalog] != expected_catalog:
        raise ValueError("gap_catalog must equal the deterministic visible-criteria catalog")
    refs = _strings(
        selected["available_evidence_refs"],
        "available_evidence_refs",
        sorted_unique=True,
    )
    _objects(selected["evidence_records"], "evidence_records")
    if refs and not selected["evidence_records"]:
        raise ValueError("evidence_records must resolve available evidence")
    return selected


def build_prompt_source(
    *,
    immutable_goal: str,
    boundary: str,
    active_step: Mapping[str, Any],
    available_evidence_refs: Sequence[str],
    evidence_records: Sequence[Mapping[str, Any]],
    feedback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Construct the sole Step Auditor input from the visible evidence boundary."""

    source = {
        "immutable_goal": immutable_goal,
        "boundary": boundary,
        "active_step": dict(active_step),
        "gap_catalog": build_gap_catalog(active_step, evidence_records),
        "available_evidence_refs": list(available_evidence_refs),
        "evidence_records": [dict(record) for record in evidence_records],
    }
    source["feedback"] = dict(feedback) if feedback is not None else None
    _validate_prompt_source(source)
    return source


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "step auditor source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    decision = _audit_decision(selected["decision"], allowed_verdicts=("continue", "repair"))
    _strings(decision["evidence_refs"], "decision.evidence_refs", sorted_unique=True)
    _strings(decision["gaps"], "decision.gaps", sorted_unique=True)
    step_id = str(selected["active_step"]["step_id"])
    if decision["step_id"] != step_id:
        raise ValueError("step audit decision must bind the active step")
    refs = set(selected["available_evidence_refs"])
    if not set(decision["evidence_refs"]) <= refs:
        raise ValueError("step audit evidence_refs must be available")
    if decision["verdict"] == "continue":
        if not decision["step_complete"] or not decision["evidence_refs"] or decision["gaps"]:
            raise ValueError("continue requires completion evidence and no gaps")
        if decision["reason"] != REASON_COMPLETE:
            raise ValueError(f"continue reason must be {REASON_COMPLETE!r}")
    elif decision["step_complete"] or not decision["gaps"]:
        raise ValueError("repair requires an incomplete step and non-empty gaps")
    else:
        if decision["reason"] != REASON_INCOMPLETE:
            raise ValueError(f"repair reason must be {REASON_INCOMPLETE!r}")
        contradicted = set(decision["gaps"]) & _contradicted_root_gaps(
            selected["active_step"], selected["evidence_records"],
        )
        if contradicted:
            raise ValueError(
                "gap contradicts visible successful evidence: " + ", ".join(sorted(contradicted))
            )
        catalog_codes = {str(item["code"]) for item in selected["gap_catalog"]}
        if not set(decision["gaps"]) <= catalog_codes:
            raise ValueError("repair gaps must be selected verbatim from gap_catalog codes")
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
        "immutable_goal": prompt["immutable_goal"],
        "catalog_semantics": "possible_unmet_conditions",
        "gap_catalog": [dict(item) for item in prompt["gap_catalog"]],
        "available_evidence_refs": list(prompt["available_evidence_refs"]),
        "evidence_records": [dict(item) for item in prompt["evidence_records"]],
        "feedback": prompt["feedback"],
        "current_question": (
            "Return audit_decision with exactly these six fields: verdict, step_id, "
            "step_complete, evidence_refs, gaps, reason. gap_catalog lists possible "
            "unmet conditions, not established findings. Decide whether each condition "
            "is unmet from the evidence_records; catalog membership does not prove a gap. "
            "A successful complete observation can establish that a resource is empty "
            "or that no matching item exists. Always include both "
            "evidence_refs and gaps arrays, even when an array is empty. Use continue "
            "only when this active step satisfies its success criteria and the relevant "
            "requirements in immutable_goal, with evidence for its declared phase; "
            "do not require mutation from observe or derive_evidence phases. Otherwise "
            "use repair and copy only exact gap codes from gap_catalog. Use reason "
            f"exactly {REASON_COMPLETE!r} for continue or {REASON_INCOMPLETE!r} for repair."
        ),
    }
    return _render(PROMPT_PREFIX, payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return ModelCommand("audit_decision", dict(source["decision"])).canonical


def parse_target(target: str) -> ModelCommand:
    command = _audit_target(target, allowed_verdicts=("continue", "repair"))
    expected_reason = (
        REASON_COMPLETE
        if command.arguments["verdict"] == "continue"
        else REASON_INCOMPLETE
    )
    if command.arguments["reason"] != expected_reason:
        raise ValueError("Auditor target reason is not canonical for its verdict")
    return command


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_PREFIX",
    "REASON_COMPLETE",
    "REASON_INCOMPLETE",
    "build_gap_catalog",
    "build_prompt_source",
    "parse_target",
    "render_prompt",
    "render_target",
    "validate_source",
]
