"""Pure projections of durable feedback, shared by runtime and trace replay."""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.goal_loop_protocol import GoalAuditDecision, rolling_goal_plan
from rwkv_lh.goal_state_protocols.execution_failures import build_rejections


def step_rejections(state: Any, step_id: str, step_revision: int) -> list[dict]:
    """Restore pre-execution failures since the last action on this exact step.

    Keep the semantic audit feedback separately: an invalid parameter call does
    not supersede the Auditor's still-unresolved task criterion.
    """
    plan = rolling_goal_plan(state)
    if step_id not in plan.steps or plan.step_revisions.get(step_id, 1) != step_revision:
        raise ValueError("rejections require the current committed step revision")
    records = []
    for event in _events(state):
        payload = event.payload
        if event.event_type == "action_started":
            break
        if event.event_type != "protocol_rejection_recorded" or payload.get("protocol_scope") != "action":
            continue
        if (payload.get("active_step_id"), payload.get("active_step_revision")) != (step_id, step_revision):
            continue
        if not payload.get("selection_id") or not payload.get("selected_operation"):
            continue
        records.append({"event_id": event.event_id, "selection_id": payload["selection_id"],
            "step_id": step_id, "step_revision": step_revision,
            "selected_operation": payload["selected_operation"],
            "rejected_arguments": payload.get("rejected_arguments") or {},
            "error_kind": str(payload.get("error_kind") or ""), "error": payload["error"],
            "action_executed": False})
    return build_rejections(list(reversed(records)))


def _events(state):
    return (state.causal_records[key] for key in reversed(state.causal_order))


def _copy(value, *, recipient=None):
    checked = validate_feedback(value, recipient=recipient)
    return deepcopy(dict(checked)) if checked is not None else None


def feedback_for_audit(state: Any, audit_id: str) -> dict | None:
    for event in _events(state):
        if event.event_type == "goal_audit_accepted" and event.payload.get("audit_id") == audit_id:
            feedback = event.payload.get("feedback")
            if feedback is None and (event.payload.get("audit") or {}).get("verdict") == "repair":
                raise ValueError("accepted repair is missing its current feedback contract")
            return _copy(feedback)
    raise ValueError("feedback requires a durable accepted audit")


def step_feedback(state: Any, step_id: str, step_revision: int) -> dict | None:
    plan = rolling_goal_plan(state)
    if plan.step_revisions.get(step_id, 1) != step_revision:
        raise ValueError("feedback requires the current step revision")
    boundaries = {event.subject_id: event.payload for event in _events(state)
                  if event.event_type == "goal_audit_boundary_opened"}
    for event in _events(state):
        if event.event_type != "goal_audit_accepted":
            continue
        bound = boundaries.get(event.payload.get("audit_boundary_id"), {})
        if (bound.get("active_step_id"), bound.get("active_step_revision")) != (step_id, step_revision):
            continue
        feedback = feedback_for_audit(state, event.payload["audit_id"])
        if feedback is not None and (feedback["step_id"], feedback["step_revision"]) != (step_id, step_revision):
            raise ValueError("audit feedback and boundary disagree on step identity")
        return feedback
    return None


def protocol_feedback(state: Any, role: str, boundary_id: str) -> dict | None:
    for event in _events(state):
        if event.event_type == "protocol_rejection_recorded":
            value = event.payload.get("feedback")
            if isinstance(value, Mapping) and value.get("source_role") == role and value.get("boundary_id") == boundary_id:
                return _copy(value, recipient=role)
    return None


def rejected_audit_output(state: Any, request_id: str, boundary_id: str) -> str:
    """Recover the exact rejected generation from its durable audit boundary."""
    if not request_id:
        # A pre-generation contract failure has no rejected model output.
        return ""
    for event in _events(state):
        payload = event.payload
        if (event.event_type == "goal_audit_recorded"
            and payload.get("request_id") == request_id
            and payload.get("audit_boundary_id") == boundary_id):
            raw = (payload.get("raw_generation") or {}).get("raw_output")
            if not isinstance(raw, str):
                raise ValueError("rejected audit generation lacks its raw output")
            return raw
    raise ValueError("rejected audit request has no matching durable boundary")


def audit_protocol_rejections(state: Any, boundary_id: str) -> int:
    count = 0
    for event in _events(state):
        if event.event_type == "run_started" and event.payload.get("protocol_rejection_budget_reset"):
            break
        if event.event_type == "protocol_rejection_recorded" and event.payload.get("audit_boundary_id") == boundary_id:
            count += 1
    return count


def finalizer_feedback(state: Any) -> dict | None:
    revision = len(rolling_goal_plan(state).patch_ids)
    for event in _events(state):
        if event.event_type == "goal_plan_patch_committed":
            break
        if event.event_type == "goal_final_rejected":
            value = event.payload.get("feedback")
            if isinstance(value, Mapping) and value.get("plan_revision") == revision and "finalizer_answer" in value.get("recipient_roles", ()):
                return _copy(value, recipient="finalizer_answer")
    return None


def finalizer_retry_feedback(state: Any) -> dict | None:
    revision = len(rolling_goal_plan(state).patch_ids)
    for event in _events(state):
        if event.event_type in {"goal_plan_patch_committed", "goal_final_rejected"}:
            break
        if event.event_type == "model_call_accepted" and event.payload.get("model_role") == "finalizer_answer":
            break
        if event.event_type == "protocol_rejection_recorded":
            value = event.payload.get("feedback")
            if isinstance(value, Mapping) and value.get("plan_revision") == revision and value.get("source_role") == "finalizer_answer":
                return _copy(value, recipient="finalizer_answer")
    return None


def pending_final_execution_repair(state: Any) -> tuple[GoalAuditDecision, dict] | None:
    revision = len(rolling_goal_plan(state).patch_ids)
    consumed = {event.payload.get("source_audit_id") for event in _events(state)
                if event.event_type == "goal_plan_patch_committed"}
    for event in _events(state):
        if event.event_type != "goal_final_rejected":
            continue
        feedback = event.payload.get("feedback")
        if not isinstance(feedback, Mapping) or feedback.get("plan_revision") != revision:
            continue
        if "planner" not in feedback.get("recipient_roles", ()) or event.payload.get("audit_id") in consumed:
            return None
        checked = _copy(feedback, recipient="planner")
        for accepted in _events(state):
            if accepted.event_type == "goal_audit_accepted" and accepted.payload.get("audit_id") == event.payload.get("audit_id"):
                return GoalAuditDecision.from_dict(accepted.payload["audit"]), checked
        raise ValueError("final execution repair lacks an accepted audit")
    return None
