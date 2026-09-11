"""Rebuild current role protocols from an exact durable request-boundary snapshot.

No workspace is read and no model is initialized. A recorded rendered prompt is
never used as input authority. The caller must load the *exact* stored snapshot
at ``request['boundary_event_id']``; truncating a final state's event list while
retaining future projections is rejected by RunState's replay validation.

Selector requests name ``menu_order_id`` (one of the three registered menus).
Executor requests name ``checkpoint_id`` of the actual disclosed input, whose
parent is the checkpoint used by the production prompt builder. Auditor
requests may name ``audit_boundary_id``; it is otherwise taken from the durable
session-start record. Finalizer uses its durable session-start boundary alone.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

from rwkv_lh.exact_tool_selector.input_protocol import network_selector_input_protocol
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.exact_tool_selector.runtime_projection import (
    build_network_selector_input, goal_frontier_selector_context,
)
from rwkv_lh.goal_loop_protocol import goal_step_action_bindings, rolling_goal_plan
from rwkv_lh.role_feedback import finalizer_feedback, finalizer_retry_feedback, protocol_feedback
from rwkv_lh.goal_state_protocols import (
    auditor_final, auditor_step_v7, executor_args_v7, finalizer_answer, selector_intent_v7,
)
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION, canonical_digest, parse_model_command, render_bootstrap
from rwkv_lh.operation_contracts import project_goal_step_operations
from rwkv_lh.retrieval.actions import build_retrieval_actions
from rwkv_lh.retrieval.policy import NetworkPolicy
from rwkv_lh.retrieval.providers import PublicConnectorProvider
from rwkv_lh.schema import RunState
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController


class RoleInputReconstructionError(ValueError):
    """Required durable facts are absent, inconsistent or outside this boundary."""


def _reconstruction_harness() -> ActionHarness:
    """Read the production tool definitions without creating an execution runtime.

    The full stable menu includes policy-gated extensions even for offline runs.
    Reuse their factory and configured connector capabilities; never reconstruct
    a tool contract from the model's prompt or a separate schema copy.
    """

    def unavailable(*args, **kwargs):
        raise RoleInputReconstructionError("trace reconstruction cannot execute tools")

    class DefinitionOnlyBackend:
        provider_name = "definition-only"
        execute = staticmethod(unavailable)
        recover = staticmethod(unavailable)

    actions = build_retrieval_actions(
        backend=DefinitionOnlyBackend(), network_policy=NetworkPolicy(),
        provenance_resolver=unavailable,
        connector_operations=PublicConnectorProvider.supported_operations,
        include_network_actions=True, clock=unavailable,
    )
    return ActionHarness(actions=actions)


_MODULES = {
    "selector_intent": selector_intent_v7,
    "executor_args": executor_args_v7,
    "auditor_step": auditor_step_v7,
    "finalizer_answer": finalizer_answer,
    "auditor_final": auditor_final,
}


def _latest(state: RunState, event_type: str):
    for event_id in reversed(state.causal_order):
        record = state.causal_records[event_id]
        if record.event_type == event_type:
            return record
    raise RoleInputReconstructionError(f"missing durable {event_type} boundary")


def _coverage(step, progress, contract):
    roots = [*(step.read_roots if step else ()), *(step.write_roots if step else ())]
    descriptors = contract.get("target_descriptors") or ()
    last = progress.get("last_action") or {}
    return {
        "failed_last_action": bool(last and (last.get("status") != "succeeded" or last.get("error_type"))),
        "nonempty_error_type": bool(last.get("error_type")),
        "directory_target": any(item.get("target_kind") == "directory" for item in descriptors),
        "py_root": any(root.endswith(".py") for root in roots),
        "json_root": any(root.endswith(".json") for root in roots),
        "directory_root": any(item.get("target_kind") == "directory" and item.get("path") in roots for item in descriptors),
        "mutate": bool(step and step.phase == "mutate"),
        "execute": bool(step and step.phase == "execute"),
        "missing_target": any(item.get("target_kind") == "missing" for item in descriptors),
    }


def _audit_coverage(state: RunState, evidence_records) -> dict[str, bool]:
    """Project only the source scenarios of actions visible to this role.

    These are historical source-scenario coverage flags, not a claim that every
    role prompt has Selector progress fields. A descriptor records its type at
    the visible action's assignment, including targets later created by that
    action. Unreferenced actions and later assignments contribute no coverage.
    """

    coverage = _coverage(None, {}, {})
    plan = rolling_goal_plan(state)
    bindings = goal_step_action_bindings(state)
    visible_action_ids = {record["action"]["action_id"] for record in evidence_records}
    for action_id in sorted(visible_action_ids):
        binding = bindings.get(action_id)
        started = next((state.causal_records[eid] for eid in state.causal_order if state.causal_records[eid].event_type == "action_started" and state.causal_records[eid].subject_id == action_id), None)
        if binding is None or started is None:
            continue
        step_id, revision = binding
        step = plan.steps.get(step_id)
        if step is None or plan.step_revisions.get(step_id, 1) != revision:
            continue
        assignment = None
        for event_id in reversed(state.causal_order[:started.sequence - 1]):
            event = state.causal_records[event_id]
            if (
                event.event_type == "goal_role_input_boundary"
                and event.payload.get("active_step_id") == step_id
                and event.payload.get("active_step_revision") == revision
            ):
                assignment = event
                break
        if assignment is None:
            continue
        # This input state is the Controller's durable builder result, bound to
        # the visible action's own pre-execution assignment, never model prose.
        execution = assignment.payload.get("executor_execution_state") or {}
        last = execution.get("last_action") or {}
        outcome = last.get("result_progress") or {}
        scenario = _coverage(step, {}, assignment.payload.get("target_contract") or {})
        scenario["failed_last_action"] = bool(last and (last.get("status") != "succeeded" or outcome.get("success") is False))
        scenario["nonempty_error_type"] = bool(outcome.get("error_type"))
        for name, value in scenario.items():
            coverage[name] = coverage[name] or value
    return coverage


def _frontier_facts(state: RunState):
    record = _latest(state, "goal_role_input_boundary")
    payload = record.payload
    plan = rolling_goal_plan(state)
    step_id = str(payload.get("active_step_id") or "")
    revision = payload.get("active_step_revision")
    if not isinstance(revision, int) or isinstance(revision, bool):
        raise RoleInputReconstructionError("durable role boundary has invalid step revision")
    step = plan.steps.get(step_id)
    if step is None or not plan.frontier or plan.frontier[0].step_id != step_id:
        raise RoleInputReconstructionError("durable role boundary is not the active plan frontier")
    # No new action or plan/audit mutation may intervene between the recorded
    # Harness scope and the model input whose facts are being reconstructed.
    for event_id in state.causal_order[record.sequence:]:
        if state.causal_records[event_id].event_type in {
            "action_started", "action_finished", "goal_plan_patch_committed", "goal_audit_accepted",
        }:
            raise RoleInputReconstructionError("durable role boundary is stale after action or plan change")
    mechanical = StatefulGoalLoopController._step_mechanical_evidence_coverage(state, step_id, revision)
    if canonical_digest(mechanical) != payload.get("mechanical_evidence_sha256"):
        raise RoleInputReconstructionError("durable mechanical evidence digest mismatch")
    phase = "observe" if step.phase != "observe" and mechanical["missing_read_roots"] else step.phase
    if payload.get("effective_phase") != phase:
        raise RoleInputReconstructionError("durable effective phase differs from causal facts")
    raw_contract = payload.get("target_contract")
    if not isinstance(raw_contract, Mapping):
        raise RoleInputReconstructionError("missing durable Harness target contract")
    roots = StatefulGoalLoopController._goal_step_target_roots(step, phase, mechanical)
    if tuple(raw_contract.get("roots") or ()) != roots:
        raise RoleInputReconstructionError("durable target roots differ from the active plan remainder")
    contract = executor_args_v7.build_target_contract(
        phase=phase, roots=roots,
        target_descriptors=raw_contract.get("target_descriptors") or (),
        operations=tuple(raw_contract["argument_targets_by_operation"]),
        scope_roots=step.write_roots if phase == "mutate" else roots,
        discovery_complete=raw_contract["discovery_complete"],
    )
    if contract != raw_contract:
        raise RoleInputReconstructionError("durable Harness target contract cannot be rebuilt")
    eligible = payload.get("eligible_operations")
    if not isinstance(eligible, list) or not eligible or len(eligible) != len(set(eligible)):
        raise RoleInputReconstructionError("missing durable operation eligibility")
    authorized = project_goal_step_operations(
        authorized_operations=step.allowed_operations or NETWORK_EXACT_TOOL_LABELS,
        phase=phase, read_roots=step.read_roots, write_roots=step.write_roots,
    )
    if not set(eligible) <= set(authorized):
        raise RoleInputReconstructionError("durable operation eligibility violates the plan")
    from rwkv_lh.operation_contracts import eligible_target_operations
    if tuple(eligible) != eligible_target_operations(contract["argument_targets_by_operation"]):
        raise RoleInputReconstructionError("durable operation eligibility differs from parameter preconditions")
    execution = StatefulGoalLoopController._executor_execution_state(
        state, step_id, revision, mechanical, effective_phase=phase, target_contract=contract,
    )
    if execution != payload.get("executor_execution_state"):
        raise RoleInputReconstructionError("persisted execution state differs from durable actions")
    progress = StatefulGoalLoopController._selector_current_progress(
        state, step_id, revision, mechanical, target_contract=contract,
    )
    return record, step, mechanical, contract, execution, progress, eligible, phase


def rebuild_role_input(role: str, state: RunState, request: Mapping[str, Any]) -> dict[str, Any]:
    """Return byte-recomputable protocol text and its causal evidence bindings.

    Any omission or mismatch is an exclusion, never a prompt-source fallback.
    ``full_input_text`` for Selector is its menu bootstrap followed by a newline
    and the unique protocol prompt; other transports are rebuilt independently
    by the checkpoint/context reconstruction layer.
    """
    if role not in _MODULES:
        raise RoleInputReconstructionError(f"unsupported role {role!r}")
    boundary_id = request.get("boundary_event_id")
    if not state.causal_order or state.causal_order[-1] != boundary_id:
        raise RoleInputReconstructionError("exact request-boundary snapshot is required")
    try:
        state = RunState.from_dict(state.to_dict())
        return _rebuild(role, state, request)
    except RoleInputReconstructionError:
        raise
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise RoleInputReconstructionError(str(exc)) from exc


def _rebuild(role, state, request):
    module = _MODULES[role]
    boundary = state.causal_records[state.causal_order[-1]]
    result = {
        "protocol_version": module.INPUT_SCHEMA_VERSION,
        "boundary_refs": [boundary.event_id], "coverage": _coverage(None, {}, {}),
        "active_step": None, "eligible_operations": [], "missing_read_roots": [],
        "missing_write_roots": [], "evidence_refs": [],
    }
    if role in {"selector_intent", "executor_args"}:
        assignment, step, mechanical, contract, execution, progress, eligible, phase = _frontier_facts(state)
        result.update(
            active_step=step.to_dict(), eligible_operations=eligible,
            missing_read_roots=mechanical["missing_read_roots"],
            missing_write_roots=mechanical["missing_write_roots"],
            coverage=_coverage(step, progress, contract),
            boundary_refs=list(dict.fromkeys([assignment.event_id, boundary.event_id])),
        )
        if role == "selector_intent":
            if boundary.event_type != "goal_role_input_boundary":
                raise RoleInputReconstructionError("Selector requires its durable assignment snapshot")
            context = goal_frontier_selector_context(
                {**step.to_dict(), "effective_phase": phase}, current_progress=progress,
            )
            network = build_network_selector_input(
                context,
                eligible_labels=tuple(label for label in NETWORK_EXACT_TOOL_LABELS if label in eligible),
                menu_order_id=request.get("menu_order_id", "canonical"),
            )
            source = module.build_prompt_source(
                current_subtask=network.current_subtask,
                current_progress=network.current_progress,
                eligible_labels=network.eligible_labels,
            )
            protocol = network_selector_input_protocol(module.INPUT_SCHEMA_VERSION)
            result.update(
                bootstrap_prompt=protocol.render_bootstrap(network), network_input=network.to_dict(),
            )
            result["full_input_text"] = result["bootstrap_prompt"] + "\n" + protocol.render_step(network)
            result["expected_checkpoint_transcript"] = result["full_input_text"]
        else:
            if boundary.event_type != "tool_schema_disclosed":
                raise RoleInputReconstructionError("Executor requires the durable tool disclosure snapshot")
            checkpoint_id = request.get("checkpoint_id")
            if not checkpoint_id or checkpoint_id != boundary.payload.get("checkpoint_id"):
                raise RoleInputReconstructionError("Executor input checkpoint does not match disclosure")
            checkpoint = state.model_states[checkpoint_id]
            parent = state.model_states[checkpoint.parent_checkpoint_id]
            operation = str(boundary.payload.get("selected_operation") or "")
            if operation not in eligible:
                raise RoleInputReconstructionError("Executor operation is outside durable eligibility")
            definition = _reconstruction_harness().g1i_tool_definitions([operation])[0]
            if canonical_digest(definition) != boundary.payload.get("definition_digest"):
                raise RoleInputReconstructionError("current Harness definition differs from durable disclosure")
            source, facts = LongHorizonModel._executor_prompt_source(
                state, parent, definition, current_requirement=step.objective,
                fact_action_ids=StatefulGoalLoopController._step_executor_fact_action_ids(state, step.step_id, execution["active_step_revision"]),
                execution_state=execution,
            )
            if canonical_digest(execution) != boundary.payload.get("executor_execution_state_sha256"):
                raise RoleInputReconstructionError("Executor disclosure execution state digest mismatch")
            result.update(source_checkpoint_id=parent.checkpoint_id, bound_fact_records=list(facts), evidence_refs=list(source["committed_fact_refs"]))
            if checkpoint.transport not in {"native_rwkv", "prompt_replay"}:
                raise RoleInputReconstructionError("unsupported Executor checkpoint transport")
            result["expected_checkpoint_transcript"] = (
                parent.transcript if checkpoint.transport == "prompt_replay" else ""
            ) + "\n\n" + module.render_generation_prompt(source)
    else:
        plan = rolling_goal_plan(state)
        if role == "finalizer_answer":
            if boundary.event_type != "goal_finalizer_session_started" or not plan.complete or not plan.completed_step_ids:
                raise RoleInputReconstructionError("Finalizer requires a complete durable plan at session start")
            refs = tuple(sorted({ref for values in plan.completed_evidence.values() for ref in values}))
            records = LongHorizonModel._audit_evidence_records(state, refs, focus_text=state.goal.request)
            source = module.build_prompt_source(
                immutable_goal=state.goal.request,
                completed_steps=LongHorizonModel._completed_step_records(plan),
                committed_facts=LongHorizonModel._committed_fact_records(records), evidence_records=records,
                feedback=finalizer_feedback(state),
                retry_feedback=finalizer_retry_feedback(state),
            )
        else:
            if boundary.event_type != "goal_auditor_session_started" or boundary.payload.get("auditor_role") != role:
                raise RoleInputReconstructionError("Auditor requires its durable session-start snapshot")
            audit_id = request.get("audit_boundary_id", boundary.payload.get("audit_boundary_id"))
            if not audit_id or audit_id != boundary.payload.get("audit_boundary_id"):
                raise RoleInputReconstructionError("Auditor boundary identity mismatch")
            opened = [state.causal_records[eid] for eid in state.causal_order if state.causal_records[eid].event_type == "goal_audit_boundary_opened" and state.causal_records[eid].subject_id == audit_id]
            if len(opened) != 1:
                raise RoleInputReconstructionError("missing or ambiguous durable audit boundary")
            audit = opened[0]
            if any(state.causal_records[eid].event_type == "goal_audit_boundary_resolved" and state.causal_records[eid].subject_id == audit_id for eid in state.causal_order):
                raise RoleInputReconstructionError("audit boundary was already resolved")
            payload = audit.payload
            if bool(payload.get("final_candidate")) != (role == "auditor_final"):
                raise RoleInputReconstructionError("audit kind differs from durable boundary")
            step_id = str(payload.get("active_step_id") or "")
            step = plan.steps.get(step_id) if step_id else None
            if step_id and (step is None or plan.step_revisions.get(step_id, 1) != payload.get("active_step_revision")):
                raise RoleInputReconstructionError("audit boundary has a stale step revision")
            active = step.to_dict() if step else None
            refs = tuple(sorted(set(payload.get("evidence_refs") or ())))
            records = LongHorizonModel._audit_evidence_records(
                state, refs, focus_text="\n".join(item for item in (state.goal.request, json.dumps(active, ensure_ascii=False, sort_keys=True) if active else "") if item),
            )
            result.update(active_step=active, boundary_refs=[audit.event_id, boundary.event_id])
            if role == "auditor_step":
                if active is None:
                    raise RoleInputReconstructionError("Step Auditor has no active committed step")
                source = module.build_prompt_source(
                    immutable_goal=state.goal.request,
                    boundary=str(payload.get("boundary") or ""), active_step=active,
                    available_evidence_refs=refs, evidence_records=records,
                    feedback=protocol_feedback(state, role, audit_id),
                )
                mechanical = StatefulGoalLoopController._step_mechanical_evidence_coverage(state, step_id, payload["active_step_revision"])
                result.update(missing_read_roots=mechanical["missing_read_roots"], missing_write_roots=mechanical["missing_write_roots"])
            else:
                if not plan.complete:
                    raise RoleInputReconstructionError("Final Auditor requires a complete durable plan")
                decision = state.decisions.get(str(payload.get("decision_id") or ""))
                if decision is None or not decision.accepted:
                    raise RoleInputReconstructionError("Final Auditor lacks an accepted durable Finalizer candidate")
                candidate = parse_model_command(decision.raw_output)
                finalizer_answer.parse_target(candidate.canonical)
                source = module.build_prompt_source(
                    immutable_goal=state.goal.request, completed_steps=LongHorizonModel._completed_step_records(plan),
                    available_evidence_refs=refs, evidence_records=records,
                    final_candidate={"function": candidate.name, "params": dict(candidate.arguments)},
                    feedback=protocol_feedback(state, role, audit_id),
                )
        result["evidence_refs"] = list(refs)
        result["coverage"] = _audit_coverage(state, records)
    prompt = module.render_generation_prompt(source) if role == "executor_args" else module.render_prompt(source)
    result.update(prompt_source=source, protocol_prompt=prompt)
    if role in {"auditor_step", "auditor_final", "finalizer_answer"}:
        definition = (
            FINAL_ANSWER_DEFINITION if role == "finalizer_answer"
            else LongHorizonModel._goal_audit_definition(role == "auditor_final")
        )
        result["expected_checkpoint_transcript"] = render_bootstrap(
            (definition,), prompt, native_tool_call_json=True,
        )
    expected_digest = boundary.payload.get("prompt_sha256")
    if role != "selector_intent":
        hashed_prompt = "\n\n" + prompt if role == "executor_args" else prompt
        if not expected_digest or hashlib.sha256(hashed_prompt.encode("utf-8")).hexdigest() != expected_digest:
            raise RoleInputReconstructionError("rebuilt protocol prompt differs from durable prompt digest")
    return result


__all__ = ["RoleInputReconstructionError", "rebuild_role_input"]
