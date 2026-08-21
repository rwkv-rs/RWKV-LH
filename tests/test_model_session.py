from __future__ import annotations

import json
from dataclasses import dataclass

import pytest

from rwkv_lh.model_io import (
    FINAL_ANSWER_DEFINITION,
    ModelCommand,
    ModelIOError,
    parse_model_command,
    parse_model_command_with_trace,
    render_bootstrap,
    render_event_append,
    validate_final_answer,
)
from rwkv_lh.model_session import InputBudgetError, ModelSession
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelEvent, ModelLaneKind


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"


class QueueClient:
    model_name = "test-rwkv"

    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        return Response(self.outputs.pop(0))


def settings(max_model_len: int = 16384) -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=max_model_len,
        context_safety_margin=8,
        bos_token_count=1,
    )


@pytest.mark.parametrize(
    "raw",
    [
        '{"function":"read_file","params":{"path":"a.txt"}}',
        '{"name":"read_file","arguments":{"path":"a.txt"}}',
        '{"tool":"read_file","parameters":{"path":"a.txt"}}',
        '{"read_file":{"path":"a.txt"}}',
        '```json\n{"function":"read_file","params":{"path":"a.txt"}}\n```',
    ],
)
def test_common_envelopes_preserve_explicit_operation_and_arguments(raw: str) -> None:
    command, trace = parse_model_command_with_trace(raw)
    assert command == ModelCommand("read_file", {"path": "a.txt"})
    assert trace.normalized_payload == {
        "function": "read_file",
        "params": {"path": "a.txt"},
    }
    assert trace.to_dict()["controller_semantic_fields_generated"] is False


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not-json",
        "[]",
        '{"function":"read_file"}',
        '{"function":"read_file","params":{},"path":"a.txt"}',
        '{"function":"read_file","name":"read_file","params":{}}',
        '{"function":"read_file","params":[],"arguments":{}}',
        '```python\n{"function":"read_file","params":{}}\n```',
        '```json\n{"function":"read_file","params":{}}',
    ],
)
def test_boundary_rejects_ambiguous_or_non_call_shapes(raw: str) -> None:
    with pytest.raises(ModelIOError):
        parse_model_command(raw)


def test_no_historical_task_wrapper_is_normalized() -> None:
    raw = json.dumps(
        {
            "function": "lh_task_call",
            "params": {
                "task_id": "T1",
                "operation": "read_file",
                "operation_args": {"path": "a.txt"},
            },
        },
        separators=(",", ":"),
    )
    command = parse_model_command(raw)
    assert command.name == "lh_task_call"
    assert command.arguments["operation"] == "read_file"
    # The parser only transports explicit bytes; the model rejects this name
    # because it is not registered. It never unwraps it into read_file.


def test_final_answer_requires_one_nonempty_text_field() -> None:
    validate_final_answer(ModelCommand("final_answer", {"text": "done"}))
    with pytest.raises(ModelIOError):
        validate_final_answer(ModelCommand("final_answer", {"text": ""}))
    with pytest.raises(ModelIOError):
        validate_final_answer(ModelCommand("final_answer", {"text": "x", "status": "ok"}))


def test_bootstrap_contains_exact_tool_schema_and_no_selector() -> None:
    definition = {
        "name": "read_file",
        "description": "read",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }
    prompt = render_bootstrap([definition, FINAL_ANSWER_DEFINITION], "do the work")
    assert '"name":"read_file"' in prompt
    assert '"required":["path"]' in prompt
    assert "lh_task_call" not in prompt
    assert "operation_args" not in prompt


def test_event_append_uses_one_generic_observation_envelope() -> None:
    event = ModelEvent(
        event_type="action_result",
        event_id="EV-1",
        scope_id="LANE:ACTION",
        payload={"action_id": "A1", "result": {"success": True}},
    )
    rendered = render_event_append(event)
    assert "action_result" in rendered
    assert "A1" in rendered
    assert "event_id" not in rendered
    assert "scope_id" not in rendered


def test_session_commit_keeps_exact_prompt_replay_lineage() -> None:
    client = QueueClient(['{"function":"read_file","params":{"path":"a.txt"}}'])
    audits: list[dict] = []
    session = ModelSession(client, settings=settings(), audit_hook=audits.append)
    definition = {
        "name": "read_file",
        "description": "read",
        "parameters": {"type": "object", "properties": {}, "required": []},
    }
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read a.txt",
        [definition],
        lane_id="LANE:ACTION",
    )
    candidate = session.generate(checkpoint, max_output_tokens=100)
    command = session.parse(candidate)
    committed = session.commit(candidate, command)
    assert committed.parent_checkpoint_id == checkpoint.checkpoint_id
    assert committed.transcript.endswith(candidate.raw_output)
    assert any(item["type"] == "model_session_candidate_committed" for item in audits)


def test_session_rejects_commit_with_changed_model_command() -> None:
    client = QueueClient(['{"function":"read_file","params":{"path":"a.txt"}}'])
    session = ModelSession(client, settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read",
        [FINAL_ANSWER_DEFINITION],
    )
    candidate = session.generate(checkpoint, max_output_tokens=100)
    with pytest.raises(ModelIOError, match="differs"):
        session.commit(candidate, ModelCommand("read_file", {"path": "b.txt"}))


def test_session_rollback_returns_exact_parent() -> None:
    client = QueueClient(["bad"])
    session = ModelSession(client, settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    candidate = session.generate(checkpoint, max_output_tokens=100)
    assert session.rollback(candidate, error="bad") == checkpoint


def test_session_append_preserves_same_lane() -> None:
    session = ModelSession(QueueClient([]), settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "work",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:ACTION",
    )
    event = ModelEvent("action_result", "EV-1", "LANE:ACTION", {"success": True})
    appended = session.append(checkpoint, event)
    assert appended.lane_id == checkpoint.lane_id == "LANE:ACTION"
    assert appended.event_ids == ["EV-1"]


def test_session_fails_before_network_when_prompt_exceeds_budget() -> None:
    client = QueueClient(['{"function":"final_answer","params":{"text":"x"}}'])
    session = ModelSession(client, settings=settings(max_model_len=80))
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "x" * 1000,
        [FINAL_ANSWER_DEFINITION],
    )
    with pytest.raises(InputBudgetError):
        session.generate(checkpoint, max_output_tokens=20)
    assert client.prompts == []
