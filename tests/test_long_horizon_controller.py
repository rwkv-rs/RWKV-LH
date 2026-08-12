import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from rwkv_lh.runtime import RWKVOutcomeUnknownError
from rwkv_lh.runtime.sampling import get_request_sampling, get_request_temperature
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
    CriterionEvidence,
    CriterionEvidenceStatus,
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
    if tasks and not any(task.satisfies_criteria for task in tasks):
        final_required = next(
            (task for task in reversed(tasks) if task.required),
            tasks[-1],
        )
        final_required.satisfies_criteria = [
            criterion.criterion_id
            for criterion in state.goal.success_criteria
            if criterion.required
        ]
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
            satisfies_criteria=["GC1"],
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
            satisfies_criteria=["GC1"],
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


def test_final_answer_is_returned_without_rule_based_rewriting():
    raw = "  <think>internal</think>\nRWKV final answer\n  "

    class RawFinalClient:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            return type("Response", (), {"content": raw})()

    with tempfile.TemporaryDirectory() as directory:
        state = RunState(
            run_id="RAW-FINAL",
            goal=make_goal(Path(directory) / "workspace"),
        )
        trace = []
        output = LongHorizonModel(
            ModelInvoker(client=RawFinalClient(), audit_hook=trace.append)
        ).final_answer(state, "verified context", lambda *_args: None)

    assert output == raw
    returned = next(item for item in trace if item["type"] == "model_request_returned")
    assert returned["raw_output"] == raw
    assert returned["normalized_visible_output"] == "RWKV final answer"


class RecordingClient:
    def __init__(self):
        self.calls = []
        self.lock = threading.Lock()

    def text_completion(self, prompt, max_tokens=768, stop=None):
        with self.lock:
            self.calls.append((get_request_sampling(), prompt))
        return type("Response", (), {"content": '"schema_version":"test.v1"}'})()


def test_model_invoker_persists_request_sampling_profile():
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
        )
        assert result.payload == {"schema_version": "test.v1"}
        observed = client.calls[0][0]
        assert observed.temperature == 0.36
        assert observed.request_id == result.decision.request_id
        assert observed.task_id == "T1"
        assert observed.lane == "replan"
        loaded = store.load(state.run_id)
        assert loaded.temp_decisions[-1].temperature == 0.36
        assert loaded.temp_decisions[-1].top_p == 1.0
        assert loaded.temp_decisions[-1].top_k == 0
        assert loaded.temp_decisions[-1].seed_supported is False
        assert loaded.temp_decisions[-1].outcome == "ok"
        assert [event["type"] for event in store.event_records(state.run_id)][-3:] == [
            "model_request_started",
            "model_request_returned",
            "model_protocol_parsed",
        ]


def test_request_sampling_and_correlation_context_is_isolated_between_threads():
    client = RecordingClient()
    invoker = ModelInvoker(client=client)
    threads = [
        threading.Thread(
            target=invoker.invoke_json,
            kwargs={"prompt": "strict", "request_type": "evidence_extract", "task_id": "A"},
        ),
        threading.Thread(
            target=invoker.invoke_json,
            kwargs={"prompt": "explore", "request_type": "alternative_generation", "task_id": "B"},
        ),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    observed = sorted(
        (snapshot.temperature, snapshot.task_id, snapshot.lane)
        for snapshot, _ in client.calls
    )
    assert observed == [
        (0.02, "A", "evidence_extract"),
        (0.32, "B", "alternative_generation"),
    ]
    assert len({snapshot.request_id for snapshot, _ in client.calls}) == 2
    assert get_request_sampling().request_id == ""


def test_model_invoker_persists_unknown_generation_outcome():
    class UnknownClient:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            raise RWKVOutcomeUnknownError("response connection was lost")

    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-UNKNOWN")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        with pytest.raises(RWKVOutcomeUnknownError):
            ModelInvoker(client=UnknownClient()).invoke_text(
                "prompt",
                request_type="tool_action",
                task_id="T1",
                state=state,
                persist=persist,
            )

        loaded = store.load(state.run_id)
        assert loaded.temp_decisions[-1].outcome == "unknown"
        assert [event["type"] for event in store.event_records(state.run_id)][-2:] == [
            "model_request_started",
            "model_request_unknown",
        ]


def test_model_invoker_out_of_run_audit_captures_goal_exchange():
    trace = []
    client = RecordingClient()
    ModelInvoker(client=client, audit_hook=trace.append).invoke_json(
        "goal prompt",
        request_type="goal_parse",
        task_id="GOAL",
    )
    assert [item["type"] for item in trace] == [
        "model_request_started",
        "model_request_returned",
        "model_protocol_parsed",
    ]
    assert trace[0]["prompt"] == "goal prompt"
    assert trace[0]["seed_supported"] is False
    assert trace[0]["top_p"] == 1.0
    assert trace[1]["raw_output"] == '"schema_version":"test.v1"}'
    assert trace[1]["normalized_visible_output"] == '"schema_version":"test.v1"}'
    assert trace[2]["parser"] == "extract_json_object"
    assert trace[2]["parsed_payload"] == {"schema_version": "test.v1"}


def test_model_invoker_recovers_only_opted_in_length_truncated_decision():
    class TruncatedDecisionClient:
        def text_completion(self, prompt, max_tokens=768, stop=None):
            return type(
                "Response",
                (),
                {
                    "content": (
                        '"schema_version":"long-horizon.failure-analysis.v1",'
                        '"decision":"replan","reason":"Repeated diagnosis'
                    ),
                    "finish_reason": "length",
                },
            )()

    trace = []
    result = ModelInvoker(
        client=TruncatedDecisionClient(),
        audit_hook=trace.append,
    ).invoke_json(
        "failure prompt",
        request_type="failure_analysis",
        task_id="T1",
        recover_truncated_decision=True,
    )
    assert result.payload["decision"] == "replan"
    assert result.decision.outcome == "protocol_recovered"
    assert [item["type"] for item in trace] == [
        "model_request_started",
        "model_request_returned",
        "model_protocol_parsed",
        "model_protocol_recovered",
    ]
    assert trace[2]["parser"] == "extract_truncated_decision_object"
    assert trace[2]["parsed_payload"] == result.payload


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
        self.calls.append((get_request_temperature(), prompt))
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
        self.calls.append((get_request_temperature(), prompt))
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


class NestedTaskGraphPlanClient:
    def text_completion(self, prompt, max_tokens=768, stop=None):
        return type(
            "Response",
            (),
            {
                "content": json.dumps(
                    {
                        "schema_version": "long-horizon.plan.v2",
                        "task_graph": {
                            "nodes": [
                                {
                                    "local_id": "step_1",
                                    "title": "Write artifact",
                                    "description": "Create the required artifact",
                                    "dependencies": [],
                                    "required": True,
                                    "priority": 50,
                                    "advances_criteria": ["GC1"],
                                    "satisfies_criteria": ["GC1"],
                                    "retry_policy": {"max_attempts": 3},
                                }
                            ],
                            "edges": [],
                        },
                    }
                )
            },
        )()


def test_model_plan_aliases_complete_nested_task_graph_without_semantic_inference():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-NESTED-PLAN")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        tasks = LongHorizonModel(
            ModelInvoker(client=NestedTaskGraphPlanClient()), action_contract="{}"
        ).plan(state, persist)

        assert [task.task_id for task in tasks] == ["step_1"]
        normalizations = [
            event
            for event in store.event_records(state.run_id)
            if event["type"] == "model_protocol_normalized"
        ]
        assert normalizations[-1]["data"]["field"] == "task_graph.nodes"
        assert normalizations[-1]["data"]["input_payload"]["task_graph"]["nodes"] == (
            normalizations[-1]["data"]["normalized_payload"]["tasks"]
        )


class BareTaskPlanClient:
    def __init__(self):
        self.calls = []

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_request_temperature(), prompt))
        return type(
            "Response",
            (),
            {
                "content": json.dumps(
                    {
                        "task_id": "T1",
                        "title": "Inspect input",
                        "description": "Read the scoped input before deriving the result",
                        "dependencies": [],
                        "required": True,
                        "priority": 50,
                        "goal_criteria": ["GC1"],
                        "retry_policy": {
                            "max_attempts": 3,
                            "backoff_seconds": 0.2,
                            "replan_after": 2,
                        },
                    }
                )
            },
        )()


def test_model_plan_safely_recovers_complete_bare_task_envelope():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-PLAN-ENVELOPE")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = BareTaskPlanClient()
        tasks = LongHorizonModel(ModelInvoker(client=client), action_contract="{}").plan(
            state, persist
        )

        assert [task.task_id for task in tasks] == ["T1"]
        assert tasks[0].action.action_type == "model_action"
        assert len(client.calls) == 1
        assert state.temp_decisions[-1].outcome == "protocol_recovered"
        recoveries = [
            event
            for event in store.event_records(state.run_id)
            if event["type"] == "model_protocol_recovered"
        ]
        assert recoveries[-1]["data"] == {
            "request_id": state.temp_decisions[-1].request_id,
            "request_type": "task_decomposition",
            "field": "plan_envelope",
            "reason": "single_complete_task_node",
            "ignored_fields": [],
        }


def test_bare_plan_recovery_rejects_partial_or_unknown_task_objects():
    base = {
        "task_id": "T1",
        "title": "Inspect",
        "description": "Inspect input",
        "dependencies": [],
        "required": True,
        "priority": 50,
        "goal_criteria": ["GC1"],
        "retry_policy": {"max_attempts": 3},
    }
    assert LongHorizonModel._recover_bare_plan_task(
        base, criterion_ids=["GC1"]
    ) is not None
    assert LongHorizonModel._recover_bare_plan_task(
        {key: value for key, value in base.items() if key != "goal_criteria"},
        criterion_ids=["GC1"],
    ) is None
    assert LongHorizonModel._recover_bare_plan_task(
        {**base, "untrusted_extension": True},
        criterion_ids=["GC1"],
    ) is None
    assert LongHorizonModel._recover_bare_plan_task(
        {**base, "arguments": {"path": "input.txt"}},
        criterion_ids=["GC1"],
    ) is None
    assert LongHorizonModel._recover_bare_plan_task(
        base,
        criterion_ids=["GC1", "GC2"],
    ) is None


def test_plan_v2_separates_progress_from_direct_satisfaction_claims():
    tasks = LongHorizonModel._task_nodes(
        [
            {
                "local_id": "inspect",
                "title": "Inspect input",
                "description": "Obtain an intermediate observation",
                "dependencies": [],
                "advances_criteria": ["GC1"],
                "satisfies_criteria": [],
            },
            {
                "local_id": "produce",
                "title": "Produce output",
                "description": "Establish the observable result",
                "dependencies": ["inspect"],
                "advances_criteria": ["GC1"],
                "satisfies_criteria": ["GC1"],
            },
        ]
    )

    assert tasks[0].goal_criteria == ["GC1"]
    assert tasks[0].satisfies_criteria == []
    assert tasks[1].satisfies_criteria == ["GC1"]


class SequenceActionClient:
    def __init__(self):
        self.calls = []
        self.outputs = [
            '"schema_version":"long-horizon.action-choice.v1",'
            '"task_id":"T1","action_type":"write_file"}',
            '{"name":"write_file","arguments":{'
            '"path":"result.txt","content":"verified"}}',
        ]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_request_temperature(), prompt))
        return type("Response", (), {"content": self.outputs.pop(0)})()


class StringArgumentsActionClient(SequenceActionClient):
    def __init__(self):
        super().__init__()
        self.outputs[1] = (
            '{"name":"write_file","arguments":'
            '"{\\"path\\":\\"result.txt\\",\\"content\\":\\"verified\\"}"}'
        )


def test_model_action_pipeline_keeps_choice_and_narrows_g1i_tool_contract():
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
        assert [item.kind for item in proposal.completion_criteria] == [
            "action_succeeded",
            "file_content",
        ]
        assert [temperature for temperature, _ in client.calls] == [0.05, 0.05]
        assert "ACTION TYPE CATALOG" in client.calls[0][1]
        assert client.calls[1][1].startswith("System: Tools: [")
        assert client.calls[1][1].count('"name":"write_file"') == 1
        assert '"name":"read_file"' not in client.calls[1][1]
        assert client.calls[1][1].endswith("Assistant: ```json\n")


def test_model_action_normalizes_stringified_g1i_arguments():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-ACTION-ECHO")
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

        client = StringArgumentsActionClient()
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
        normalizations = [
            event
            for event in store.event_records(state.run_id)
            if event["type"] == "model_protocol_normalized"
        ]
        assert normalizations[-1]["data"]["field"] == "arguments"
        assert normalizations[-1]["data"]["normalization"] == "json_string_to_object"
        assert normalizations[-1]["data"]["input_payload"]["arguments"] == (
            '{"path":"result.txt","content":"verified"}'
        )
        assert normalizations[-1]["data"]["normalized_payload"] == {
            "name": "write_file",
            "arguments": {"path": "result.txt", "content": "verified"},
        }


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


def test_replan_intent_treats_model_ids_as_local_and_rejects_failed_dependency():
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
        LongHorizonModel._validate_replan_intent(
            state,
            "T1",
            [TaskNode("T1", "Local reference", "A local id may repeat a global id")],
        )
        with pytest.raises(ModelProtocolError, match="cannot depend on failed task"):
            LongHorizonModel._validate_replan_intent(
                state,
                "T1",
                [
                    TaskNode(
                        "correction",
                        "Replacement",
                        "Invalid dependency on the failed global task",
                        dependencies=["T1"],
                    )
                ],
            )


def test_intermediate_progress_cannot_cover_goal_without_typed_evidence():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(workspace), "LH-EVIDENCE-BOUNDARY")
        (workspace / "scores.csv").write_text("name,score\na,1\n", encoding="utf-8")
        task = TaskNode(
            "T1",
            "Inspect scores",
            "Read the input as preparation for a later aggregate",
            goal_criteria=["GC1"],
            satisfies_criteria=[],
            action=TaskAction("read_file", {"path": "scores.csv"}),
            completion_criteria=[ValidationSpec("action_succeeded", {})],
        )
        state.tasks = {"T1": task}
        state.status = RunStatus.RUNNING
        state = store.save(state, event_type="plan_saved")

        result = LongHorizonController(store).run(state.run_id)

        assert result.state.tasks["T1"].status == TaskStatus.COMPLETED
        assert result.state.status == RunStatus.BLOCKED
        assert result.state.criterion_evidence == {}
        assert store.event_records(state.run_id)[-1]["data"] == {
            "reason": "required_goal_evidence_missing",
            "criterion_ids": ["GC1"],
        }


class TaskLocalValidationModel:
    def __init__(self):
        self.validated_tasks = []
        self.validation_scopes = []

    def plan(self, state, persist):
        raise AssertionError("persisted graph is used")

    def propose_action(self, state, task, context, action_contract, persist):
        raise AssertionError("actions are already materialized")

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
        self.validated_tasks.append(task.task_id)
        self.validation_scopes.append(context.goal)
        return True, "direct task evidence satisfies the claimed criterion"

    def final_answer(self, state, context, persist):
        return "task-local evidence verified"


def test_semantic_validation_runs_only_for_direct_satisfaction_claims():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(workspace), "LH-TASK-LOCAL")
        (workspace / "input.txt").write_text("source", encoding="utf-8")
        tasks = [
            TaskNode(
                "T1",
                "Read source",
                "Obtain dependency evidence only",
                goal_criteria=["GC1"],
                action=TaskAction("read_file", {"path": "input.txt"}),
                completion_criteria=[ValidationSpec("action_succeeded", {})],
            ),
            TaskNode(
                "T2",
                "Write result",
                "Create the directly verifiable Goal artifact",
                dependencies=["T1"],
                goal_criteria=["GC1"],
                satisfies_criteria=["GC1"],
                action=TaskAction(
                    "write_file", {"path": "result.txt", "content": "source"}
                ),
                completion_criteria=[
                    ValidationSpec(
                        "file_content",
                        {"path": "result.txt", "expected_content": "source"},
                    )
                ],
            ),
        ]
        state.tasks = {task.task_id: task for task in tasks}
        state.status = RunStatus.RUNNING
        state = store.save(state, event_type="plan_saved")
        model = TaskLocalValidationModel()

        result = LongHorizonController(store, model=model).run(state.run_id)

        assert result.state.status == RunStatus.COMPLETED
        assert model.validated_tasks == ["T2"]
        assert all("TASK VALIDATION SCOPE" in scope for scope in model.validation_scopes)
        evidence = list(result.state.criterion_evidence.values())
        assert len(evidence) == 1
        assert evidence[0].owner_task_id == "T2"
        assert evidence[0].status == CriterionEvidenceStatus.VERIFIED


class RepeatingReplanModel:
    def __init__(self):
        self.same_failure_counts = []

    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        self.same_failure_counts.append(same_failure_count)
        replacement = TaskNode(
            "replacement",
            "Equivalent replacement",
            "Repeat the same failing observation",
            action=TaskAction("noop", {"output": "same"}),
            completion_criteria=[ValidationSpec("file_exists", {"path": "missing.txt"})],
            retry_policy=RetryPolicy(max_attempts=3, replan_after=1),
        )
        return ReplanProposal(
            [replacement],
            {failed_task.task_id: "replacement"},
            "same strategy",
        )

    def final_answer(self, state, context, persist):
        raise AssertionError("repeated failures must not complete")


def test_recovery_lineage_survives_replacements_and_exhausts_global_budget():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-LINEAGE")
        failed = TaskNode(
            "T1",
            "Initial failure",
            "Fail with a stable fingerprint",
            satisfies_criteria=["GC1"],
            action=TaskAction("noop", {"output": "same"}),
            completion_criteria=[ValidationSpec("file_exists", {"path": "missing.txt"})],
            retry_policy=RetryPolicy(max_attempts=3, replan_after=1),
        )
        state.tasks = {"T1": failed}
        state.status = RunStatus.RUNNING
        state = store.save(state, event_type="plan_saved")
        model = RepeatingReplanModel()

        result = LongHorizonController(store, model=model).run(state.run_id)

        assert result.state.status == RunStatus.BLOCKED
        assert model.same_failure_counts == [0, 1]
        assert len(result.state.recovery_states) == 1
        lineage = next(iter(result.state.recovery_states.values()))
        assert lineage.remaining_budget == 0
        assert lineage.same_failure_count == 2
        assert len([item for item in lineage.decision_history if item["type"] == "failure"]) == 3
        assert all(
            task.recovery_lineage_id == lineage.lineage_id
            for task in result.state.tasks.values()
        )


class ProducerCorrectionModel:
    def replan(self, state, failed_task, context, persist, *, same_failure_count):
        assert failed_task.subject_task_id == "T1"
        correction = TaskNode(
            "fix_producer",
            "Correct producer output",
            "Replace the invalid producer artifact with the verified value",
            satisfies_criteria=["GC1"],
            action=TaskAction(
                "write_file", {"path": "value.txt", "content": "correct"}
            ),
            completion_criteria=[
                ValidationSpec(
                    "file_content",
                    {"path": "value.txt", "expected_content": "correct"},
                )
            ],
        )
        return ReplanProposal(
            [correction],
            {failed_task.task_id: "fix_producer"},
            "correct the producer",
        )

    def final_answer(self, state, context, persist):
        return "producer corrected"


def test_validation_failure_routes_to_completed_producer_without_mutating_history():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "value.txt").write_text("wrong", encoding="utf-8")
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(workspace), "LH-PRODUCER-ROUTING")
        producer = TaskNode(
            "T1",
            "Produce value",
            "Historical producer event",
            status=TaskStatus.COMPLETED,
            action=TaskAction("write_file", {"path": "value.txt", "content": "wrong"}),
        )
        verifier = TaskNode(
            "T2",
            "Verify producer",
            "Run an independent check against the producer output",
            dependencies=["T1"],
            satisfies_criteria=["GC1"],
            action=TaskAction(
                "check_command",
                {
                    "argv": [
                        sys.executable,
                        "-c",
                        "from pathlib import Path; raise SystemExit(0 if Path('value.txt').read_text() == 'correct' else 1)",
                    ]
                },
            ),
            completion_criteria=[ValidationSpec("command_exit_code", {"expected": 0})],
            retry_policy=RetryPolicy(max_attempts=3, replan_after=1),
        )
        state.tasks = {"T1": producer, "T2": verifier}
        state.criterion_evidence["CE-OLD"] = CriterionEvidence(
            "CE-OLD",
            "GC1",
            CriterionEvidenceStatus.VERIFIED,
            "T1",
            "T1-A1",
        )
        state.status = RunStatus.RUNNING
        state = store.save(state, event_type="plan_saved")

        result = LongHorizonController(
            store,
            model=ProducerCorrectionModel(),
        ).run(state.run_id)

        assert result.state.status == RunStatus.COMPLETED
        assert result.state.tasks["T1"].status == TaskStatus.COMPLETED
        assert result.state.tasks["T1"].active is True
        assert result.state.criterion_evidence["CE-OLD"].status == CriterionEvidenceStatus.INVALIDATED
        lineage = next(iter(result.state.recovery_states.values()))
        assert lineage.subject_task_id == "T1"
        correction_id = result.state.tasks["T2"].superseded_by
        assert correction_id in result.state.tasks
        assert result.state.tasks[correction_id].subject_task_id == "T1"
        assert (workspace / "value.txt").read_text(encoding="utf-8") == "correct"
