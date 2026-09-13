"""Read-only projections of direct and child-atom activity from one run ledger."""

from __future__ import annotations

from typing import Any, Mapping

from rwkv_lh.schema import RunState


def unresolved_supervisor_pending(
    state: RunState,
) -> tuple[Mapping[str, Any], ...]:
    """Fold pending/resolved supervisor events into the current retry set."""

    unresolved: dict[str, Mapping[str, Any]] = {}
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type == "supervisor_call_pending":
            pending_id = str(event.payload.get("pending_id") or "")
            if pending_id:
                unresolved[pending_id] = dict(event.payload)
        elif event.event_type == "supervisor_call_resolved":
            pending_id = str(event.payload.get("pending_id") or "")
            if pending_id:
                unresolved.pop(pending_id, None)
    return tuple(unresolved.values())


def _network_policy_rejected(
    *,
    outcome_type: str = "",
    error: Mapping[str, Any] | None = None,
    result: Mapping[str, Any] | None = None,
) -> bool:
    selected_result = result if isinstance(result, Mapping) else {}
    result_error = selected_result.get("error")
    error_types = {
        str(item.get("type") or "")
        for item in (error, result_error)
        if isinstance(item, Mapping)
    }
    if "NetworkPolicyRejected" in error_types:
        return True
    return str(outcome_type or selected_result.get("outcome_type") or "") == (
        "policy_rejected"
    )


def project_run_activity(state: RunState) -> dict[str, Any]:
    """Fold parent and atom execution without creating a second mutable ledger."""

    direct_actions = [
        {
            "activity_id": action.action_id,
            "origin": "direct",
            "action_id": action.action_id,
            "sequence": action.sequence,
            "operation": action.action_type,
            "status": action.status.value,
            "artifact_refs": list(action.artifact_refs),
            "atom_id": "",
            "stage_id": "",
            "network_policy_rejected": _network_policy_rejected(
                outcome_type=action.outcome_type,
                error=action.error,
                result=action.result,
            ),
        }
        for action in sorted(state.actions.values(), key=lambda item: item.sequence)
    ]
    atom_actions: list[dict[str, Any]] = []
    atom_model_requests = 0
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type != "atom_outcome_committed":
            continue
        outcome = event.payload.get("outcome")
        if not isinstance(outcome, Mapping):
            continue
        stage_id = str(outcome.get("stage_id") or "")
        atom_id = str(outcome.get("atom_id") or "")
        atom_model_requests += int(outcome.get("model_request_count", 0) or 0)
        for action in outcome.get("actions") or ():
            if not isinstance(action, Mapping):
                continue
            action_id = str(action.get("action_id") or "")
            activity_id = f"{stage_id}:{atom_id}:{action_id}"
            atom_actions.append(
                {
                    "activity_id": activity_id,
                    "origin": "atom",
                    "action_id": action_id,
                    "sequence": int(action.get("sequence", 0) or 0),
                    "operation": str(action.get("operation") or ""),
                    "status": str(action.get("status") or ""),
                    "artifact_refs": list(action.get("artifact_refs") or ()),
                    "atom_id": atom_id,
                    "stage_id": stage_id,
                    "network_policy_rejected": _network_policy_rejected(
                        outcome_type=str(action.get("outcome_type") or ""),
                        error=(
                            action.get("error")
                            if isinstance(action.get("error"), Mapping)
                            else None
                        ),
                        result=(
                            action.get("result")
                            if isinstance(action.get("result"), Mapping)
                            else None
                        ),
                    ),
                }
            )
    direct_model_requests = len(state.temp_decisions)
    return {
        "actions": [*direct_actions, *atom_actions],
        "direct_actions": direct_actions,
        "atom_actions": atom_actions,
        "direct_model_requests": direct_model_requests,
        "atom_model_requests": atom_model_requests,
        "rwkv_model_requests": direct_model_requests + atom_model_requests,
    }


def projected_tool_outputs(state: RunState) -> tuple[str, ...]:
    """Return committed tool output text across direct and atom execution."""

    outputs: list[str] = []
    for action in state.actions.values():
        result = action.result
        if isinstance(result, Mapping):
            output = result.get("output")
            if isinstance(output, str) and output.strip():
                outputs.append(output)
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type != "atom_outcome_committed":
            continue
        outcome = event.payload.get("outcome")
        if not isinstance(outcome, Mapping):
            continue
        for action in outcome.get("actions") or ():
            if not isinstance(action, Mapping):
                continue
            result = action.get("result")
            if not isinstance(result, Mapping):
                continue
            output = result.get("output")
            if isinstance(output, str) and output.strip():
                outputs.append(output)
    return tuple(outputs)


__all__ = [
    "project_run_activity",
    "projected_tool_outputs",
    "unresolved_supervisor_pending",
]
