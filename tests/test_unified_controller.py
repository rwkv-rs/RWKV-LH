from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass, replace
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionDefinition, ActionHarness, ActionResult
from rwkv_lh.model import LongHorizonModel, ModelProtocolError
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import (
    ActionStatus,
    CausalEventDraft,
    ModelEvent,
    RunStatus,
    TaskAction,
)
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

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        if not self.outputs:
            raise AssertionError("unexpected model request")
        return Response(self.outputs.pop(0))


def call(name: str, **arguments):
    return {"function": name, "params": arguments}


def choose(name: str):
    return {"function": "select_tool", "params": {"name": name}}


def settings(tool_disclosure_mode: str = "full") -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode=tool_disclosure_mode,
    )


def build(
    tmp_path: Path,
    calls: list[dict | str],
    *,
    harness: ActionHarness | None = None,
    max_transitions: int = 30,
    max_actions: int | None = None,
    min_actions: int = 0,
    tool_disclosure_mode: str = "full",
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    selected_harness = harness or ActionHarness(sandbox_commands=False)
    client = QueueClient(calls)
    session = ModelSession(
        client,
        settings=settings(tool_disclosure_mode),
    )
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
        max_actions=max_actions,
        min_actions=min_actions,
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


def test_native_search_text_flows_through_controller_observation(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call(
                "search_text",
                pattern="TODO|FIXME",
                mode="regex",
                path=".",
            ),
            call("final_answer", text="Found one TODO and one FIXME."),
        ],
    )
    (workspace / "src.py").write_text(
        "# TODO: implement\n# FIXME: validate\n",
        encoding="utf-8",
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    action = result.state.actions["A00001"]
    assert action.action_type == "search_text"
    observation = json.loads(action.result["output"])
    assert [item["line_number"] for item in observation["matches"]] == [1, 2]
    assert "TODO" in client.prompts[1]
    assert "FIXME" in client.prompts[1]


def test_min_actions_rejects_premature_final_in_same_worker(tmp_path: Path) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call("final_answer", text="premature"),
            call("read_file", path="evidence.txt"),
            call("final_answer", text="observed evidence"),
        ],
        max_actions=1,
        min_actions=1,
    )
    (workspace / "evidence.txt").write_text("evidence", encoding="utf-8")

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "observed evidence"
    assert len(result.state.actions) == 1
    assert result.state.protocol_rejections == 1
    assert "Do not finalize yet" in client.prompts[1]


def test_progressive_disclosure_selects_then_exposes_one_tool_schema(
    tmp_path: Path,
) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            choose("write_file"),
            call("write_file", path="hello.txt", content="hello"),
            choose("final_answer"),
            call("final_answer", text="Created hello.txt."),
        ],
        tool_disclosure_mode="progressive",
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text() == "hello"
    assert len(client.prompts) == 4

    selection_prompt = client.prompts[0]
    system, user = selection_prompt.split("\n\nUser:", 1)
    assert "write_file" not in system
    assert "final_answer" not in system
    assert '"name":"write_file"' in user
    assert '"parameters"' not in user

    write_prompt = client.prompts[1]
    assert "System: Tools" not in write_prompt
    assert '"selected_operation":"write_file"' in write_prompt
    assert '"required":["path","content"]' in write_prompt
    assert write_prompt.count('"selected_tool_contract"') == 1
    assert '"selected_operation":"read_file"' not in write_prompt

    next_selection_prompt = client.prompts[2]
    assert "System: Tools" not in next_selection_prompt
    assert '"required":["path","content"]' not in next_selection_prompt
    assert '"recent_exact_action_records"' in next_selection_prompt
    assert '"operation": "write_file"' in next_selection_prompt
    assert '"action_result_projection_version": "action-result-decision-state.v1"' in next_selection_prompt
    assert "Deterministic recent controller event summary" not in next_selection_prompt
    assert '"event_type":"action_result"' not in next_selection_prompt

    final_prompt = client.prompts[3]
    assert "System: Tools" not in final_prompt
    assert '"selected_operation":"final_answer"' in final_prompt
    assert '"required":["text"]' in final_prompt
    assert '"required":["path","content"]' not in final_prompt

    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("tool_selection_accepted") == 2
    assert event_types.count("tool_schema_disclosed") == 2


def test_action_result_decision_projection_is_bounded_and_marks_prefix_incomplete() -> None:
    output = "x" * (LongHorizonModel._RESULT_OUTPUT_MAX_CHARS + 17)
    projected = LongHorizonModel._project_action_result(
        {
            "action_type": "read_file",
            "success": True,
            "outcome_type": "success",
            "output": output,
            "artifacts": [{"path": "large.txt", "sha256": "a" * 64}],
            "evidence": [{"record": "duplicate full evidence"}],
            "metadata": {
                "complete": True,
                "truncated": False,
                "next_start_byte": None,
                "observed_tokens": 7000,
                "chunk": {"content_digest": "b" * 64},
            },
        }
    )

    assert projected["output"] == output[: LongHorizonModel._RESULT_OUTPUT_MAX_CHARS]
    assert "artifacts" not in projected
    assert "evidence" not in projected
    assert "action_type" not in projected
    assert projected["metadata"] == {
        "complete": False,
        "truncated": True,
        "next_start_byte": None,
        "observed_tokens": 7000,
        "source_complete": True,
        "source_truncated": False,
        "projection_truncated": True,
        "original_output_chars": len(output),
        "retained_output_chars": LongHorizonModel._RESULT_OUTPUT_MAX_CHARS,
    }


def test_progressive_argument_rejection_reuses_disclosed_schema_without_reselection(
    tmp_path: Path,
) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            choose("write_file"),
            call("write_file", path="x.txt", content="x", invented=True),
            call("write_file", path="x.txt", content="x"),
            choose("final_answer"),
            call("final_answer", text="done"),
        ],
        tool_disclosure_mode="progressive",
    )

    result = controller.run("RUN")

    assert result.state.protocol_rejections == 1
    assert (workspace / "x.txt").read_text() == "x"
    assert len(client.prompts) == 5
    retry_prompt = client.prompts[2]
    assert "protocol_rejection" in retry_prompt
    assert '"schema_already_disclosed":true' in retry_prompt
    assert (
        '"rejected_arguments":{"content":"x","invented":true,"path":"x.txt"}'
        in retry_prompt
    )
    assert '"selected_operation_schema"' not in retry_prompt
    assert retry_prompt.count('"selected_tool_contract"') == 1
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("tool_selection_accepted") == 2


def test_progressive_terminal_budget_discloses_only_final_schema(
    tmp_path: Path,
) -> None:
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            choose("write_file"),
            call("write_file", path="partial.txt", content="partial"),
            call("final_answer", text="Stopped after the transition budget."),
        ],
        max_transitions=1,
        tool_disclosure_mode="progressive",
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert (workspace / "partial.txt").read_text() == "partial"
    assert len(client.prompts) == 3
    terminal_prompt = client.prompts[2]
    assert '"selected_operation":"final_answer"' in terminal_prompt
    assert '"required":["text"]' in terminal_prompt
    assert '"required":["path","content"]' not in terminal_prompt


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


def test_contract_graph_v2_resume_without_supervisor_fails_closed_before_action(
    tmp_path: Path,
) -> None:
    controller, store, _, client, _ = build(
        tmp_path,
        [call("final_answer", text="must not execute")],
    )
    state = store.load("RUN")
    store.save(
        state,
        causal_event=CausalEventDraft.create(
            "run_started",
            {
                "architecture": "strong-planner-reviewer-rwkv-contract-graph.v2",
                "online_task_graph": True,
                "parallel_rwkv_atoms": True,
                "result_capsules_only": True,
                "reviewer": True,
                "resumed": False,
                "supersedes_terminal_event_id": "",
            },
            subject_id=state.run_id,
            cause_id=state.causal_order[-1],
        ),
    )

    result = controller.resume("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert client.prompts == []
    assert any(
        event.event_type == "supervisor_configuration_missing"
        for event in result.state.causal_records.values()
    )


def test_progressive_parameter_retry_rolls_over_after_rejection_event_exceeds_budget(
    tmp_path: Path,
) -> None:
    controller, store, _, client, model = build(
        tmp_path,
        [
            choose("read_file"),
            call("read_file"),
            call("read_file", path="input.txt"),
        ],
        tool_disclosure_mode="progressive",
    )
    state = store.load("RUN")
    with pytest.raises(ModelProtocolError) as rejected:
        model.next_command(
            state,
            controller._persist,
            max_output_tokens=64,
        )
    assert rejected.value.selected_operation == "read_file"
    checkpoint = state.model_states[state.action_lane_checkpoint_id]
    model.session.settings = replace(
        model.session.settings,
        max_model_len=(
            checkpoint.token_count
            + 64
            + model.session.settings.context_safety_margin
            + model.session.settings.bos_token_count
        ),
    )
    event = ModelEvent(
        event_type="protocol_rejection",
        event_id="EV-budget-retry",
        scope_id="LANE:ACTION",
        payload={
            "selected_operation": "read_file",
            "error": "path is required",
            "rejected_arguments": {"wrong": "value"},
        },
    )

    decision = model.next_command(
        state,
        controller._persist,
        event=event,
        max_output_tokens=64,
    )

    assert decision.command.name == "read_file"
    assert decision.command.arguments["path"] == "input.txt"
    assert state.rollovers
    assert len(client.prompts) == 3
    retry_prompt = client.prompts[-1]
    assert '"required":["path"]' in retry_prompt
    assert '"event_type":"protocol_rejection"' in retry_prompt
    assert '"error":"path is required"' in retry_prompt
    assert '"rejected_arguments":{"wrong":"value"}' in retry_prompt
    assert '"selected_operation":"read_file"' in retry_prompt
    assert decision.decision.visible_event_ids == (event.event_id,)
    rollover = state.rollovers[next(reversed(state.rollovers))]
    assert rollover.retained_event_ids == (event.event_id,)


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


def test_third_identical_read_only_success_enters_terminal_path(tmp_path: Path) -> None:
    controller, _, _, client, _ = build(
        tmp_path,
        [
            call("list_directory", path="."),
            call("list_directory", path="."),
            call("list_directory", path="."),
            call("final_answer", text="Stopped the repeated read loop."),
        ],
        max_transitions=20,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.INTERRUPTED
    assert len(result.state.actions) == 3
    assert result.final_output == "Stopped the repeated read loop."
    assert len(client.prompts) == 4
    terminal = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_interrupted"
    ]
    assert terminal[-1].payload["reason"] == "identical_success_budget_exhausted"


def test_second_identical_idempotent_mutation_forces_completed_final(
    tmp_path: Path,
) -> None:
    value = {"project": "Orion", "doubled_count": 14}
    controller, _, workspace, client, _ = build(
        tmp_path,
        [
            call("write_json", path="report.json", value=value),
            call("write_json", path="report.json", value=value),
            call("final_answer", text="Created report.json once."),
        ],
        max_actions=4,
    )

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert result.final_output == "Created report.json once."
    assert len(result.state.actions) == 2
    assert json.loads((workspace / "report.json").read_text()) == value
    boundary = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "idempotent_mutation_repeat_boundary"
    ]
    assert len(boundary) == 1
    assert boundary[0].payload["identical_result_count"] == 2
    assert "do not repeat the operation" in client.prompts[-1]


def test_first_idempotent_noop_does_not_hide_remaining_atom_work(
    tmp_path: Path,
) -> None:
    controller, _, workspace, _, _ = build(
        tmp_path,
        [
            call("make_directory", path="existing"),
            call("write_file", path="existing/result.txt", content="done"),
            call("final_answer", text="Created the requested result."),
        ],
        max_actions=3,
    )
    (workspace / "existing").mkdir()

    result = controller.run("RUN")

    assert result.state.status == RunStatus.COMPLETED
    assert len(result.state.actions) == 2
    assert (workspace / "existing/result.txt").read_text() == "done"
    assert not any(
        event.event_type == "idempotent_mutation_repeat_boundary"
        for event in result.state.causal_records.values()
    )


class CrashAfterRepeatBoundaryController(LongHorizonController):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.crash_after_repeat_boundary = True

    def _persist(self, state, event_type, event, *, subject_id=None):
        super()._persist(
            state,
            event_type,
            event,
            subject_id=subject_id,
        )
        if (
            event_type == "idempotent_mutation_repeat_boundary"
            and self.crash_after_repeat_boundary
        ):
            self.crash_after_repeat_boundary = False
            raise CrashAfterEffect("process lost after committed repeat boundary")


def test_idempotent_mutation_repeat_boundary_recovers_without_third_write(
    tmp_path: Path,
) -> None:
    value = {"project": "Orion", "doubled_count": 14}
    original, store, workspace, client, model = build(
        tmp_path,
        [
            call("write_json", path="report.json", value=value),
            call("write_json", path="report.json", value=value),
            call("final_answer", text="Recovered after the committed boundary."),
        ],
        max_actions=4,
    )
    controller = CrashAfterRepeatBoundaryController(
        store,
        model=model,
        harness=original.harness,
        max_actions=4,
    )

    with pytest.raises(CrashAfterEffect):
        controller.run("RUN")

    crashed = store.load("RUN")
    assert crashed.status == RunStatus.RUNNING
    assert len(crashed.actions) == 2
    assert crashed.causal_records[crashed.causal_order[-1]].event_type == (
        "idempotent_mutation_repeat_boundary"
    )

    resumed = controller.run("RUN")

    assert resumed.state.status == RunStatus.COMPLETED
    assert resumed.final_output == "Recovered after the committed boundary."
    assert len(resumed.state.actions) == 2
    assert json.loads((workspace / "report.json").read_text()) == value
    assert "do not repeat the operation" in client.prompts[-1]


def test_external_evidence_fingerprint_ignores_per_action_projection_id() -> None:
    action = SimpleNamespace(
        action_type="connector_lookup",
        arguments={"operation": "package_release", "query": "requests"},
    )

    def result(action_id: str) -> ActionResult:
        external = {
            "action_id": action_id,
            "route_id": "ROUTE-stable",
            "request_digest": "digest-stable",
            "status": "evidence_committed",
            "records": [{"evidence_record_id": "E-stable"}],
        }
        return ActionResult(
            "connector_lookup",
            True,
            output=json.dumps(external, sort_keys=True),
            metadata={"external_evidence": external},
        )

    first = LongHorizonController._observation_fingerprint(
        action, result("A00001")
    )
    second = LongHorizonController._observation_fingerprint(
        action, result("A00002")
    )

    assert first == second


def test_external_evidence_model_projection_is_bounded_and_keeps_structured_fact() -> None:
    long_text = "x" * 10_000
    full = {
        "success": True,
        "outcome_type": "success",
        "action_type": "connector_lookup",
        "output": long_text,
        "evidence": [
            {
                "evidence_record_id": "E-1",
                "source_object": {
                    "source_object_id": "pypi:requests",
                    "source_object_type": "pypi_release",
                },
                "snapshot_digest": "a" * 64,
                "url": "https://pypi.org/pypi/requests/json",
                "structured_fields": {"info": {"version": "2.34.2"}},
                "exact_spans": [
                    {"span_id": "SPAN-1", "text": long_text, "locator": {}}
                ],
            },
            {
                "evidence_record_id": "E-2",
                "source_object": {
                    "source_object_id": "pypi:requests",
                    "source_object_type": "pypi_release",
                },
                "snapshot_digest": "a" * 64,
                "url": "https://pypi.org/pypi/requests/json",
                "structured_fields": {"info": {"version": "2.34.2"}},
                "exact_spans": [
                    {"span_id": "SPAN-2", "text": long_text, "locator": {}}
                ],
            },
        ],
        "metadata": {
            "external_evidence": {
                "action_id": "A00001",
                "route_id": "ROUTE-1",
                "request_digest": "digest-1",
                "status": "evidence_committed",
                "records": [{"large_duplicate": long_text}],
            },
            "network_policy": {"allowed": True},
        },
    }

    projected = LongHorizonController._model_action_result(full)
    encoded = json.dumps(projected, ensure_ascii=False)

    assert len(encoded) < 4_000
    assert projected["evidence"][0]["structured_fields"]["info"]["version"] == "2.34.2"
    assert len(projected["evidence"]) == 1
    projected_span = projected["evidence"][0]["exact_spans"][0]
    assert len(projected_span["text"]) == 512
    assert projected_span["text"] == long_text[:512]
    assert projected_span["source_span_id"] == "SPAN-1"
    assert projected_span["text_sha256"] == hashlib.sha256(
        long_text[:512].encode()
    ).hexdigest()
    assert projected_span["source_text_chars"] == len(long_text)
    assert projected_span["projection"] == {
        "source_offset_start": 0,
        "source_offset_end": 512,
        "document_start_char": 0,
        "document_end_char": 512,
        "complete_source_span": False,
    }
    assert full["evidence"][0]["exact_spans"][0]["text"] == long_text
    assert "A00001" not in encoded
    assert projected["metadata"]["projection_complete"] is False


def test_external_evidence_projection_selects_query_relevant_later_chunk() -> None:
    prefix = "unrelated metadata " * 80
    relevant = "registered context before RWKV Reinventing RNNs for the Transformer Era"
    full_span = prefix + relevant + (" trailing" * 100)
    source = {
        "source_object_id": "crossref:response-1",
        "source_object_type": "crossref_works",
    }
    records = []
    for index, text in enumerate(("first chunk", "second chunk", full_span), 1):
        records.append(
            {
                "evidence_record_id": f"E-{index}",
                "source_object": source,
                "snapshot_digest": "b" * 64,
                "url": "https://api.crossref.org/works?q=rwkv",
                "structured_fields": {"status": "ok"},
                "exact_spans": [
                    {
                        "span_id": f"SPAN-{index}",
                        "text": text,
                        "locator": {
                            "start_char": (index - 1) * 6000,
                            "end_char": (index - 1) * 6000 + len(text),
                        },
                    }
                ],
            }
        )
    full = {
        "success": True,
        "outcome_type": "success",
        "action_type": "connector_lookup",
        "output": "authoritative output remains unchanged",
        "evidence": records,
        "metadata": {
            "external_evidence": {
                "route_id": "ROUTE-1",
                "request_digest": "digest-1",
                "status": "evidence_committed",
            },
            "network_policy": {"allowed": True},
        },
    }
    original = deepcopy(full)

    projected = LongHorizonController._model_action_result(
        full,
        arguments={"query": "RWKV Reinventing RNNs for the Transformer Era"},
    )

    assert len(projected["evidence"]) == 1
    span = projected["evidence"][0]["exact_spans"][0]
    assert span["source_span_id"] == "SPAN-3"
    assert "RWKV Reinventing RNNs for the Transformer Era" in span["text"]
    assert span["projection"]["source_offset_start"] > 0
    assert projected["evidence_projection"]["selection_protocol"] == (
        "query-exact-source-chunk.v2"
    )
    assert full == original


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
    assert not any(item.event_type.startswith("supervisor_") for item in records)


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
