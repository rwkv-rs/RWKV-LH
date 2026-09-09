"""Shared feedback value contract; no model role or completion authority."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from typing import Any

from rwkv_lh.goal_state_protocols import _exact_fields, _nonempty, _nonnegative_int, _objects, _strings

SCHEMA_VERSION = "rwkv-lh.role-feedback.v1"
FIELDS = ("schema_version", "kind", "source_role", "recipient_roles", "boundary_id",
          "source_id", "plan_revision", "step_id", "step_revision", "issues", "rejected_output")
ISSUE_FIELDS = ("code", "criterion", "repair_scope", "evidence_refs")
ROLES = frozenset({"selector_intent", "executor_args", "auditor_step", "finalizer_answer", "auditor_final", "planner"})


def validate_feedback(value: Any, *, recipient: str | None = None) -> Mapping[str, Any] | None:
    if value is None:
        return None
    packet = _exact_fields(value, FIELDS, "feedback")
    if packet["schema_version"] != SCHEMA_VERSION:
        raise ValueError("unsupported feedback schema")
    if packet["kind"] not in {"semantic", "protocol"} or packet["source_role"] not in ROLES:
        raise ValueError("invalid feedback kind or source role")
    recipients = _strings(packet["recipient_roles"], "feedback.recipient_roles", nonempty=True, sorted_unique=True)
    if not set(recipients) <= ROLES or (recipient is not None and recipient not in recipients):
        raise ValueError("feedback belongs to another role")
    for name in ("boundary_id", "source_id"):
        _nonempty(packet[name], f"feedback.{name}")
    for name in ("plan_revision", "step_revision"):
        _nonnegative_int(packet[name], f"feedback.{name}")
    if not isinstance(packet["step_id"], str) or not isinstance(packet["rejected_output"], str):
        raise ValueError("feedback step and rejected output must be strings")
    if bool(packet["step_id"]) != bool(packet["step_revision"]):
        raise ValueError("feedback step revision binding is incomplete")
    scopes, codes = set(), []
    for issue in _objects(packet["issues"], "feedback.issues", nonempty=True):
        item = _exact_fields(issue, ISSUE_FIELDS, "feedback issue")
        codes.append(_nonempty(item["code"], "feedback issue code"))
        _nonempty(item["criterion"], "feedback issue criterion")
        if item["repair_scope"] not in {"step", "answer", "execution", "protocol"}:
            raise ValueError("invalid feedback repair scope")
        scopes.add(item["repair_scope"])
        _strings(item["evidence_refs"], "feedback issue evidence_refs", sorted_unique=True)
    if codes != sorted(set(codes)):
        raise ValueError("feedback issues must have sorted unique codes")
    if packet["kind"] == "protocol":
        expected = (packet["source_role"],)
        if scopes != {"protocol"}:
            raise ValueError("protocol feedback cannot carry semantic authority")
    else:
        if packet["source_role"] == "auditor_step" and scopes == {"step"}:
            expected = ("executor_args", "selector_intent")
        elif packet["source_role"] == "auditor_final" and scopes <= {"answer", "execution"}:
            expected = ("planner",) if "execution" in scopes else ("finalizer_answer",)
        else:
            raise ValueError("semantic feedback scope differs from its source role")
    if recipients != expected:
        raise ValueError("feedback recipients differ from the declared repair scope")
    return packet


def build_feedback(*, kind: str, source_role: str, boundary_id: str, source_id: str,
                   plan_revision: int, step_id: str = "", step_revision: int = 0,
                   issues: Sequence[Mapping[str, Any]], rejected_output: str = "") -> dict[str, Any]:
    ordered = sorted((deepcopy(dict(item)) for item in issues), key=lambda item: item["code"])
    scopes = {item["repair_scope"] for item in ordered}
    recipients = ([source_role] if kind == "protocol" else ["planner"] if "execution" in scopes
                  else ["finalizer_answer"] if "answer" in scopes else ["executor_args", "selector_intent"])
    packet = {"schema_version": SCHEMA_VERSION, "kind": kind, "source_role": source_role,
              "recipient_roles": recipients, "boundary_id": boundary_id, "source_id": source_id,
              "plan_revision": plan_revision, "step_id": step_id, "step_revision": step_revision,
              "issues": ordered, "rejected_output": rejected_output}
    validate_feedback(packet)
    return packet


def semantic_feedback(*, source_role: str, boundary_id: str, source_id: str, plan_revision: int,
                      step_id: str = "", step_revision: int = 0, gap_codes: Sequence[str],
                      gap_catalog: Sequence[Mapping[str, Any]], evidence_refs: Sequence[str],
                      rejected_output: str = "") -> dict[str, Any] | None:
    if not gap_codes:
        return None
    catalog = {item["code"]: item for item in gap_catalog}
    if not set(gap_codes) <= set(catalog):
        raise ValueError("feedback gaps are absent from the audited input")
    issues = [{"code": code, "criterion": catalog[code]["criterion"],
               "repair_scope": "step" if source_role == "auditor_step" else catalog[code]["repair_scope"],
               "evidence_refs": sorted(set(evidence_refs))} for code in gap_codes]
    return build_feedback(kind="semantic", source_role=source_role, boundary_id=boundary_id,
                          source_id=source_id, plan_revision=plan_revision, step_id=step_id,
                          step_revision=step_revision, issues=issues, rejected_output=rejected_output)
