from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

import pytest

from rwkv_lh.model_io import (
    FINAL_ANSWER_DEFINITION,
    ModelCommand,
    ModelIOError,
    parse_model_command,
    parse_model_command_with_trace,
    parse_tool_selection,
    render_bootstrap,
    render_event_append,
    render_independent_executor_bootstrap,
    render_independent_executor_tool_disclosure,
    render_rollover_event_summary,
    render_tool_disclosure,
    validate_final_answer,
)
from rwkv_lh.model_session import (
    InputBudgetError,
    ModelSession,
    ModelSessionError,
    NativeRWKVModelSession,
    NativeStateUnavailableError,
    create_model_session,
)
from rwkv_lh.runtime.native_state import NativeStateCandidate, NativeStateSnapshot
from rwkv_lh.runtime.protocol import RuntimeCapabilities
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelEvent, ModelLaneKind


@dataclass
class Response:
    content: str
    finish_reason: str = "stop"
    metadata: dict = field(default_factory=dict)
    response_id: str = ""
    model: str = ""


class QueueClient:
    model_name = "test-rwkv"

    def __init__(self, outputs: list[str]):
        self.outputs = list(outputs)
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        return Response(self.outputs.pop(0))


class FakeNativeStateClient:
    model_name = "test-native-rwkv"

    def __init__(self, outputs: list[str], *, durable: bool = True):
        self.outputs = list(outputs)
        self.durable = durable
        self.states: dict[str, str] = {}
        self.calls: list[tuple[str, str]] = []
        self.counter = 0

    def capabilities(self):
        return RuntimeCapabilities(
            recurrent_state_create=self.durable,
            recurrent_state_resume=self.durable,
            recurrent_state_fork=self.durable,
            recurrent_state_commit=self.durable,
            recurrent_state_rollback=self.durable,
            recurrent_state_export=self.durable,
            recurrent_state_import=self.durable,
        )

    def _snapshot(self, text: str, *, ref: str | None = None):
        if ref is None:
            self.counter += 1
            ref = f"STATE-{self.counter}"
        self.states[ref] = text
        return NativeStateSnapshot(
            state_ref=ref,
            state_digest=hashlib.sha256(text.encode()).hexdigest(),
            export_record={"text": text},
            state_format_version="fake-state-v1",
            server_build="fake-server-1",
            tokenizer_build="fake-tokenizer-1",
        )

    def state_create(self, *, lane_id: str, text: str):
        self.calls.append(("create", text))
        return self._snapshot(text)

    def state_append(self, *, parent_state_ref: str, lane_id: str, text: str):
        self.calls.append(("append", text))
        return self._snapshot(self.states[parent_state_ref] + text)

    def state_fork(self, *, parent_state_ref: str, lane_id: str, text: str):
        self.calls.append(("fork", text))
        return self._snapshot(self.states[parent_state_ref] + text)

    def state_generate(
        self, *, parent_state_ref: str, request_id: str, max_tokens: int, stop, sampling
    ):
        raw = self.outputs.pop(0)
        snapshot = self._snapshot(self.states[parent_state_ref] + raw)
        self.calls.append(("generate", parent_state_ref))
        return NativeStateCandidate(snapshot.state_ref, snapshot.state_digest, raw)

    def state_commit(self, *, candidate_state_ref: str):
        self.calls.append(("commit", candidate_state_ref))
        return self._snapshot(self.states[candidate_state_ref], ref=candidate_state_ref)

    def state_rollback(self, *, candidate_state_ref: str, parent_state_ref: str):
        self.calls.append(("rollback", candidate_state_ref))

    def state_import(self, *, export_record):
        self.calls.append(("import", ""))
        return self._snapshot(str(export_record["text"]))


def settings(
    max_model_len: int = 16384,
    *,
    state_transport: str = "prompt_replay",
    state_profile_id: str = "",
    state_profile_sha256: str = "",
    model_sha256: str = "",
) -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        model_sha256=model_sha256,
        max_model_len=max_model_len,
        context_safety_margin=8,
        bos_token_count=1,
        tool_disclosure_mode="full",
        state_transport=state_transport,
        state_profile_id=state_profile_id,
        state_profile_sha256=state_profile_sha256,
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
        validate_final_answer(
            ModelCommand("final_answer", {"text": "x", "status": "ok"})
        )


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


def test_progressive_bootstrap_exposes_menu_without_tool_schema_in_system() -> None:
    definition = {
        "name": "read_file",
        "description": "Read one workspace file.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }
    prompt = render_bootstrap(
        [definition, FINAL_ANSWER_DEFINITION],
        "do the work",
        progressive_tool_disclosure=True,
    )
    system, user = prompt.split("\n\nUser:", 1)
    assert "read_file" not in system
    assert "final_answer" not in system
    assert '"name":"read_file"' in user
    assert "Read one workspace file." in user
    assert '"parameters"' not in user
    assert '"required"' not in user
    assert '"function":"select_tool"' in user


def test_independent_executor_bootstrap_has_no_selector_menu_or_schema() -> None:
    prompt = render_independent_executor_bootstrap("do the work")
    assert "Executor task state: do the work" in prompt
    assert "independent Selector commits the operation" in prompt
    assert "Available operation menu" not in prompt
    assert '"function":"select_tool"' not in prompt
    assert '"parameters"' not in prompt
    assert "Assistant:" not in prompt


def test_selected_tool_disclosure_contains_only_one_exact_contract() -> None:
    definition = {
        "name": "read_file",
        "description": "Read one workspace file.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }
    rendered = render_tool_disclosure(definition)
    assert "System: Tools" not in rendered
    assert '"selected_operation":"read_file"' in rendered
    assert '"required":["path"]' in rendered
    assert "final_answer" not in rendered


def test_independent_executor_disclosure_puts_closed_requirement_at_tail() -> None:
    definition = {
        "name": "read_file",
        "description": "Read one workspace file.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }
    requirement = "Read exact.txt and report its contents."
    rendered = render_independent_executor_tool_disclosure(
        definition,
        requirement,
    )
    prefix = "\n\nUser: Executor continuation input: "
    assert rendered.startswith(prefix)
    payload_text, suffix = rendered[len(prefix) :].split("\n\nAssistant:", 1)
    payload = json.loads(payload_text)
    assert list(payload)[-1] == "current_requirement"
    assert payload["current_requirement"] == requirement
    assert payload["selected_operation"] == "read_file"
    assert suffix == " ```json\n"
    assert rendered.count(requirement) == 1


def test_tool_selection_requires_exact_selector_envelope() -> None:
    assert (
        parse_tool_selection('{"function":"select_tool","params":{"name":"read_file"}}')
        == "read_file"
    )
    with pytest.raises(ModelIOError, match="exactly one name"):
        parse_tool_selection(
            '{"function":"select_tool","params":{"name":"read_file","why":"x"}}'
        )
    with pytest.raises(ModelIOError, match="select_tool"):
        parse_tool_selection('{"function":"read_file","params":{"path":"a"}}')


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


def test_rollover_summary_renders_exact_event_bodies_for_visible_ids() -> None:
    event = ModelEvent(
        event_type="protocol_rejection",
        event_id="EV-REJECT-1",
        scope_id="LANE:ACTION",
        payload={
            "error": "path is required",
            "rejected_arguments": {},
            "selected_operation": "read_file",
        },
    )
    rendered = render_rollover_event_summary((event,))
    assert '"event_type":"protocol_rejection"' in rendered
    assert '"error":"path is required"' in rendered
    assert '"rejected_arguments":{}' in rendered
    assert '"selected_operation":"read_file"' in rendered

    session = ModelSession(QueueClient([]), settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read a file",
        [FINAL_ANSWER_DEFINITION],
    )
    compact = session.rollover(
        checkpoint,
        "read a file",
        [FINAL_ANSWER_DEFINITION],
        events=(event,),
        input_limit=10_000,
        rollover_id="RO-1",
    )

    assert compact.event_ids == [event.event_id]
    assert rendered in compact.transcript


def test_native_rollover_rebuilds_state_with_retained_event_bodies() -> None:
    event = ModelEvent(
        event_type="protocol_rejection",
        event_id="EV-NATIVE-REJECT",
        scope_id="LANE:NATIVE",
        payload={"error": "query is required", "rejected_arguments": {}},
    )
    client = FakeNativeStateClient([])
    session = NativeRWKVModelSession(client, settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "search",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:NATIVE",
    )

    compact = session.rollover(
        checkpoint,
        "search",
        [FINAL_ANSWER_DEFINITION],
        events=(event,),
        input_limit=10_000,
        rollover_id="RO-NATIVE-1",
    )

    assert compact.event_ids == [event.event_id]
    assert '"error":"query is required"' in compact.transcript
    assert client.calls[-1] == ("create", compact.transcript)


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


def test_generation_keeps_immutable_raw_record_and_profile_identity() -> None:
    raw = '  {"function":"final_answer","params":{"text":"完成"}}\n'

    class RawClient(QueueClient):
        def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
            self.prompts.append(prompt)
            return Response(
                raw,
                finish_reason="length",
                metadata={"token_ids": [1, 2, 3]},
                response_id="cmpl-raw",
                model="rwkv-13.3b",
            )

    audits: list[dict] = []
    session = ModelSession(
        RawClient([]),
        settings=settings(
            state_profile_id="executor",
            state_profile_sha256="a" * 64,
            model_sha256="b" * 64,
        ),
        audit_hook=audits.append,
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )

    candidate = session.generate(checkpoint, max_output_tokens=100)
    record = candidate.raw_record()

    assert candidate.raw_output == raw
    assert record["raw_output"] == raw
    assert record["raw_output_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert record["raw_token_ids"] == [1, 2, 3]
    assert record["finish_reason"] == "length"
    assert record["postprocessed"] is False
    assert checkpoint.state_profile_id == "executor"
    assert checkpoint.state_profile_sha256 == "a" * 64
    assert checkpoint.native_state_metadata == {
        "model_sha256": "b" * 64,
        "state_profile_delivery": "request",
    }
    returned = next(
        item for item in audits if item["type"] == "model_session_generation_returned"
    )
    assert returned["raw_generation"] == record


def test_session_rejects_resumed_checkpoint_from_a_different_profile() -> None:
    original = ModelSession(
        QueueClient([]),
        settings=settings(
            state_profile_id="executor-general",
            state_profile_sha256="a" * 64,
            model_sha256="b" * 64,
        ),
    ).bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    replacement_client = QueueClient(
        ['{"function":"final_answer","params":{"text":"wrong state"}}']
    )
    replacement = ModelSession(
        replacement_client,
        settings=settings(
            state_profile_id="executor-network",
            state_profile_sha256="c" * 64,
            model_sha256="b" * 64,
        ),
    )

    with pytest.raises(ModelSessionError, match="immutable session profile"):
        replacement.generate(original, max_output_tokens=100)
    assert replacement_client.prompts == []


def test_session_rejects_candidate_commit_under_a_different_profile() -> None:
    original = ModelSession(
        QueueClient(['{"function":"final_answer","params":{"text":"raw"}}']),
        settings=settings(
            state_profile_id="executor-general",
            state_profile_sha256="a" * 64,
        ),
    )
    checkpoint = original.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    candidate = original.generate(checkpoint, max_output_tokens=100)
    replacement = ModelSession(
        QueueClient([]),
        settings=settings(
            state_profile_id="executor-network",
            state_profile_sha256="b" * 64,
        ),
    )

    with pytest.raises(ModelSessionError, match="immutable session profile"):
        replacement.commit(candidate, original.parse(candidate))


def test_session_rejects_resumed_checkpoint_from_a_different_model() -> None:
    original = ModelSession(
        QueueClient([]),
        settings=settings(model_sha256="a" * 64),
    ).bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    original.native_state_metadata = {
        **dict(original.native_state_metadata or {}),
        "model_sha256": "b" * 64,
    }
    replacement_client = QueueClient(
        ['{"function":"final_answer","params":{"text":"wrong model"}}']
    )
    replacement = ModelSession(
        replacement_client,
        settings=settings(model_sha256="a" * 64),
    )

    with pytest.raises(ModelSessionError, match="base-model SHA-256"):
        replacement.generate(original, max_output_tokens=100)
    assert replacement_client.prompts == []


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


def test_native_session_commits_and_recovers_durable_recurrent_state() -> None:
    client = FakeNativeStateClient(
        ['{"function":"read_file","params":{"path":"a.txt"}}']
    )
    audits: list[dict] = []
    session = NativeRWKVModelSession(
        client,
        settings=settings(),
        audit_hook=audits.append,
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read a.txt",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:NATIVE",
    )
    candidate = session.generate(checkpoint, max_output_tokens=100)
    committed = session.commit(candidate, session.parse(candidate))
    exported = session.export(committed)
    recovered = session.import_checkpoint(exported)

    assert committed.transport == "native_rwkv"
    assert committed.native_state_digest == candidate.checkpoint.native_state_digest
    assert recovered.native_state_digest == committed.native_state_digest
    assert recovered.native_state_ref != committed.native_state_ref
    assert client.calls[0][0] == "create"
    assert client.calls[1][0] == "generate"
    assert client.calls[2][0] == "commit"
    assert client.calls[3][0] == "import"
    started = next(
        item for item in audits if item["type"] == "model_session_generation_started"
    )
    assert started["static_replay_tokens"] == 0
    assert started["input_digest"] == checkpoint.native_state_digest


def test_native_snapshot_keeps_model_and_profile_identity_metadata() -> None:
    selected = settings(
        state_transport="auto",
        state_profile_id="executor-network",
        state_profile_sha256="a" * 64,
        model_sha256="b" * 64,
    )
    session = NativeRWKVModelSession(
        FakeNativeStateClient([]),
        settings=selected,
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )

    assert checkpoint.native_state_metadata == {
        "model_sha256": "b" * 64,
        "state_profile_delivery": "request",
        "protocol_version": "rwkv-lh.native-state.v1",
        "state_format_version": "fake-state-v1",
        "server_build": "fake-server-1",
        "tokenizer_build": "fake-tokenizer-1",
    }
    recovered = session.import_checkpoint(session.export(checkpoint))
    assert recovered.native_state_metadata == checkpoint.native_state_metadata


def test_native_session_rolls_back_candidate_to_exact_parent_state() -> None:
    client = FakeNativeStateClient(["invalid"])
    session = NativeRWKVModelSession(client, settings=settings())
    parent = session.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    candidate = session.generate(parent, max_output_tokens=100)

    restored = session.rollback(candidate, error="protocol invalid")

    assert restored is parent
    assert client.calls[-1] == ("rollback", candidate.checkpoint.native_state_ref)


def test_native_session_refuses_partial_state_capability() -> None:
    with pytest.raises(NativeStateUnavailableError, match="create/resume"):
        NativeRWKVModelSession(
            FakeNativeStateClient([], durable=False),
            settings=settings(),
        )


def test_session_factory_selects_native_only_with_complete_capability() -> None:
    client = FakeNativeStateClient([])
    session = create_model_session(
        client,
        settings=settings(state_transport="auto"),
    )
    assert isinstance(session, NativeRWKVModelSession)


def test_session_factory_native_required_fails_without_adapter() -> None:
    with pytest.raises(NativeStateUnavailableError, match="methods unavailable"):
        create_model_session(
            QueueClient([]),
            settings=settings(state_transport="native_required"),
        )


def test_session_append_preserves_same_lane() -> None:
    audits: list[dict] = []
    session = ModelSession(
        QueueClient([]),
        settings=settings(),
        audit_hook=audits.append,
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "work",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:ACTION",
    )
    event = ModelEvent(
        "protocol_rejection",
        "EV-1",
        "LANE:ACTION",
        {
            "selected_operation": "ABSTAIN",
            "error_record": {"type": "ModelProtocolError", "message": "private"},
        },
    )
    appended = session.append(checkpoint, event)
    assert appended.lane_id == checkpoint.lane_id == "LANE:ACTION"
    assert appended.event_ids == ["EV-1"]
    audit = next(
        item for item in audits if item["type"] == "model_session_event_appended"
    )
    assert audit["event_type"] == "protocol_rejection"
    assert audit["event_error_type"] == "ModelProtocolError"
    assert audit["event_selected_operation"] == "ABSTAIN"
    assert "private" not in json.dumps(audit)


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
