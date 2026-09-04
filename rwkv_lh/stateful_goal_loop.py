"""Single-State RWKV Goal loop with an evidence-bound RWKV audit fork."""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Mapping
from uuid import uuid4

from rwkv_lh.controller import ControllerResult, LongHorizonController
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_ABSTAIN_LABEL
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SelectorStageContext,
    goal_frontier_selector_context,
)
from rwkv_lh.goal_loop_protocol import (
    GOAL_PLAN_PATCH_SCHEMA_VERSION,
    GoalAuditDecision,
    GoalAuditVerdict,
    GoalPlanPatch,
    GoalPlanRequest,
    GoalStageReview,
    GoalStageReviewRequest,
    GoalStageReviewVerdict,
    RollingGoalPlan,
    action_mutates_root,
    action_observes_root,
    goal_step_action_bindings,
    rolling_goal_plan,
)
from rwkv_lh.model import ModelProtocolError
from rwkv_lh.model_io import parse_model_command
from rwkv_lh.operation_contracts import (
    EXTERNAL_OBSERVE_OPERATIONS,
    GOAL_STEP_PHASE_OPERATIONS,
    LOCAL_OBSERVE_OPERATIONS,
)
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.schema import ActionStatus, ModelEvent, RunStatus, utc_now
from rwkv_lh.supervisor import supervisor_identity


STATEFUL_GOAL_LOOP_ARCHITECTURE = "rwkv-stateful-goal-loop.v4"


class StatefulGoalLoopController(LongHorizonController):
    """Strong-plan, single-State RWKV execute, RWKV-audit Goal loop."""

    _MAX_EXECUTOR_RETRIES_PER_SELECTION = 1

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        if self.supervisor is None:
            raise ValueError(
                "stateful_goal requires the existing validated Strong Planner"
            )
        if self.atom_worker_pool is not None:
            raise ValueError("stateful_goal uses one RWKV State, not an atom worker pool")
        if self.model.tool_selector is None:
            raise ValueError(
                "stateful_goal requires the independent Selector; direct Executor "
                "tool-selection fallback is not part of this architecture"
            )
        self.model.validate_goal_role_sessions()

    @staticmethod
    def _recent_action_facts(
        state: Any,
        *,
        action_ids: tuple[str, ...] | None = None,
        max_actions: int = 12,
        result_limit: int = 2400,
    ) -> tuple[Mapping[str, Any], ...]:
        """Expose bounded Harness facts without any Executor prose."""

        def summary(value: Any, limit: int) -> tuple[str, bool]:
            text = json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                default=str,
            )
            encoded = text.encode("utf-8")
            if len(encoded) <= limit:
                return text, False
            return encoded[:limit].decode("utf-8", errors="ignore"), True

        allowed = set(action_ids) if action_ids is not None else None
        actions = sorted(
            (
                action
                for action in state.actions.values()
                if allowed is None or action.action_id in allowed
            ),
            key=lambda item: item.sequence,
        )[-max_actions:]
        projected: list[Mapping[str, Any]] = []
        for action in actions:
            arguments_summary, arguments_truncated = summary(action.arguments, 1200)
            result_summary, result_truncated = summary(action.result, result_limit)
            projected.append({
                "action_id": action.action_id,
                "operation": action.action_type,
                "status": action.status.value,
                "arguments_projection": arguments_summary,
                "arguments_truncated": arguments_truncated,
                "result_projection": result_summary,
                "result_truncated": result_truncated,
                "artifact_refs": list(action.artifact_refs),
                "workspace_digest_after": action.workspace_digest_after,
                "error_type": str(
                    (action.error if isinstance(action.error, Mapping) else {}).get(
                        "type"
                    )
                    or ""
                ),
            })
        return tuple(projected)

    @staticmethod
    def _step_audit_evidence_refs(
        state: Any,
        step_id: str,
        step_revision: int,
    ) -> tuple[str, ...]:
        """Project bounded cumulative Harness facts for one assigned plan step."""

        bindings = goal_step_action_bindings(state)
        actions = sorted(
            (
                action
                for action_id, action in state.actions.items()
                if bindings.get(action_id) == (step_id, step_revision)
            ),
            key=lambda item: item.sequence,
        )
        if not actions:
            return ()

        # Preserve the current boundary plus the newest successful action that
        # covers each Planner root. A plain latest-eight window can irreversibly
        # discard the only read/write proof after unrelated repeated actions.
        selected: list[Any] = [actions[-1]]
        step = rolling_goal_plan(state).steps.get(step_id)
        if step is not None:
            root_checks = (
                *((root, action_mutates_root) for root in step.write_roots),
                *((root, action_observes_root) for root in step.read_roots),
            )
            for root, covers in root_checks:
                match = next(
                    (
                        action
                        for action in reversed(actions)
                        if action.status is ActionStatus.SUCCEEDED
                        and bool((action.result or {}).get("success"))
                        and covers(action, root)
                    ),
                    None,
                )
                if match is not None and match not in selected:
                    selected.append(match)
                if len(selected) >= 8:
                    break

        # Root-free semantic steps still need at least one successful Harness
        # fact when the latest boundary is a failure.
        if len(selected) < 8 and not any(
            action.status is ActionStatus.SUCCEEDED
            and bool((action.result or {}).get("success"))
            for action in selected
        ):
            latest_success = next(
                (
                    action
                    for action in reversed(actions)
                    if action.status is ActionStatus.SUCCEEDED
                    and bool((action.result or {}).get("success"))
                ),
                None,
            )
            if latest_success is not None and latest_success not in selected:
                selected.append(latest_success)

        return tuple(
            action.action_id
            for action in sorted(selected, key=lambda item: item.sequence)
        )

    @staticmethod
    def _step_mechanical_evidence_coverage(
        state: Any,
        step_id: str,
        step_revision: int,
    ) -> dict[str, Any]:
        """Compile Harness-owned prerequisites before semantic Step Audit.

        The Planner declares roots and semantic success criteria.  It does not
        prove that an action observed or mutated those roots.  The Controller
        can establish that mechanical fact from exact successful action
        arguments, so an incomplete step must not consume an Auditor call or
        gain completion authority.
        """

        plan = rolling_goal_plan(state)
        step = plan.steps.get(step_id)
        if step is None:
            raise ValueError("mechanical evidence gate requires a committed plan step")
        expected_revision = plan.step_revisions.get(step_id, 1)
        if step_revision != expected_revision:
            raise ValueError("mechanical evidence gate received a stale step revision")

        bindings = goal_step_action_bindings(state)
        assigned_actions = sorted(
            (
                action
                for action_id, action in state.actions.items()
                if bindings.get(action_id) == (step_id, step_revision)
            ),
            key=lambda item: item.sequence,
        )
        successful_actions = tuple(
            action
            for action in assigned_actions
            if action.status is ActionStatus.SUCCEEDED
            and bool((action.result or {}).get("success"))
        )
        missing_read_roots = tuple(
            root
            for root in step.read_roots
            if not any(
                action_observes_root(action, root)
                for action in successful_actions
            )
        )
        missing_write_roots = tuple(
            root
            for root in step.write_roots
            if not any(
                action_mutates_root(action, root)
                for action in successful_actions
            )
        )
        gaps = [
            f"missing successful observation evidence for read_root {root!r}"
            for root in missing_read_roots
        ]
        gaps.extend(
            f"missing successful mutation evidence for write_root {root!r}"
            for root in missing_write_roots
        )
        if not successful_actions and not gaps:
            gaps.append("active step has no successful Harness action evidence")

        return {
            "active_step_id": step_id,
            "active_step_revision": step_revision,
            "assigned_action_ids": [action.action_id for action in assigned_actions],
            "successful_action_ids": [
                action.action_id for action in successful_actions
            ],
            "missing_read_roots": list(missing_read_roots),
            "missing_write_roots": list(missing_write_roots),
            "gaps": gaps,
            "completion_preconditions_satisfied": not gaps,
            "completion_authority": False,
            "source": "controller_mechanical_evidence_gate",
        }

    @staticmethod
    def _step_executor_fact_action_ids(
        state: Any,
        step_id: str,
        step_revision: int,
    ) -> tuple[str, ...]:
        """Return only current-step and declared-dependency facts for Executor."""

        plan = rolling_goal_plan(state)
        step = plan.steps.get(step_id)
        if step is None:
            raise ValueError("Executor fact scope requires a committed plan step")
        if plan.step_revisions.get(step_id, 1) != step_revision:
            raise ValueError("Executor fact scope received a stale step revision")

        bindings = goal_step_action_bindings(state)
        selected = {
            action_id
            for action_id, binding in bindings.items()
            if binding == (step_id, step_revision)
        }
        revisions = {
            revision.revision_id: revision
            for values in state.artifact_revisions.values()
            for revision in values
        }
        for dependency_id in step.depends_on:
            for evidence_ref in plan.completed_evidence.get(dependency_id, ()):
                if evidence_ref in state.actions:
                    selected.add(evidence_ref)
                elif (artifact := state.artifacts.get(evidence_ref)) is not None:
                    selected.add(artifact.action_id)
                elif (revision := revisions.get(evidence_ref)) is not None:
                    selected.add(revision.action_id)

        return tuple(
            action.action_id
            for action in sorted(
                (state.actions[action_id] for action_id in selected),
                key=lambda item: item.sequence,
            )
        )

    def _goal_step_operations(
        self,
        state: Any,
        step: Any,
        *,
        mechanical_evidence: Mapping[str, Any] | None = None,
    ) -> tuple[str, ...]:
        """Compile the Harness menu for one Planner step without choosing a tool."""

        authorized = (
            tuple(
                operation
                for operation in step.allowed_operations
                if operation != "final_answer"
            )
            if step.allowed_operations
            else self.model.goal_action_operations(state)
        )
        phase = step.phase
        if (
            phase != "observe"
            and mechanical_evidence is not None
            and mechanical_evidence.get("missing_read_roots")
        ):
            phase = "observe"
        family = GOAL_STEP_PHASE_OPERATIONS[phase]
        if phase == "observe":
            family = (
                LOCAL_OBSERVE_OPERATIONS
                if step.read_roots
                else EXTERNAL_OBSERVE_OPERATIONS
            )
        elif phase == "execute":
            family = frozenset(
                {"run_command" if step.write_roots else "check_command"}
            )
        operations = tuple(
            operation
            for operation in authorized
            if operation in family
        )
        if not operations:
            raise ModelProtocolError(
                f"Planner phase {phase!r} has no authorized operation for step "
                f"{step.step_id!r}"
            )
        return operations

    def _pending_executor_protocol_retry(
        self,
        state: Any,
    ) -> ModelEvent | None:
        """Recover one durable same-tool Executor retry without reselecting.

        A malformed parameter object consumes its staged Selector handoff, but
        it does not invalidate the selected tool. Replaying the causal rejection
        as a deterministic Executor event preserves the selection lineage across
        controller restarts and keeps the Selector out of parameter repair.
        """

        for causal_event_id in reversed(state.causal_order):
            record = state.causal_records[causal_event_id]
            if record.event_type != "protocol_rejection_recorded":
                continue
            payload = record.payload
            if str(payload.get("protocol_scope") or "") != "action":
                continue
            selection_id = str(payload.get("selection_id") or "")
            selected_operation = str(payload.get("selected_operation") or "")
            selection = state.tool_selections.get(selection_id)
            selection_rejections = sum(
                1
                for event_id in state.causal_order
                if (
                    state.causal_records[event_id].event_type
                    == "protocol_rejection_recorded"
                    and str(
                        state.causal_records[event_id].payload.get(
                            "protocol_scope"
                        )
                        or ""
                    )
                    == "action"
                    and str(
                        state.causal_records[event_id].payload.get("selection_id")
                        or ""
                    )
                    == selection_id
                )
            )
            if (
                not selection_id
                or selected_operation not in self.model._definitions_by_name
                or selection is None
                or selection.status.value != "consumed"
                or selection.selected_operation != selected_operation
                or not bool(payload.get("schema_already_disclosed"))
                or selection_rejections
                > self._MAX_EXECUTOR_RETRIES_PER_SELECTION
            ):
                return None
            retry_event_id = "EV-GOAL-REJECT-" + hashlib.sha256(
                causal_event_id.encode("utf-8")
            ).hexdigest()[:16]
            if retry_event_id in state.model_events:
                return None
            return ModelEvent(
                event_type="protocol_rejection",
                event_id=retry_event_id,
                scope_id=self.model.ACTION_LANE_ID,
                payload={
                    "error": str(payload.get("error") or "")[:2000],
                    "action_executed": False,
                    "rejected_arguments": dict(
                        payload.get("rejected_arguments") or {}
                    ),
                    "selection_id": selection_id,
                    "selected_operation": selected_operation,
                    "schema_already_disclosed": True,
                    "instruction": (
                        "Retry the same selected operation. Return one displayed "
                        "direct function call with its complete explicit parameter "
                        "object; do not choose another operation."
                    ),
                },
            )
        return None

    @staticmethod
    def _consecutive_action_protocol_rejections(state: Any) -> int:
        """Count durable Executor failures since the latest executed action."""

        count = 0
        for event_id in reversed(state.causal_order):
            event = state.causal_records[event_id]
            if event.event_type == "action_finished":
                break
            if (
                event.event_type == "run_started"
                and bool(event.payload.get("protocol_rejection_budget_reset"))
            ):
                break
            if (
                event.event_type == "protocol_rejection_recorded"
                and str(event.payload.get("protocol_scope") or "") == "action"
            ):
                count += 1
        return count

    def _assign_action_to_step(
        self,
        state: Any,
        *,
        action_id: str,
        step_id: str,
        step_revision: int,
        patch_ids: tuple[str, ...] | list[str],
    ) -> None:
        bindings = goal_step_action_bindings(state)
        prior = bindings.get(action_id)
        if prior is not None:
            if prior != (step_id, step_revision):
                raise ValueError("Harness action cannot be reassigned to another step")
            return
        if action_id not in state.actions or not step_id or step_revision < 1:
            raise ValueError("goal action assignment requires action and step")
        self._persist(
            state,
            "goal_action_plan_step_assigned",
            {
                "action_id": action_id,
                "step_id": step_id,
                "step_revision": step_revision,
                "strong_planner_patch_ids": list(patch_ids),
                "assignment_source": "active_committed_frontier",
                "completion_authority": False,
            },
            subject_id=action_id,
        )

    @staticmethod
    def _pending_audit_boundary(state: Any) -> dict[str, Any] | None:
        opened: dict[str, dict[str, Any]] = {}
        resolved: set[str] = set()
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type == "goal_audit_boundary_opened":
                opened[event.subject_id] = {
                    **dict(event.payload),
                    "audit_boundary_id": event.subject_id,
                }
            elif event.event_type == "goal_audit_boundary_resolved":
                resolved.add(event.subject_id)
        pending = [
            payload for boundary_id, payload in opened.items() if boundary_id not in resolved
        ]
        if len(pending) > 1:
            raise ValueError("more than one Goal Audit boundary is unresolved")
        return pending[0] if pending else None

    def _open_audit_boundary(
        self,
        state: Any,
        *,
        boundary_kind: str,
        boundary: str,
        active_step_id: str = "",
        active_step_revision: int = 0,
        action_id: str = "",
        decision_id: str = "",
        evidence_refs: tuple[str, ...] = (),
        final_candidate: bool = False,
    ) -> dict[str, Any]:
        if self._pending_audit_boundary(state) is not None:
            raise ValueError("cannot open a second Goal Audit boundary")
        boundary_id = f"GAB-{uuid4().hex[:16]}"
        payload = {
            "boundary_kind": boundary_kind,
            "boundary": boundary,
            "active_step_id": active_step_id,
            "active_step_revision": active_step_revision,
            "action_id": action_id,
            "decision_id": decision_id,
            "evidence_refs": list(evidence_refs),
            "final_candidate": bool(final_candidate),
            "observation_event_id": (
                f"EV-ACTION-{action_id}" if action_id else ""
            ),
            "authorizes_new_action": False,
        }
        self._persist(
            state,
            "goal_audit_boundary_opened",
            payload,
            subject_id=boundary_id,
        )
        return {**payload, "audit_boundary_id": boundary_id}

    @staticmethod
    def _accepted_boundary_audit(
        state: Any,
        audit_boundary_id: str,
    ) -> GoalAuditDecision | None:
        for event_id in reversed(state.causal_order):
            event = state.causal_records[event_id]
            if event.event_type != "goal_audit_accepted":
                continue
            if str(event.payload.get("audit_boundary_id") or "") != audit_boundary_id:
                continue
            raw = event.payload.get("audit")
            if not isinstance(raw, Mapping):
                raise ValueError("accepted Goal Audit boundary has no complete decision")
            return GoalAuditDecision.from_dict(raw)
        return None

    def _run_pending_audit_boundary(
        self,
        state: Any,
        pending: Mapping[str, Any],
    ) -> GoalAuditDecision:
        boundary_id = str(pending.get("audit_boundary_id") or "")
        accepted = self._accepted_boundary_audit(state, boundary_id)
        if accepted is not None:
            return accepted
        action_id = str(pending.get("action_id") or "")
        event = None
        if action_id:
            action = state.actions.get(action_id)
            if action is None:
                raise ValueError("pending Goal Audit action is missing")
            observation_event_id = str(pending.get("observation_event_id") or "")
            if observation_event_id not in state.model_events:
                event = self._action_observation_event(state, action)
        return self.model.audit_goal_boundary(
            state,
            self._persist_callback,
            boundary=str(pending.get("boundary") or ""),
            audit_boundary_id=boundary_id,
            event=event,
            final_candidate=bool(pending.get("final_candidate")),
            final_candidate_command=(
                parse_model_command(
                    state.decisions[
                        str(pending.get("decision_id") or "")
                    ].raw_output
                )
                if bool(pending.get("final_candidate"))
                and str(pending.get("decision_id") or "") in state.decisions
                else None
            ),
            active_step_id=str(pending.get("active_step_id") or ""),
            relevant_evidence_refs=tuple(
                str(item) for item in pending.get("evidence_refs") or ()
            ),
        )

    def _resolve_audit_boundary(
        self,
        state: Any,
        pending: Mapping[str, Any],
        audit: GoalAuditDecision,
    ) -> None:
        boundary_id = str(pending.get("audit_boundary_id") or "")
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if (
                event.event_type == "goal_audit_boundary_resolved"
                and event.subject_id == boundary_id
            ):
                return
        self._persist(
            state,
            "goal_audit_boundary_resolved",
            {
                "audit_boundary_id": boundary_id,
                "audit_id": audit.audit_id,
                "verdict": audit.verdict.value,
                "boundary_kind": str(pending.get("boundary_kind") or ""),
                "authorizes_new_action": True,
            },
            subject_id=boundary_id,
        )

    def _resolve_protocol_invalid_audit_boundary(
        self,
        state: Any,
        pending: Mapping[str, Any],
        error: ModelProtocolError,
    ) -> None:
        """Release one exhausted Audit gate without granting audit authority."""

        boundary_id = str(pending.get("audit_boundary_id") or "")
        boundary_kind = str(pending.get("boundary_kind") or "")
        if not boundary_id or boundary_kind not in {"action", "pre_final"}:
            raise ValueError("invalid pending Goal Audit boundary")
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if (
                event.event_type == "goal_audit_boundary_resolved"
                and event.subject_id == boundary_id
            ):
                return

        error_text = str(error)[:2000]
        if boundary_kind == "pre_final":
            decision_id = str(pending.get("decision_id") or "")
            decision_record = state.decisions.get(decision_id)
            if decision_record is None or not decision_record.accepted:
                raise ValueError("pending final Audit has no accepted decision")
            final_command = parse_model_command(decision_record.raw_output)
            if final_command.name != "final_answer":
                raise ValueError("pending final Audit decision is not final_answer")
            output = str(final_command.arguments.get("text") or "")
            self._persist(
                state,
                "goal_final_rejected",
                {
                    "audit_id": "",
                    "audit_boundary_id": boundary_id,
                    "decision_id": decision_id,
                    "verdict": "protocol_invalid",
                    "gaps": [error_text],
                    "candidate_output_sha256": hashlib.sha256(
                        output.encode("utf-8")
                    ).hexdigest(),
                    "controller_rewritten": False,
                    "step_completed": False,
                    "kernel_validated": False,
                    "at": utc_now(),
                },
            )

        self._persist(
            state,
            "goal_audit_boundary_resolved",
            {
                "audit_boundary_id": boundary_id,
                "audit_id": "",
                "verdict": "protocol_invalid",
                "boundary_kind": boundary_kind,
                "active_step_id": str(pending.get("active_step_id") or ""),
                "action_id": str(pending.get("action_id") or ""),
                "decision_id": str(pending.get("decision_id") or ""),
                "protocol_error": error_text,
                "step_completed": False,
                "kernel_validated": False,
                "completion_authority": False,
                "authorizes_new_action": True,
            },
            subject_id=boundary_id,
        )

    def _resolve_mechanically_incomplete_audit_boundary(
        self,
        state: Any,
        pending: Mapping[str, Any],
        coverage: Mapping[str, Any],
    ) -> None:
        """Release an action boundary without asking a model to prove path facts."""

        boundary_id = str(pending.get("audit_boundary_id") or "")
        if not boundary_id or str(pending.get("boundary_kind") or "") != "action":
            raise ValueError("mechanical evidence gaps apply only to action boundaries")
        if bool(coverage.get("completion_preconditions_satisfied")):
            raise ValueError("cannot reject mechanically complete step evidence")

        already_recorded = any(
            state.causal_records[event_id].event_type
            == "goal_step_evidence_gap_recorded"
            and state.causal_records[event_id].subject_id == boundary_id
            for event_id in state.causal_order
        )
        if not already_recorded:
            self._persist(
                state,
                "goal_step_evidence_gap_recorded",
                {
                    "audit_boundary_id": boundary_id,
                    **dict(coverage),
                    "authorizes_new_action": True,
                },
                subject_id=boundary_id,
            )

        already_resolved = any(
            state.causal_records[event_id].event_type
            == "goal_audit_boundary_resolved"
            and state.causal_records[event_id].subject_id == boundary_id
            for event_id in state.causal_order
        )
        if not already_resolved:
            self._persist(
                state,
                "goal_audit_boundary_resolved",
                {
                    "audit_boundary_id": boundary_id,
                    "audit_id": "",
                    "verdict": "mechanical_repair",
                    "boundary_kind": "action",
                    "active_step_id": str(coverage.get("active_step_id") or ""),
                    "active_step_revision": int(
                        coverage.get("active_step_revision", 0) or 0
                    ),
                    "action_id": str(pending.get("action_id") or ""),
                    "gaps": list(coverage.get("gaps") or ()),
                    "step_completed": False,
                    "kernel_validated": True,
                    "completion_authority": False,
                    "authorizes_new_action": True,
                },
                subject_id=boundary_id,
            )

    def _link_action_audit(
        self,
        state: Any,
        pending: Mapping[str, Any],
        audit: GoalAuditDecision,
    ) -> None:
        action_id = str(pending.get("action_id") or "")
        active_step_id = str(pending.get("active_step_id") or "")
        active_step_revision = int(pending.get("active_step_revision", 0) or 0)
        linked_step_id = audit.step_id or active_step_id
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "goal_action_plan_step_linked":
                continue
            if str(event.payload.get("action_id") or "") != action_id:
                continue
            if str(event.payload.get("step_id") or "") != linked_step_id:
                raise ValueError("accepted audit changed an action's assigned step")
            return
        if linked_step_id:
            self._persist(
                state,
                "goal_action_plan_step_linked",
                {
                    "action_id": action_id,
                    "step_id": linked_step_id,
                    "step_revision": active_step_revision,
                    "audit_id": audit.audit_id,
                    "audit_boundary_id": str(
                        pending.get("audit_boundary_id") or ""
                    ),
                    "audit_verdict": audit.verdict.value,
                    "evidence_refs": list(audit.evidence_refs),
                    "controller_completed_step": False,
                },
                subject_id=action_id,
            )

    def _issue_strong_plan_patch(
        self,
        state: Any,
        *,
        plan: RollingGoalPlan,
        audit: GoalAuditDecision | None = None,
        stage_review: GoalStageReview | None = None,
        transitions: int,
    ) -> ControllerResult | None:
        method = getattr(self.supervisor, "plan_goal_patch", None)
        if not callable(method):
            self._persist(
                state,
                "strong_planner_call_failed",
                {
                    "phase": "goal_plan",
                    "error": {
                        "type": "TypeError",
                        "message": "Strong Planner has no native goal patch method",
                    },
                    "resumable": True,
                },
            )
            return self._yield(state, "strong_planner_unavailable", transitions)
        request_materials = {
            "run_id": state.run_id,
            "immutable_request": state.goal.request,
            "goal_digest": state.goal.digest,
            "plan_revision": len(plan.patch_ids),
            "active_plan": plan.to_model_dict(),
            "latest_audit": audit.to_dict() if audit is not None else None,
            "latest_stage_review": (
                stage_review.to_dict() if stage_review is not None else None
            ),
            "workspace_manifest": self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
            "recent_action_facts": self._recent_action_facts(state),
        }
        local_validation_repair: Mapping[str, Any] | None = None
        patch: GoalPlanPatch | None = None
        semantic_repair_attempts = getattr(
            self.supervisor,
            "semantic_repair_attempts",
            1,
        )
        if (
            isinstance(semantic_repair_attempts, bool)
            or not isinstance(semantic_repair_attempts, int)
            or not 0 <= semantic_repair_attempts <= 2
        ):
            raise ValueError(
                "Strong Planner semantic_repair_attempts must be between 0 and 2"
            )
        for semantic_attempt in range(1 + semantic_repair_attempts):
            request = GoalPlanRequest(
                **request_materials,
                local_validation_repair=local_validation_repair,
            )
            rejected_patch: Mapping[str, Any] | None = None
            semantic_error: Exception | None = None
            try:
                returned = method(request)
            except ValueError as exc:
                semantic_error = exc
            except Exception as exc:
                self._persist(
                    state,
                    "strong_planner_call_failed",
                    {
                        "phase": "goal_plan",
                        "error": {
                            "type": type(exc).__name__,
                            "message": str(exc)[:2000],
                        },
                        "resumable": True,
                    },
                )
                return self._yield(
                    state, "strong_planner_unavailable", transitions
                )
            else:
                try:
                    if not isinstance(returned, GoalPlanPatch):
                        raise TypeError(
                            "Strong Planner returned an invalid Goal PlanPatch"
                        )
                    patch = GoalPlanPatch.from_dict(returned.to_dict())
                    rejected_patch = patch.to_dict()
                    # Validate against an isolated candidate. A rejected repair
                    # must not contaminate the base used by the bounded semantic
                    # retry in this same call.
                    candidate_plan = deepcopy(plan)
                    candidate_plan.apply_goal_patch(patch)
                    self._validate_stage_repair_patch(
                        plan,
                        candidate_plan,
                        patch,
                        stage_review,
                    )
                    accept_cache = getattr(
                        self.supervisor,
                        "accept_goal_plan_cache_candidate",
                        None,
                    )
                    if callable(accept_cache):
                        accept_cache(patch.patch_id)
                except (TypeError, ValueError) as exc:
                    semantic_error = exc

            if semantic_error is None:
                break
            if patch is not None:
                discard_cache = getattr(
                    self.supervisor,
                    "discard_goal_plan_cache_candidate",
                    None,
                )
                if callable(discard_cache):
                    discard_cache(patch.patch_id)
            repair_scheduled = semantic_attempt < semantic_repair_attempts
            error_text = (
                f"{type(semantic_error).__name__}: {semantic_error}"
            )[:2000]
            self._persist(
                state,
                "strong_planner_patch_rejected",
                {
                    "phase": "goal_plan",
                    "attempt": semantic_attempt + 1,
                    "configured_semantic_repair_attempts": (
                        semantic_repair_attempts
                    ),
                    "error": {
                        "type": type(semantic_error).__name__,
                        "message": str(semantic_error)[:2000],
                    },
                    "rejected_patch": (
                        dict(rejected_patch) if rejected_patch is not None else None
                    ),
                    "repair_scheduled": repair_scheduled,
                    "resumable": True,
                },
            )
            if not repair_scheduled:
                return self._yield(
                    state, "strong_planner_semantic_invalid", transitions
                )
            local_validation_repair = {
                "attempt": 1,
                "previous_response_rejected": True,
                "error": error_text,
                "instruction": (
                    "Return one fresh complete GoalPlanPatch that satisfies the "
                    "current active_plan and the exact local invariant."
                ),
            }
            if rejected_patch is not None:
                local_validation_repair["rejected_patch"] = dict(rejected_patch)

        if patch is None:
            raise RuntimeError("Goal Planner semantic repair produced no patch")
        self._persist(
            state,
            "goal_plan_patch_committed",
            {
                "patch_id": patch.patch_id,
                "patch": patch.to_dict(),
                "plan_revision": patch.base_revision + 1,
                "request_digest": state.goal.digest,
                "supervisor": supervisor_identity(self.supervisor),
                "planner_only": True,
                "rwkv_action_authority": True,
                "replaced_step_ids": [item.step_id for item in patch.replace_steps],
                "discarded_step_ids": list(patch.discard_step_ids),
                "source_audit_id": audit.audit_id if audit is not None else "",
                "source_stage_review_id": (
                    stage_review.review_id if stage_review is not None else ""
                ),
            },
            subject_id=patch.patch_id,
        )
        return None

    @staticmethod
    def _validate_stage_repair_patch(
        prior_plan: RollingGoalPlan,
        candidate_plan: RollingGoalPlan,
        patch: GoalPlanPatch,
        stage_review: GoalStageReview | None,
    ) -> None:
        """Require a stage repair to change the next executable work."""

        if (
            stage_review is None
            or stage_review.verdict is not GoalStageReviewVerdict.REPAIR
        ):
            return
        prior_frontier_ids = {step.step_id for step in prior_plan.frontier}
        if not prior_frontier_ids:
            # A repair after the final planned stage necessarily adds new work.
            if not candidate_plan.frontier:
                raise ValueError(
                    "Goal stage repair must add executable repair work"
                )
            return
        changed_frontier_ids = {
            step.step_id for step in patch.replace_steps
        } | set(patch.discard_step_ids)
        if prior_frontier_ids.isdisjoint(changed_frontier_ids):
            raise ValueError(
                "Goal stage repair must replace or discard at least one currently "
                "open frontier step; appending only later work does not repair the "
                "rejected stage boundary"
            )

    @staticmethod
    def _pending_stage_repair_feedback(
        state: Any,
    ) -> GoalStageReview | None:
        """Replay a Stage Checker repair not yet linked to a Planner patch."""

        repaired_stage_review_ids: set[str] = set()
        candidates: list[tuple[int, GoalStageReview]] = []
        for sequence, event_id in enumerate(state.causal_order):
            event = state.causal_records[event_id]
            if event.event_type == "goal_plan_patch_committed":
                review_id = str(
                    event.payload.get("source_stage_review_id") or ""
                )
                if review_id:
                    repaired_stage_review_ids.add(review_id)
            elif event.event_type == "goal_stage_review_committed":
                raw = event.payload.get("review")
                if isinstance(raw, Mapping):
                    review = GoalStageReview.from_dict(raw)
                    if review.verdict is GoalStageReviewVerdict.REPAIR:
                        candidates.append((sequence, review))
        for _sequence, review in reversed(candidates):
            if review.review_id not in repaired_stage_review_ids:
                return review
        return None

    @staticmethod
    def _reviewed_stage_boundary_keys(state: Any) -> frozenset[str]:
        return frozenset(
            str(event.payload.get("stage_boundary_key") or "")
            for event_id in state.causal_order
            if (event := state.causal_records[event_id]).event_type
            == "goal_stage_review_committed"
        )

    def _next_unreviewed_completed_stage(
        self,
        state: Any,
        plan: RollingGoalPlan,
    ) -> tuple[int, str] | None:
        reviewed = self._reviewed_stage_boundary_keys(state)
        for stage in plan.completed_stages:
            key = plan.stage_boundary_key(stage)
            if key not in reviewed:
                return stage, key
        return None

    def _issue_strong_stage_review(
        self,
        state: Any,
        *,
        plan: RollingGoalPlan,
        stage: int,
        stage_boundary_key: str,
        transitions: int,
    ) -> GoalStageReview | ControllerResult:
        method = getattr(self.supervisor, "review_goal_stage", None)
        if not callable(method):
            self._persist(
                state,
                "strong_stage_checker_call_failed",
                {
                    "phase": "goal_stage_review",
                    "stage": stage,
                    "error": {
                        "type": "TypeError",
                        "message": "Strong model has no native stage review method",
                    },
                    "resumable": True,
                },
            )
            return self._yield(state, "strong_stage_checker_unavailable", transitions)
        steps = plan.stage_steps(stage)
        stage_evidence_refs = tuple(
            dict.fromkeys(
                ref
                for step in steps
                for ref in plan.completed_evidence[step.step_id]
            )
        )
        request = GoalStageReviewRequest(
            run_id=state.run_id,
            immutable_request=state.goal.request,
            goal_digest=state.goal.digest,
            stage=stage,
            stage_steps=tuple(
                {
                    **{
                        key: item
                        for key, item in step.to_dict().items()
                        if key != "stage"
                    },
                    "step_revision": plan.step_revisions.get(step.step_id, 1),
                    "accepted_evidence_refs": list(
                        plan.completed_evidence[step.step_id]
                    ),
                }
                for step in steps
            ),
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
            # A stage checker receives only the Harness records accepted for
            # this stage. Unrelated history increases cost and can make a small
            # stage look responsible for downstream work.
            recent_action_facts=self._recent_action_facts(
                state,
                action_ids=stage_evidence_refs,
                max_actions=8,
                result_limit=6000,
            ),
        )
        try:
            returned = method(request)
            if not isinstance(returned, GoalStageReview):
                raise TypeError("Strong model returned an invalid Goal stage review")
            review = GoalStageReview(
                review_id=returned.review_id,
                stage=returned.stage,
                verdict=returned.verdict,
                reviewed_step_ids=returned.reviewed_step_ids,
                evidence_refs=returned.evidence_refs,
                gaps=returned.gaps,
                reason=returned.reason,
            )
            expected_step_ids = tuple(step.step_id for step in steps)
            expected_refs = stage_evidence_refs
            if review.stage != stage:
                raise ValueError("Strong stage review changed the bound stage")
            if review.reviewed_step_ids != expected_step_ids:
                raise ValueError("Strong stage review changed the bound step set")
            if review.evidence_refs != expected_refs:
                raise ValueError("Strong stage review changed the bound evidence set")
        except Exception as exc:
            self._persist(
                state,
                "strong_stage_checker_call_failed",
                {
                    "phase": "goal_stage_review",
                    "stage": stage,
                    "stage_boundary_key": stage_boundary_key,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc)[:2000],
                    },
                    "resumable": True,
                },
            )
            return self._yield(state, "strong_stage_checker_unavailable", transitions)
        self._persist(
            state,
            "goal_stage_review_committed",
            {
                "stage": stage,
                "stage_boundary_key": stage_boundary_key,
                "review": review.to_dict(),
                "supervisor": supervisor_identity(self.supervisor),
                "read_only": True,
                "authorizes_tool_action": False,
                "controller_bound_fields": [
                    "review_id",
                    "stage",
                    "reviewed_step_ids",
                    "evidence_refs",
                    "schema_version",
                ],
            },
            subject_id=review.review_id,
        )
        return review

    def run(self, run_id: str) -> ControllerResult:
        with self.store.controller_lease(run_id):
            state = self.store.load(run_id)
            if state.status is RunStatus.COMPLETED:
                return ControllerResult(state, state.final_output, 0)
            if not state.goal.verify_digest():
                raise ValueError("literal request digest mismatch")
            stored_architecture = next(
                (
                    str(state.causal_records[event_id].payload.get("architecture") or "")
                    for event_id in reversed(state.causal_order)
                    if state.causal_records[event_id].event_type == "run_started"
                ),
                "",
            )
            if (
                stored_architecture
                and stored_architecture != STATEFUL_GOAL_LOOP_ARCHITECTURE
            ):
                raise ValueError(
                    "stored Goal run architecture does not match this runtime: "
                    f"{stored_architecture!r} != "
                    f"{STATEFUL_GOAL_LOOP_ARCHITECTURE!r}"
                )

            self._recover_active_action(state)
            if state.status is not RunStatus.RUNNING:
                manual_blocked_resume = state.status is RunStatus.BLOCKED
                prior_boundary = next(
                    (
                        event_id
                        for event_id in reversed(state.causal_order)
                        if state.causal_records[event_id].event_type
                        in {
                            "run_completed",
                            "run_failed",
                            "run_interrupted",
                            "run_blocked",
                            "run_yielded",
                        }
                    ),
                    "",
                )
                self._persist(
                    state,
                    "run_started",
                    {
                        "architecture": STATEFUL_GOAL_LOOP_ARCHITECTURE,
                        "persistent_executor_state_count": 0,
                        "executor_state_scope": "one_selected_action",
                        "executor_facts_source": "bounded_causal_projection",
                        "selector_state_isolated": True,
                        "selector_state_count_per_step": 3,
                        "selector_menu_order_ids": [
                            "canonical",
                            "rotate_8",
                            "rotate_17",
                        ],
                        "selector_vote_rule": "three_menu_order_vote_v1",
                        "selector_authority": "exclusive_tool_intent_and_selection",
                        "executor_reselects_tool": False,
                        "selector_model": self.model.tool_selector.settings.model,
                        "planner": supervisor_identity(self.supervisor),
                        "planner_contract": GOAL_PLAN_PATCH_SCHEMA_VERSION,
                        "step_auditor_model": (
                            self.model.step_auditor_session.model_name
                        ),
                        "finalizer_model": self.model.finalizer_session.model_name,
                        "final_auditor_model": (
                            self.model.final_auditor_session.model_name
                        ),
                        "auditor_state_source": "clean_boundary_bootstrap",
                        "auditor_inherits_executor_state": False,
                        "audit_wkv_merge": False,
                        "strong_model_dependency": True,
                        "strong_model_role": "planner_and_read_only_stage_checker",
                        "plan_stage_format": "nested_stages_with_peer_steps",
                        "stage_barriers": True,
                        "parallel_mutations": False,
                        "resumed": bool(prior_boundary),
                        "protocol_rejection_budget_reset": manual_blocked_resume,
                        "supersedes_terminal_event_id": prior_boundary,
                    },
                )

            transitions = 0
            transport_failures = 0

            # A crash may leave a finished Harness action not yet observed by
            # the recurrent action State.  It must cross the same audit boundary
            # as a normally completed transaction.
            pending_observation = self._first_unappended_action_observation(state)

            while transitions < self.max_transitions:
                if (
                    self._consecutive_action_protocol_rejections(state)
                    >= self._MAX_PROTOCOL_REJECTIONS
                ):
                    return self._block(
                        state,
                        "protocol_rejection_budget_exhausted",
                        transitions,
                    )
                try:
                    plan = rolling_goal_plan(state)
                    if not plan.steps:
                        boundary = self._issue_strong_plan_patch(
                            state,
                            plan=plan,
                            transitions=transitions,
                        )
                        if boundary is not None:
                            return boundary
                        transitions += 1
                        plan = rolling_goal_plan(state)

                    pending_audit = self._pending_audit_boundary(state)
                    if pending_audit is not None:
                        if str(pending_audit.get("boundary_kind") or "") == "action":
                            coverage = self._step_mechanical_evidence_coverage(
                                state,
                                str(pending_audit.get("active_step_id") or ""),
                                int(
                                    pending_audit.get("active_step_revision", 0) or 0
                                ),
                            )
                            if not bool(
                                coverage.get("completion_preconditions_satisfied")
                            ):
                                self._resolve_mechanically_incomplete_audit_boundary(
                                    state,
                                    pending_audit,
                                    coverage,
                                )
                                transitions += 1
                                pending_observation = None
                                continue
                        audit = self._run_pending_audit_boundary(state, pending_audit)
                        transitions += 1
                        if str(pending_audit.get("boundary_kind") or "") == "action":
                            self._link_action_audit(state, pending_audit, audit)
                            self._resolve_audit_boundary(state, pending_audit, audit)
                            pending_observation = None
                            continue

                        if str(pending_audit.get("boundary_kind") or "") != "pre_final":
                            raise ValueError("unsupported durable Goal Audit boundary kind")
                        decision_id = str(pending_audit.get("decision_id") or "")
                        decision_record = state.decisions.get(decision_id)
                        if decision_record is None or not decision_record.accepted:
                            raise ValueError("pending final Audit has no accepted decision")
                        final_command = parse_model_command(decision_record.raw_output)
                        if final_command.name != "final_answer":
                            raise ValueError("pending final Audit decision is not final_answer")
                        output = str(final_command.arguments.get("text") or "")
                        if audit.verdict is not GoalAuditVerdict.READY_FOR_FINAL:
                            self._persist(
                                state,
                                "goal_final_rejected",
                                {
                                    "audit_id": audit.audit_id,
                                    "audit_boundary_id": str(
                                        pending_audit.get("audit_boundary_id") or ""
                                    ),
                                    "decision_id": decision_id,
                                    "verdict": audit.verdict.value,
                                    "gaps": list(audit.gaps),
                                    "candidate_output_sha256": hashlib.sha256(
                                        output.encode("utf-8")
                                    ).hexdigest(),
                                    "controller_rewritten": False,
                                    "at": utc_now(),
                                },
                            )
                            self._resolve_audit_boundary(state, pending_audit, audit)
                            continue
                        self._resolve_audit_boundary(state, pending_audit, audit)
                        state.final_output = output
                        state.final_decision_id = decision_id
                        state.status = RunStatus.COMPLETED
                        self._persist(
                            state,
                            "run_completed",
                            {
                                "decision_id": decision_id,
                                "request_id": decision_record.request_id,
                                "audit_id": audit.audit_id,
                                "audit_boundary_id": str(
                                    pending_audit.get("audit_boundary_id") or ""
                                ),
                                "final_output_sha256": hashlib.sha256(
                                    output.encode("utf-8")
                                ).hexdigest(),
                                "output_source": "rwkv_explicit_final_answer_text",
                                "controller_rewritten": False,
                                "rwkv_audit_accepted": True,
                                "final_output": output,
                            },
                        )
                        return ControllerResult(state, output, transitions)

                    if pending_observation is not None:
                        recovered_action_id = str(
                            pending_observation.payload.get("action_id") or ""
                        )
                        recovered_action = state.actions.get(recovered_action_id)
                        if recovered_action is None:
                            raise ValueError("recovered action observation has no action")
                        bindings = goal_step_action_bindings(state)
                        recovered_binding = bindings.get(recovered_action_id)
                        recovered_step_id = (
                            recovered_binding[0] if recovered_binding is not None else ""
                        )
                        recovered_step_revision = (
                            recovered_binding[1] if recovered_binding is not None else 0
                        )
                        if not recovered_step_id:
                            recovered_step_id = (
                                plan.frontier[0].step_id if plan.frontier else ""
                            )
                            recovered_step_revision = plan.step_revisions.get(
                                recovered_step_id, 1
                            )
                            self._assign_action_to_step(
                                state,
                                action_id=recovered_action_id,
                                step_id=recovered_step_id,
                                step_revision=recovered_step_revision,
                                patch_ids=plan.patch_ids,
                            )
                        self._open_audit_boundary(
                            state,
                            boundary_kind="action",
                            boundary=(
                                "tool_failure"
                                if recovered_action.status is not ActionStatus.SUCCEEDED
                                else "observation_complete"
                            ),
                            active_step_id=recovered_step_id,
                            active_step_revision=recovered_step_revision,
                            action_id=recovered_action_id,
                            evidence_refs=self._step_audit_evidence_refs(
                                state,
                                recovered_step_id,
                                recovered_step_revision,
                            ),
                        )
                        pending_observation = None
                        continue

                    pending_stage_repair = self._pending_stage_repair_feedback(state)
                    if pending_stage_repair is not None:
                        boundary = self._issue_strong_plan_patch(
                            state,
                            plan=plan,
                            stage_review=pending_stage_repair,
                            transitions=transitions,
                        )
                        if boundary is not None:
                            return boundary
                        transitions += 1
                        continue

                    stage_boundary = self._next_unreviewed_completed_stage(state, plan)
                    if stage_boundary is not None:
                        stage, stage_boundary_key = stage_boundary
                        review_or_boundary = self._issue_strong_stage_review(
                            state,
                            plan=plan,
                            stage=stage,
                            stage_boundary_key=stage_boundary_key,
                            transitions=transitions,
                        )
                        if isinstance(review_or_boundary, ControllerResult):
                            return review_or_boundary
                        transitions += 1
                        if (
                            review_or_boundary.verdict
                            is GoalStageReviewVerdict.REPAIR
                        ):
                            boundary = self._issue_strong_plan_patch(
                                state,
                                plan=plan,
                                stage_review=review_or_boundary,
                                transitions=transitions,
                            )
                            if boundary is not None:
                                return boundary
                            transitions += 1
                        continue

                    if not plan.frontier and not plan.complete:
                        raise ValueError("acyclic rolling plan has no executable frontier")

                    active_step_id = ""
                    active_step_revision = 0
                    current_requirement = state.goal.request
                    selector_stage_context: SelectorStageContext | None = None
                    eligible_operations: tuple[str, ...] | None
                    if plan.complete:
                        decision = self.model.finalize_goal_answer(
                            state,
                            self._persist_callback,
                        )
                    else:
                        frontier = plan.frontier[0]
                        active_step_id = frontier.step_id
                        active_step_revision = plan.step_revisions.get(
                            active_step_id, 1
                        )
                        current_requirement = frontier.objective
                        mechanical_evidence = self._step_mechanical_evidence_coverage(
                            state,
                            active_step_id,
                            active_step_revision,
                        )
                        guidance = ModelEvent(
                            event_type="goal_frontier_assignment",
                            event_id=f"EV-GOAL-FRONTIER-{uuid4().hex[:16]}",
                            scope_id=self.model.ACTION_LANE_ID,
                            payload={
                                "active_step": {
                                    **frontier.to_dict(),
                                    "step_revision": active_step_revision,
                                },
                                "mechanical_evidence": mechanical_evidence,
                                "instruction": (
                                    "Execute only this one active step. Do not audit, replan, "
                                    "judge completion, or consider another plan step."
                                ),
                            },
                        )
                        eligible_operations = self._goal_step_operations(
                            state,
                            frontier,
                            mechanical_evidence=mechanical_evidence,
                        )
                        selector_stage_context = goal_frontier_selector_context(
                            state,
                            {
                                **frontier.to_dict(),
                                "step_revision": active_step_revision,
                                "effective_phase": (
                                    "observe"
                                    if frontier.phase != "observe"
                                    and mechanical_evidence["missing_read_roots"]
                                    else frontier.phase
                                ),
                            },
                            eligible_labels=eligible_operations,
                        )
                        executor_retry = self._pending_executor_protocol_retry(state)
                        decision = self.model.next_command(
                            state,
                            self._persist_callback,
                            event=(executor_retry or guidance),
                            eligible_operations=eligible_operations,
                            selector_stage_context=(
                                None if executor_retry is not None
                                else selector_stage_context
                            ),
                            current_requirement=current_requirement,
                            executor_fact_action_ids=(
                                self._step_executor_fact_action_ids(
                                    state,
                                    active_step_id,
                                    active_step_revision,
                                )
                            ),
                        )
                    transport_failures = 0

                    if decision.command.name == "final_answer":
                        final_evidence_refs = tuple(
                            sorted(
                                set(
                                    ref
                                    for refs in plan.completed_evidence.values()
                                    for ref in refs
                                )
                            )
                        )
                        self._open_audit_boundary(
                            state,
                            boundary_kind="pre_final",
                            boundary="pre_final",
                            decision_id=decision.decision.decision_id,
                            evidence_refs=final_evidence_refs,
                            final_candidate=True,
                        )
                        continue

                    action = self._execute_decision(state, decision)
                    transitions += 1
                    self._assign_action_to_step(
                        state,
                        action_id=action.action_id,
                        step_id=active_step_id,
                        step_revision=active_step_revision,
                        patch_ids=plan.patch_ids,
                    )
                    if (
                        action.failure_key
                        and state.failure_budgets.get(action.failure_key, 0)
                        >= self._MAX_IDENTICAL_FAILURES
                    ):
                        return self._block(
                            state,
                            "identical_failure_budget_exhausted",
                            transitions,
                        )
                    definition = self.harness.definition(action.action_type)
                    mutation = (
                        definition.side_effect
                        and definition.side_effect_class == "workspace_mutation"
                    )
                    repeated = state.observation_counts.get(
                        action.observation_fingerprint, 0
                    )
                    if (
                        action.status is ActionStatus.SUCCEEDED
                        and definition.read_only
                        and not definition.side_effect
                        and bool(action.workspace_digest_before)
                        and action.workspace_digest_before
                        == action.workspace_digest_after
                        and repeated
                        >= self._MAX_IDENTICAL_ZERO_PROGRESS_SUCCESSES
                    ):
                        return self._block(
                            state,
                            "identical_success_budget_exhausted",
                            transitions,
                        )
                    boundary = (
                        "tool_failure"
                        if action.status is not ActionStatus.SUCCEEDED
                        else "stagnation"
                        if repeated >= self._MAX_IDENTICAL_ZERO_PROGRESS_SUCCESSES
                        else "mutation_transaction_complete"
                        if mutation
                        else "observation_complete"
                    )
                    self._open_audit_boundary(
                        state,
                        boundary_kind="action",
                        boundary=boundary,
                        active_step_id=active_step_id,
                        active_step_revision=active_step_revision,
                        action_id=action.action_id,
                        evidence_refs=self._step_audit_evidence_refs(
                            state,
                            active_step_id,
                            active_step_revision,
                        ),
                    )
                    continue

                except RWKVRuntimeError as exc:
                    transport_failures += 1
                    self._record_transport_failure(state, exc, transport_failures)
                    if transport_failures >= self._MAX_TRANSPORT_FAILURES:
                        return self._yield(
                            state,
                            "model_transport_unavailable",
                            transitions,
                        )
                    self._transport_backoff(transport_failures)
                except ModelProtocolError as exc:
                    transitions += 1
                    pending_protocol_audit = self._pending_audit_boundary(state)
                    if (
                        pending_protocol_audit is None
                        and exc.selected_operation == NETWORK_ABSTAIN_LABEL
                    ):
                        return self._block(state, "selector_abstained", transitions)
                    self._persist(
                        state,
                        "protocol_rejection_recorded",
                        {
                            "decision_id": exc.decision_id,
                            "request_id": exc.request_id,
                            "selection_id": exc.selection_id,
                            "selected_operation": exc.selected_operation,
                            "rejected_arguments": dict(exc.rejected_arguments),
                            "selected_operation_schema": dict(
                                exc.selected_operation_schema
                            ),
                            "schema_already_disclosed": (
                                exc.schema_already_disclosed
                            ),
                            "error": str(exc)[:2000],
                            "error_record": {
                                "type": "ModelProtocolError",
                                "message": str(exc)[:2000],
                                "at": utc_now(),
                            },
                            "protocol_scope": (
                                "goal_audit"
                                if pending_protocol_audit is not None
                                else "action"
                            ),
                            "audit_boundary_id": (
                                str(
                                    pending_protocol_audit.get(
                                        "audit_boundary_id"
                                    )
                                    or ""
                                )
                                if pending_protocol_audit is not None
                                else ""
                            ),
                            "rejection_count": state.protocol_rejections + 1,
                            "action_executed": False,
                        },
                    )
                    if pending_protocol_audit is not None:
                        self._resolve_protocol_invalid_audit_boundary(
                            state,
                            pending_protocol_audit,
                            exc,
                        )
                        pending_observation = None
                        continue
                    if (
                        self._consecutive_action_protocol_rejections(state)
                        >= self._MAX_PROTOCOL_REJECTIONS
                    ):
                        return self._block(
                            state,
                            "protocol_rejection_budget_exhausted",
                            transitions,
                        )

            return self._yield(state, "controller_slice_exhausted", transitions)

    def _block(
        self,
        state: Any,
        reason: str,
        transitions: int,
    ) -> ControllerResult:
        """Stop automatic Goal continuation after a durable hard budget."""

        self._persist(
            state,
            "run_blocked",
            {
                "reason": str(reason),
                "decision_id": "",
                "output_source": "none",
                "controller_rewritten": False,
                "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                "final_output": "",
                "resumable": True,
                "termination_permitted": False,
                "continuation": "explicit_manual_resume_only",
                "at": utc_now(),
            },
        )
        return ControllerResult(state, "", transitions)

    def _yield(
        self,
        state: Any,
        reason: str,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": str(reason),
                "decision_id": "",
                "output_source": "none",
                "controller_rewritten": False,
                "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                "final_output": "",
                "resumable": True,
                "at": utc_now(),
            },
        )
        return ControllerResult(state, "", transitions)


__all__ = ["STATEFUL_GOAL_LOOP_ARCHITECTURE", "StatefulGoalLoopController"]
