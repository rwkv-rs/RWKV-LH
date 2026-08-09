"""Single-controller state machine for persistent Long-Horizon runs."""

from __future__ import annotations

import json
import hashlib
import os
import tempfile
from dataclasses import dataclass
from typing import Any, Mapping, Protocol

from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import LongHorizonModel, PersistCallback, ReplanProposal
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    MemoryEntry,
    RunState,
    RunStatus,
    TaskStatus,
    ValidationResult,
    ValidationSpec,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore, StateStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.validation import ValidationEngine


class PlannerModel(Protocol):
    def plan(self, state: RunState, persist: PersistCallback) -> list: ...

    def propose_action(self, state, task, context, action_contract, persist): ...

    def replan(self, state, failed_task, context, persist, *, same_failure_count: int) -> ReplanProposal: ...

    def final_answer(self, state: RunState, context: str, persist: PersistCallback) -> str: ...


@dataclass
class ControllerResult:
    state: RunState
    final_output: str
    transitions: int


class LongHorizonController:
    def __init__(
        self,
        store: StateStore | None = None,
        *,
        model: PlannerModel | None = None,
        harness: ActionHarness | None = None,
        validator: ValidationEngine | None = None,
        memory: WorkingMemoryBuilder | None = None,
        max_transitions: int = 500,
    ):
        self.store = store or LongHorizonStore()
        self.model = model
        self.harness = harness or ActionHarness()
        self.validator = validator or ValidationEngine(self.harness)
        self.memory = memory or WorkingMemoryBuilder()
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
                while transitions < self.max_transitions:
                    graph = TaskGraph(state.tasks)
                    if graph.required_complete():
                        output = self._complete_run(state)
                        return ControllerResult(state, output, transitions)
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
        tasks = self.model.plan(state, self._persist_callback())
        graph = TaskGraph()
        graph.add_tasks(tasks)
        state.tasks = graph.tasks
        state.plan_generation += 1
        state.status = RunStatus.RUNNING
        self._persist(
            state,
            "plan_saved",
            {"task_ids": list(state.tasks), "plan_generation": state.plan_generation},
        )

    def _execute_task(self, state: RunState, graph: TaskGraph, task_id: str) -> None:
        task = state.tasks[task_id]
        if not task.action.action_type or task.action.action_type == "model_action":
            if self.model is None:
                raise RuntimeError(f"task {task_id} requires a model-proposed action")
            context = self.memory.build(state, task, action_contract=self.harness.action_contract())
            task.action = self.model.propose_action(
                state,
                task,
                context,
                self.harness.action_contract(),
                self._persist_callback(),
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
        self._record_artifacts_and_memory(state, task_id, attempt_id, result)
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
        state.status = RunStatus.VALIDATING
        validation = self.validator.validate(
            task,
            result,
            state.goal,
            state,
            cross_check=self._model_cross_check(state),
        )
        attempt.validation_results = list(validation.results)
        if validation.required_passed:
            attempt.status = AttemptStatus.SUCCEEDED
            attempt.ended_at = utc_now()
            graph.transition(task_id, TaskStatus.COMPLETED)
            task.error = None
            state.active_task_id = None
            state.status = RunStatus.RUNNING
            self._persist(
                state,
                "task_completed",
                {
                    "task_id": task_id,
                    "attempt_id": attempt_id,
                    "validation": [vars(item) for item in validation.results],
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
            "results": [vars(item) for item in validation.results],
        }
        state.errors.append({"task_id": task_id, **task.error, "at": utc_now()})
        self._persist(
            state,
            "task_failed",
            {"task_id": task_id, "attempt_id": attempt_id, "validation": [vars(item) for item in validation.results]},
        )
        self._retry_or_replan(state, graph, task_id)

    def _retry_or_replan(self, state: RunState, graph: TaskGraph, task_id: str) -> None:
        task = state.tasks[task_id]
        attempt_count = len(task.attempt_ids)
        if (
            self.model is not None
            and attempt_count >= task.retry_policy.replan_after
        ):
            context = self.memory.build(state, task, action_contract=self.harness.action_contract())
            state.status = RunStatus.REPLANNING
            self._persist(state, "replan_started", {"task_id": task_id, "attempt_count": attempt_count})
            proposal = self.model.replan(
                state,
                task,
                context,
                self._persist_callback(),
                same_failure_count=max(0, attempt_count - 1),
            )
            self._apply_replan(state, graph, task_id, proposal)
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
        try:
            graph.add_tasks(proposal.tasks)
            replacement_id = proposal.supersede.get(failed_task_id)
            if not replacement_id:
                raise TaskGraphError(f"replan did not supersede failed task {failed_task_id}")
            graph.supersede(failed_task_id, replacement_id)
            for old_task_id, new_task_id in proposal.supersede.items():
                if old_task_id == failed_task_id:
                    continue
                graph.supersede(old_task_id, new_task_id)
            graph.validate()
        except Exception:
            state.tasks.clear()
            state.tasks.update(original_tasks)
            raise
        state.plan_generation += 1
        state.active_task_id = None
        state.status = RunStatus.RUNNING
        self._persist(
            state,
            "replan_saved",
            {
                "reason": proposal.reason,
                "new_task_ids": [task.task_id for task in proposal.tasks],
                "supersede": proposal.supersede,
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
        validation = self.validator.validate(
            task,
            result,
            state.goal,
            state,
            cross_check=self._model_cross_check(state),
        )
        graph = TaskGraph(state.tasks)
        if validation.required_passed:
            attempt.status = AttemptStatus.SUCCEEDED
            attempt.ended_at = utc_now()
            attempt.validation_results = list(validation.results)
            graph.transition(task.task_id, TaskStatus.COMPLETED)
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
        attempt.validation_results = list(validation.results)
        graph.transition(task.task_id, TaskStatus.FAILED)
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
            if (
                self.model is not None
                and len(task.attempt_ids) >= task.retry_policy.replan_after
            ):
                context = self.memory.build(
                    state,
                    task,
                    action_contract=self.harness.action_contract(),
                )
                state.status = RunStatus.REPLANNING
                self._persist(
                    state,
                    "replan_recovery_started",
                    {"task_id": task.task_id, "attempt_count": len(task.attempt_ids)},
                )
                proposal = self.model.replan(
                    state,
                    task,
                    context,
                    self._persist_callback(),
                    same_failure_count=max(0, len(task.attempt_ids) - 1),
                )
                self._apply_replan(state, graph, task.task_id, proposal)
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
    ) -> None:
        artifact_refs: list[str] = []
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
        state.tasks[task_id].output_refs = [memory_id, *artifact_refs]

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
                    }
                    for task_id, task in state.tasks.items()
                    if task.active
                },
                "artifacts": {key: vars(value) for key, value in state.artifacts.items()},
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

    def _model_cross_check(self, state: RunState):
        method = getattr(self.model, "cross_validate", None) if self.model is not None else None
        if not callable(method):
            return None

        def check(task, action_result, spec):
            context = self.memory.build(
                state,
                task,
                action_contract=self.harness.action_contract(),
            )
            passed, reason = method(
                state,
                task,
                context,
                self._persist_callback(),
            )
            return ValidationResult(
                kind="model_cross_check",
                passed=bool(passed),
                required=spec.required,
                message=str(reason),
                evidence={"owner": "rwkv"},
            )

        return check

    @staticmethod
    def _goal_criteria_covered(state: RunState) -> bool:
        required = {
            criterion.criterion_id
            for criterion in state.goal.success_criteria
            if criterion.required
        }
        explicit = {
            criterion_id
            for task in state.tasks.values()
            if task.active and task.status == TaskStatus.COMPLETED
            for criterion_id in task.goal_criteria
        }
        if not any(task.goal_criteria for task in state.tasks.values()):
            return True
        return required.issubset(explicit)

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
