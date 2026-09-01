"""Single-State RWKV Goal loop with an evidence-bound RWKV audit fork."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping
from uuid import uuid4

from rwkv_lh.controller import ControllerResult, LongHorizonController
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
    goal_step_action_bindings,
    rolling_goal_plan,
)
from rwkv_lh.model import ModelProtocolError
from rwkv_lh.model_io import parse_model_command
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.schema import ActionStatus, ModelEvent, RunStatus, utc_now
from rwkv_lh.supervisor import supervisor_identity


STATEFUL_GOAL_LOOP_ARCHITECTURE = "rwkv-stateful-goal-loop.v2"


class StatefulGoalLoopController(LongHorizonController):
    """Strong-plan, single-State RWKV execute, RWKV-audit Goal loop."""

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

    @staticmethod
    def _recent_action_facts(state: Any) -> tuple[Mapping[str, Any], ...]:
        """Expose bounded Harness facts to Planner without Executor text."""

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

        actions = sorted(state.actions.values(), key=lambda item: item.sequence)[-12:]
        projected: list[Mapping[str, Any]] = []
        for action in actions:
            arguments_summary, arguments_truncated = summary(action.arguments, 1200)
            result_summary, result_truncated = summary(action.result, 2400)
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
        # One action id per transaction preserves provenance for multi-file steps
        # within the frozen Audit protocol's eight-reference ceiling.  Remaining
        # slots expose exact artifact/revision facts without dropping an action.
        refs = [action.action_id for action in actions]
        if len(refs) > 8:
            refs = refs[-8:]
        for action in reversed(actions):
            extras = [*action.artifact_refs]
            extras.extend(
                revision.revision_id
                for revisions in state.artifact_revisions.values()
                for revision in revisions
                if revision.action_id == action.action_id
            )
            for ref in extras:
                if ref not in refs and len(refs) < 8:
                    refs.append(ref)
        return tuple(refs)

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
        for semantic_attempt in range(2):
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
                    # Validate the complete replacement/discard result before it
                    # becomes causal authority. The reconstructed view is mutated
                    # only after all candidate invariants pass.
                    plan.apply_goal_patch(patch)
                except (TypeError, ValueError) as exc:
                    semantic_error = exc

            if semantic_error is None:
                break
            repair_scheduled = semantic_attempt == 0
            error_text = (
                f"{type(semantic_error).__name__}: {semantic_error}"
            )[:2000]
            self._persist(
                state,
                "strong_planner_patch_rejected",
                {
                    "phase": "goal_plan",
                    "attempt": semantic_attempt + 1,
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
    def _pending_plan_repair_feedback(
        state: Any,
    ) -> tuple[GoalAuditDecision | None, GoalStageReview | None]:
        """Replay repair feedback that has not yet produced a committed patch."""

        repaired_audit_ids: set[str] = set()
        repaired_stage_review_ids: set[str] = set()
        candidates: list[
            tuple[int, GoalAuditDecision | None, GoalStageReview | None]
        ] = []
        for sequence, event_id in enumerate(state.causal_order):
            event = state.causal_records[event_id]
            if event.event_type == "goal_plan_patch_committed":
                audit_id = str(event.payload.get("source_audit_id") or "")
                review_id = str(
                    event.payload.get("source_stage_review_id") or ""
                )
                if audit_id:
                    repaired_audit_ids.add(audit_id)
                if review_id:
                    repaired_stage_review_ids.add(review_id)
            elif event.event_type == "goal_audit_accepted":
                raw = event.payload.get("audit")
                if isinstance(raw, Mapping):
                    audit = GoalAuditDecision.from_dict(raw)
                    if audit.verdict is GoalAuditVerdict.REPAIR:
                        candidates.append((sequence, audit, None))
            elif event.event_type == "goal_stage_review_committed":
                raw = event.payload.get("review")
                if isinstance(raw, Mapping):
                    review = GoalStageReview.from_dict(raw)
                    if review.verdict is GoalStageReviewVerdict.REPAIR:
                        candidates.append((sequence, None, review))
        for _sequence, audit, review in reversed(candidates):
            if audit is not None and audit.audit_id not in repaired_audit_ids:
                return audit, None
            if (
                review is not None
                and review.review_id not in repaired_stage_review_ids
            ):
                return None, review
        return None, None

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
            recent_action_facts=self._recent_action_facts(state),
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
            expected_refs = tuple(
                dict.fromkeys(
                    ref
                    for step in steps
                    for ref in plan.completed_evidence[step.step_id]
                )
            )
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

            self._recover_active_action(state)
            if state.status is not RunStatus.RUNNING:
                prior_boundary = next(
                    (
                        event_id
                        for event_id in reversed(state.causal_order)
                        if state.causal_records[event_id].event_type
                        in {"run_completed", "run_failed", "run_interrupted", "run_yielded"}
                    ),
                    "",
                )
                self._persist(
                    state,
                    "run_started",
                    {
                        "architecture": STATEFUL_GOAL_LOOP_ARCHITECTURE,
                        "persistent_executor_state_count": 1,
                        "selector_state_isolated": True,
                        "selector_authority": "exclusive_tool_intent_and_selection",
                        "executor_reselects_tool": False,
                        "selector_model": self.model.tool_selector.settings.model,
                        "planner": supervisor_identity(self.supervisor),
                        "planner_contract": GOAL_PLAN_PATCH_SCHEMA_VERSION,
                        "auditor_model": self.model.auditor_session.model_name,
                        "auditor_state_source": "clean_boundary_bootstrap",
                        "auditor_inherits_executor_state": False,
                        "audit_wkv_merge": False,
                        "strong_model_dependency": True,
                        "strong_model_role": "planner_and_read_only_stage_checker",
                        "plan_stage_format": "nested_stages_with_peer_steps",
                        "stage_barriers": True,
                        "parallel_mutations": False,
                        "resumed": bool(prior_boundary),
                        "supersedes_terminal_event_id": prior_boundary,
                    },
                )

            transitions = 0
            transport_failures = 0
            protocol_failures = 0

            # A crash may leave a finished Harness action not yet observed by
            # the recurrent action State.  It must cross the same audit boundary
            # as a normally completed transaction.
            pending_observation = self._first_unappended_action_observation(state)

            while transitions < self.max_transitions:
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
                        audit = self._run_pending_audit_boundary(state, pending_audit)
                        transitions += 1
                        if str(pending_audit.get("boundary_kind") or "") == "action":
                            self._link_action_audit(state, pending_audit, audit)
                            self._resolve_audit_boundary(state, pending_audit, audit)
                            pending_observation = None
                            protocol_failures = 0
                            plan = rolling_goal_plan(state)
                            if (
                                audit.verdict is GoalAuditVerdict.REPAIR
                                and not plan.complete
                            ):
                                boundary = self._issue_strong_plan_patch(
                                    state,
                                    plan=plan,
                                    audit=audit,
                                    transitions=transitions,
                                )
                                if boundary is not None:
                                    return boundary
                                transitions += 1
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
                            protocol_failures = 0
                            continue
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
                                "recovered_tool_failure"
                                if recovered_action.status is not ActionStatus.SUCCEEDED
                                else "recovered_transaction_complete"
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

                    pending_audit_repair, pending_stage_repair = (
                        self._pending_plan_repair_feedback(state)
                    )
                    if (
                        pending_audit_repair is not None
                        or pending_stage_repair is not None
                    ):
                        boundary = self._issue_strong_plan_patch(
                            state,
                            plan=plan,
                            audit=pending_audit_repair,
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
                        guidance = ModelEvent(
                            event_type="goal_frontier_complete",
                            event_id=f"EV-GOAL-FRONTIER-{uuid4().hex[:16]}",
                            scope_id=self.model.ACTION_LANE_ID,
                            payload={
                                "completed_step_ids": sorted(plan.completed_step_ids),
                                "instruction": (
                                    "The rolling plan is evidence-complete. Return one "
                                    "final_answer candidate grounded in committed facts."
                                ),
                            },
                        )
                        eligible_operations = ("final_answer",)
                    else:
                        frontier = plan.frontier[0]
                        active_step_id = frontier.step_id
                        active_step_revision = plan.step_revisions.get(
                            active_step_id, 1
                        )
                        current_requirement = frontier.objective
                        guidance = ModelEvent(
                            event_type="goal_frontier_assignment",
                            event_id=f"EV-GOAL-FRONTIER-{uuid4().hex[:16]}",
                            scope_id=self.model.ACTION_LANE_ID,
                            payload={
                                "active_step": {
                                    **frontier.to_dict(),
                                    "step_revision": active_step_revision,
                                },
                                "instruction": (
                                    "Execute only this one active step. Do not audit, replan, "
                                    "judge completion, or consider another plan step."
                                ),
                            },
                        )
                        eligible_operations = (
                            tuple(frontier.allowed_operations)
                            if frontier.allowed_operations
                            else None
                        )
                        selector_stage_context = goal_frontier_selector_context(
                            state,
                            {
                                **frontier.to_dict(),
                                "step_revision": active_step_revision,
                            },
                        )
                    decision = self.model.next_command(
                        state,
                        self._persist_callback,
                        event=guidance,
                        eligible_operations=eligible_operations,
                        selector_stage_context=selector_stage_context,
                        current_requirement=current_requirement,
                    )
                    transport_failures = 0
                    protocol_failures = 0

                    if decision.command.name == "final_answer":
                        final_evidence_refs = tuple(
                            dict.fromkeys(
                                ref
                                for refs in plan.completed_evidence.values()
                                for ref in refs
                            )
                        )[-8:]
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
                    definition = self.harness.definition(action.action_type)
                    mutation = (
                        definition.side_effect
                        and definition.side_effect_class == "workspace_mutation"
                    )
                    repeated = state.observation_counts.get(
                        action.observation_fingerprint, 0
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
                    protocol_failures += 1
                    transitions += 1
                    self._persist(
                        state,
                        "protocol_rejection_recorded",
                        {
                            "decision_id": exc.decision_id,
                            "request_id": exc.request_id,
                            "selection_id": exc.selection_id,
                            "selected_operation": exc.selected_operation,
                            "rejected_arguments": dict(exc.rejected_arguments),
                            "error": str(exc)[:2000],
                            "error_record": {
                                "type": "ModelProtocolError",
                                "message": str(exc)[:2000],
                                "at": utc_now(),
                            },
                            "rejection_count": state.protocol_rejections + 1,
                            "action_executed": False,
                        },
                    )
                    if protocol_failures >= self._MAX_PROTOCOL_REJECTIONS:
                        return self._yield(
                            state,
                            "protocol_rejection_budget_exhausted",
                            transitions,
                        )

            return self._yield(state, "controller_slice_exhausted", transitions)

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
