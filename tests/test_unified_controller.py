from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionDefinition, ActionHarness, ActionResult
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ActionStatus, RunStatus, TaskAction
from rwkv_lh.store import LongHorizonStore


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"


class QueueClient:
    model_name = "test-rwkv"

    def __init__(self, calls: list[dict | str]):
        self.outputs = [
            item if isinstance(item, str) else json.dumps(item, separators=(",", ":"))
            for item in calls
        ]
        self.prompts: list[str] = []
        self._ensemble_output = ""
        self._ensemble_remaining = 0

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        pair_count = prompt.count("\n\nAssistant: ```json\n") - 1
        if pair_count <= 1:
            if self._ensemble_remaining:
                raise AssertionError("incomplete ensemble request group")
            if not self.outputs:
                raise AssertionError("unexpected model request")
            return Response(self.outputs.pop(0))
        if not self._ensemble_remaining:
            if not self.outputs:
                raise AssertionError("unexpected model request")
            self._ensemble_output = self.outputs.pop(0)
            self._ensemble_remaining = 3
        self._ensemble_remaining -= 1
        return Response(self._ensemble_output)


def call(name: str, **arguments):
    return {"function": name, "params": arguments}


def settings() -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
    )


def build(
    tmp_path: Path,
    calls: list[dict | str],
    *,
    harness: ActionHarness | None = None,
    max_transitions: int = 30,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    selected_harness = harness or ActionHarness(sandbox_commands=False)
    client = QueueClient(calls)
    session = ModelSession(client, settings=settings())
    model = LongHorizonModel(session, harness=selected_harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(
        "Complete the requested workspace change.",
        str(workspace),
        constraints=["Operate only inside the workspace"],
    )
    state = store.create_run(goal, "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=selected_harness,
        max_transitions=max_transitions,
    )
    return controller, store, workspace, client, model


def test_direct_write_then_final_has_one_session_and_one_action(tmp_path: Path) -> None:
    controller, store, workspace, client, _ = build(
        tmp_path,
        [
            call("write_file", path="hello.txt", content="hello"),
            call("final_answer", text="Created hello.txt."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created hello.txt."
    assert (workspace / "hello.txt").read_text() == "hello"
    assert len(result.state.actions) == 1
    action = result.state.actions["A00001"]
    assert action.status == ActionStatus.SUCCEEDED
    assert action.result is not None and action.result["success"] is True
    assert action.artifact_refs
    assert result.state.artifact_revisions["hello.txt"][-1].action_id == action.action_id
    reloaded = store.load("RUN")
    assert reloaded.actions["A00001"].status == ActionStatus.SUCCEEDED
    assert reloaded.actions["A00001"].result == action.result
    assert {checkpoint.lane_id for checkpoint in result.state.model_states.values()} == {
        "LANE:ACTION"
    }
    assert len(client.prompts) == 2
    assert "action_result" in client.prompts[1]


def test_read_observation_is_visible_before_producer_action(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call("read_file", path="input.txt"),
            call("write_json", path="report.json", value={"project": "Orion", "count": 7}),
            call("final_answer", text="Done"),
        ],
    )
    (workspace / "input.txt").write_text("project=Orion\ncount=7\n")
    result = controller.run("RUN")
    assert json.loads((workspace / "report.json").read_text()) == {
        "project": "Orion",
        "count": 7,
    }
    assert [item.action_type for item in result.state.actions.values()] == [
        "read_file",
        "write_json",
    ]
    assert "project=Orion" in client.prompts[1]


def test_two_independent_reads_are_not_collapsed_by_task_boundary(tmp_path: Path) -> None:
    controller, _, workspace, _, _ = build(
        tmp_path,
        [
            call("read_file", path="a.txt"),
            call("read_file", path="b.txt"),
            call("write_file", path="combined.txt", content="alpha\nbeta\n"),
            call("final_answer", text="Combined"),
        ],
    )
    (workspace / "a.txt").write_text("alpha\n")
    (workspace / "b.txt").write_text("beta\n")
    result = controller.run("RUN")
    assert (workspace / "combined.txt").read_text() == "alpha\nbeta\n"
    assert [action.action_type for action in result.state.actions.values()] == [
        "read_file", "read_file", "write_file"
    ]


def test_protocol_rejection_executes_no_action_and_same_session_recovers(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            "not-json",
            call("write_file", path="ok.txt", content="ok"),
            call("final_answer", text="Recovered"),
        ],
    )
    result = controller.run("RUN")
    assert result.state.protocol_rejections == 1
    assert len(result.state.actions) == 1
    assert (workspace / "ok.txt").read_text() == "ok"
    assert "protocol_rejection" in client.prompts[1]
    assert "selected_operation_schema" not in client.prompts[1]


def test_operation_specific_schema_is_direct_and_exact(tmp_path: Path) -> None:
    _, _, _, _, model = build(tmp_path, [call("final_answer", text="x")])
    definitions = {item["name"]: item for item in model.direct_definitions()}
    assert "write_json" in definitions
    assert definitions["write_json"]["parameters"]["required"] == ["path", "value"]
    assert definitions["write_json"]["parameters"]["additionalProperties"] is False
    assert not {"lh_tasks", "lh_task_done", "lh_goal_done", "lh_task_call"} & set(definitions)


def test_argument_alias_normalizer_only_moves_explicit_values(tmp_path: Path) -> None:
    controller, _, workspace, _, _ = build(
        tmp_path,
        [
            call("write_json", path="x.json", content='{"a":1}'),
            call("final_answer", text="done"),
        ],
    )
    result = controller.run("RUN")
    action = next(iter(result.state.actions.values()))
    assert action.wire_arguments["content"] == '{"a":1}'
    assert action.arguments["value"] == {"a": 1}
    assert json.loads((workspace / "x.json").read_text()) == {"a": 1}


def test_unknown_action_parameter_is_rejected_before_harness(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call("write_file", path="x.txt", content="x", invented=True),
            call("write_file", path="x.txt", content="x"),
            call("final_answer", text="done"),
        ],
    )
    result = controller.run("RUN")
    assert result.state.protocol_rejections == 1
    assert len(result.state.actions) == 1
    assert (workspace / "x.txt").read_text() == "x"
    assert '"selected_operation":"write_file"' in client.prompts[1]
    assert '"required":["path","content"]' in client.prompts[1]
    assert "invented" in client.prompts[1]


class CountingHarness(ActionHarness):
    def __init__(self):
        super().__init__(sandbox_commands=False)
        self.executions: list[str] = []

    def execute(self, action: TaskAction, goal) -> ActionResult:
        self.executions.append(action.action_type)
        return super().execute(action, goal)


def test_each_accepted_direct_action_executes_harness_exactly_once(tmp_path: Path) -> None:
    harness = CountingHarness()
    controller, _, _, _, _ = build(
        tmp_path,
        [
            call("write_file", path="a.txt", content="a"),
            call("read_file", path="a.txt"),
            call("final_answer", text="done"),
        ],
        harness=harness,
    )
    result = controller.run("RUN")
    assert harness.executions == ["write_file", "read_file"]
    assert len(result.state.actions) == 2


class CrashAfterEffect(RuntimeError):
    rwkv_lh_process_loss = True


class CrashOnceHarness(ActionHarness):
    def __init__(self):
        super().__init__(sandbox_commands=False)
        self.crashed = False

    def execute(self, action: TaskAction, goal) -> ActionResult:
        result = super().execute(action, goal)
        if action.action_type == "write_file" and not self.crashed:
            self.crashed = True
            raise CrashAfterEffect("crash after write")
        return result


class CrashAppendOnceHarness(ActionHarness):
    def __init__(self):
        super().__init__(sandbox_commands=False)
        self.executions = 0

    def execute(self, action: TaskAction, goal) -> ActionResult:
        if action.action_type == "append_file":
            self.executions += 1
        result = super().execute(action, goal)
        if action.action_type == "append_file" and self.executions == 1:
            raise CrashAfterEffect("crash after append")
        return result


def test_idempotent_running_action_recovers_without_new_model_action(tmp_path: Path) -> None:
    harness = CrashOnceHarness()
    controller, store, workspace, _, _ = build(
        tmp_path,
        [
            call("write_file", path="safe.txt", content="once"),
            call("final_answer", text="recovered"),
        ],
        harness=harness,
    )
    with pytest.raises(CrashAfterEffect):
        controller.run("RUN")
    crashed = store.load("RUN")
    assert crashed.active_action_id == "A00001"
    resumed = controller.run("RUN")
    assert resumed.state.status == RunStatus.COMPLETED
    assert len(resumed.state.actions) == 1
    assert (workspace / "safe.txt").read_text() == "once"


def test_non_idempotent_running_action_is_not_replayed_after_crash(tmp_path: Path) -> None:
    harness = CrashAppendOnceHarness()
    controller, store, workspace, _, _ = build(
        tmp_path,
        [
            call("append_file", path="events.log", content="once\n"),
            call("final_answer", text="append outcome was interrupted"),
        ],
        harness=harness,
    )
    with pytest.raises(CrashAfterEffect):
        controller.run("RUN")
    resumed = controller.run("RUN")
    assert harness.executions == 1
    assert (workspace / "events.log").read_text() == "once\n"
    action = store.load("RUN").actions["A00001"]
    assert action.status == ActionStatus.INTERRUPTED
    assert action.result is not None and action.result["outcome_type"] == "interrupted"
    assert resumed.state.status == RunStatus.COMPLETED


def test_completed_resume_is_a_read_only_noop(tmp_path: Path) -> None:
    controller, store, _, client, _ = build(
        tmp_path,
        [call("final_answer", text="nothing needed")],
    )
    first = controller.run("RUN")
    revision = first.state.revision
    second = controller.resume("RUN")
    assert second.transitions == 0
    assert second.state.revision == revision
    assert second.final_output == "nothing needed"
    assert len(client.prompts) == 1


def test_identical_failure_budget_is_stable_without_task_replacement(tmp_path: Path) -> None:
    calls = [call("read_file", path="missing.txt") for _ in range(5)]
    calls.append(call("final_answer", text="Could not read missing.txt."))
    controller, store, _, _, _ = build(tmp_path, calls, max_transitions=20)
    result = controller.run("RUN")
    assert result.state.status == RunStatus.INTERRUPTED
    assert len(result.state.actions) == 5
    assert len(result.state.failure_budgets) == 1
    assert next(iter(result.state.failure_budgets.values())) == 5
    assert store.load("RUN").failure_budgets == result.state.failure_budgets
    assert result.final_output == "Could not read missing.txt."


def test_final_text_is_delivered_byte_exact_from_rwkv_field(tmp_path: Path) -> None:
    text = "  中文 Final\nline two\n"
    controller, _, _, _, _ = build(tmp_path, [call("final_answer", text=text)])
    result = controller.run("RUN")
    decision = result.state.decisions[result.state.final_decision_id]
    assert result.final_output == text
    assert json.loads(decision.raw_output)["params"]["text"] == result.final_output


def test_terminal_budget_still_requests_output_from_same_action_lane(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call("write_file", path="partial.txt", content="partial"),
            call("final_answer", text="Stopped after the transition budget."),
        ],
        max_transitions=1,
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.INTERRUPTED
    assert result.final_output == "Stopped after the transition budget."
    assert (workspace / "partial.txt").exists()
    assert len(client.prompts) == 2
    assert {item.lane_id for item in result.state.model_states.values()} == {"LANE:ACTION"}


def test_causal_event_chain_is_contiguous_across_model_action_observation_final(tmp_path: Path) -> None:
    controller, _, _, _, _ = build(
        tmp_path,
        [
            call("write_file", path="x.txt", content="x"),
            call("final_answer", text="done"),
        ],
    )
    state = controller.run("RUN").state
    records = [state.causal_records[item] for item in state.causal_order]
    assert [item.sequence for item in records] == list(range(1, len(records) + 1))
    assert all(
        current.parent_id == previous.event_id
        for previous, current in zip(records, records[1:])
    )
    assert {item.event_type for item in records} >= {
        "run_created", "run_started", "action_session_started",
        "model_call_accepted", "action_started", "action_finished",
        "action_observation_appended", "run_completed",
    }


def test_custom_registered_action_is_exposed_and_executed_directly(tmp_path: Path) -> None:
    observed: list[dict] = []

    def handler(goal, arguments):
        observed.append(dict(arguments))
        return ActionResult("custom_lookup", True, output="value=7")

    harness = ActionHarness(
        sandbox_commands=False,
        actions={
            "custom_lookup": (
                ActionDefinition(
                    "custom_lookup",
                    "Look up one explicit key.",
                    True,
                    False,
                    True,
                    5.0,
                    {"key": {"type": "string"}},
                    required_arguments=("key",),
                ),
                handler,
            )
        },
    )
    controller, _, _, _, model = build(
        tmp_path,
        [call("custom_lookup", key="alpha"), call("final_answer", text="7")],
        harness=harness,
    )
    result = controller.run("RUN")
    assert observed == [{"key": "alpha"}]
    assert "custom_lookup" in {item["name"] for item in model.direct_definitions()}
    assert result.final_output == "7"
