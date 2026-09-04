"""Persistent RWKV executor with an optional bounded supervisor boundary."""

from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping
from uuid import uuid4

from rwkv_lh.atom_execution import (
    AtomExecutionBinding,
    AtomExecutionContract,
    atom_contract_progress,
    atom_execution_contract_digest,
    final_answer_eligible,
)
from rwkv_lh.capability_projection import (
    CAPABILITY_PROJECTION_VERSION,
)
from rwkv_lh.contract_graph import (
    ContractAssertion,
    ContractAssertionKind,
    ContractExecutionBatch,
    ContractGraphNode,
    ContractGraphPatch,
    ContractGraphReview,
    ContractObligation,
    ContractPlanRequest,
    ContractReviewRequest,
    ObligationPhase,
    ObligationVerdict,
    ObligationVerdictStatus,
    ResultCapsule,
)
from rwkv_lh.contract_validation import (
    contract_scopes_overlap,
    validate_contract_patch_semantics,
)
from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.model import (
    ActionDecision,
    LongHorizonModel,
    ModelProtocolError,
    PersistCallback,
)
from rwkv_lh.model_io import (
    canonical_digest,
    canonical_json,
    parse_model_command,
    validate_final_answer,
)
from rwkv_lh.parallel_atoms import (
    PATH_MUTATION_OPERATIONS,
    AtomExecutionOutcome,
    AtomExecutionStatus,
    AtomWorkerPool,
)
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.retrieval.runtime import operation_allowed_by_retrieval_policy
from rwkv_lh.run_lifecycle import (
    goal_self_termination_only,
    model_voluntary_completion,
)
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
from rwkv_lh.trace_projection import unresolved_supervisor_pending
from rwkv_lh.supervisor import (
    AtomRole,
    DirectiveDisposition,
    ReviewDisposition,
    StageDisposition,
    SupervisorClient,
    SupervisorDirective,
    SupervisorDirectiveRequest,
    SupervisorPlan,
    SupervisorPlanRequest,
    SupervisorPolicy,
    SupervisorReview,
    SupervisorReviewRequest,
    SupervisorStage,
    SupervisorStageRequest,
    supervisor_identity,
)


@dataclass
class ControllerResult:
    state: RunState
    final_output: str
    transitions: int


_CONTENT_OBSERVATION_OPERATIONS = frozenset(
    {"read_file", "read_json", "bind_evidence", "mock_api"}
)
_COMMAND_OBSERVATION_OPERATIONS = frozenset(
    {"run_command", "check_command", "mock_api"}
)
CONTRACT_GRAPH_ARCHITECTURE = "strong-planner-reviewer-rwkv-contract-graph.v2"
CONTRACT_GRAPH_ARCHITECTURE_VERSIONS = frozenset(
    {
        "strong-planner-reviewer-rwkv-contract-graph.v1",
        CONTRACT_GRAPH_ARCHITECTURE,
    }
)


class LongHorizonController:
    """Execute RWKV operations; optionally gate planning and completion externally."""

    _MAX_PROTOCOL_REJECTIONS = 12
    _MAX_IDENTICAL_FAILURES = 5
    _MAX_IDENTICAL_ZERO_PROGRESS_SUCCESSES = 3
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
        atom_worker_pool: AtomWorkerPool | None = None,
        max_transitions: int = 500,
        max_actions: int | None = None,
        min_actions: int | None = None,
        **_removed_options: Any,
    ) -> None:
        self.store = store or LongHorizonStore()
        self.harness = harness or ActionHarness()
        self.model = model or LongHorizonModel(harness=self.harness)
        self.supervisor = supervisor
        self.supervisor_policy = supervisor_policy or SupervisorPolicy()
        self.atom_worker_pool = atom_worker_pool
        self.max_transitions = max(1, int(max_transitions))
        self._legacy_max_actions = (
            None if max_actions is None else max(0, int(max_actions))
        )
        self._legacy_minimum_actions = (
            0 if min_actions is None else max(0, int(min_actions))
        )
        self._minimum_actions_was_supplied = min_actions is not None
        if (
            self._legacy_max_actions is not None
            and self._legacy_minimum_actions > self._legacy_max_actions
        ):
            raise ValueError("min_actions cannot exceed max_actions")

    def _action_limits(self, state: RunState) -> tuple[int | None, int]:
        binding = AtomExecutionBinding.from_goal(state.goal)
        if binding is None:
            return self._legacy_max_actions, self._legacy_minimum_actions
        contract = binding.contract
        if (
            self._legacy_max_actions is not None
            and self._legacy_max_actions != contract.atom.action_budget
        ):
            raise ValueError(
                "Controller max_actions differs from the immutable atom contract"
            )
        if (
            self._minimum_actions_was_supplied
            and self._legacy_minimum_actions != contract.minimum_actions
        ):
            raise ValueError(
                "Controller min_actions differs from the immutable atom contract"
            )
        return contract.atom.action_budget, contract.minimum_actions

    @staticmethod
    def _goal_self_termination_only(state: RunState) -> bool:
        """Apply Goal lifecycle semantics only to the parent run, not its atoms."""

        return (
            AtomExecutionBinding.from_goal(state.goal) is None
            and goal_self_termination_only(state.goal)
        )

    def _goal_epoch_start_sequence(self, state: RunState) -> int:
        if not self._goal_self_termination_only(state):
            return 0
        return next(
            (
                state.causal_records[event_id].sequence
                for event_id in reversed(state.causal_order)
                if state.causal_records[event_id].event_type == "run_yielded"
            ),
            0,
        )

    def _goal_epoch_event_count(self, state: RunState, event_type: str) -> int:
        start = self._goal_epoch_start_sequence(state)
        return sum(
            event.event_type == event_type and event.sequence > start
            for event in state.causal_records.values()
        )

    def _lifecycle_budget_count(
        self,
        state: RunState,
        *,
        event_type: str,
        bounded_total: int,
    ) -> int:
        """Make controller budgets per-continuation in Goal mode."""

        if self._goal_self_termination_only(state):
            return self._goal_epoch_event_count(state, event_type)
        return bounded_total

    @property
    def max_actions(self) -> int | None:
        """Compatibility surface for non-atom top-level runs only."""

        return self._legacy_max_actions

    @max_actions.setter
    def max_actions(self, value: int | None) -> None:
        selected = None if value is None else max(0, int(value))
        if (
            selected is not None
            and self._legacy_minimum_actions > selected
        ):
            raise ValueError("min_actions cannot exceed max_actions")
        self._legacy_max_actions = selected

    def run(self, run_id: str) -> ControllerResult:
        with self.store.controller_lease(run_id):
            state = self.store.load(run_id)
            action_budget, minimum_actions = self._action_limits(state)
            if state.status == RunStatus.COMPLETED:
                return ControllerResult(state, state.final_output, 0)
            if not state.goal.verify_digest():
                raise ValueError("literal request digest mismatch")
            if self.supervisor is None and self._run_requires_supervisor(state):
                return self._missing_supervisor_configuration(state)

            transitions = 0
            self._recover_active_action(state)
            if state.status != RunStatus.RUNNING:
                prior_terminal_event_id = next(
                    (
                        event_id
                        for event_id in reversed(state.causal_order)
                        if state.causal_records[event_id].event_type
                        in {
                            "run_completed",
                            "run_failed",
                            "run_blocked",
                            "run_interrupted",
                        }
                    ),
                    "",
                )
                state.status = RunStatus.RUNNING
                hybrid = self.supervisor is not None
                online_microtask = (
                    hybrid and self.supervisor_policy.mode == "online_microtask"
                )
                parallel_atoms = (
                    hybrid and self.supervisor_policy.mode == "parallel_atoms"
                )
                contract_graph = (
                    hybrid and self.supervisor_policy.mode == "contract_graph"
                )
                self._persist(
                    state,
                    "run_started",
                    {
                        "architecture": (
                            CONTRACT_GRAPH_ARCHITECTURE
                            if contract_graph
                            else
                            "strong-supervisor-parallel-rwkv-atoms.v5"
                            if parallel_atoms
                            else
                            "online-strong-supervisor-rwkv-microtask-worker.v1"
                            if online_microtask
                            else "strong-supervisor-rwkv-worker.v1"
                            if hybrid
                            else "single-rwkv-direct-action.v1"
                        ),
                        "online_task_graph": (
                            online_microtask or parallel_atoms or contract_graph
                        ),
                        "parallel_rwkv_atoms": parallel_atoms or contract_graph,
                        "result_capsules_only": contract_graph,
                        "reviewer": hybrid,
                        "resumed": bool(prior_terminal_event_id),
                        "supersedes_terminal_event_id": prior_terminal_event_id,
                        **(
                            {"supervisor": supervisor_identity(self.supervisor)}
                            if self.supervisor is not None
                            else {}
                        ),
                        },
                    )

            self._reconcile_supervisor_pending(state)

            if (
                self.supervisor is not None
                and self.supervisor_policy.mode == "online_microtask"
            ):
                return self._run_online_supervised(state)
            if (
                self.supervisor is not None
                and self.supervisor_policy.mode == "parallel_atoms"
            ):
                return self._run_parallel_atoms(state)
            if (
                self.supervisor is not None
                and self.supervisor_policy.mode == "contract_graph"
            ):
                try:
                    return self._run_contract_graph(state)
                except Exception as exc:
                    transitions = sum(
                        item.action_count
                        for item in self._committed_atom_outcomes(state).values()
                    )
                    self._persist(
                        state,
                        "contract_graph_runtime_failed",
                        {
                            "error": {
                                "type": type(exc).__name__,
                                "message": str(exc)[:2000],
                            },
                            "terminalized": not self._goal_self_termination_only(state),
                            "at": utc_now(),
                        },
                    )
                    return self._interrupt_contract_graph(
                        state,
                        reason="contract_graph_runtime_failure",
                        transitions=transitions,
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
                self._persist_supervisor_resolved(state, phase="plan")
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
            forced_terminal_event = (
                self._pending_idempotent_mutation_repeat_event(state)
            )
            transport_failures = 0
            while transitions < self.max_transitions:
                try:
                    action_budget_reached = (
                        action_budget is not None
                        and len(state.actions) >= action_budget
                    )
                    if action_budget_reached and not final_answer_eligible(
                        state,
                        legacy_minimum_actions=minimum_actions,
                    ):
                        # The immutable atom cannot legally execute another
                        # operation.  Do not force Final and then reject it in a
                        # protocol loop; return the incomplete outcome to the
                        # contract graph so its Planner can issue a correction.
                        terminal_reason = "atom_contract_action_budget_exhausted"
                        break
                    if forced_terminal_event is not None:
                        decision = self.model.terminal_answer(
                            state,
                            self._persist_callback,
                            event=forced_terminal_event,
                        )
                        forced_terminal_event = None
                        pending_events = []
                    elif action_budget_reached:
                        decision = self.model.terminal_answer(
                            state,
                            self._persist_callback,
                            event=ModelEvent(
                                event_type="action_budget_boundary",
                                event_id=(
                                    f"EV-ACTION-BUDGET-{len(state.actions)}-"
                                    f"{transitions}"
                                ),
                                scope_id=self.model.ACTION_LANE_ID,
                                payload={
                                    "action_budget": action_budget,
                                    "actions_observed": len(state.actions),
                                    "instruction": (
                                        "The committed atom action budget is exhausted. "
                                        "Return final_answer now using only observed facts; "
                                        "do not request another operation."
                                    ),
                                    "pending_events": [
                                        item.to_model_dict()
                                        for item in pending_events[-2:]
                                    ],
                                },
                            ),
                        )
                    elif len(pending_events) > 1:
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
                        "selection_id": exc.selection_id,
                        "selected_operation": exc.selected_operation,
                        "rejected_arguments": dict(exc.rejected_arguments),
                        "at": utc_now(),
                    }
                    self._persist(
                        state,
                        "protocol_rejection_recorded",
                        {
                            "decision_id": exc.decision_id,
                            "request_id": exc.request_id,
                            "error": str(exc)[:2000],
                            "rejected_arguments": dict(exc.rejected_arguments),
                            "selected_operation": exc.selected_operation,
                            "error_record": error_record,
                            "rejection_count": state.protocol_rejections + 1,
                            "action_executed": False,
                            **(
                                {"selection_id": exc.selection_id}
                                if exc.selection_id
                                else {}
                            ),
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
                            "rejected_arguments": dict(exc.rejected_arguments),
                            **(
                                {"selection_id": exc.selection_id}
                                if exc.selection_id
                                else {}
                            ),
                            **(
                                {
                                    "selected_operation": exc.selected_operation,
                                    **(
                                        {
                                            "selected_operation_schema": (
                                                exc.selected_operation_schema
                                            )
                                        }
                                        if not exc.schema_already_disclosed
                                        else {}
                                    ),
                                    "schema_already_disclosed": (
                                        exc.schema_already_disclosed
                                    ),
                                }
                                if exc.selected_operation
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
                    if not final_answer_eligible(
                        state,
                        legacy_minimum_actions=minimum_actions,
                    ):
                        progress = atom_contract_progress(state)
                        error = (
                            "final_answer is premature: the immutable atom execution "
                            f"contract still has {progress.remaining_required_count} "
                            "required result(s)"
                            if progress is not None
                            else (
                                "final_answer is premature: this run must complete at "
                                f"least {minimum_actions} direct action(s) before "
                                "finalizing"
                            )
                        )
                        self._persist(
                            state,
                            "protocol_rejection_recorded",
                            {
                                "decision_id": decision.decision.decision_id,
                                "request_id": decision.decision.request_id,
                                "rejection_ref": (
                                    "protocol:" + decision.decision.decision_id
                                ),
                                "error": error,
                                "error_record": {
                                    "type": "PrematureFinalAnswer",
                                    "message": error,
                                    "decision_id": decision.decision.decision_id,
                                    "request_id": decision.decision.request_id,
                                    "at": utc_now(),
                                },
                                "rejection_count": state.protocol_rejections + 1,
                                "action_executed": False,
                            },
                        )
                        if state.protocol_rejections >= self._MAX_PROTOCOL_REJECTIONS:
                            terminal_reason = "protocol_rejection_budget_exhausted"
                            break
                        pending_events = [
                            ModelEvent(
                                event_type="protocol_rejection",
                                event_id=f"EV-REJECT-{uuid4().hex[:16]}",
                                scope_id=self.model.ACTION_LANE_ID,
                                payload={
                                    "error": error,
                                    "action_executed": False,
                                    "instruction": (
                                        "Do not finalize yet. Execute the one displayed "
                                        "observation operation required by this atom, using "
                                        "its complete explicit parameter object."
                                    ),
                                },
                            )
                        ]
                        continue
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
                definition = self.harness.definition(action.action_type)
                identical_result_count = state.observation_counts.get(
                    action.observation_fingerprint,
                    0,
                )
                if (
                    action.status == ActionStatus.SUCCEEDED
                    and definition.side_effect
                    and definition.idempotent
                    and definition.network_access == "none"
                    and definition.side_effect_class == "workspace_mutation"
                    and bool(action.workspace_digest_before)
                    and action.workspace_digest_before
                    == action.workspace_digest_after
                    and identical_result_count >= 2
                ):
                    # The same deterministic workspace mutation has already
                    # succeeded and the latest replay changed no bytes. Keep
                    # the committed evidence but close the operation menu so a
                    # weak worker cannot spend the remaining atom budget on a
                    # third identical side effect. One initial no-op remains
                    # legal because a multi-step atom may still have other work.
                    self._persist(
                        state,
                        "idempotent_mutation_repeat_boundary",
                        {
                            "action_id": action.action_id,
                            "operation": action.action_type,
                            "observation_fingerprint": (
                                action.observation_fingerprint
                            ),
                            "identical_result_count": identical_result_count,
                            "workspace_digest": action.workspace_digest_after,
                            "next_required_function": "final_answer",
                        },
                    )
                    forced_terminal_event = (
                        self._pending_idempotent_mutation_repeat_event(state)
                    )
                    if forced_terminal_event is None:
                        raise ValueError(
                            "committed idempotent mutation boundary was not recoverable"
                        )
                if (
                    action.status == ActionStatus.SUCCEEDED
                    and definition.read_only
                    and not definition.side_effect
                    and bool(action.workspace_digest_before)
                    and action.workspace_digest_before == action.workspace_digest_after
                    and identical_result_count
                    >= self._MAX_IDENTICAL_ZERO_PROGRESS_SUCCESSES
                ):
                    terminal_reason = "identical_success_budget_exhausted"
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

    def _run_contract_graph(self, state: RunState) -> ControllerResult:
        """Run an append-only strong-plan/RWKV-execute/strong-review graph."""

        if self.supervisor is None:
            raise RuntimeError("contract graph mode requires a supervisor")
        if self.atom_worker_pool is None:
            return self._interrupt_contract_graph(
                state,
                reason="contract_graph_atom_worker_pool_missing",
                transitions=0,
            )

        while True:
            obligations, nodes, patches, reviews = self._committed_contract_graph(
                state
            )
            outcomes = self._committed_atom_outcomes(state)
            transitions = sum(item.action_count for item in outcomes.values())
            capsules = self._contract_result_capsules(state, nodes, outcomes)
            evidence_digest = canonical_digest(
                [item.to_dict() for item in capsules]
            )

            if self._project_parallel_atom_actions(state, outcomes):
                continue

            batches = self._committed_contract_batches(state)
            pending_batch = next(
                (
                    batch
                    for batch in reversed(batches)
                    if any(node_id not in outcomes for node_id in batch.node_ids)
                ),
                None,
            )
            if pending_batch is not None:
                pending_atoms = tuple(
                    nodes[node_id].atom
                    for node_id in pending_batch.node_ids
                    if node_id not in outcomes
                )
                attempted = self._parallel_attempted_atom_ids(state)
                for atom in pending_atoms:
                    if atom.atom_id in attempted:
                        continue
                    execution_contract = AtomExecutionContract.create(
                        immutable_request=state.goal.request,
                        atom=atom,
                    )
                    self._persist(
                        state,
                        "atom_attempt_started",
                        {
                            "stage_id": pending_batch.stage_id,
                            "stage_index": pending_batch.stage_index,
                            "atom_id": atom.atom_id,
                            "contract_digest": (
                                execution_contract.contract_digest
                            ),
                            "role": atom.role.value,
                            "depends_on": list(atom.depends_on),
                            "write_roots": list(atom.write_roots),
                            "exclusive": atom.exclusive,
                            "graph_revision": len(patches),
                            "at": utc_now(),
                        },
                        subject_id=atom.atom_id,
                    )
                returned = self.atom_worker_pool.run_stage(
                    state.goal,
                    pending_batch,
                    pending_atoms,
                    max_workers=min(
                        self.supervisor_policy.max_parallel_atoms,
                        len(pending_atoms),
                    ),
                    max_transitions=self.supervisor_policy.atom_max_transitions,
                    completed_outcomes=outcomes,
                )
                returned_by_id = {item.atom_id: item for item in returned}
                if set(returned_by_id) != {
                    atom.atom_id for atom in pending_atoms
                }:
                    raise ValueError(
                        "contract atom pool returned an incomplete batch"
                    )
                for atom in pending_atoms:
                    execution_contract = AtomExecutionContract.create(
                        immutable_request=state.goal.request,
                        atom=atom,
                    )
                    outcome = AtomExecutionOutcome.from_dict(
                        returned_by_id[atom.atom_id].to_dict()
                    )
                    if (
                        outcome.stage_id != pending_batch.stage_id
                        or outcome.contract_digest
                        != execution_contract.contract_digest
                        or outcome.role != atom.role
                        or outcome.write_roots != atom.write_roots
                    ):
                        raise ValueError(
                            "contract atom outcome changed committed node identity"
                        )
                    self._persist(
                        state,
                        "atom_outcome_committed",
                        {
                            "stage_id": pending_batch.stage_id,
                            "stage_index": pending_batch.stage_index,
                            "atom_id": atom.atom_id,
                            "outcome": outcome.to_dict(),
                            "graph_revision": len(patches),
                            "rwkv_action_authority": True,
                            "supervisor_action_executed": False,
                            "controller_rewritten": False,
                        },
                        subject_id=atom.atom_id,
                    )
                continue

            current_review_record = next(
                (
                    item
                    for item in reversed(reviews)
                    if item[0].graph_revision == len(patches)
                    and item[1] == evidence_digest
                ),
                None,
            )
            current_review = (
                current_review_record[0]
                if current_review_record is not None
                else None
            )
            all_satisfied = self._contract_all_required_satisfied(
                obligations,
                current_review,
            )
            presentation_obligations = {
                obligation_id: obligation
                for obligation_id, obligation in obligations.items()
                if obligation.phase == ObligationPhase.FINAL_PRESENTATION
            }
            presentation_reviews = (
                self._committed_contract_presentation_reviews(
                    state,
                    presentation_obligations,
                )
            )
            failed_presentation_review: ContractGraphReview | None = None
            failed_presentation_capsules: tuple[ResultCapsule, ...] | None = None
            finalizer_nodes = [
                node
                for node in nodes.values()
                if node.atom.role == AtomRole.FINALIZER
            ]
            latest_finalizer = finalizer_nodes[-1] if finalizer_nodes else None
            completed_work_ids = {
                node_id
                for node_id, outcome in outcomes.items()
                if node_id in nodes
                and nodes[node_id].atom.role == AtomRole.WORK
                and outcome.status == AtomExecutionStatus.COMPLETED
            }
            completed_finalizer = (
                outcomes.get(latest_finalizer.node_id)
                if latest_finalizer is not None
                and completed_work_ids
                <= set(latest_finalizer.atom.depends_on)
                else None
            )
            if (
                completed_finalizer is not None
                and completed_finalizer.status == AtomExecutionStatus.COMPLETED
                and completed_finalizer.candidate_output
            ):
                if not all_satisfied:
                    raise ValueError(
                        "a contract finalizer completed without a current satisfied review"
                    )
                if not presentation_obligations:
                    return self._complete_contract_finalizer(
                        state,
                        completed_finalizer,
                        nodes,
                        current_review,
                        transitions,
                    )
                workspace_manifest = self.harness.workspace_manifest(
                    state.goal,
                    max_entries=256,
                    max_tokens=1800,
                )
                candidate_capsule = self._contract_finalizer_capsule(
                    completed_finalizer,
                    workspace_revision=canonical_digest(workspace_manifest),
                )
                review_capsules = (*capsules, candidate_capsule)
                presentation_evidence_digest = canonical_digest(
                    {
                        "capsules": [item.to_dict() for item in review_capsules],
                        "workspace_manifest": workspace_manifest,
                    }
                )
                candidate_sha256 = hashlib.sha256(
                    completed_finalizer.candidate_output.encode("utf-8")
                ).hexdigest()
                presentation_review = presentation_reviews.get(
                    (
                        completed_finalizer.atom_id,
                        candidate_sha256,
                        presentation_evidence_digest,
                    )
                )
                if presentation_review is None:
                    if (
                        self._lifecycle_budget_count(
                            state,
                            event_type="contract_final_presentation_review_committed",
                            bounded_total=len(presentation_reviews),
                        )
                        >= self.supervisor_policy.max_reviewer_rounds
                    ):
                        return self._interrupt_contract_graph(
                            state,
                            reason="contract_final_presentation_reviewer_budget_exhausted",
                            transitions=transitions,
                        )
                    boundary = self._issue_contract_presentation_review(
                        state,
                        presentation_obligations,
                        nodes,
                        patches,
                        review_capsules,
                        completed_finalizer,
                        workspace_manifest=workspace_manifest,
                        evidence_digest=presentation_evidence_digest,
                        transitions=transitions,
                    )
                    if boundary is not None:
                        return boundary
                    continue
                if self._contract_all_phase_satisfied(
                    presentation_obligations,
                    presentation_review,
                ):
                    return self._complete_contract_finalizer(
                        state,
                        completed_finalizer,
                        nodes,
                        current_review,
                        transitions,
                        presentation_review=presentation_review,
                    )
                failed_presentation_review = presentation_review
                failed_presentation_capsules = review_capsules

            if not patches:
                if self._lifecycle_budget_count(
                    state,
                    event_type="contract_graph_patch_committed",
                    bounded_total=len(patches),
                ) >= self.supervisor_policy.max_graph_patches:
                    return self._interrupt_contract_graph(
                        state,
                        reason="contract_graph_patch_budget_exhausted",
                        transitions=transitions,
                    )
                boundary = self._issue_contract_patch(
                    state,
                    obligations,
                    nodes,
                    outcomes,
                    patches,
                    reviews,
                    capsules,
                    finalizer_required=False,
                    transitions=transitions,
                )
                if boundary is not None:
                    return boundary
                continue

            ready = self._contract_ready_nodes(
                nodes,
                outcomes,
                allow_finalizer=all_satisfied,
            )
            if ready:
                selected = self._select_contract_batch(ready)
                stage = self._create_contract_batch(
                    state,
                    selected,
                    batches,
                    graph_revision=len(patches),
                )
                self._persist(
                    state,
                    "contract_graph_batch_committed",
                    {
                        "stage_id": stage.stage_id,
                        "stage_index": stage.stage_index,
                        "batch": stage.to_dict(),
                        "graph_revision": len(patches),
                        "scheduler": "deterministic_scope_ready_set.v1",
                        "rwkv_action_authority": True,
                        "supervisor_action_executed": False,
                    },
                    subject_id=stage.stage_id,
                )
                continue

            if current_review is None:
                if self._lifecycle_budget_count(
                    state,
                    event_type="contract_graph_review_committed",
                    bounded_total=len(reviews),
                ) >= self.supervisor_policy.max_reviewer_rounds:
                    return self._interrupt_contract_graph(
                        state,
                        reason="contract_graph_reviewer_budget_exhausted",
                        transitions=transitions,
                    )
                boundary = self._issue_contract_review(
                    state,
                    obligations,
                    nodes,
                    patches,
                    reviews,
                    capsules,
                    evidence_digest=evidence_digest,
                    transitions=transitions,
                )
                if boundary is not None:
                    return boundary
                continue

            if (
                current_review_record is not None
                and current_review_record[2] > 0
                and self._lifecycle_budget_count(
                    state,
                    event_type="contract_graph_review_committed",
                    bounded_total=current_review_record[2],
                )
                >= self.supervisor_policy.max_graph_stagnant_rounds
            ):
                return self._interrupt_contract_graph(
                    state,
                    reason="contract_graph_evidence_stagnant",
                    transitions=transitions,
                )

            eligible_finalizers = self._contract_ready_nodes(
                nodes,
                outcomes,
                allow_finalizer=True,
                finalizers_only=True,
            )
            finalizer_required = all_satisfied and not eligible_finalizers
            if self._lifecycle_budget_count(
                state,
                event_type="contract_graph_patch_committed",
                bounded_total=len(patches),
            ) >= self.supervisor_policy.max_graph_patches:
                return self._interrupt_contract_graph(
                    state,
                    reason="contract_graph_patch_budget_exhausted",
                    transitions=transitions,
                )
            boundary = self._issue_contract_patch(
                state,
                obligations,
                nodes,
                outcomes,
                patches,
                reviews,
                capsules,
                finalizer_required=finalizer_required,
                transitions=transitions,
                planning_review=failed_presentation_review,
                planning_capsules=failed_presentation_capsules,
            )
            if boundary is not None:
                return boundary

    def _committed_contract_graph(
        self,
        state: RunState,
    ) -> tuple[
        dict[str, ContractObligation],
        dict[str, ContractGraphNode],
        list[ContractGraphPatch],
        list[tuple[ContractGraphReview, str, int]],
    ]:
        obligations: dict[str, ContractObligation] = {}
        nodes: dict[str, ContractGraphNode] = {}
        patches: list[ContractGraphPatch] = []
        reviews: list[tuple[ContractGraphReview, str, int]] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type == "contract_graph_patch_committed":
                value = event.payload.get("patch")
                if not isinstance(value, Mapping):
                    raise ValueError("committed contract graph patch is incomplete")
                patch = ContractGraphPatch.from_dict(
                    value,
                    immutable_request=state.goal.request,
                    request_digest=state.goal.digest,
                    existing_obligation_ids=tuple(obligations),
                    existing_node_ids=tuple(nodes),
                )
                if patch.base_revision != len(patches):
                    raise ValueError("contract graph patch revisions are not contiguous")
                for obligation in patch.new_obligations:
                    obligations[obligation.obligation_id] = obligation
                for node in patch.new_nodes:
                    nodes[node.node_id] = node
                patches.append(patch)
            elif event.event_type == "contract_graph_review_committed":
                value = event.payload.get("review")
                if not isinstance(value, Mapping):
                    raise ValueError("committed contract graph review is incomplete")
                evidence_ids = tuple(
                    str(item) for item in event.payload.get("evidence_ids") or ()
                )
                review = ContractGraphReview.from_dict(
                    value,
                    obligation_ids=tuple(
                        obligation_id
                        for obligation_id, obligation in obligations.items()
                        if obligation.phase == ObligationPhase.EXECUTION_EVIDENCE
                    ),
                    evidence_ids=evidence_ids,
                )
                if review.graph_revision != len(patches):
                    raise ValueError("contract review changed the graph revision")
                reviews.append(
                    (
                        review,
                        str(event.payload.get("evidence_digest") or ""),
                        int(event.payload.get("stagnant_rounds", 0) or 0),
                    )
                )
        return obligations, nodes, patches, reviews

    @staticmethod
    def _committed_contract_presentation_reviews(
        state: RunState,
        obligations: Mapping[str, ContractObligation],
    ) -> dict[tuple[str, str, str], ContractGraphReview]:
        """Restore content-addressed reviews of exact RWKV final candidates."""

        obligation_ids = tuple(obligations)
        reviews: dict[tuple[str, str, str], ContractGraphReview] = {}
        if not obligation_ids:
            return reviews
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "contract_final_presentation_review_committed":
                continue
            value = event.payload.get("review")
            if not isinstance(value, Mapping):
                raise ValueError("committed final-presentation review is incomplete")
            evidence_ids = tuple(
                str(item) for item in event.payload.get("evidence_ids") or ()
            )
            review = ContractGraphReview.from_dict(
                value,
                obligation_ids=obligation_ids,
                evidence_ids=evidence_ids,
            )
            candidate_atom_id = str(
                event.payload.get("candidate_atom_id") or ""
            )
            candidate_sha256 = str(
                event.payload.get("candidate_output_sha256") or ""
            )
            evidence_digest = str(event.payload.get("evidence_digest") or "")
            if (
                not candidate_atom_id
                or len(candidate_sha256) != 64
                or len(evidence_digest) != 64
            ):
                raise ValueError(
                    "committed final-presentation review has invalid identity"
                )
            reviews[(candidate_atom_id, candidate_sha256, evidence_digest)] = review
        return reviews

    @staticmethod
    def _committed_contract_batches(
        state: RunState,
    ) -> list[ContractExecutionBatch]:
        batches: list[ContractExecutionBatch] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "contract_graph_batch_committed":
                continue
            value = event.payload.get("batch")
            if isinstance(value, Mapping):
                stage = ContractExecutionBatch.restore(value)
            else:
                # Resume Round149-Round162 histories without retaining the old
                # SupervisorStage dependency in newly committed batches.
                legacy = event.payload.get("stage")
                if not isinstance(legacy, Mapping):
                    raise ValueError("committed contract graph batch is incomplete")
                old_stage = SupervisorStage.restore(
                    legacy,
                    immutable_request=state.goal.request,
                )
                stage = ContractExecutionBatch.from_legacy_stage(
                    stage_id=old_stage.stage_id,
                    stage_index=old_stage.stage_index,
                    graph_revision=int(event.payload.get("graph_revision", 0) or 0),
                    node_ids=tuple(atom.atom_id for atom in old_stage.atoms),
                    request_digest=old_stage.request_digest,
                )
            if stage.stage_index != len(batches) + 1:
                raise ValueError("contract graph batch indexes are not contiguous")
            if stage.request_digest != state.goal.digest:
                raise ValueError("contract graph batch changed the request digest")
            batches.append(stage)
        return batches

    def _contract_result_capsules(
        self,
        state: RunState,
        nodes: Mapping[str, ContractGraphNode],
        outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> tuple[ResultCapsule, ...]:
        capsules: list[ResultCapsule] = []
        network_attempts: list[dict[str, Any]] = []
        for node_id, node in nodes.items():
            outcome = outcomes.get(node_id)
            if outcome is None or node.atom.role == AtomRole.FINALIZER:
                continue
            expected_contract = AtomExecutionContract.create(
                immutable_request=state.goal.request,
                atom=node.atom,
            )
            if outcome.contract_digest != expected_contract.contract_digest:
                raise ValueError(
                    "committed atom outcome differs from its graph execution contract"
                )
            artifact_records = tuple(
                {
                    "_action_id": str(item.get("action_id") or ""),
                    "path": str(item.get("path") or ""),
                    "sha256": str(item.get("sha256") or ""),
                    "size_bytes": int(item.get("size_bytes", 0) or 0),
                    "media_type": str(item.get("media_type") or ""),
                }
                for item in outcome.artifacts
            )
            artifacts = tuple(
                {key: value for key, value in item.items() if key != "_action_id"}
                for item in artifact_records
            )
            revision = canonical_digest(
                [
                    {
                        "path": item["path"],
                        "sha256": item["sha256"],
                        "size_bytes": item["size_bytes"],
                    }
                    for item in artifacts
                ]
            )
            if outcome.actions:
                for action in outcome.actions:
                    durable_result = dict(action.get("result") or {})
                    model_result = self._model_action_result(
                        durable_result,
                        arguments=(
                            action.get("arguments")
                            if isinstance(action.get("arguments"), Mapping)
                            else {}
                        ),
                    )
                    model_result["durable_result_digest"] = canonical_digest(
                        durable_result
                    )
                    model_result["durable_result_persisted"] = True
                    result = self._bounded_contract_result(model_result)
                    action_id = str(action.get("action_id") or "terminal")
                    operation = str(action.get("operation") or "")
                    definition = self.harness.definition(operation)
                    if definition.network_access != "none":
                        metadata = result.get("metadata")
                        policy = (
                            metadata.get("network_policy")
                            if isinstance(metadata, Mapping)
                            and isinstance(metadata.get("network_policy"), Mapping)
                            else {}
                        )
                        allowed = bool(policy.get("allowed"))
                        network_attempts.append(
                            {
                                "action_id": action_id,
                                "operation": operation,
                                "network_access": definition.network_access,
                                "outcome_type": str(
                                    result.get("outcome_type") or ""
                                ),
                                "policy_allowed": allowed,
                                "policy_reason": str(policy.get("reason") or ""),
                                # The registered network handler calls its backend
                                # only after this immutable authorization decision.
                                "backend_invoked": allowed,
                            }
                        )
                    selected_records = tuple(
                        item
                        for item in artifact_records
                        if item["_action_id"] == action_id
                    )
                    # Legacy single-action records without action_id remain
                    # unambiguous.  They cannot be attached to every action in
                    # a multi-action transaction.
                    if len(outcome.actions) == 1:
                        selected_records += tuple(
                            item for item in artifact_records if not item["_action_id"]
                        )
                    selected_artifacts = tuple(
                        {
                            key: value
                            for key, value in item.items()
                            if key != "_action_id"
                        }
                        for item in selected_records
                    )
                    capsules.append(
                        ResultCapsule.create(
                            node_id=node_id,
                            observation_id=action_id,
                            node_status=outcome.status.value,
                            operation=operation,
                            result=result,
                            artifacts=selected_artifacts,
                            workspace_revision=revision,
                            error_type=(
                                ""
                                if outcome.status == AtomExecutionStatus.COMPLETED
                                else f"RWKVAtom{outcome.status.value.title()}"
                            ),
                            error_message=outcome.error,
                        )
                    )
            else:
                capsules.append(
                    ResultCapsule.create(
                        node_id=node_id,
                        observation_id="terminal",
                        node_status=outcome.status.value,
                        operation=node.atom.allowed_operations[0],
                        result={
                            "success": False,
                            "terminal_without_operation_result": True,
                        },
                        artifacts=artifacts,
                        workspace_revision=revision,
                        error_type=f"RWKVAtom{outcome.status.value.title()}",
                    error_message=outcome.error,
                )
            )
        network_capabilities = sorted(
            str(item["name"])
            for item in self.harness.g1i_tool_definitions()
            if self.harness.definition(str(item["name"])).network_access != "none"
        )
        if network_capabilities:
            audit_result = {
                "success": True,
                "fact_type": "controller_network_audit",
                "authority": "committed_atom_operation_results",
                "network_capabilities": network_capabilities,
                "network_action_count": len(network_attempts),
                "network_backend_invocation_count": sum(
                    bool(item["backend_invoked"]) for item in network_attempts
                ),
                "network_policy_rejection_count": sum(
                    item["outcome_type"] == "policy_rejected"
                    for item in network_attempts
                ),
                "no_network_action_attempted": not network_attempts,
                "no_network_backend_invoked": not any(
                    bool(item["backend_invoked"]) for item in network_attempts
                ),
                "attempts": network_attempts,
            }
            audit_digest = canonical_digest(audit_result)
            capsules.append(
                ResultCapsule.create(
                    node_id="SYSTEM.network-audit",
                    observation_id=f"audit-{audit_digest[:20]}",
                    node_status="completed",
                    operation="network_audit",
                    result=audit_result,
                    artifacts=(),
                    # Review events do not change executed network facts. Keeping
                    # this identity content-addressed lets the next loop consume
                    # the just-committed review instead of invalidating it merely
                    # because the review itself appended one causal event.
                    workspace_revision=f"network-audit-{audit_digest[:20]}",
                )
            )
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "replan_applied":
                continue
            payload = event.payload
            patch_id = str(payload.get("patch_id") or "")
            if not patch_id:
                continue
            capsules.append(
                ResultCapsule.create(
                    node_id=patch_id,
                    observation_id=event.event_id,
                    node_status="completed",
                    operation="replan_applied",
                    result={
                        "success": True,
                        "fact_type": "replan_applied",
                        "from_graph_revision": int(
                            payload.get("from_graph_revision", 0) or 0
                        ),
                        "to_graph_revision": int(
                            payload.get("to_graph_revision", 0) or 0
                        ),
                        "patch_id": patch_id,
                        "review_id": str(payload.get("review_id") or ""),
                        "unsatisfied_obligation_ids": list(
                            payload.get("unsatisfied_obligation_ids") or ()
                        ),
                        "correction_node_ids": list(
                            payload.get("correction_node_ids") or ()
                        ),
                    },
                    artifacts=(),
                    workspace_revision=(
                        f"graph-{int(payload.get('to_graph_revision', 0) or 0)}"
                    ),
                )
            )
        return self._latest_contract_result_capsules(tuple(capsules))

    @staticmethod
    def _contract_finalizer_capsule(
        outcome: AtomExecutionOutcome,
        *,
        workspace_revision: str,
    ) -> ResultCapsule:
        output_sha256 = hashlib.sha256(
            outcome.candidate_output.encode("utf-8")
        ).hexdigest()
        return ResultCapsule.create(
            node_id=outcome.atom_id,
            observation_id="final-candidate",
            node_status="completed",
            operation="final_answer",
            result={
                "success": True,
                "output": outcome.candidate_output,
                "output_sha256": output_sha256,
                "controller_rewritten": False,
            },
            artifacts=outcome.artifacts,
            workspace_revision=workspace_revision,
        )

    @staticmethod
    def _latest_contract_result_capsules(
        capsules: tuple[ResultCapsule, ...],
    ) -> tuple[ResultCapsule, ...]:
        """Select independent latest content, identity, command, and fact views."""

        # A path has independent content and identity observations: a
        # digest/check result cannot overwrite file contents, while a mutation
        # invalidates stale content until the target is read again.
        latest: dict[tuple[str, str], tuple[int, ResultCapsule]] = {}
        first_mutation: dict[str, int] = {}
        for index, capsule in enumerate(capsules):
            if capsule.operation not in PATH_MUTATION_OPERATIONS:
                continue
            for artifact in capsule.artifacts:
                path = str(artifact.get("path") or "")
                if path:
                    first_mutation[path] = min(first_mutation.get(path, index), index)

        # A preservation contract needs the last complete value before the
        # first committed mutation. Keep it as a distinct fact view: it can be
        # compared with current content but can never masquerade as current.
        baseline_candidates: dict[str, tuple[int, ResultCapsule]] = {}
        for index, capsule in enumerate(capsules):
            if capsule.operation not in _CONTENT_OBSERVATION_OPERATIONS:
                continue
            for artifact in capsule.artifacts:
                path = str(artifact.get("path") or "")
                if path and index < first_mutation.get(path, -1):
                    baseline_candidates[path] = (index, capsule)
        for path, (index, source) in baseline_candidates.items():
            artifacts = tuple(
                dict(item)
                for item in source.artifacts
                if str(item.get("path") or "") == path
            )
            baseline = ResultCapsule.create(
                node_id=(
                    "SYSTEM.pre-mutation."
                    + hashlib.sha256(path.encode("utf-8")).hexdigest()[:12]
                ),
                observation_id=f"baseline-{source.observation_id}",
                node_status="completed",
                operation="pre_mutation_snapshot",
                result={
                    **dict(source.result),
                    "fact_type": "pre_mutation_snapshot",
                    "snapshot_of": path,
                    "source_evidence_id": source.evidence_id,
                },
                artifacts=artifacts,
                workspace_revision=source.workspace_revision,
            )
            latest[("baseline_content", path)] = (index, baseline)
        for index, capsule in enumerate(capsules):
            paths = tuple(
                str(item.get("path") or "")
                for item in capsule.artifacts
                if str(item.get("path") or "")
            )
            keys: list[tuple[str, str]] = []
            for path in paths:
                keys.append(("identity", path))
                if capsule.operation in _CONTENT_OBSERVATION_OPERATIONS:
                    keys.append(("content", path))
                elif capsule.operation in PATH_MUTATION_OPERATIONS:
                    # Mutation results are content tombstones, not file text.
                    keys.append(("content", path))
            if capsule.operation in _COMMAND_OBSERVATION_OPERATIONS or (
                capsule.result.get("exit_code") is not None
            ):
                keys.append(("command", capsule.operation))
            if not keys:
                fact_type = str(capsule.result.get("fact_type") or capsule.operation)
                keys.append(("fact", fact_type))
            for key in keys:
                latest[key] = (index, capsule)
        selected = {
            capsule.evidence_id: (index, capsule)
            for index, capsule in latest.values()
        }
        return tuple(
            capsule
            for _, capsule in sorted(selected.values(), key=lambda item: item[0])
        )

    @staticmethod
    def _bounded_contract_result(result: Mapping[str, Any]) -> dict[str, Any]:
        selected = dict(result)
        output = str(selected.get("output") or "")
        if len(output) > 8000:
            selected["output"] = output[:8000]
            raw_metadata = selected.get("metadata")
            metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
            metadata["source_complete"] = metadata.get("complete", True)
            metadata["complete"] = False
            metadata["projection_complete"] = False
            selected["metadata"] = metadata
            selected["output_projection"] = {
                "truncated": True,
                "original_chars": len(output),
                "retained_chars": 8000,
                "full_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            }
        encoded = json.dumps(
            selected,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(encoded) <= 18_000:
            return selected
        return {
            "success": bool(selected.get("success")),
            "action_type": str(selected.get("action_type") or ""),
            "exit_code": selected.get("exit_code"),
            "error": dict(selected.get("error") or {}),
            "metadata": {
                "complete": False,
                "projection_complete": False,
            },
            "result_projection": {
                "truncated": True,
                "original_chars": len(encoded),
                "full_sha256": hashlib.sha256(encoded.encode("utf-8")).hexdigest(),
            },
        }

    @staticmethod
    def _json_pointer(value: Any, pointer: str) -> tuple[bool, Any]:
        if not pointer:
            return True, value
        current = value
        for raw in pointer.lstrip("/").split("/"):
            token = raw.replace("~1", "/").replace("~0", "~")
            if isinstance(current, Mapping) and token in current:
                current = current[token]
                continue
            if isinstance(current, list) and token.isdigit():
                index = int(token)
                if 0 <= index < len(current):
                    current = current[index]
                    continue
            return False, None
        return True, current

    @staticmethod
    def _match_unordered_template_rows(
        text: str,
        rendered: list[str],
        *,
        max_search_states: int = 100_000,
    ) -> bool | None:
        """Find a quantity-preserving non-overlapping assignment for all rows."""

        if any(not item for item in rendered):
            return False
        if not rendered:
            return True
        counts = Counter(rendered)
        patterns = tuple(sorted(counts))
        candidates: tuple[tuple[tuple[int, int], ...], ...] = tuple(
            tuple(
                (position, position + len(pattern))
                for position in (
                    match.start()
                    for match in re.finditer(
                        f"(?={re.escape(pattern)})",
                        text,
                    )
                )
            )
            for pattern in patterns
        )
        required = tuple(counts[pattern] for pattern in patterns)
        if any(
            len(candidates[index]) < required[index]
            for index in range(len(patterns))
        ):
            return False

        memo: set[
            tuple[
                tuple[int, ...],
                tuple[int, ...],
                tuple[tuple[int, int], ...],
            ]
        ] = set()
        visited_states = 0
        exhausted = False

        def available_intervals(
            group_index: int,
            next_candidate: tuple[int, ...],
            occupied: tuple[tuple[int, int], ...],
        ) -> tuple[tuple[int, tuple[int, int]], ...]:
            return tuple(
                (candidate_index, interval)
                for candidate_index, interval in enumerate(candidates[group_index])
                if candidate_index >= next_candidate[group_index]
                and not any(
                    interval[0] < end and interval[1] > start
                    for start, end in occupied
                )
            )

        def search(
            remaining: tuple[int, ...],
            next_candidate: tuple[int, ...],
            occupied: tuple[tuple[int, int], ...],
        ) -> bool:
            nonlocal visited_states, exhausted
            if exhausted:
                return False
            if not any(remaining):
                return True
            visited_states += 1
            if visited_states > max_search_states:
                exhausted = True
                return False
            state_key = (remaining, next_candidate, occupied)
            if state_key in memo:
                return False

            selected_group = -1
            selected_available: tuple[tuple[int, tuple[int, int]], ...] = ()
            selected_score: tuple[int, int, int, str] | None = None
            for group_index, needed in enumerate(remaining):
                if needed == 0:
                    continue
                available = available_intervals(
                    group_index,
                    next_candidate,
                    occupied,
                )
                if len(available) < needed:
                    memo.add(state_key)
                    return False
                score = (
                    len(available) - needed,
                    len(available),
                    -len(patterns[group_index]),
                    patterns[group_index],
                )
                if selected_score is None or score < selected_score:
                    selected_group = group_index
                    selected_available = available
                    selected_score = score

            for candidate_index, interval in selected_available:
                updated_remaining = list(remaining)
                updated_remaining[selected_group] -= 1
                updated_next = list(next_candidate)
                updated_next[selected_group] = candidate_index + 1
                updated_occupied = tuple(sorted((*occupied, interval)))
                if search(
                    tuple(updated_remaining),
                    tuple(updated_next),
                    updated_occupied,
                ):
                    return True
            memo.add(state_key)
            return False

        matched = search(
            required,
            tuple(0 for _ in patterns),
            (),
        )
        if exhausted and not matched:
            return None
        return matched

    @classmethod
    def _evaluate_typed_assertion(
        cls,
        assertion: ContractAssertion,
        capsules: tuple[ResultCapsule, ...],
    ) -> tuple[bool | None, tuple[str, ...], str]:
        semantic_issue = assertion.local_evaluation_issue()
        if semantic_issue:
            return None, (), f"semantic exception: {semantic_issue}"

        texts: dict[str, tuple[str, str]] = {}
        parsed: dict[str, tuple[Any, str]] = {}
        baseline_texts: dict[str, tuple[str, str]] = {}
        baseline_parsed: dict[str, tuple[Any, str]] = {}
        digests: dict[str, tuple[str, str]] = {}
        successful: list[ResultCapsule] = []
        for capsule in capsules:
            if capsule.node_status != "completed" or not bool(
                capsule.result.get("success")
            ):
                continue
            successful.append(capsule)
            output = capsule.result.get("output")
            metadata = capsule.result.get("metadata")
            complete = not isinstance(metadata, Mapping) or metadata.get("complete") is not False
            for artifact in capsule.artifacts:
                path = str(artifact.get("path") or "")
                if not path:
                    continue
                sha256 = str(artifact.get("sha256") or "")
                if sha256:
                    digests[path] = (sha256, capsule.evidence_id)
                if (
                    capsule.operation in _CONTENT_OBSERVATION_OPERATIONS
                    and isinstance(output, str)
                    and complete
                ):
                    texts[path] = (output, capsule.evidence_id)
                    try:
                        parsed[path] = (json.loads(output), capsule.evidence_id)
                    except json.JSONDecodeError:
                        pass
                elif (
                    capsule.operation == "pre_mutation_snapshot"
                    and isinstance(output, str)
                    and complete
                ):
                    baseline_texts[path] = (output, capsule.evidence_id)
                    try:
                        baseline_parsed[path] = (
                            json.loads(output),
                            capsule.evidence_id,
                        )
                    except json.JSONDecodeError:
                        pass

        refs: list[str] = []

        def document(path: str, pointer: str) -> tuple[bool, Any]:
            if path not in parsed:
                return False, None
            value, evidence_id = parsed[path]
            found, selected = cls._json_pointer(value, pointer)
            if found:
                refs.append(evidence_id)
            return found, selected

        def baseline_document(path: str, pointer: str) -> tuple[bool, Any]:
            if path not in baseline_parsed:
                return False, None
            value, evidence_id = baseline_parsed[path]
            found, selected = cls._json_pointer(value, pointer)
            if found:
                refs.append(evidence_id)
            return found, selected

        def without_pointer(value: Any, pointer: str) -> tuple[bool, Any]:
            selected = deepcopy(value)
            tokens = [
                raw.replace("~1", "/").replace("~0", "~")
                for raw in pointer.lstrip("/").split("/")
                if raw
            ]
            if not tokens:
                return False, selected
            parent = selected
            for token in tokens[:-1]:
                if isinstance(parent, Mapping) and token in parent:
                    parent = parent[token]
                elif (
                    isinstance(parent, list)
                    and token.isdigit()
                    and 0 <= int(token) < len(parent)
                ):
                    parent = parent[int(token)]
                else:
                    return False, selected
            leaf = tokens[-1]
            if isinstance(parent, dict) and leaf in parent:
                del parent[leaf]
                return True, selected
            if (
                isinstance(parent, list)
                and leaf.isdigit()
                and 0 <= int(leaf) < len(parent)
            ):
                del parent[int(leaf)]
                return True, selected
            return False, selected

        def source_values() -> tuple[bool, list[Any]]:
            values: list[Any] = []
            for source in assertion.sources:
                if source.pointer:
                    found, value = document(source.path, source.pointer)
                elif source.path in parsed:
                    value, evidence_id = parsed[source.path]
                    refs.append(evidence_id)
                    found = True
                elif source.path in texts:
                    value, evidence_id = texts[source.path]
                    refs.append(evidence_id)
                    found = True
                else:
                    found, value = False, None
                if not found:
                    return False, []
                values.append(value)
            return True, values

        kind = assertion.kind
        target_text = texts.get(assertion.target_path)
        if kind == ContractAssertionKind.ARTIFACT_EXISTS:
            evidence = texts.get(assertion.target_path) or digests.get(assertion.target_path)
            return (
                (True, (evidence[1],), "target artifact is present")
                if evidence
                else (None, (), "target artifact has no public observation")
            )
        if kind in {
            ContractAssertionKind.TEXT_EXACT,
            ContractAssertionKind.TEXT_CONTAINS,
            ContractAssertionKind.TEXT_EXCLUDES,
            ContractAssertionKind.TEXT_TEMPLATE,
            ContractAssertionKind.TEXT_REMOVE_ONLY,
            ContractAssertionKind.TRAILING_NEWLINE,
        }:
            if target_text is None:
                return None, (), "target text has no complete public observation"
            text, evidence_id = target_text
            refs.append(evidence_id)
            if kind == ContractAssertionKind.TEXT_EXACT:
                passed = text == assertion.expected
            elif kind == ContractAssertionKind.TEXT_CONTAINS:
                passed = assertion.expected in text
            elif kind == ContractAssertionKind.TEXT_EXCLUDES:
                passed = assertion.expected not in text
            elif kind == ContractAssertionKind.TRAILING_NEWLINE:
                wanted = assertion.expected.strip().casefold() not in {"false", "0", "no"}
                passed = text.endswith("\n") == wanted
            elif kind == ContractAssertionKind.TEXT_REMOVE_ONLY:
                source = assertion.sources[0]
                baseline = baseline_texts.get(source.path)
                if baseline is None:
                    return None, tuple(dict.fromkeys(refs)), "baseline text is unresolved"
                original, baseline_evidence_id = baseline
                refs.append(baseline_evidence_id)
                needle = assertion.expected
                if original.count(needle + "\r\n") == 1:
                    expected_text = original.replace(needle + "\r\n", "", 1)
                elif original.count(needle + "\n") == 1:
                    expected_text = original.replace(needle + "\n", "", 1)
                elif original.count(needle) == 1:
                    expected_text = original.replace(needle, "", 1)
                else:
                    return False, tuple(dict.fromkeys(refs)), (
                        "removed text is absent or ambiguous in the baseline"
                    )
                passed = text == expected_text
            else:
                found, values = source_values()
                if not found:
                    return None, tuple(dict.fromkeys(refs)), "template sources are unresolved"
                try:
                    if len(values) == 1 and isinstance(values[0], list) and all(
                        isinstance(item, Mapping) for item in values[0]
                    ):
                        expected_rows = list(values[0])
                        if assertion.order:
                            sort_key = assertion.keys[0]
                            if any(sort_key not in item for item in expected_rows):
                                return None, tuple(dict.fromkeys(refs)), (
                                    "template sort key is unresolved"
                                )
                            expected_rows = sorted(
                                expected_rows,
                                key=lambda item: item[sort_key],
                                reverse=assertion.order == "descending",
                            )
                        rendered = [
                            assertion.expected.format_map(dict(item))
                            for item in expected_rows
                        ]
                        if assertion.order:
                            passed = all(rendered)
                            cursor = 0
                            for item in rendered:
                                if not passed:
                                    break
                                position = text.find(item, cursor)
                                if position < 0:
                                    passed = False
                                    break
                                cursor = position + len(item)
                        else:
                            matched = cls._match_unordered_template_rows(
                                text,
                                rendered,
                            )
                            if matched is None:
                                return None, tuple(dict.fromkeys(refs)), (
                                    "template match search exceeded its deterministic bound"
                                )
                            passed = matched
                    else:
                        if assertion.order:
                            return None, tuple(dict.fromkeys(refs)), (
                                "ordered text_template source is not an object list"
                            )
                        rendered_value = assertion.expected.format(*values)
                        passed = rendered_value in text
                except (KeyError, IndexError, ValueError, TypeError):
                    return None, tuple(dict.fromkeys(refs)), "typed template could not be rendered"
            return passed, tuple(dict.fromkeys(refs)), (
                "typed text relation passed" if passed else "typed text relation failed"
            )

        found_target, target = document(assertion.target_path, assertion.target_pointer)
        if kind == ContractAssertionKind.COMMAND_SUCCEEDED:
            expected_operation = (
                "" if assertion.expected.strip() in {"", "0"} else assertion.expected
            )
            command_candidates = [
                item
                for item in capsules
                if (
                    item.operation == expected_operation
                    if expected_operation
                    else item.operation in {"run_command", "check_command", "mock_api"}
                    or item.result.get("exit_code") is not None
                )
            ]
            matching = [
                item
                for item in command_candidates
                if item.node_status == "completed"
                and bool(item.result.get("success"))
                and item.result.get("exit_code") in {None, 0}
                and (not expected_operation or item.operation == expected_operation)
            ]
            if not matching:
                relevant = [
                    item
                    for item in command_candidates
                    if not expected_operation or item.operation == expected_operation
                ]
                if relevant:
                    return (
                        False,
                        tuple(item.evidence_id for item in relevant[-4:]),
                        "command result failed",
                    )
                return None, (), "command result is not publicly observed"
            return True, (matching[-1].evidence_id,), "command result succeeded"
        if kind == ContractAssertionKind.DIGEST_EQUAL:
            if assertion.target_pointer:
                if not found_target or not isinstance(target, str):
                    return (
                        None,
                        tuple(dict.fromkeys(refs)),
                        "target digest value is unresolved",
                    )
                target_digest_value = target.strip().casefold()
                if not re.fullmatch(r"[0-9a-f]{64}", target_digest_value):
                    return (
                        None,
                        tuple(dict.fromkeys(refs)),
                        "target value is not a SHA256 digest",
                    )
            else:
                target_digest = digests.get(assertion.target_path)
                if target_digest is None:
                    return None, (), "target digest is unresolved"
                refs.append(target_digest[1])
                target_digest_value = target_digest[0].casefold()
            if assertion.sources:
                source = assertion.sources[0]
                if source.pointer:
                    found, source_value = document(source.path, source.pointer)
                    if not found or not isinstance(source_value, str):
                        return None, tuple(dict.fromkeys(refs)), "source digest value is unresolved"
                    expected_digest = source_value.strip().casefold()
                    if not re.fullmatch(r"[0-9a-f]{64}", expected_digest):
                        return None, tuple(dict.fromkeys(refs)), "source value is not a SHA256 digest"
                    passed = target_digest_value == expected_digest
                else:
                    source_digest = digests.get(source.path)
                    if source_digest is None:
                        return None, tuple(refs), "source digest is unresolved"
                    refs.append(source_digest[1])
                    passed = target_digest_value == source_digest[0].casefold()
            else:
                passed = (
                    target_digest_value == assertion.expected.strip().casefold()
                )
            return passed, tuple(dict.fromkeys(refs)), (
                "digest relation passed" if passed else "digest relation failed"
            )
        if not found_target:
            return None, tuple(dict.fromkeys(refs)), "target JSON value is unresolved"
        try:
            expected: Any = json.loads(assertion.expected)
        except json.JSONDecodeError:
            expected = assertion.expected
        if kind == ContractAssertionKind.JSON_REQUIRED_KEYS:
            passed = isinstance(target, Mapping) and set(assertion.keys) <= set(target)
        elif kind == ContractAssertionKind.JSON_EXACT_KEYS:
            passed = isinstance(target, Mapping) and set(assertion.keys) == set(target)
        elif kind == ContractAssertionKind.JSON_VALUE_EQUALS:
            passed = target == expected
        elif kind in {
            ContractAssertionKind.JSON_VALUE_FROM_SOURCE,
            ContractAssertionKind.JSON_PRESERVE,
        }:
            source = assertion.sources[0]
            if (
                kind == ContractAssertionKind.JSON_PRESERVE
                and source.path == assertion.target_path
            ):
                found, source_value = baseline_document(source.path, source.pointer)
            else:
                found, values = source_values()
                source_value = values[0] if found and values else None
            if not found:
                return None, tuple(dict.fromkeys(refs)), "source JSON value is unresolved"
            compared_target = target
            compared_source = source_value
            for pointer in assertion.keys:
                target_removed, compared_target = without_pointer(
                    compared_target, pointer
                )
                source_removed, compared_source = without_pointer(
                    compared_source, pointer
                )
                if not target_removed or not source_removed:
                    return False, tuple(dict.fromkeys(refs)), (
                        "preservation exception pointer is unresolved"
                    )
            passed = compared_target == compared_source
        elif kind == ContractAssertionKind.SEQUENCE_SORTED:
            if not isinstance(target, list):
                passed = False
            else:
                key = assertion.keys[0] if assertion.keys else ""
                try:
                    projected = [
                        item.get(key) if key and isinstance(item, Mapping) else item
                        for item in target
                    ]
                    passed = projected == sorted(
                        projected, reverse=assertion.order == "descending"
                    )
                except TypeError:
                    passed = False
        elif kind == ContractAssertionKind.NUMERIC_AGGREGATE:
            found, values = source_values()
            if not found:
                return None, tuple(dict.fromkeys(refs)), "aggregate sources are unresolved"
            flat = values[0] if len(values) == 1 and isinstance(values[0], list) else values
            if assertion.algorithm == "count":
                calculated = len(flat)
            elif not all(isinstance(item, (int, float)) and not isinstance(item, bool) for item in flat):
                return None, tuple(dict.fromkeys(refs)), "aggregate sources are not numeric"
            elif assertion.algorithm == "sum":
                calculated = sum(flat)
            elif assertion.algorithm == "minimum":
                if not flat:
                    return None, tuple(dict.fromkeys(refs)), (
                        "aggregate source collection is empty"
                    )
                calculated = min(flat)
            elif assertion.algorithm == "maximum":
                if not flat:
                    return None, tuple(dict.fromkeys(refs)), (
                        "aggregate source collection is empty"
                    )
                calculated = max(flat)
            else:
                return None, tuple(dict.fromkeys(refs)), "aggregate algorithm is unresolved"
            passed = target == calculated
        else:
            return None, tuple(dict.fromkeys(refs)), "assertion kind is not locally supported"
        return passed, tuple(dict.fromkeys(refs)), (
            "typed JSON relation passed" if passed else "typed JSON relation failed"
        )

    @classmethod
    def _evaluate_typed_contract(
        cls,
        obligations: Mapping[str, ContractObligation],
        capsules: tuple[ResultCapsule, ...],
    ) -> dict[str, ObligationVerdict]:
        verdicts: dict[str, ObligationVerdict] = {}
        for obligation in obligations.values():
            if not obligation.assertions:
                continue
            evaluations = [
                cls._evaluate_typed_assertion(assertion, capsules)
                for assertion in obligation.assertions
            ]
            if any(passed is None for passed, _, _ in evaluations):
                continue
            passed = all(bool(item[0]) for item in evaluations)
            refs = tuple(
                dict.fromkeys(
                    evidence_id
                    for _, evidence_refs, _ in evaluations
                    for evidence_id in evidence_refs
                )
            )[:32]
            verdicts[obligation.obligation_id] = ObligationVerdict.create(
                obligation_id=obligation.obligation_id,
                status="satisfied" if passed else "contradicted",
                evidence_refs=refs,
                reason=(
                    "All typed assertions passed deterministic public-result checks."
                    if passed
                    else "At least one typed assertion contradicted the public result: "
                    + "; ".join(reason for ok, _, reason in evaluations if not ok)[:1200]
                ),
            )
        return verdicts

    @staticmethod
    def _contract_all_required_satisfied(
        obligations: Mapping[str, ContractObligation],
        review: ContractGraphReview | None,
    ) -> bool:
        if review is None or not obligations:
            return False
        verdicts = {item.obligation_id: item for item in review.verdicts}
        execution_obligation_ids = tuple(
            obligation_id
            for obligation_id, obligation in obligations.items()
            if obligation.phase == ObligationPhase.EXECUTION_EVIDENCE
        )
        return bool(execution_obligation_ids) and all(
            obligation_id in verdicts
            and verdicts[obligation_id].status
            == ObligationVerdictStatus.SATISFIED
            for obligation_id in execution_obligation_ids
        )

    @staticmethod
    def _contract_all_phase_satisfied(
        obligations: Mapping[str, ContractObligation],
        review: ContractGraphReview | None,
    ) -> bool:
        if review is None or not obligations:
            return False
        verdicts = {item.obligation_id: item for item in review.verdicts}
        return all(
            obligation_id in verdicts
            and verdicts[obligation_id].status
            == ObligationVerdictStatus.SATISFIED
            for obligation_id in obligations
        )

    @staticmethod
    def _contract_ready_nodes(
        nodes: Mapping[str, ContractGraphNode],
        outcomes: Mapping[str, AtomExecutionOutcome],
        *,
        allow_finalizer: bool,
        finalizers_only: bool = False,
    ) -> list[ContractGraphNode]:
        completed = {
            node_id
            for node_id, outcome in outcomes.items()
            if outcome.status == AtomExecutionStatus.COMPLETED
        }
        completed_work = {
            node_id
            for node_id in completed
            if node_id in nodes and nodes[node_id].atom.role == AtomRole.WORK
        }
        ready: list[ContractGraphNode] = []
        for node_id, node in nodes.items():
            if node_id in outcomes:
                continue
            is_finalizer = node.atom.role == AtomRole.FINALIZER
            if finalizers_only and not is_finalizer:
                continue
            if not finalizers_only and is_finalizer and not allow_finalizer:
                continue
            if not set(node.atom.depends_on) <= completed:
                continue
            if is_finalizer and not completed_work <= set(node.atom.depends_on):
                # Correction work invalidates an older frozen finalizer.  A
                # replacement must receive every accepted child result handoff.
                continue
            ready.append(node)
        return ready

    def _select_contract_batch(
        self,
        ready: list[ContractGraphNode],
    ) -> tuple[ContractGraphNode, ...]:
        finalizers = [
            node for node in ready if node.atom.role == AtomRole.FINALIZER
        ]
        if finalizers:
            return (finalizers[-1],)
        selected: list[ContractGraphNode] = []
        for node in ready:
            if node.atom.exclusive:
                if not selected:
                    return (node,)
                continue
            conflicts = any(
                self._contract_scopes_overlap(
                    node.atom.write_roots,
                    prior.atom.write_roots,
                )
                for prior in selected
            )
            if conflicts:
                continue
            selected.append(node)
            if len(selected) >= self.supervisor_policy.max_parallel_atoms:
                break
        if not selected:
            raise ValueError("contract scheduler found no conflict-free ready node")
        return tuple(selected)

    @staticmethod
    def _contract_scopes_overlap(
        left_roots: tuple[str, ...],
        right_roots: tuple[str, ...],
    ) -> bool:
        return contract_scopes_overlap(left_roots, right_roots)

    def _create_contract_batch(
        self,
        state: RunState,
        selected: tuple[ContractGraphNode, ...],
        batches: list[ContractExecutionBatch],
        *,
        graph_revision: int,
    ) -> ContractExecutionBatch:
        return ContractExecutionBatch.create(
            request_digest=state.goal.digest,
            stage_index=len(batches) + 1,
            graph_revision=graph_revision,
            node_ids=tuple(node.node_id for node in selected),
        )

    def _contract_operation_catalog(
        self,
        goal: GoalState,
    ) -> tuple[Mapping[str, Any], ...]:
        catalog: list[Mapping[str, Any]] = []
        for item in self.harness.g1i_tool_definitions():
            name = str(item["name"])
            definition = self.harness.definition(name)
            if not operation_allowed_by_retrieval_policy(
                goal,
                network_access=definition.network_access,
            ):
                continue
            catalog.append(
                {
                    "name": name,
                    "description": str(item.get("description") or ""),
                    "scope_mode": (
                        "read_only"
                        if not definition.side_effect
                        else "path_mutation"
                        if name in PATH_MUTATION_OPERATIONS
                        else "exclusive_side_effect"
                    ),
                    "capability_class": definition.capability_class,
                    "network_access": definition.network_access,
                    "data_boundary": definition.data_boundary,
                    "side_effect_class": definition.side_effect_class,
                    "result_schema": definition.result_schema,
                    "evidence_output": definition.evidence_output,
                }
            )
        return tuple(catalog)

    @staticmethod
    def _validate_contract_patch_semantics(
        patch: ContractGraphPatch,
        *,
        existing_obligations: Mapping[str, ContractObligation],
        existing_nodes: Mapping[str, ContractGraphNode],
        operation_catalog: tuple[Mapping[str, Any], ...],
        capsules: tuple[ResultCapsule, ...],
        finalizer_required: bool,
        workspace_manifest: Mapping[str, Any],
        existing_node_statuses: Mapping[str, str],
    ) -> None:
        validate_contract_patch_semantics(
            patch,
            existing_obligations=existing_obligations,
            existing_nodes=existing_nodes,
            operation_catalog=operation_catalog,
            capsules=capsules,
            finalizer_required=finalizer_required,
            workspace_manifest=workspace_manifest,
            existing_node_statuses=existing_node_statuses,
        )

    @staticmethod
    def _contract_correction_signature(
        review: ContractGraphReview,
        capsules: tuple[ResultCapsule, ...],
    ) -> tuple[str, tuple[str, ...], str]:
        """Project a stable recovery state independent of correction node ids."""

        unresolved = tuple(
            sorted(
                item.obligation_id
                for item in review.verdicts
                if item.status != ObligationVerdictStatus.SATISFIED
            )
        )
        statuses = {
            item.obligation_id: item.status.value
            for item in review.verdicts
            if item.status != ObligationVerdictStatus.SATISFIED
        }
        if any(
            item.status == ObligationVerdictStatus.CONTRADICTED
            for item in review.verdicts
        ):
            recovery_class = "contract_contradiction"
        elif any(
            capsule.node_status in {"failed", "interrupted"}
            for capsule in capsules
            if capsule.operation != "replan_applied"
        ):
            recovery_class = "execution_failure"
        else:
            recovery_class = "evidence_insufficient"

        projection_by_digest: dict[str, Mapping[str, Any]] = {}
        for capsule in capsules:
            # A correction commit changes graph bookkeeping, not workspace or
            # executable evidence.  Including patch_id/revision made every
            # stagnant correction look new.
            if capsule.operation == "replan_applied":
                continue
            output = str(capsule.result.get("output") or "")
            expose_output = capsule.operation in (
                _CONTENT_OBSERVATION_OPERATIONS
                | _COMMAND_OBSERVATION_OPERATIONS
            )
            item = {
                "operation": capsule.operation,
                "status": capsule.node_status,
                "success": bool(capsule.result.get("success")),
                "artifacts": sorted(
                    (
                        str(artifact.get("path") or ""),
                        str(artifact.get("sha256") or ""),
                    )
                    for artifact in capsule.artifacts
                ),
                "output_sha256": (
                    hashlib.sha256(output.encode("utf-8")).hexdigest()
                    if expose_output and output
                    else ""
                ),
                "exit_code": capsule.result.get("exit_code"),
                "error_type": capsule.error_type,
            }
            projection_by_digest[canonical_digest(item)] = item
        projection = [
            projection_by_digest[key] for key in sorted(projection_by_digest)
        ]
        signature = canonical_digest(
            {
                "recovery_class": recovery_class,
                "unsatisfied": statuses,
                "latest_state": projection,
            }
        )
        return signature, unresolved, recovery_class

    def _issue_contract_patch(
        self,
        state: RunState,
        obligations: Mapping[str, ContractObligation],
        nodes: Mapping[str, ContractGraphNode],
        outcomes: Mapping[str, AtomExecutionOutcome],
        patches: list[ContractGraphPatch],
        reviews: list[tuple[ContractGraphReview, str, int]],
        capsules: tuple[ResultCapsule, ...],
        *,
        finalizer_required: bool,
        transitions: int,
        planning_review: ContractGraphReview | None = None,
        planning_capsules: tuple[ResultCapsule, ...] | None = None,
        node_statuses: Mapping[str, str] | None = None,
    ) -> ControllerResult | None:
        correction_signature = ""
        if patches and not finalizer_required and reviews:
            (
                correction_signature,
                unsatisfied,
                recovery_class,
            ) = self._contract_correction_signature(
                reviews[-1][0], capsules
            )
            committed_signatures = {
                str(state.causal_records[event_id].payload.get("signature") or "")
                for event_id in state.causal_order
                if state.causal_records[event_id].event_type
                == "contract_correction_signature_committed"
                and state.causal_records[event_id].sequence
                > self._goal_epoch_start_sequence(state)
            }
            if correction_signature in committed_signatures:
                self._persist(
                    state,
                    "contract_correction_duplicate_blocked",
                    {
                        "signature": correction_signature,
                        "unsatisfied_obligation_ids": unsatisfied,
                        "recovery_class": recovery_class,
                        "strategy": "safe_stop",
                    },
                )
                return self._interrupt_contract_graph(
                    state,
                    reason="contract_graph_correction_repeated",
                    transitions=transitions,
                )
        method = getattr(self.supervisor, "plan_contract_graph", None)
        if not callable(method):
            return self._contract_supervisor_failure(
                state,
                TypeError("supervisor has no contract graph planner"),
                phase="contract_plan",
                transitions=transitions,
            )
        workspace_manifest = self.harness.workspace_manifest(
            state.goal,
            max_entries=256,
            max_tokens=1800,
        )
        selected_review = (
            planning_review
            if planning_review is not None
            else (reviews[-1][0] if reviews else None)
        )
        selected_capsules = (
            planning_capsules
            if planning_capsules is not None
            else capsules
        )
        request = ContractPlanRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            graph_revision=len(patches),
            obligations=tuple(item.to_dict() for item in obligations.values()),
            nodes=tuple(item.to_dict() for item in nodes.values()),
            latest_review=(
                selected_review.to_dict()
                if selected_review is not None
                else None
            ),
            result_capsules=selected_capsules,
            available_operations=self._contract_operation_catalog(state.goal),
            workspace_manifest=workspace_manifest,
            node_statuses={
                node_id: str(
                    (node_statuses or {}).get(
                        node_id,
                        outcomes[node_id].status.value
                        if node_id in outcomes
                        else "pending",
                    )
                )
                for node_id in nodes
            },
            finalizer_required=finalizer_required,
        )
        try:
            returned = method(request)
            if not isinstance(returned, ContractGraphPatch):
                raise TypeError("supervisor returned an invalid contract graph patch")
            patch = ContractGraphPatch.from_dict(
                returned.to_dict(),
                immutable_request=state.goal.request,
                request_digest=state.goal.digest,
                existing_obligation_ids=tuple(obligations),
                existing_node_ids=tuple(nodes),
            )
            if patch.base_revision != len(patches):
                raise ValueError("contract planner returned a stale graph revision")
            operation_catalog = self._contract_operation_catalog(state.goal)
            self._validate_contract_patch_semantics(
                patch,
                existing_obligations=obligations,
                existing_nodes=nodes,
                operation_catalog=operation_catalog,
                capsules=selected_capsules,
                finalizer_required=finalizer_required,
                workspace_manifest=workspace_manifest,
                existing_node_statuses=request.node_statuses,
            )
            if len(nodes) + len(patch.new_nodes) > self.supervisor_policy.max_graph_atoms:
                raise ValueError("contract graph atom budget exceeded")
        except Exception as exc:
            return self._contract_supervisor_failure(
                state,
                exc,
                phase="contract_plan",
                transitions=transitions,
            )
        self._persist(
            state,
            "contract_graph_patch_committed",
            {
                "patch_id": patch.patch_id,
                "patch": patch.to_dict(),
                "graph_revision": len(patches) + 1,
                "request_digest": state.goal.digest,
                "supervisor": supervisor_identity(self.supervisor),
                "planner_can_accept": False,
                "supervisor_action_executed": False,
                "rwkv_action_authority": True,
                "operation_allowset_source": CAPABILITY_PROJECTION_VERSION,
                "strong_planner_concrete_operation_count": 0,
                "result_capsule_count": len(selected_capsules),
                "result_capsules_only": True,
            },
            subject_id=patch.patch_id,
        )
        self._persist_supervisor_resolved(state, phase="contract_plan")
        if correction_signature:
            self._persist(
                state,
                "contract_correction_signature_committed",
                {
                    "signature": correction_signature,
                    "patch_id": patch.patch_id,
                    "base_revision": patch.base_revision,
                    "recovery_class": recovery_class,
                    "strategy": "planner_correction",
                },
                subject_id=patch.patch_id,
            )
        correction_nodes = [
            item.node_id
            for item in patch.new_nodes
            if item.atom.role == AtomRole.WORK
        ]
        if patch.base_revision > 0 and correction_nodes and reviews:
            latest_review = reviews[-1][0]
            unsatisfied = [
                item.obligation_id
                for item in latest_review.verdicts
                if item.status != ObligationVerdictStatus.SATISFIED
            ]
            self._persist(
                state,
                "replan_applied",
                {
                    "from_graph_revision": patch.base_revision,
                    "to_graph_revision": patch.base_revision + 1,
                    "patch_id": patch.patch_id,
                    "review_id": latest_review.review_id,
                    "unsatisfied_obligation_ids": unsatisfied,
                    "correction_node_ids": correction_nodes,
                    "reason": (
                        "append-only correction graph after independent result review"
                    ),
                    "supervisor_action_executed": False,
                    "rwkv_action_authority": True,
                },
                subject_id=patch.patch_id,
            )
        return None

    def _issue_contract_review(
        self,
        state: RunState,
        obligations: Mapping[str, ContractObligation],
        nodes: Mapping[str, ContractGraphNode],
        patches: list[ContractGraphPatch],
        reviews: list[tuple[ContractGraphReview, str, int]],
        capsules: tuple[ResultCapsule, ...],
        *,
        evidence_digest: str,
        transitions: int,
    ) -> ControllerResult | None:
        execution_obligations = {
            obligation_id: obligation
            for obligation_id, obligation in obligations.items()
            if obligation.phase == ObligationPhase.EXECUTION_EVIDENCE
        }
        if not execution_obligations:
            return self._contract_supervisor_failure(
                state,
                ValueError("contract graph has no execution-evidence obligations"),
                phase="contract_review",
                transitions=transitions,
            )
        request = ContractReviewRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            graph_revision=len(patches),
            obligations=tuple(
                item.to_dict() for item in execution_obligations.values()
            ),
            nodes=tuple(item.to_dict() for item in nodes.values()),
            result_capsules=capsules,
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
        )
        evidence_ids = tuple(item.evidence_id for item in capsules)
        typed_verdicts = self._evaluate_typed_contract(
            execution_obligations, capsules
        )
        unresolved_ids = tuple(
            obligation_id
            for obligation_id in execution_obligations
            if obligation_id not in typed_verdicts
        )
        review_source = "local_typed_checker"
        try:
            if unresolved_ids:
                method = getattr(self.supervisor, "review_contract_graph", None)
                if not callable(method):
                    raise TypeError("supervisor has no contract graph reviewer")
                exception_request = ContractReviewRequest(
                    run_id=request.run_id,
                    request=request.request,
                    request_digest=request.request_digest,
                    graph_revision=request.graph_revision,
                    obligations=tuple(
                        execution_obligations[obligation_id].to_dict()
                        for obligation_id in unresolved_ids
                    ),
                    nodes=request.nodes,
                    result_capsules=request.result_capsules,
                    workspace_manifest=request.workspace_manifest,
                )
                returned = method(exception_request)
                if not isinstance(returned, ContractGraphReview):
                    raise TypeError("supervisor returned an invalid contract graph review")
                exception_review = ContractGraphReview.from_dict(
                    returned.to_dict(),
                    obligation_ids=unresolved_ids,
                    evidence_ids=evidence_ids,
                )
                combined = {
                    item.obligation_id: item for item in exception_review.verdicts
                }
                combined.update(typed_verdicts)
                review = ContractGraphReview.create(
                    graph_revision=len(patches),
                    summary=(
                        f"Typed checker resolved {len(typed_verdicts)} obligations; "
                        f"exception Reviewer resolved {len(unresolved_ids)}. "
                        + exception_review.summary
                    ),
                    verdicts=tuple(
                        combined[item] for item in execution_obligations
                    ),
                    obligation_ids=tuple(execution_obligations),
                    evidence_ids=evidence_ids,
                )
                review_source = "typed_checker_plus_exception_reviewer"
            else:
                review = ContractGraphReview.create(
                    graph_revision=len(patches),
                    summary="All obligations were resolved by typed public-result assertions.",
                    verdicts=tuple(
                        typed_verdicts[item] for item in execution_obligations
                    ),
                    obligation_ids=tuple(execution_obligations),
                    evidence_ids=evidence_ids,
                )
            if review.graph_revision != len(patches):
                raise ValueError("contract reviewer changed the graph revision")
            review, deterministic_vetoes = self._apply_deterministic_review_vetoes(
                request,
                review,
            )
        except Exception as exc:
            return self._contract_supervisor_failure(
                state,
                exc,
                phase="contract_review",
                transitions=transitions,
            )
        satisfied = sum(
            item.status == ObligationVerdictStatus.SATISFIED
            for item in review.verdicts
        )
        previous_satisfied = (
            sum(
                item.status == ObligationVerdictStatus.SATISFIED
                for item in reviews[-1][0].verdicts
            )
            if reviews
            else -1
        )
        stagnant_rounds = (
            reviews[-1][2] + 1
            if reviews and satisfied <= previous_satisfied
            else 0
        )
        self._persist(
            state,
            "contract_graph_review_committed",
            {
                "review_id": review.review_id,
                "review": review.to_dict(),
                "graph_revision": len(patches),
                "evidence_ids": list(evidence_ids),
                "evidence_digest": evidence_digest,
                "stagnant_rounds": stagnant_rounds,
                "supervisor": (
                    {"provider": "local_typed_checker", "model": "deterministic-v1"}
                    if not unresolved_ids
                    else supervisor_identity(self.supervisor)
                ),
                "review_source": review_source,
                "typed_obligation_ids": list(typed_verdicts),
                "exception_reviewer_obligation_ids": list(unresolved_ids),
                "reviewer_can_plan": False,
                "supervisor_action_executed": False,
                "result_capsule_count": len(capsules),
                "result_capsules_only": True,
                "deterministic_veto_obligation_ids": list(
                    deterministic_vetoes
                ),
            },
            subject_id=review.review_id,
        )
        self._persist_supervisor_resolved(state, phase="contract_review")
        return None

    def _issue_contract_presentation_review(
        self,
        state: RunState,
        obligations: Mapping[str, ContractObligation],
        nodes: Mapping[str, ContractGraphNode],
        patches: list[ContractGraphPatch],
        capsules: tuple[ResultCapsule, ...],
        outcome: AtomExecutionOutcome,
        *,
        workspace_manifest: Mapping[str, Any],
        evidence_digest: str,
        transitions: int,
    ) -> ControllerResult | None:
        """Independently accept or reject the exact RWKV presentation text."""

        request = ContractReviewRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            graph_revision=len(patches),
            obligations=tuple(item.to_dict() for item in obligations.values()),
            nodes=tuple(item.to_dict() for item in nodes.values()),
            result_capsules=capsules,
            workspace_manifest=workspace_manifest,
        )
        obligation_ids = tuple(obligations)
        evidence_ids = tuple(item.evidence_id for item in capsules)
        try:
            method = getattr(self.supervisor, "review_contract_graph", None)
            if not callable(method):
                raise TypeError("supervisor has no contract graph reviewer")
            returned = method(request)
            if not isinstance(returned, ContractGraphReview):
                raise TypeError("supervisor returned an invalid presentation review")
            review = ContractGraphReview.from_dict(
                returned.to_dict(),
                obligation_ids=obligation_ids,
                evidence_ids=evidence_ids,
            )
            if review.graph_revision != len(patches):
                raise ValueError("presentation reviewer changed the graph revision")
        except Exception as exc:
            return self._contract_supervisor_failure(
                state,
                exc,
                phase="contract_final_presentation_review",
                transitions=transitions,
            )
        output_sha256 = hashlib.sha256(
            outcome.candidate_output.encode("utf-8")
        ).hexdigest()
        self._persist(
            state,
            "contract_final_presentation_review_committed",
            {
                "review_id": review.review_id,
                "review": review.to_dict(),
                "graph_revision": len(patches),
                "candidate_atom_id": outcome.atom_id,
                "candidate_output_sha256": output_sha256,
                "evidence_ids": list(evidence_ids),
                "evidence_digest": evidence_digest,
                "supervisor": supervisor_identity(self.supervisor),
                "review_source": "independent_final_presentation_reviewer",
                "reviewer_can_plan": False,
                "reviewer_rewrote_output": False,
                "controller_rewritten": False,
                "supervisor_action_executed": False,
            },
            subject_id=outcome.atom_id,
        )
        self._persist_supervisor_resolved(
            state,
            phase="contract_final_presentation_review",
        )
        return None

    @staticmethod
    def _apply_deterministic_review_vetoes(
        request: ContractReviewRequest,
        review: ContractGraphReview,
    ) -> tuple[ContractGraphReview, tuple[str, ...]]:
        """Veto satisfied verdicts contradicted by mechanical public facts.

        This kernel never accepts an obligation and never sees hidden acceptance.
        It only calculates format relations explicitly named by the immutable
        request, leaving semantic judgment to the independent Reviewer.
        """

        request_text = request.request
        normalized_request = request_text.casefold()
        if not any(
            term in normalized_request
            for term in (
                "relative path",
                "line_count",
                "byte_count",
                "total_files",
                "total_bytes",
            )
        ):
            return review, ()

        root_match = re.search(
            r"(?:inspect|under)\s+([A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*/)",
            request_text,
            flags=re.IGNORECASE,
        )
        relative_root = (
            root_match.group(1).replace("\\", "/").rstrip("/")
            if root_match
            else ""
        )
        source_text: dict[str, tuple[str, str]] = {}
        json_observations_by_artifact: dict[str, tuple[ResultCapsule, Any]] = {}
        for capsule in request.result_capsules:
            if capsule.node_status != "completed" or not bool(
                capsule.result.get("success")
            ):
                continue
            output = str(capsule.result.get("output") or "")
            metadata = capsule.result.get("metadata")
            if isinstance(metadata, Mapping) and metadata.get("complete") is False:
                continue
            artifact_paths = [
                str(item.get("path") or "")
                for item in capsule.artifacts
                if str(item.get("path") or "")
            ]
            if capsule.operation == "read_file" and output:
                for path in artifact_paths:
                    source_text[path] = (output, capsule.evidence_id)
            if capsule.operation == "read_json" and output:
                try:
                    parsed = json.loads(output)
                except json.JSONDecodeError:
                    continue
                keys = artifact_paths or [f"node:{capsule.node_id}"]
                for key in keys:
                    # Capsules are emitted in append-only node/action order, so
                    # replacement here selects the current successful observation
                    # of an artifact and prevents stale revisions from vetoing it.
                    json_observations_by_artifact[key] = (capsule, parsed)

        violations: list[str] = []
        evidence_refs: list[str] = []
        for capsule, observed in json_observations_by_artifact.values():
            if not isinstance(observed, Mapping):
                continue
            collections = [
                value
                for value in observed.values()
                if isinstance(value, list)
                and all(isinstance(item, Mapping) for item in value)
            ]
            indexed_entries = next(
                (
                    value
                    for value in collections
                    if value
                    and all("path" in item for item in value)
                    and any(
                        key in item
                        for item in value
                        for key in ("line_count", "byte_count")
                    )
                ),
                None,
            )
            if indexed_entries is None:
                continue
            evidence_refs.append(capsule.evidence_id)
            calculated_bytes = 0
            matched_sources = 0
            for entry in indexed_entries:
                value = str(entry.get("path") or "")
                if relative_root and value.startswith(relative_root + "/"):
                    violations.append(
                        f"path value {value!r} retains relative root prefix "
                        f"{relative_root!r}"
                    )
                source_path = (
                    value
                    if not relative_root or value.startswith(relative_root + "/")
                    else f"{relative_root}/{value}"
                )
                source = source_text.get(source_path)
                if source is None:
                    continue
                text, source_evidence_id = source
                matched_sources += 1
                evidence_refs.append(source_evidence_id)
                byte_count = len(text.encode("utf-8"))
                line_count = len(text.splitlines())
                calculated_bytes += byte_count
                if "byte_count" in entry and entry.get("byte_count") != byte_count:
                    violations.append(
                        f"{value!r} byte_count={entry.get('byte_count')!r}, "
                        f"calculated={byte_count}"
                    )
                if "line_count" in entry and entry.get("line_count") != line_count:
                    violations.append(
                        f"{value!r} line_count={entry.get('line_count')!r}, "
                        f"calculated={line_count}"
                    )
            if "total_files" in observed and observed.get("total_files") != len(
                indexed_entries
            ):
                violations.append(
                    f"total_files={observed.get('total_files')!r}, "
                    f"calculated={len(indexed_entries)}"
                )
            if (
                "total_bytes" in observed
                and matched_sources == len(indexed_entries)
                and observed.get("total_bytes") != calculated_bytes
            ):
                violations.append(
                    f"total_bytes={observed.get('total_bytes')!r}, "
                    f"calculated={calculated_bytes}"
                )

        if not violations or not evidence_refs:
            return review, ()
        obligation_by_id = {
            str(item.get("obligation_id") or ""): str(item.get("predicate") or "")
            for item in request.obligations
        }
        eligible = [
            item.obligation_id
            for item in review.verdicts
            if item.status == ObligationVerdictStatus.SATISFIED
            and any(
                term in obligation_by_id.get(item.obligation_id, "").casefold()
                for term in (
                    "relative path",
                    "line_count",
                    "byte_count",
                    "total_files",
                    "total_bytes",
                    "verify",
                )
            )
        ]
        if not eligible:
            return review, ()
        veto_id = eligible[0]
        refs = tuple(dict.fromkeys(evidence_refs))[:32]
        verdicts = tuple(
            ObligationVerdict.create(
                obligation_id=item.obligation_id,
                status="contradicted",
                evidence_refs=refs,
                reason=(
                    "Deterministic public-result check contradicts satisfaction: "
                    + "; ".join(violations[:8])
                ),
            )
            if item.obligation_id == veto_id
            else item
            for item in review.verdicts
        )
        revised = ContractGraphReview.create(
            graph_revision=review.graph_revision,
            summary=(
                review.summary
                + " Deterministic result checks vetoed an unsound satisfied verdict."
            ),
            verdicts=verdicts,
            obligation_ids=tuple(obligation_by_id),
            evidence_ids=tuple(
                item.evidence_id for item in request.result_capsules
            ),
        )
        return revised, (veto_id,)

    def _complete_contract_finalizer(
        self,
        state: RunState,
        outcome: AtomExecutionOutcome,
        nodes: Mapping[str, ContractGraphNode],
        review: ContractGraphReview,
        transitions: int,
        *,
        presentation_review: ContractGraphReview | None = None,
    ) -> ControllerResult:
        node = nodes.get(outcome.atom_id)
        if node is None or node.atom.role != AtomRole.FINALIZER:
            raise ValueError("contract finalizer node is unavailable")
        output = outcome.candidate_output
        self._persist(
            state,
            "run_completed",
            {
                "decision_id": f"{outcome.atom_id}:{outcome.candidate_decision_id}",
                "request_id": "",
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": "rwkv_contract_finalizer_exact_candidate",
                "controller_rewritten": False,
                "accepted_candidate_atom_id": outcome.atom_id,
                "contract_review_id": review.review_id,
                "final_presentation_review_id": (
                    presentation_review.review_id
                    if presentation_review is not None
                    else ""
                ),
                "reviewer_rewrote_output": False,
                "supervisor_action_executed": False,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _contract_supervisor_failure(
        self,
        state: RunState,
        exc: BaseException,
        *,
        phase: str,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "supervisor_call_failed",
            {
                "phase": phase,
                "supervisor": supervisor_identity(self.supervisor),
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "fail_closed": True,
                "resumable": True,
                "at": utc_now(),
            },
        )
        self._persist_supervisor_pending(state, phase=phase)
        return self._interrupt_contract_graph(
            state,
            reason=f"{phase}_unavailable",
            transitions=transitions,
        )

    def _interrupt_contract_graph(
        self,
        state: RunState,
        *,
        reason: str,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": reason,
                "decision_id": "",
                "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                "output_source": "none",
                "controller_rewritten": False,
                "final_output": "",
            },
        )
        return ControllerResult(state, "", transitions)

    def _run_parallel_atoms(self, state: RunState) -> ControllerResult:
        """Run low-frequency GPT stages over a pool of scoped RWKV atom workers."""

        if self.supervisor is None:
            raise RuntimeError("parallel atom mode requires a supervisor")
        if self.atom_worker_pool is None:
            self._persist(
                state,
                "run_failed",
                {
                    "reason": "parallel_atom_worker_pool_missing",
                    "decision_id": "",
                    "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                    "output_source": "none",
                    "controller_rewritten": False,
                    "final_output": "",
                },
            )
            return ControllerResult(state, "", 0)

        while True:
            stages = self._committed_parallel_stages(state)
            outcomes = self._committed_atom_outcomes(state)
            transitions = sum(item.action_count for item in outcomes.values())
            current = stages[-1] if stages else None

            if self._project_parallel_atom_actions(state, outcomes):
                continue

            if current is not None and current.disposition == StageDisposition.ACCEPT_FINAL:
                return self._complete_parallel_candidate(
                    state,
                    current,
                    outcomes,
                    transitions,
                )

            pending_atoms = tuple(
                atom
                for atom in (current.atoms if current is not None else ())
                if atom.atom_id not in outcomes
            )
            if pending_atoms:
                attempted = self._parallel_attempted_atom_ids(state)
                for atom in pending_atoms:
                    if atom.atom_id in attempted:
                        continue
                    execution_contract = AtomExecutionContract.create(
                        immutable_request=state.goal.request,
                        atom=atom,
                    )
                    self._persist(
                        state,
                        "atom_attempt_started",
                        {
                            "stage_id": current.stage_id,
                            "stage_index": current.stage_index,
                            "atom_id": atom.atom_id,
                            "contract_digest": (
                                execution_contract.contract_digest
                            ),
                            "role": atom.role.value,
                            "depends_on": list(atom.depends_on),
                            "write_roots": list(atom.write_roots),
                            "exclusive": atom.exclusive,
                            "at": utc_now(),
                        },
                        subject_id=atom.atom_id,
                    )
                returned = self.atom_worker_pool.run_stage(
                    state.goal,
                    current,
                    pending_atoms,
                    max_workers=min(
                        self.supervisor_policy.max_parallel_atoms,
                        len(pending_atoms),
                    ),
                    max_transitions=self.supervisor_policy.atom_max_transitions,
                    completed_outcomes=outcomes,
                )
                returned_by_id = {item.atom_id: item for item in returned}
                if set(returned_by_id) != {atom.atom_id for atom in pending_atoms}:
                    raise ValueError("atom worker pool returned an incomplete stage batch")
                for atom in pending_atoms:
                    execution_contract = AtomExecutionContract.create(
                        immutable_request=state.goal.request,
                        atom=atom,
                    )
                    outcome = AtomExecutionOutcome.from_dict(
                        returned_by_id[atom.atom_id].to_dict()
                    )
                    if (
                        outcome.stage_id != current.stage_id
                        or outcome.contract_digest
                        != execution_contract.contract_digest
                        or outcome.role != atom.role
                        or outcome.write_roots != atom.write_roots
                    ):
                        raise ValueError("atom worker outcome changed committed atom identity")
                    self._persist(
                        state,
                        "atom_outcome_committed",
                        {
                            "stage_id": current.stage_id,
                            "stage_index": current.stage_index,
                            "atom_id": atom.atom_id,
                            "outcome": outcome.to_dict(),
                            "rwkv_action_authority": True,
                            "supervisor_action_executed": False,
                            "controller_rewritten": False,
                        },
                        subject_id=atom.atom_id,
                    )
                continue

            if len(stages) >= self.supervisor_policy.max_parallel_stages:
                candidate = self._latest_parallel_finalizer(outcomes)
                output = candidate.candidate_output if candidate is not None else ""
                self._persist(
                    state,
                    "run_interrupted",
                    {
                        "reason": "parallel_stage_budget_exhausted",
                        "decision_id": (
                            candidate.candidate_decision_id if candidate else ""
                        ),
                        "final_output_sha256": hashlib.sha256(
                            output.encode("utf-8")
                        ).hexdigest(),
                        "output_source": (
                            "rwkv_parallel_finalizer_not_accepted"
                            if output
                            else "none"
                        ),
                        "controller_rewritten": False,
                        "final_output": output,
                    },
                )
                return ControllerResult(state, output, transitions)

            request = self._parallel_stage_request(state, stages, outcomes)
            try:
                returned_stage = self.supervisor.next_stage(request)
                if not isinstance(returned_stage, SupervisorStage):
                    raise TypeError("supervisor returned an invalid stage object")
                stage = SupervisorStage.from_dict(
                    returned_stage.to_dict(),
                    request=request,
                )
                if len(stage.atoms) > self.supervisor_policy.max_parallel_atoms:
                    raise ValueError(
                        "supervisor stage exceeds configured parallel atom limit"
                    )
            except Exception as exc:
                return self._parallel_stage_failure(
                    state,
                    exc,
                    outcomes,
                    transitions,
                )
            self._persist(
                state,
                "supervisor_stage_committed",
                {
                    "stage_id": stage.stage_id,
                    "stage_index": stage.stage_index,
                    "stage": stage.to_dict(),
                    "request_digest": state.goal.digest,
                    "supervisor": supervisor_identity(self.supervisor),
                    "rwkv_action_authority": True,
                    "supervisor_action_executed": False,
                    "rwkv_output_rewritten": False,
                },
                subject_id=stage.stage_id,
            )
            self._persist_supervisor_resolved(state, phase="stage")
            failed_basis = self._parallel_replan_basis(request)
            if stage.disposition == StageDisposition.DISPATCH and failed_basis:
                self._persist(
                    state,
                    "replan_applied",
                    {
                        "from_stage_id": request.previous_stage_id,
                        "to_stage_id": stage.stage_id,
                        "failed_atom_ids": failed_basis,
                        "reason": "new dispatch after exact failed atom action evidence",
                        "supervisor_action_executed": False,
                        "rwkv_action_authority": True,
                    },
                    subject_id=stage.stage_id,
                )

    def _committed_parallel_stages(
        self,
        state: RunState,
    ) -> list[SupervisorStage]:
        stages: list[SupervisorStage] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "supervisor_stage_committed":
                continue
            value = event.payload.get("stage")
            if not isinstance(value, Mapping):
                raise ValueError("committed supervisor stage is incomplete")
            stage = SupervisorStage.restore(
                value,
                immutable_request=state.goal.request,
            )
            if stage.request_digest != state.goal.digest:
                raise ValueError("committed supervisor stage changed the request digest")
            if stage.stage_index != len(stages) + 1:
                raise ValueError("committed supervisor stage indexes are not contiguous")
            stages.append(stage)
        return stages

    @staticmethod
    def _committed_atom_outcomes(
        state: RunState,
    ) -> dict[str, AtomExecutionOutcome]:
        outcomes: dict[str, AtomExecutionOutcome] = {}
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "atom_outcome_committed":
                continue
            value = event.payload.get("outcome")
            if not isinstance(value, Mapping):
                raise ValueError("committed atom outcome is incomplete")
            outcome = AtomExecutionOutcome.from_dict(value)
            if outcome.atom_id in outcomes:
                raise ValueError("an atom outcome was committed more than once")
            outcomes[outcome.atom_id] = outcome
        return outcomes

    @staticmethod
    def _parallel_attempted_atom_ids(state: RunState) -> set[str]:
        return {
            str(state.causal_records[event_id].payload.get("atom_id") or "")
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type == "atom_attempt_started"
        }

    def _project_parallel_atom_actions(
        self,
        state: RunState,
        outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> bool:
        """Project committed child actions into the parent append-only ledger."""

        started_attempts = {
            str(state.causal_records[event_id].payload.get("attempt_id") or "")
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type == "attempt_started"
        }
        returned_attempts = {
            str(state.causal_records[event_id].payload.get("attempt_id") or "")
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type == "action_returned"
        }
        changed = False
        for outcome in outcomes.values():
            for action in outcome.actions:
                action_id = str(action.get("action_id") or "")
                attempt_id = f"{outcome.stage_id}:{outcome.atom_id}:{action_id}"
                if not action_id or attempt_id in returned_attempts:
                    continue
                result = dict(action.get("result") or {})
                common = {
                    "attempt_id": attempt_id,
                    "stage_id": outcome.stage_id,
                    "atom_id": outcome.atom_id,
                    "contract_digest": outcome.contract_digest,
                    "action_id": action_id,
                    "operation": str(action.get("operation") or ""),
                    "arguments": dict(action.get("arguments") or {}),
                    "action_sequence": int(action.get("sequence", 0) or 0),
                    "rwkv_action_authority": True,
                    "supervisor_action_executed": False,
                }
                if attempt_id not in started_attempts:
                    self._persist(
                        state,
                        "attempt_started",
                        {**common, "at": outcome.started_at},
                        subject_id=attempt_id,
                    )
                    started_attempts.add(attempt_id)
                self._persist(
                    state,
                    "action_returned",
                    {
                        **common,
                        "success": bool(result.get("success")),
                        "status": str(action.get("status") or ""),
                        "output": str(result.get("output") or ""),
                        "exit_code": result.get("exit_code"),
                        "error": dict(result.get("error") or {}),
                        "artifact_refs": list(action.get("artifact_refs") or ()),
                        "workspace_changed": bool(action.get("workspace_changed")),
                        "at": outcome.ended_at,
                    },
                    subject_id=attempt_id,
                )
                returned_attempts.add(attempt_id)
                changed = True
        return changed

    @staticmethod
    def _parallel_replan_basis(request: SupervisorStageRequest) -> list[str]:
        failed: list[str] = []
        for item in request.completed_atoms:
            if str(item.get("stage_id") or "") != request.previous_stage_id:
                continue
            atom_id = str(item.get("atom_id") or "")
            outcome_failed = str(item.get("status") or "") != "completed"
            action_failed = any(
                not bool((action.get("result") or {}).get("success"))
                for action in item.get("recent_actions") or ()
                if isinstance(action, Mapping)
            )
            if atom_id and (outcome_failed or action_failed):
                failed.append(atom_id)
        return failed

    def _parallel_stage_request(
        self,
        state: RunState,
        stages: list[SupervisorStage],
        outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> SupervisorStageRequest:
        ordered_outcomes = tuple(
            {
                **outcomes[atom.atom_id].to_supervisor_dict(),
                "execution_contract": AtomExecutionContract.create(
                    immutable_request=state.goal.request,
                    atom=atom,
                ).to_dict(),
            }
            for stage in stages
            if stage.disposition == StageDisposition.DISPATCH
            for atom in stage.atoms
            if atom.atom_id in outcomes
        )
        return SupervisorStageRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            constraints=tuple(state.goal.constraints),
            stage_index=len(stages) + 1,
            max_parallel_atoms=self.supervisor_policy.max_parallel_atoms,
            previous_stage_id=(stages[-1].stage_id if stages else ""),
            completed_atoms=ordered_outcomes,
            available_operations=tuple(
                {
                    "name": str(item["name"]),
                    "description": str(item.get("description") or ""),
                    "scope_mode": (
                        "read_only"
                        if not self.harness.definition(str(item["name"])).side_effect
                        else "path_mutation"
                        if str(item["name"]) in PATH_MUTATION_OPERATIONS
                        else "exclusive_side_effect"
                    ),
                }
                for item in self.harness.g1i_tool_definitions()
            ),
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
            causal_evidence=tuple(
                {
                    "event_type": event.event_type,
                    "subject_id": event.subject_id,
                    "payload": dict(event.payload),
                }
                for event in (
                    state.causal_records[event_id]
                    for event_id in state.causal_order
                )
                if event.event_type
                in {"attempt_started", "action_returned", "replan_applied"}
            )[-128:],
        )

    @staticmethod
    def _latest_parallel_finalizer(
        outcomes: Mapping[str, AtomExecutionOutcome],
    ) -> AtomExecutionOutcome | None:
        candidates = [
            outcome
            for outcome in outcomes.values()
            if outcome.role.value == "finalizer"
            and outcome.status == AtomExecutionStatus.COMPLETED
            and outcome.candidate_output
        ]
        return candidates[-1] if candidates else None

    def _complete_parallel_candidate(
        self,
        state: RunState,
        stage: SupervisorStage,
        outcomes: Mapping[str, AtomExecutionOutcome],
        transitions: int,
    ) -> ControllerResult:
        outcome = outcomes.get(stage.accepted_candidate_atom_id)
        if (
            outcome is None
            or outcome.role.value != "finalizer"
            or outcome.status != AtomExecutionStatus.COMPLETED
            or not outcome.candidate_output
        ):
            raise ValueError("accepted parallel finalizer outcome is unavailable")
        output = outcome.candidate_output
        decision_id = f"{outcome.atom_id}:{outcome.candidate_decision_id}"
        self._persist(
            state,
            "run_completed",
            {
                "decision_id": decision_id,
                "request_id": "",
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": "rwkv_parallel_finalizer_exact_candidate",
                "controller_rewritten": False,
                "supervisor_stage_id": stage.stage_id,
                "supervisor_disposition": stage.disposition.value,
                "accepted_candidate_atom_id": outcome.atom_id,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _parallel_stage_failure(
        self,
        state: RunState,
        exc: BaseException,
        outcomes: Mapping[str, AtomExecutionOutcome],
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "supervisor_call_failed",
            {
                "phase": "stage",
                "supervisor": supervisor_identity(self.supervisor),
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "fail_closed": True,
                "resumable": True,
                "at": utc_now(),
            },
        )
        self._persist_supervisor_pending(state, phase="stage")
        candidate = self._latest_parallel_finalizer(outcomes)
        output = candidate.candidate_output if candidate is not None else ""
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": "supervisor_stage_unavailable",
                "decision_id": (
                    candidate.candidate_decision_id if candidate is not None else ""
                ),
                "final_output_sha256": hashlib.sha256(
                    output.encode("utf-8")
                ).hexdigest(),
                "output_source": (
                    "rwkv_parallel_finalizer_supervisor_unavailable"
                    if output
                    else "none"
                ),
                "controller_rewritten": False,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _run_online_supervised(self, state: RunState) -> ControllerResult:
        """Run one RWKV operation under each committed online microtask."""

        transitions = 0
        pending_events: list[ModelEvent] = []
        wave_actions, wave_rejections, unreviewed_final = (
            self._unreviewed_online_state(state)
        )
        directives = self._committed_online_directives(state)
        if unreviewed_final is not None:
            outcome = self._online_final_outcome(
                unreviewed_final, wave_actions, wave_rejections
            )
            boundary = self._issue_online_directive(state, outcome, transitions)
            if isinstance(boundary, ControllerResult):
                return boundary
            directive = boundary
            wave_actions = []
            wave_rejections = []
        elif wave_actions and self._online_wave_requires_review(wave_actions):
            boundary = self._issue_online_directive(
                state,
                self._online_action_batch_outcome(
                    wave_actions, wave_rejections
                ),
                transitions,
            )
            if isinstance(boundary, ControllerResult):
                return boundary
            directive = boundary
            wave_actions = []
            wave_rejections = []
        elif (
            len(wave_rejections)
            >= self.supervisor_policy.online_protocol_rejections_per_directive
        ):
            boundary = self._issue_online_directive(
                state,
                self._online_protocol_batch_outcome(
                    wave_actions, wave_rejections
                ),
                transitions,
            )
            if isinstance(boundary, ControllerResult):
                return boundary
            directive = boundary
            wave_actions = []
            wave_rejections = []
        elif not directives:
            boundary = self._issue_online_directive(state, None, transitions)
            if isinstance(boundary, ControllerResult):
                return boundary
            directive = boundary
        else:
            directive = directives[-1]

        if directive.disposition == DirectiveDisposition.ACCEPT_FINAL:
            return self._recover_accepted_online_final(state, directive, transitions)

        pending_action_event = self._first_unappended_action_observation(state)
        if pending_action_event is not None:
            pending_events.append(pending_action_event)
        directive_event = self._online_directive_event(directive)
        if directive_event.event_id not in state.model_events:
            pending_events.append(directive_event)

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
                rejection_ref = f"protocol:{exc.decision_id or exc.request_id}"
                error_record = {
                    "type": "ModelProtocolError",
                    "message": str(exc)[:2000],
                    "decision_id": exc.decision_id,
                    "request_id": exc.request_id,
                    "rejected_arguments": dict(exc.rejected_arguments),
                    "at": utc_now(),
                }
                self._persist(
                    state,
                    "protocol_rejection_recorded",
                    {
                        "decision_id": exc.decision_id,
                        "request_id": exc.request_id,
                        "rejection_ref": rejection_ref,
                        "error": str(exc)[:2000],
                        "rejected_arguments": dict(exc.rejected_arguments),
                        "error_record": error_record,
                        "rejection_count": state.protocol_rejections + 1,
                        "action_executed": False,
                    },
                )
                if state.protocol_rejections >= self._MAX_PROTOCOL_REJECTIONS:
                    terminal_reason = "protocol_rejection_budget_exhausted"
                    break
                wave_rejections.append(
                    {
                        "rejection_ref": rejection_ref,
                        "decision_id": exc.decision_id,
                        "request_id": exc.request_id,
                        "error": str(exc)[:2000],
                        "selected_operation": exc.selected_operation or "",
                        "rejected_arguments": dict(exc.rejected_arguments),
                    }
                )
                pending_events = [
                    ModelEvent(
                        event_type="protocol_rejection",
                        event_id=f"EV-REJECT-{uuid4().hex[:16]}",
                        scope_id=self.model.ACTION_LANE_ID,
                        payload={
                            "error": str(exc)[:2000],
                            "action_executed": False,
                            "rejected_arguments": dict(exc.rejected_arguments),
                            **(
                                {
                                    "selected_operation": exc.selected_operation,
                                    **(
                                        {
                                            "selected_operation_schema": (
                                                exc.selected_operation_schema
                                            )
                                        }
                                        if not exc.schema_already_disclosed
                                        else {}
                                    ),
                                    "schema_already_disclosed": (
                                        exc.schema_already_disclosed
                                    ),
                                }
                                if exc.selected_operation
                                and exc.selected_operation_schema
                                else {}
                            ),
                            "instruction": (
                                "Keep the current supervisor microtask. Return one displayed "
                                "direct function call with its complete explicit parameter "
                                "object; no operation or value was inferred."
                            ),
                        },
                    )
                ]
                if (
                    len(wave_rejections)
                    >= self.supervisor_policy.online_protocol_rejections_per_directive
                ):
                    boundary = self._issue_online_directive(
                        state,
                        self._online_protocol_batch_outcome(
                            wave_actions, wave_rejections
                        ),
                        transitions,
                    )
                    if isinstance(boundary, ControllerResult):
                        return boundary
                    directive = boundary
                    wave_actions = []
                    wave_rejections = []
                    pending_events.append(
                        self._online_directive_event(directive)
                    )
                continue

            transitions += 1
            if decision.wire_command.name == "final_answer":
                output = str(decision.wire_command.arguments["text"])
                outcome = self._online_final_outcome(
                    {
                        "candidate_decision_id": decision.decision.decision_id,
                        "candidate_output": output,
                    },
                    wave_actions,
                    wave_rejections,
                )
                boundary = self._issue_online_directive(state, outcome, transitions)
                if isinstance(boundary, ControllerResult):
                    return boundary
                directive = boundary
                if directive.disposition == DirectiveDisposition.ACCEPT_FINAL:
                    return self._complete_online_candidate(
                        state,
                        decision.decision.decision_id,
                        decision.decision.request_id,
                        output,
                        directive,
                        transitions,
                    )
                wave_actions = []
                wave_rejections = []
                pending_events = [self._online_directive_event(directive)]
                continue

            action = self._execute_decision(state, decision)
            observation = self._action_observation_event(state, action)
            wave_actions.append(action)
            pending_events = [observation]
            if self._online_wave_requires_review(wave_actions):
                boundary = self._issue_online_directive(
                    state,
                    self._online_action_batch_outcome(
                        wave_actions, wave_rejections
                    ),
                    transitions,
                )
                if isinstance(boundary, ControllerResult):
                    return boundary
                directive = boundary
                wave_actions = []
                wave_rejections = []
                pending_events.append(self._online_directive_event(directive))
        if not terminal_reason:
            terminal_reason = "transition_budget_exhausted"
        return self._interrupt_online_run(state, terminal_reason, transitions)

    @staticmethod
    def _committed_online_directives(state: RunState) -> list[SupervisorDirective]:
        directives: list[SupervisorDirective] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "supervisor_directive_committed":
                continue
            value = event.payload.get("directive")
            if not isinstance(value, Mapping):
                raise ValueError("committed online directive is incomplete")
            directive = SupervisorDirective.from_dict(value)
            if directive.directive_index != len(directives) + 1:
                raise ValueError("online directive indexes are not contiguous")
            directives.append(directive)
        return directives

    def _unreviewed_online_state(
        self,
        state: RunState,
    ) -> tuple[
        list[ActionRecord],
        list[Mapping[str, Any]],
        Mapping[str, Any] | None,
    ]:
        reviewed_final_refs: set[str] = set()
        reviewed_action_ids: set[str] = set()
        reviewed_rejection_refs: set[str] = set()
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type != "supervisor_directive_committed":
                continue
            outcome = event.payload.get("worker_outcome")
            if not isinstance(outcome, Mapping):
                continue
            reviewed_action_ids.update(
                str(item) for item in outcome.get("action_ids") or ()
            )
            reviewed_rejection_refs.update(
                str(item) for item in outcome.get("rejection_refs") or ()
            )
            if str(outcome.get("type") or "") in {
                "final_candidate",
                "microtask_report",
            }:
                reviewed_final_refs.add(str(outcome.get("outcome_ref") or ""))
        actions: list[ActionRecord] = []
        rejections: list[Mapping[str, Any]] = []
        final_outcomes: list[Mapping[str, Any]] = []
        for event_id in state.causal_order:
            event = state.causal_records[event_id]
            if event.event_type == "action_finished":
                action_id = str(event.payload.get("action_id") or "")
                action = state.actions.get(action_id)
                if action is not None and action_id not in reviewed_action_ids:
                    actions.append(action)
            elif (
                event.event_type == "model_call_accepted"
                and str(event.payload.get("operation") or "") == "final_answer"
            ):
                decision_id = str(event.payload.get("decision_id") or "")
                ref = f"final:{decision_id}"
                decision = state.decisions.get(decision_id)
                if decision is None or ref in reviewed_final_refs:
                    continue
                command = parse_model_command(decision.raw_output)
                validate_final_answer(command)
                output = str(command.arguments["text"])
                final_outcomes.append(
                    {
                        "candidate_decision_id": decision_id,
                        "candidate_output": output,
                    }
                )
            elif event.event_type == "protocol_rejection_recorded":
                ref = str(event.payload.get("rejection_ref") or "")
                if not ref:
                    ref = "protocol:" + str(
                        event.payload.get("decision_id")
                        or event.payload.get("request_id")
                        or event.event_id
                    )
                if ref not in reviewed_rejection_refs:
                    rejections.append(
                        {
                            "rejection_ref": ref,
                            "decision_id": str(
                                event.payload.get("decision_id") or ""
                            ),
                            "request_id": str(
                                event.payload.get("request_id") or ""
                            ),
                            "error": str(event.payload.get("error") or "")[:2000],
                        }
                    )
        if len(final_outcomes) > 1:
            raise ValueError("online supervisor has multiple unreviewed final candidates")
        return actions, rejections, (
            final_outcomes[0] if final_outcomes else None
        )

    def _online_action_projection(self, action: ActionRecord) -> dict[str, Any]:
        result = dict(action.result or {})
        observed_output = str(result.get("output") or "")
        if len(observed_output) > 2000:
            result["output"] = observed_output[:2000]
            result["output_projection"] = {
                "truncated": True,
                "original_chars": len(observed_output),
                "retained_chars": 2000,
            }
        return {
            "action_id": action.action_id,
            "sequence": action.sequence,
            "operation": action.action_type,
            "arguments": dict(action.arguments),
            "status": action.status.value,
            "result": result,
            "artifact_refs": list(action.artifact_refs),
            "workspace_digest_before": action.workspace_digest_before,
            "workspace_digest_after": action.workspace_digest_after,
            "observation_fingerprint": action.observation_fingerprint,
        }

    def _online_action_batch_outcome(
        self,
        actions: list[ActionRecord],
        rejections: list[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        if not actions:
            raise ValueError("online action batch must be non-empty")
        action_ids = [action.action_id for action in actions]
        return {
            "type": "action_batch",
            "outcome_ref": f"actions:{action_ids[0]}:{action_ids[-1]}",
            "action_ids": action_ids,
            "action_count": len(action_ids),
            "rejection_refs": [
                str(item.get("rejection_ref") or "") for item in rejections
            ],
            "protocol_rejections": [dict(item) for item in rejections],
        }

    def _online_protocol_batch_outcome(
        self,
        actions: list[ActionRecord],
        rejections: list[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        if not rejections:
            raise ValueError("online protocol batch must be non-empty")
        refs = [str(item.get("rejection_ref") or "") for item in rejections]
        return {
            "type": "protocol_batch",
            "outcome_ref": f"protocols:{refs[0]}:{refs[-1]}",
            "action_ids": [action.action_id for action in actions],
            "action_count": len(actions),
            "rejection_refs": refs,
            "protocol_rejections": [dict(item) for item in rejections],
        }

    def _online_final_outcome(
        self,
        final: Mapping[str, Any],
        actions: list[ActionRecord],
        rejections: list[Mapping[str, Any]],
    ) -> Mapping[str, Any]:
        decision_id = str(final.get("candidate_decision_id") or "")
        output = str(final.get("candidate_output") or "")
        return {
            "type": "microtask_report",
            "outcome_ref": f"final:{decision_id}",
            "action_ids": [action.action_id for action in actions],
            "action_count": len(actions),
            "rejection_refs": [
                str(item.get("rejection_ref") or "") for item in rejections
            ],
            "protocol_rejections": [dict(item) for item in rejections],
            "candidate_decision_id": decision_id,
            "candidate_output": output,
            "candidate_output_sha256": hashlib.sha256(
                output.encode("utf-8")
            ).hexdigest(),
        }

    def _online_wave_requires_review(self, actions: list[ActionRecord]) -> bool:
        if len(actions) >= self.supervisor_policy.online_actions_per_directive:
            return True
        if len(actions) < 2:
            return False
        first, second = actions[-2:]
        return bool(
            first.observation_fingerprint
            and first.observation_fingerprint == second.observation_fingerprint
            and first.workspace_digest_before == first.workspace_digest_after
            and second.workspace_digest_before == second.workspace_digest_after
        )

    @staticmethod
    def _online_artifacts(state: RunState) -> tuple[Mapping[str, Any], ...]:
        return tuple(
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

    def _issue_online_directive(
        self,
        state: RunState,
        worker_outcome: Mapping[str, Any] | None,
        transitions: int,
    ) -> SupervisorDirective | ControllerResult:
        if self.supervisor is None:
            raise RuntimeError("online directive requested without a supervisor")
        prior = self._committed_online_directives(state)
        if len(prior) >= self.supervisor_policy.max_online_directives:
            return self._interrupt_online_run(
                state,
                "supervisor_directive_budget_exhausted",
                transitions,
                candidate_output=(
                    str(worker_outcome.get("candidate_output") or "")
                    if isinstance(worker_outcome, Mapping)
                    else ""
                ),
            )
        outcome_ref = (
            str(worker_outcome.get("outcome_ref") or "")
            if isinstance(worker_outcome, Mapping)
            else "initial"
        )
        ordered = sorted(state.actions.values(), key=lambda item: item.sequence)
        request = SupervisorDirectiveRequest(
            run_id=state.run_id,
            request=state.goal.request,
            request_digest=state.goal.digest,
            constraints=tuple(state.goal.constraints),
            directive_index=len(prior) + 1,
            outcome_ref=outcome_ref,
            previous_directive=(prior[-1].to_dict() if prior else None),
            worker_outcome=worker_outcome,
            action_count=len(ordered),
            actions=tuple(
                self._online_action_projection(action) for action in ordered[-32:]
            ),
            artifacts=self._online_artifacts(state),
            workspace_manifest=self.harness.workspace_manifest(
                state.goal,
                max_entries=256,
                max_tokens=1800,
            ),
        )
        try:
            returned = self.supervisor.next_directive(request)
            if not isinstance(returned, SupervisorDirective):
                raise TypeError("supervisor returned an invalid directive object")
            directive = SupervisorDirective.from_dict(returned.to_dict())
            if directive.directive_index != request.directive_index:
                raise ValueError("supervisor directive index does not match request")
            if directive.outcome_ref != request.outcome_ref:
                raise ValueError("supervisor directive outcome does not match request")
            if (
                directive.disposition == DirectiveDisposition.ACCEPT_FINAL
                and (
                    not isinstance(worker_outcome, Mapping)
                    or str(worker_outcome.get("type") or "")
                    not in {"final_candidate", "microtask_report"}
                )
            ):
                raise ValueError("supervisor can accept only a current final candidate")
        except Exception as exc:
            return self._online_directive_failure(
                state,
                outcome_ref,
                worker_outcome,
                exc,
                transitions,
            )
        self._persist(
            state,
            "supervisor_directive_committed",
            {
                "directive_id": directive.directive_id,
                "directive": directive.to_dict(),
                "outcome_ref": outcome_ref,
                "worker_outcome": dict(worker_outcome or {}),
                "request_digest": state.goal.digest,
                "supervisor": supervisor_identity(self.supervisor),
                "rwkv_action_authority": True,
                "supervisor_action_executed": False,
                "rwkv_output_rewritten": False,
            },
        )
        self._persist_supervisor_resolved(state, phase="directive")
        return directive

    def _online_directive_event(self, directive: SupervisorDirective) -> ModelEvent:
        return ModelEvent(
            event_type="supervisor_microtask",
            event_id=f"EV-SUPERVISOR-{directive.directive_id}",
            scope_id=self.model.ACTION_LANE_ID,
            payload={
                "source": "external_strong_model_supervisor",
                "authority": "online_planning_and_review_only",
                "directive": directive.to_dict(),
                "instruction": (
                    "Work only on this one microtask now. You remain the only component that "
                    "selects and executes operations. Choose one displayed direct operation "
                    "with a complete explicit parameter object at a time. Use final_answer to "
                    "report that this microtask appears complete; the online supervisor may "
                    "accept it as the top-level Final or issue the next microtask."
                ),
            },
        )

    def _recover_accepted_online_final(
        self,
        state: RunState,
        directive: SupervisorDirective,
        transitions: int,
    ) -> ControllerResult:
        payload = next(
            state.causal_records[event_id].payload
            for event_id in reversed(state.causal_order)
            if state.causal_records[event_id].event_type
            == "supervisor_directive_committed"
            and str(
                state.causal_records[event_id].payload.get("directive_id") or ""
            )
            == directive.directive_id
        )
        outcome = payload.get("worker_outcome")
        if (
            not isinstance(outcome, Mapping)
            or str(outcome.get("type") or "")
            not in {"final_candidate", "microtask_report"}
        ):
            raise ValueError("accepted online directive has no final candidate")
        decision_id = str(outcome.get("candidate_decision_id") or "")
        decision = state.decisions.get(decision_id)
        request_id = decision.request_id if decision is not None else ""
        return self._complete_online_candidate(
            state,
            decision_id,
            request_id,
            str(outcome.get("candidate_output") or ""),
            directive,
            transitions,
        )

    def _complete_online_candidate(
        self,
        state: RunState,
        decision_id: str,
        request_id: str,
        output: str,
        directive: SupervisorDirective,
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
                "supervisor_directive_id": directive.directive_id,
                "supervisor_disposition": directive.disposition.value,
                "final_output": output,
            },
        )
        return ControllerResult(state, output, transitions)

    def _online_directive_failure(
        self,
        state: RunState,
        outcome_ref: str,
        worker_outcome: Mapping[str, Any] | None,
        exc: BaseException,
        transitions: int,
    ) -> ControllerResult:
        self._persist(
            state,
            "supervisor_call_failed",
            {
                "phase": "directive",
                "outcome_ref": outcome_ref,
                "supervisor": (
                    supervisor_identity(self.supervisor)
                    if self.supervisor is not None
                    else {}
                ),
                "error": {"type": type(exc).__name__, "message": str(exc)[:2000]},
                "fail_closed": True,
                "resumable": True,
                "at": utc_now(),
            },
        )
        self._persist_supervisor_pending(state, phase="directive")
        return self._interrupt_online_run(
            state,
            "supervisor_directive_unavailable",
            transitions,
            candidate_output=(
                str(worker_outcome.get("candidate_output") or "")
                if isinstance(worker_outcome, Mapping)
                else ""
            ),
        )

    def _interrupt_online_run(
        self,
        state: RunState,
        reason: str,
        transitions: int,
        *,
        candidate_output: str = "",
    ) -> ControllerResult:
        self._persist(
            state,
            "run_interrupted",
            {
                "reason": reason,
                "decision_id": state.final_decision_id,
                "final_output_sha256": hashlib.sha256(
                    candidate_output.encode("utf-8")
                ).hexdigest(),
                "output_source": (
                    "rwkv_candidate_not_approved_by_supervisor"
                    if candidate_output
                    else "none"
                ),
                "controller_rewritten": False,
                "final_output": candidate_output,
            },
        )
        return ControllerResult(state, candidate_output, transitions)

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
            event.event_type
            in {
                "supervisor_plan_committed",
                "supervisor_directive_committed",
                "contract_graph_patch_committed",
                "contract_graph_review_committed",
            }
            or (
                event.event_type == "run_started"
                and str(event.payload.get("architecture") or "")
                in {
                    "strong-supervisor-rwkv-worker.v1",
                    "online-strong-supervisor-rwkv-microtask-worker.v1",
                    "strong-supervisor-parallel-rwkv-atoms.v1",
                    "strong-supervisor-parallel-rwkv-atoms.v2",
                    "strong-supervisor-parallel-rwkv-atoms.v3",
                    "strong-supervisor-parallel-rwkv-atoms.v5",
                    *CONTRACT_GRAPH_ARCHITECTURE_VERSIONS,
                }
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
                    "selects and executes operations. Follow the operation protocol displayed "
                    "in the current prompt exactly: when it asks for select_tool, return only "
                    "select_tool; after one parameter contract is disclosed, return that direct "
                    "operation. Verify tool results and use final_answer only after the "
                    "completion checks are satisfied."
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
                "resumable": True,
                "at": utc_now(),
            },
        )
        self._persist_supervisor_pending(state, phase="plan")
        self._persist(
            state,
            "run_interrupted",
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
        self._persist_supervisor_resolved(state, phase="review")
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
                    "using observed facts. Follow the operation protocol displayed in each "
                    "current prompt exactly: select_tool first when requested, then the disclosed "
                    "direct operation. Return final_answer again only after the issues and "
                    "original completion checks are satisfied."
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
                "resumable": True,
                "at": utc_now(),
            },
        )
        self._persist_supervisor_pending(state, phase="review")
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
        with self.harness.action_transaction(state.goal):
            return self._execute_decision_locked(state, decision)

    def _execute_decision_locked(
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
                f"{state.run_id}:{sequence}:{fingerprint}".encode()
            ).hexdigest(),
            decision_id=decision.decision.decision_id,
            request_id=decision.decision.request_id,
            started_at=utc_now(),
            workspace_digest_before=str(before.get("digest") or ""),
            atom_execution_contract_digest=atom_execution_contract_digest(
                state.goal
            ),
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
        if authoritative.atom_execution_contract_digest != (
            atom_execution_contract_digest(state.goal)
        ):
            raise ValueError(
                "running action execution contract differs from the active Goal"
            )
        finished = ActionRecord.from_dict(authoritative.to_dict())
        after = self.harness.workspace_observation_snapshot(state.goal)
        external_evidence = result.metadata.get("external_evidence")
        if isinstance(external_evidence, Mapping):
            # Bind a handler-produced evidence packet to the Controller-owned
            # action identity without changing its factual spans, query or
            # provider outcome.  Invalid packets fail the action boundary.
            from rwkv_lh.retrieval.contracts import ExternalEvidenceEnvelope

            try:
                envelope = ExternalEvidenceEnvelope.from_dict(
                    external_evidence
                ).bind_action(authoritative.action_id)
            except (TypeError, ValueError) as exc:
                result = ActionResult(
                    authoritative.action_type,
                    False,
                    metadata={
                        **dict(result.metadata),
                        "invalid_external_evidence": dict(external_evidence),
                    },
                    error={
                        "type": "ExternalEvidenceContractError",
                        "message": str(exc)[:2000],
                    },
                )
            else:
                bound_evidence = envelope.to_dict()
                result.metadata = dict(result.metadata)
                result.metadata["external_evidence"] = bound_evidence
                result.output = canonical_json(bound_evidence)
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
            if (
                definition.recovery_policy
                == "resume_committed_snapshot_or_do_not_replay_unknown"
            ):
                with self.harness.action_transaction(state.goal):
                    recovered = self.harness.recover_committed_action(
                        TaskAction(record.action_type, dict(record.arguments)),
                        state.goal,
                    )
                if recovered is not None:
                    self._finish_action(state, record, recovered)
                    if recovered.success:
                        self._persist(
                            state,
                            "committed_snapshot_action_recovered",
                            {
                                "action_id": action_id,
                                "operation": record.action_type,
                                "provider_replayed": False,
                            },
                        )
                    return
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
        with self.harness.action_transaction(state.goal):
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
                f"{action.action_id}:{index}:{observed.path}:{observed.sha256}".encode()
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
        external = result.metadata.get("external_evidence")
        if isinstance(external, Mapping):
            stable_output: Any = {
                "route_id": str(external.get("route_id") or ""),
                "request_digest": str(external.get("request_digest") or ""),
                "status": str(external.get("status") or ""),
                "evidence_record_ids": [
                    str(item.get("evidence_record_id") or "")
                    for item in external.get("records") or ()
                    if isinstance(item, Mapping)
                ],
            }
        else:
            stable_output = result.output
        return canonical_digest(
            {
                "operation": action.action_type,
                "target": target,
                "outcome_type": result.outcome_type,
                "exit_code": result.exit_code,
                "error": result.error,
                "output": stable_output,
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
                "result": self._model_action_result(
                    action.result or {},
                    arguments=action.arguments,
                ),
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

    @staticmethod
    def _bounded_model_value(value: Any, *, depth: int = 0) -> Any:
        if depth >= 4:
            return None
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            return value[:2000]
        if isinstance(value, Mapping):
            return {
                str(key)[:160]: projected
                for key, item in list(value.items())[:32]
                if (
                    projected := LongHorizonController._bounded_model_value(
                        item, depth=depth + 1
                    )
                )
                is not None
            }
        if isinstance(value, (list, tuple)):
            return [
                projected
                for item in value[:12]
                if (
                    projected := LongHorizonController._bounded_model_value(
                        item, depth=depth + 1
                    )
                )
                is not None
            ]
        return str(value)[:500]

    _STRUCTURED_FIELD_PRIORITY = (
        "full_name",
        "default_branch",
        "html_url",
        "tag_name",
        "published_at",
        "sha",
        "name",
        "version",
        "info",
        "message",
        "current",
        "current_units",
        "timezone",
        "latitude",
        "longitude",
        "DOI",
        "doi",
        "title",
        "published",
        "author",
        "url",
    )
    _EVIDENCE_QUERY_TOKEN_PATTERN = re.compile(r"[a-z0-9]+|[\u3400-\u9fff]")
    _EVIDENCE_PROJECTION_VERSION = "query-exact-source-chunk.v2"

    @classmethod
    def _evidence_query_terms(cls, query: str) -> tuple[str, ...]:
        """Return frozen exact-match terms without adding semantic expansion."""

        return tuple(
            dict.fromkeys(
                cls._EVIDENCE_QUERY_TOKEN_PATTERN.findall(str(query).casefold())
            )
        )

    @staticmethod
    def _evidence_search_text(record: Mapping[str, Any]) -> str:
        spans = [
            str(span.get("text") or "")
            for span in record.get("exact_spans") or ()
            if isinstance(span, Mapping)
        ]
        return "\n".join(
            (
                str(record.get("title") or ""),
                canonical_json(record.get("structured_fields") or {}),
                *spans,
            )
        ).casefold()

    @staticmethod
    def _evidence_match_score(
        text: str,
        terms: tuple[str, ...],
    ) -> tuple[int, int]:
        matched = tuple(term for term in terms if term and term in text)
        return sum(len(term) for term in matched), len(matched)

    @classmethod
    def _evidence_projection_window(
        cls,
        source_text: str,
        terms: tuple[str, ...],
        *,
        limit: int = 512,
    ) -> tuple[int, str]:
        folded = source_text.casefold()
        matches = [
            (len(term), folded.find(term), term)
            for term in terms
            if term and folded.find(term) >= 0
        ]
        if matches:
            _length, position, _term = min(
                matches,
                key=lambda item: (-item[0], item[1], item[2]),
            )
            start = max(0, position - 128)
        else:
            start = 0
        return start, source_text[start : start + max(1, int(limit))]

    @classmethod
    def _best_record_per_source(
        cls,
        records: list[Mapping[str, Any]],
        terms: tuple[str, ...],
    ) -> list[Mapping[str, Any]]:
        source_order: list[str] = []
        selected: dict[str, tuple[tuple[int, int], int, Mapping[str, Any]]] = {}
        for index, item in enumerate(records):
            source = item.get("source_object")
            source_id = (
                str(source.get("source_object_id") or "")
                if isinstance(source, Mapping)
                else ""
            )
            identity = source_id or str(item.get("url") or "") or str(
                item.get("evidence_record_id") or ""
            )
            if identity not in selected:
                source_order.append(identity)
            score = cls._evidence_match_score(
                cls._evidence_search_text(item),
                terms,
            )
            previous = selected.get(identity)
            if previous is None or score > previous[0]:
                selected[identity] = (score, index, item)
        return [selected[identity][2] for identity in source_order]

    @classmethod
    def _structured_model_value(
        cls,
        value: Any,
        *,
        budget: int = 1400,
        depth: int = 0,
    ) -> Any:
        """Project structured facts into a deterministic total character budget."""

        limit = max(2, int(budget))
        if value is None or isinstance(value, (bool, int, float)):
            return value
        if isinstance(value, str):
            overhead = 2
            return value[: max(0, min(300, limit - overhead))]
        if depth >= 3:
            return None
        if isinstance(value, Mapping):
            keys = [key for key in cls._STRUCTURED_FIELD_PRIORITY if key in value]
            keys.extend(key for key in value if key not in keys)
            projected: dict[str, Any] = {}
            for raw_key in keys[:32]:
                key = str(raw_key)[:160]
                remaining = limit - len(canonical_json(projected)) - len(key) - 6
                if remaining < 8:
                    break
                item = cls._structured_model_value(
                    value[raw_key],
                    budget=remaining,
                    depth=depth + 1,
                )
                if item is None:
                    continue
                candidate = {**projected, key: item}
                if len(canonical_json(candidate)) > limit:
                    continue
                projected = candidate
            return projected
        if isinstance(value, (list, tuple)):
            projected_items: list[Any] = []
            for item in value[:3]:
                remaining = limit - len(canonical_json(projected_items)) - 2
                if remaining < 8:
                    break
                projected = cls._structured_model_value(
                    item,
                    budget=remaining,
                    depth=depth + 1,
                )
                if projected is None:
                    continue
                candidate = [*projected_items, projected]
                if len(canonical_json(candidate)) > limit:
                    continue
                projected_items = candidate
            return projected_items
        return str(value)[: max(0, min(300, limit - 2))]

    @classmethod
    def _model_action_result(
        cls,
        result: Mapping[str, Any],
        *,
        arguments: Mapping[str, Any] | None = None,
        evidence_source_limit: int = 2,
        evidence_span_chars: int = 512,
        structured_field_budget: int = 1400,
    ) -> dict[str, Any]:
        """Project full durable results into one bounded RWKV observation."""

        source_limit = max(1, int(evidence_source_limit))
        span_limit = max(1, int(evidence_span_chars))
        structured_budget = max(8, int(structured_field_budget))

        selected = dict(result)
        raw_metadata = selected.get("metadata")
        metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
        external = metadata.get("external_evidence")
        if isinstance(external, Mapping):
            raw_records = [
                item
                for item in selected.get("evidence") or ()
                if isinstance(item, Mapping)
            ]
            query = str((arguments or {}).get("query") or "")
            query_terms = cls._evidence_query_terms(query)
            source_records = cls._best_record_per_source(raw_records, query_terms)
            records: list[dict[str, Any]] = []
            for item in source_records:
                source = item.get("source_object")
                source_id = (
                    str(source.get("source_object_id") or "")
                    if isinstance(source, Mapping)
                    else ""
                )
                spans: list[dict[str, Any]] = []
                candidate_spans = [
                    span
                    for span in item.get("exact_spans") or ()
                    if isinstance(span, Mapping)
                ]
                candidate_spans.sort(
                    key=lambda span: cls._evidence_match_score(
                        str(span.get("text") or "").casefold(),
                        query_terms,
                    ),
                    reverse=True,
                )
                for span in candidate_spans[:1]:
                    source_text = str(span.get("text") or "")
                    source_offset, projected_text = cls._evidence_projection_window(
                        source_text,
                        query_terms,
                        limit=span_limit,
                    )
                    source_locator = cls._bounded_model_value(
                        span.get("locator") or {}
                    )
                    start_char = (
                        int(source_locator.get("start_char", 0) or 0)
                        if isinstance(source_locator, Mapping)
                        else 0
                    )
                    spans.append(
                        {
                            "source_span_id": str(span.get("span_id") or ""),
                            "text": projected_text,
                            "text_sha256": hashlib.sha256(
                                projected_text.encode("utf-8")
                            ).hexdigest(),
                            "source_text_chars": len(source_text),
                            "projection": {
                                "source_offset_start": source_offset,
                                "source_offset_end": source_offset
                                + len(projected_text),
                                "document_start_char": start_char + source_offset,
                                "document_end_char": start_char
                                + source_offset
                                + len(projected_text),
                                "complete_source_span": len(projected_text)
                                == len(source_text)
                                and source_offset == 0,
                            },
                            "source_locator": source_locator,
                        }
                    )
                records.append(
                    {
                        "evidence_record_id": str(
                            item.get("evidence_record_id") or ""
                        ),
                        "source_object_id": source_id,
                        "source_object_type": (
                            str(source.get("source_object_type") or "")
                            if isinstance(source, Mapping)
                            else ""
                        ),
                        "snapshot_digest": str(item.get("snapshot_digest") or ""),
                        "url": str(item.get("url") or ""),
                        "title": str(item.get("title") or ""),
                        "published": str(item.get("published") or ""),
                        "structured_fields": cls._structured_model_value(
                            item.get("structured_fields") or {},
                            budget=structured_budget,
                        ),
                        "exact_spans": spans,
                    }
                )
                if len(records) >= source_limit:
                    break
            external_identity = {
                key: cls._bounded_model_value(external.get(key))
                for key in (
                    "route_id",
                    "request_digest",
                    "status",
                    "as_of",
                    "provider_attempts",
                    "truncated",
                )
                if external.get(key) is not None
            }
            return {
                "success": bool(selected.get("success")),
                "outcome_type": str(selected.get("outcome_type") or ""),
                "action_type": str(selected.get("action_type") or ""),
                "error": cls._bounded_model_value(selected.get("error") or {}),
                "metadata": {
                    "network_policy": cls._bounded_model_value(
                        metadata.get("network_policy") or {}
                    ),
                    "external_evidence": external_identity,
                    "projection_complete": False,
                },
                "evidence": records,
                "evidence_projection": {
                    "full_record_count": len(raw_records),
                    "projected_source_count": len(records),
                    "content_addressed_full_result_persisted": True,
                    "selection_protocol": cls._EVIDENCE_PROJECTION_VERSION,
                    "query_digest": hashlib.sha256(
                        query.encode("utf-8")
                    ).hexdigest(),
                },
            }
        output = str(selected.get("output") or "")
        if len(output) > 8000:
            selected["output"] = output[:8000]
            metadata["source_complete"] = metadata.get("complete", True)
            metadata["complete"] = False
            metadata["projection_complete"] = False
            selected["metadata"] = metadata
            selected["output_projection"] = {
                "truncated": True,
                "original_chars": len(output),
                "retained_chars": 8000,
                "full_sha256": hashlib.sha256(output.encode("utf-8")).hexdigest(),
            }
        return selected

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

    def _pending_idempotent_mutation_repeat_event(
        self,
        state: RunState,
    ) -> ModelEvent | None:
        """Recover a committed repeat boundary without replaying a mutation."""

        for event_id in reversed(state.causal_order):
            event = state.causal_records[event_id]
            if event.event_type != "idempotent_mutation_repeat_boundary":
                continue
            action_id = str(event.payload.get("action_id") or "")
            model_event_id = f"EV-MUTATION-REPEAT-{action_id}"
            if model_event_id in state.model_events:
                return None
            action = state.actions.get(action_id)
            if action is None or action.status != ActionStatus.SUCCEEDED:
                raise ValueError(
                    "idempotent mutation repeat boundary has no successful action"
                )
            count = int(event.payload.get("identical_result_count", 0) or 0)
            return ModelEvent(
                event_type="idempotent_mutation_repeat_boundary",
                event_id=model_event_id,
                scope_id=self.model.ACTION_LANE_ID,
                payload={
                    "instruction": (
                        "This exact idempotent workspace mutation already "
                        "succeeded, and its latest repeat changed no workspace "
                        "bytes. Return final_answer now using committed facts; "
                        "do not repeat the operation."
                    ),
                    "identical_result_count": count,
                    "last_action_result": self._action_observation_event(
                        state,
                        action,
                    ).to_model_dict(),
                },
            )
        return None

    def _terminal_output(
        self,
        state: RunState,
        reason: str,
        pending_event: ModelEvent | None,
    ) -> str:
        if self._goal_self_termination_only(state):
            # A controller boundary is not permission to coerce a Final in Goal
            # mode.  Persist a resumable checkpoint; the next slice restores the
            # same RWKV lane and appends the pending action observation.
            self._persist(
                state,
                "run_interrupted",
                {
                    "reason": reason,
                    "decision_id": "",
                    "output_source": "none",
                    "controller_rewritten": False,
                    "final_output_sha256": hashlib.sha256(b"").hexdigest(),
                    "final_output": "",
                    "pending_event_id": (
                        pending_event.event_id if pending_event is not None else ""
                    ),
                },
            )
            return ""
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

    def _persist_supervisor_pending(self, state: RunState, *, phase: str) -> None:
        """Record a durable retry boundary; a later resume re-enters this phase."""

        attempts = 1 + sum(
            1
            for event_id in state.causal_order
            if state.causal_records[event_id].event_type == "supervisor_call_pending"
            and str(state.causal_records[event_id].payload.get("phase") or "") == phase
        )
        self._persist(
            state,
            "supervisor_call_pending",
            {
                "pending_id": f"SUP-PENDING-{phase}-{attempts:04d}",
                "phase": phase,
                "attempt": attempts,
                "state": "pending_retry",
                "retry_trigger": "resume_or_proactive_scheduler",
                "retry_policy": {
                    "transport_retries_are_owned_by_supervisor_client": True,
                    "controller_inline_replay": False,
                    "reenter_from_committed_causal_state": True,
                },
                "at": utc_now(),
            },
            subject_id=f"supervisor:{phase}",
        )

    def _persist_supervisor_resolved(self, state: RunState, *, phase: str) -> None:
        """Consume every durable pending boundary satisfied by this phase call."""

        for pending in unresolved_supervisor_pending(state):
            if str(pending.get("phase") or "") != phase:
                continue
            self._persist_supervisor_pending_resolution(state, pending)

    def _persist_supervisor_pending_resolution(
        self,
        state: RunState,
        pending: Mapping[str, Any],
    ) -> None:
        phase = str(pending.get("phase") or "")
        pending_id = str(pending.get("pending_id") or "")
        if not phase or not pending_id:
            return
        self._persist(
            state,
            "supervisor_call_resolved",
            {
                "pending_id": pending_id,
                "phase": phase,
                "attempt": int(pending.get("attempt", 0) or 0),
                "state": "resolved",
                "resolution": "validated_supervisor_response_committed",
                "at": utc_now(),
            },
            subject_id=pending_id,
        )

    def _reconcile_supervisor_pending(self, state: RunState) -> None:
        """Close a crash window after response commit but before resolution."""

        success_phases = {
            "supervisor_plan_committed": "plan",
            "supervisor_review_recorded": "review",
            "supervisor_directive_committed": "directive",
            "supervisor_stage_committed": "stage",
            "contract_graph_patch_committed": "contract_plan",
            "contract_graph_review_committed": "contract_review",
            "contract_final_presentation_review_committed": (
                "contract_final_presentation_review"
            ),
        }
        pending_sequences = {
            str(event.payload.get("pending_id") or ""): event.sequence
            for event in state.causal_records.values()
            if event.event_type == "supervisor_call_pending"
            and str(event.payload.get("pending_id") or "")
        }
        for pending in unresolved_supervisor_pending(state):
            pending_id = str(pending.get("pending_id") or "")
            phase = str(pending.get("phase") or "")
            pending_sequence = pending_sequences.get(pending_id, 0)
            if not pending_id or not phase or not pending_sequence:
                continue
            committed_after = any(
                event.sequence > pending_sequence
                and success_phases.get(event.event_type) == phase
                for event in state.causal_records.values()
            )
            if committed_after:
                self._persist_supervisor_pending_resolution(state, pending)

    def _persist(
        self,
        state: RunState,
        event_type: str,
        event: Mapping[str, Any],
        *,
        subject_id: str | None = None,
    ) -> None:
        selected_event_type = str(event_type)
        selected_event = dict(event)
        if self._goal_self_termination_only(state):
            if selected_event_type == "run_completed" and not model_voluntary_completion(
                selected_event
            ):
                raise ValueError(
                    "Goal mode completion must reference an explicit RWKV final decision"
                )
            if selected_event_type in {
                "run_interrupted",
                "run_failed",
            }:
                candidate_output = str(selected_event.get("final_output") or "")
                selected_event = {
                    "reason": str(
                        selected_event.get("reason")
                        or selected_event_type.removeprefix("run_")
                    ),
                    "boundary_type": selected_event_type,
                    "resumable": True,
                    "termination_permitted": False,
                    "continuation": "controller_resume",
                    "candidate_decision_id": str(
                        selected_event.get("decision_id") or ""
                    ),
                    "candidate_output_source": str(
                        selected_event.get("output_source") or "none"
                    ),
                    "candidate_output_sha256": hashlib.sha256(
                        candidate_output.encode("utf-8")
                    ).hexdigest(),
                    "candidate_output": candidate_output,
                    "at": utc_now(),
                }
                selected_event_type = "run_yielded"
        subject_keys = {
            "action_session_started": "lane_id",
            "action_session_rolled_over": "rollover_id",
            "selector_state_cache_rebuilt": "checkpoint_id",
            "model_call_accepted": "decision_id",
            "model_call_rejected": "decision_id",
            "tool_selection_accepted": "decision_id",
            "tool_selection_rejected": "decision_id",
            "tool_schema_disclosed": "checkpoint_id",
            "exact_tool_selection_committed": "selection_id",
            "exact_tool_selection_staged": "selection_id",
            "exact_tool_selection_consumed": "selection_id",
            "exact_tool_selection_discarded": "selection_id",
            "exact_tool_selection_rejected": "selection_id",
            "protocol_rejection_recorded": "decision_id",
            "action_started": "action_id",
            "action_finished": "action_id",
            "idempotent_mutation_repeat_boundary": "action_id",
            "action_observation_appended": "event_id",
            "stale_active_action_cleared": "action_id",
            "idempotent_action_recovered": "action_id",
            "committed_snapshot_action_recovered": "action_id",
            "supervisor_plan_committed": "plan_id",
            "supervisor_directive_committed": "directive_id",
            "supervisor_stage_committed": "stage_id",
            "atom_attempt_started": "atom_id",
            "atom_outcome_committed": "atom_id",
            "supervisor_review_recorded": "review_id",
        }
        subject_key = subject_keys.get(selected_event_type)
        selected_subject = (
            str(subject_id)
            if subject_id is not None
            else str(selected_event.get(subject_key) or state.run_id)
            if subject_key
            else state.run_id
        )
        draft = CausalEventDraft.create(
            selected_event_type,
            selected_event,
            subject_id=selected_subject,
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
