"""Round119 v18-P0 fact-integrity regressions.

Covers: observation fingerprint budgets (C1), terminal transport transaction (C2),
and generic capability completion move_file/file_digest/timeout_ms (C3).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness, HarnessError
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.runtime.protocol import RWKVOutcomeUnknownError
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import RunStatus, TaskAction
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
            item = self.outputs.pop(0)
            if item == "<transport-failure>":
                raise RWKVOutcomeUnknownError("connection dropped mid-generation")
            return Response(item)
        if not self._ensemble_remaining:
            if not self.outputs:
                raise AssertionError("unexpected model request")
            item = self.outputs.pop(0)
            if item == "<transport-failure>":
                raise RWKVOutcomeUnknownError("connection dropped mid-generation")
            self._ensemble_output = item
            self._ensemble_remaining = 3
        self._ensemble_remaining -= 1
        return Response(self._ensemble_output)


def call(name: str, **arguments):
    return {"function": name, "params": arguments}


TRANSPORT_FAILURE = "<transport-failure>"


def settings() -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
    )


def build(tmp_path: Path, calls: list[dict | str], *, max_transitions: int = 40):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    harness = ActionHarness(sandbox_commands=False)
    client = QueueClient(calls)
    session = ModelSession(client, settings=settings())
    model = LongHorizonModel(session, harness=harness)
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    goal = model.create_literal_goal(
        "Complete the requested workspace change.",
        str(workspace),
        constraints=["Operate only inside the workspace"],
    )
    store.create_run(goal, "RUN")
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=max_transitions,
    )
    return controller, store, workspace, client


@pytest.fixture(autouse=True)
def no_transport_backoff(monkeypatch):
    monkeypatch.setattr(LongHorizonController, "_transport_backoff", lambda self, attempt: None)


def test_identical_failure_accrues_budget_across_workspace_changes(tmp_path: Path) -> None:
    """M24 regression: the same failure must share one budget key even when
    successful writes keep changing the workspace digest between attempts."""

    calls: list[dict | str] = []
    for index in range(5):
        calls.append(call("write_file", path="draft.txt", content=f"attempt {index}"))
        calls.append(call("read_file", path="missing.txt"))
    calls.append(call("final_answer", text="missing.txt does not exist."))
    controller, store, _, _ = build(tmp_path, calls, max_transitions=40)
    result = controller.run("RUN")
    assert result.state.status == RunStatus.INTERRUPTED
    failed = [a for a in result.state.actions.values() if a.failure_key]
    assert len(failed) == 5
    assert len({a.failure_key for a in failed}) == 1
    assert result.state.failure_budgets[failed[0].failure_key] == 5
    reloaded = store.load("RUN")
    assert reloaded.failure_budgets == result.state.failure_budgets
    assert reloaded.observation_counts == result.state.observation_counts


def test_identical_success_repeat_count_is_visible_to_model(tmp_path: Path) -> None:
    controller, store, _, client = build(
        tmp_path,
        [
            call("list_directory", path="."),
            call("list_directory", path="."),
            call("final_answer", text="Workspace is empty."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    events = [
        event
        for event in result.state.model_events.values()
        if event.event_type == "action_result"
    ]
    counts = {
        event.payload["action_id"]: event.payload["identical_result_count"]
        for event in events
    }
    assert counts == {"A00001": 1, "A00002": 2}
    fingerprints = {
        event.payload["observation_fingerprint"] for event in events
    }
    assert len(fingerprints) == 1
    assert result.state.observation_counts[next(iter(fingerprints))] == 2
    assert '"identical_result_count":2' in client.prompts[-1].replace(" ", "")


def test_transport_outage_lands_in_failed_terminal_state(tmp_path: Path) -> None:
    """M16/M17/M21 regression: an endpoint outage must never leave the run
    in `running`; every exit appends a terminal causal event."""

    calls: list[dict | str] = [TRANSPORT_FAILURE] * 40
    controller, store, _, _ = build(tmp_path, calls)
    result = controller.run("RUN")
    assert result.state.status == RunStatus.FAILED
    assert result.final_output == ""
    terminal = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "run_failed"
    ]
    assert len(terminal) == 1
    assert terminal[0].payload["reason"] == "model_transport_unavailable"
    transport_events = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "model_transport_failure"
    ]
    assert len(transport_events) == 16  # 8 in the main loop + 8 in the terminal path
    reloaded = store.load("RUN")
    assert reloaded.status == RunStatus.FAILED


def test_transient_transport_failure_recovers_and_continues(tmp_path: Path) -> None:
    controller, _, workspace, _ = build(
        tmp_path,
        [
            TRANSPORT_FAILURE,
            call("write_file", path="out.txt", content="ok"),
            call("final_answer", text="Wrote out.txt."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    assert (workspace / "out.txt").read_text() == "ok"
    transport_events = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "model_transport_failure"
    ]
    assert len(transport_events) == 1


def test_move_file_moves_bytes_and_is_non_idempotent(tmp_path: Path) -> None:
    controller, _, workspace, _ = build(
        tmp_path,
        [
            call("write_file", path="logs/app.log", content="line-1\n"),
            call("move_file", source="logs/app.log", destination="archive/app.log"),
            call("final_answer", text="Moved the log."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    assert not (workspace / "logs/app.log").exists()
    assert (workspace / "archive/app.log").read_text() == "line-1\n"
    definition = controller.harness.definition("move_file")
    assert definition.idempotent is False
    assert definition.side_effect is True


def test_file_digest_reports_exact_sha256(tmp_path: Path) -> None:
    controller, _, workspace, _ = build(
        tmp_path,
        [
            call("write_file", path="payload.txt", content="digest me"),
            call("file_digest", path="payload.txt"),
            call("final_answer", text="Digest observed."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    action = result.state.actions["A00002"]
    observed = json.loads(action.result["output"])
    assert observed["sha256"] == hashlib.sha256(b"digest me").hexdigest()
    assert observed["size_bytes"] == len(b"digest me")
    definition = controller.harness.definition("file_digest")
    assert definition.read_only is True
    assert definition.idempotent is True


def test_timeout_ms_is_transparently_converted_to_seconds() -> None:
    harness = ActionHarness(sandbox_commands=False)
    action, trace = harness.normalize_action_with_trace(
        TaskAction(
            "run_command",
            {"argv": ["true"], "timeout_ms": 12000},
        )
    )
    assert action.arguments["timeout"] == 12.0
    assert "timeout_ms" not in action.arguments
    assert "explicit_unit:timeout_ms->timeout_seconds" in trace["transformations"]

    duplicate, trace = harness.normalize_action_with_trace(
        TaskAction(
            "run_command",
            {"argv": ["true"], "timeout_ms": 12000, "timeout": 12.0},
        )
    )
    assert duplicate.arguments["timeout"] == 12.0
    assert "explicit_unit:timeout_ms=duplicate_timeout->omitted" in trace["transformations"]

    with pytest.raises(HarnessError):
        harness.normalize_action_with_trace(
            TaskAction(
                "run_command",
                {"argv": ["true"], "timeout_ms": 12000, "timeout": 10.0},
            )
        )


def test_observation_counts_projection_survives_reload(tmp_path: Path) -> None:
    controller, store, _, _ = build(
        tmp_path,
        [
            call("write_file", path="a.txt", content="a"),
            call("read_file", path="a.txt"),
            call("read_file", path="a.txt"),
            call("final_answer", text="Done."),
        ],
    )
    result = controller.run("RUN")
    assert result.state.status == RunStatus.COMPLETED
    reloaded = store.load("RUN")
    assert reloaded.observation_counts == result.state.observation_counts
    assert max(reloaded.observation_counts.values()) == 2
    assert reloaded.projection_digest == result.state.projection_digest
