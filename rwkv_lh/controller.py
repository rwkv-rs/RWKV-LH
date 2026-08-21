"""Persistent RWKV executor with an optional bounded supervisor boundary."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4

from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.model import ActionDecision, LongHorizonModel, ModelProtocolError, PersistCallback
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.model_io import canonical_digest, parse_model_command, validate_final_answer
from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    ArtifactRecord,
    ArtifactRevision,
    CausalEventDraft,
    DecisionRecord,
    ModelEvent,
    RunState,
    RunStatus,
    TaskAction,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore, StateStore
from rwkv_lh.supervisor import (
    ReviewDisposition,
    SupervisorClient,
    SupervisorPlan,
    SupervisorPlanRequest,
    SupervisorPolicy,
    SupervisorReview,
    SupervisorReviewRequest,
    supervisor_identity,
)


@dataclass
class ControllerResult:
    state: RunState
    final_output: str
    transitions: int


class LongHorizonController:
    """Execute RWKV operations; optionally gate planning and completion externally."""

    _MAX_PROTOCOL_REJECTIONS = 12
    _MAX_IDENTICAL_FAILURES = 5
    _MAX_TERMINAL_ATTEMPTS = 6
    _MAX_TRANSPORT_FAILURES = 8
    _TRANSPORT_BACKOFF_CAP_SECONDS = 60.0

    def __init__(
        self,
        store: StateStore | None = None,
        *,
        model: LongHorizonModel | None = None,
        harness: ActionHarness | None = None,
        supervisor: SupervisorClient | None = None,
        supervisor_policy: SupervisorPolicy | None = None,
        max_transitions: int = 500,
        **_removed_options: Any,
    ) -> None:
        self.store = store or LongHorizonStore()
        self.harness = harness or ActionHarness()
        self.model = model or LongHorizonModel(harness=self.harness)
        self.supervisor = supervisor
        self.supervisor_policy = supervisor_policy or SupervisorPolicy()
        self.max_transitions = max(1, int(max_transitions))

    def run(self, run_id: str) -> ControllerResult:
        with self.store.controller_lease(run_id):
            state = self.store.load(run_id)
            if state.status == RunStatus.COMPLETED:
                return ControllerResult(state, state.final_output, 0)
            if not state.goal.verify_digest():
                raise ValueError("literal request digest mismatch")
            if self.supervisor is None and self._run_requires_supervisor(state):
                return self._missing_supervisor_configuration(state)

            transitions = 0
            self._recover_active_action(state)
            if state.status != RunStatus.RUNNING:
                state.status = RunStatus.RUNNING
                hybrid = self.supervisor is not None
                self._persist(
                    state,
                    "run_started",
                    {
                        "architecture": (
                            "strong-supervisor-rwkv-worker.v1"
                            if hybrid
                            else "single-rwkv-direct-action.v1"
                        ),
                        "online_task_graph": False,
                        "reviewer": hybrid,
                        **(
                            {"supervisor": supervisor_identity(self.supervisor)}
                            if self.supervisor is not None
                            else {}
                        ),
                    },
                )

            plan: SupervisorPlan | None = None
            pending_events: list[ModelEvent] = []
            if self.supervisor is not None:
                try:
                    plan = self._committed_supervisor_plan(state)
                    if plan is None:
                        requested = self.supervisor.create_plan(
                            self._supervisor_plan_request(state)
                        )
                        if not isinstance(requested, SupervisorPlan):
                            raise TypeError("supervisor returned an invalid plan object")
                        plan = SupervisorPlan.from_dict(requested.to_dict())
                except Exception as exc:
                    return self._supervisor_plan_failure(state, exc)
                if self._committed_supervisor_plan(state) is None:
                    self._persist(
                        state,
                        "supervisor_plan_committed",
                        {
                            "plan_id": plan.plan_id,
                            "plan": plan.to_dict(),
                            "request_digest": state.goal.digest,
                            "supervisor": supervisor_identity(self.supervisor),
                            "rwkv_action_authority": True,
                        },
                    )
                plan_event = self._supervisor_plan_event(plan)
                if plan_event.event_id not in state.model_events:
                    pending_events.append(plan_event)

                review_boundary = self._recover_supervisor_review_boundary(
                    state,
                    plan,
                )
                if isinstance(review_boundary, ControllerResult):
                    return review_boundary
                if review_boundary is not None:
                    pending_events.append(review_boundary)
                else:
                    recovered_decision = self._unreviewed_supervisor_decision(state)
                    if recovered_decision is not None:
                        wire_command = parse_model_command(recovered_decision.raw_output)
                        validate_final_answer(wire_command)
                        checkpoint = state.model_states.get(
                            recovered_decision.output_checkpoint_id
                        )
                        if checkpoint is None:
                            raise ValueError(
                                "unreviewed supervisor candidate checkpoint is missing"
                            )
                        recovered_boundary = self._review_supervisor_candidate(
                            state,
                            plan,
                            ActionDecision(
                                wire_command=wire_command,
                                command=wire_command,
                                checkpoint=checkpoint,
                                decision=recovered_decision,
                                argument_normalization={},
                            ),
                            str(wire_command.arguments["text"]),
                            0,
                        )
                        if isinstance(recovered_boundary, ControllerResult):
                            return recovered_boundary
                        pending_events.append(recovered_boundary)

            pending_action_event = self._first_unappended_action_observation(state)
            if pending_action_event is not None:
                pending_events.append(pending_action_event)
            terminal_reason = ""
            transport_failures = 0
            while transitions < self.max_transitions:
                try:
                    if len(pending_events) > 1:
                        decision = self.model.next_command(
                            state,
                            self._persist_callback,
                            events=tuple(pending_events),
                        )
                    else:
                        decision = self.model.next_command(
                            state,
                            self._persist_callback,
                            event=(pending_events[0] if pending_events else None),
                        )
                    pending_events = []
                    transport_failures = 0
                except RWKVRuntimeError as exc:
                    transport_failures += 1
                    self._record_transport_failure(state, exc, transport_failures)
                    if transport_failures >= self._MAX_TRANSPORT_FAILURES:
                        terminal_reason = "model_transport_unavailable"
                        break
                    self._transport_backoff(transport_failures)
                    continue
                except ModelProtocolError as exc:
                    transitions += 1
                    error_record = {
                        "type": "ModelProtocolError",
                        "message": str(exc)[:2000],
                        "decision_id": exc.decision_id,
                        "request_id": exc.request_id,
                        "at": utc_now(),
                    }
                    self._persist(
                        state,
                        "protocol_rejection_recorded",
                        {
                            "decision_id": exc.decision_id,
                            "request_id": exc.request_id,
                            "error": str(exc)[:2000],
                            "error_record": error_record,
                            "rejection_count": state.protocol_rejections + 1,
                            "action_executed": False,
                        },
                    )
                    if state.protocol_rejections >= self._MAX_PROTOCOL_REJECTIONS:
                        terminal_reason = "protocol_rejection_budget_exhausted"
                        break
                    pending_events = [ModelEvent(
                        event_type="protocol_rejection",
                        event_id=f"EV-REJECT-{uuid4().hex[:16]}",
                        scope_id=self.model.ACTION_LANE_ID,
                        payload={
                            "error": str(exc)[:2000],
                            "action_executed": False,
                            **(
                                {
                                    "selected_operation": exc.selected_operation,
                                    "selected_operation_schema": exc.selected_operation_schema,
                                }
                                if exc.selected_operation and exc.selected_operation_schema
                                else {}
                            ),
                            "instruction": (
                                "Return one displayed direct function call with its complete "
                                "explicit parameter object. No operation or value was inferred."
                            ),
                        },
                    )]
                    continue

                transitions += 1
                if decision.wire_command.name == "final_answer":
                    output = str(decision.wire_command.arguments["text"])
                    if self.supervisor is not None:
                        if plan is None:
                            raise RuntimeError("hybrid run has no committed supervisor plan")
                        review_boundary = self._review_supervisor_candidate(
                            state,
                            plan,
                            decision,
                            output,
                            transitions,
                        )
                        if isinstance(review_boundary, ControllerResult):
                            return review_boundary
                        pending_events = [review_boundary]
                        continue
                    state.final_output = output
                    state.final_decision_id = decision.decision.decision_id
                    state.status = RunStatus.COMPLETED
                    self._persist(
                        state,
                        "run_completed",
                        {
                            "decision_id": decision.decision.decision_id,
                            "request_id": decision.decision.request_id,
                            "final_output_sha256": hashlib.sha256(
                                output.encode("utf-8")
                            ).hexdigest(),
                            "output_source": "rwkv_explicit_final_answer_text",
                            "controller_rewritten": False,
                            "final_output": output,
                        },
                    )
                    return ControllerResult(state, output, transitions)

                action = self._execute_decision(state, decision)
                pending_events = [self._action_observation_event(state, action)]
                if (
                    action.failure_key
                    and state.failure_budgets.get(action.failure_key, 0)
                    >= self._MAX_IDENTICAL_FAILURES
                ):
                    terminal_reason = "identical_failure_budget_exhausted"
                    break

            if not terminal_reason:
                terminal_reason = "transition_budget_exhausted"
            output = self._terminal_output(
                state,
                terminal_reason,
                (pending_events[-1] if pending_events else None),
            )
            return ControllerResult(state, output, transitions)

    def resume(self, run_id: str) -> ControllerResult:
        return self.run(run_id)

    def _supervisor_plan_request(self, state: RunState) -> SupervisorPlanRequest:
        return SupervisorPlanRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            constraints=tuple(state.goal.constraints),
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
        )

    @staticmethod
    def _run_requires_supervisor(state: RunState) -> bool:
        return any(
            event.event_type == "supervisor_plan_committed"
            or (
                event.event_type == "run_started"
                and str(event.payload.get("architecture") or "")
                == "strong-supervisor-rwkv-worker.v1"
            )
            for event in state.causal_records.values()
        )

    def _missing_supervisor_configuration(self, state: RunState) -> ControllerResult:
        if state.status in {
            RunStatus.FAILED,
            RunStatus.INTERRUPTED,
            RunStatus.BLOCKED,
        }:
            return ControllerResult(state, state.final_output, 0)
        self._persist(
            state,
            "supervisor_configuration_missing",
            {
                "reason": "hybrid_run_requires_supervisor_client",
                "fail_closed": True,
                "action_executed": False,
                "at": utc_now(),
            },
        )
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": "supervisor_configuration_missing",
                "decision_id": state.final_decision_id,
                "final_output_sha256": hashlib.sha256(
                    state.final_output.encode("utf-8")
                ).hexdigest(),
                "output_source": "previous_persisted_output",
                "controller_rewritten": False,
                "final_output": state.final_output,
            },
        )
        return ControllerResult(state, state.final_output, 0)

    @staticmethod
    def _committed_supervisor_plan(state: RunState) -> SupervisorPlan | None:
        payloads = [
            state.causal_records[event_id].payload
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type == "supervisor_plan_committed"
        ]
        if len(payloads) > 1:
            raise ValueError("run contains more than one committed supervisor plan")
        if not payloads:
            return None
        value = payloads[0].get("plan")
        if not isinstance(value, Mapping):
            raise ValueError("committed supervisor plan is incomplete")
        return SupervisorPlan.from_dict(value)

    def _supervisor_plan_event(self, plan: SupervisorPlan) -> ModelEvent:
        return ModelEvent(
            event_type="supervisor_plan",
            event_id=f"EV-SUPERVISOR-{plan.plan_id}",
            scope_id=self.model.ACTION_LANE_ID,
            payload={
                "source": "external_strong_model_supervisor",
                "authority": "planning_and_completion_review_only",
                "plan": plan.to_dict(),
                "instruction": (
                    "Use this bounded plan as guidance. You remain the only component that "
                    "selects and executes direct operations. Verify tool results and return "
                    "final_answer only after the completion checks are satisfied."
                ),
            },
        )

    def _supervisor_plan_failure(
        self,
        state: RunState,
        exc: BaseException,
    ) -> ControllerResult:
        self._persist(
            state,
            "supervisor_call_failed",
            {
                "phase": "plan",
                "supervisor": (
                    supervisor_identity(self.supervisor)
                    if self.supervisor is not None
                    else {}
                ),
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "fail_closed": True,
                "at": utc_now(),
            },
        )
        self._persist(
            state,
            "run_failed",
            {
                "reason": "supervisor_plan_unavailable",
                "output_source": "none",
                "controller_rewritten": False,
                "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                "final_output": "",
            },
        )
        return ControllerResult(state, "", 0)

    def _supervisor_review_request(
        self,
        state: RunState,
        plan: SupervisorPlan,
        decision: ActionDecision,
        output: str,
    ) -> SupervisorReviewRequest:
        actions: list[dict[str, Any]] = []
        ordered = sorted(state.actions.values(), key=lambda item: item.sequence)
        for action in ordered[-96:]:
            result = dict(action.result or {})
            observed_output = str(result.get("output") or "")
            if len(observed_output) > 4000:
                result["output"] = observed_output[:4000]
                result["output_projection"] = {
                    "truncated": True,
                    "original_chars": len(observed_output),
                    "retained_chars": 4000,
                }
            actions.append(
                {
                    "action_id": action.action_id,
                    "sequence": action.sequence,
                    "operation": action.action_type,
                    "arguments": dict(action.arguments),
                    "status": action.status.value,
                    "result": result,
                    "artifact_refs": list(action.artifact_refs),
                }
            )
        artifacts = tuple(
            {
                "artifact_id": artifact.artifact_id,
                "action_id": artifact.action_id,
                "path": artifact.path,
                "sha256": artifact.sha256,
                "media_type": artifact.media_type,
                "size_bytes": artifact.size_bytes,
                "summary": artifact.summary,
            }
            for artifact in state.artifacts.values()
        )
        return SupervisorReviewRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            plan=plan,
            candidate_output=output,
            candidate_decision_id=decision.decision.decision_id,
            action_count=len(ordered),
            actions=tuple(actions),
            artifacts=artifacts,
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
        )

    @staticmethod
    def _unreviewed_supervisor_decision(state: RunState) -> DecisionRecord | None:
        reviewed = {
            str(event.payload.get("candidate_decision_id") or "")
            for event in state.causal_records.values()
            if event.event_type == "supervisor_review_recorded"
        }
        candidate = None
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if (
                event.event_type == "model_call_accepted"
                and str(event.payload.get("operation") or "") == "final_answer"
            ):
                decision_id = str(event.payload.get("decision_id") or "")
                if decision_id and decision_id not in reviewed:
                    candidate = state.decisions.get(decision_id)
        return candidate

    def _review_supervisor_candidate(
        self,
        state: RunState,
        plan: SupervisorPlan,
        decision: ActionDecision,
        output: str,
        transitions: int,
    ) -> ControllerResult | ModelEvent:
        if self.supervisor is None:
            raise RuntimeError("supervisor review requested without a supervisor")
        request = self._supervisor_review_request(state, plan, decision, output)
        try:
            returned = self.supervisor.review_final(request)
            if not isinstance(returned, SupervisorReview):
                raise TypeError("supervisor returned an invalid review object")
            review = SupervisorReview.from_dict(returned.to_dict())
        except Exception as exc:
            return self._supervisor_review_failure(
                state,
                decision,
                output,
                exc,
                transitions,
            )

        prior_repairs = len(self._supervisor_revision_payloads(state))
        self._persist(
            state,
            "supervisor_review_recorded",
            {
                "review_id": review.review_id,
                "review": review.to_dict(),
                "plan_id": plan.plan_id,
                "candidate_decision_id": decision.decision.decision_id,
                "candidate_output": output,
                "candidate_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "review_attempt": prior_repairs + 1,
                "supervisor": supervisor_identity(self.supervisor),
                "rwkv_output_rewritten": False,
            },
        )
        if review.disposition == ReviewDisposition.PASS:
            return self._complete_supervised_candidate(
                state,
                decision.decision.decision_id,
                decision.decision.request_id,
                output,
                review,
                transitions,
            )
        if prior_repairs >= self.supervisor_policy.max_review_repairs:
            return self._interrupt_supervised_candidate(
                state,
                decision.decision.decision_id,
                output,
                review,
                transitions,
            )
        return self._supervisor_review_event(
            review,
            decision.decision.decision_id,
            repair_number=prior_repairs + 1,
        )

    @staticmethod
    def _supervisor_revision_payloads(state: RunState) -> list[Mapping[str, Any]]:
        revisions: list[Mapping[str, Any]] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "supervisor_review_recorded":
                continue
            review = event.payload.get("review")
            if (
                isinstance(review, Mapping)
                and str(review.get("disposition") or "")
                == ReviewDisposition.REVISE.value
            ):
                revisions.append(event.payload)
        return revisions

    def _supervisor_review_event(
        self,
        review: SupervisorReview,
        candidate_decision_id: str,
        *,
        repair_number: int,
    ) -> ModelEvent:
        return ModelEvent(
            event_type="supervisor_review",
            event_id=f"EV-SUPERVISOR-REVIEW-{candidate_decision_id}",
            scope_id=self.model.ACTION_LANE_ID,
            payload={
                "source": "external_strong_model_supervisor",
                "candidate_decision_id": candidate_decision_id,
                "repair_number": repair_number,
                "review": review.to_dict(),
                "instruction": (
                    "The completion candidate was not accepted. Address every concrete issue "
                    "using direct operations and observed facts. Return final_answer again only "
                    "after the issues and original completion checks are satisfied."
                ),
            },
        )

    def _recover_supervisor_review_boundary(
        self,
        state: RunState,
        plan: SupervisorPlan,
    ) -> ControllerResult | ModelEvent | None:
        payload: Mapping[str, Any] | None = None
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type == "supervisor_review_recorded":
                payload = event.payload
        if payload is None:
            return None
        review_value = payload.get("review")
        if not isinstance(review_value, Mapping):
            raise ValueError("recorded supervisor review is incomplete")
        review = SupervisorReview.from_dict(review_value)
        candidate_decision_id = str(payload.get("candidate_decision_id") or "")
        output = str(payload.get("candidate_output") or "")
        if not candidate_decision_id:
            raise ValueError("recorded supervisor review has no candidate decision")
        if str(payload.get("plan_id") or "") != plan.plan_id:
            raise ValueError("recorded supervisor review references another plan")
        if review.disposition == ReviewDisposition.PASS:
            decision = state.decisions.get(candidate_decision_id)
            request_id = decision.request_id if decision is not None else ""
            return self._complete_supervised_candidate(
                state,
                candidate_decision_id,
                request_id,
                output,
                review,
                0,
            )
        revision_count = len(self._supervisor_revision_payloads(state))
        if revision_count > self.supervisor_policy.max_review_repairs:
            return self._interrupt_supervised_candidate(
                state,
                candidate_decision_id,
                output,
                review,
                0,
            )
        model_event = self._supervisor_review_event(
            review,
            candidate_decision_id,
            repair_number=revision_count,
        )
        if model_event.event_id not in state.model_events:
            return model_event
        return None

    def _complete_supervised_candidate(
        self,
        state: RunState,
        decision_id: str,
        request_id: str,
        output: str,
        review: SupervisorReview,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "run_completed",
            {
                "decision_id": decision_id,
                "request_id": request_id,
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": "rwkv_explicit_final_answer_text",
                "controller_rewritten": False,
                "supervisor_review_id": review.review_id,
                "supervisor_disposition": review.disposition.value,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _interrupt_supervised_candidate(
        self,
        state: RunState,
        decision_id: str,
        output: str,
        review: SupervisorReview,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": "supervisor_revision_budget_exhausted",
                "decision_id": decision_id,
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": "rwkv_candidate_not_approved_by_supervisor",
                "controller_rewritten": False,
                "supervisor_review_id": review.review_id,
                "supervisor_disposition": review.disposition.value,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _supervisor_review_failure(
        self,
        state: RunState,
        decision: ActionDecision,
        output: str,
        exc: BaseException,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "supervisor_call_failed",
            {
                "phase": "review",
                "candidate_decision_id": decision.decision.decision_id,
                "supervisor": (
                    supervisor_identity(self.supervisor)
                    if self.supervisor is not None
                    else {}
                ),
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "fail_closed": True,
                "at": utc_now(),
            },
        )
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": "supervisor_review_unavailable",
                "decision_id": decision.decision.decision_id,
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": "rwkv_candidate_supervisor_unavailable",
                "controller_rewritten": False,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _execute_decision(
        self,
        state: RunState,
        decision: ActionDecision,
    ) -> ActionRecord:
        action = TaskAction(decision.command.name, dict(decision.command.arguments))
        sequence = state.next_action_sequence
        action_id = f"A{sequence:05d}"
        before = self.harness.workspace_observation_snapshot(state.goal)
        fingerprint = action_fingerprint(action)
        record = ActionRecord(
            action_id=action_id,
            sequence=sequence,
            status=ActionStatus.RUNNING,
            action_type=action.action_type,
            arguments=dict(action.arguments),
            wire_arguments=dict(decision.wire_command.arguments),
            action_fingerprint=fingerprint,
            idempotency_key=hashlib.sha256(
                f"{state.run_id}:{sequence}:{fingerprint}".encode("utf-8")
            ).hexdigest(),
            decision_id=decision.decision.decision_id,
            request_id=decision.decision.request_id,
            started_at=utc_now(),
            workspace_digest_before=str(before.get("digest") or ""),
        )
        self._persist(
            state,
            "action_started",
            {
                "action_id": action_id,
                "action": record.to_dict(),
            },
        )
        record = state.actions[action_id]

        try:
            result = self.harness.execute(action, state.goal)
        except BaseException as exc:
            if getattr(exc, "rwkv_lh_process_loss", False):
                raise
            result = ActionResult(
                action.action_type,
                False,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )
        return self._finish_action(state, record, result)

    def _finish_action(
        self,
        state: RunState,
        record: ActionRecord,
        result: ActionResult,
    ) -> ActionRecord:
        authoritative = state.actions.get(record.action_id)
        if authoritative is None or authoritative.status != ActionStatus.RUNNING:
            raise ValueError(f"action is not running: {record.action_id}")
        finished = ActionRecord.from_dict(authoritative.to_dict())
        after = self.harness.workspace_observation_snapshot(state.goal)
        finished.result = result.to_dict()
        finished.status = ActionStatus.SUCCEEDED if result.success else ActionStatus.FAILED
        if result.outcome_type == "interrupted":
            finished.status = ActionStatus.INTERRUPTED
        finished.outcome_type = result.outcome_type
        finished.error = dict(result.error) if isinstance(result.error, Mapping) else None
        finished.ended_at = utc_now()
        finished.workspace_digest_after = str(after.get("digest") or "")
        artifacts, revisions = self._artifact_records(state, finished, result)
        finished.artifact_refs = [item.artifact_id for item in artifacts]
        finished.observation_fingerprint = self._observation_fingerprint(finished, result)
        if not result.success:
            finished.failure_key = finished.observation_fingerprint
        identical_result_count = (
            state.observation_counts.get(finished.observation_fingerprint, 0) + 1
        )
        self._persist(
            state,
            "action_finished",
            {
                "action_id": finished.action_id,
                "action": finished.to_dict(),
                "artifacts": [item.__dict__ for item in artifacts],
                "artifact_revisions": [item.__dict__ for item in revisions],
                "identical_result_count": identical_result_count,
                "result_digest": canonical_digest(finished.result),
            },
        )
        return state.actions[finished.action_id]

    def _recover_active_action(self, state: RunState) -> None:
        action_id = state.active_action_id
        if not action_id:
            return
        record = state.actions.get(action_id)
        if record is None or record.status != ActionStatus.RUNNING:
            state.active_action_id = None
            self._persist(
                state,
                "stale_active_action_cleared",
                {"action_id": action_id},
            )
            return
        definition = self.harness.definition(record.action_type)
        if not definition.idempotent:
            result = ActionResult(
                record.action_type,
                False,
                error={
                    "type": "InterruptedNonIdempotentAction",
                    "message": (
                        "process ended after the action started; its effect is unknown and "
                        "the runtime did not replay a non-idempotent operation"
                    ),
                },
                outcome_type="interrupted",
            )
            self._finish_action(state, record, result)
            return
        result = self.harness.execute(
            TaskAction(record.action_type, dict(record.arguments)),
            state.goal,
        )
        self._finish_action(state, record, result)
        self._persist(
            state,
            "idempotent_action_recovered",
            {"action_id": action_id, "operation": record.action_type},
        )

    def _artifact_records(
        self,
        state: RunState,
        action: ActionRecord,
        result: ActionResult,
    ) -> tuple[list[ArtifactRecord], list[ArtifactRevision]]:
        artifacts: list[ArtifactRecord] = []
        revisions: list[ArtifactRevision] = []
        for index, observed in enumerate(result.artifacts, start=1):
            artifact_id = "ART-" + hashlib.sha256(
                f"{action.action_id}:{index}:{observed.path}:{observed.sha256}".encode(
                    "utf-8"
                )
            ).hexdigest()[:20]
            artifact = ArtifactRecord(
                artifact_id=artifact_id,
                action_id=action.action_id,
                path=observed.path,
                sha256=observed.sha256,
                media_type=observed.media_type,
                size_bytes=observed.size_bytes,
                summary=observed.summary,
            )
            prior = state.artifact_revisions.get(observed.path, [])
            revision = ArtifactRevision(
                revision_id=f"REV-{uuid4().hex[:16]}",
                target=observed.path,
                artifact_id=artifact_id,
                action_id=action.action_id,
                sha256=observed.sha256,
                outcome_type=result.outcome_type,
                supersedes_revision_ids=(
                    [prior[-1].revision_id] if prior else []
                ),
            )
            artifacts.append(artifact)
            revisions.append(revision)
        return artifacts, revisions

    @staticmethod
    def _observation_fingerprint(
        action: ActionRecord,
        result: ActionResult,
    ) -> str:
        """Stable identity of one exact observed fact, for success and failure alike.

        Deliberately excludes workspace digests, artifact revisions, and volatile
        non-target arguments so that byte-identical results accumulate an exact
        repeat count instead of fragmenting into unique keys.
        """

        target = {
            key: action.arguments[key]
            for key in ("path", "destination", "argv", "cwd")
            if key in action.arguments
        }
        return canonical_digest(
            {
                "operation": action.action_type,
                "target": target,
                "outcome_type": result.outcome_type,
                "exit_code": result.exit_code,
                "error": result.error,
                "output": result.output,
            }
        )

    def _action_observation_event(
        self,
        state: RunState,
        action: ActionRecord,
    ) -> ModelEvent:
        revisions = [
            revision.__dict__
            for artifact_id in action.artifact_refs
            for revisions in state.artifact_revisions.values()
            for revision in revisions
            if revision.artifact_id == artifact_id
        ]
        return ModelEvent(
            event_type="action_result",
            event_id=f"EV-ACTION-{action.action_id}",
            scope_id=self.model.ACTION_LANE_ID,
            payload={
                "action_id": action.action_id,
                "operation": action.action_type,
                "explicit_arguments": dict(action.arguments),
                "result": dict(action.result or {}),
                "artifact_refs": list(action.artifact_refs),
                "artifact_revisions": revisions,
                "workspace_digest_before": action.workspace_digest_before,
                "workspace_digest_after": action.workspace_digest_after,
                "observation_fingerprint": action.observation_fingerprint,
                "identical_result_count": (
                    state.observation_counts.get(action.observation_fingerprint, 0)
                    if action.observation_fingerprint
                    else 0
                ),
            },
            content_refs=tuple(action.artifact_refs),
        )

    def _first_unappended_action_observation(
        self,
        state: RunState,
    ) -> ModelEvent | None:
        for action in sorted(state.actions.values(), key=lambda item: item.sequence):
            if action.status == ActionStatus.RUNNING:
                continue
            event_id = f"EV-ACTION-{action.action_id}"
            if event_id not in state.model_events:
                return self._action_observation_event(state, action)
        return None

    def _terminal_output(
        self,
        state: RunState,
        reason: str,
        pending_event: ModelEvent | None,
    ) -> str:
        last_raw = ""
        event = ModelEvent(
            event_type="terminal_boundary",
            event_id=f"EV-TERMINAL-{uuid4().hex[:16]}",
            scope_id=self.model.ACTION_LANE_ID,
            payload={
                "run_status": "interrupted",
                "reason": reason,
                "actions_observed": len(state.actions),
                "instruction": "Return final_answer now; do not claim unobserved work.",
                **(
                    {"last_unappended_action_result": pending_event.to_model_dict()}
                    if pending_event is not None
                    else {}
                ),
            },
        )
        transport_failures = 0
        protocol_attempts = 0
        failure_reason = "rwkv_terminal_answer_protocol_exhausted"
        while protocol_attempts < self._MAX_TERMINAL_ATTEMPTS:
            try:
                decision = self.model.terminal_answer(
                    state,
                    self._persist_callback,
                    event=event,
                )
            except RWKVRuntimeError as exc:
                transport_failures += 1
                self._record_transport_failure(state, exc, transport_failures)
                if transport_failures >= self._MAX_TRANSPORT_FAILURES:
                    failure_reason = "model_transport_unavailable"
                    break
                self._transport_backoff(transport_failures)
                continue
            except ModelProtocolError as exc:
                protocol_attempts += 1
                rejected = state.decisions.get(exc.decision_id)
                if rejected is not None:
                    last_raw = rejected.raw_output
                event = ModelEvent(
                    event_type="terminal_protocol_rejection",
                    event_id=f"EV-TERMINAL-REJECT-{uuid4().hex[:16]}",
                    scope_id=self.model.ACTION_LANE_ID,
                    payload={
                        "error": str(exc)[:2000],
                        "required_function": "final_answer",
                        "required_parameters": {"text": "non-empty string"},
                    },
                )
                continue
            output = str(decision.wire_command.arguments["text"])
            state.final_output = output
            state.final_decision_id = decision.decision.decision_id
            state.status = RunStatus.INTERRUPTED
            self._persist(
                state,
                "run_interrupted",
                {
                    "reason": reason,
                    "decision_id": decision.decision.decision_id,
                    "final_output_sha256": hashlib.sha256(
                        output.encode("utf-8")
                    ).hexdigest(),
                    "output_source": "rwkv_explicit_final_answer_text",
                    "controller_rewritten": False,
                    "final_output": output,
                },
            )
            return output

        state.final_output = last_raw
        state.status = RunStatus.FAILED
        self._persist(
            state,
            "run_failed",
            {
                "reason": failure_reason,
                "output_source": "last_raw_rwkv_response",
                "controller_rewritten": False,
                "final_output_sha256": hashlib.sha256(
                    last_raw.encode("utf-8")
                ).hexdigest(),
                "final_output": last_raw,
            },
        )
        return last_raw

    def _record_transport_failure(
        self,
        state: RunState,
        exc: BaseException,
        attempt: int,
    ) -> None:
        self._persist(
            state,
            "model_transport_failure",
            {
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "attempt": attempt,
                "max_attempts": self._MAX_TRANSPORT_FAILURES,
                "action_executed": False,
                "at": utc_now(),
            },
        )

    def _transport_backoff(self, attempt: int) -> None:
        time.sleep(min(self._TRANSPORT_BACKOFF_CAP_SECONDS, 2.0 ** attempt))

    def _persist_callback(
        self,
        state: RunState,
        event_type: str,
        event: Mapping[str, Any],
    ) -> None:
        self._persist(state, event_type, event)

    def _persist(
        self,
        state: RunState,
        event_type: str,
        event: Mapping[str, Any],
    ) -> None:
        subject_keys = {
            "action_session_started": "lane_id",
            "action_session_rolled_over": "rollover_id",
            "model_call_accepted": "decision_id",
            "model_call_rejected": "decision_id",
            "protocol_rejection_recorded": "decision_id",
            "action_started": "action_id",
            "action_finished": "action_id",
            "action_observation_appended": "event_id",
            "stale_active_action_cleared": "action_id",
            "idempotent_action_recovered": "action_id",
            "supervisor_plan_committed": "plan_id",
            "supervisor_review_recorded": "review_id",
        }
        subject_key = subject_keys.get(event_type)
        subject_id = str(event.get(subject_key) or state.run_id) if subject_key else state.run_id
        draft = CausalEventDraft.create(
            event_type,
            event,
            subject_id=subject_id,
            cause_id=(state.causal_order[-1] if state.causal_order else None),
        )
        saved = self.store.save(
            state,
            expected_revision=state.revision,
            causal_event=draft,
        )
        state.__dict__.clear()
        state.__dict__.update(saved.__dict__)


__all__ = ["ControllerResult", "LongHorizonController"]
