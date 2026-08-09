import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from rwkv_lh.runtime.sampling import get_llm_seed, get_llm_temperature
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import (
    ActionProposal,
    FailureAnalysisProposal,
    LongHorizonModel,
    ModelInvoker,
    ModelProtocolError,
    ReplanProposal,
)
from rwkv_lh.schema import (
    Attempt,
    AttemptStatus,
    GoalCriterion,
    GoalState,
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


def make_goal(root: Path) -> GoalState:
    root.mkdir(parents=True, exist_ok=True)
    return GoalState.create(
        objective="Execute and verify a long task",
        original_request="Execute every dependent step and verify the artifacts",
        constraints=["Stay in the workspace"],
        success_criteria=[GoalCriterion("GC1", "All required tasks are verified")],
        workspace_root=root,
    )


def save_tasks(store: LongHorizonStore, state: RunState, tasks: list[TaskNode]) -> RunState:
    state.tasks = {task.task_id: task for task in tasks}
    state.status = RunStatus.RUNNING
    return store.save(state, event_type="plan_saved")


def test_controller_executes_dependency_chain_and_resume_is_noop():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-CHAIN")
        tasks = [
            TaskNode(
                "T1",
                "Write first",
                "Create the first dependency",
                action=TaskAction("write_file", {"path": "first.txt", "content": "first"}),
                completion_criteria=[ValidationSpec("file_contains", {"path": "first.txt", "text": "first"})],
            ),
            TaskNode(
                "T2",
                "Write second",
                "Create the dependent artifact",
                dependencies=["T1"],
                action=TaskAction("append_file", {"path": "second.txt", "content": "once"}),
                completion_criteria=[ValidationSpec("file_contains", {"path": "second.txt", "text": "once"})],
            ),
        ]
        state = save_tasks(store, state, tasks)
        result = LongHorizonController(store).run(state.run_id)
        revision = result.state.revision
        assert result.state.status == RunStatus.COMPLETED
        assert (root / "workspace" / "second.txt").read_text() == "once"
        resumed = LongHorizonController(store).resume(state.run_id)
        assert resumed.state.revision == revision
        assert (root / "workspace" / "second.txt").read_text() == "once"


def test_controller_retries_a_verified_command_failure():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-RETRY")
        script = (
            "from pathlib import Path; "
            "p=Path('counter.txt'); n=int(p.read_text())+1 if p.exists() else 1; "
            "p.write_text(str(n)); raise SystemExit(0 if n >= 2 else 7)"
        )
        task = TaskNode(
            "T1",
            "Retry checker",
            "Fail once and then pass",
            action=TaskAction("run_command", {"argv": [sys.executable, "-c", script]}),
            completion_criteria=[ValidationSpec("command_exit_code", {"expected": 0})],
            retry_policy=RetryPolicy(max_attempts=2, replan_after=99),
        )
        state = save_tasks(store, state, [task])
        result = LongHorizonController(store).run(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert len(result.state.tasks["T1"].attempt_ids) == 2
        assert (root / "workspace" / "counter.txt").read_text() == "2"


def test_recovery_accepts_postcondition_without_repeating_write():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        goal = make_goal(root / "workspace")
        state = store.create_run(goal, "LH-RECOVER-WRITE")
        task = TaskNode(
            "T1",
            "Write artifact",
            "Write before a simulated crash",
            status=TaskStatus.RUNNING,
            action=TaskAction("write_file", {"path": "done.txt", "content": "done"}),
            completion_criteria=[ValidationSpec("file_contains", {"path": "done.txt", "text": "done"})],
            attempt_ids=["T1-A1"],
        )
        attempt = Attempt(
            "T1-A1",
            "T1",
            AttemptStatus.RUNNING,
            action_fingerprint(task.action),
            "key",
            utc_now(),
        )
        state.tasks = {"T1": task}
        state.attempts = {attempt.attempt_id: attempt}
        state.active_task_id = "T1"
        state.status = RunStatus.INTERRUPTED
        state = store.save(state, event_type="simulated_crash")
        ActionHarness().execute(task.action, goal)
        result = LongHorizonController(store).resume(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert result.state.attempts["T1-A1"].status == AttemptStatus.SUCCEEDED
        assert len(result.state.tasks["T1"].attempt_ids) == 1


def test_recovery_blocks_unverifiable_non_idempotent_action():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        goal = make_goal(root / "workspace")
        state = store.create_run(goal, "LH-UNSAFE")
        task = TaskNode(
            "T1",
            "Append unknown",
            "Append with no observable postcondition",
            status=TaskStatus.RUNNING,
            action=TaskAction("append_file", {"path": "log.txt", "content": "x"}),
            attempt_ids=["T1-A1"],
        )
        state.tasks = {"T1": task}
        state.attempts = {
            "T1-A1": Attempt(
                "T1-A1",
                "T1",
                AttemptStatus.RUNNING,
                action_fingerprint(task.action),
                "key",
                utc_now(),
            )
        }
        state.active_task_id = "T1"
        state.status = RunStatus.INTERRUPTED
        state = store.save(state, event_type="simulated_crash")
        result = LongHorizonController(store).resume(state.run_id)
        assert result.state.status == RunStatus.BLOCKED
        assert result.state.tasks["T1"].status == TaskStatus.BLOCKED
        assert result.state.tasks["T1"].error["type"] == "UnsafeInterruptedAction"


class ReplanModel:
    def __init__(self):
        self.same_failure_counts = []

    def plan(self, state, persist):
        raise AssertionError("existing plan should be used")

    def propose_action(self, state, task, context, action_contract, persist):
        raise AssertionError("task already has an action")

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        self.same_failure_counts.append(same_failure_count)
        replacement = TaskNode(
            "T2",
            "Replacement",
            "Use a different valid path",
            action=TaskAction("write_file", {"path": "answer.txt", "content": "replacement"}),
            completion_criteria=[ValidationSpec("file_contains", {"path": "answer.txt", "text": "replacement"})],
        )
        return ReplanProposal([replacement], {failed_task.task_id: "T2"}, "changed strategy")

    def final_answer(self, state, context, persist):
        return "model final"


def test_controller_replan_supersedes_failed_path():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-REPLAN")
        failed = TaskNode(
            "T1",
            "Bad path",
            "Fail a postcondition",
            action=TaskAction("noop", {"output": "nothing"}),
            completion_criteria=[ValidationSpec("file_exists", {"path": "missing.txt"})],
            retry_policy=RetryPolicy(max_attempts=3, replan_after=1),
        )
        state = save_tasks(store, state, [failed])
        model = ReplanModel()
        result = LongHorizonController(store, model=model).run(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert result.state.tasks["T1"].active is False
        assert result.state.tasks["T1"].superseded_by == "T2"
        assert result.state.tasks["T2"].status == TaskStatus.COMPLETED
        assert result.final_output == "model final"
        assert model.same_failure_counts == [0]


class DelayedActionModel:
    def plan(self, state, persist):
        raise AssertionError("existing graph should be used")

    def propose_action(self, state, task, context, action_contract, persist):
        assert task.action.action_type == "model_action"
        return TaskAction("write_file", {"path": "selected.txt", "content": "selected"})

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        raise AssertionError("delayed action should pass")

    def final_answer(self, state, context, persist):
        return "selected and verified"


def test_controller_asks_model_for_delayed_action_and_audits_selection():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-DELAYED-ACTION")
        task = TaskNode(
            "T1",
            "Select action",
            "Choose a concrete action at execution time",
            action=TaskAction("model_action", {}),
            completion_criteria=[
                ValidationSpec(
                    "file_contains",
                    {"path": "selected.txt", "text": "selected"},
                )
            ],
        )
        state = save_tasks(store, state, [task])
        result = LongHorizonController(store, model=DelayedActionModel()).run(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert result.state.tasks["T1"].action.action_type == "write_file"
        assert (root / "workspace" / "selected.txt").read_text() == "selected"
        selected = [
            event for event in store.event_records(state.run_id)
            if event["type"] == "action_selected"
        ]
        assert selected[0]["data"]["source"] == "rwkv"


def test_resume_continues_replan_after_interrupted_failed_state():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-REPLAN-RESUME")
        failed = TaskNode(
            "T1",
            "Interrupted failed path",
            "Resume through a replacement",
            status=TaskStatus.FAILED,
            action=TaskAction("noop", {"output": "failed"}),
            completion_criteria=[ValidationSpec("file_exists", {"path": "missing.txt"})],
            retry_policy=RetryPolicy(max_attempts=3, replan_after=1),
            attempt_ids=["T1-A1"],
        )
        state.tasks = {"T1": failed}
        state.attempts = {
            "T1-A1": Attempt(
                "T1-A1",
                "T1",
                AttemptStatus.FAILED,
                action_fingerprint(failed.action),
                "key",
                utc_now(),
                ended_at=utc_now(),
            )
        }
        state.status = RunStatus.INTERRUPTED
        state = store.save(state, event_type="simulated_replan_interruption")
        result = LongHorizonController(store, model=ReplanModel()).resume(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert result.state.tasks["T1"].superseded_by == "T2"
        assert any(
            event["type"] == "replan_recovery_started"
            for event in store.event_records(state.run_id)
        )


def test_controller_blocks_action_without_required_postcondition_before_side_effect():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-POSTCONDITION")
        unsafe_plan = TaskNode(
            "T1",
            "Insufficient validation",
            "Must not execute",
            action=TaskAction("write_file", {"path": "unverified.txt", "content": "bad"}),
            completion_criteria=[ValidationSpec("action_succeeded", {})],
        )
        state = save_tasks(store, state, [unsafe_plan])
        result = LongHorizonController(store).run(state.run_id)
        assert result.state.status == RunStatus.BLOCKED
        assert result.state.tasks["T1"].error["type"] == "MissingRequiredPostcondition"
        assert not (root / "workspace" / "unverified.txt").exists()


def test_replan_rejects_replacement_dependency_cycle_without_mutating_graph():
    old = TaskNode("T1", "Old", "Failed old path", status=TaskStatus.FAILED)
    replacement = TaskNode(
        "T2",
        "Replacement",
        "Invalid replacement dependency",
        dependencies=["T1"],
    )
    graph = TaskGraph({"T1": old})
    graph.add_tasks([replacement])
    with pytest.raises(TaskGraphError, match="replacement"):
        graph.supersede("T1", "T2")
    assert graph.tasks["T1"].active is True
    assert graph.tasks["T1"].superseded_by is None


class EmptyFinalModel:
    def plan(self, state, persist):
        raise AssertionError

    def propose_action(self, state, task, context, action_contract, persist):
        raise AssertionError

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        raise AssertionError

    def final_answer(self, state, context, persist):
        return ""


def test_empty_final_output_never_marks_run_completed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-EMPTY-FINAL")
        node = TaskNode(
            "T1",
            "Write artifact",
            "Write verified artifact",
            action=TaskAction("write_file", {"path": "x.txt", "content": "x"}),
            completion_criteria=[ValidationSpec("file_content", {"path": "x.txt", "expected_content": "x"})],
        )
        state = save_tasks(store, state, [node])
        with pytest.raises(ValueError, match="final model output is empty"):
            LongHorizonController(store, model=EmptyFinalModel()).run(state.run_id)
        assert store.load(state.run_id).status == RunStatus.INTERRUPTED


class RecordingClient:
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def text_completion(self, prompt, max_tokens=768, stop=None):
        with self.lock:
            self.calls.append((get_llm_temperature(), get_llm_seed(), prompt))
        return type("Response", (), {"content": '"schema_version":"test.v1"}'})()


def test_model_invoker_persists_request_temperature_and_seed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-TEMP")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = RecordingClient()
        result = ModelInvoker(client=client).invoke_json(
            "prompt",
            request_type="replan",
            task_id="T1",
            state=state,
            persist=persist,
            generation=2,
            seed=17,
        )
        assert result.payload == {"schema_version": "test.v1"}
        assert client.calls[0][:2] == (0.36, 17)
        loaded = store.load(state.run_id)
        assert loaded.temp_decisions[-1].temperature == 0.36
        assert loaded.temp_decisions[-1].outcome == "ok"
        assert [event["type"] for event in store.event_records(state.run_id)][-2:] == [
            "model_request_started",
            "model_request_returned",
        ]


def test_request_temperature_context_is_isolated_between_threads():
    client = RecordingClient()
    invoker = ModelInvoker(client=client)
    threads = [
        threading.Thread(
            target=invoker.invoke_json,
            kwargs={"prompt": "strict", "request_type": "evidence_extract", "task_id": "A", "seed": 1},
        ),
        threading.Thread(
            target=invoker.invoke_json,
            kwargs={"prompt": "explore", "request_type": "alternative_generation", "task_id": "B", "seed": 2},
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted((temperature, seed) for temperature, seed, _ in client.calls) == [(0.02, 1), (0.32, 2)]
    assert get_llm_seed() is None


def test_model_invoker_out_of_run_audit_captures_goal_exchange():
    trace = []
    client = RecordingClient()
    ModelInvoker(client=client, audit_hook=trace.append).invoke_json(
        "goal prompt",
        request_type="goal_parse",
        task_id="GOAL",
        seed=91,
    )
    assert [item["type"] for item in trace] == [
        "model_request_started",
        "model_request_returned",
    ]
    assert trace[0]["prompt"] == "goal prompt"
    assert trace[0]["seed"] == 91
    assert trace[1]["output"] == '"schema_version":"test.v1"}'


class SequencePlanClient:
    def __init__(self):
        self.calls = []
        self.outputs = [
            '"schema_version":"long-horizon.goal.v1","tasks":[]}',
            '"schema_version":"long-horizon.plan.v1","tasks":[{'
            '"task_id":"T1","title":"Write","description":"Write file",'
            '"dependencies":[],"goal_criteria":["GC1"],"required":true,"priority":50,'
            '"action":{"type":"write_file","arguments":{"path":"x.txt","content":"x"}},'
            '"completion_criteria":[{"kind":"file_contains","parameters":{"path":"x.txt","text":"x"},"required":true}],'
            '"retry_policy":{"max_attempts":2,"replan_after":2}}]}'
        ]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_llm_temperature(), prompt))
        return type("Response", (), {"content": self.outputs.pop(0)})()


class SequenceGoalClient:
    def __init__(self):
        six = [
            {"id": f"C{index}", "description": f"criterion {index}", "required": True}
            for index in range(1, 7)
        ]
        self.outputs = [
            json.dumps(
                {
                    "schema_version": "long-horizon.goal-proposal.v1",
                    "objective": "too granular",
                    "constraints": [],
                    "success_criteria": six,
                }
            ),
            json.dumps(
                {
                    "schema_version": "long-horizon.goal-proposal.v1",
                    "objective": "compact",
                    "constraints": [],
                    "success_criteria": [
                        {
                            "id": "C1",
                            "description": "one observable outcome",
                            "required": True,
                        }
                    ],
                }
            ),
        ]
        self.calls = []

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_llm_temperature(), prompt))
        return type("Response", (), {"content": self.outputs.pop(0)})()


def test_goal_parser_repairs_over_granular_criteria_at_same_temperature():
    with tempfile.TemporaryDirectory() as directory:
        client = SequenceGoalClient()
        goal, decision = LongHorizonModel(
            ModelInvoker(client=client)
        ).parse_goal("Create one verified artifact", directory)
        assert goal.objective == "compact"
        assert [item.criterion_id for item in goal.success_criteria] == ["GC1"]
        assert [temperature for temperature, _ in client.calls] == [0.03, 0.03]
        assert "PROTOCOL CORRECTION" in client.calls[1][1]
        assert decision.attempt == 2


def test_model_plan_repairs_contract_once_without_raising_temperature():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-PLAN-REPAIR")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = SequencePlanClient()
        tasks = LongHorizonModel(ModelInvoker(client=client), action_contract="{}").plan(state, persist)
        assert [task.task_id for task in tasks] == ["T1"]
        assert [temperature for temperature, _ in client.calls] == [0.18, 0.18]
        assert "PROTOCOL CORRECTION" in client.calls[1][1]
        assert [item.outcome for item in state.temp_decisions] == ["contract_error", "ok"]


class SequenceActionClient:
    def __init__(self):
        self.calls = []
        self.outputs = [
            '"schema_version":"long-horizon.action-choice.v1",'
            '"task_id":"T1","action_type":"write_file"}',
            '"schema_version":"long-horizon.action.v1",'
            '"action":{"type":"write_file","arguments":{'
            '"path":"result.txt","content":"verified"}}}',
            '"schema_version":"long-horizon.verification-design.v1",'
            '"completion_criteria":[{"kind":"file_content","parameters":{'
            '"path":"result.txt","expected_content":"verified"},"required":true}]}',
        ]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_llm_temperature(), prompt))
        return type("Response", (), {"content": self.outputs.pop(0)})()


def test_model_action_pipeline_separates_choice_arguments_and_verification():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-ACTION-PIPELINE")
        task = TaskNode(
            "T1",
            "Write result",
            "Write verified text to result.txt",
            goal_criteria=["GC1"],
            action=TaskAction("model_action", {}),
        )

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = SequenceActionClient()
        harness = ActionHarness()
        model = LongHorizonModel(ModelInvoker(client=client), harness=harness)
        context = WorkingMemoryBuilder().build(state, task)
        proposal = model.propose_action(
            state,
            task,
            context,
            harness.action_contract(),
            persist,
        )

        assert proposal.action == TaskAction(
            "write_file", {"path": "result.txt", "content": "verified"}
        )
        assert [item.kind for item in proposal.completion_criteria] == ["file_content"]
        assert [temperature for temperature, _ in client.calls] == [0.05, 0.05, 0.03]
        assert "ACTION TYPE CATALOG" in client.calls[0][1]
        assert "SELECTED ACTION CONTRACT" in client.calls[1][1]
        assert "ALLOWED VERIFIER CONTRACT" in client.calls[2][1]


class ReselectingFailureModel:
    def __init__(self):
        self.analysis_calls = 0
        self.cross_checks = 0

    def plan(self, state, persist):
        raise AssertionError("existing plan should be used")

    def propose_action(self, state, task, context, action_contract, persist):
        return ActionProposal(
            TaskAction(
                "write_file",
                {"path": "result.txt", "content": "correct"},
            ),
            [
                ValidationSpec(
                    "file_content",
                    {"path": "result.txt", "expected_content": "correct"},
                )
            ],
        )

    def analyze_failure(
        self,
        state,
        failed_task,
        context,
        persist,
        *,
        same_failure_count,
    ):
        self.analysis_calls += 1
        return FailureAnalysisProposal("reselect_action", "the concrete value is wrong")

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        raise AssertionError("action reselection should recover without graph replan")

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
        self.cross_checks += 1
        return task.action.arguments.get("content") == "correct", "checked against Goal"

    def final_answer(self, state, context, persist):
        return "corrected and verified"


def test_rwkv_failure_analysis_reselects_action_instead_of_blind_retry():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-RESELECT")
        task = TaskNode(
            "T1",
            "Write exact result",
            "Write the correct value",
            goal_criteria=["GC1"],
            action=TaskAction(
                "write_file",
                {"path": "result.txt", "content": "wrong"},
            ),
            completion_criteria=[
                ValidationSpec(
                    "file_content",
                    {"path": "result.txt", "expected_content": "wrong"},
                )
            ],
        )
        state = save_tasks(store, state, [task])
        model = ReselectingFailureModel()
        result = LongHorizonController(store, model=model).run(state.run_id)
        assert result.state.status == RunStatus.COMPLETED
        assert (root / "workspace" / "result.txt").read_text() == "correct"
        assert len(result.state.tasks["T1"].attempt_ids) == 2
        assert model.analysis_calls == 1
        assert model.cross_checks == 2
        assert any(
            event["type"] == "action_reselection_scheduled"
            for event in store.event_records(state.run_id)
        )


def test_replan_candidate_rejects_reused_ids_and_replacement_self_dependency():
    with tempfile.TemporaryDirectory() as directory:
        state = RunState(
            "LH-REPLAN-CONTRACT",
            make_goal(Path(directory) / "workspace"),
        )
        state.tasks = {
            "T1": TaskNode(
                "T1",
                "Failed",
                "Failed task",
                status=TaskStatus.FAILED,
            )
        }
        with pytest.raises(ModelProtocolError, match="reuses existing task ids"):
            LongHorizonModel._validate_replan_candidate(
                state,
                "T1",
                [TaskNode("T1", "Reuse", "Invalid reuse")],
                {"T1": "T1"},
            )
        with pytest.raises(TaskGraphError, match="replacement"):
            LongHorizonModel._validate_replan_candidate(
                state,
                "T1",
                [
                    TaskNode(
                        "T2",
                        "Replacement",
                        "Invalid self dependency through supersede",
                        dependencies=["T1"],
                    )
                ],
                {"T1": "T2"},
            )
