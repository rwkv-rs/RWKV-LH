"""Single-controller state machine for persistent Long-Horizon runs."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from rwkv_lh.harness import ActionHarness, ActionResult, HarnessError
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import (
    ActionProposal,
    CrossValidationDecision,
    FailureAnalysisProposal,
    GoalObligationProposal,
    LongHorizonModel,
    ModelProtocolError,
    PersistCallback,
    ReplanProposal,
)
from rwkv_lh.proof import CriterionProofEngine
from rwkv_lh.schema import (
    ArtifactRecord,
    ArtifactRevision,
    Attempt,
    AttemptStatus,
    CriterionEvidence,
    CriterionEvidenceStatus,
    CriterionClaim,
    CriterionClaimStatus,
    EvidenceRef,
    GoalObligationState,
    GoalObligationStatus,
    ProofExpr,
    MemoryEntry,
    RunState,
    RunStatus,
    RecoveryState,
    TaskCommitStatus,
    TaskEffectStatus,
    TaskStatus,
    TaskAction,
    ValidationResult,
    ValidationSpec,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore, StateStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.token_budget import get_token_count
from rwkv_lh.validation import ValidationEngine


class PlannerModel(Protocol):
    def plan(self, state: RunState, persist: PersistCallback) -> list: ...

    def propose_action(self, state, task, context, action_contract, persist): ...

    def commit_criterion_evidence(
        self,
        state,
        context,
        persist,
        *,
        criterion_ids,
        source_catalog,
    ): ...

    def plan_goal_obligations(
        self,
        state: RunState,
        capsule: Mapping[str, Any],
        persist: PersistCallback,
    ) -> GoalObligationProposal: ...

    def replan(self, state, failed_task, context, persist, *, same_failure_count: int) -> ReplanProposal: ...

    def analyze_failure(self, state, failed_task, context, persist, *, same_failure_count: int) -> FailureAnalysisProposal: ...

    def final_answer(self, state: RunState, context: str, persist: PersistCallback) -> str: ...


@dataclass
class ControllerResult:
    state: RunState
    final_output: str
    transitions: int


class LongHorizonController:
    _MODEL_WRITTEN_TARGET_PROOF_FAILURE = (
        "actual and expected share model-written workspace target lineage"
    )
    _POST_ACTION_SNAPSHOT_SCHEMA = (
        "rwkv-lh.post-action-workspace-snapshot.v1"
    )
    _POST_ACTION_SNAPSHOT_ACTIONS = frozenset(
        {"write_file", "write_json", "append_file", "copy_file"}
    )
    _POST_ACTION_SNAPSHOT_CONTENT_LIMIT_BYTES = 20_000

    def __init__(
        self,
        store: StateStore | None = None,
        *,
        model: PlannerModel | None = None,
        harness: ActionHarness | None = None,
        validator: ValidationEngine | None = None,
        memory: WorkingMemoryBuilder | None = None,
        proof_engine: CriterionProofEngine | None = None,
        max_transitions: int = 500,
        max_goal_expansions: int = 64,
        max_parallel_tasks: int = 8,
    ):
        self.store = store or LongHorizonStore()
        self.model = model
        self.harness = harness or ActionHarness()
        self.validator = validator or ValidationEngine(self.harness)
        self.memory = memory or WorkingMemoryBuilder()
        artifact_resolver = getattr(self.store, "resolve_artifact_locator", None)
        self.proof_engine = proof_engine or CriterionProofEngine(
            self.harness,
            artifact_resolver=(artifact_resolver if callable(artifact_resolver) else None),
        )
        self.max_transitions = max(1, int(max_transitions))
        self.max_goal_expansions = max(1, int(max_goal_expansions))
        self.max_parallel_tasks = max(1, min(32, int(max_parallel_tasks)))

    def run(self, run_id: str) -> ControllerResult:
        with self.store.controller_lease(run_id):
            state = self.store.load(run_id)
            if state.status == RunStatus.COMPLETED:
                return ControllerResult(state, self._final_output(state), 0)
            if not state.goal.verify_digest():
                state.status = RunStatus.BLOCKED
                self._persist(state, "run_blocked", {"reason": "goal_digest_mismatch"})
                return ControllerResult(state, "", 0)
            transitions = 0
            try:
                self._recover_interrupted_attempt(state)
                self._recover_failed_tasks(state)
                if state.status == RunStatus.BLOCKED:
                    return ControllerResult(state, self._final_output(state), transitions)
                if not state.tasks:
                    self._create_plan(state)
                    transitions += 1
                    if state.status == RunStatus.BLOCKED:
                        return ControllerResult(state, self._final_output(state), transitions)
                while transitions < self.max_transitions:
                    graph = TaskGraph(state.tasks)
                    skipped = self._skip_unselected_outcome_tasks(state, graph)
                    if skipped:
                        self._persist(
                            state,
                            "dependency_outcome_branches_skipped",
                            {"task_ids": skipped},
                        )
                    if graph.required_complete():
                        invalidated_claim_ids = self._revalidate_goal_proofs(state)
                        self._sync_goal_obligation_state(state)
                        if self._goal_criteria_covered(state):
                            output = self._complete_run(state)
                            return ControllerResult(state, output, transitions)
                        self._commit_goal_criterion_evidence(state)
                        self._sync_goal_obligation_state(state)
                        if self._goal_criteria_covered(state):
                            output = self._complete_run(state)
                            return ControllerResult(state, output, transitions)
                        extended = self._advance_goal_obligations(
                            state,
                            graph,
                            invalidated_claim_ids=invalidated_claim_ids,
                        )
                        transitions += 1
                        if extended:
                            continue
                        return ControllerResult(
                            state,
                            self._final_output(state),
                            transitions,
                        )
                    ready = graph.ready_tasks()
                    if not ready:
                        self._block_unreachable_tasks(state, graph)
                        state.status = RunStatus.BLOCKED
                        self._persist(
                            state,
                            "run_blocked",
                            {"reason": "no_ready_required_tasks", "unresolved": [task.task_id for task in graph.unresolved_required()]},
                        )
                        return ControllerResult(state, self._final_output(state), transitions)
                    executed = self._execute_ready_frontier(state, graph, ready)
                    transitions += max(1, executed)
                    if state.status == RunStatus.BLOCKED:
                        return ControllerResult(state, self._final_output(state), transitions)
                state.status = RunStatus.INTERRUPTED
                self._persist(state, "run_interrupted", {"reason": "controller_transition_limit"})
                return ControllerResult(state, self._final_output(state), transitions)
            except BaseException as exc:
                if not isinstance(exc, (KeyboardInterrupt, SystemExit)):
                    state.errors.append(
                        {
                            "task_id": state.active_task_id,
                            "type": type(exc).__name__,
                            "message": str(exc)[:2000],
                            "at": utc_now(),
                        }
                    )
                state.status = RunStatus.INTERRUPTED
                self._persist(
                    state,
                    "run_interrupted",
                    {"reason": f"{type(exc).__name__}: {exc}"[:2000]},
                )
                raise

    def resume(self, run_id: str) -> ControllerResult:
        return self.run(run_id)

    def _create_plan(self, state: RunState) -> None:
        if self.model is None:
            raise RuntimeError("a model is required when the run has no task graph")
        state.status = RunStatus.PLANNING
        self._persist(state, "planning_started", {})
        try:
            proposed_tasks = self.model.plan(state, self._persist_callback())
        except ModelProtocolError as exc:
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "model_protocol_blocked",
                {
                    "phase": "plan_materialization",
                    "error": str(exc)[:2000],
                },
            )
            return
        tasks, local_to_global, next_sequence = TaskGraph.materialize_model_tasks(
            proposed_tasks,
            next_sequence=state.next_task_sequence,
        )
        graph = TaskGraph()
        graph.add_tasks(tasks)
        state.tasks = graph.tasks
        state.next_task_sequence = next_sequence
        state.plan_generation += 1
        state.status = RunStatus.RUNNING
        required_ids = sorted(
            criterion.criterion_id
            for criterion in state.goal.success_criteria
            if criterion.required
        )
        unassigned_ids = sorted(
            set(required_ids)
            - {
                criterion_id
                for task in state.tasks.values()
                for criterion_id in task.satisfies_criteria
            }
        )
        state.goal_obligation = GoalObligationState(
            goal_digest=state.goal.digest,
            unresolved_criterion_ids=required_ids,
            status=GoalObligationStatus.UNRESOLVED,
            remaining_budget=self.max_goal_expansions,
        )
        self._persist(
            state,
            "goal_obligation_state_created",
            {
                "goal_digest": state.goal.digest,
                "unresolved_criterion_ids": required_ids,
                "unassigned_criterion_ids": unassigned_ids,
                "remaining_budget": state.goal_obligation.remaining_budget,
                "source": "immutable_goal_and_rwkv_plan",
            },
        )
        self._persist(
            state,
            "plan_saved",
            {
                "task_ids": list(state.tasks),
                "local_to_global": local_to_global,
                "plan_generation": state.plan_generation,
            },
        )

    def _sync_goal_obligation_state(self, state: RunState) -> None:
        missing = self._missing_goal_criteria(state)
        obligation = state.goal_obligation
        if obligation is None:
            obligation = GoalObligationState(
                goal_digest=state.goal.digest,
                unresolved_criterion_ids=missing,
                status=(
                    GoalObligationStatus.UNRESOLVED
                    if missing
                    else GoalObligationStatus.RESOLVED
                ),
                remaining_budget=self.max_goal_expansions,
            )
            state.goal_obligation = obligation
            self._persist(
                state,
                "goal_obligation_state_created",
                {
                    "goal_digest": state.goal.digest,
                    "unresolved_criterion_ids": missing,
                    "unassigned_criterion_ids": [],
                    "remaining_budget": obligation.remaining_budget,
                    "source": "authoritative_state_projection",
                },
            )
            return
        if obligation.goal_digest != state.goal.digest:
            raise ValueError("goal obligation digest does not match immutable Goal")
        next_status = (
            GoalObligationStatus.UNRESOLVED
            if missing
            else GoalObligationStatus.RESOLVED
        )
        if (
            obligation.unresolved_criterion_ids == missing
            and obligation.status == next_status
        ):
            return
        previous = list(obligation.unresolved_criterion_ids)
        obligation.unresolved_criterion_ids = missing
        obligation.status = next_status
        obligation.updated_at = utc_now()
        self._persist(
            state,
            "goal_obligation_state_updated",
            {
                "goal_digest": state.goal.digest,
                "previous_unresolved_criterion_ids": previous,
                "unresolved_criterion_ids": missing,
                "remaining_budget": obligation.remaining_budget,
                "source": "verified_criterion_evidence",
            },
        )

    def _goal_obligation_capsule(
        self,
        state: RunState,
        *,
        invalidated_claim_ids: list[str],
    ) -> dict[str, Any]:
        """Project the same causal ledger used by execution into frontier expansion."""

        missing = set(self._missing_goal_criteria(state))
        active_tasks = [
            task
            for task in sorted(
                state.tasks.values(),
                key=lambda item: (item.insertion_order, item.task_id),
            )
            if task.active
        ]
        selected_tasks = active_tasks[-12:]
        indexed_tasks = active_tasks[-128:]
        latest_revisions = [
            revision
            for target in sorted(state.artifact_revisions)
            for revision in state.artifact_revisions[target][-1:]
        ][-32:]
        action_memories = [
            entry
            for entry in sorted(
                state.memory_index.values(),
                key=lambda item: (item.created_at, item.memory_id),
            )
            if entry.kind == "action_result" and entry.task_id in state.tasks
        ][-128:]
        action_observations = []
        for entry in action_memories:
            task = state.tasks[entry.task_id]
            action_arguments = {
                key: value
                for key, value in task.action.arguments.items()
                if key
                in {
                    "path",
                    "source",
                    "destination",
                    "start_char",
                    "start_after",
                    "recursive",
                }
            }
            content = entry.content or entry.summary
            content_limit = 6000 if task.action.action_type == "list_directory" else 0
            observation_metadata: dict[str, Any] = {}
            marker = "\n\nACTION RESULT METADATA\n"
            if marker in content:
                _, metadata_text = content.rsplit(marker, 1)
                try:
                    parsed_metadata = json.loads(metadata_text)
                except (TypeError, ValueError):
                    parsed_metadata = {}
                if isinstance(parsed_metadata, Mapping):
                    observation_metadata = {
                        key: parsed_metadata[key]
                        for key in {
                            "next_cursor",
                            "next_start_char",
                            "complete",
                            "truncated",
                        }
                        if key in parsed_metadata
                    }
            observation = {
                    "memory_id": entry.memory_id,
                    "task_id": task.task_id,
                    "action": {
                        "name": task.action.action_type,
                        "arguments": action_arguments,
                    },
                    "outcome_type": task.outcome_type,
                    "content": content[:content_limit],
                    "content_truncated": len(content) > content_limit,
                }
            if observation_metadata:
                observation["metadata"] = observation_metadata
            action_observations.append(observation)
        workspace_manifest = self.harness.workspace_manifest(state.goal, max_entries=32)
        workspace_observation = self.harness.workspace_observation_snapshot(state.goal)
        unchanged_failures = self._unchanged_deterministic_proof_failures(
            state,
            workspace_observation,
        )
        previous_suppression = next(
            (
                item
                for item in reversed(
                    state.goal_obligation.decision_history
                    if state.goal_obligation is not None
                    else []
                )
                if item.get("type")
                == "unchanged_deterministic_proof_proposal_suppressed"
            ),
            None,
        )
        capsule: dict[str, Any] = {
            "schema_version": "long-horizon.goal-obligation-capsule.v2",
            "goal_digest": state.goal.digest,
            "unresolved_criteria": [
                {
                    "criterion_id": criterion.criterion_id,
                    "description": criterion.description,
                    "required": criterion.required,
                }
                for criterion in state.goal.success_criteria
                if criterion.criterion_id in missing
            ],
            "plan_generation": state.plan_generation,
            "active_task_index": {
                "fields": [
                    "task_id",
                    "status",
                    "dependencies",
                    "operation_kind",
                    "member_key",
                    "effect_targets",
                    "satisfies_criteria",
                ],
                "rows": [
                    [
                        task.task_id,
                        task.status.value,
                        list(task.dependencies),
                        task.operation_kind,
                        task.member_key,
                        list(task.effect_targets)[:8],
                        list(task.satisfies_criteria),
                    ]
                    for task in indexed_tasks
                ],
            },
            "active_tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title[:120],
                    "description": task.description[:320],
                    "postcondition": task.postcondition[:320],
                    "status": task.status.value,
                    "outcome_type": task.outcome_type,
                    "dependencies": list(task.dependencies),
                    "dependency_outcomes": task.dependency_outcomes,
                    "operation_kind": task.operation_kind,
                    "subject_key": task.subject_key,
                    "member_key": task.member_key,
                    "phase_key": task.phase_key,
                    "effect_targets": list(task.effect_targets),
                    "advances_criteria": list(task.advances_criteria),
                    "satisfies_criteria": list(task.satisfies_criteria),
                    "output_refs": list(task.output_refs),
                }
                for task in selected_tasks
            ],
            "artifact_revisions": [vars(item) for item in latest_revisions],
            "criterion_evidence": [
                evidence.to_dict()
                for evidence in sorted(
                    state.criterion_evidence.values(),
                    key=lambda item: (item.verified_at, item.evidence_id),
                )[-16:]
            ],
            "invalidated_claim_ids": sorted(invalidated_claim_ids),
            "workspace_manifest": workspace_manifest,
            "workspace_observation": {
                "cacheable": bool(workspace_observation.get("cacheable", False)),
                "digest": str(workspace_observation.get("digest") or ""),
                "reason": str(workspace_observation.get("reason") or ""),
                "entry_count": int(workspace_observation.get("entry_count", 0) or 0),
                "total_bytes": int(workspace_observation.get("total_bytes", 0) or 0),
            },
            "unchanged_failed_verifier_tasks": unchanged_failures[-12:],
            "recovery_feedback": (
                {
                    "type": previous_suppression.get("type"),
                    "workspace_digest": previous_suppression.get("workspace_digest", ""),
                    "conflicts": previous_suppression.get("conflicts", []),
                    "entire_proposal_rejected": True,
                }
                if previous_suppression is not None
                else None
            ),
            "action_observations": action_observations,
            "artifacts": [
                vars(artifact)
                for artifact in sorted(
                    state.artifacts.values(),
                    key=lambda item: (item.created_at, item.artifact_id),
                )[-32:]
            ],
            "projection": {
                "active_task_count": len(active_tasks),
                "included_index_task_count": len(indexed_tasks),
                "excluded_index_task_ids": [
                    task.task_id for task in active_tasks[: -len(indexed_tasks)]
                ]
                if len(active_tasks) > len(indexed_tasks)
                else [],
                "included_detailed_task_count": len(selected_tasks),
                "excluded_detailed_task_ids": [
                    task.task_id for task in active_tasks[: -len(selected_tasks)]
                ]
                if len(active_tasks) > len(selected_tasks)
                else [],
                "action_observation_count": sum(
                    entry.kind == "action_result"
                    for entry in state.memory_index.values()
                ),
                "included_action_observation_count": len(action_observations),
                "excluded_action_observation_ids": [
                    entry.memory_id
                    for entry in action_memories[: -len(action_observations)]
                ],
                "artifact_count": len(state.artifacts),
                "included_artifact_count": min(32, len(state.artifacts)),
                "excluded_artifact_ids": [
                    item.artifact_id
                    for item in sorted(
                        state.artifacts.values(),
                        key=lambda entry: (entry.created_at, entry.artifact_id),
                    )[:-32]
                ],
                "criterion_evidence_count": len(state.criterion_evidence),
                "included_criterion_evidence_count": min(
                    16,
                    len(state.criterion_evidence),
                ),
                "excluded_criterion_evidence_ids": [],
                "included_workspace_entry_count": len(
                    workspace_manifest.get("entries") or []
                ),
                "excluded_workspace_paths": [],
                "task_text_truncated": any(
                    len(task.title) > 120
                    or len(task.description) > 320
                    or len(task.postcondition) > 320
                    for task in selected_tasks
                ),
                "capsule_tokens": 0,
            },
        }

        def measure() -> int:
            return get_token_count(
                json.dumps(
                    capsule,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

        projection = capsule["projection"]
        while measure() > 5000:
            if capsule["active_tasks"]:
                removed = capsule["active_tasks"].pop(0)
                projection["excluded_detailed_task_ids"].append(removed["task_id"])
                projection["included_detailed_task_count"] = len(
                    capsule["active_tasks"]
                )
            elif capsule["artifact_revisions"]:
                capsule["artifact_revisions"].pop(0)
            elif capsule["artifacts"]:
                removed = capsule["artifacts"].pop(0)
                projection["excluded_artifact_ids"].append(
                    removed["artifact_id"]
                )
                projection["included_artifact_count"] = len(
                    capsule["artifacts"]
                )
            elif capsule["criterion_evidence"]:
                capsule["criterion_evidence"].pop(0)
                projection["included_criterion_evidence_count"] = len(
                    capsule["criterion_evidence"]
                )
            elif capsule["workspace_manifest"].get("entries"):
                removed = capsule["workspace_manifest"]["entries"].pop()
                projection["excluded_workspace_paths"].append(removed.get("path", ""))
                projection["included_workspace_entry_count"] = len(
                    capsule["workspace_manifest"]["entries"]
                )
            elif len(capsule["action_observations"]) > 1:
                removed = capsule["action_observations"].pop(0)
                projection["excluded_action_observation_ids"].append(
                    removed["memory_id"]
                )
                projection["included_action_observation_count"] = len(
                    capsule["action_observations"]
                )
            elif len(capsule["active_task_index"]["rows"]) > 1:
                removed = capsule["active_task_index"]["rows"].pop(0)
                projection["excluded_index_task_ids"].append(str(removed[0]))
                projection["included_index_task_count"] = len(
                    capsule["active_task_index"]["rows"]
                )
            else:
                raise RuntimeError(
                    "causal task index exceeds goal obligation capsule budget"
                )
        for _ in range(8):
            tokens = measure()
            if projection["capsule_tokens"] == tokens:
                break
            projection["capsule_tokens"] = tokens
        return capsule


    @staticmethod
    def _goal_obligation_task_semantic_projection(task) -> dict[str, Any]:
        return {
            "title": task.title,
            "description": task.description,
            "operation_kind": task.operation_kind,
            "subject_key": task.subject_key,
            "member_key": task.member_key,
            "phase_key": task.phase_key,
            "effect_targets": sorted(str(value) for value in task.effect_targets),
            "expected_outcomes": sorted(
                str(value) for value in task.expected_outcomes
            ),
            "dependency_outcomes": {
                str(key): sorted(str(value) for value in outcomes)
                for key, outcomes in sorted(task.dependency_outcomes.items())
            },
            "postcondition": task.postcondition,
            "advances_criteria": sorted(
                str(value) for value in task.advances_criteria
            ),
            "satisfies_criteria": sorted(
                str(value) for value in task.satisfies_criteria
            ),
        }

    @classmethod
    def _goal_obligation_task_semantic_signature(cls, task) -> str:
        projection = cls._goal_obligation_task_semantic_projection(task)
        return hashlib.sha256(
            json.dumps(
                projection,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def _unchanged_deterministic_proof_failures(
        self,
        state: RunState,
        workspace_observation: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        """Project cache-safe proof failures without treating them as answers."""

        if not bool(workspace_observation.get("cacheable", False)):
            return []
        workspace_digest = str(workspace_observation.get("digest") or "")
        if not workspace_digest:
            return []
        rows: list[dict[str, Any]] = []
        seen_semantics: set[str] = set()
        tasks = sorted(
            state.tasks.values(),
            key=lambda item: (item.insertion_order, item.task_id),
            reverse=True,
        )
        for task in tasks:
            if not task.active or task.status != TaskStatus.COMPLETED:
                continue
            semantic_signature = self._goal_obligation_task_semantic_signature(task)
            if semantic_signature in seen_semantics:
                continue
            matched: dict[str, Any] | None = None
            for attempt_id in reversed(task.attempt_ids):
                attempt = state.attempts.get(attempt_id)
                if attempt is None:
                    continue
                for result in reversed(attempt.validation_results):
                    evidence = (
                        result.evidence
                        if isinstance(result.evidence, Mapping)
                        else {}
                    )
                    if (
                        result.kind
                        not in {"model_cross_check", "criterion_cross_check"}
                        or result.passed
                        or evidence.get("observation_cacheable") is not True
                        or evidence.get("protocol_valid") is not True
                        or evidence.get("proof_passed") is not False
                        or str(evidence.get("workspace_digest") or "")
                        != workspace_digest
                        or self._MODEL_WRITTEN_TARGET_PROOF_FAILURE
                        not in str(result.message or "")
                    ):
                        continue
                    failure_payload = {
                        "validation_kind": result.kind,
                        "criterion_ids": sorted(
                            str(value)
                            for value in (
                                evidence.get("criterion_ids")
                                or task.satisfies_criteria
                            )
                        ),
                        "workspace_digest": workspace_digest,
                        "proof_reason": str(result.message or ""),
                        "witness_catalog_digest": str(
                            evidence.get("witness_catalog_digest") or ""
                        ),
                        "witness_bindings": evidence.get("witness_bindings") or [],
                        "witness_source_selections": evidence.get(
                            "witness_source_selections"
                        )
                        or [],
                    }
                    matched = {
                        "task_id": task.task_id,
                        "semantic_signature": semantic_signature,
                        "failure_fingerprint": hashlib.sha256(
                            json.dumps(
                                failure_payload,
                                ensure_ascii=False,
                                sort_keys=True,
                                separators=(",", ":"),
                            ).encode("utf-8")
                        ).hexdigest(),
                        "validation_kind": result.kind,
                        "criterion_ids": failure_payload["criterion_ids"],
                        "workspace_digest": workspace_digest,
                        "title": task.title[:160],
                        "description": task.description[:300],
                        "failure_class": "model_written_same_target_lineage",
                    }
                    break
                if matched is not None:
                    break
            if matched is not None:
                rows.append(matched)
                seen_semantics.add(semantic_signature)
        rows.sort(key=lambda item: (item["task_id"], item["semantic_signature"]))
        return rows

    def _unchanged_obligation_proposal_conflicts(
        self,
        state: RunState,
        proposal: GoalObligationProposal,
        capsule: Mapping[str, Any],
    ) -> list[dict[str, Any]]:
        observation = capsule.get("workspace_observation")
        observation = observation if isinstance(observation, Mapping) else {}
        failures = self._unchanged_deterministic_proof_failures(
            state,
            observation,
        )
        failures_by_semantic = {
            str(item.get("semantic_signature") or ""): item
            for item in failures
            if str(item.get("semantic_signature") or "")
        }
        conflicts: list[dict[str, Any]] = []
        for task in proposal.tasks:
            semantic_signature = self._goal_obligation_task_semantic_signature(task)
            previous = failures_by_semantic.get(semantic_signature)
            if previous is None:
                continue
            conflicts.append(
                {
                    "proposal_local_id": task.task_id,
                    "semantic_signature": semantic_signature,
                    "prior_task_id": previous["task_id"],
                    "failure_fingerprint": previous["failure_fingerprint"],
                    "failure_class": previous["failure_class"],
                }
            )
        return conflicts

    def _advance_goal_obligations(
        self,
        state: RunState,
        graph: TaskGraph,
        *,
        invalidated_claim_ids: list[str],
    ) -> bool:
        missing = self._missing_goal_criteria(state)
        if not missing:
            return False
        method = (
            getattr(self.model, "plan_goal_obligations", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            state.status = RunStatus.BLOCKED
            event = {
                "reason": (
                    "stale_or_invalid_goal_proof"
                    if invalidated_claim_ids
                    else "required_goal_evidence_missing"
                ),
                "criterion_ids": missing,
            }
            if invalidated_claim_ids:
                event["claim_ids"] = invalidated_claim_ids
            self._persist(
                state,
                "run_blocked",
                event,
            )
            return False
        obligation = state.goal_obligation
        if obligation is None:
            raise RuntimeError("goal obligation state was not initialized")
        if obligation.remaining_budget <= 0:
            obligation.status = GoalObligationStatus.EXHAUSTED
            obligation.updated_at = utc_now()
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "goal_obligation_replan_blocked",
                {
                    "reason": "unresolved_goal_obligations",
                    "criterion_ids": missing,
                    "remaining_budget": 0,
                },
            )
            self._persist(
                state,
                "run_blocked",
                {
                    "reason": "unresolved_goal_obligations",
                    "criterion_ids": missing,
                },
            )
            return False
        capsule = self._goal_obligation_capsule(
            state,
            invalidated_claim_ids=invalidated_claim_ids,
        )
        capsule_payload = json.dumps(
            capsule,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        observation_digest = hashlib.sha256(capsule_payload).hexdigest()
        self._persist(
            state,
            "goal_obligation_capsule_prepared",
            {
                "observation_digest": observation_digest,
                "capsule": capsule,
                "remaining_budget": obligation.remaining_budget,
            },
        )
        state.status = RunStatus.REPLANNING
        obligation.generation_count += 1
        obligation.last_observation_digest = observation_digest
        obligation.updated_at = utc_now()
        obligation.decision_history.append(
            {
                "type": "started",
                "generation": obligation.generation_count,
                "observation_digest": observation_digest,
                "criterion_ids": missing,
                "at": obligation.updated_at,
            }
        )
        self._persist(
            state,
            "goal_obligation_replan_started",
            {
                "generation": obligation.generation_count,
                "observation_digest": observation_digest,
                "criterion_ids": missing,
                "remaining_budget": obligation.remaining_budget,
                "active_required_tasks_complete": graph.required_complete(),
            },
        )
        try:
            proposal = method(state, capsule, self._persist_callback())
        except ModelProtocolError as exc:
            obligation.remaining_budget = max(0, obligation.remaining_budget - 1)
            obligation.status = GoalObligationStatus.BLOCKED
            obligation.updated_at = utc_now()
            obligation.decision_history.append(
                {
                    "type": "protocol_error",
                    "generation": obligation.generation_count,
                    "observation_digest": observation_digest,
                    "error": str(exc)[:2000],
                    "at": obligation.updated_at,
                }
            )
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "model_protocol_blocked",
                {
                    "phase": "goal_obligation_replan",
                    "error": str(exc)[:2000],
                    "criterion_ids": missing,
                    "remaining_budget": obligation.remaining_budget,
                },
            )
            return False
        if not isinstance(proposal, GoalObligationProposal):
            raise TypeError("model returned an unsupported goal obligation proposal")
        if self._immediately_ready_obligation_count(state, proposal.tasks) > 8:
            obligation.remaining_budget = max(0, obligation.remaining_budget - 1)
            obligation.status = GoalObligationStatus.BLOCKED
            obligation.updated_at = utc_now()
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "model_protocol_blocked",
                {
                    "phase": "goal_obligation_replan",
                    "error": "causal frontier exceeds 8 immediately-ready entry tasks",
                    "criterion_ids": missing,
                    "remaining_budget": obligation.remaining_budget,
                    "controller_trust_boundary": True,
                },
            )
            return False
        conflicts = self._unchanged_obligation_proposal_conflicts(
            state,
            proposal,
            capsule,
        )
        if conflicts:
            obligation.remaining_budget = max(0, obligation.remaining_budget - 1)
            obligation.status = GoalObligationStatus.UNRESOLVED
            obligation.updated_at = utc_now()
            proposal_projection = [
                {
                    "local_id": task.task_id,
                    **self._goal_obligation_task_semantic_projection(task),
                    "semantic_signature": self._goal_obligation_task_semantic_signature(
                        task
                    ),
                }
                for task in proposal.tasks
            ]
            history = {
                "type": "unchanged_deterministic_proof_proposal_suppressed",
                "generation": obligation.generation_count,
                "observation_digest": observation_digest,
                "workspace_digest": str(
                    (capsule.get("workspace_observation") or {}).get("digest")
                    or ""
                ),
                "conflicts": conflicts,
                "proposal_tasks": proposal_projection,
                "controller_partial_selection": False,
                "remaining_budget": obligation.remaining_budget,
                "at": obligation.updated_at,
            }
            obligation.decision_history.append(history)
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "unchanged_deterministic_proof_obligation_suppressed",
                {
                    key: value
                    for key, value in history.items()
                    if key not in {"type", "at"}
                },
            )
            return True
        materialized, local_to_global, next_sequence = (
            TaskGraph.materialize_model_tasks(
                proposal.tasks,
                existing_ids=state.tasks,
                next_sequence=state.next_task_sequence,
            )
        )
        graph.add_tasks(materialized)
        obligation.remaining_budget = max(0, obligation.remaining_budget - 1)
        obligation.task_ids.extend(task.task_id for task in materialized)
        obligation.status = GoalObligationStatus.UNRESOLVED
        obligation.updated_at = utc_now()
        obligation.decision_history.append(
            {
                "type": "tasks_appended",
                "generation": obligation.generation_count,
                "observation_digest": observation_digest,
                "reason": proposal.reason,
                "rwkv_reason_provided": proposal.reason_provided,
                "rwkv_schema_version_provided": proposal.schema_version_provided,
                "task_ids": [task.task_id for task in materialized],
                "at": obligation.updated_at,
            }
        )
        state.next_task_sequence = next_sequence
        state.plan_generation += 1
        state.active_task_id = None
        state.status = RunStatus.RUNNING
        self._persist(
            state,
            "goal_obligation_replan_saved",
            {
                "generation": obligation.generation_count,
                "observation_digest": observation_digest,
                "reason": proposal.reason,
                "rwkv_reason_provided": proposal.reason_provided,
                "rwkv_schema_version_provided": proposal.schema_version_provided,
                "new_task_ids": [task.task_id for task in materialized],
                "local_to_global": local_to_global,
                "proposal_tasks": [
                    {
                        "local_id": task.task_id,
                        "title": task.title,
                        "description": task.description,
                        "dependencies": list(task.dependencies),
                        "advances_criteria": list(task.advances_criteria),
                        "satisfies_criteria": list(task.satisfies_criteria),
                    }
                    for task in proposal.tasks
                ],
                "remaining_budget": obligation.remaining_budget,
                "plan_generation": state.plan_generation,
            },
        )
        return True

    @staticmethod
    def _immediately_ready_obligation_count(
        state: RunState,
        tasks: list,
    ) -> int:
        completed = {
            task.task_id
            for task in state.tasks.values()
            if task.active and task.status == TaskStatus.COMPLETED
        }
        local_ids = {task.task_id for task in tasks}
        return sum(
            all(
                dependency in completed and dependency not in local_ids
                for dependency in task.dependencies
            )
            for task in tasks
        )

    def _execute_ready_frontier(
        self,
        state: RunState,
        graph: TaskGraph,
        ready: list,
    ) -> int:
        """Execute one dependency-independent frontier with a serial state merge.

        RWKV action decisions may run concurrently against isolated RunState
        snapshots. Only actions whose authoritative Harness metadata says
        read_only=true and side_effect=false are dispatched concurrently.
        Every durable state mutation remains on this controller thread.
        """

        candidates = list(ready[: self.max_parallel_tasks])
        self._materialize_frontier_actions(state, graph, candidates)
        if state.status == RunStatus.BLOCKED:
            return 0

        parallel: list = []
        for task in candidates:
            definition = self.harness.definition(task.action.action_type)
            if not definition.read_only or definition.side_effect:
                break
            parallel.append(task)
        if len(parallel) < 2:
            self._execute_task(state, graph, candidates[0].task_id)
            return 1

        dispatched_at = {task.task_id: utc_now() for task in parallel}
        self._persist(
            state,
            "parallel_frontier_dispatched",
            {
                "task_ids": [task.task_id for task in parallel],
                "actions": [
                    {
                        "task_id": task.task_id,
                        "name": task.action.action_type,
                        "arguments": dict(task.action.arguments),
                    }
                    for task in parallel
                ],
                "max_workers": len(parallel),
                "state_mutation_in_workers": False,
                "read_only_only": True,
            },
        )
        with ThreadPoolExecutor(
            max_workers=len(parallel),
            thread_name_prefix="rwkv-lh-read",
        ) as executor:
            futures = [
                executor.submit(
                    self.harness.execute,
                    TaskAction(
                        task.action.action_type,
                        dict(task.action.arguments),
                    ),
                    state.goal,
                )
                for task in parallel
            ]
            results = [future.result() for future in futures]

        blocked = False
        for task, result in zip(parallel, results, strict=True):
            self._execute_task(
                state,
                graph,
                task.task_id,
                observed_result=result,
                observed_started_at=dispatched_at[task.task_id],
            )
            blocked = blocked or state.status == RunStatus.BLOCKED
        if blocked:
            state.status = RunStatus.BLOCKED
        self._persist(
            state,
            "parallel_frontier_merged",
            {
                "task_ids": [task.task_id for task in parallel],
                "outcomes": [result.outcome_type for result in results],
                "merge_order": [task.task_id for task in parallel],
                "state_mutation_in_workers": False,
            },
        )
        return len(parallel)

    def _materialize_frontier_actions(
        self,
        state: RunState,
        graph: TaskGraph,
        tasks: list,
    ) -> None:
        unresolved = [
            task
            for task in tasks
            if not task.action.action_type
            or task.action.action_type == "model_action"
        ]
        if not unresolved:
            return
        if (
            len(unresolved) == 1
            or not isinstance(self.model, LongHorizonModel)
            or self.max_parallel_tasks == 1
        ):
            for task in unresolved:
                if not self._materialize_task_action(state, graph, task.task_id):
                    return
            return

        if self.model is None:
            raise RuntimeError("ready frontier requires a model-proposed action")
        contexts: dict[str, Any] = {}
        for task in unresolved:
            context = self.memory.build_action_commit(state, task)
            contexts[task.task_id] = context
            self._persist(
                state,
                "execution_capsule_prepared",
                {
                    "task_id": task.task_id,
                    "request_scope": "action_commit",
                    "capsule": context.to_dict(),
                    "frontier_mode": "isolated_parallel_proposal",
                },
            )
        snapshot = state.to_dict()

        def propose(task_id: str):
            local_state = RunState.from_dict(snapshot)
            local_task = local_state.tasks[task_id]
            start = len(local_state.temp_decisions)
            events: list[tuple[str, dict[str, Any]]] = []

            def collect(_state, event_type, event):
                events.append((str(event_type), dict(event)))

            try:
                proposal = self.model.propose_action(
                    local_state,
                    local_task,
                    contexts[task_id],
                    self.harness.action_contract(),
                    collect,
                )
                error: Exception | None = None
            except Exception as exc:
                proposal = None
                error = exc
            return (
                proposal,
                error,
                local_state.temp_decisions[start:],
                events,
            )

        with ThreadPoolExecutor(
            max_workers=len(unresolved),
            thread_name_prefix="rwkv-lh-model",
        ) as executor:
            futures = [
                executor.submit(propose, task.task_id) for task in unresolved
            ]
            proposals = [future.result() for future in futures]

        for task, (proposal, error, decisions, events) in zip(
            unresolved,
            proposals,
            strict=True,
        ):
            state.temp_decisions.extend(decisions)
            for event_type, event in events:
                self._persist(state, event_type, event)
            if error is not None:
                if isinstance(error, ModelProtocolError):
                    self._block_action_materialization(
                        state,
                        graph,
                        task.task_id,
                        error,
                    )
                    return
                raise error
            self._apply_action_proposal(state, task.task_id, proposal)

    def _materialize_task_action(
        self,
        state: RunState,
        graph: TaskGraph,
        task_id: str,
    ) -> bool:
        task = state.tasks[task_id]
        if task.action.action_type and task.action.action_type != "model_action":
            return True
        if self.model is None:
            raise RuntimeError(f"task {task_id} requires a model-proposed action")
        context = self.memory.build_action_commit(state, task)
        self._persist(
            state,
            "execution_capsule_prepared",
            {
                "task_id": task_id,
                "request_scope": "action_commit",
                "capsule": context.to_dict(),
                "frontier_mode": "serial_proposal",
            },
        )
        try:
            proposal = self.model.propose_action(
                state,
                task,
                context,
                self.harness.action_contract(),
                self._persist_callback(),
            )
        except ModelProtocolError as exc:
            self._block_action_materialization(state, graph, task_id, exc)
            return False
        self._apply_action_proposal(state, task_id, proposal)
        return True

    def _apply_action_proposal(
        self,
        state: RunState,
        task_id: str,
        proposal: Any,
    ) -> None:
        task = state.tasks[task_id]
        if isinstance(proposal, ActionProposal):
            task.action = proposal.action
            task.completion_criteria = list(proposal.completion_criteria)
        elif isinstance(proposal, TaskAction):
            # Compatibility for deterministic architecture fixtures.
            task.action = proposal
        else:
            raise TypeError("model returned an unsupported action proposal")
        if not task.completion_criteria:
            raise ValueError(f"task {task_id} action proposal has no completion criteria")
        task.operation_kind = task.action.action_type
        target = str(
            task.action.arguments.get("path")
            or task.action.arguments.get("destination")
            or task.action.arguments.get("source")
            or ""
        ).strip()
        task.subject_key = target
        task.member_key = target
        task.phase_key = task.action.action_type
        task.effect_targets = [target] if target else []
        self._persist(
            state,
            "action_selected",
            {
                "task_id": task_id,
                "action": task.action.action_type,
                "arguments": task.action.arguments,
                "completion_criteria": [
                    {
                        "kind": criterion.kind,
                        "parameters": criterion.parameters,
                        "required": criterion.required,
                    }
                    for criterion in task.completion_criteria
                ],
                "source": "rwkv",
            },
        )

    def _block_action_materialization(
        self,
        state: RunState,
        graph: TaskGraph,
        task_id: str,
        error: ModelProtocolError,
    ) -> None:
        task = state.tasks[task_id]
        graph.transition(task_id, TaskStatus.BLOCKED)
        task.error = {
            "type": "ModelProtocolError",
            "phase": "action_materialization",
            "message": str(error)[:2000],
        }
        state.status = RunStatus.BLOCKED
        state.active_task_id = None
        self._persist(
            state,
            "model_protocol_blocked",
            {"task_id": task_id, **task.error},
        )

    def _execute_task(
        self,
        state: RunState,
        graph: TaskGraph,
        task_id: str,
        *,
        observed_result: ActionResult | None = None,
        observed_started_at: str | None = None,
    ) -> None:
        task = state.tasks[task_id]
        if not task.action.action_type or task.action.action_type == "model_action":
            if not self._materialize_task_action(state, graph, task_id):
                return
        definition = self.harness.definition(task.action.action_type)
        missing_postconditions = self.harness.missing_required_postconditions(
            task.action.action_type,
            [criterion.kind for criterion in task.completion_criteria],
        )
        if missing_postconditions:
            graph.transition(task_id, TaskStatus.BLOCKED)
            task.error = {
                "type": "MissingRequiredPostcondition",
                "missing": missing_postconditions,
            }
            state.status = RunStatus.BLOCKED
            state.active_task_id = None
            self._persist(
                state,
                "run_blocked",
                {
                    "reason": "missing_required_postcondition",
                    "task_id": task_id,
                    "missing": missing_postconditions,
                },
            )
            return
        graph.transition(task_id, TaskStatus.RUNNING)
        task.effect_observation_status = TaskEffectStatus.PENDING
        task.postcondition_commit_status = TaskCommitStatus.PENDING
        task.postcondition_observation_digest = ""
        state.status = RunStatus.RUNNING
        state.active_task_id = task_id
        attempt_number = len(task.attempt_ids) + 1
        attempt_id = f"{task_id}-A{attempt_number}"
        attempt = Attempt(
            attempt_id=attempt_id,
            task_id=task_id,
            status=AttemptStatus.RUNNING,
            action_fingerprint=action_fingerprint(task.action),
            idempotency_key=f"{state.run_id}:{task_id}:{action_fingerprint(task.action)}",
            started_at=observed_started_at or utc_now(),
        )
        task.attempt_ids.append(attempt_id)
        state.attempts[attempt_id] = attempt
        self._persist(
            state,
            "attempt_started",
            {
                "task_id": task_id,
                "attempt_id": attempt_id,
                "action": task.action.action_type,
                "arguments": task.action.arguments,
                "idempotent": definition.idempotent,
                "side_effect": definition.side_effect,
                "execution_mode": (
                    "parallel_read_only"
                    if observed_result is not None
                    else "serial"
                ),
            },
        )
        result = observed_result or self.harness.execute(task.action, state.goal)
        attempt.outcome_type = result.outcome_type
        task.outcome_type = result.outcome_type
        snapshot_audits = self._record_artifacts_and_memory(
            state,
            task_id,
            attempt_id,
            result,
        )
        attempt.tool_result = result.to_dict()
        self._persist(
            state,
            "action_returned",
            {
                "task_id": task_id,
                "attempt_id": attempt_id,
                "success": result.success,
                "exit_code": result.exit_code,
                "output": result.output,
                "metadata": result.metadata,
                "error": result.error,
                "outcome_type": result.outcome_type,
            },
        )
        for audit in snapshot_audits:
            self._persist(
                state,
                (
                    "post_action_workspace_snapshot_recorded"
                    if audit.get("memory_id")
                    else "post_action_workspace_snapshot_omitted"
                ),
                audit,
            )
        state.status = RunStatus.VALIDATING
        validation_results, effect_passed, task_committed = self._validate_task_result(
            state,
            task,
            result,
        )
        attempt.validation_results = validation_results
        self._apply_task_commit_state(
            task,
            validation_results,
            effect_passed=effect_passed,
            task_committed=task_committed,
        )
        self._apply_revision_commit_state(
            state,
            attempt_id,
            task.postcondition_commit_status,
        )
        self._persist(
            state,
            "task_commit_state_recorded",
            {
                "task_id": task_id,
                "attempt_id": attempt_id,
                "effect_observation_status": task.effect_observation_status.value,
                "postcondition_commit_status": task.postcondition_commit_status.value,
                "postcondition_observation_digest": task.postcondition_observation_digest,
                "decision_source": (
                    "rwkv"
                    if any(
                        item.kind == "task_postcondition_cross_check"
                        for item in validation_results
                    )
                    else "deterministic_fixture"
                ),
            },
        )
        if task_committed:
            attempt.status = AttemptStatus.SUCCEEDED
            attempt.ended_at = utc_now()
            graph.transition(task_id, TaskStatus.COMPLETED)
            self._sync_goal_obligation_state(state)
            task.error = None
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "task_completed",
                {
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "validation": [vars(item) for item in validation_results],
                },
            )
            return
        attempt.status = AttemptStatus.FAILED
        attempt.ended_at = utc_now()
        attempt.error = result.error or {"type": "ValidationFailed", "message": "required postcondition failed"}
        graph.transition(task_id, TaskStatus.FAILED)
        task.error = {
            "type": "ValidationFailed",
            "attempt_id": attempt_id,
            "results": [vars(item) for item in validation_results],
        }
        self._record_recovery_failure(state, task, validation_results)
        state.errors.append({"task_id": task_id, **task.error, "at": utc_now()})
        self._persist(
            state,
            "task_failed",
            {"task_id": task_id, "attempt_id": attempt_id, "validation": [vars(item) for item in validation_results]},
        )
        self._retry_or_replan(state, graph, task_id)

    def _retry_or_replan(
        self,
        state: RunState,
        graph: TaskGraph,
        task_id: str,
        *,
        recovery: bool = False,
    ) -> None:
        task = state.tasks[task_id]
        attempt_count = len(task.attempt_ids)
        lineage = (
            state.recovery_states.get(task.recovery_lineage_id)
            if task.recovery_lineage_id
            else None
        )
        if lineage is not None and lineage.remaining_budget <= 0:
            graph.transition(task_id, TaskStatus.BLOCKED)
            self._block_unreachable_tasks(state, graph)
            state.active_task_id = None
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "run_blocked",
                {
                    "reason": "recovery_lineage_budget_exhausted",
                    "task_id": task_id,
                    "lineage_id": lineage.lineage_id,
                },
            )
            return
        analyzer = (
            getattr(self.model, "analyze_failure", None)
            if self.model is not None
            else None
        )
        if callable(analyzer):
            same_failure_count = self._same_failure_count(state, task)
            context = self.memory.build_recovery(state, task)
            state.status = RunStatus.REPLANNING
            self._persist(
                state,
                "failure_analysis_started",
                {
                    "task_id": task_id,
                    "attempt_count": attempt_count,
                    "same_failure_count": same_failure_count,
                    "recovery": recovery,
                },
            )
            analysis = analyzer(
                state,
                task,
                context,
                self._persist_callback(),
                same_failure_count=same_failure_count,
            )
            decision = str(analysis.decision or "").strip().casefold()
            if decision not in {"retry_same", "reselect_action", "replan"}:
                raise ValueError(f"unsupported failure-analysis decision: {decision}")
            if same_failure_count >= 2 and decision in {
                "retry_same",
                "reselect_action",
            }:
                decision = "replan"
                self._persist(
                    state,
                    "near_duplicate_recovery_guard",
                    {
                        "task_id": task_id,
                        "lineage_id": task.recovery_lineage_id,
                        "same_failure_count": same_failure_count,
                    },
                )
            self._record_recovery_decision(state, task, decision, analysis.reason)
            self._persist(
                state,
                "failure_analysis_returned",
                {
                    "task_id": task_id,
                    "decision": decision,
                    "reason": analysis.reason,
                    "recovery": recovery,
                },
            )
            definition = self.harness.definition(task.action.action_type)
            if decision == "retry_same" and not (
                definition.idempotent or definition.read_only
            ):
                decision = "reselect_action"
                self._persist(
                    state,
                    "failure_decision_safety_adjusted",
                    {
                        "task_id": task_id,
                        "from": "retry_same",
                        "to": "reselect_action",
                        "reason": "non_idempotent_action_cannot_be_blindly_retried",
                    },
                )
            if decision in {"retry_same", "reselect_action"} and (
                attempt_count >= task.retry_policy.max_attempts
                or (lineage is not None and lineage.remaining_budget <= 0)
            ):
                decision = "replan"
                self._persist(
                    state,
                    "failure_decision_budget_adjusted",
                    {
                        "task_id": task_id,
                        "to": "replan",
                        "reason": "task_attempt_budget_exhausted",
                    },
                )
            if decision == "retry_same":
                graph.transition(task_id, TaskStatus.PENDING)
                state.active_task_id = None
                state.status = RunStatus.RUNNING
                self._persist(
                    state,
                    "retry_scheduled",
                    {
                        "task_id": task_id,
                        "next_attempt": attempt_count + 1,
                        "source": "rwkv_failure_analysis",
                    },
                )
                return
            if decision == "reselect_action":
                task.action = TaskAction("model_action", {})
                task.completion_criteria = []
                graph.transition(task_id, TaskStatus.PENDING)
                state.active_task_id = None
                state.status = RunStatus.RUNNING
                self._persist(
                    state,
                    "action_reselection_scheduled",
                    {
                        "task_id": task_id,
                        "next_attempt": attempt_count + 1,
                        "source": "rwkv_failure_analysis",
                    },
                )
                return
            self._start_replan(
                state,
                graph,
                task,
                same_failure_count=same_failure_count,
                recovery=recovery,
            )
            return
        if (
            self.model is not None
            and attempt_count >= task.retry_policy.replan_after
        ):
            self._start_replan(
                state,
                graph,
                task,
                same_failure_count=self._same_failure_count(state, task),
                recovery=recovery,
            )
            return
        if attempt_count < task.retry_policy.max_attempts:
            graph.transition(task_id, TaskStatus.PENDING)
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "retry_scheduled",
                {"task_id": task_id, "next_attempt": attempt_count + 1},
            )
            return
        graph.transition(task_id, TaskStatus.BLOCKED)
        self._block_unreachable_tasks(state, graph)
        state.active_task_id = None
        state.status = RunStatus.BLOCKED
        self._persist(
            state,
            "run_blocked",
            {"reason": "task_retry_exhausted", "task_id": task_id, "attempts": attempt_count},
        )

    def _start_replan(
        self,
        state: RunState,
        graph: TaskGraph,
        task,
        *,
        same_failure_count: int,
        recovery: bool,
    ) -> None:
        if self.model is None:
            raise RuntimeError("replan requires a model")
        context = self.memory.build_recovery(state, task)
        state.status = RunStatus.REPLANNING
        event_type = "replan_recovery_started" if recovery else "replan_started"
        self._persist(
            state,
            event_type,
            {
                "task_id": task.task_id,
                "attempt_count": len(task.attempt_ids),
                "same_failure_count": same_failure_count,
            },
        )
        try:
            proposal = self.model.replan(
                state,
                task,
                context,
                self._persist_callback(),
                same_failure_count=same_failure_count,
            )
        except ModelProtocolError as exc:
            graph.transition(task.task_id, TaskStatus.BLOCKED)
            task.error = {
                "type": "ModelProtocolError",
                "phase": "replan_intent",
                "message": str(exc)[:2000],
            }
            state.active_task_id = None
            state.status = RunStatus.BLOCKED
            self._persist(
                state,
                "model_protocol_blocked",
                {"task_id": task.task_id, **task.error},
            )
            return
        self._apply_replan(state, graph, task.task_id, proposal)

    @staticmethod
    def _same_failure_count(state: RunState, task) -> int:
        if task.recovery_lineage_id:
            lineage = state.recovery_states.get(task.recovery_lineage_id)
            if lineage is not None:
                return lineage.same_failure_count
        fingerprints = [
            state.attempts[attempt_id].action_fingerprint
            for attempt_id in task.attempt_ids
            if attempt_id in state.attempts
            and state.attempts[attempt_id].status == AttemptStatus.FAILED
        ]
        if not fingerprints:
            return 0
        latest = fingerprints[-1]
        trailing = 0
        for fingerprint in reversed(fingerprints):
            if fingerprint != latest:
                break
            trailing += 1
        return max(0, trailing - 1)

    def _apply_replan(
        self,
        state: RunState,
        graph: TaskGraph,
        failed_task_id: str,
        proposal: ReplanProposal,
    ) -> None:
        if not proposal.tasks:
            raise TaskGraphError("replan produced no replacement tasks")
        original_tasks = {
            task_id: type(task).from_dict(task.to_dict())
            for task_id, task in state.tasks.items()
        }
        failed_task = state.tasks[failed_task_id]
        replacement_local_id = proposal.supersede.get(failed_task_id)
        if not replacement_local_id:
            replacement_local_id = proposal.tasks[0].task_id
        materialized, local_to_global, next_sequence = TaskGraph.materialize_model_tasks(
            proposal.tasks,
            existing_ids=state.tasks,
            next_sequence=state.next_task_sequence,
        )
        replacement_id = local_to_global.get(replacement_local_id)
        if not replacement_id:
            raise TaskGraphError("replan replacement local id is missing")
        replacement_task = next(
            task for task in materialized if task.task_id == replacement_id
        )
        if not replacement_task.satisfies_criteria:
            replacement_task.satisfies_criteria = list(failed_task.satisfies_criteria)
        if not replacement_task.advances_criteria:
            replacement_task.advances_criteria = list(
                failed_task.advances_criteria
            )
        lineage = (
            state.recovery_states.get(failed_task.recovery_lineage_id)
            if failed_task.recovery_lineage_id
            else None
        )
        for task in materialized:
            task.recovery_lineage_id = failed_task.recovery_lineage_id
            task.subject_task_id = (
                lineage.subject_task_id if lineage is not None else failed_task.subject_task_id
            )
        try:
            graph.add_tasks(materialized)
            graph.supersede(failed_task_id, replacement_id)
            graph.validate()
        except Exception:
            state.tasks.clear()
            state.tasks.update(original_tasks)
            raise
        if lineage is not None:
            lineage.task_ids.extend(
                task.task_id for task in materialized if task.task_id not in lineage.task_ids
            )
            lineage.failed_task_id = failed_task_id
            lineage.updated_at = utc_now()
            self._invalidate_criterion_evidence(
                state,
                lineage.subject_task_id,
                invalidated_by=lineage.lineage_id,
            )
        state.next_task_sequence = next_sequence
        state.plan_generation += 1
        state.active_task_id = None
        state.status = RunStatus.RUNNING
        self._persist(
            state,
            "replan_saved",
            {
                "reason": proposal.reason,
                "new_task_ids": [task.task_id for task in materialized],
                "local_to_global": local_to_global,
                "supersede": {failed_task_id: replacement_id},
                "lineage_id": failed_task.recovery_lineage_id,
                "plan_generation": state.plan_generation,
            },
        )

    def _recover_interrupted_attempt(self, state: RunState) -> None:
        running_attempts = [
            attempt for attempt in state.attempts.values() if attempt.status == AttemptStatus.RUNNING
        ]
        if not running_attempts:
            return
        if len(running_attempts) > 1:
            state.status = RunStatus.BLOCKED
            self._persist(state, "run_blocked", {"reason": "multiple_running_attempts"})
            return
        attempt = running_attempts[0]
        task = state.tasks.get(attempt.task_id)
        if task is None or task.status != TaskStatus.RUNNING:
            state.status = RunStatus.BLOCKED
            self._persist(state, "run_blocked", {"reason": "orphan_running_attempt", "attempt_id": attempt.attempt_id})
            return
        result = ActionResult.from_dict(attempt.tool_result)
        attempt.outcome_type = result.outcome_type
        task.outcome_type = result.outcome_type
        validation_results, effect_passed, task_committed = self._validate_task_result(
            state,
            task,
            result,
        )
        self._apply_task_commit_state(
            task,
            validation_results,
            effect_passed=effect_passed,
            task_committed=task_committed,
        )
        self._apply_revision_commit_state(
            state,
            attempt.attempt_id,
            task.postcondition_commit_status,
        )
        graph = TaskGraph(state.tasks)
        if task_committed:
            attempt.status = AttemptStatus.SUCCEEDED
            attempt.ended_at = utc_now()
            attempt.validation_results = validation_results
            graph.transition(task.task_id, TaskStatus.COMPLETED)
            self._sync_goal_obligation_state(state)
            task.error = None
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "recovered_as_completed",
                {"task_id": task.task_id, "attempt_id": attempt.attempt_id},
            )
            return
        definition = self.harness.definition(task.action.action_type)
        attempt.status = AttemptStatus.INTERRUPTED
        attempt.ended_at = utc_now()
        attempt.validation_results = validation_results
        graph.transition(task.task_id, TaskStatus.FAILED)
        self._record_recovery_failure(state, task, validation_results)
        if definition.idempotent or definition.read_only:
            graph.transition(task.task_id, TaskStatus.PENDING)
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "interrupted_attempt_retryable",
                {"task_id": task.task_id, "attempt_id": attempt.attempt_id},
            )
            return
        graph.transition(task.task_id, TaskStatus.BLOCKED)
        task.error = {
            "type": "UnsafeInterruptedAction",
            "message": "non-idempotent action has no verified postcondition",
            "attempt_id": attempt.attempt_id,
        }
        state.active_task_id = None
        state.status = RunStatus.BLOCKED
        self._persist(
            state,
            "run_blocked",
            {"reason": "unsafe_interrupted_action", "task_id": task.task_id, "attempt_id": attempt.attempt_id},
        )

    def _recover_failed_tasks(self, state: RunState) -> None:
        if state.status != RunStatus.INTERRUPTED:
            return
        graph = TaskGraph(state.tasks)
        recovered: list[str] = []
        blocked: list[str] = []
        for task in state.tasks.values():
            if not task.active or task.status != TaskStatus.FAILED:
                continue
            analyzer = (
                getattr(self.model, "analyze_failure", None)
                if self.model is not None
                else None
            )
            if callable(analyzer):
                self._retry_or_replan(
                    state,
                    graph,
                    task.task_id,
                    recovery=True,
                )
                return
            if (
                self.model is not None
                and len(task.attempt_ids) >= task.retry_policy.replan_after
            ):
                self._start_replan(
                    state,
                    graph,
                    task,
                    same_failure_count=self._same_failure_count(state, task),
                    recovery=True,
                )
                return
            definition = self.harness.definition(task.action.action_type)
            if (
                len(task.attempt_ids) < task.retry_policy.max_attempts
                and (definition.idempotent or definition.read_only)
            ):
                graph.transition(task.task_id, TaskStatus.PENDING)
                recovered.append(task.task_id)
            else:
                graph.transition(task.task_id, TaskStatus.BLOCKED)
                blocked.append(task.task_id)
        if blocked:
            self._block_unreachable_tasks(state, graph)
            state.status = RunStatus.BLOCKED
            state.active_task_id = None
            self._persist(
                state,
                "run_blocked",
                {"reason": "failed_task_not_safely_resumable", "task_ids": blocked},
            )
        elif recovered:
            state.status = RunStatus.RUNNING
            state.active_task_id = None
            self._persist(
                state,
                "interrupted_failure_retryable",
                {"task_ids": recovered},
            )

    def _complete_run(self, state: RunState) -> str:
        graph = TaskGraph(state.tasks)
        if (
            not state.goal.verify_digest()
            or not graph.required_complete()
            or not self._goal_criteria_covered(state)
        ):
            raise TaskGraphError("run-level completion invariant failed")
        context = self._verified_context(state)
        output = (
            self.model.final_answer(state, context, self._persist_callback())
            if self.model is not None
            else self._deterministic_completion_summary(state)
        )
        if not str(output or "").strip():
            raise ValueError("final model output is empty")
        state.memory_index["M-FINAL"] = MemoryEntry(
            memory_id="M-FINAL",
            kind="final",
            task_id="FINAL",
            summary=output[:1000],
            content=output,
        )
        state.status = RunStatus.COMPLETED
        state.active_task_id = None
        if state.goal_obligation is not None:
            state.goal_obligation.unresolved_criterion_ids = []
            state.goal_obligation.status = GoalObligationStatus.RESOLVED
            state.goal_obligation.updated_at = utc_now()
        self._persist(
            state,
            "run_completed",
            {"task_count": len(state.tasks), "artifact_count": len(state.artifacts), "final_output": output},
        )
        return output

    def _record_artifacts_and_memory(
        self,
        state: RunState,
        task_id: str,
        attempt_id: str,
        result: ActionResult,
    ) -> list[dict[str, Any]]:
        artifact_refs: list[str] = []
        observed_artifacts: list[tuple[str, Any, int]] = []
        full_output = str(result.output or "")
        if len(full_output) > 20_000:
            output_artifact_id = f"{attempt_id}-OUTPUT"
            artifact_directory = getattr(self.store, "artifact_directory", None)
            if not callable(artifact_directory):
                raise RuntimeError("state store does not expose an artifact directory")
            output_directory = artifact_directory(state.run_id) / "tool-results"
            output_directory.mkdir(parents=True, exist_ok=True)
            output_path = output_directory / f"{attempt_id}.txt"
            self._atomic_text_write(output_path, full_output)
            digest = hashlib.sha256(full_output.encode("utf-8")).hexdigest()
            state.artifacts[output_artifact_id] = ArtifactRecord(
                artifact_id=output_artifact_id,
                task_id=task_id,
                path=self.store.artifact_locator(output_path),
                sha256=digest,
                media_type="text/plain",
                summary=f"Full tool output ({len(full_output)} characters)",
            )
            artifact_refs.append(output_artifact_id)
            result.output = full_output[:20_000]
            result.metadata["output_truncated"] = True
            result.metadata["output_artifact"] = output_artifact_id
        for index, observed in enumerate(result.artifacts, start=1):
            artifact_id = f"{attempt_id}-R{index}"
            state.artifacts[artifact_id] = ArtifactRecord(
                artifact_id=artifact_id,
                task_id=task_id,
                path=observed.path,
                sha256=observed.sha256,
                media_type=observed.media_type,
                summary=observed.summary,
            )
            artifact_refs.append(artifact_id)
            observed_artifacts.append((artifact_id, observed, index))
        revisions_by_target = {
            str(target).strip(): ("", "")
            for target in state.tasks[task_id].effect_targets
            if str(target).strip()
        }
        for artifact_id, observed, _ in observed_artifacts:
            revisions_by_target[str(observed.path)] = (
                artifact_id,
                str(observed.sha256),
            )
        for revision_index, (target, artifact_data) in enumerate(
            sorted(revisions_by_target.items()),
            start=1,
        ):
            artifact_id, digest = artifact_data
            state.artifact_revisions.setdefault(target, []).append(
                ArtifactRevision(
                    revision_id=f"{attempt_id}-REV{revision_index}",
                    target=target,
                    artifact_id=artifact_id,
                    task_id=task_id,
                    attempt_id=attempt_id,
                    sha256=digest,
                    outcome_type=result.outcome_type,
                )
            )
        state.attempts[attempt_id].artifact_refs = artifact_refs
        memory_id = f"M-{attempt_id}"
        output = str(result.output or "")
        observation_metadata = {
            key: value
            for key, value in result.metadata.items()
            if key
            in {
                "path",
                "recursive",
                "entry_count",
                "truncated",
                "next_cursor",
                "start_char",
                "end_char",
                "next_start_char",
                "complete",
                "original_chars",
                "json_type",
                "output_truncated",
                "output_artifact",
            }
        }
        metadata_text = json.dumps(
            observation_metadata,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        observation_content = output
        if observation_metadata:
            marker = f"\n\nACTION RESULT METADATA\n{metadata_text}"
            observation_content = output[: max(0, 20_000 - len(marker))] + marker
        state.memory_index[memory_id] = MemoryEntry(
            memory_id=memory_id,
            kind="action_result",
            task_id=task_id,
            summary=(output[:1000] or json.dumps(result.error or {}, ensure_ascii=False)[:1000]),
            content=observation_content[:20_000],
            artifact_refs=artifact_refs,
            evidence_refs=[
                str(item.get("locator") or item.get("url") or item.get("source") or "")
                for item in result.evidence
                if item.get("locator") or item.get("url") or item.get("source")
            ],
        )
        snapshot_memory_ids: list[str] = []
        snapshot_audits: list[dict[str, Any]] = []
        if (
            result.success
            and result.action_type in self._POST_ACTION_SNAPSHOT_ACTIONS
        ):
            for artifact_id, observed, index in observed_artifacts:
                snapshot_memory_id = f"M-{attempt_id}-POST-R{index}"
                snapshot, audit = self._post_action_workspace_snapshot(
                    state,
                    task_id=task_id,
                    attempt_id=attempt_id,
                    artifact_id=artifact_id,
                    snapshot_memory_id=snapshot_memory_id,
                    action_type=result.action_type,
                    observed=observed,
                )
                snapshot_audits.append(audit)
                if snapshot is None:
                    continue
                state.memory_index[snapshot_memory_id] = snapshot
                snapshot_memory_ids.append(snapshot_memory_id)
        state.tasks[task_id].output_refs = [
            memory_id,
            *snapshot_memory_ids,
            *artifact_refs,
        ]
        return snapshot_audits

    def _post_action_workspace_snapshot(
        self,
        state: RunState,
        *,
        task_id: str,
        attempt_id: str,
        artifact_id: str,
        snapshot_memory_id: str,
        action_type: str,
        observed: Any,
    ) -> tuple[MemoryEntry | None, dict[str, Any]]:
        observed_path = str(getattr(observed, "path", "") or "").strip()
        observed_hash = str(getattr(observed, "sha256", "") or "").strip().casefold()
        observed_media_type = str(
            getattr(observed, "media_type", "application/octet-stream")
            or "application/octet-stream"
        )
        audit: dict[str, Any] = {
            "schema_version": self._POST_ACTION_SNAPSHOT_SCHEMA,
            "task_id": task_id,
            "attempt_id": attempt_id,
            "memory_id": "",
            "artifact_id": artifact_id,
            "action_type": action_type,
            "path": observed_path,
            "sha256": observed_hash,
            "media_type": observed_media_type,
            "size_bytes": None,
            "content_included": False,
            "omission_reason": "",
            "source": "post_action_workspace_read",
            "reference_or_acceptance_used": False,
            "rwkv_output_modified": False,
        }

        def omitted(reason: str) -> tuple[None, dict[str, Any]]:
            audit["omission_reason"] = reason
            return None, audit

        if not observed_path:
            return omitted("artifact_path_missing")
        relative = Path(observed_path)
        if relative.is_absolute():
            return omitted("artifact_path_not_workspace_relative")
        if ".." in relative.parts:
            return omitted("artifact_path_parent_traversal")

        try:
            root = Path(state.goal.workspace_root).resolve(strict=True)
            lexical = root
            for part in relative.parts:
                if part in {"", "."}:
                    continue
                lexical = lexical / part
                if lexical.is_symlink():
                    return omitted("artifact_path_uses_symlink")
            resolved = self.harness.resolve_path(
                state.goal,
                observed_path,
                must_exist=True,
            )
            if not resolved.is_file():
                return omitted("artifact_path_not_regular_file")
            canonical_path = resolved.relative_to(root).as_posix()
            content_bytes = resolved.read_bytes()
        except FileNotFoundError:
            return omitted("artifact_path_missing")
        except OSError:
            return omitted("artifact_read_failed")
        except Exception as exc:
            # Snapshot collection is an optional observation lane. Any scope
            # resolver or extension failure must fail closed without changing
            # the already-executed RWKV action result.
            return omitted(f"artifact_scope_or_read_rejected:{type(exc).__name__}")

        actual_size = len(content_bytes)
        actual_hash = hashlib.sha256(content_bytes).hexdigest()
        audit["path"] = canonical_path
        audit["size_bytes"] = actual_size
        if actual_hash != observed_hash:
            audit["observed_sha256"] = observed_hash
            audit["actual_sha256"] = actual_hash
            return omitted("artifact_hash_mismatch")
        try:
            observed_size = int(getattr(observed, "size_bytes", actual_size))
        except (TypeError, ValueError):
            return omitted("artifact_size_invalid")
        if observed_size != actual_size:
            audit["observed_size_bytes"] = observed_size
            return omitted("artifact_size_mismatch")

        payload: dict[str, Any] = {
            "schema_version": self._POST_ACTION_SNAPSHOT_SCHEMA,
            "action_type": action_type,
            "path": canonical_path,
            "sha256": actual_hash,
            "media_type": observed_media_type,
            "size_bytes": actual_size,
            "content_included": False,
            "omission_reason": "",
        }
        if actual_size > self._POST_ACTION_SNAPSHOT_CONTENT_LIMIT_BYTES:
            payload["omission_reason"] = "content_exceeds_20000_bytes"
        else:
            try:
                payload["content"] = content_bytes.decode("utf-8")
                payload["content_included"] = True
            except UnicodeDecodeError:
                payload["omission_reason"] = "content_not_utf8"

        snapshot_content = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        content_included = bool(payload["content_included"])
        omission_reason = str(payload["omission_reason"])
        audit.update(
            {
                "memory_id": snapshot_memory_id,
                "sha256": actual_hash,
                "content_included": content_included,
                "omission_reason": omission_reason,
            }
        )
        memory = MemoryEntry(
            memory_id=snapshot_memory_id,
            kind="post_action_workspace_snapshot",
            task_id=task_id,
            summary=(
                f"Observed post-action workspace file {canonical_path}; "
                f"sha256={actual_hash}; size_bytes={actual_size}; "
                f"content_included={str(content_included).lower()}"
            ),
            content=snapshot_content,
            artifact_refs=[artifact_id],
        )
        return memory, audit

    @staticmethod
    def _atomic_text_write(path, content: str) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass

    @staticmethod
    def _skip_unselected_outcome_tasks(
        state: RunState,
        graph: TaskGraph,
    ) -> list[str]:
        skipped: list[str] = []
        for task in graph.outcome_mismatched_tasks():
            graph.transition(task.task_id, TaskStatus.SKIPPED)
            task.error = {
                "type": "DependencyOutcomeNotSelected",
                "dependencies": {
                    dependency: state.tasks[dependency].outcome_type
                    for dependency in task.dependencies
                    if dependency in task.dependency_outcomes
                },
            }
            skipped.append(task.task_id)
        return skipped

    @staticmethod
    def _block_unreachable_tasks(state: RunState, graph: TaskGraph) -> None:
        for task in graph.unresolved_required():
            if task.status != TaskStatus.PENDING:
                continue
            failed_dependencies = [
                dependency
                for dependency in task.dependencies
                if state.tasks[dependency].status in {TaskStatus.FAILED, TaskStatus.BLOCKED}
            ]
            if failed_dependencies:
                graph.transition(task.task_id, TaskStatus.BLOCKED)
                task.error = {"type": "DependencyBlocked", "dependencies": failed_dependencies}

    @staticmethod
    def _verified_context(state: RunState) -> str:
        return json.dumps(
            {
                "tasks": {
                    task_id: {
                        "title": task.title,
                        "status": task.status.value,
                        "output_refs": task.output_refs,
                        "advances_criteria": task.advances_criteria,
                        "satisfies_criteria": task.satisfies_criteria,
                        "subject_task_id": task.subject_task_id,
                        "recovery_lineage_id": task.recovery_lineage_id,
                    }
                    for task_id, task in state.tasks.items()
                    if task.active
                },
                "artifacts": {key: vars(value) for key, value in state.artifacts.items()},
                "criterion_evidence": {
                    key: value.to_dict()
                    for key, value in state.criterion_evidence.items()
                },
                "goal_obligation": (
                    state.goal_obligation.to_dict()
                    if state.goal_obligation is not None
                    else None
                ),
                "memory": {
                    key: {"summary": value.summary, "artifact_refs": value.artifact_refs, "evidence_refs": value.evidence_refs}
                    for key, value in state.memory_index.items()
                    if value.kind == "action_result"
                },
            },
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def _deterministic_completion_summary(state: RunState) -> str:
        return f"Verified {sum(1 for task in state.tasks.values() if task.status == TaskStatus.COMPLETED)} task(s) and {len(state.artifacts)} artifact(s)."

    @staticmethod
    def _final_output(state: RunState) -> str:
        final = state.memory_index.get("M-FINAL")
        return final.content if final is not None else ""

    def _persist_callback(self) -> PersistCallback:
        return self._persist

    def _validate_task_result(
        self,
        state: RunState,
        task,
        action_result: ActionResult,
    ) -> tuple[list[ValidationResult], bool, bool]:
        validation = self.validator.validate(
            task,
            action_result,
            state.goal,
            state,
            cross_check=self._model_cross_check(state),
        )
        results = list(validation.results)
        declared_outcome_observed = (
            action_result.outcome_type != "success"
            and action_result.outcome_type in task.expected_outcomes
            and action_result.outcome_type
            in {"not_found", "invalid", "conflict", "timeout", "nonzero"}
        )
        if declared_outcome_observed:
            results.append(
                ValidationResult(
                    kind="declared_outcome_observed",
                    passed=True,
                    required=True,
                    message=(
                        f"observed model-declared outcome {action_result.outcome_type}"
                    ),
                    evidence={
                        "outcome_type": action_result.outcome_type,
                        "expected_outcomes": list(task.expected_outcomes),
                        "tool_success": action_result.success,
                    },
                )
            )
        effect_passed = validation.required_passed or declared_outcome_observed
        task_committed = effect_passed
        existing_rwkv_semantic_commit = any(
            item.required
            and item.passed
            and item.kind in {
                "model_cross_check",
                "criterion_cross_check",
                "task_postcondition_cross_check",
            }
            for item in results
        )
        if effect_passed and not existing_rwkv_semantic_commit:
            commit_result = self._task_postcondition_check(
                state,
                task,
                action_result,
                results,
            )
            if commit_result is not None:
                results.append(commit_result)
                task_committed = commit_result.passed
        subject_task_id = self._validation_subject_task_id(state, task)
        failed_required = (
            []
            if declared_outcome_observed and task_committed
            else [item for item in results if item.required and not item.passed]
        )
        fingerprint = (
            self._failure_fingerprint(task, subject_task_id, failed_required)
            if failed_required
            else ""
        )
        for index, result in enumerate(results, start=1):
            result.subject_task_id = subject_task_id
            result.criterion_ids = list(task.satisfies_criteria)
            result.evidence_refs = list(dict.fromkeys(task.output_refs))
            if result.required and not result.passed:
                result.failure_fingerprint = fingerprint
            if not result.evidence_refs and task.attempt_ids:
                result.evidence_refs = [f"{task.attempt_ids[-1]}:V{index}"]
        return results, effect_passed, task_committed

    @staticmethod
    def _apply_task_commit_state(
        task,
        validation_results: list[ValidationResult],
        *,
        effect_passed: bool,
        task_committed: bool,
    ) -> None:
        task.effect_observation_status = (
            TaskEffectStatus.OBSERVED if effect_passed else TaskEffectStatus.FAILED
        )
        if task_committed:
            task.postcondition_commit_status = TaskCommitStatus.COMMITTED
        elif effect_passed:
            task.postcondition_commit_status = TaskCommitStatus.REJECTED
        else:
            task.postcondition_commit_status = TaskCommitStatus.PENDING
        task.postcondition_observation_digest = next(
            (
                str(item.evidence.get("observation_digest") or "")
                for item in validation_results
                if item.kind == "task_postcondition_cross_check"
                and isinstance(item.evidence, Mapping)
            ),
            "",
        )

    @staticmethod
    def _apply_revision_commit_state(
        state: RunState,
        attempt_id: str,
        commit_status: TaskCommitStatus,
    ) -> None:
        for revisions in state.artifact_revisions.values():
            for revision in revisions:
                if revision.attempt_id == attempt_id:
                    revision.task_commit_status = commit_status.value

    def _task_postcondition_check(
        self,
        state: RunState,
        task,
        action_result: ActionResult,
        validation_results: list[ValidationResult],
    ) -> ValidationResult | None:
        method = (
            getattr(self.model, "commit_task_postcondition", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            return None
        return self._cross_check_with_observation_gate(
            state,
            task,
            action_result,
            validation_results,
            kind="task_postcondition_cross_check",
            required=True,
            parameters={},
        )

    def _model_cross_check(self, state: RunState):
        method = (
            getattr(self.model, "cross_validate", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            return None

        def check(task, action_result, spec, validation_results):
            return self._cross_check_with_observation_gate(
                state,
                task,
                action_result,
                list(validation_results),
                kind="model_cross_check",
                required=spec.required,
                parameters=dict(spec.parameters),
            )

        return check

    def _commit_goal_criterion_evidence(self, state: RunState) -> bool:
        """Ask RWKV for Goal evidence only after the required graph closes."""

        criterion_ids = self._missing_goal_criteria(state)
        if not criterion_ids:
            return True
        method = (
            getattr(self.model, "commit_criterion_evidence", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            return False
        source_catalog = self._goal_criterion_provenance_catalog(
            state,
            criterion_ids,
        )
        completed_task_ids = [
            task.task_id for task in self._completed_active_tasks(state)
        ]
        collected_bindings: list[dict[str, Any]] = []
        try:
            for criterion_id in criterion_ids:
                local_catalog = dict(source_catalog)
                local_catalog["claimed_criterion_ids"] = [criterion_id]
                context = self.memory.build_goal_validation(
                    state,
                    criterion_ids=[criterion_id],
                    selected_memory_ids=[
                        str(item.get("ref") or "")
                        for item in source_catalog["causal_actual_sources"]
                    ],
                )
                self._persist(
                    state,
                    "goal_criterion_provenance_catalog_prepared",
                    {
                        "criterion_ids": [criterion_id],
                        "catalog": local_catalog,
                        "completed_active_task_ids": completed_task_ids,
                        "criterion_local": True,
                        "controller_semantic_fields_generated": False,
                    },
                )
                local_proposal = method(
                    state,
                    context,
                    self._persist_callback(),
                    criterion_ids=[criterion_id],
                    source_catalog=local_catalog,
                )
                if not isinstance(local_proposal, Mapping):
                    raise ModelProtocolError(
                        "criterion-local evidence proposal must be an object"
                    )
                decision = str(
                    local_proposal.get("decision") or ""
                ).strip().casefold()
                bindings = local_proposal.get("bindings")
                if decision == "replan" and bindings == []:
                    self._persist(
                        state,
                        "goal_criterion_local_batch_replan_requested",
                        {
                            "criterion_id": criterion_id,
                            "collected_pass_criterion_ids": [
                                str(item.get("criterion_id") or "")
                                for item in collected_bindings
                            ],
                            "partial_evidence_committed": False,
                            "controller_semantic_fields_generated": False,
                        },
                    )
                    self._persist(
                        state,
                        "goal_criterion_provenance_replan_requested",
                        {
                            "claim_ids": [],
                            "criterion_ids": [],
                            "producer_task_ids": [],
                            "protocol": "rwkv_goal_provenance_commit.v1",
                            "controller_semantic_fields_generated": False,
                        },
                    )
                    return False
                if decision != "pass" or not isinstance(bindings, list):
                    raise ModelProtocolError(
                        "criterion-local evidence must pass with one binding or replan empty"
                    )
                if len(bindings) != 1 or not isinstance(bindings[0], Mapping):
                    raise ModelProtocolError(
                        "criterion-local pass must return exactly one binding"
                    )
                binding = dict(bindings[0])
                if str(binding.get("criterion_id") or "") != criterion_id:
                    raise ModelProtocolError(
                        "criterion-local binding changed the fixed criterion id"
                    )
                collected_bindings.append(binding)
                self._persist(
                    state,
                    "goal_criterion_local_decision_collected",
                    {
                        "criterion_id": criterion_id,
                        "decision": "pass",
                        "actual_ref": str(binding.get("actual_ref") or ""),
                        "expected_ref": str(binding.get("expected_ref") or ""),
                        "partial_evidence_committed": False,
                        "controller_semantic_fields_generated": False,
                    },
                )
            self._persist(
                state,
                "goal_criterion_local_batch_ready",
                {
                    "criterion_ids": criterion_ids,
                    "binding_count": len(collected_bindings),
                    "partial_evidence_committed": False,
                    "controller_semantic_fields_generated": False,
                },
            )
            claims = self._validate_and_commit_goal_provenance_bindings(
                state,
                criterion_ids,
                source_catalog,
                {"decision": "pass", "bindings": collected_bindings},
            )
            self._commit_goal_criterion_evidence_records(state, claims)
        except ModelProtocolError as exc:
            self._persist(
                state,
                "goal_criterion_provenance_commit_blocked",
                {
                    "criterion_ids": criterion_ids,
                    "error": str(exc)[:2000],
                    "controller_semantic_fields_generated": False,
                },
            )
            return False
        committed = bool(claims)
        self._persist(
            state,
            (
                "goal_criterion_provenance_committed"
                if committed
                else "goal_criterion_provenance_replan_requested"
            ),
            {
                "claim_ids": [claim.claim_id for claim in claims],
                "criterion_ids": [claim.criterion_id for claim in claims],
                "producer_task_ids": [claim.producer_task_id for claim in claims],
                "protocol": "rwkv_goal_provenance_commit.v1",
                "controller_semantic_fields_generated": False,
            },
        )
        return committed

    @staticmethod
    def _completed_active_tasks(state: RunState) -> list:
        return [
            task
            for task in sorted(
                state.tasks.values(),
                key=lambda item: (item.insertion_order, item.task_id),
            )
            if task.active and task.status == TaskStatus.COMPLETED
        ]

    def _criterion_provenance_source(
        self,
        state: RunState,
        memory_id: str,
    ) -> dict[str, Any]:
        entry = state.memory_index[memory_id]
        owner = state.tasks.get(entry.task_id)
        workspace_digests = {
            state.artifacts[artifact_id].path: state.artifacts[artifact_id].sha256
            for artifact_id in entry.artifact_refs
            if artifact_id in state.artifacts
            and state.artifacts[artifact_id].path
        }
        action_arguments = {}
        if owner is not None:
            action_arguments = {
                key: value
                for key, value in owner.action.arguments.items()
                if key
                in {
                    "path",
                    "source",
                    "destination",
                    "start_char",
                    "start_after",
                    "recursive",
                }
            }
        preview_limit = 240
        source_content = entry.content or entry.summary
        attempt_id = owner.attempt_ids[-1] if owner and owner.attempt_ids else ""
        return {
            "ref": memory_id,
            "source_type": "memory",
            "owner_task_id": entry.task_id,
            "owner_attempt_id": attempt_id,
            "action": (
                {
                    "name": owner.action.action_type,
                    "arguments": action_arguments,
                }
                if owner is not None
                else {}
            ),
            "workspace_paths": sorted(workspace_digests),
            "workspace_digests": dict(sorted(workspace_digests.items())),
            "content_digest": self._provenance_memory_digest(state, memory_id),
            "content_preview": source_content[:preview_limit],
            "content_preview_truncated": len(source_content) > preview_limit,
        }

    def _goal_criterion_provenance_catalog(
        self,
        state: RunState,
        criterion_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        actual_sources: list[dict[str, Any]] = []
        for task in self._completed_active_tasks(state):
            memory_ids = self._canonical_goal_memory_ids(state, task)
            actual_sources.extend(
                self._criterion_provenance_source(state, memory_id)
                for memory_id in memory_ids
            )
            if not memory_ids:
                actual_sources.extend(
                    self._recovered_workspace_provenance_sources(state, task)
                )
        expected_sources = [
            {
                "ref": "GOAL",
                "source_type": "goal",
                "owner_task_id": "GOAL",
                "owner_attempt_id": "",
                "workspace_paths": [],
                "workspace_digests": {},
                "content_digest": state.goal.digest,
                "content_preview": state.goal.original_request[:480],
                "content_preview_truncated": len(state.goal.original_request)
                > 480,
                "evidence_role": "immutable_goal",
            },
            *[
                {**source, "evidence_role": "original_read_only_observation"}
                for source in actual_sources
                if self._is_original_read_only_provenance(state, source)
            ],
        ]
        for source in actual_sources:
            source_paths = set(source.get("workspace_paths") or [])
            source["eligible_expected_refs"] = [
                str(expected.get("ref") or "")
                for expected in expected_sources
                if str(expected.get("ref") or "")
                and str(expected.get("ref") or "")
                != str(source.get("ref") or "")
                and not (
                    source_paths
                    & set(expected.get("workspace_paths") or [])
                )
            ]
        return {
            "schema_version": "rwkv-lh.goal-criterion-provenance-catalog.v1",
            "goal_digest": state.goal.digest,
            "claimed_criterion_ids": list(
                criterion_ids
                if criterion_ids is not None
                else self._missing_goal_criteria(state)
            ),
            "causal_actual_sources": actual_sources,
            "independent_expected_sources": expected_sources,
        }

    @staticmethod
    def _canonical_goal_memory_ids(state: RunState, task) -> list[str]:
        memory_ids = list(
            dict.fromkeys(
                ref for ref in task.output_refs if ref in state.memory_index
            )
        )
        snapshot_artifacts = {
            artifact_ref
            for memory_id in memory_ids
            if state.memory_index[memory_id].kind
            == "post_action_workspace_snapshot"
            for artifact_ref in state.memory_index[memory_id].artifact_refs
        }
        if not snapshot_artifacts:
            return memory_ids
        return [
            memory_id
            for memory_id in memory_ids
            if not (
                state.memory_index[memory_id].kind == "action_result"
                and bool(
                    set(state.memory_index[memory_id].artifact_refs)
                    & snapshot_artifacts
                )
            )
        ]

    def _is_original_read_only_provenance(
        self,
        state: RunState,
        source: Mapping[str, Any],
    ) -> bool:
        owner_task_id = str(source.get("owner_task_id") or "")
        owner = state.tasks.get(owner_task_id)
        paths = set(source.get("workspace_paths") or [])
        if owner is None or not paths:
            return False
        try:
            if not self.harness.definition(owner.action.action_type).read_only:
                return False
        except HarnessError:
            return False
        for candidate in state.tasks.values():
            if (
                not candidate.active
                or candidate.status != TaskStatus.COMPLETED
                or candidate.insertion_order >= owner.insertion_order
            ):
                continue
            try:
                if not self.harness.definition(
                    candidate.action.action_type
                ).side_effect:
                    continue
            except HarnessError:
                continue
            targets = set(candidate.effect_targets)
            for key in ("path", "destination"):
                value = str(candidate.action.arguments.get(key) or "").strip()
                if value:
                    targets.add(value)
            if paths & targets:
                return False
        return True

    def _recovered_workspace_provenance_sources(
        self,
        state: RunState,
        task,
    ) -> list[dict[str, Any]]:
        """Represent a recovered effect when the pre-crash action memory is absent."""

        attempt_id = task.attempt_ids[-1] if task.attempt_ids else ""
        attempt = state.attempts.get(attempt_id)
        if attempt is None or attempt.status != AttemptStatus.SUCCEEDED:
            return []
        root = Path(state.goal.workspace_root).resolve(strict=True)
        paths: set[str] = set()
        for result in attempt.validation_results:
            if not result.passed or not isinstance(result.evidence, Mapping):
                continue
            raw_path = str(result.evidence.get("path") or "").strip()
            if not raw_path:
                continue
            try:
                resolved = Path(raw_path).resolve(strict=True)
                paths.add(resolved.relative_to(root).as_posix())
            except (FileNotFoundError, OSError, ValueError):
                continue

        sources: list[dict[str, Any]] = []
        for relative in sorted(paths):
            try:
                resolved = self.harness.resolve_path(
                    state.goal,
                    relative,
                    must_exist=True,
                )
                if not resolved.is_file():
                    continue
                content_bytes = resolved.read_bytes()
            except (FileNotFoundError, OSError, ValueError):
                continue
            workspace_digest = hashlib.sha256(content_bytes).hexdigest()
            try:
                content = content_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content = ""
            payload_digest = hashlib.sha256(
                json.dumps(
                    {"path": relative, "sha256": workspace_digest},
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            preview_limit = 240
            sources.append(
                {
                    "ref": f"WORKSPACE:{attempt_id}:{relative}",
                    "source_type": "workspace_recovery_observation",
                    "owner_task_id": task.task_id,
                    "owner_attempt_id": attempt_id,
                    "action": {
                        "name": "observe_recovered_workspace_effect",
                        "arguments": {"path": relative},
                    },
                    "workspace_paths": [relative],
                    "workspace_digests": {relative: workspace_digest},
                    "content_digest": payload_digest,
                    "content_preview": content[:preview_limit],
                    "content_preview_truncated": len(content) > preview_limit,
                }
            )
        return sources

    @staticmethod
    def _provenance_memory_digest(state: RunState, memory_id: str) -> str:
        entry = state.memory_index[memory_id]
        artifact_hashes = sorted(
            state.artifacts[artifact_id].sha256
            for artifact_id in entry.artifact_refs
            if artifact_id in state.artifacts
        )
        payload = {
            "memory_id": memory_id,
            "task_id": entry.task_id,
            "kind": entry.kind,
            "summary": entry.summary,
            "content": entry.content,
            "artifact_hashes": artifact_hashes,
            "evidence_refs": list(entry.evidence_refs),
        }
        return hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()

    def _validate_and_commit_goal_provenance_bindings(
        self,
        state: RunState,
        declared: list[str],
        catalog: Mapping[str, Any],
        proposal: Any,
    ) -> list[CriterionClaim]:
        if not isinstance(proposal, Mapping):
            raise ModelProtocolError("criterion evidence proposal must be an object")
        decision = str(proposal.get("decision") or "").strip().casefold()
        bindings = proposal.get("bindings")
        if decision == "replan" and bindings == []:
            return []
        if decision != "pass" or not isinstance(bindings, list):
            raise ModelProtocolError("criterion evidence proposal must pass with bindings or replan empty")
        required_binding_fields = {"criterion_id", "actual_ref", "expected_ref"}
        allowed_binding_fields = {*required_binding_fields, "reason"}
        if not all(
            isinstance(item, Mapping)
            and required_binding_fields.issubset(item)
            and not set(item) - allowed_binding_fields
            and all(
                isinstance(item.get(field), str)
                and bool(str(item.get(field) or "").strip())
                for field in required_binding_fields
            )
            and (
                "reason" not in item
                or (
                    isinstance(item.get("reason"), str)
                    and bool(str(item.get("reason") or "").strip())
                )
            )
            for item in bindings
        ):
            raise ModelProtocolError(
                "criterion provenance bindings require three non-empty refs and optional reason"
            )
        criterion_ids = [str(item.get("criterion_id") or "") for item in bindings]
        if sorted(criterion_ids) != sorted(declared) or len(set(criterion_ids)) != len(bindings):
            raise ModelProtocolError(
                "criterion provenance bindings must cover each claimed criterion exactly once"
            )
        actual_sources = {
            str(item.get("ref") or ""): dict(item)
            for item in catalog.get("causal_actual_sources") or []
        }
        expected_sources = {
            str(item.get("ref") or ""): dict(item)
            for item in catalog.get("independent_expected_sources") or []
        }
        claims: list[CriterionClaim] = []
        for index, binding in enumerate(bindings, start=1):
            actual_ref = str(binding.get("actual_ref") or "")
            expected_ref = str(binding.get("expected_ref") or "")
            actual = actual_sources.get(actual_ref)
            expected = expected_sources.get(expected_ref)
            if actual is None:
                raise ModelProtocolError(
                    "actual_ref is outside completed active causal observations"
                )
            if expected is None:
                raise ModelProtocolError(
                    "expected_ref is outside Goal/completed causal observations"
                )
            if actual_ref == expected_ref:
                raise ModelProtocolError("actual_ref and expected_ref must be independent")
            producer_task_id = str(actual.get("owner_task_id") or "")
            attempt_id = str(actual.get("owner_attempt_id") or "")
            producer = state.tasks.get(producer_task_id)
            attempt = state.attempts.get(attempt_id)
            if (
                producer is None
                or not producer.active
                or producer.status != TaskStatus.COMPLETED
                or attempt is None
                or attempt.task_id != producer_task_id
                or attempt.status != AttemptStatus.SUCCEEDED
            ):
                raise ModelProtocolError(
                    "actual_ref owner must be a completed active Task with a succeeded Attempt"
                )
            actual_paths = set(actual.get("workspace_paths") or [])
            expected_paths = set(expected.get("workspace_paths") or [])
            overlap = sorted(actual_paths & expected_paths)
            if overlap:
                raise ModelProtocolError(
                    f"actual and expected share workspace path lineage: {overlap}"
                )
            eligible_expected_refs = {
                str(item or "")
                for item in actual.get("eligible_expected_refs") or []
                if str(item or "")
            }
            if (
                "eligible_expected_refs" in actual
                and expected_ref not in eligible_expected_refs
            ):
                raise ModelProtocolError(
                    "expected_ref is not an eligible independent source for actual_ref"
                )
            actual_digest = str(actual.get("content_digest") or "")
            expected_digest = str(expected.get("content_digest") or "")
            criterion_id = str(binding.get("criterion_id") or "")
            claim_key = hashlib.sha256(
                f"{state.goal.digest}\0{criterion_id}\0{actual_ref}\0{actual_digest}\0{expected_ref}\0{expected_digest}".encode(
                    "utf-8"
                )
            ).hexdigest()[:16]
            claim_id = f"CC-GOAL-{criterion_id}-{claim_key}"
            observation_digest = hashlib.sha256(
                f"{state.goal.digest}\0{actual_ref}\0{actual_digest}\0{expected_ref}\0{expected_digest}".encode(
                    "utf-8"
                )
            ).hexdigest()
            raw_claim = {
                "criterion_id": criterion_id,
                "actual_ref": actual_ref,
                "actual_digest": actual_digest,
                "actual_workspace_paths": sorted(actual_paths),
                "actual_workspace_digests": dict(actual.get("workspace_digests") or {}),
                "expected_ref": expected_ref,
                "expected_digest": expected_digest,
                "expected_workspace_paths": sorted(expected_paths),
                "expected_workspace_digests": dict(expected.get("workspace_digests") or {}),
                "goal_digest": state.goal.digest,
                "protocol": "rwkv_goal_provenance_commit.v1",
            }
            if "reason" in binding:
                raw_claim["reason"] = str(binding.get("reason") or "")
            proof_refs = [
                EvidenceRef(
                    evidence_ref_id=f"{claim_id}:actual",
                    source_type=str(actual.get("source_type") or "memory"),
                    source_id=actual_ref,
                    source_sha256=actual_digest,
                    metadata={"side": "actual", "workspace_paths": sorted(actual_paths)},
                ),
                EvidenceRef(
                    evidence_ref_id=f"{claim_id}:expected",
                    source_type=str(
                        expected.get("source_type")
                        or ("goal" if expected_ref == "GOAL" else "memory")
                    ),
                    source_id=expected_ref,
                    source_sha256=expected_digest,
                    metadata={"side": "expected", "workspace_paths": sorted(expected_paths)},
                ),
            ]
            claim = CriterionClaim(
                claim_id=claim_id,
                criterion_id=raw_claim["criterion_id"],
                subject_task_id=producer_task_id,
                producer_task_id=producer_task_id,
                attempt_id=attempt_id,
                comparison="rwkv_goal_provenance_commit",
                actual=ProofExpr("provenance_ref", {"ref": actual_ref}),
                expected=ProofExpr("provenance_ref", {"ref": expected_ref}),
                status=CriterionClaimStatus.VERIFIED,
                passed=True,
                reason="independent provenance refs validated",
                rwkv_reason=str(binding.get("reason") or ""),
                proof_refs=proof_refs,
                actual_value_sha256=actual_digest,
                expected_value_sha256=expected_digest,
                observation_digest=observation_digest,
                raw_claim=raw_claim,
                claim_protocol="rwkv_goal_provenance_commit.v1",
            )
            claims.append(claim)
        for claim in claims:
            state.criterion_claims[claim.claim_id] = claim
        return claims

    @staticmethod
    def _commit_goal_criterion_evidence_records(
        state: RunState,
        claims: list[CriterionClaim],
    ) -> None:
        for claim in claims:
            attempt = state.attempts.get(claim.attempt_id)
            if attempt is None:
                raise ModelProtocolError(
                    "criterion claim producer Attempt disappeared before commit"
                )
            validation_refs = [
                f"{attempt.attempt_id}:V{index}"
                for index, result in enumerate(attempt.validation_results, start=1)
                if result.passed
            ]
            actual_memory = state.memory_index.get(
                str(claim.raw_claim.get("actual_ref") or "")
            )
            source_artifacts = (
                list(actual_memory.artifact_refs)
                if actual_memory is not None
                else []
            )
            evidence_id = f"CE-{claim.criterion_id}-{claim.claim_id[-16:]}"
            state.criterion_evidence[evidence_id] = CriterionEvidence(
                evidence_id=evidence_id,
                criterion_id=claim.criterion_id,
                status=CriterionEvidenceStatus.VERIFIED,
                owner_task_id=claim.producer_task_id,
                attempt_id=attempt.attempt_id,
                validation_refs=validation_refs,
                artifact_refs=list(
                    dict.fromkeys([*attempt.artifact_refs, *source_artifacts])
                ),
                state_ref=None,
                claim_id=claim.claim_id,
                proof_refs=[ref.evidence_ref_id for ref in claim.proof_refs],
                observation_digest=claim.observation_digest,
            )

    def _cross_check_with_observation_gate(
        self,
        state: RunState,
        task,
        action_result: ActionResult,
        validation_results: list[ValidationResult],
        *,
        kind: str,
        required: bool,
        parameters: Mapping[str, Any],
    ) -> ValidationResult:
        observation = self._build_cross_check_observation(
            state,
            task,
            action_result,
            validation_results,
            kind=kind,
            parameters=parameters,
        )
        digest = str(observation.get("observation_digest") or "")
        cacheable = bool(observation.get("cacheable", False)) and bool(digest)
        attempt_id = task.attempt_ids[-1] if task.attempt_ids else ""
        self._persist(
            state,
            "cross_check_observation_prepared",
            {
                "task_id": task.task_id,
                "attempt_id": attempt_id,
                "validation_kind": kind,
                "observation_digest": digest,
                "cacheable": cacheable,
                "uncacheable_reason": observation.get("uncacheable_reason", ""),
                "observation": observation.get("capsule", {}),
            },
        )

        cached: dict[str, Any] | None = None
        lineage = (
            state.recovery_states.get(task.recovery_lineage_id)
            if task.recovery_lineage_id
            else None
        )
        if cacheable and lineage is not None:
            candidate = lineage.failed_observations.get(digest)
            if (
                isinstance(candidate, Mapping)
                and candidate.get("validation_kind") == kind
                and candidate.get("decision") == "replan"
                and candidate.get("protocol_valid") is True
            ):
                cached = dict(candidate)

        if cached is not None:
            lineage.suppressed_cross_check_count += 1
            lineage.updated_at = utc_now()
            self._persist(
                state,
                "unchanged_observation_cross_check_suppressed",
                {
                    "lineage_id": lineage.lineage_id,
                    "task_id": task.task_id,
                    "attempt_id": attempt_id,
                    "validation_kind": kind,
                    "observation_digest": digest,
                    "original_task_id": cached.get("task_id", ""),
                    "original_attempt_id": cached.get("attempt_id", ""),
                    "original_validation_ref": cached.get("validation_ref", ""),
                    "rwkv_reason": cached.get("message", ""),
                    "reused_decision": "replan",
                },
            )
            return ValidationResult(
                kind=kind,
                passed=False,
                required=required,
                message=str(cached.get("message") or ""),
                evidence={
                    "owner": "rwkv_prior_failure",
                    "scope": "task_local",
                    "goal_digest": state.goal.digest,
                    "criterion_ids": list(task.satisfies_criteria),
                    "observation_digest": digest,
                    "workspace_digest": observation.get("workspace_digest", ""),
                    "observation_cacheable": True,
                    "protocol_valid": True,
                    "decision": "replan",
                    "decision_source": "prior_rwkv_replan",
                    "criterion_assertion_evaluated": False,
                    "proof_passed": None,
                    "criterion_claim_ids": [],
                    "original_task_id": cached.get("task_id", ""),
                    "original_attempt_id": cached.get("attempt_id", ""),
                    "original_validation_ref": cached.get("validation_ref", ""),
                },
            )

        postcondition_method = (
            getattr(self.model, "commit_task_postcondition", None)
            if self.model is not None
            else None
        )
        method = postcondition_method
        if not callable(method):
            # Compatibility for deterministic test adapters. LongHorizonModel
            # always uses the single task-postcondition protocol here.
            method = (
                getattr(self.model, "cross_validate", None)
                if self.model is not None
                else None
            )
        if not callable(method):
            return ValidationResult(
                kind=kind,
                passed=False,
                required=required,
                message="model cross-check adapter is unavailable",
                evidence={
                    "owner": "runtime",
                    "scope": "task_local",
                    "observation_digest": digest,
                    "observation_cacheable": cacheable,
                    "protocol_valid": False,
                    "decision_source": "adapter_unavailable",
                },
            )
        # A Task-level model call decides only the active Task postcondition.
        # It cannot create, bind, revise, or validate Goal criterion evidence.
        context = self.memory.build_task_validation(state, task)
        self._persist(
            state,
            "execution_capsule_prepared",
            {
                "task_id": task.task_id,
                "attempt_id": attempt_id,
                "request_scope": kind,
                "capsule": context.to_dict(),
            },
        )
        protocol_valid = True
        try:
            raw_decision = method(
                state,
                task,
                context,
                self._persist_callback(),
                action_result=action_result.to_dict(),
                validation_results=[vars(item) for item in validation_results],
            )
            decision = self._normalize_cross_validation_decision(raw_decision)
        except ModelProtocolError as exc:
            decision = CrossValidationDecision(
                False,
                f"ModelProtocolError: {exc}",
                [],
            )
            protocol_valid = False
        return ValidationResult(
            kind=kind,
            passed=bool(decision.passed),
            required=required,
            message=str(decision.reason),
            evidence={
                "owner": "rwkv",
                "scope": "task_local",
                "goal_digest": state.goal.digest,
                "criterion_ids": list(task.satisfies_criteria),
                "observation_digest": digest,
                "workspace_digest": observation.get("workspace_digest", ""),
                "observation_cacheable": cacheable,
                "protocol_valid": protocol_valid,
                "decision": "pass" if decision.passed else "replan",
                "decision_source": "rwkv_current",
                "criterion_assertion_evaluated": False,
                "proof_passed": None,
                "criterion_claim_ids": [],
            },
        )
    @staticmethod
    def _normalize_cross_validation_decision(value: Any) -> CrossValidationDecision:
        if isinstance(value, CrossValidationDecision):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            # Compatibility is intentionally limited to non-production test
            # adapters. A legacy tuple carries no CriterionClaim and therefore
            # can never create independent Goal evidence.
            return CrossValidationDecision(bool(value[0]), str(value[1]), [])
        raise ModelProtocolError(
            "cross_validate must return CrossValidationDecision"
        )

    def _build_cross_check_observation(
        self,
        state: RunState,
        task,
        action_result: ActionResult,
        validation_results: list[ValidationResult],
        *,
        kind: str,
        parameters: Mapping[str, Any],
    ) -> dict[str, Any]:
        definition = self.harness.definition(task.action.action_type)
        snapshot = self.harness.workspace_observation_snapshot(state.goal)
        bound_ids = list(
            dict.fromkeys([*task.advances_criteria, *task.satisfies_criteria])
        )
        bound_criteria = [
            {
                "criterion_id": criterion.criterion_id,
                "description": criterion.description,
                "required": criterion.required,
            }
            for criterion in state.goal.success_criteria
            if criterion.criterion_id in bound_ids
        ]
        dependencies: list[dict[str, Any]] = []
        for dependency_id in task.dependencies:
            dependency = state.tasks.get(dependency_id)
            if dependency is None:
                dependencies.append({"task_id": dependency_id, "missing": True})
                continue
            memory_entries = []
            artifact_entries = []
            for output_ref in dependency.output_refs:
                memory = state.memory_index.get(output_ref)
                if memory is not None:
                    memory_entries.append(
                        {
                            "kind": memory.kind,
                            "summary": memory.summary,
                            "content": memory.content,
                            "artifact_refs": list(memory.artifact_refs),
                            "evidence_refs": list(memory.evidence_refs),
                        }
                    )
                artifact = state.artifacts.get(output_ref)
                if artifact is not None:
                    artifact_entries.append(
                        {
                            "path": artifact.path,
                            "sha256": artifact.sha256,
                            "media_type": artifact.media_type,
                            "summary": artifact.summary,
                        }
                    )
            dependencies.append(
                {
                    "task_id": dependency_id,
                    "title": dependency.title,
                    "description": dependency.description,
                    "status": dependency.status.value,
                    "action": {
                        "type": dependency.action.action_type,
                        "arguments": dependency.action.arguments,
                    },
                    "memory": memory_entries,
                    "artifacts": artifact_entries,
                }
            )

        capsule = {
            "schema_version": "rwkv-lh.cross-check-observation.v1",
            "check": {"kind": kind, "parameters": dict(parameters)},
            "goal": {
                "digest": state.goal.digest,
                "constraints": list(state.goal.constraints),
                "bound_criteria": bound_criteria,
            },
            "task": {
                "title": task.title,
                "description": task.description,
                "required": task.required,
                "dependencies": list(task.dependencies),
                "advances_criteria": list(task.advances_criteria),
                "satisfies_criteria": list(task.satisfies_criteria),
                "inputs": list(task.inputs),
                "action": {
                    "type": task.action.action_type,
                    "arguments": task.action.arguments,
                },
                "completion_criteria": [
                    {
                        "kind": item.kind,
                        "parameters": item.parameters,
                        "required": item.required,
                    }
                    for item in task.completion_criteria
                ],
                "subject_task_id": self._validation_subject_task_id(state, task),
            },
            "dependencies": dependencies,
            "action_result": action_result.to_dict(),
            "deterministic_validation_results": [
                {
                    "kind": item.kind,
                    "passed": item.passed,
                    "required": item.required,
                    "message": item.message,
                    "evidence": item.evidence,
                }
                for item in validation_results
                if item.kind not in {"model_cross_check", "criterion_cross_check"}
            ],
            "workspace": snapshot,
        }
        cacheable = bool(definition.failure_observation_cacheable)
        uncacheable_reason = ""
        if not cacheable:
            uncacheable_reason = "action_definition_not_cacheable"
        elif not bool(snapshot.get("cacheable", False)):
            cacheable = False
            uncacheable_reason = str(
                snapshot.get("reason") or "workspace_snapshot_incomplete"
            )
        digest = ""
        if cacheable:
            try:
                encoded = json.dumps(
                    capsule,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
                digest = hashlib.sha256(encoded).hexdigest()
            except (TypeError, ValueError) as exc:
                cacheable = False
                uncacheable_reason = (
                    f"observation_not_canonical:{type(exc).__name__}:{exc}"
                )
        return {
            "cacheable": cacheable,
            "uncacheable_reason": uncacheable_reason,
            "observation_digest": digest,
            "workspace_digest": str(snapshot.get("digest") or ""),
            "capsule": capsule,
        }

    @staticmethod
    def _validation_subject_task_id(state: RunState, task) -> str:
        if task.subject_task_id and task.subject_task_id in state.tasks:
            return task.subject_task_id
        if task.recovery_lineage_id:
            lineage = state.recovery_states.get(task.recovery_lineage_id)
            if lineage is not None and lineage.subject_task_id in state.tasks:
                return lineage.subject_task_id
        if task.action.action_type in {"run_command", "check_command"}:
            completed_dependencies = [
                dependency
                for dependency in task.dependencies
                if dependency in state.tasks
                and state.tasks[dependency].status == TaskStatus.COMPLETED
            ]
            if completed_dependencies:
                return completed_dependencies[-1]
        return task.task_id

    @staticmethod
    def _failure_fingerprint(task, subject_task_id: str, failed: list[ValidationResult]) -> str:
        payload = {
            "subject_task_id": subject_task_id,
            "action": {
                "type": task.action.action_type,
                "arguments": task.action.arguments,
            },
            "verifiers": [
                {
                    "kind": item.kind,
                    "message": item.message,
                    "criterion_ids": item.criterion_ids,
                }
                for item in failed
            ],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(encoded).hexdigest()

    def _record_recovery_failure(
        self,
        state: RunState,
        task,
        validation_results: list[ValidationResult],
    ) -> RecoveryState:
        failed = [item for item in validation_results if item.required and not item.passed]
        fingerprint = next(
            (item.failure_fingerprint for item in failed if item.failure_fingerprint),
            self._failure_fingerprint(
                task,
                self._validation_subject_task_id(state, task),
                failed,
            ),
        )
        lineage = (
            state.recovery_states.get(task.recovery_lineage_id)
            if task.recovery_lineage_id
            else None
        )
        if lineage is None:
            lineage_id = f"RL-{len(state.recovery_states) + 1:04d}"
            lineage = RecoveryState(
                lineage_id=lineage_id,
                root_task_id=task.task_id,
                failed_task_id=task.task_id,
                subject_task_id=self._validation_subject_task_id(state, task),
                remaining_budget=max(1, task.retry_policy.max_attempts),
                task_ids=[task.task_id],
            )
            state.recovery_states[lineage_id] = lineage
            task.recovery_lineage_id = lineage_id
            task.subject_task_id = lineage.subject_task_id
        previous_same = 0
        for entry in reversed(lineage.decision_history):
            if entry.get("type") != "failure":
                continue
            if entry.get("failure_fingerprint") != fingerprint:
                break
            previous_same += 1
        lineage.failure_fingerprint = fingerprint
        lineage.same_failure_count = previous_same
        lineage.failed_task_id = task.task_id
        lineage.remaining_budget = max(0, lineage.remaining_budget - 1)
        lineage.updated_at = utc_now()
        registered_observations: list[dict[str, Any]] = []
        for index, result in enumerate(validation_results, start=1):
            if not result.required or result.passed or result.kind not in {
                "model_cross_check",
                "criterion_cross_check",
                "task_postcondition_cross_check",
            }:
                continue
            evidence = result.evidence if isinstance(result.evidence, Mapping) else {}
            digest = str(evidence.get("observation_digest") or "")
            if not (
                digest
                and evidence.get("observation_cacheable") is True
                and evidence.get("protocol_valid") is True
                and evidence.get("decision") == "replan"
                and evidence.get("decision_source") == "rwkv_current"
            ):
                continue
            attempt_id = task.attempt_ids[-1] if task.attempt_ids else ""
            validation_ref = f"{attempt_id}:V{index}" if attempt_id else ""
            entry = {
                "validation_kind": result.kind,
                "decision": "replan",
                "protocol_valid": True,
                "message": result.message,
                "task_id": task.task_id,
                "attempt_id": attempt_id,
                "validation_ref": validation_ref,
                "workspace_digest": str(evidence.get("workspace_digest") or ""),
                "recorded_at": lineage.updated_at,
            }
            if digest not in lineage.failed_observations:
                lineage.failed_observations[digest] = entry
                registered_observations.append(
                    {"observation_digest": digest, **entry}
                )
        lineage.decision_history.append(
            {
                "type": "failure",
                "task_id": task.task_id,
                "subject_task_id": lineage.subject_task_id,
                "failure_fingerprint": fingerprint,
                "same_failure_count": previous_same,
                "at": lineage.updated_at,
            }
        )
        if registered_observations:
            self._persist(
                state,
                "failed_cross_check_observation_registered",
                {
                    "lineage_id": lineage.lineage_id,
                    "task_id": task.task_id,
                    "observations": registered_observations,
                },
            )
        return lineage

    @staticmethod
    def _record_recovery_decision(state: RunState, task, decision: str, reason: str) -> None:
        if not task.recovery_lineage_id:
            return
        lineage = state.recovery_states.get(task.recovery_lineage_id)
        if lineage is None:
            return
        lineage.updated_at = utc_now()
        lineage.decision_history.append(
            {
                "type": "decision",
                "task_id": task.task_id,
                "decision": decision,
                "reason": str(reason)[:2000],
                "at": lineage.updated_at,
            }
        )

    def _revalidate_provenance_claim(
        self,
        state: RunState,
        claim: CriterionClaim,
    ) -> str:
        """Recheck controller-owned scope and digest invariants without re-deciding semantics."""

        raw = claim.raw_claim
        if not isinstance(raw, Mapping):
            return "criterion provenance claim payload is missing"
        if raw.get("protocol") not in {
            "rwkv_provenance_commit.v1",
            "rwkv_goal_provenance_commit.v1",
        }:
            return "criterion provenance protocol marker changed"
        if raw.get("goal_digest") != state.goal.digest:
            return "immutable Goal digest changed"
        if raw.get("criterion_id") != claim.criterion_id:
            return "criterion provenance id changed"

        catalog = self._goal_criterion_provenance_catalog(
            state,
            [claim.criterion_id],
        )
        actual_sources = {
            str(item.get("ref") or ""): item
            for item in catalog.get("causal_actual_sources") or []
            if isinstance(item, Mapping)
        }
        expected_sources = {
            str(item.get("ref") or ""): item
            for item in catalog.get("independent_expected_sources") or []
            if isinstance(item, Mapping)
        }
        actual_ref = str(raw.get("actual_ref") or "")
        expected_ref = str(raw.get("expected_ref") or "")
        actual = actual_sources.get(actual_ref)
        expected = expected_sources.get(expected_ref)
        if actual is None:
            return "actual provenance ref left completed active causal scope"
        if expected is None:
            return "expected provenance ref left Goal/completed causal scope"
        if actual_ref == expected_ref:
            return "actual and expected provenance refs are identical"

        actual_paths = sorted(actual.get("workspace_paths") or [])
        expected_paths = sorted(expected.get("workspace_paths") or [])
        if set(actual_paths) & set(expected_paths):
            return "actual and expected now share workspace path lineage"
        actual_digest = str(actual.get("content_digest") or "")
        expected_digest = str(expected.get("content_digest") or "")
        if actual_digest != raw.get("actual_digest"):
            return "actual provenance content digest changed"
        if expected_digest != raw.get("expected_digest"):
            return "expected provenance content digest changed"
        if actual_paths != sorted(raw.get("actual_workspace_paths") or []):
            return "actual provenance workspace lineage changed"
        if expected_paths != sorted(raw.get("expected_workspace_paths") or []):
            return "expected provenance workspace lineage changed"

        actual_workspace_digests = dict(actual.get("workspace_digests") or {})
        expected_workspace_digests = dict(expected.get("workspace_digests") or {})
        if actual_workspace_digests != dict(
            raw.get("actual_workspace_digests") or {}
        ):
            return "actual provenance artifact digest changed"
        if expected_workspace_digests != dict(
            raw.get("expected_workspace_digests") or {}
        ):
            return "expected provenance artifact digest changed"
        for path, recorded_digest in {
            **expected_workspace_digests,
            **actual_workspace_digests,
        }.items():
            try:
                resolved = self.harness.resolve_path(
                    state.goal,
                    path,
                    must_exist=True,
                )
                live_digest = (
                    hashlib.sha256(resolved.read_bytes()).hexdigest()
                    if resolved.is_file()
                    else hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()
                )
            except Exception as exc:
                return f"provenance workspace source unavailable: {type(exc).__name__}"
            if live_digest != recorded_digest:
                return f"provenance workspace source changed: {path}"

        expected_observation_digest = hashlib.sha256(
            f"{state.goal.digest}\0{actual_ref}\0{actual_digest}\0{expected_ref}\0{expected_digest}".encode(
                "utf-8"
            )
        ).hexdigest()
        if claim.observation_digest != expected_observation_digest:
            return "criterion provenance observation digest changed"
        if claim.actual_value_sha256 != actual_digest:
            return "criterion actual evidence digest changed"
        if claim.expected_value_sha256 != expected_digest:
            return "criterion expected evidence digest changed"
        ref_pairs = {
            (ref.metadata.get("side"), ref.source_id, ref.source_sha256)
            for ref in claim.proof_refs
        }
        if ref_pairs != {
            ("actual", actual_ref, actual_digest),
            ("expected", expected_ref, expected_digest),
        }:
            return "criterion provenance proof refs changed"
        return ""

    def _revalidate_goal_proofs(self, state: RunState) -> list[str]:
        invalidated: list[dict[str, str]] = []
        for evidence in state.criterion_evidence.values():
            if evidence.status != CriterionEvidenceStatus.VERIFIED:
                continue
            claim = state.criterion_claims.get(evidence.claim_id)
            reason = ""
            if claim is None:
                reason = "criterion evidence has no CriterionClaim"
            elif claim.status != CriterionClaimStatus.VERIFIED or not claim.passed:
                reason = "criterion claim is no longer verified"
            else:
                attempt = state.attempts.get(claim.attempt_id)
                task = (
                    state.tasks.get(attempt.task_id)
                    if attempt is not None
                    else None
                )
                if attempt is None or task is None:
                    reason = "criterion claim attempt or task is missing"
                else:
                    if claim.claim_protocol in {
                        "rwkv_provenance_commit.v1",
                        "rwkv_goal_provenance_commit.v1",
                    }:
                        reason = self._revalidate_provenance_claim(
                            state,
                            claim,
                        )
                        refreshed = None
                    elif claim.claim_protocol == "read_operator_assertion.v1":
                        refreshed = self.proof_engine.evaluate_operator_assertion(
                            state,
                            task,
                            attempt,
                            claim.raw_claim,
                            claim_id=claim.claim_id,
                            rwkv_reason=claim.rwkv_reason,
                        )
                    elif claim.claim_protocol == "linear_typed_assertion.v1":
                        refreshed = self.proof_engine.evaluate_linear_assertion(
                            state,
                            task,
                            attempt,
                            claim.raw_claim,
                            claim_id=claim.claim_id,
                            rwkv_reason=claim.rwkv_reason,
                        )
                    else:
                        refreshed = self.proof_engine.evaluate_claim(
                            state,
                            task,
                            attempt,
                            claim.raw_claim,
                            claim_id=claim.claim_id,
                            rwkv_reason=claim.rwkv_reason,
                        )
                    if refreshed is not None:
                        if (
                            refreshed.status != CriterionClaimStatus.VERIFIED
                            or not refreshed.passed
                        ):
                            reason = refreshed.reason
                        elif refreshed.observation_digest != claim.observation_digest:
                            reason = "criterion proof provenance changed"
            if not reason:
                continue
            evidence.status = CriterionEvidenceStatus.INVALIDATED
            evidence.invalidated_by = "final_proof_revalidation"
            if claim is not None:
                claim.status = CriterionClaimStatus.INVALIDATED
                claim.passed = False
                claim.invalidated_at = utc_now()
                claim.invalidated_reason = reason
            invalidated.append(
                {
                    "criterion_id": evidence.criterion_id,
                    "evidence_id": evidence.evidence_id,
                    "claim_id": evidence.claim_id,
                    "reason": reason,
                }
            )
        if invalidated:
            self._persist(
                state,
                "criterion_proofs_invalidated",
                {"invalidated": invalidated},
            )
        return [item["claim_id"] for item in invalidated]

    @staticmethod
    def _invalidate_criterion_evidence(
        state: RunState,
        owner_task_id: str,
        *,
        invalidated_by: str,
    ) -> None:
        for evidence in state.criterion_evidence.values():
            if (
                evidence.owner_task_id == owner_task_id
                and evidence.status == CriterionEvidenceStatus.VERIFIED
            ):
                evidence.status = CriterionEvidenceStatus.INVALIDATED
                evidence.invalidated_by = invalidated_by
                claim = state.criterion_claims.get(evidence.claim_id)
                if claim is not None:
                    claim.status = CriterionClaimStatus.INVALIDATED
                    claim.passed = False
                    claim.invalidated_at = utc_now()
                    claim.invalidated_reason = invalidated_by

    @staticmethod
    def _goal_criteria_covered(state: RunState) -> bool:
        required = {
            criterion.criterion_id
            for criterion in state.goal.success_criteria
            if criterion.required
        }
        verified = {
            evidence.criterion_id
            for evidence in state.criterion_evidence.values()
            if evidence.status == CriterionEvidenceStatus.VERIFIED
            and evidence.claim_id in state.criterion_claims
            and state.criterion_claims[evidence.claim_id].status
            == CriterionClaimStatus.VERIFIED
            and state.criterion_claims[evidence.claim_id].passed
            and evidence.owner_task_id in state.tasks
            and state.tasks[evidence.owner_task_id].active
            and state.tasks[evidence.owner_task_id].status == TaskStatus.COMPLETED
        }
        return required.issubset(verified)

    @staticmethod
    def _missing_goal_criteria(state: RunState) -> list[str]:
        required = {
            criterion.criterion_id
            for criterion in state.goal.success_criteria
            if criterion.required
        }
        verified = {
            evidence.criterion_id
            for evidence in state.criterion_evidence.values()
            if evidence.status == CriterionEvidenceStatus.VERIFIED
            and evidence.claim_id in state.criterion_claims
            and state.criterion_claims[evidence.claim_id].status
            == CriterionClaimStatus.VERIFIED
            and state.criterion_claims[evidence.claim_id].passed
            and evidence.owner_task_id in state.tasks
            and state.tasks[evidence.owner_task_id].active
            and state.tasks[evidence.owner_task_id].status == TaskStatus.COMPLETED
        }
        return sorted(required - verified)

    def _persist(self, state: RunState, event_type: str, event: Mapping[str, Any]) -> None:
        saved = self.store.save(
            state,
            expected_revision=state.revision,
            event_type=event_type,
            event=event,
        )
        state.revision = saved.revision
        state.updated_at = saved.updated_at


__all__ = ["ControllerResult", "LongHorizonController", "PlannerModel"]
