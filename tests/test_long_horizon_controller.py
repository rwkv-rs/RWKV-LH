import json
import sys
import tempfile
import threading
from pathlib import Path

import pytest

from rwkv_lh.runtime import RWKVOutcomeUnknownError
from rwkv_lh.runtime.sampling import get_request_sampling, get_request_temperature
from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionDefinition, ActionHarness, ActionResult
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import (
    ActionProposal,
    CrossValidationDecision,
    FailureAnalysisProposal,
    GoalObligationProposal,
    LongHorizonModel,
    ModelInvoker,
    ModelProtocolError,
    ReplanProposal,
)
from rwkv_lh.schema import (
    ArtifactRecord,
    Attempt,
    AttemptStatus,
    CriterionEvidence,
    CriterionEvidenceStatus,
    GoalCriterion,
    GoalObligationState,
    GoalObligationStatus,
    GoalState,
    MemoryEntry,
    RetryPolicy,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationSpec,
    ValidationResult,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError
from rwkv_lh.token_budget import get_token_count


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


def passing_criterion_decision(state, task, action_result=None):
    claims = []
    for criterion_id in task.satisfies_criteria:
        claims.append(
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
                        "goal_quote": "Execute",
                        "value": str((action_result or {}).get("output") or ""),
                    },
                    "transforms": [],
                },
            }
        )
    return CrossValidationDecision(True, "fixture semantic pass", claims)


class ProofPassModel:
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
        return passing_criterion_decision(state, task, action_result)

    def final_answer(self, state, context, persist):
        return "fixture verified completion"


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
        result = LongHorizonController(store, model=ProofPassModel()).run(state.run_id)
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
        result = LongHorizonController(store, model=ProofPassModel()).run(state.run_id)
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
        result = LongHorizonController(store, model=ProofPassModel()).resume(state.run_id)
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


class ReplanModel(ProofPassModel):
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


class DelayedActionModel(ProofPassModel):
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


class EmptyFinalModel(ProofPassModel):
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
        assert [item.request_type for item in state.temp_decisions] == [
            "task_decomposition"
        ]
        normalizations = [
            event
            for event in store.event_records(state.run_id)
            if event["type"] == "model_protocol_normalized"
        ]
        assert normalizations[-1]["data"]["field"] == "task_graph.nodes"
        assert normalizations[-1]["data"]["input_payload"]["task_graph"]["nodes"] == (
            normalizations[-1]["data"]["normalized_payload"]["tasks"]
        )
        ledger = next(
            item
            for item in store.event_records(state.run_id)
            if item["type"] == "goal_obligation_ledger_created"
        )
        assert ledger["data"]["missing_criterion_ids"] == []


class RegisteredTaskGraphWithoutVersionClient:
    def text_completion(self, prompt, max_tokens=768, stop=None):
        return type(
            "Response",
            (),
            {
                "content": json.dumps(
                    {
                        "task_graph": {
                            "tasks": [
                                {
                                    "local_id": "step_1",
                                    "title": "Inspect input",
                                    "description": "Read the scoped input",
                                    "dependencies": [],
                                    "required": True,
                                    "priority": 50,
                                    "advances_criteria": ["GC1"],
                                    "satisfies_criteria": ["GC1"],
                                    "retry_policy": {"max_attempts": 3},
                                }
                            ]
                        }
                    }
                )
            },
        )()


def test_round23_registered_task_graph_without_version_closes_protocol_identity():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-R23-PLAN")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        tasks = LongHorizonModel(
            ModelInvoker(client=RegisteredTaskGraphWithoutVersionClient()),
            action_contract="{}",
        ).plan(state, persist)

        assert [task.task_id for task in tasks] == ["step_1"]
        event = next(
            item
            for item in store.event_records(state.run_id)
            if item["type"] == "model_protocol_normalized"
        )["data"]
        assert event["transformations"] == [
            "task_graph_tasks_to_canonical_tasks",
            "registered_plan_envelope_implies_v2",
        ]
        assert event["normalized_payload"]["tasks"] == (
            event["input_payload"]["task_graph"]["tasks"]
        )
        assert event["controller_semantic_fields_generated"] is False
        assert event["input_payload_digest"] != event["normalized_payload_digest"]


class ParserFailureThenValidPlanClient:
    def __init__(self):
        self.calls = []
        self.outputs = [
            "not a JSON object",
            json.dumps(
                {
                    "schema_version": "long-horizon.plan.v2",
                    "tasks": [
                        {
                            "local_id": "step_1",
                            "title": "Inspect input",
                            "description": "Read the scoped input",
                            "dependencies": [],
                            "required": True,
                            "priority": 50,
                            "advances_criteria": ["GC1"],
                            "satisfies_criteria": ["GC1"],
                            "retry_policy": {"max_attempts": 3},
                        }
                    ],
                }
            ),
        ]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append(prompt)
        return type("Response", (), {"content": self.outputs.pop(0)})()


def test_round23_plan_json_parser_failure_reaches_same_type_correction_attempt():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-R23-PLAN-RETRY")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = ParserFailureThenValidPlanClient()
        tasks = LongHorizonModel(
            ModelInvoker(client=client), action_contract="{}"
        ).plan(state, persist)

        assert [task.task_id for task in tasks] == ["step_1"]
        assert len(client.calls) == 2
        assert "Failure stage: json_extraction_or_normalization" in client.calls[1]
        assert "not a JSON object" not in client.calls[1]
        assert [decision.attempt for decision in state.temp_decisions] == [1, 2]


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


class InitialObligationPlanClient:
    def __init__(self):
        self.calls = []
        self.outputs = [{
            "schema_version": "long-horizon.plan.v2",
            "tasks": [
                {
                    "local_id": "inspect",
                    "title": "Inspect input",
                    "description": "Read the input before producing output",
                    "dependencies": [],
                    "required": True,
                    "priority": 50,
                    "advances_criteria": ["GC1"],
                    "satisfies_criteria": [],
                    "retry_policy": {"max_attempts": 3},
                }
            ],
        }]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_request_temperature(), prompt))
        payload = self.outputs.pop(0)
        return type("Response", (), {"content": json.dumps(payload)})()


class ObligationReplanClient:
    def __init__(self, payload):
        self.calls = []
        self.outputs = [payload, payload]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_request_temperature(), prompt))
        return type(
            "Response", (), {"content": json.dumps(self.outputs.pop(0))}
        )()


def obligation_capsule():
    return {
        "schema_version": "long-horizon.goal-obligation-capsule.v1",
        "goal_digest": "fixture",
        "unresolved_criteria": [
            {"criterion_id": "GC1", "description": "finish", "required": True}
        ],
        "active_tasks": [],
        "artifacts": [],
        "criterion_evidence": [],
        "workspace_manifest": {"entries": []},
        "unchanged_failed_verifier_tasks": [
            {
                "task_id": "T0",
                "semantic_signature": "fixture-failed-semantic",
                "failure_fingerprint": "fixture-failure",
                "failure_class": "model_written_same_target_lineage",
            }
        ],
    }


def test_structural_plan_is_preserved_without_synchronous_obligation_expansion():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-OBLIGATION")

        def persist(current, event_type, event):
            saved = store.save(current, event_type=event_type, event=event)
            current.revision = saved.revision
            current.updated_at = saved.updated_at

        client = InitialObligationPlanClient()
        tasks = LongHorizonModel(
            ModelInvoker(client=client), action_contract="{}"
        ).plan(state, persist)

        assert [task.task_id for task in tasks] == ["inspect"]
        assert tasks[0].satisfies_criteria == []
        assert [temperature for temperature, _ in client.calls] == [0.18]
        assert [item.request_type for item in state.temp_decisions] == [
            "task_decomposition",
        ]
        events = store.event_records(state.run_id)
        ledger = next(
            item for item in events if item["type"] == "goal_obligation_ledger_created"
        )
        assert ledger["data"]["missing_criterion_ids"] == ["GC1"]
        assert not any(
            item.request_type == "goal_obligation_planning"
            for item in state.temp_decisions
        )


def test_goal_obligation_replan_rejects_existing_id_without_mutating_state():
    bad = {
        "schema_version": "long-horizon.obligation-replan.v1",
        "reason": "replace history",
        "new_tasks": [
            {
                "local_id": "T1",
                "title": "Overwrite",
                "description": "Attempt to replace the existing task",
                "dependencies": [],
                "required": True,
                "priority": 50,
                "advances_criteria": ["GC1"],
                "satisfies_criteria": ["GC1"],
                "retry_policy": {"max_attempts": 3},
            }
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("LH-OBLIGATION-BAD", make_goal(root / "workspace"))
        state.tasks = {
            "T1": TaskNode(
                "T1",
                "Inspect",
                "Completed history",
                status=TaskStatus.COMPLETED,
            )
        }
        client = ObligationReplanClient(bad)

        with pytest.raises(ModelProtocolError, match="reuse existing task ids"):
            LongHorizonModel(
                ModelInvoker(client=client), action_contract="{}"
            ).plan_goal_obligations(
                state,
                obligation_capsule(),
                lambda *_args: None,
            )
        assert list(state.tasks) == ["T1"]


def test_goal_obligation_replan_rewrites_existing_and_new_dependencies_stably():
    supplemental = {
        "schema_version": "long-horizon.obligation-replan.v1",
        "reason": "finish unresolved evidence",
        "new_tasks": [
            {
                "local_id": "prepare",
                "title": "Prepare result",
                "description": "Prepare evidence after inspection",
                "dependencies": ["T1"],
                "required": True,
                "priority": 50,
                "advances_criteria": ["GC1"],
                "satisfies_criteria": [],
                "retry_policy": {"max_attempts": 3},
            },
            {
                "local_id": "verify",
                "title": "Establish result",
                "description": "Directly establish GC1",
                "dependencies": ["prepare"],
                "required": True,
                "priority": 50,
                "advances_criteria": ["GC1"],
                "satisfies_criteria": ["GC1"],
                "retry_policy": {"max_attempts": 3},
            },
        ],
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("LOCAL-IDS", make_goal(root / "workspace"))
        state.tasks = {
            "T1": TaskNode(
                "T1",
                "Inspect",
                "Completed input observation",
                status=TaskStatus.COMPLETED,
            )
        }
        client = ObligationReplanClient(supplemental)
        proposal = LongHorizonModel(
            ModelInvoker(client=client), action_contract="{}"
        ).plan_goal_obligations(
            state,
            obligation_capsule(),
            lambda *_args: None,
        )
        materialized, mapping, _ = TaskGraph.materialize_model_tasks(
            proposal.tasks,
            existing_ids=state.tasks,
            next_sequence=2,
        )

        assert mapping == {"prepare": "T2", "verify": "T3"}
        assert materialized[0].dependencies == ["T1"]
        assert materialized[1].dependencies == ["T2"]
        assert [temperature for temperature, _ in client.calls] == [0.18]
        assert "STATE CAPSULE" in client.calls[0][1]
        assert "unchanged_failed_verifier_tasks" in client.calls[0][1]
        assert "runtime rejects the entire proposal" in client.calls[0][1]


def test_goal_obligation_replan_accepts_semantic_minimum_without_filling_metadata():
    supplemental = {
        "new_tasks": [
            {
                "local_id": "verify",
                "title": "Establish result",
                "description": "Directly establish GC1",
                "dependencies": ["T1"],
                "required": True,
                "priority": 50,
                "advances_criteria": ["GC1"],
                "satisfies_criteria": ["GC1"],
                "retry_policy": {"max_attempts": 3},
            }
        ]
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("MINIMAL-OBLIGATION", make_goal(root / "workspace"))
        state.tasks = {
            "T1": TaskNode(
                "T1",
                "Inspect",
                "Completed input observation",
                status=TaskStatus.COMPLETED,
            )
        }
        proposal = LongHorizonModel(
            ModelInvoker(client=ObligationReplanClient(supplemental)),
            action_contract="{}",
        ).plan_goal_obligations(
            state,
            obligation_capsule(),
            lambda *_args: None,
        )

        assert [task.task_id for task in proposal.tasks] == ["verify"]
        assert proposal.reason == ""
        assert proposal.reason_provided is False
        assert proposal.schema_version_provided is False


def test_goal_obligation_replan_rejects_unknown_top_level_field():
    payload = {
        "new_tasks": [],
        "task_complete": True,
    }
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("MINIMAL-OBLIGATION-EXTRA", make_goal(root / "workspace"))
        client = ObligationReplanClient(payload)

        with pytest.raises(
            ModelProtocolError,
            match="requires new_tasks; only optional schema_version and reason are allowed",
        ):
            LongHorizonModel(
                ModelInvoker(client=client), action_contract="{}"
            ).plan_goal_obligations(
                state,
                obligation_capsule(),
                lambda *_args: None,
            )


@pytest.mark.parametrize(
    ("metadata", "message"),
    [
        ({"schema_version": "wrong"}, "invalid obligation replan schema"),
        ({"reason": {"text": "not a string"}}, "optional obligation reason must be a string"),
    ],
)
def test_goal_obligation_replan_validates_optional_metadata(metadata, message):
    valid_task = {
        "local_id": "verify",
        "title": "Establish result",
        "description": "Directly establish GC1",
        "dependencies": [],
        "required": True,
        "advances_criteria": ["GC1"],
        "satisfies_criteria": ["GC1"],
    }
    payload = {"new_tasks": [valid_task], **metadata}
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("MINIMAL-OBLIGATION-METADATA", make_goal(root / "workspace"))

        with pytest.raises(ModelProtocolError, match=message):
            LongHorizonModel(
                ModelInvoker(client=ObligationReplanClient(payload)),
                action_contract="{}",
            ).plan_goal_obligations(
                state,
                obligation_capsule(),
                lambda *_args: None,
            )


class PersistentObligationLifecycleModel(ProofPassModel):
    def __init__(self):
        self.capsules = []
        self.final_calls = 0

    def plan(self, state, persist):
        return [
            TaskNode(
                "inspect",
                "Create preparation",
                "Produce an observed dependency before resolving Goal evidence",
                action=TaskAction(
                    "write_file", {"path": "input.txt", "content": "observed"}
                ),
                completion_criteria=[
                    ValidationSpec(
                        "file_content",
                        {"path": "input.txt", "expected_content": "observed"},
                    )
                ],
            )
        ]

    def plan_goal_obligations(self, state, capsule, persist):
        self.capsules.append(capsule)
        return GoalObligationProposal(
            [
                TaskNode(
                    "produce_result",
                    "Produce verified result",
                    "Use completed T1 observations to establish GC1",
                    dependencies=["T1"],
                    goal_criteria=["GC1"],
                    satisfies_criteria=["GC1"],
                    action=TaskAction(
                        "write_file",
                        {"path": "result.txt", "content": "verified"},
                    ),
                    completion_criteria=[
                        ValidationSpec(
                            "file_content",
                            {
                                "path": "result.txt",
                                "expected_content": "verified",
                            },
                        )
                    ],
                )
            ],
            "completed observation now supports an evidence-producing task",
        )

    def final_answer(self, state, context, persist):
        self.final_calls += 1
        return "fixture verified completion"


def test_persistent_goal_obligation_runs_base_plan_before_rwkv_extension():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(
            make_goal(root / "workspace"),
            "PERSISTENT-GOAL-OBLIGATION",
        )
        model = PersistentObligationLifecycleModel()

        result = LongHorizonController(store, model=model).run(state.run_id)

        assert result.state.status == RunStatus.COMPLETED
        assert model.final_calls == 1
        assert len(model.capsules) == 1
        capsule = model.capsules[0]
        assert capsule["goal_digest"] == state.goal.digest
        assert [item["criterion_id"] for item in capsule["unresolved_criteria"]] == [
            "GC1"
        ]
        assert capsule["active_tasks"][0]["status"] == "completed"
        assert capsule["active_tasks"][0]["output_refs"]
        assert capsule["workspace_manifest"]["entry_count"] == 1
        assert capsule["projection"]["capsule_tokens"] <= 5000
        actual_capsule_tokens = get_token_count(
            json.dumps(
                capsule,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        assert capsule["projection"]["capsule_tokens"] == actual_capsule_tokens
        obligation = result.state.goal_obligation
        assert obligation is not None
        assert obligation.status == GoalObligationStatus.RESOLVED
        assert obligation.unresolved_criterion_ids == []
        assert obligation.generation_count == 1
        assert obligation.remaining_budget == 2
        assert obligation.task_ids == ["T2"]
        events = store.event_records(state.run_id)
        types = [item["type"] for item in events]
        assert types.index("task_completed") < types.index(
            "goal_obligation_capsule_prepared"
        )
        assert types.index("goal_obligation_capsule_prepared") < types.index(
            "goal_obligation_replan_saved"
        )
        saved = next(
            item for item in events if item["type"] == "goal_obligation_replan_saved"
        )
        assert saved["data"]["local_to_global"] == {"produce_result": "T2"}
        assert saved["data"]["rwkv_reason_provided"] is False
        assert saved["data"]["rwkv_schema_version_provided"] is False


def test_goal_obligation_capsule_is_bounded_without_dropping_task_structure():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        state = RunState("BOUNDED-OBLIGATION-CAPSULE", make_goal(root / "workspace"))
        state.tasks = {
            f"T{index}": TaskNode(
                f"T{index}",
                f"Task {index} " + "title " * 80,
                "long observed task description " * 120,
                status=TaskStatus.COMPLETED,
                goal_criteria=["GC1"],
                output_refs=[f"M-T{index}-A1", f"T{index}-A1-R1"],
            )
            for index in range(1, 65)
        }
        for index in range(1, 41):
            memory_id = f"M-T{index}-A1"
            state.memory_index[memory_id] = MemoryEntry(
                memory_id,
                "action_result",
                f"T{index}",
                "observed output " * 100,
            )
        for index in range(1, 71):
            artifact_id = f"T{index}-A1-R1"
            state.artifacts[artifact_id] = ArtifactRecord(
                artifact_id,
                f"T{min(index, 64)}",
                f"artifact-{index}.txt",
                f"{index:064x}",
                summary="artifact summary " * 80,
            )

        capsule = LongHorizonController(
            LongHorizonStore(root / "state")
        )._goal_obligation_capsule(
            state,
            invalidated_claim_ids=[],
        )

        assert len(capsule["active_task_index"]["rows"]) == 64
        assert len(capsule["active_tasks"]) <= 24
        assert capsule["projection"]["active_task_count"] == 64
        assert capsule["projection"]["excluded_detailed_task_ids"]
        assert capsule["projection"]["capsule_tokens"] <= 5000
        actual_capsule_tokens = get_token_count(
            json.dumps(
                capsule,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
        assert capsule["projection"]["capsule_tokens"] == actual_capsule_tokens
        assert capsule["projection"]["task_text_truncated"] is True
        assert capsule["projection"]["excluded_action_observation_ids"]
        assert capsule["projection"]["excluded_artifact_ids"]


class ExhaustingGoalObligationModel:
    def __init__(self):
        self.obligation_calls = 0

    def plan(self, state, persist):
        return [
            TaskNode(
                "base",
                "Base observation",
                "Complete a base task without claiming Goal evidence",
                action=TaskAction("noop", {"output": "base"}),
                completion_criteria=[ValidationSpec("action_succeeded", {})],
            )
        ]

    def plan_goal_obligations(self, state, capsule, persist):
        self.obligation_calls += 1
        local_id = f"followup_{self.obligation_calls}"
        completed = [
            task.task_id
            for task in state.tasks.values()
            if task.active and task.status == TaskStatus.COMPLETED
        ]
        return GoalObligationProposal(
            [
                TaskNode(
                    local_id,
                    "Observe unresolved criterion",
                    "Advance GC1 without claiming unsupported proof",
                    dependencies=[completed[-1]],
                    goal_criteria=["GC1"],
                    satisfies_criteria=[],
                    action=TaskAction("noop", {"output": local_id}),
                    completion_criteria=[ValidationSpec("action_succeeded", {})],
                )
            ],
            "another observation is needed",
        )


def test_goal_obligation_budget_exhausts_without_controller_generated_claims():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(
            make_goal(root / "workspace"),
            "GOAL-OBLIGATION-BUDGET",
        )
        model = ExhaustingGoalObligationModel()

        result = LongHorizonController(store, model=model).run(state.run_id)

        assert result.state.status == RunStatus.BLOCKED
        assert model.obligation_calls == 3
        obligation = result.state.goal_obligation
        assert obligation is not None
        assert obligation.status == GoalObligationStatus.EXHAUSTED
        assert obligation.remaining_budget == 0
        assert len(obligation.task_ids) == 3
        assert result.state.criterion_claims == {}
        assert result.state.criterion_evidence == {}
        events = store.event_records(state.run_id)
        assert sum(
            item["type"] == "goal_obligation_replan_saved" for item in events
        ) == 3
        assert events[-1]["type"] == "run_blocked"
        assert events[-1]["data"]["reason"] == "unresolved_goal_obligations"


class InvalidGoalObligationModel(ExhaustingGoalObligationModel):
    def plan_goal_obligations(self, state, capsule, persist):
        self.obligation_calls += 1
        raise ModelProtocolError("invalid obligation fixture")


def test_goal_obligation_protocol_error_is_audited_and_fails_closed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(
            make_goal(root / "workspace"),
            "GOAL-OBLIGATION-PROTOCOL",
        )
        model = InvalidGoalObligationModel()

        result = LongHorizonController(store, model=model).run(state.run_id)

        assert result.state.status == RunStatus.BLOCKED
        assert model.obligation_calls == 1
        obligation = result.state.goal_obligation
        assert obligation is not None
        assert obligation.status == GoalObligationStatus.BLOCKED
        assert obligation.remaining_budget == 2
        assert obligation.decision_history[-1]["type"] == "protocol_error"
        events = store.event_records(state.run_id)
        assert any(
            item["type"] == "goal_obligation_capsule_prepared" for item in events
        )
        assert events[-1]["type"] == "model_protocol_blocked"
        assert events[-1]["data"]["phase"] == "goal_obligation_replan"


class SequenceGoalObligationModel:
    def __init__(self, proposals):
        self.proposals = list(proposals)
        self.capsules = []

    def plan_goal_obligations(self, state, capsule, persist):
        self.capsules.append(capsule)
        return self.proposals.pop(0)


def seeded_unchanged_proof_obligation(root: Path):
    harness = ActionHarness()
    workspace = root / "workspace"
    goal = make_goal(workspace)
    (workspace / "result.json").write_text('{"value":1}\n', encoding="utf-8")
    snapshot = harness.workspace_observation_snapshot(goal)
    assert snapshot["cacheable"] is True
    task = TaskNode(
        "T1",
        "Verify result.json",
        "Read result.json to establish GC1",
        status=TaskStatus.COMPLETED,
        goal_criteria=["GC1"],
        satisfies_criteria=["GC1"],
        action=TaskAction("read_json", {"path": "result.json"}),
        completion_criteria=[ValidationSpec("file_exists", {"path": "result.json"})],
        attempt_ids=["T1-A1"],
        insertion_order=1,
    )
    proof_message = (
        "criterion assertion rejected: ProofEvaluationError: actual and expected "
        "share model-written workspace target lineage: ['result.json']"
    )
    attempt = Attempt(
        "T1-A1",
        "T1",
        AttemptStatus.SUCCEEDED,
        action_fingerprint(task.action),
        "fixture:T1",
        utc_now(),
        ended_at=utc_now(),
        validation_results=[
            ValidationResult(
                "criterion_cross_check",
                False,
                False,
                proof_message,
                evidence={
                    "observation_cacheable": True,
                    "protocol_valid": True,
                    "proof_passed": False,
                    "criterion_ids": ["GC1"],
                    "workspace_digest": snapshot["digest"],
                    "witness_catalog_digest": "catalog-1",
                    "witness_bindings": [{"actual": "A", "expected": "E"}],
                    "witness_source_selections": [
                        {"actual_source": "A", "expected_source": "E"}
                    ],
                },
            )
        ],
    )
    store = LongHorizonStore(root / "state")
    state = store.create_run(goal, "UNCHANGED-PROOF-OBLIGATION")
    state.tasks = {task.task_id: task}
    state.attempts = {attempt.attempt_id: attempt}
    state.goal_obligation = GoalObligationState(
        goal.digest,
        unresolved_criterion_ids=["GC1"],
        remaining_budget=3,
    )
    state.status = RunStatus.RUNNING
    state.next_task_sequence = 2
    state = store.save(state, event_type="fixture_seeded")
    return store, state, harness, snapshot["digest"]


def obligation_task(local_id: str, *, duplicate: bool) -> TaskNode:
    return TaskNode(
        local_id,
        "Verify result.json" if duplicate else "Repair result producer",
        (
            "Read result.json to establish GC1"
            if duplicate
            else "Create a different producer correction before establishing GC1"
        ),
        dependencies=["T1"],
        goal_criteria=["GC1"],
        satisfies_criteria=["GC1"],
    )


def test_unchanged_deterministic_proof_replan_rejects_entire_mixed_proposal():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store, state, harness, digest = seeded_unchanged_proof_obligation(root)
        model = SequenceGoalObligationModel(
            [
                GoalObligationProposal(
                    [
                        obligation_task("repeat", duplicate=True),
                        obligation_task("correction", duplicate=False),
                    ],
                    "try both",
                )
            ]
        )
        controller = LongHorizonController(store, model=model, harness=harness)

        extended = controller._advance_goal_obligations(
            state,
            TaskGraph(state.tasks),
            invalidated_claim_ids=[],
        )

        assert extended is True
        assert sorted(state.tasks) == ["T1"]
        assert state.goal_obligation is not None
        assert state.goal_obligation.remaining_budget == 2
        history = state.goal_obligation.decision_history[-1]
        assert history["type"] == "unchanged_deterministic_proof_proposal_suppressed"
        assert history["workspace_digest"] == digest
        assert history["controller_partial_selection"] is False
        assert [item["local_id"] for item in history["proposal_tasks"]] == [
            "repeat",
            "correction",
        ]
        events = store.event_records(state.run_id)
        suppressed = [
            item
            for item in events
            if item["type"]
            == "unchanged_deterministic_proof_obligation_suppressed"
        ]
        assert len(suppressed) == 1
        capsule = model.capsules[0]
        assert capsule["workspace_observation"]["cacheable"] is True
        assert capsule["workspace_observation"]["digest"] == digest
        assert len(capsule["unchanged_failed_verifier_tasks"]) == 1


def test_unchanged_deterministic_proof_feedback_allows_distinct_recovery_task():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store, state, harness, _ = seeded_unchanged_proof_obligation(root)
        model = SequenceGoalObligationModel(
            [
                GoalObligationProposal(
                    [obligation_task("repeat", duplicate=True)], "repeat"
                ),
                GoalObligationProposal(
                    [obligation_task("correction", duplicate=False)], "change strategy"
                ),
            ]
        )
        controller = LongHorizonController(store, model=model, harness=harness)

        assert controller._advance_goal_obligations(
            state, TaskGraph(state.tasks), invalidated_claim_ids=[]
        )
        assert controller._advance_goal_obligations(
            state, TaskGraph(state.tasks), invalidated_claim_ids=[]
        )

        assert sorted(state.tasks) == ["T1", "T2"]
        assert state.tasks["T2"].title == "Repair result producer"
        assert state.goal_obligation is not None
        assert state.goal_obligation.remaining_budget == 1
        feedback = model.capsules[1]["recovery_feedback"]
        assert feedback["type"] == "unchanged_deterministic_proof_proposal_suppressed"
        assert feedback["entire_proposal_rejected"] is True


@pytest.mark.parametrize("changed_workspace", [True, False])
def test_unchanged_deterministic_proof_suppression_fails_closed_on_workspace_snapshot(
    changed_workspace,
):
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store, state, harness, prior_digest = seeded_unchanged_proof_obligation(root)
        if changed_workspace:
            (root / "workspace" / "result.json").write_text(
                '{"value":2}\n', encoding="utf-8"
            )
        else:
            outside = root / "outside.txt"
            outside.write_text("outside\n", encoding="utf-8")
            (root / "workspace" / "link.txt").symlink_to(outside)
        model = SequenceGoalObligationModel(
            [GoalObligationProposal([obligation_task("repeat", duplicate=True)], "retry")]
        )
        controller = LongHorizonController(store, model=model, harness=harness)

        assert controller._advance_goal_obligations(
            state, TaskGraph(state.tasks), invalidated_claim_ids=[]
        )

        assert sorted(state.tasks) == ["T1", "T2"]
        capsule = model.capsules[0]
        if changed_workspace:
            assert capsule["workspace_observation"]["cacheable"] is True
            assert capsule["workspace_observation"]["digest"] != prior_digest
        else:
            assert capsule["workspace_observation"]["cacheable"] is False
            assert capsule["workspace_observation"]["reason"].startswith(
                "symbolic_link_not_cacheable:"
            )
        assert capsule["unchanged_failed_verifier_tasks"] == []
        assert not any(
            item["type"] == "unchanged_deterministic_proof_obligation_suppressed"
            for item in store.event_records(state.run_id)
        )


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


def test_atomic_action_pipeline_keeps_legacy_fallback_and_narrows_g1i_contract():
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
        assert "FIXED COMPACT ACTION CATALOG" in client.calls[0][1]
        assert '"argument_names"' in client.calls[0][1]
        assert client.calls[1][1].startswith("System: Tools: [")
        assert client.calls[1][1].count('"name":"write_file"') == 1
        assert '"name":"read_file"' not in client.calls[1][1]
        assert client.calls[1][1].endswith("Assistant: ```json\n")


class ParserFailureThenRegisteredActionClient:
    def __init__(self):
        self.calls = []
        self.outputs = [
            '"schema_version":"long-horizon.action-choice.v1",'
            '"task_id":"T1","action_type":"write_file"}',
            "not a JSON function call",
            json.dumps(
                {
                    "action": {
                        "type": "write_file",
                        "arguments": {
                            "path": "result.txt",
                            "content": "verified",
                            "overwrite": True,
                            "create_parents": True,
                        },
                    }
                }
            ),
        ]

    def text_completion(self, prompt, max_tokens=768, stop=None):
        self.calls.append((get_request_temperature(), prompt))
        return type("Response", (), {"content": self.outputs.pop(0)})()


def test_round23_tool_parser_failure_retries_and_registered_action_stays_name_bound():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-R23-ACTION")
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

        client = ParserFailureThenRegisteredActionClient()
        harness = ActionHarness()
        proposal = LongHorizonModel(
            ModelInvoker(client=client), harness=harness
        ).propose_action(
            state,
            task,
            WorkingMemoryBuilder().build(state, task),
            harness.action_contract(),
            persist,
        )

        assert proposal.action == TaskAction(
            "write_file",
            {
                "path": "result.txt",
                "content": "verified",
                "overwrite": True,
                "create_parents": True,
            },
        )
        assert len(client.calls) == 3
        assert "Failure stage: json_extraction_or_normalization" in client.calls[2][1]
        assert "not a JSON function call" not in client.calls[2][1]
        event = [
            item
            for item in store.event_records(state.run_id)
            if item["type"] == "model_protocol_normalized"
            and item["data"]["request_type"] == "tool_action"
        ][-1]["data"]
        assert event["transformations"] == ["action_envelope_to_canonical"]
        assert event["selected_action"] == "write_file"
        assert event["controller_semantic_fields_generated"] is False


class ConflictingActionIdentityClient(ParserFailureThenRegisteredActionClient):
    def __init__(self):
        super().__init__()
        conflicting = json.dumps(
            {
                "action": {
                    "type": "read_file",
                    "arguments": {"path": "result.txt"},
                }
            }
        )
        self.outputs = [self.outputs[0], conflicting, conflicting]


def test_round23_action_wrapper_never_rewrites_conflicting_identity():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "state")
        state = store.create_run(make_goal(root / "workspace"), "LH-R23-CONFLICT")
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

        client = ConflictingActionIdentityClient()
        harness = ActionHarness()
        with pytest.raises(ModelProtocolError, match="does not match"):
            LongHorizonModel(
                ModelInvoker(client=client), harness=harness
            ).propose_action(
                state,
                task,
                WorkingMemoryBuilder().build(state, task),
                harness.action_contract(),
                persist,
            )

        assert len(client.calls) == 3
        assert not any(
            item["type"] == "model_protocol_normalized"
            and item["data"].get("request_type") == "tool_action"
            for item in store.event_records(state.run_id)
        )


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
        if task.action.arguments.get("content") != "correct":
            return CrossValidationDecision(False, "checked against Goal", [])
        return passing_criterion_decision(state, task, action_result)

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
                ),
                ValidationSpec("model_cross_check", {}),
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
        return passing_criterion_decision(state, task, action_result)

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


class ProducerCorrectionModel(ProofPassModel):
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


class ObservationGateModel:
    def __init__(self, *, protocol_error_first=False, change_workspace=False):
        self.cross_checks = 0
        self.analysis_calls = 0
        self.protocol_error_first = protocol_error_first
        self.change_workspace = change_workspace

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
        if self.protocol_error_first and self.cross_checks == 1:
            raise ModelProtocolError("invalid validation object")
        return False, "RWKV observed the same unmet criterion"

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
        if self.change_workspace:
            path = Path(state.goal.workspace_root) / "new-evidence.txt"
            path.write_text("changed after first validation", encoding="utf-8")
        return FailureAnalysisProposal("retry_same", "retry the observation")

    def final_answer(self, state, context, persist):
        raise AssertionError("a failed criterion must not complete")


def _run_observation_gate_case(
    root: Path,
    model: ObservationGateModel,
    *,
    harness: ActionHarness | None = None,
    action: TaskAction | None = None,
    explicit_cross_check: bool = False,
):
    workspace = root / "workspace"
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "value.txt").write_text("stable", encoding="utf-8")
    store = LongHorizonStore(root / "state")
    state = store.create_run(make_goal(workspace), "LH-OBSERVATION-GATE")
    criteria = [ValidationSpec("action_succeeded", {})]
    if explicit_cross_check:
        criteria.append(ValidationSpec("model_cross_check", {}))
    task = TaskNode(
        "T1",
        "Inspect exact workspace evidence",
        "Read the same deterministic evidence and let RWKV judge the criterion",
        satisfies_criteria=["GC1"],
        action=action or TaskAction("read_file", {"path": "value.txt"}),
        completion_criteria=criteria,
        retry_policy=RetryPolicy(max_attempts=2, replan_after=99),
    )
    state.tasks = {"T1": task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")
    result = LongHorizonController(
        store,
        model=model,
        harness=harness,
    ).run(state.run_id)
    return store, result


def test_unchanged_failed_observation_reuses_only_prior_rwkv_replan(
):
    explicit_cross_check = True
    with tempfile.TemporaryDirectory() as directory:
        model = ObservationGateModel()
        store, result = _run_observation_gate_case(
            Path(directory),
            model,
            explicit_cross_check=explicit_cross_check,
        )

        assert result.state.status == RunStatus.BLOCKED
        assert model.cross_checks == 1
        assert model.analysis_calls == 1
        lineage = next(iter(result.state.recovery_states.values()))
        assert len(lineage.failed_observations) == 1
        assert lineage.suppressed_cross_check_count == 1
        second = result.state.attempts["T1-A2"]
        cross_check = next(
            item
            for item in second.validation_results
            if item.kind
            == (
                "model_cross_check"
                if explicit_cross_check
                else "criterion_cross_check"
            )
        )
        assert cross_check.passed is False
        assert cross_check.message == "RWKV observed the same unmet criterion"
        assert cross_check.evidence["decision_source"] == "prior_rwkv_replan"
        events = store.event_records(result.state.run_id)
        assert len(
            [
                event
                for event in events
                if event["type"]
                == "unchanged_observation_cross_check_suppressed"
            ]
        ) == 1


def test_workspace_change_forces_a_fresh_rwkv_cross_check():
    with tempfile.TemporaryDirectory() as directory:
        model = ObservationGateModel(change_workspace=True)
        store, result = _run_observation_gate_case(
            Path(directory),
            model,
            explicit_cross_check=True,
        )

        assert result.state.status == RunStatus.BLOCKED
        assert model.cross_checks == 2
        lineage = next(iter(result.state.recovery_states.values()))
        assert len(lineage.failed_observations) == 2
        assert lineage.suppressed_cross_check_count == 0
        assert not any(
            event["type"] == "unchanged_observation_cross_check_suppressed"
            for event in store.event_records(result.state.run_id)
        )


def test_external_or_time_sensitive_action_is_never_observation_cached():
    with tempfile.TemporaryDirectory() as directory:
        definition = ActionDefinition(
            name="inspect_external",
            description="Return an external observation.",
            read_only=True,
            side_effect=False,
            idempotent=True,
            default_timeout=5.0,
            argument_schema={},
        )

        def handler(goal, arguments):
            return ActionResult("inspect_external", True, output="same")

        harness = ActionHarness(
            actions={"inspect_external": (definition, handler)}
        )
        model = ObservationGateModel()
        store, result = _run_observation_gate_case(
            Path(directory),
            model,
            harness=harness,
            action=TaskAction("inspect_external", {}),
            explicit_cross_check=True,
        )

        assert result.state.status == RunStatus.BLOCKED
        assert model.cross_checks == 2
        lineage = next(iter(result.state.recovery_states.values()))
        assert lineage.failed_observations == {}
        assert lineage.suppressed_cross_check_count == 0
        prepared = [
            event
            for event in store.event_records(result.state.run_id)
            if event["type"] == "cross_check_observation_prepared"
        ]
        assert len(prepared) == 2
        assert all(event["data"]["cacheable"] is False for event in prepared)
        assert all(
            event["data"]["uncacheable_reason"]
            == "action_definition_not_cacheable"
            for event in prepared
        )


def test_model_protocol_error_is_not_a_failed_observation_cache_source():
    with tempfile.TemporaryDirectory() as directory:
        model = ObservationGateModel(protocol_error_first=True)
        store, result = _run_observation_gate_case(
            Path(directory),
            model,
            explicit_cross_check=True,
        )

        assert result.state.status == RunStatus.BLOCKED
        assert model.cross_checks == 2
        lineage = next(iter(result.state.recovery_states.values()))
        assert len(lineage.failed_observations) == 1
        assert lineage.suppressed_cross_check_count == 0
        assert not any(
            event["type"] == "unchanged_observation_cross_check_suppressed"
            for event in store.event_records(result.state.run_id)
        )
