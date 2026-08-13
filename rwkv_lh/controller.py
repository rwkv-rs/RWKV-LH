"""Single-controller state machine for persistent Long-Horizon runs."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol

from rwkv_lh.harness import ActionHarness, ActionResult
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
    WitnessSelectionProposal,
)
from rwkv_lh.proof import CriterionProofEngine
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    CriterionEvidence,
    CriterionEvidenceStatus,
    CriterionClaim,
    CriterionClaimStatus,
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
    WitnessIntentState,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore, StateStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.token_budget import get_token_count
from rwkv_lh.validation import ValidationEngine
from rwkv_lh.witness import WitnessCatalogBuilder, WitnessCatalogError


class PlannerModel(Protocol):
    def plan(self, state: RunState, persist: PersistCallback) -> list: ...

    def propose_action(self, state, task, context, action_contract, persist): ...

    def prepare_witness_intents(
        self,
        state,
        task,
        context,
        persist,
        *,
        previous_intents=None,
        proof_feedback=None,
    ): ...

    def select_witness_sources(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result,
        validation_results,
        witness_catalog,
    ) -> WitnessSelectionProposal: ...

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
        self.witness_catalog = WitnessCatalogBuilder(self.proof_engine)
        self.max_transitions = max(1, int(max_transitions))

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
                    if graph.required_complete():
                        invalidated_claim_ids = self._revalidate_goal_proofs(state)
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
                    task = ready[0]
                    self._execute_task(state, graph, task.task_id)
                    transitions += 1
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
            remaining_budget=3,
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
                remaining_budget=3,
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
        missing = set(self._missing_goal_criteria(state))
        active_tasks = [
            task
            for task in sorted(
                state.tasks.values(),
                key=lambda item: (item.insertion_order, item.task_id),
            )
            if task.active
        ]
        selected_active_tasks = active_tasks[-24:]
        action_observations = sorted(
            (
                entry
                for entry in state.memory_index.values()
                if entry.kind == "action_result"
            ),
            key=lambda item: (item.created_at, item.memory_id),
        )
        selected_observations = action_observations[-32:]
        artifacts = sorted(
            state.artifacts.values(),
            key=lambda item: (item.created_at, item.artifact_id),
        )
        selected_artifacts = artifacts[-64:]
        criterion_evidence = sorted(
            state.criterion_evidence.values(),
            key=lambda item: (item.verified_at, item.evidence_id),
        )
        selected_evidence = criterion_evidence[-32:]
        workspace_manifest = self.harness.workspace_manifest(
            state.goal,
            max_entries=64,
        )
        workspace_observation = self.harness.workspace_observation_snapshot(
            state.goal,
        )
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
        capsule = {
            "schema_version": "long-horizon.goal-obligation-capsule.v1",
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
                    "required",
                    "dependencies",
                    "advances_criteria",
                    "satisfies_criteria",
                    "output_refs",
                ],
                "rows": [
                    [
                        task.task_id,
                        task.status.value,
                        task.required,
                        list(task.dependencies),
                        list(task.goal_criteria),
                        list(task.satisfies_criteria),
                        list(task.output_refs),
                    ]
                    for task in active_tasks
                ],
            },
            "active_tasks": [
                {
                    "task_id": task.task_id,
                    "title": task.title[:300],
                    "description": task.description[:1000],
                    "status": task.status.value,
                    "required": task.required,
                    "dependencies": list(task.dependencies),
                    "advances_criteria": list(task.goal_criteria),
                    "satisfies_criteria": list(task.satisfies_criteria),
                    "output_refs": list(task.output_refs),
                }
                for task in selected_active_tasks
            ],
            "action_observations": [
                {
                    "memory_id": entry.memory_id,
                    "task_id": entry.task_id,
                    "summary": entry.summary[:600],
                    "artifact_refs": list(entry.artifact_refs),
                    "evidence_refs": list(entry.evidence_refs),
                }
                for entry in selected_observations
            ],
            "artifacts": [
                {
                    "artifact_id": artifact.artifact_id,
                    "task_id": artifact.task_id,
                    "path": artifact.path,
                    "sha256": artifact.sha256,
                    "media_type": artifact.media_type,
                    "summary": artifact.summary[:500],
                }
                for artifact in selected_artifacts
            ],
            "criterion_evidence": [
                evidence.to_dict()
                for evidence in selected_evidence
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
                    "workspace_digest": previous_suppression.get(
                        "workspace_digest", ""
                    ),
                    "conflicts": previous_suppression.get("conflicts", []),
                    "entire_proposal_rejected": True,
                }
                if previous_suppression is not None
                else None
            ),
            "projection": {
                "active_task_count": len(active_tasks),
                "included_detailed_task_count": len(selected_active_tasks),
                "excluded_detailed_task_ids": [
                    task.task_id
                    for task in active_tasks[: -len(selected_active_tasks)]
                ]
                if len(active_tasks) > len(selected_active_tasks)
                else [],
                "action_observation_count": len(action_observations),
                "included_action_observation_count": len(selected_observations),
                "excluded_action_observation_ids": [
                    entry.memory_id
                    for entry in action_observations[: -len(selected_observations)]
                ]
                if len(action_observations) > len(selected_observations)
                else [],
                "artifact_count": len(artifacts),
                "included_artifact_count": len(selected_artifacts),
                "excluded_artifact_ids": [
                    artifact.artifact_id
                    for artifact in artifacts[: -len(selected_artifacts)]
                ]
                if len(artifacts) > len(selected_artifacts)
                else [],
                "criterion_evidence_count": len(criterion_evidence),
                "included_criterion_evidence_count": len(selected_evidence),
                "excluded_criterion_evidence_ids": [
                    evidence.evidence_id
                    for evidence in criterion_evidence[: -len(selected_evidence)]
                ]
                if len(criterion_evidence) > len(selected_evidence)
                else [],
                "excluded_workspace_paths": [],
                "workspace_entry_count": int(
                    workspace_manifest.get("entry_count", 0)
                ),
                "included_workspace_entry_count": len(
                    workspace_manifest.get("entries") or []
                ),
                "unchanged_failed_verifier_count": len(unchanged_failures),
                "included_unchanged_failed_verifier_count": min(
                    12, len(unchanged_failures)
                ),
                "task_text_truncated": False,
                "capsule_tokens": 0,
            },
        }
        projection = capsule["projection"]
        workspace_entries = capsule["workspace_manifest"].get("entries") or []

        def capsule_tokens() -> int:
            return get_token_count(
                json.dumps(
                    capsule,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )

        while capsule_tokens() > 5000:
            if len(workspace_entries) > 16:
                removed = workspace_entries.pop()
                projection["excluded_workspace_paths"].append(
                    str((removed or {}).get("path") or "")
                )
                capsule["workspace_manifest"]["truncated"] = True
                continue
            if len(capsule["artifacts"]) > 16:
                removed = capsule["artifacts"].pop(0)
                projection["excluded_artifact_ids"].append(
                    str(removed.get("artifact_id") or "")
                )
                continue
            if len(capsule["action_observations"]) > 16:
                removed = capsule["action_observations"].pop(0)
                projection["excluded_action_observation_ids"].append(
                    str(removed.get("memory_id") or "")
                )
                continue
            if len(capsule["criterion_evidence"]) > 8:
                removed = capsule["criterion_evidence"].pop(0)
                projection["excluded_criterion_evidence_ids"].append(
                    str(removed.get("evidence_id") or "")
                )
                continue
            if len(capsule["active_tasks"]) > 8:
                removed = capsule["active_tasks"].pop(0)
                projection["excluded_detailed_task_ids"].append(
                    str(removed.get("task_id") or "")
                )
                continue
            descriptions = [
                task
                for task in capsule["active_tasks"]
                if str(task.get("description") or "")
            ]
            if descriptions:
                for task in descriptions:
                    task["description"] = str(task["description"])[:160]
                projection["task_text_truncated"] = True
                if all(len(str(task.get("description") or "")) <= 160 for task in descriptions):
                    for task in descriptions:
                        task["description"] = ""
                continue
            titled = [
                task
                for task in capsule["active_tasks"]
                if len(str(task.get("title") or "")) > 80
            ]
            if titled:
                for task in titled:
                    task["title"] = str(task["title"])[:80]
                projection["task_text_truncated"] = True
                continue
            if len(capsule["action_observations"]) > 8:
                removed = capsule["action_observations"].pop(0)
                projection["excluded_action_observation_ids"].append(
                    str(removed.get("memory_id") or "")
                )
                continue
            if len(capsule["artifacts"]) > 8:
                removed = capsule["artifacts"].pop(0)
                projection["excluded_artifact_ids"].append(
                    str(removed.get("artifact_id") or "")
                )
                continue
            if len(workspace_entries) > 8:
                removed = workspace_entries.pop()
                projection["excluded_workspace_paths"].append(
                    str((removed or {}).get("path") or "")
                )
                capsule["workspace_manifest"]["truncated"] = True
                continue
            if capsule["action_observations"]:
                removed = capsule["action_observations"].pop(0)
                projection["excluded_action_observation_ids"].append(
                    str(removed.get("memory_id") or "")
                )
                continue
            if capsule["artifacts"]:
                removed = capsule["artifacts"].pop(0)
                projection["excluded_artifact_ids"].append(
                    str(removed.get("artifact_id") or "")
                )
                continue
            if capsule["criterion_evidence"]:
                removed = capsule["criterion_evidence"].pop(0)
                projection["excluded_criterion_evidence_ids"].append(
                    str(removed.get("evidence_id") or "")
                )
                continue
            if workspace_entries:
                removed = workspace_entries.pop()
                projection["excluded_workspace_paths"].append(
                    str((removed or {}).get("path") or "")
                )
                capsule["workspace_manifest"]["truncated"] = True
                continue
            if capsule["active_tasks"]:
                removed = capsule["active_tasks"].pop(0)
                projection["excluded_detailed_task_ids"].append(
                    str(removed.get("task_id") or "")
                )
                continue
            break
        def update_projection_counts() -> None:
            projection["included_action_observation_count"] = len(
                capsule["action_observations"]
            )
            projection["included_artifact_count"] = len(capsule["artifacts"])
            projection["included_criterion_evidence_count"] = len(
                capsule["criterion_evidence"]
            )
            projection["included_workspace_entry_count"] = len(
                workspace_entries
            )
            projection["included_detailed_task_count"] = len(
                capsule["active_tasks"]
            )

        def settle_capsule_token_count() -> int:
            for _ in range(8):
                measured = capsule_tokens()
                if projection["capsule_tokens"] == measured:
                    return measured
                projection["capsule_tokens"] = measured
            return capsule_tokens()

        update_projection_counts()
        actual_tokens = settle_capsule_token_count()
        while actual_tokens > 5000:
            if capsule["action_observations"]:
                removed = capsule["action_observations"].pop(0)
                projection["excluded_action_observation_ids"].append(
                    str(removed.get("memory_id") or "")
                )
            elif capsule["artifacts"]:
                removed = capsule["artifacts"].pop(0)
                projection["excluded_artifact_ids"].append(
                    str(removed.get("artifact_id") or "")
                )
            elif capsule["criterion_evidence"]:
                removed = capsule["criterion_evidence"].pop(0)
                projection["excluded_criterion_evidence_ids"].append(
                    str(removed.get("evidence_id") or "")
                )
            elif workspace_entries:
                removed = workspace_entries.pop()
                projection["excluded_workspace_paths"].append(
                    str((removed or {}).get("path") or "")
                )
                capsule["workspace_manifest"]["truncated"] = True
            elif capsule["active_tasks"]:
                removed = capsule["active_tasks"].pop(0)
                projection["excluded_detailed_task_ids"].append(
                    str(removed.get("task_id") or "")
                )
            else:
                raise RuntimeError(
                    "goal obligation capsule authoritative index exceeds 5000 tokens"
                )
            update_projection_counts()
            actual_tokens = settle_capsule_token_count()
        projection["capsule_tokens"] = actual_tokens
        if capsule_tokens() != actual_tokens:
            projection["capsule_tokens"] = settle_capsule_token_count()
        if capsule_tokens() > 5000:
            raise RuntimeError("goal obligation capsule exceeds 5000 tokens")
        return capsule

    @staticmethod
    def _goal_obligation_task_semantic_projection(task) -> dict[str, Any]:
        return {
            "title": task.title,
            "description": task.description,
            "advances_criteria": sorted(str(value) for value in task.goal_criteria),
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
                        "advances_criteria": list(task.goal_criteria),
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
    def _task_witness_intents(
        state: RunState,
        task,
    ) -> list[WitnessIntentState]:
        return sorted(
            (
                intent
                for intent in state.witness_intents.values()
                if intent.task_id == task.task_id
            ),
            key=lambda item: (item.criterion_id, item.intent_id),
        )

    def _ensure_task_witness_intents(
        self,
        state: RunState,
        graph: TaskGraph,
        task,
    ) -> bool:
        if not task.satisfies_criteria:
            return True
        existing = self._task_witness_intents(state, task)
        if existing:
            if (
                sorted(item.criterion_id for item in existing)
                == sorted(task.satisfies_criteria)
                and len({item.criterion_id for item in existing}) == len(existing)
            ):
                return True
            graph.transition(task.task_id, TaskStatus.BLOCKED)
            task.error = {
                "type": "WitnessIntentStateError",
                "phase": "witness_intent_precommit",
                "message": "persisted witness intents do not exactly cover task criteria",
            }
            state.status = RunStatus.BLOCKED
            state.active_task_id = None
            self._persist(
                state,
                "witness_intent_state_blocked",
                {"task_id": task.task_id, **task.error},
            )
            return False
        method = (
            getattr(self.model, "prepare_witness_intents", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            # Deterministic/legacy fixtures retain the pre-Round12 proof path.
            return True
        context = self.memory.build_task_validation(state, task)
        self._persist(
            state,
            "witness_intent_precommit_started",
            {
                "task_id": task.task_id,
                "criterion_ids": list(task.satisfies_criteria),
                "protocol": "rwkv_witness_intent_lifecycle.v1",
                "phase": "before_action",
            },
        )
        try:
            proposals = method(
                state,
                task,
                context,
                self._persist_callback(),
                previous_intents=None,
                proof_feedback=None,
            )
            if not isinstance(proposals, list) or not all(
                isinstance(item, WitnessIntentState) for item in proposals
            ):
                raise ModelProtocolError(
                    "prepare_witness_intents must return WitnessIntentState objects"
                )
            if (
                sorted(item.criterion_id for item in proposals)
                != sorted(task.satisfies_criteria)
                or len({item.criterion_id for item in proposals}) != len(proposals)
            ):
                raise ModelProtocolError(
                    "prepared witness intents do not exactly cover task criteria"
                )
        except ModelProtocolError as exc:
            graph.transition(task.task_id, TaskStatus.BLOCKED)
            task.error = {
                "type": "ModelProtocolError",
                "phase": "witness_intent_precommit",
                "message": str(exc)[:2000],
            }
            state.status = RunStatus.BLOCKED
            state.active_task_id = None
            self._persist(
                state,
                "model_protocol_blocked",
                {"task_id": task.task_id, **task.error},
            )
            return False
        for intent in proposals:
            state.witness_intents[intent.intent_id] = intent
        self._persist(
            state,
            "witness_intents_precommitted",
            {
                "task_id": task.task_id,
                "phase": "before_action",
                "criterion_ids": [item.criterion_id for item in proposals],
                "intents": [item.to_dict() for item in proposals],
            },
        )
        return True

    def _revise_task_witness_intents(
        self,
        state: RunState,
        task,
        previous: list[WitnessIntentState],
        feedback: list[dict[str, Any]],
    ) -> list[WitnessIntentState]:
        method = (
            getattr(self.model, "prepare_witness_intents", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            raise ModelProtocolError("witness-intent revision adapter is unavailable")
        context = self.memory.build_task_validation(state, task)
        revised = method(
            state,
            task,
            context,
            self._persist_callback(),
            previous_intents=previous,
            proof_feedback=feedback,
        )
        if not isinstance(revised, list) or not all(
            isinstance(item, WitnessIntentState) for item in revised
        ):
            raise ModelProtocolError(
                "witness-intent revision must return WitnessIntentState objects"
            )
        if (
            {item.intent_id for item in revised} != {item.intent_id for item in previous}
            or sorted(item.criterion_id for item in revised)
            != sorted(task.satisfies_criteria)
        ):
            raise ModelProtocolError(
                "revised witness intents must preserve IDs and criterion coverage"
            )
        previous_by_id = {item.intent_id: item for item in previous}
        for item in revised:
            prior = previous_by_id[item.intent_id]
            if item.revision != prior.revision + 1:
                raise ModelProtocolError(
                    "revised witness intent revision must advance exactly once"
                )
            # Audit history is controller-owned structural state. The RWKV
            # proposal changes only its explicit semantic intent fields.
            item.binding_history = list(prior.binding_history)
            item.current_binding = {}
            item.catalog_digest = ""
            item.status = "prepared"
            item.created_at = prior.created_at
            item.updated_at = utc_now()
        before = [item.to_dict() for item in previous]
        for item in revised:
            state.witness_intents[item.intent_id] = item
        self._persist(
            state,
            "witness_intents_revised",
            {
                "task_id": task.task_id,
                "before": before,
                "after": [item.to_dict() for item in revised],
                "proof_feedback": feedback,
                "action_reexecuted": False,
            },
        )
        return self._task_witness_intents(state, task)

    def _build_task_witness_catalog(
        self,
        state: RunState,
        task,
        attempt: Attempt,
        intents: list[WitnessIntentState],
        *,
        allow_intent_revision_change: bool,
    ) -> dict[str, Any]:
        catalog = self.witness_catalog.build(state, task, attempt, intents)
        digest = str(catalog.get("catalog_digest") or "")
        previous_digest = attempt.witness_catalog_digest
        if (
            previous_digest
            and previous_digest != digest
            and not allow_intent_revision_change
        ):
            raise WitnessCatalogError(
                "witness catalog digest changed for the same persisted attempt"
            )
        attempt.witness_catalog_digest = digest
        for intent in intents:
            intent.catalog_digest = digest
            intent.updated_at = utc_now()
        self._persist(
            state,
            (
                "witness_catalog_rebuilt_after_intent_revision"
                if allow_intent_revision_change and previous_digest
                else "witness_catalog_prepared"
            ),
            {
                "task_id": task.task_id,
                "attempt_id": attempt.attempt_id,
                "previous_catalog_digest": previous_digest,
                "catalog": catalog,
                "protocol": "rwkv_witness_intent_lifecycle.v1",
                "criterion_text_used_for_catalog": False,
                "reference_or_acceptance_used": False,
            },
        )
        return catalog

    def _select_post_action_witness_intents(
        self,
        state: RunState,
        task,
        attempt: Attempt,
        action_result: ActionResult,
        validation_results: list[ValidationResult],
    ) -> tuple[
        WitnessSelectionProposal,
        dict[str, Any] | None,
    ]:
        method = (
            getattr(self.model, "select_witness_sources", None)
            if self.model is not None
            else None
        )
        if not callable(method):
            raise ModelProtocolError("post-action witness selection adapter is unavailable")
        discovery_catalog = self.witness_catalog.build(state, task, attempt, [])
        self._persist(
            state,
            "witness_source_catalog_prepared",
            {
                "task_id": task.task_id,
                "attempt_id": attempt.attempt_id,
                "criterion_ids": list(task.satisfies_criteria),
                "catalog": discovery_catalog,
                "protocol": "post_action_catalog_bound_witness.v2",
                "selection_contract": "rwkv_committed_progressive_witness_disclosure.v6",
                "phase": "after_action",
                "criterion_text_used_for_catalog": False,
                "reference_or_acceptance_used": False,
            },
        )
        context = self.memory.build_task_validation(state, task)
        self._persist(
            state,
            "witness_selection_started",
            {
                "task_id": task.task_id,
                "attempt_id": attempt.attempt_id,
                "criterion_ids": list(task.satisfies_criteria),
                "discovery_catalog_digest": discovery_catalog.get(
                    "catalog_digest", ""
                ),
                "protocol": "post_action_catalog_bound_witness.v2",
                "selection_contract": "rwkv_committed_progressive_witness_disclosure.v6",
            },
        )
        proposal = method(
            state,
            task,
            context,
            self._persist_callback(),
            action_result=action_result.to_dict(),
            validation_results=[vars(item) for item in validation_results],
            witness_catalog=discovery_catalog,
        )
        if not isinstance(proposal, WitnessSelectionProposal):
            raise ModelProtocolError(
                "select_witness_sources must return WitnessSelectionProposal"
            )
        if proposal.decision == "replan":
            if proposal.intents or proposal.source_selections:
                raise ModelProtocolError(
                    "replan witness selection must not compile intents or sources"
                )
            self._persist(
                state,
                "witness_selection_replan_requested",
                {
                    "task_id": task.task_id,
                    "attempt_id": attempt.attempt_id,
                    "reason": proposal.reason,
                    "rwkv_reason_provided": proposal.reason_provided,
                    "selection_contract": "rwkv_committed_progressive_witness_disclosure.v6",
                    "discovery_catalog_digest": discovery_catalog.get(
                        "catalog_digest", ""
                    ),
                },
            )
            return proposal, None
        if proposal.decision != "pass":
            raise ModelProtocolError("post-action witness decision must be pass or replan")
        if (
            sorted(item.criterion_id for item in proposal.intents)
            != sorted(task.satisfies_criteria)
            or len({item.criterion_id for item in proposal.intents})
            != len(proposal.intents)
        ):
            raise ModelProtocolError(
                "post-action witness intents must exactly cover task criteria"
            )

        final_catalog = self._build_task_witness_catalog(
            state,
            task,
            attempt,
            proposal.intents,
            allow_intent_revision_change=False,
        )
        final_sources = {
            str(item.get("source_handle_id") or ""): item
            for item in final_catalog.get("sources") or []
            if isinstance(item, Mapping)
        }
        for intent, selection in zip(
            proposal.intents, proposal.source_selections, strict=True
        ):
            if selection.get("intent_id") != intent.intent_id:
                raise ModelProtocolError(
                    "compiled witness source order does not match intents"
                )
            actual_id = str(selection.get("actual_source_handle_id") or "")
            actual = final_sources.get(actual_id)
            if actual is None:
                raise WitnessCatalogError(
                    "RWKV-selected actual source disappeared from final catalog"
                )
            expected_id = str(selection.get("expected_source_handle_id") or "")
            if intent.expected_source_kind == "goal_literal":
                matches = [
                    source
                    for source in final_sources.values()
                    if source.get("source_kind") == "goal_literal"
                    and source.get("intent_id") == intent.intent_id
                ]
                if len(matches) != 1:
                    raise WitnessCatalogError(
                        "RWKV-selected Goal literal did not compile to one source"
                    )
                expected_id = str(matches[0].get("source_handle_id") or "")
                selection["expected_source_handle_id"] = expected_id
            if expected_id not in final_sources:
                raise WitnessCatalogError(
                    "RWKV-selected expected source disappeared from final catalog"
                )
            intent.source_selection = dict(selection)
            intent.selection_reason = proposal.reason
            intent.catalog_digest = str(final_catalog.get("catalog_digest") or "")
            state.witness_intents[intent.intent_id] = intent
        self._persist(
            state,
            "witness_selection_compiled",
            {
                "task_id": task.task_id,
                "attempt_id": attempt.attempt_id,
                "protocol": "post_action_catalog_bound_witness.v2",
                "selection_contract": "rwkv_committed_progressive_witness_disclosure.v6",
                "reason": proposal.reason,
                "rwkv_reason_provided": proposal.reason_provided,
                "rwkv_selection_notes": proposal.selection_notes,
                "discovery_catalog_digest": discovery_catalog.get(
                    "catalog_digest", ""
                ),
                "final_catalog_digest": final_catalog.get("catalog_digest", ""),
                "intents": [item.to_dict() for item in proposal.intents],
                "source_selections": [
                    dict(item) for item in proposal.source_selections
                ],
                "controller_semantic_fields_generated": False,
                "reference_or_acceptance_used": False,
            },
        )
        return proposal, final_catalog

    def _execute_task(self, state: RunState, graph: TaskGraph, task_id: str) -> None:
        task = state.tasks[task_id]
        if not task.action.action_type or task.action.action_type == "model_action":
            if self.model is None:
                raise RuntimeError(f"task {task_id} requires a model-proposed action")
            context = self.memory.build(state, task)
            self._persist(
                state,
                "execution_capsule_prepared",
                {
                    "task_id": task_id,
                    "request_scope": "action_commit",
                    "capsule": context.to_dict(),
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
                graph.transition(task_id, TaskStatus.BLOCKED)
                task.error = {
                    "type": "ModelProtocolError",
                    "phase": "action_materialization",
                    "message": str(exc)[:2000],
                }
                state.status = RunStatus.BLOCKED
                state.active_task_id = None
                self._persist(
                    state,
                    "model_protocol_blocked",
                    {"task_id": task_id, **task.error},
                )
                return
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
            started_at=utc_now(),
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
            },
        )
        result = self.harness.execute(task.action, state.goal)
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
                "error": result.error,
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
            self._commit_criterion_evidence(
                state,
                task,
                attempt,
                validation_results,
            )
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
            context = self.memory.build(state, task)
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
        context = self.memory.build(state, task)
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
        if not replacement_task.goal_criteria:
            replacement_task.goal_criteria = list(failed_task.goal_criteria)
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
        graph = TaskGraph(state.tasks)
        if task_committed:
            attempt.status = AttemptStatus.SUCCEEDED
            attempt.ended_at = utc_now()
            attempt.validation_results = validation_results
            graph.transition(task.task_id, TaskStatus.COMPLETED)
            self._commit_criterion_evidence(
                state,
                task,
                attempt,
                validation_results,
            )
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
        state.attempts[attempt_id].artifact_refs = artifact_refs
        memory_id = f"M-{attempt_id}"
        output = str(result.output or "")
        state.memory_index[memory_id] = MemoryEntry(
            memory_id=memory_id,
            kind="action_result",
            task_id=task_id,
            summary=(output[:1000] or json.dumps(result.error or {}, ensure_ascii=False)[:1000]),
            content=output[:20_000],
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
                        "goal_criteria": task.goal_criteria,
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
        effect_passed = validation.required_passed
        task_committed = effect_passed
        if effect_passed:
            commit_result = self._task_postcondition_check(
                state,
                task,
                action_result,
                results,
            )
            if commit_result is not None:
                results.append(commit_result)
                task_committed = commit_result.passed
        assertion_was_requested = any(
            item.kind == "model_cross_check"
            and isinstance(item.evidence, Mapping)
            and item.evidence.get("criterion_assertion_evaluated") is True
            for item in results
        )
        if (
            task_committed
            and task.satisfies_criteria
            and not assertion_was_requested
        ):
            semantic_result = self._criterion_semantic_check(
                state,
                task,
                action_result,
                results,
            )
            if semantic_result is not None:
                results.append(semantic_result)
        subject_task_id = self._validation_subject_task_id(state, task)
        failed_required = [
            item for item in results if item.required and not item.passed
        ]
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

    def _criterion_semantic_check(
        self,
        state: RunState,
        task,
        action_result: ActionResult,
        validation_results: list[ValidationResult],
    ) -> ValidationResult | None:
        method = (
            getattr(self.model, "cross_validate", None)
            if self.model is not None
            else None
        )
        if not callable(method) or not task.satisfies_criteria:
            return None
        return self._cross_check_with_observation_gate(
            state,
            task,
            action_result,
            validation_results,
            kind="criterion_cross_check",
            required=False,
            parameters={},
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
                    "criterion_assertion_evaluated": bool(
                        task.satisfies_criteria
                    ),
                    "proof_passed": (
                        False if task.satisfies_criteria else None
                    ),
                    "criterion_claim_ids": [],
                    "original_task_id": cached.get("task_id", ""),
                    "original_attempt_id": cached.get("attempt_id", ""),
                    "original_validation_ref": cached.get("validation_ref", ""),
                },
            )

        method_name = (
            "commit_task_postcondition"
            if kind == "task_postcondition_cross_check"
            else "cross_validate"
        )
        method = (
            getattr(self.model, method_name, None)
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
        assertion_evaluated = bool(task.satisfies_criteria) and kind in {
            "model_cross_check",
            "criterion_cross_check",
        }
        witness_intents = (
            self._task_witness_intents(state, task) if assertion_evaluated else []
        )
        attempt = state.attempts.get(attempt_id)
        witness_catalog: dict[str, Any] | None = None
        witness_source_selections: list[dict[str, Any]] | None = None
        witness_semantic_reason = ""
        selection_method = (
            getattr(self.model, "select_witness_sources", None)
            if self.model is not None
            else None
        )
        if assertion_evaluated and attempt is not None and not witness_intents and callable(selection_method):
            try:
                proposal, witness_catalog = self._select_post_action_witness_intents(
                    state,
                    task,
                    attempt,
                    action_result,
                    validation_results,
                )
            except (ModelProtocolError, WitnessCatalogError) as exc:
                self._persist(
                    state,
                    "witness_selection_blocked",
                    {
                        "task_id": task.task_id,
                        "attempt_id": attempt_id,
                        "error": str(exc),
                        "protocol": "post_action_catalog_bound_witness.v2",
                        "selection_contract": "rwkv_committed_progressive_witness_disclosure.v6",
                    },
                )
                return ValidationResult(
                    kind=kind,
                    passed=False,
                    required=required,
                    message=f"{type(exc).__name__}: {exc}",
                    evidence={
                        "owner": "rwkv",
                        "scope": "task_local",
                        "protocol_valid": False,
                        "decision": "replan",
                        "decision_source": "rwkv_contract_error",
                        "criterion_assertion_evaluated": True,
                        "proof_passed": False,
                    },
                )
            if proposal.decision == "replan":
                return ValidationResult(
                    kind=kind,
                    passed=False,
                    required=required,
                    message=proposal.reason,
                    evidence={
                        "owner": "rwkv",
                        "scope": "task_local",
                        "protocol_valid": True,
                        "decision": "replan",
                        "decision_source": "rwkv_current",
                        "criterion_assertion_evaluated": True,
                        "criterion_assertion_intents": [],
                        "proof_passed": False,
                    },
                )
            witness_intents = list(proposal.intents)
            witness_source_selections = [
                dict(item) for item in proposal.source_selections
            ]
            witness_semantic_reason = proposal.reason
        elif assertion_evaluated and attempt is not None and not witness_intents:
            legacy_method = (
                getattr(self.model, "prepare_witness_intents", None)
                if self.model is not None
                else None
            )
            if callable(legacy_method):
                try:
                    context = self.memory.build_task_validation(state, task)
                    proposals = legacy_method(
                        state,
                        task,
                        context,
                        self._persist_callback(),
                        previous_intents=None,
                        proof_feedback=None,
                    )
                    if not isinstance(proposals, list) or not all(
                        isinstance(item, WitnessIntentState) for item in proposals
                    ):
                        raise ModelProtocolError(
                            "prepare_witness_intents must return WitnessIntentState objects"
                        )
                    if (
                        sorted(item.criterion_id for item in proposals)
                        != sorted(task.satisfies_criteria)
                        or len({item.criterion_id for item in proposals})
                        != len(proposals)
                    ):
                        raise ModelProtocolError(
                            "post-action legacy witness intents do not exactly cover task criteria"
                        )
                    for intent in proposals:
                        state.witness_intents[intent.intent_id] = intent
                    self._persist(
                        state,
                        "legacy_witness_intents_prepared_after_action",
                        {
                            "task_id": task.task_id,
                            "attempt_id": attempt_id,
                            "intents": [item.to_dict() for item in proposals],
                        },
                    )
                    witness_intents = list(proposals)
                except ModelProtocolError as exc:
                    return ValidationResult(
                        kind=kind,
                        passed=False,
                        required=required,
                        message=f"ModelProtocolError: {exc}",
                        evidence={
                            "owner": "rwkv",
                            "scope": "task_local",
                            "protocol_valid": False,
                            "decision": "replan",
                            "criterion_assertion_evaluated": True,
                            "proof_passed": False,
                        },
                    )
        if witness_intents and witness_catalog is None:
            if attempt is None:
                return ValidationResult(
                    kind=kind,
                    passed=False,
                    required=required,
                    message="witness catalog rejected: current attempt is missing",
                    evidence={
                        "owner": "runtime",
                        "scope": "task_local",
                        "protocol_valid": False,
                        "criterion_assertion_evaluated": True,
                        "proof_passed": False,
                    },
                )
            if all(item.source_selection for item in witness_intents):
                witness_source_selections = [
                    dict(item.source_selection) for item in witness_intents
                ]
                witness_semantic_reason = next(
                    (
                        item.selection_reason
                        for item in witness_intents
                        if item.selection_reason
                    ),
                    "persisted post-action witness selection",
                )
            try:
                witness_catalog = self._build_task_witness_catalog(
                    state,
                    task,
                    attempt,
                    witness_intents,
                    allow_intent_revision_change=False,
                )
            except WitnessCatalogError as exc:
                self._persist(
                    state,
                    "witness_catalog_blocked",
                    {
                        "task_id": task.task_id,
                        "attempt_id": attempt_id,
                        "error": str(exc),
                    },
                )
                return ValidationResult(
                    kind=kind,
                    passed=False,
                    required=required,
                    message=f"WitnessCatalogError: {exc}",
                    evidence={
                        "owner": "runtime",
                        "scope": "task_local",
                        "protocol_valid": False,
                        "criterion_assertion_evaluated": True,
                        "proof_passed": False,
                    },
                )

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
        decision = CrossValidationDecision(False, "", [])
        proof_passed: bool | None = None
        proof_message = ""
        claim_ids: list[str] = []
        binding_feedback: list[dict[str, Any]] = []
        witness_rounds = 3 if witness_catalog is not None else 1
        completed_witness_rounds = 0
        for witness_round in range(1, witness_rounds + 1):
            completed_witness_rounds = witness_round
            try:
                call_kwargs: dict[str, Any] = {
                    "action_result": action_result.to_dict(),
                    "validation_results": [vars(item) for item in validation_results],
                }
                if witness_catalog is not None:
                    call_kwargs.update(
                        {
                            "witness_intents": witness_intents,
                            "witness_catalog": witness_catalog,
                            "binding_feedback": binding_feedback,
                        }
                    )
                    if witness_source_selections is not None:
                        call_kwargs.update(
                            {
                                "witness_source_selections": witness_source_selections,
                                "witness_semantic_reason": witness_semantic_reason,
                            }
                        )
                if kind == "task_postcondition_cross_check":
                    raw_decision = method(
                        state,
                        task,
                        context,
                        self._persist_callback(),
                        action_result=action_result.to_dict(),
                        validation_results=[
                            vars(item) for item in validation_results
                        ],
                    )
                else:
                    raw_decision = method(
                        state,
                        task,
                        context,
                        self._persist_callback(),
                        **call_kwargs,
                    )
                decision = self._normalize_cross_validation_decision(raw_decision)
            except ModelProtocolError as exc:
                decision = CrossValidationDecision(
                    False,
                    f"ModelProtocolError: {exc}",
                    [],
                )
                protocol_valid = False
                break

            claim_ids = []
            proof_passed = None
            proof_message = ""
            if assertion_evaluated:
                claim_ids, proof_passed, proof_message = self._evaluate_criterion_assertions(
                    state,
                    task,
                    decision,
                    witness_round=(witness_round if witness_catalog is not None else 0),
                )

            if witness_catalog is None:
                break
            binding_by_intent = {
                str(item.get("intent_id") or ""): dict(item)
                for item in decision.witness_bindings
            }
            claims = [
                state.criterion_claims[claim_id]
                for claim_id in claim_ids
                if claim_id in state.criterion_claims
            ]
            for intent in witness_intents:
                claim = next(
                    (
                        item
                        for item in claims
                        if item.criterion_id == intent.criterion_id
                    ),
                    None,
                )
                binding = binding_by_intent.get(intent.intent_id, {})
                record = {
                    "round": witness_round,
                    "catalog_digest": witness_catalog.get("catalog_digest", ""),
                    "rwkv_decision": decision.witness_decision,
                    "rwkv_reason": decision.reason,
                    "source_selection": next(
                        (
                            dict(item)
                            for item in decision.witness_source_selections
                            if str(item.get("intent_id") or "") == intent.intent_id
                        ),
                        {},
                    ),
                    "binding": binding,
                    "claim_id": claim.claim_id if claim is not None else "",
                    "proof_status": claim.status.value if claim is not None else "not_evaluated",
                    "proof_passed": bool(claim is not None and claim.passed),
                    "proof_reason": claim.reason if claim is not None else proof_message,
                    "action_reexecuted": False,
                }
                intent.binding_history.append(record)
                intent.current_binding = binding
                intent.updated_at = utc_now()
                if claim is not None and claim.passed:
                    intent.status = "verified"
                elif decision.witness_decision == "replan":
                    intent.status = "replan_requested"
                elif decision.witness_decision == "revise_intent":
                    intent.status = "intent_revision_requested"
                else:
                    intent.status = "binding_rejected"
            self._persist(
                state,
                "witness_binding_evaluated",
                {
                    "task_id": task.task_id,
                    "attempt_id": attempt_id,
                    "round": witness_round,
                    "catalog_digest": witness_catalog.get("catalog_digest", ""),
                    "rwkv_decision": decision.witness_decision,
                    "rwkv_reason": decision.reason,
                    "source_selections": list(
                        decision.witness_source_selections
                    ),
                    "bindings": list(decision.witness_bindings),
                    "expanded_assertions": list(decision.criterion_assertions),
                    "claim_ids": claim_ids,
                    "proof_passed": proof_passed,
                    "proof_message": proof_message,
                    "action_reexecuted": False,
                },
            )
            if decision.witness_decision == "replan":
                break
            if decision.witness_decision == "revise_intent":
                if witness_round >= witness_rounds:
                    break
                binding_feedback = [
                    {
                        "type": "rwkv_requested_intent_revision",
                        "reason": decision.reason,
                    }
                ]
                try:
                    witness_intents = self._revise_task_witness_intents(
                        state,
                        task,
                        witness_intents,
                        binding_feedback,
                    )
                    witness_catalog = self._build_task_witness_catalog(
                        state,
                        task,
                        attempt,
                        witness_intents,
                        allow_intent_revision_change=True,
                    )
                except (ModelProtocolError, WitnessCatalogError) as exc:
                    decision = CrossValidationDecision(
                        False,
                        f"{type(exc).__name__}: {exc}",
                        [],
                        witness_decision="replan",
                    )
                    protocol_valid = False
                    break
                continue
            if decision.passed and proof_passed is False and witness_round < witness_rounds:
                binding_feedback = [
                    {
                        "claim_id": claim.claim_id,
                        "criterion_id": claim.criterion_id,
                        "status": claim.status.value,
                        "reason": claim.reason,
                        "raw_claim": claim.raw_claim,
                    }
                    for claim in claims
                    if not claim.passed
                ]
                if decision.assertion_binding_error:
                    binding_feedback.append(
                        {
                            "type": "binding_protocol_error",
                            "reason": decision.assertion_binding_error,
                        }
                    )
                self._persist(
                    state,
                    "witness_binding_revision_requested",
                    {
                        "task_id": task.task_id,
                        "attempt_id": attempt_id,
                        "completed_round": witness_round,
                        "remaining_rounds": witness_rounds - witness_round,
                        "proof_feedback": binding_feedback,
                        "action_reexecuted": False,
                    },
                )
                continue
            break

        passed = bool(decision.passed)
        if assertion_evaluated:
            passed = passed and proof_passed is True
        message = str(decision.reason)
        if decision.passed and proof_message:
            message = f"{message}; {proof_message}" if message else proof_message
        return ValidationResult(
            kind=kind,
            passed=passed,
            required=required,
            message=message,
            evidence={
                "owner": "rwkv",
                "scope": "task_local",
                "goal_digest": state.goal.digest,
                "criterion_ids": list(task.satisfies_criteria),
                "observation_digest": digest,
                "workspace_digest": observation.get("workspace_digest", ""),
                "observation_cacheable": cacheable,
                "protocol_valid": protocol_valid,
                "decision": (
                    decision.witness_decision
                    or ("pass" if decision.passed else "replan")
                ),
                "decision_source": "rwkv_current",
                "criterion_assertion_evaluated": assertion_evaluated,
                "criterion_assertion_intents": list(
                    decision.criterion_assertion_intents
                ),
                "assertion_binding_protocol_valid": (
                    decision.assertion_binding_protocol_valid
                ),
                "assertion_binding_error": decision.assertion_binding_error,
                "proof_passed": proof_passed,
                "criterion_claim_ids": claim_ids,
                "witness_catalog_digest": (
                    witness_catalog.get("catalog_digest", "")
                    if witness_catalog is not None
                    else ""
                ),
                "witness_bindings": list(decision.witness_bindings),
                "witness_source_selections": list(
                    decision.witness_source_selections
                ),
                "witness_local_rounds": completed_witness_rounds,
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

    def _evaluate_criterion_assertions(
        self,
        state: RunState,
        task,
        decision: CrossValidationDecision,
        *,
        witness_round: int = 0,
    ) -> tuple[list[str], bool, str]:
        attempt_id = task.attempt_ids[-1] if task.attempt_ids else ""
        attempt = state.attempts.get(attempt_id)
        declared = list(task.satisfies_criteria)
        evaluated: list[CriterionClaim] = []
        if attempt is None:
            return [], False, "criterion proof rejected: current attempt is missing"
        for index, raw_claim in enumerate(decision.criterion_assertions, start=1):
            claim_id = (
                f"CC-{attempt_id}-W{witness_round}-{index}"
                if witness_round > 0
                else f"CC-{attempt_id}-{index}"
            )
            if decision.passed:
                actual_raw = raw_claim.get("actual")
                operator_protocol = (
                    isinstance(actual_raw, Mapping)
                    and "read_op" in actual_raw
                )
                evaluator = (
                    self.proof_engine.evaluate_operator_assertion
                    if operator_protocol
                    else self.proof_engine.evaluate_linear_assertion
                )
                claim = evaluator(
                    state,
                    task,
                    attempt,
                    raw_claim,
                    claim_id=claim_id,
                    rwkv_reason=decision.reason,
                )
            else:
                normalization_trace: list[dict[str, Any]] = []
                actual_input = raw_claim.get("actual")
                operator_protocol = (
                    isinstance(actual_input, Mapping)
                    and "read_op" in actual_input
                )
                try:
                    normalizer = (
                        self.proof_engine.normalize_operator_assertion
                        if operator_protocol
                        else self.proof_engine.normalize_linear_assertion
                    )
                    normalized, normalization_trace = normalizer(raw_claim)
                except (TypeError, ValueError):
                    normalized = dict(raw_claim)
                actual_raw = normalized.get("actual")
                if not isinstance(actual_raw, Mapping):
                    actual_raw = {}
                expected_raw = normalized.get("expected")
                if not isinstance(expected_raw, Mapping):
                    expected_raw = {}
                claim = CriterionClaim(
                    claim_id=claim_id,
                    criterion_id=str(raw_claim.get("criterion_id") or ""),
                    subject_task_id=str(raw_claim.get("subject_task_id") or ""),
                    producer_task_id=str(raw_claim.get("producer_task_id") or ""),
                    attempt_id=attempt_id,
                    comparison=str(raw_claim.get("comparison") or ""),
                    actual=ProofExpr.from_dict(actual_raw),
                    expected=ProofExpr.from_dict(expected_raw),
                    status=CriterionClaimStatus.REJECTED,
                    passed=False,
                    reason="RWKV decision was replan; assertion was not executed",
                    rwkv_reason=decision.reason,
                    raw_claim=dict(raw_claim),
                    claim_protocol=(
                        "read_operator_assertion.v1"
                        if operator_protocol
                        else "linear_typed_assertion.v1"
                    ),
                    normalization_trace=normalization_trace,
                )
            state.criterion_claims[claim_id] = claim
            evaluated.append(claim)

        claim_ids = [claim.claim_id for claim in evaluated]
        declared_counts = {criterion_id: declared.count(criterion_id) for criterion_id in set(declared)}
        claim_counts = {
            criterion_id: sum(
                1 for claim in evaluated if claim.criterion_id == criterion_id
            )
            for criterion_id in set([*declared, *(claim.criterion_id for claim in evaluated)])
        }
        exact_coverage = (
            len(evaluated) == len(declared)
            and declared_counts == claim_counts
            and all(count == 1 for count in declared_counts.values())
        )
        proof_passed = (
            decision.passed
            and exact_coverage
            and all(
                claim.status == CriterionClaimStatus.VERIFIED and claim.passed
                for claim in evaluated
            )
        )
        self._persist(
            state,
            "criterion_assertions_evaluated",
            {
                "task_id": task.task_id,
                "attempt_id": attempt_id,
                "rwkv_decision": "pass" if decision.passed else "replan",
                "criterion_assertion_intents": list(
                    decision.criterion_assertion_intents
                ),
                "assertion_binding_protocol_valid": (
                    decision.assertion_binding_protocol_valid
                ),
                "assertion_binding_error": decision.assertion_binding_error,
                "witness_round": witness_round,
                "witness_decision": decision.witness_decision,
                "witness_bindings": list(decision.witness_bindings),
                "witness_source_selections": list(
                    decision.witness_source_selections
                ),
                "declared_criterion_ids": declared,
                "exact_coverage": exact_coverage,
                "proof_passed": proof_passed,
                "assertion_protocol": (
                    "read_operator_assertion.v1"
                    if decision.criterion_assertion_intents
                    or any(
                        claim.claim_protocol == "read_operator_assertion.v1"
                        for claim in evaluated
                    )
                    else "linear_typed_assertion.v1"
                ),
                "claims": [claim.to_dict() for claim in evaluated],
            },
        )
        if not decision.passed:
            summary = "criterion assertion not executed because RWKV chose replan"
        elif not exact_coverage:
            summary = (
                "criterion assertion rejected: RWKV must emit exactly one assertion "
                "for each declared criterion"
            )
        elif proof_passed:
            summary = "all RWKV-proposed criterion assertions passed exact evaluation"
        else:
            reasons = [
                claim.reason
                for claim in evaluated
                if claim.status != CriterionClaimStatus.VERIFIED
            ]
            summary = "criterion assertion rejected: " + " | ".join(reasons)
        return claim_ids, proof_passed, summary

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
            dict.fromkeys([*task.goal_criteria, *task.satisfies_criteria])
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
                "goal_criteria": list(task.goal_criteria),
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
                    if claim.claim_protocol == "read_operator_assertion.v1":
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
    def _commit_criterion_evidence(
        state: RunState,
        task,
        attempt: Attempt,
        validation_results: list[ValidationResult],
    ) -> None:
        if not task.satisfies_criteria:
            return
        validation_refs = [
            f"{attempt.attempt_id}:V{index}"
            for index, result in enumerate(validation_results, start=1)
            if result.passed
        ]
        proof_results = [
            result
            for result in validation_results
            if result.kind in {"model_cross_check", "criterion_cross_check"}
            and result.passed
            and isinstance(result.evidence, Mapping)
            and result.evidence.get("proof_passed") is True
        ]
        claim_ids = [
            str(claim_id)
            for result in proof_results
            for claim_id in result.evidence.get("criterion_claim_ids") or []
        ]
        for claim_id in claim_ids:
            claim = state.criterion_claims.get(claim_id)
            if (
                claim is None
                or claim.status != CriterionClaimStatus.VERIFIED
                or not claim.passed
                or claim.criterion_id not in task.satisfies_criteria
            ):
                continue
            criterion_id = claim.criterion_id
            evidence_id = f"CE-{criterion_id}-{attempt.attempt_id}"
            state.criterion_evidence[evidence_id] = CriterionEvidence(
                evidence_id=evidence_id,
                criterion_id=criterion_id,
                status=CriterionEvidenceStatus.VERIFIED,
                owner_task_id=claim.producer_task_id,
                attempt_id=attempt.attempt_id,
                validation_refs=validation_refs,
                artifact_refs=list(
                    dict.fromkeys(
                        [
                            *attempt.artifact_refs,
                            *[
                                ref.source_id
                                for ref in claim.proof_refs
                                if ref.source_type == "dependency_artifact"
                            ],
                        ]
                    )
                ),
                state_ref=None,
                claim_id=claim.claim_id,
                proof_refs=[ref.evidence_ref_id for ref in claim.proof_refs],
                observation_digest=claim.observation_digest,
            )

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
