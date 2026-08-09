"""RWKV model adapter and audited request-level sampling invoker."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Protocol
from uuid import uuid4

from rwkv_lh.memory import ContextBundle
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import (
    GoalCriterion,
    GoalState,
    RetryPolicy,
    RunState,
    TaskAction,
    TaskNode,
    TempDecision,
    ValidationSpec,
    utc_now,
)
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.temp_policy import TemperaturePolicy
from rwkv_lh.validation import ValidationEngine
from rwkv_lh.prompting import JSON_CALL_STOP_SUFFIXES, assistant_json_prefix, visible_model_text
from rwkv_lh.runtime import (
    OpenAICompatibleRWKVClient,
    current_model_lane,
    current_task_id,
    sampling_parameters,
)


PersistCallback = Callable[[RunState, str, Mapping[str, Any]], None]


class CompletionClient(Protocol):
    def text_completion(
        self,
        prompt: str,
        max_tokens: int = 768,
        stop: list[str] | tuple[str, ...] | None = None,
    ) -> Any: ...


class ModelProtocolError(ValueError):
    pass


@dataclass
class ModelCallResult:
    text: str
    decision: TempDecision
    payload: dict[str, Any] | None = None


@dataclass
class ReplanProposal:
    tasks: list[TaskNode]
    supersede: dict[str, str]
    reason: str


class ModelInvoker:
    def __init__(
        self,
        client: CompletionClient | None = None,
        policy: TemperaturePolicy | None = None,
    ):
        self.client = client or OpenAICompatibleRWKVClient()
        self.policy = policy or TemperaturePolicy()

    def invoke_json(
        self,
        prompt: str,
        *,
        request_type: str,
        task_id: str,
        state: RunState | None = None,
        persist: PersistCallback | None = None,
        generation: int = 1,
        attempt: int = 1,
        same_failure_count: int = 0,
        complex_task: bool = False,
        new_evidence: bool = False,
        seed: int | None = None,
        max_tokens: int = 4096,
    ) -> ModelCallResult:
        result = self.invoke_text(
            prompt,
            request_type=request_type,
            task_id=task_id,
            state=state,
            persist=persist,
            generation=generation,
            attempt=attempt,
            same_failure_count=same_failure_count,
            complex_task=complex_task,
            new_evidence=new_evidence,
            seed=seed,
            max_tokens=max_tokens,
            json_output=True,
        )
        try:
            result.payload = extract_json_object(result.text)
            return result
        except Exception as exc:
            result.decision.outcome = "protocol_error"
            result.decision.error = f"{type(exc).__name__}: {exc}"[:1000]
            if state is not None and persist is not None:
                persist(
                    state,
                    "model_protocol_error",
                    {
                        "request_id": result.decision.request_id,
                        "request_type": request_type,
                        "temperature": result.decision.temperature,
                        "output": result.text,
                        "error": result.decision.error,
                    },
                )
            raise ModelProtocolError(str(exc)) from exc

    def invoke_text(
        self,
        prompt: str,
        *,
        request_type: str,
        task_id: str,
        state: RunState | None = None,
        persist: PersistCallback | None = None,
        generation: int = 1,
        attempt: int = 1,
        same_failure_count: int = 0,
        complex_task: bool = False,
        new_evidence: bool = False,
        seed: int | None = None,
        max_tokens: int = 4096,
        json_output: bool = False,
    ) -> ModelCallResult:
        selection = self.policy.decide(
            request_type,
            generation=generation,
            same_failure_count=same_failure_count,
            complex_task=complex_task,
            new_evidence=new_evidence,
        )
        decision = TempDecision(
            request_id=f"MR-{uuid4().hex[:16]}",
            task_id=str(task_id or "RUN"),
            request_type=selection.request_type,
            temperature=selection.temperature,
            policy_reason=selection.reason,
            attempt=max(1, int(attempt)),
            started_at=utc_now(),
        )
        if state is not None:
            state.temp_decisions.append(decision)
            if persist is not None:
                persist(
                    state,
                    "model_request_started",
                    {
                        "request_id": decision.request_id,
                        "task_id": decision.task_id,
                        "request_type": decision.request_type,
                        "temperature": decision.temperature,
                        "policy_reason": decision.policy_reason,
                        "seed": seed,
                        "prompt": prompt,
                    },
                )
        task_token = current_task_id.set(state.run_id if state is not None else task_id)
        lane_token = current_model_lane.set("control")
        try:
            with sampling_parameters(decision.temperature, seed=seed):
                response = self.client.text_completion(
                    prompt,
                    max_tokens=max(1, int(max_tokens)),
                    stop=JSON_CALL_STOP_SUFFIXES if json_output else None,
                )
            text = str(getattr(response, "content", response) or "")
            decision.ended_at = utc_now()
            decision.outcome = "ok"
            decision.result_summary = visible_model_text(text)[:1000]
            if state is not None and persist is not None:
                persist(
                    state,
                    "model_request_returned",
                    {
                        "request_id": decision.request_id,
                        "task_id": decision.task_id,
                        "request_type": decision.request_type,
                        "temperature": decision.temperature,
                        "seed": seed,
                        "output": visible_model_text(text),
                    },
                )
            return ModelCallResult(text=text, decision=decision)
        except Exception as exc:
            decision.ended_at = utc_now()
            decision.outcome = "error"
            decision.error = f"{type(exc).__name__}: {exc}"[:1000]
            if state is not None and persist is not None:
                persist(
                    state,
                    "model_request_failed",
                    {
                        "request_id": decision.request_id,
                        "task_id": decision.task_id,
                        "request_type": decision.request_type,
                        "temperature": decision.temperature,
                        "seed": seed,
                        "error": decision.error,
                    },
                )
            raise
        finally:
            current_model_lane.reset(lane_token)
            current_task_id.reset(task_token)


class LongHorizonModel:
    def __init__(
        self,
        invoker: ModelInvoker | None = None,
        *,
        harness: ActionHarness | None = None,
        action_contract: str | None = None,
    ):
        self.invoker = invoker or ModelInvoker()
        self.harness = harness or ActionHarness()
        self.action_contract = action_contract or self.harness.action_contract()

    def parse_goal(
        self,
        request: str,
        workspace_root: str,
        *,
        constraints: list[str] | None = None,
        seed: int | None = None,
    ) -> tuple[GoalState, TempDecision]:
        prompt = self._json_prompt(
            "Normalize the user's long-running task into an immutable goal. Preserve every hard constraint. "
            "Do not invent requirements. Return one JSON object with schema_version=long-horizon.goal-proposal.v1, "
            "objective, constraints (array), and success_criteria (array of objects with id, description, required). "
            "Every criterion must describe an externally verifiable outcome, not the model saying done.\n\n"
            f"USER REQUEST:\n{request}\n\n"
            f"CALLER CONSTRAINTS:\n{json.dumps(constraints or [], ensure_ascii=False)}\n\n"
            f"SCOPED WORKSPACE:\n{workspace_root}"
        )
        call = self.invoker.invoke_json(
            prompt,
            request_type="goal_parse",
            task_id="GOAL",
            seed=seed,
            max_tokens=1600,
        )
        payload = call.payload or {}
        if str(payload.get("schema_version") or "") != "long-horizon.goal-proposal.v1":
            raise ModelProtocolError("invalid goal proposal schema")
        criteria = [
            GoalCriterion.from_dict(item)
            for item in payload.get("success_criteria") or []
            if isinstance(item, Mapping)
        ]
        if not criteria:
            raise ModelProtocolError("goal proposal has no success criteria")
        merged_constraints = list(constraints or [])
        merged_constraints.extend(str(item) for item in payload.get("constraints") or [])
        goal = GoalState.create(
            objective=str(payload.get("objective") or request),
            original_request=request,
            constraints=list(dict.fromkeys(item.strip() for item in merged_constraints if item.strip())),
            success_criteria=criteria,
            workspace_root=workspace_root,
        )
        return goal, call.decision

    def plan(self, state: RunState, persist: PersistCallback) -> list[TaskNode]:
        criterion_ids = [
            criterion.criterion_id for criterion in state.goal.success_criteria
        ]
        body = (
            "Decompose the immutable goal into a compact acyclic task graph. Return one JSON object with "
            "schema_version=long-horizon.plan.v1 and tasks. Each task requires task_id, title, description, "
            "dependencies, required, priority, action {type, arguments}, completion_criteria, and retry_policy. "
            "Each task must include goal_criteria containing the immutable criterion ids it advances. "
            "Use only actions from the supplied contract. Completion criteria must verify observable state. "
            "Do not repeat or rewrite GoalState fields. Do not put required_postconditions inside action. "
            "Every completion_criteria item must use exactly {kind, parameters, required}; it is a verifier, "
            "not a copy of a textual Goal criterion. Example task shape: "
            '{"task_id":"T1","title":"...","description":"...","dependencies":[],"goal_criteria":["GC1"],'
            '"required":true,"priority":50,"action":{"type":"write_file","arguments":{"path":"x.txt","content":"x"}},'
            '"completion_criteria":[{"kind":"file_contains","parameters":{"path":"x.txt","text":"x"},"required":true}],'
            '"retry_policy":{"max_attempts":3,"backoff_seconds":0.2,"replan_after":2}}. '
            "Do not alter the goal, create benchmark-specific shortcuts, or claim completion.\n\n"
            f"GOAL:\n{json.dumps(state.goal.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"ACTION CONTRACT:\n{self.action_contract}\n\n"
            "FINAL STRUCTURAL CHECK:\n"
            f"- The only valid goal_criteria ids are: {json.dumps(criterion_ids, ensure_ascii=False)}.\n"
            "- Every task object MUST contain a non-empty goal_criteria array.\n"
            "- Across all required tasks, every required Goal criterion id MUST appear at least once.\n"
            "- Copy criterion ids exactly; never rename, summarize, or omit them."
        )
        last_error = ""
        last_output = ""
        for attempt in range(1, 3):
            request_body = body
            if attempt > 1:
                request_body += (
                    "\n\nPROTOCOL CORRECTION: The previous plan was rejected by the deterministic parser. "
                    f"Error: {last_error}. Return a new compact long-horizon.plan.v1 object only. "
                    "Do not repeat schema_version=long-horizon.goal.v1, objective, original_request, constraints, "
                    "success_criteria, workspace_root, created_at, or digest. Use executable verifier kinds and parameters. "
                    f"Every task must include goal_criteria copied from this exact allowed list: "
                    f"{json.dumps(criterion_ids, ensure_ascii=False)}. The complete plan must cover every required id. "
                    f"Previous rejected output for correction:\n{last_output[:8000]}"
                )
            call = self.invoker.invoke_json(
                self._json_prompt(request_body),
                request_type="task_decomposition",
                task_id="PLAN",
                state=state,
                persist=persist,
                generation=max(1, state.plan_generation + 1),
                attempt=attempt,
                complex_task=len(state.goal.original_request) > 1000,
                max_tokens=5000 if attempt == 1 else 3600,
            )
            payload = call.payload or {}
            try:
                if str(payload.get("schema_version") or "") != "long-horizon.plan.v1":
                    raise ModelProtocolError("invalid plan schema")
                tasks = self._task_nodes(payload.get("tasks"))
                self._validate_task_contracts(tasks)
                TaskGraph({task.task_id: task for task in tasks})
                self._validate_goal_bindings(state, tasks, require_coverage=True)
                return tasks
            except (ModelProtocolError, TaskGraphError) as exc:
                last_error = str(exc)
                last_output = visible_model_text(call.text)
                call.decision.outcome = "contract_error"
                call.decision.error = last_error[:1000]
                persist(
                    state,
                    "model_contract_error",
                    {
                        "request_id": call.decision.request_id,
                        "request_type": "task_decomposition",
                        "temperature": call.decision.temperature,
                        "error": last_error,
                        "output": last_output,
                    },
                )
        raise ModelProtocolError(last_error or "task plan contract validation failed")

    def propose_action(
        self,
        state: RunState,
        task: TaskNode,
        context: ContextBundle,
        action_contract: str,
        persist: PersistCallback,
    ) -> TaskAction:
        prompt = self._json_prompt(
            "Select one concrete harness action for the active task. Return one JSON object with "
            "schema_version=long-horizon.action.v1 and action {type, arguments}. Stay inside the scoped workspace. "
            "Do not mark the task complete; the Controller will execute and verify it.\n\n"
            f"CONTEXT:\n{context.to_prompt()}\n\nACTION CONTRACT:\n{action_contract}"
        )
        call = self.invoker.invoke_json(
            prompt,
            request_type="tool_action",
            task_id=task.task_id,
            state=state,
            persist=persist,
            attempt=len(task.attempt_ids) + 1,
            max_tokens=1800,
        )
        payload = call.payload or {}
        if str(payload.get("schema_version") or "") != "long-horizon.action.v1":
            raise ModelProtocolError("invalid action schema")
        return TaskAction.from_dict(payload.get("action"))

    def replan(
        self,
        state: RunState,
        failed_task: TaskNode,
        context: ContextBundle,
        persist: PersistCallback,
        *,
        same_failure_count: int,
    ) -> ReplanProposal:
        body = (
            "Replan only the unresolved part of the task graph after a material verified failure. Preserve every "
            "completed task. Return one JSON object with schema_version=long-horizon.replan.v1, reason, new_tasks, "
            "and supersede (array of {old_task_id,new_task_id}). New task ids must not reuse existing ids. "
            "Change the failed strategy instead of restating it. Do not emit reasoning, plan prose, commands, "
            "keystrokes, shell snippets, or task_complete. Each new task uses the same exact task schema as the "
            "initial plan, including goal_criteria and executable completion_criteria {kind,parameters,required}. "
            "Example envelope: "
            '{"schema_version":"long-horizon.replan.v1","reason":"material verifier gap",'
            '"new_tasks":[{"task_id":"T9","title":"...","description":"...","dependencies":[],'
            '"goal_criteria":["GC1"],"required":true,"priority":50,'
            '"action":{"type":"write_file","arguments":{"path":"x.txt","content":"x"}},'
            '"completion_criteria":[{"kind":"file_content","parameters":{"path":"x.txt","expected_content":"x","exact_match":true},"required":true}],'
            '"retry_policy":{"max_attempts":3,"backoff_seconds":0.2,"replan_after":2}}],'
            '"supersede":[{"old_task_id":"T1","new_task_id":"T9"}]}.\n\n'
            f"FAILED TASK:\n{json.dumps(failed_task.to_dict(), ensure_ascii=False, indent=2)}\n\n"
            f"CURRENT CONTEXT:\n{context.to_prompt()}\n\n"
            f"EXISTING TASK IDS:\n{json.dumps(sorted(state.tasks), ensure_ascii=False)}"
        )
        last_error = ""
        last_output = ""
        for attempt in range(1, 3):
            request_body = body
            if attempt > 1:
                request_body += (
                    "\n\nPROTOCOL CORRECTION: The previous replan was rejected. "
                    f"Error: {last_error}. Return only the exact long-horizon.replan.v1 envelope. "
                    "Do not return reasoning/plan/commands/keystrokes/task_complete. "
                    f"Previous rejected output:\n{last_output[:6000]}"
                )
            call = self.invoker.invoke_json(
                self._json_prompt(request_body),
                request_type="replan",
                task_id=failed_task.task_id,
                state=state,
                persist=persist,
                generation=max(1, state.plan_generation + 1),
                attempt=attempt,
                same_failure_count=same_failure_count,
                max_tokens=4200 if attempt == 1 else 3200,
            )
            payload = call.payload or {}
            try:
                if str(payload.get("schema_version") or "") != "long-horizon.replan.v1":
                    raise ModelProtocolError("invalid replan schema")
                tasks = self._task_nodes(payload.get("new_tasks"))
                self._validate_task_contracts(tasks)
                self._validate_goal_bindings(state, tasks, require_coverage=False)
                supersede = {
                    str(item.get("old_task_id") or ""): str(item.get("new_task_id") or "")
                    for item in payload.get("supersede") or []
                    if isinstance(item, Mapping)
                    and str(item.get("old_task_id") or "")
                    and str(item.get("new_task_id") or "")
                }
                if failed_task.task_id not in supersede:
                    raise ModelProtocolError("replan does not supersede the failed task")
                if supersede[failed_task.task_id] not in {task.task_id for task in tasks}:
                    raise ModelProtocolError("replan replacement task is missing")
                return ReplanProposal(tasks, supersede, str(payload.get("reason") or ""))
            except ModelProtocolError as exc:
                last_error = str(exc)
                last_output = visible_model_text(call.text)
                call.decision.outcome = "contract_error"
                call.decision.error = last_error[:1000]
                persist(
                    state,
                    "model_contract_error",
                    {
                        "request_id": call.decision.request_id,
                        "request_type": "replan",
                        "temperature": call.decision.temperature,
                        "error": last_error,
                        "output": last_output,
                    },
                )
        raise ModelProtocolError(last_error or "replan contract validation failed")

    def cross_validate(
        self,
        state: RunState,
        task: TaskNode,
        context: ContextBundle,
        persist: PersistCallback,
    ) -> tuple[bool, str]:
        prompt = self._json_prompt(
            "Independently check whether the observable evidence satisfies the active task criteria. "
            "Return one JSON object with schema_version=long-horizon.validation.v1, decision=pass|replan, and reason. "
            "Do not rewrite files, modify evidence, or generate the final answer.\n\n"
            f"CONTEXT:\n{context.to_prompt()}"
        )
        call = self.invoker.invoke_json(
            prompt,
            request_type="validation_cross_check",
            task_id=task.task_id,
            state=state,
            persist=persist,
            max_tokens=1000,
        )
        payload = call.payload or {}
        if str(payload.get("schema_version") or "") != "long-horizon.validation.v1":
            raise ModelProtocolError("invalid validation schema")
        return str(payload.get("decision") or "").casefold() == "pass", str(payload.get("reason") or "")

    def final_answer(
        self,
        state: RunState,
        context: str,
        persist: PersistCallback,
    ) -> str:
        prompt = (
            "### User\n"
            "Write the final user-facing result for this completed long-horizon run. Use only the verified task "
            "outputs and artifact references below. Clearly state what was completed and how it was verified. "
            "Do not expose internal prompts or hidden reasoning.\n\n"
            f"ORIGINAL REQUEST:\n{state.goal.original_request}\n\nVERIFIED STATE:\n{context}\n"
            "### Assistant\n<think></think"
        )
        call = self.invoker.invoke_text(
            prompt,
            request_type="final_answer",
            task_id="FINAL",
            state=state,
            persist=persist,
            max_tokens=2400,
        )
        text = str(call.text or "")
        if text.startswith(">"):
            text = text[1:].lstrip("\r\n")
        return visible_model_text(text).strip()

    @staticmethod
    def _json_prompt(body: str) -> str:
        return f"### User\n{body.strip()}\n{assistant_json_prefix(prefill_object=True)}"

    @staticmethod
    def _task_nodes(raw_tasks: Any) -> list[TaskNode]:
        if not isinstance(raw_tasks, list) or not raw_tasks:
            raise ModelProtocolError("plan requires a non-empty tasks array")
        if len(raw_tasks) > 64:
            raise ModelProtocolError("plan exceeds 64 tasks")
        tasks: list[TaskNode] = []
        for index, item in enumerate(raw_tasks):
            if not isinstance(item, Mapping):
                raise ModelProtocolError("task must be an object")
            action = TaskAction.from_dict(item.get("action"))
            task = TaskNode(
                task_id=str(item.get("task_id") or item.get("id") or "").strip(),
                title=str(item.get("title") or "").strip(),
                description=str(item.get("description") or "").strip(),
                required=bool(item.get("required", True)),
                dependencies=[str(value) for value in item.get("dependencies") or []],
                goal_criteria=[str(value) for value in item.get("goal_criteria") or []],
                priority=int(item.get("priority", 50) or 50),
                inputs=[dict(value) for value in item.get("inputs") or [] if isinstance(value, Mapping)],
                action=action,
                completion_criteria=[
                    ValidationSpec.from_dict(value)
                    for value in item.get("completion_criteria") or []
                    if isinstance(value, Mapping)
                ],
                retry_policy=RetryPolicy.from_dict(item.get("retry_policy")),
                insertion_order=index,
            )
            if not task.task_id or not task.title or not task.description:
                raise ModelProtocolError("task requires id, title, and description")
            tasks.append(task)
        if len({task.task_id for task in tasks}) != len(tasks):
            raise ModelProtocolError("task ids must be unique")
        return tasks

    @staticmethod
    def _validate_goal_bindings(
        state: RunState,
        tasks: list[TaskNode],
        *,
        require_coverage: bool,
    ) -> None:
        known = {criterion.criterion_id for criterion in state.goal.success_criteria}
        bound = {criterion_id for task in tasks for criterion_id in task.goal_criteria}
        unknown = sorted(bound - known)
        if unknown:
            raise ModelProtocolError(f"tasks bind unknown goal criteria: {unknown}")
        if require_coverage:
            required = {
                criterion.criterion_id
                for criterion in state.goal.success_criteria
                if criterion.required
            }
            missing = sorted(required - bound)
            if missing:
                raise ModelProtocolError(f"plan does not cover required goal criteria: {missing}")

    def _validate_task_contracts(self, tasks: list[TaskNode]) -> None:
        harness = self.harness
        for task in tasks:
            try:
                definition = harness.definition(task.action.action_type)
            except Exception as exc:
                raise ModelProtocolError(
                    f"task {task.task_id} uses unsupported action: {task.action.action_type}"
                ) from exc
            if not task.completion_criteria:
                raise ModelProtocolError(
                    f"task {task.task_id} has no executable completion criteria"
                )
            invalid = [
                criterion.kind
                for criterion in task.completion_criteria
                if criterion.kind not in ValidationEngine.supported_kinds
            ]
            if invalid:
                raise ModelProtocolError(
                    f"task {task.task_id} uses unsupported verifier kinds: {invalid}"
                )
            missing = harness.missing_required_postconditions(
                definition.name,
                [criterion.kind for criterion in task.completion_criteria],
            )
            if missing:
                raise ModelProtocolError(
                    f"task {task.task_id} is missing required postconditions: {missing}"
                )


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = visible_model_text(text).strip()
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    decoder = json.JSONDecoder()
    candidates = [cleaned]
    if re.match(r'^"(?:schema_version|tasks|new_tasks|action|decision|objective)"\s*:', cleaned):
        candidates.insert(0, "{" + cleaned)
    for candidate in candidates:
        for index, character in enumerate(candidate):
            if character != "{":
                continue
            try:
                value, _ = decoder.raw_decode(candidate[index:])
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value
    raise ModelProtocolError("model output does not contain a complete JSON object")


__all__ = [
    "LongHorizonModel",
    "ModelCallResult",
    "ModelInvoker",
    "ModelProtocolError",
    "ReplanProposal",
    "extract_json_object",
]
