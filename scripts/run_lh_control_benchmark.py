"""Execute the LH-Control-30 deterministic architecture regression suite."""

from __future__ import annotations

import argparse
import hashlib
import importlib.resources
import json
import sqlite3
import sys
import tempfile
import threading
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.memory import MemoryBudgets, WorkingMemoryBuilder
from rwkv_lh.model import (
    CrossValidationDecision,
    LongHorizonModel,
    ModelInvoker,
    ReplanProposal,
)
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    CriterionEvidence,
    CriterionEvidenceStatus,
    GoalCriterion,
    GoalState,
    MemoryEntry,
    RetryPolicy,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationSpec,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.runtime.sampling import get_request_sampling


CATALOG_PATH = importlib.resources.files(
    "benchmarks.architecture_regression.lh_control_30"
).joinpath("tasks.json")


@dataclass
class CaseContext:
    spec: dict[str, Any]
    root: Path
    workspace: Path
    store: LongHorizonStore
    run_id: str


@dataclass
class CaseExecution:
    passed: bool
    actual_result: str
    final_verification: dict[str, Any]
    state: RunState | None = None
    extra: dict[str, Any] | None = None


def fixture_proof_decision(
    state: RunState,
    task: TaskNode,
    action_result: dict[str, Any] | None,
) -> CrossValidationDecision:
    output = str((action_result or {}).get("output") or "")
    return CrossValidationDecision(
        True,
        "fixture semantic pass",
        [
            {
                "criterion_id": criterion_id,
                "subject_task_id": task.subject_task_id or task.task_id,
                "producer_task_id": task.task_id,
                "comparison": "exact_equals",
                "actual": {
                    "read_op": "action_output_text",
                    "arguments": {},
                    "transforms": [],
                },
                "expected": {
                    "read_op": "goal_literal",
                    "arguments": {
                        "goal_quote": state.goal.original_request,
                        "value": output,
                    },
                    "transforms": [],
                },
            }
            for criterion_id in task.satisfies_criteria
        ],
    )


class FixtureProofModel:
    def cross_validate(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result=None,
        validation_results=None,
    ):
        return fixture_proof_decision(state, task, action_result)

    def final_answer(self, state, context, persist):
        return "verified fixture final"


class FixtureReplanModel(FixtureProofModel):
    def __init__(self, factory: Callable[[RunState, TaskNode], ReplanProposal], final: str = "verified fixture final"):
        self.factory = factory
        self.final = final

    def plan(self, state, persist):
        raise AssertionError("benchmark uses a persisted initial graph")

    def propose_action(self, state, task, context, action_contract, persist):
        raise AssertionError("benchmark task already has an action")

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        return self.factory(state, failed_task)

    def final_answer(self, state, context, persist):
        return self.final


class SequenceClient:
    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.calls: list[dict[str, Any]] = []
        self.lock = threading.Lock()

    def text_completion(self, prompt, max_tokens=768, stop=None):
        with self.lock:
            if not self.outputs:
                raise RuntimeError("fixture model output queue exhausted")
            output = self.outputs.pop(0)
            self.calls.append(
                {
                    "sampling": asdict(get_request_sampling()),
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                }
            )
        return type("Response", (), {"content": output})()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the LH-Control-30 deterministic architecture regression suite"
    )
    parser.add_argument(
        "--output",
        default=str(
            Path.cwd()
            / "outputs"
            / f"lh_control_30_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ),
    )
    parser.add_argument("--case", action="append", default=[], help="Run selected task id(s)")
    return parser.parse_args()


def load_catalog() -> list[dict[str, Any]]:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    tasks = payload.get("tasks") or []
    if len(tasks) != 30 or len({item["task_id"] for item in tasks}) != 30:
        raise ValueError("LH-Control-30 catalog must contain 30 unique tasks")
    return tasks


def make_context(output_root: Path, spec: dict[str, Any]) -> CaseContext:
    case_root = output_root / "cases" / spec["task_id"]
    workspace = case_root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    return CaseContext(
        spec=spec,
        root=case_root,
        workspace=workspace,
        store=LongHorizonStore(case_root / "state"),
        run_id=spec["task_id"],
    )


def make_goal(context: CaseContext) -> GoalState:
    return GoalState.create(
        objective=context.spec["description"],
        original_request=context.spec["description"],
        constraints=["Only modify the isolated benchmark workspace", "Verify observable results"],
        success_criteria=[GoalCriterion("GC1", context.spec["expected_result"])],
        workspace_root=context.workspace,
    )


def task(
    task_id: str,
    title: str,
    action_type: str,
    arguments: dict[str, Any],
    criteria: list[ValidationSpec] | None = None,
    *,
    dependencies: list[str] | None = None,
    retry: RetryPolicy | None = None,
    priority: int = 50,
) -> TaskNode:
    return TaskNode(
        task_id=task_id,
        title=title,
        description=title,
        dependencies=list(dependencies or []),
        goal_criteria=["GC1"],
        priority=priority,
        action=TaskAction(action_type, arguments),
        completion_criteria=list(criteria or []),
        retry_policy=retry or RetryPolicy(),
    )


def persist_graph(context: CaseContext, tasks: list[TaskNode]) -> RunState:
    state = context.store.create_run(make_goal(context), context.run_id)
    depended_on = {
        dependency for item in tasks for dependency in item.dependencies
    }
    for item in tasks:
        if item.required and item.task_id not in depended_on:
            item.satisfies_criteria = ["GC1"]
    state.tasks = {item.task_id: item for item in tasks}
    state.status = RunStatus.RUNNING
    return context.store.save(
        state,
        event_type="plan_saved",
        event={"task_ids": [item.task_id for item in tasks], "source": "benchmark_fixture"},
    )


def run_graph(
    context: CaseContext,
    tasks: list[TaskNode],
    *,
    model=None,
    max_transitions: int = 500,
) -> tuple[RunState, str]:
    state = persist_graph(context, tasks)
    result = LongHorizonController(
        context.store,
        model=model or FixtureProofModel(),
        max_transitions=max_transitions,
    ).run(state.run_id)
    return result.state, result.final_output


def execution(
    passed: bool,
    actual: str,
    verification: dict[str, Any],
    state: RunState | None = None,
    **extra: Any,
) -> CaseExecution:
    return CaseExecution(passed, actual, verification, state, extra or None)


def case_b01(context: CaseContext) -> CaseExecution:
    state, _ = run_graph(
        context,
        [task("T1", "write exact text", "write_file", {"path": "answer.txt", "content": "RWKV verified"}, [ValidationSpec("file_contains", {"path": "answer.txt", "text": "RWKV verified"})])],
    )
    content = (context.workspace / "answer.txt").read_text(encoding="utf-8")
    return execution(state.status == RunStatus.COMPLETED and content == "RWKV verified", state.status.value, {"content": content}, state)


def case_b02(context: CaseContext) -> CaseExecution:
    path = context.workspace / "config.json"
    path.write_text(json.dumps({"name": "keep", "feature": {"enabled": False}}, indent=2), encoding="utf-8")
    state, _ = run_graph(
        context,
        [task("T1", "enable feature", "replace_text", {"path": "config.json", "old": '"enabled": false', "new": '"enabled": true'}, [ValidationSpec("json_field_equals", {"path": "config.json", "field": "feature.enabled", "expected": True})])],
    )
    value = json.loads(path.read_text(encoding="utf-8"))
    passed = state.status == RunStatus.COMPLETED and value == {"name": "keep", "feature": {"enabled": True}}
    return execution(passed, state.status.value, {"json": value}, state)


def case_b03(context: CaseContext) -> CaseExecution:
    tasks = [
        task("T1", "first dependency", "write_file", {"path": "first.txt", "content": "first"}, [ValidationSpec("file_exists", {"path": "first.txt"})]),
        task("T2", "dependent output", "write_file", {"path": "second.txt", "content": "second"}, [ValidationSpec("file_exists", {"path": "second.txt"})], dependencies=["T1"]),
    ]
    state, _ = run_graph(context, tasks)
    completed_events = [item["data"]["task_id"] for item in context.store.event_records(context.run_id) if item["type"] == "task_completed"]
    passed = state.status == RunStatus.COMPLETED and completed_events == ["T1", "T2"]
    return execution(passed, state.status.value, {"completion_order": completed_events}, state)


def case_b04(context: CaseContext) -> CaseExecution:
    source = context.workspace / "input.bin"
    source.write_bytes(b"long-horizon-hash-input")
    expected = hashlib.sha256(source.read_bytes()).hexdigest()
    script = "from pathlib import Path; import hashlib; p=Path('input.bin'); Path('manifest.txt').write_text(hashlib.sha256(p.read_bytes()).hexdigest())"
    tasks = [task("T1", "write hash manifest", "run_command", {"argv": [sys.executable, "-c", script]}, [ValidationSpec("command_exit_code", {"expected": 0}), ValidationSpec("file_contains", {"path": "manifest.txt", "text": expected})])]
    state, _ = run_graph(context, tasks)
    actual = (context.workspace / "manifest.txt").read_text()
    return execution(state.status == RunStatus.COMPLETED and actual == expected, state.status.value, {"expected_sha256": expected, "actual_sha256": actual}, state)


def temporary_failure_task() -> TaskNode:
    script = "from pathlib import Path; p=Path('counter.txt'); n=int(p.read_text())+1 if p.exists() else 1; p.write_text(str(n)); raise SystemExit(0 if n >= 2 else 9)"
    return task(
        "T1", "retry temporary failure", "run_command", {"argv": [sys.executable, "-c", script]},
        [ValidationSpec("command_exit_code", {"expected": 0})],
        retry=RetryPolicy(max_attempts=2, replan_after=99),
    )


def case_b05(context: CaseContext) -> CaseExecution:
    state, _ = run_graph(context, [temporary_failure_task()])
    attempts = state.tasks["T1"].attempt_ids
    counter = (context.workspace / "counter.txt").read_text()
    return execution(state.status == RunStatus.COMPLETED and len(attempts) == 2 and counter == "2", state.status.value, {"attempts": attempts, "counter": counter}, state)


def case_b06(context: CaseContext) -> CaseExecution:
    state, _ = run_graph(context, [task("T1", "append once", "append_file", {"path": "log.txt", "content": "once\n"}, [ValidationSpec("file_contains", {"path": "log.txt", "text": "once"})])])
    first_revision = state.revision
    resumed = LongHorizonController(context.store).resume(state.run_id).state
    content = (context.workspace / "log.txt").read_text()
    passed = resumed.revision == first_revision and content == "once\n" and len(resumed.tasks["T1"].attempt_ids) == 1
    return execution(passed, resumed.status.value, {"first_revision": first_revision, "resume_revision": resumed.revision, "content": content}, resumed)


def case_b07(context: CaseContext) -> CaseExecution:
    state, _ = run_graph(context, [task("T1", "missing postcondition", "noop", {"output": "claimed"}, [ValidationSpec("file_exists", {"path": "missing.txt"})], retry=RetryPolicy(max_attempts=1, replan_after=99))])
    passed = state.status == RunStatus.BLOCKED and state.tasks["T1"].status == TaskStatus.BLOCKED
    return execution(passed, state.status.value, {"task_status": state.tasks["T1"].status.value, "file_exists": (context.workspace / "missing.txt").exists()}, state)


def case_b08(context: CaseContext) -> CaseExecution:
    (context.workspace / "condition.txt").write_text("blue", encoding="utf-8")
    script = "from pathlib import Path; v=Path('condition.txt').read_text().strip(); Path('branch.txt').write_text('BLUE' if v == 'blue' else 'OTHER')"
    state, _ = run_graph(
        context,
        [
            task(
                "T1",
                "choose branch",
                "run_command",
                {"argv": [sys.executable, "-c", script]},
                [
                    ValidationSpec("command_exit_code", {"expected": 0}),
                    ValidationSpec("file_contains", {"path": "branch.txt", "text": "BLUE"}),
                ],
            )
        ],
    )
    content = (context.workspace / "branch.txt").read_text()
    return execution(state.status == RunStatus.COMPLETED and content == "BLUE", state.status.value, {"branch": content}, state)


def case_b09(context: CaseContext) -> CaseExecution:
    state = context.store.create_run(make_goal(context), context.run_id)
    state.tasks = {
        "T0": task("T0", "dependency", "noop", {}),
        "T1": task("T1", "build release report", "noop", {}, dependencies=["T0"]),
    }
    state.memory_index["M-DEP"] = MemoryEntry("M-DEP", "result", "T0", "dependency", "required dependency")
    state.memory_index["M-EVIDENCE"] = MemoryEntry("M-EVIDENCE", "evidence", "S", "release evidence", "bound release fact", evidence_refs=["S#L1"], tags=["release"])
    state.memory_index["M-NOISE"] = MemoryEntry("M-NOISE", "noise", "N", "noise", "noise " * 20_000)
    bundle = WorkingMemoryBuilder(MemoryBudgets(total_input=1800)).build(state, state.tasks["T1"], action_contract="noop")
    passed = bundle.total_tokens <= 1800 and "M-DEP" in bundle.selected_memory_ids and "M-EVIDENCE" in bundle.selected_memory_ids and "M-NOISE" in bundle.excluded_memory_ids
    state = context.store.save(state, event_type="context_built", event={"selected": bundle.selected_memory_ids, "excluded": bundle.excluded_memory_ids, "tokens": bundle.total_tokens})
    return execution(passed, "context_built", {"tokens": bundle.total_tokens, "selected": bundle.selected_memory_ids, "noise_excluded": "M-NOISE" in bundle.excluded_memory_ids}, state)


def persist_callback(store: LongHorizonStore):
    def persist(state: RunState, event_type: str, event: dict[str, Any]) -> None:
        saved = store.save(state, event_type=event_type, event=event)
        state.revision = saved.revision
        state.updated_at = saved.updated_at

    return persist


def case_b10(context: CaseContext) -> CaseExecution:
    state = context.store.create_run(make_goal(context), context.run_id)
    client = SequenceClient(['"schema_version":"tool.v1"}', '"schema_version":"replan.v1"}'])
    invoker = ModelInvoker(client=client)
    invoker.invoke_json("tool", request_type="tool_action", task_id="T1", state=state, persist=persist_callback(context.store))
    invoker.invoke_json("replan", request_type="replan", task_id="T1", state=state, persist=persist_callback(context.store), generation=2)
    temperatures = [item.temperature for item in state.temp_decisions]
    profiles = [item["sampling"] for item in client.calls]
    passed = (
        temperatures == [0.05, 0.36]
        and [item["temperature"] for item in profiles] == temperatures
        and all(item["top_p"] == 1.0 and item["top_k"] == 0 for item in profiles)
        and len({item["request_id"] for item in profiles}) == 2
        and get_request_sampling().request_id == ""
    )
    return execution(
        passed,
        "model_requests_recorded",
        {"temperatures": temperatures, "sampling_profiles": profiles},
        state,
    )


def case_m01(context: CaseContext) -> CaseExecution:
    tasks = []
    for index in range(1, 4):
        tasks.append(task(f"T{index}", f"write config {index}", "write_json", {"path": f"config{index}.json", "value": {"enabled": True, "index": index}}, [ValidationSpec("json_field_equals", {"path": f"config{index}.json", "field": "enabled", "expected": True})]))
    checker = "import json; from pathlib import Path; raise SystemExit(0 if all(json.loads(Path(f'config{i}.json').read_text())['enabled'] for i in range(1,4)) else 1)"
    tasks.append(task("T4", "check all configs", "check_command", {"argv": [sys.executable, "-c", checker]}, [ValidationSpec("command_exit_code", {"expected": 0})], dependencies=["T1", "T2", "T3"]))
    state, _ = run_graph(context, tasks)
    return execution(state.status == RunStatus.COMPLETED, state.status.value, {"files": sorted(path.name for path in context.workspace.glob("config*.json"))}, state)


def replacement_model(replacement: TaskNode, failed_id: str = "T1", final: str = "replanned and verified") -> FixtureReplanModel:
    return FixtureReplanModel(lambda state, failed: ReplanProposal([replacement], {failed_id: replacement.task_id}, "material strategy change"), final=final)


def case_m02(context: CaseContext) -> CaseExecution:
    (context.workspace / "app.py").write_text("VALUE = 1\n", encoding="utf-8")
    check = "from pathlib import Path; raise SystemExit(0 if 'VALUE = 2' in Path('app.py').read_text() else 1)"
    tasks = [
        task("T1", "detect failing implementation", "check_command", {"argv": [sys.executable, "-c", check]}, [ValidationSpec("command_exit_code", {"expected": 0})], retry=RetryPolicy(max_attempts=3, replan_after=1)),
        task("T2", "run repaired check", "check_command", {"argv": [sys.executable, "-c", check]}, [ValidationSpec("command_exit_code", {"expected": 0})], dependencies=["T1"]),
    ]
    replacement = task("T1R", "repair implementation", "replace_text", {"path": "app.py", "old": "VALUE = 1", "new": "VALUE = 2"}, [ValidationSpec("file_contains", {"path": "app.py", "text": "VALUE = 2"})])
    state, _ = run_graph(context, tasks, model=replacement_model(replacement))
    passed = state.status == RunStatus.COMPLETED and not state.tasks["T1"].active and state.tasks["T2"].status == TaskStatus.COMPLETED
    return execution(passed, state.status.value, {"app": (context.workspace / "app.py").read_text(), "superseded_by": state.tasks["T1"].superseded_by}, state)


def case_m03(context: CaseContext) -> CaseExecution:
    tasks = [
        task("T1", "source A", "write_file", {"path": "a.txt", "content": "A"}, [ValidationSpec("file_exists", {"path": "a.txt"})]),
        task("T2", "source B", "write_file", {"path": "b.txt", "content": "B"}, [ValidationSpec("file_exists", {"path": "b.txt"})]),
        task("T3", "source C", "write_file", {"path": "c.txt", "content": "C"}, [ValidationSpec("file_exists", {"path": "c.txt"})]),
        task("T4", "combined report", "write_file", {"path": "report.txt", "content": "A+B+C"}, [ValidationSpec("file_contains", {"path": "report.txt", "text": "A+B+C"})], dependencies=["T1", "T2", "T3"]),
    ]
    state, _ = run_graph(context, tasks)
    return execution(state.status == RunStatus.COMPLETED, state.status.value, {"report": (context.workspace / "report.txt").read_text()}, state)


def case_m04(context: CaseContext) -> CaseExecution:
    (context.workspace / "source.txt").write_text("header\nVersion 8 theme is Ocean Renewal.\nfooter\n", encoding="utf-8")

    class WitnessFixtureClient:
        def __init__(self):
            self.calls: list[dict[str, Any]] = []

        @staticmethod
        def prompt_json(prompt: str, marker: str) -> Any:
            suffix = prompt.split(marker, 1)[1].lstrip()
            value, _ = json.JSONDecoder().raw_decode(suffix)
            return value

        def text_completion(self, prompt, max_tokens=768, stop=None):
            self.calls.append(
                {
                    "sampling": asdict(get_request_sampling()),
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                }
            )
            if "long-horizon.witness-mode.v1" in prompt:
                output = json.dumps(
                    {
                        "schema_version": "long-horizon.witness-mode.v1",
                        "decision": "goal_literal",
                    },
                    ensure_ascii=False,
                )
            elif "COMPLETE RAW SOURCE CATALOG:" in prompt:
                sources = self.prompt_json(
                    prompt, "COMPLETE RAW SOURCE CATALOG:\n"
                )
                actual = next(
                    item
                    for item in sources
                    if item["source_kind"] == "action_output"
                    and "actual" in item["eligible_sides"]
                )
                output = json.dumps(
                    {
                        "schema_version": "long-horizon.witness-binding.v1",
                        "decision": "pass",
                        "reason": "span directly supports the fact",
                        "witness_selections": [
                            {
                                "criterion_id": "GC1",
                                "actual_source_handle_id": actual["source_handle_id"],
                                "expected_goal_quote": "RWKV",
                                "expected_goal_value": "Version 8 theme is Ocean Renewal.",
                                "note": "bind action output to the requested release fact",
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            elif "SELECTED-SOURCE DERIVED HANDLE VARIANTS:" in prompt:
                view = self.prompt_json(
                    prompt, "SELECTED-SOURCE DERIVED HANDLE VARIANTS:\n"
                )
                item = view[0]

                def identity(groups):
                    return next(
                        variant["handle_id"]
                        for group in groups
                        for variant in group["variants"]
                        if variant["transforms"] == []
                    )

                output = json.dumps(
                    {
                        "schema_version": "long-horizon.witness-handle-binding.v1",
                        "witness_bindings": [
                            {
                                "intent_id": "WI-T1-GC1",
                                "criterion_id": "GC1",
                                "actual_handle_id": identity(item["actual_source_groups"]),
                                "expected_handle_id": identity(item["expected_source_groups"]),
                            }
                        ],
                    },
                    ensure_ascii=False,
                )
            else:
                output = ">Evidence span was bound and cross-validated."
            return type("Response", (), {"content": output})()

    client = WitnessFixtureClient()
    model = LongHorizonModel(ModelInvoker(client=client), action_contract="{}")
    evidence_task = task(
        "T1", "bind exact source span", "bind_evidence",
        {"path": "source.txt", "start_line": 2, "end_line": 2, "source": "fixture://game-release"},
        [ValidationSpec("evidence_bound", {}), ValidationSpec("model_cross_check", {})],
    )
    state, final = run_graph(context, [evidence_task], model=model)
    memory = state.memory_index.get("M-T1-A1")
    request_types = {item.request_type for item in state.temp_decisions}
    passed = (
        state.status == RunStatus.COMPLETED
        and bool(memory and memory.evidence_refs)
        and {
            "witness_selection",
            "witness_handle_binding",
        }.issubset(request_types)
    )
    return execution(passed, state.status.value, {"evidence_refs": memory.evidence_refs if memory else [], "temperatures": [asdict(item) for item in state.temp_decisions], "final": final}, state, model_calls=client.calls)


def interrupted_state(context: CaseContext, interrupted_task: TaskNode) -> RunState:
    state = context.store.create_run(make_goal(context), context.run_id)
    interrupted_task.satisfies_criteria = ["GC1"]
    interrupted_task.status = TaskStatus.RUNNING
    attempt = Attempt(
        attempt_id=f"{interrupted_task.task_id}-A1",
        task_id=interrupted_task.task_id,
        status=AttemptStatus.RUNNING,
        action_fingerprint=action_fingerprint(interrupted_task.action),
        idempotency_key="fixture-interrupted",
        started_at=utc_now(),
    )
    interrupted_task.attempt_ids = [attempt.attempt_id]
    state.tasks = {interrupted_task.task_id: interrupted_task}
    state.attempts = {attempt.attempt_id: attempt}
    state.active_task_id = interrupted_task.task_id
    state.status = RunStatus.INTERRUPTED
    return context.store.save(state, event_type="simulated_interruption")


def case_m05(context: CaseContext) -> CaseExecution:
    (context.workspace / "input.txt").write_text("read me", encoding="utf-8")
    interrupted = task("T1", "resume read-only task", "read_file", {"path": "input.txt"}, [ValidationSpec("action_succeeded", {})])
    state = interrupted_state(context, interrupted)
    result = LongHorizonController(
        context.store,
        model=FixtureProofModel(),
    ).resume(state.run_id).state
    statuses = [result.attempts[item].status.value for item in result.tasks["T1"].attempt_ids]
    passed = result.status == RunStatus.COMPLETED and statuses == ["interrupted", "succeeded"]
    return execution(passed, result.status.value, {"attempt_statuses": statuses}, result)


def case_m06(context: CaseContext) -> CaseExecution:
    first = task("T1", "cycle one", "noop", {}, dependencies=["T2"])
    second = task("T2", "cycle two", "noop", {}, dependencies=["T1"])
    error = ""
    try:
        TaskGraph({"T1": first, "T2": second})
    except TaskGraphError as exc:
        error = str(exc)
    return execution("cycle" in error, "plan_rejected", {"error": error, "side_effect_files": list(context.workspace.iterdir())})


def case_m07(context: CaseContext) -> CaseExecution:
    initial = task("T1", "missing subtask", "noop", {}, [ValidationSpec("file_exists", {"path": "needed.txt"})], retry=RetryPolicy(max_attempts=2, replan_after=1))
    replacement = task("T1R", "create missing artifact", "write_file", {"path": "needed.txt", "content": "added by replan"}, [ValidationSpec("file_contains", {"path": "needed.txt", "text": "added by replan"})])
    state, _ = run_graph(context, [initial], model=replacement_model(replacement))
    return execution(state.status == RunStatus.COMPLETED and (context.workspace / "needed.txt").exists(), state.status.value, {"replacement": state.tasks["T1"].superseded_by}, state)


def case_m08(context: CaseContext) -> CaseExecution:
    tasks = [
        task("T1", "upstream fails", "noop", {}, [ValidationSpec("file_exists", {"path": "never.txt"})], retry=RetryPolicy(max_attempts=1, replan_after=99)),
        task("T2", "must not execute", "write_file", {"path": "downstream.txt", "content": "bad"}, [ValidationSpec("file_exists", {"path": "downstream.txt"})], dependencies=["T1"]),
    ]
    state, _ = run_graph(context, tasks)
    passed = state.status == RunStatus.BLOCKED and state.tasks["T2"].status == TaskStatus.BLOCKED and not state.tasks["T2"].attempt_ids and not (context.workspace / "downstream.txt").exists()
    return execution(passed, state.status.value, {"upstream": state.tasks["T1"].status.value, "downstream": state.tasks["T2"].status.value}, state)


def case_m09(context: CaseContext) -> CaseExecution:
    (context.workspace / "log.txt").write_text("once\n", encoding="utf-8")
    completed = task("T1", "already completed append", "append_file", {"path": "log.txt", "content": "once\n"}, [ValidationSpec("file_contains", {"path": "log.txt", "text": "once"})])
    completed.status = TaskStatus.COMPLETED
    completed.attempt_ids = ["T1-A1"]
    state = persist_graph(context, [completed])
    state.attempts["T1-A1"] = Attempt("T1-A1", "T1", AttemptStatus.SUCCEEDED, action_fingerprint(completed.action), "done", utc_now(), ended_at=utc_now())
    state.criterion_evidence["CE-GC1-T1-A1"] = CriterionEvidence(
        "CE-GC1-T1-A1",
        "GC1",
        CriterionEvidenceStatus.VERIFIED,
        "T1",
        "T1-A1",
        validation_refs=["T1-A1:V1"],
    )
    state = context.store.save(state, event_type="completed_fixture_saved")
    first = LongHorizonController(context.store).run(state.run_id).state
    second = LongHorizonController(context.store).resume(state.run_id).state
    content = (context.workspace / "log.txt").read_text()
    passed = first.revision == second.revision and content == "once\n" and len(second.tasks["T1"].attempt_ids) == 1
    return execution(passed, second.status.value, {"first_revision": first.revision, "second_revision": second.revision, "content": content}, second)


def case_m10(context: CaseContext) -> CaseExecution:
    store = context.store
    contexts = []
    for suffix in ("A", "B"):
        workspace = context.root / f"workspace-{suffix}"
        workspace.mkdir()
        local = CaseContext(context.spec, context.root, workspace, store, f"{context.run_id}-{suffix}")
        state = store.create_run(make_goal(local), local.run_id)
        node = task("T1", f"write {suffix}", "write_file", {"path": f"{suffix}.txt", "content": suffix}, [ValidationSpec("file_contains", {"path": f"{suffix}.txt", "text": suffix})])
        node.satisfies_criteria = ["GC1"]
        state.tasks = {"T1": node}
        state.status = RunStatus.RUNNING
        store.save(state, event_type="plan_saved")
        contexts.append(local)
    results: dict[str, RunState] = {}
    threads = [
        threading.Thread(
            target=lambda item=local: results.__setitem__(
                item.run_id,
                LongHorizonController(
                    store,
                    model=FixtureProofModel(),
                ).run(item.run_id).state,
            )
        )
        for local in contexts
    ]
    for worker in threads:
        worker.start()
    for worker in threads:
        worker.join()
    passed = all(results[item.run_id].status == RunStatus.COMPLETED for item in contexts) and (contexts[0].workspace / "A.txt").read_text() == "A" and (contexts[1].workspace / "B.txt").read_text() == "B"
    return execution(passed, "concurrent_runs_finished", {"statuses": {key: value.status.value for key, value in results.items()}}, results[contexts[0].run_id], run_ids=list(results))


def case_h01(context: CaseContext) -> CaseExecution:
    interrupted = task("T1", "recover completed write", "write_file", {"path": "done.txt", "content": "single-write"}, [ValidationSpec("file_contains", {"path": "done.txt", "text": "single-write"})])
    state = interrupted_state(context, interrupted)
    ActionHarness().execute(interrupted.action, state.goal)
    resumed = LongHorizonController(
        context.store,
        model=FixtureProofModel(),
    ).resume(state.run_id).state
    passed = resumed.status == RunStatus.COMPLETED and len(resumed.tasks["T1"].attempt_ids) == 1 and (context.workspace / "done.txt").read_text() == "single-write"
    return execution(passed, resumed.status.value, {"attempts": resumed.tasks["T1"].attempt_ids, "content": (context.workspace / "done.txt").read_text()}, resumed)


def case_h02(context: CaseContext) -> CaseExecution:
    interrupted = task("T1", "unsafe append", "append_file", {"path": "log.txt", "content": "unknown"})
    state = interrupted_state(context, interrupted)
    resumed = LongHorizonController(context.store).resume(state.run_id).state
    passed = resumed.status == RunStatus.BLOCKED and resumed.tasks["T1"].error.get("type") == "UnsafeInterruptedAction"
    return execution(passed, resumed.status.value, {"error": resumed.tasks["T1"].error, "file_exists": (context.workspace / "log.txt").exists()}, resumed)


def case_h03(context: CaseContext) -> CaseExecution:
    state = context.store.create_run(make_goal(context), context.run_id)
    state.tasks["T1"] = task("T1", "checkpoint task", "noop", {})
    state = context.store.save(state, event_type="plan_saved")
    with sqlite3.connect(context.store.database_path) as connection:
        connection.execute("UPDATE runs SET state_json = ? WHERE run_id = ?", ("{broken", state.run_id))
    recovered = context.store.load(state.run_id)
    with sqlite3.connect(context.store.database_path) as connection:
        repaired = connection.execute("SELECT state_json FROM runs WHERE run_id = ?", (state.run_id,)).fetchone()[0]
    passed = recovered.revision == state.revision and "T1" in recovered.tasks and json.loads(repaired)["run_id"] == state.run_id
    return execution(passed, "checkpoint_recovered", {"revision": recovered.revision, "snapshot_repaired": True}, recovered)


def case_h04(context: CaseContext) -> CaseExecution:
    state = context.store.create_run(make_goal(context), context.run_id)
    errors: list[str] = []

    def contender():
        try:
            with context.store.controller_lease(state.run_id, timeout_seconds=0.05):
                pass
        except Exception as exc:
            errors.append(type(exc).__name__)

    with context.store.controller_lease(state.run_id):
        worker = threading.Thread(target=contender)
        worker.start()
        worker.join()
        with sqlite3.connect(context.store.database_path) as connection:
            owners = connection.execute("SELECT COUNT(*) FROM run_leases WHERE run_id = ?", (state.run_id,)).fetchone()[0]
    return execution(errors == ["TimeoutError"] and owners == 1, "lease_competition", {"contender_errors": errors, "active_owners": owners}, state)


def case_h05(context: CaseContext) -> CaseExecution:
    state = context.store.create_run(make_goal(context), context.run_id)
    dependency = task("T0", "artifact source", "noop", {})
    active = task("T1", "use selected artifact 42", "noop", {}, dependencies=["T0"])
    active.inputs = [{"ref": "memory:M42"}]
    state.tasks = {"T0": dependency, "T1": active}
    for index in range(50):
        path = context.workspace / f"artifact-{index}.txt"
        path.write_text((f"artifact {index} " * 300), encoding="utf-8")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        artifact_id = f"A{index}"
        state.artifacts[artifact_id] = ArtifactRecord(artifact_id, "T0", path.name, digest, "text/plain", f"artifact {index}")
        state.memory_index[f"M{index}"] = MemoryEntry(f"M{index}", "artifact", "T0" if index == 42 else f"N{index}", f"artifact summary {index}", path.read_text(), artifact_refs=[artifact_id], tags=["selected" if index == 42 else "noise"])
    bundle = WorkingMemoryBuilder().build(state, active, action_contract="read_file")
    state = context.store.save(state, event_type="large_context_built", event={"tokens": bundle.total_tokens, "selected": bundle.selected_memory_ids})
    passed = bundle.total_tokens <= 13600 and "M42" in bundle.selected_memory_ids and len(bundle.excluded_memory_ids) >= 49
    return execution(passed, "context_built", {"tokens": bundle.total_tokens, "selected_count": len(bundle.selected_memory_ids), "excluded_count": len(bundle.excluded_memory_ids)}, state)


def case_h06(context: CaseContext) -> CaseExecution:
    initial = task("T1", "out of scope proposal", "write_file", {"path": "../escape.txt", "content": "bad"}, [ValidationSpec("file_exists", {"path": "safe.txt"})], retry=RetryPolicy(max_attempts=2, replan_after=1))
    replacement = task("T1R", "scoped replacement", "write_file", {"path": "safe.txt", "content": "safe"}, [ValidationSpec("file_contains", {"path": "safe.txt", "text": "safe"})])
    state, _ = run_graph(context, [initial], model=replacement_model(replacement))
    escaped = context.workspace.parent / "escape.txt"
    passed = state.status == RunStatus.COMPLETED and not escaped.exists() and (context.workspace / "safe.txt").exists()
    return execution(passed, state.status.value, {"escaped_exists": escaped.exists(), "safe_exists": (context.workspace / "safe.txt").exists()}, state)


def case_h07(context: CaseContext) -> CaseExecution:
    (context.workspace / "status.txt").write_text("stable", encoding="utf-8")
    initial = task("T1", "conflicting validation", "read_file", {"path": "status.txt"}, [ValidationSpec("file_contains", {"path": "status.txt", "text": "stable"}), ValidationSpec("file_not_contains", {"path": "status.txt", "text": "stable"})], retry=RetryPolicy(max_attempts=2, replan_after=1))
    replacement = task("T1R", "resolve status", "write_file", {"path": "resolved.txt", "content": "status=stable; source=v2"}, [ValidationSpec("file_contains", {"path": "resolved.txt", "text": "source=v2"})])
    state, _ = run_graph(context, [initial], model=replacement_model(replacement))
    failed_attempt = state.attempts["T1-A1"]
    replacement_id = state.tasks["T1"].superseded_by
    passed = (
        state.status == RunStatus.COMPLETED
        and any(not item.passed for item in failed_attempt.validation_results)
        and replacement_id in state.tasks
        and state.tasks[replacement_id].title == "resolve status"
    )
    return execution(passed, state.status.value, {"failed_validation": [asdict(item) for item in failed_attempt.validation_results], "replacement": state.tasks["T1"].superseded_by}, state)


def case_h08(context: CaseContext) -> CaseExecution:
    client = SequenceClient(['"schema_version":"strict.v1"}', '"schema_version":"explore.v1"}'])
    invoker = ModelInvoker(client=client)
    errors: list[str] = []

    def invoke(request_type: str):
        try:
            invoker.invoke_json(request_type, request_type=request_type, task_id=request_type)
        except Exception as exc:
            errors.append(str(exc))

    workers = [
        threading.Thread(target=invoke, args=("evidence_extract",)),
        threading.Thread(target=invoke, args=("alternative_generation",)),
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    observed = sorted(
        (
            item["sampling"]["temperature"],
            item["sampling"]["task_id"],
            item["sampling"]["lane"],
        )
        for item in client.calls
    )
    request_ids = {item["sampling"]["request_id"] for item in client.calls}
    passed = (
        not errors
        and observed
        == [
            (0.02, "evidence_extract", "evidence_extract"),
            (0.32, "alternative_generation", "alternative_generation"),
        ]
        and len(request_ids) == 2
        and "" not in request_ids
        and get_request_sampling().request_id == ""
    )
    return execution(passed, "concurrent_model_requests", {"observed": observed, "errors": errors})


def case_h09(context: CaseContext) -> CaseExecution:
    tasks = []
    for index in range(1, 21):
        dependencies = [f"T{index - 1}"] if index > 1 else []
        tasks.append(task(f"T{index}", f"chain node {index}", "write_file", {"path": f"node-{index}.txt", "content": str(index)}, [ValidationSpec("file_contains", {"path": f"node-{index}.txt", "text": str(index)})], dependencies=dependencies))
    state = persist_graph(context, tasks)
    interrupted = LongHorizonController(
        context.store,
        model=FixtureProofModel(),
        max_transitions=11,
    ).run(state.run_id).state
    completed_before = {task_id for task_id, node in interrupted.tasks.items() if node.status == TaskStatus.COMPLETED}
    resumed = LongHorizonController(
        context.store,
        model=FixtureProofModel(),
    ).resume(state.run_id).state
    attempts = {task_id: len(node.attempt_ids) for task_id, node in resumed.tasks.items()}
    passed = interrupted.status == RunStatus.INTERRUPTED and len(completed_before) == 11 and resumed.status == RunStatus.COMPLETED and all(value == 1 for value in attempts.values())
    return execution(passed, resumed.status.value, {"completed_before_resume": sorted(completed_before), "attempt_counts": attempts}, resumed)


def case_h10(context: CaseContext) -> CaseExecution:
    (context.workspace / "app.py").write_text("def value():\n    return 1\n", encoding="utf-8")
    check = "from pathlib import Path; raise SystemExit(0 if 'return 2' in Path('app.py').read_text() else 1)"
    tasks = [
        task("T1", "write target config", "write_json", {"path": "config.json", "value": {"target": 2}}, [ValidationSpec("json_field_equals", {"path": "config.json", "field": "target", "expected": 2})]),
        task("T2", "check implementation", "check_command", {"argv": [sys.executable, "-c", check]}, [ValidationSpec("command_exit_code", {"expected": 0})], dependencies=["T1"], retry=RetryPolicy(max_attempts=3, replan_after=1)),
        task("T3", "recheck repaired implementation", "check_command", {"argv": [sys.executable, "-c", check]}, [ValidationSpec("command_exit_code", {"expected": 0})], dependencies=["T2"]),
        task("T4", "write final manifest", "write_file", {"path": "manifest.txt", "content": "config=verified\nimplementation=verified\n"}, [ValidationSpec("file_contains", {"path": "manifest.txt", "text": "implementation=verified"})], dependencies=["T3"]),
    ]
    replacement = task("T2R", "repair implementation", "replace_text", {"path": "app.py", "old": "return 1", "new": "return 2"}, [ValidationSpec("file_contains", {"path": "app.py", "text": "return 2"})], dependencies=["T1"])
    model = replacement_model(replacement, failed_id="T2", final="Full workflow verified")
    state, final = run_graph(context, tasks, model=model)
    manifest = (context.workspace / "manifest.txt").read_text() if (context.workspace / "manifest.txt").exists() else ""
    replacement_id = state.tasks["T2"].superseded_by
    passed = (
        state.status == RunStatus.COMPLETED
        and replacement_id in state.tasks
        and state.tasks[replacement_id].title == "repair implementation"
        and "implementation=verified" in manifest
    )
    return execution(passed, state.status.value, {"manifest": manifest, "replacement": state.tasks["T2"].superseded_by, "final": final}, state)


RUNNERS: dict[str, Callable[[CaseContext], CaseExecution]] = {
    "LH-B01": case_b01, "LH-B02": case_b02, "LH-B03": case_b03, "LH-B04": case_b04,
    "LH-B05": case_b05, "LH-B06": case_b06, "LH-B07": case_b07, "LH-B08": case_b08,
    "LH-B09": case_b09, "LH-B10": case_b10, "LH-M01": case_m01, "LH-M02": case_m02,
    "LH-M03": case_m03, "LH-M04": case_m04, "LH-M05": case_m05, "LH-M06": case_m06,
    "LH-M07": case_m07, "LH-M08": case_m08, "LH-M09": case_m09, "LH-M10": case_m10,
    "LH-H01": case_h01, "LH-H02": case_h02, "LH-H03": case_h03, "LH-H04": case_h04,
    "LH-H05": case_h05, "LH-H06": case_h06, "LH-H07": case_h07, "LH-H08": case_h08,
    "LH-H09": case_h09, "LH-H10": case_h10,
}


def audit_record(context: CaseContext, outcome: CaseExecution) -> dict[str, Any]:
    events = context.store.event_records(outcome.state.run_id) if outcome.state is not None else []
    temp_decisions = [asdict(item) for item in outcome.state.temp_decisions] if outcome.state is not None else []
    errors = list(outcome.state.errors) if outcome.state is not None else []
    return {
        "task_id": context.spec["task_id"],
        "level": context.spec["level"],
        "task_description": context.spec["description"],
        "expected_result": context.spec["expected_result"],
        "actual_result": outcome.actual_result,
        "success": outcome.passed,
        "steps": [
            {"revision": item["revision"], "type": item["type"], "data": item["data"]}
            for item in events
        ],
        "tool_calls": [item["data"] for item in events if item["type"] == "attempt_started"],
        "retries": [item["data"] for item in events if item["type"] in {"retry_scheduled", "replan_started", "replan_saved"}],
        "temp_decisions": temp_decisions,
        "model_inputs_outputs": [item["data"] for item in events if item["type"].startswith("model_request")],
        "errors": errors,
        "recovery": [item["data"] for item in events if "recover" in item["type"] or "interrupt" in item["type"]],
        "final_verification": outcome.final_verification,
        "extra": outcome.extra or {},
    }


def markdown_report(records: list[dict[str, Any]], started_at: str, finished_at: str) -> str:
    passed = sum(1 for item in records if item["success"])
    lines = [
        "# LH-Control-30 Architecture Regression",
        "",
        f"- Started: `{started_at}`",
        f"- Finished: `{finished_at}`",
        f"- Passed: `{passed}/{len(records)}`",
        "- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.",
        "- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.",
        "",
        "| Task | Level | Result | Actual |",
        "| --- | --- | --- | --- |",
    ]
    for item in records:
        result = "PASS" if item["success"] else "FAIL"
        actual = str(item["actual_result"]).replace("|", "\\|").replace("\n", " ")
        lines.append(f"| {item['task_id']} | {item['level']} | {result} | {actual} |")
    lines.extend(["", "Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.", ""])
    return "\n".join(lines)


def main() -> int:
    arguments = parse_args()
    output_root = Path(arguments.output).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)
    selected = set(arguments.case or [])
    catalog = [item for item in load_catalog() if not selected or item["task_id"] in selected]
    unknown = selected - {item["task_id"] for item in load_catalog()}
    if unknown:
        raise ValueError(f"unknown benchmark case(s): {sorted(unknown)}")
    started_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    records: list[dict[str, Any]] = []
    for spec in catalog:
        context = make_context(output_root, spec)
        try:
            outcome = RUNNERS[spec["task_id"]](context)
        except Exception as exc:
            outcome = execution(False, f"{type(exc).__name__}: {exc}", {"exception": f"{type(exc).__name__}: {exc}"})
        record = audit_record(context, outcome)
        records.append(record)
        (context.root / "audit.json").write_text(json.dumps(record, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
        print(f"{spec['task_id']}: {'PASS' if record['success'] else 'FAIL'} - {record['actual_result']}", flush=True)
    finished_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    summary = {
        "schema_version": "lh-control-30-results.v1",
        "started_at": started_at,
        "finished_at": finished_at,
        "total": len(records),
        "passed": sum(1 for item in records if item["success"]),
        "failed": sum(1 for item in records if not item["success"]),
        "records": records,
    }
    (output_root / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")
    (output_root / "REPORT.md").write_text(markdown_report(records, started_at, finished_at), encoding="utf-8")
    print(json.dumps({key: summary[key] for key in ("total", "passed", "failed")}, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
