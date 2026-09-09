from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, replace
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_state_protocols import executor_args_v5
from rwkv_lh.model_io import (
    FINAL_ANSWER_DEFINITION,
    JSON_CALL_STOP_SUFFIXES,
    TOOL_CALL_JSON_CONTINUATION_ANCHOR,
    ModelCommand,
    ModelIOError,
    parse_model_command,
    parse_model_command_with_trace,
    parse_ranked_tool_choice,
    parse_tool_selection,
    render_bootstrap,
    render_event_append,
    render_independent_executor_bootstrap,
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
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.runtime.native_state import NativeStateCandidate, NativeStateSnapshot
from rwkv_lh.runtime.protocol import RuntimeCapabilities
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import GoalState, ModelEvent, ModelLaneKind, RunState
from rwkv_lh.token_budget import tokenizer


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


def test_json_generation_stops_at_native_rwkv_dialogue_boundaries() -> None:
    assert "✿text1✿" in JSON_CALL_STOP_SUFFIXES
    assert "\n`✿text1✿" in JSON_CALL_STOP_SUFFIXES
    # A bare "\n{" stop would truncate a leading blank line or a nested object;
    # a trailing second object is removed by the parser instead.
    assert "\n{" not in JSON_CALL_STOP_SUFFIXES
    assert {"\nSystem:", "\nUser:", "\nAssistant:"} <= set(
        JSON_CALL_STOP_SUFFIXES
    )


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
            recurrent_state_protocol="rwkv-lh.native-state.v1",
        )

    def _snapshot(self, text: str, cache_binding, *, ref: str | None = None):
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
            cache_binding_digest=cache_binding.digest,
        )

    def state_create(self, *, lane_id: str, text: str, cache_binding):
        self.calls.append(("create", text))
        return self._snapshot(text, cache_binding)

    def state_append(
        self, *, parent_state_ref: str, lane_id: str, text: str, cache_binding
    ):
        self.calls.append(("append", text))
        return self._snapshot(self.states[parent_state_ref] + text, cache_binding)

    def state_fork(
        self, *, parent_state_ref: str, lane_id: str, text: str, cache_binding
    ):
        self.calls.append(("fork", text))
        return self._snapshot(self.states[parent_state_ref] + text, cache_binding)

    def state_generate(
        self,
        *,
        parent_state_ref: str,
        request_id: str,
        max_tokens: int,
        stop,
        sampling,
        parent_cache_binding_digest: str,
    ):
        raw = self.outputs.pop(0)
        parent_text = self.states[parent_state_ref]
        self.counter += 1
        candidate_ref = f"STATE-{self.counter}"
        candidate_text = parent_text + raw
        self.states[candidate_ref] = candidate_text
        self.calls.append(("generate", parent_state_ref))
        return NativeStateCandidate(
            candidate_ref,
            hashlib.sha256(candidate_text.encode()).hexdigest(),
            raw,
            parent_state_digest=hashlib.sha256(parent_text.encode()).hexdigest(),
            parent_cache_binding_digest=parent_cache_binding_digest,
        )

    def state_commit(self, *, candidate_state_ref: str, cache_binding):
        self.calls.append(("commit", candidate_state_ref))
        return self._snapshot(
            self.states[candidate_state_ref],
            cache_binding,
            ref=candidate_state_ref,
        )

    def state_rollback(self, *, candidate_state_ref: str, parent_state_ref: str):
        self.calls.append(("rollback", candidate_state_ref))

    def state_import(self, *, export_record, cache_binding):
        self.calls.append(("import", ""))
        return self._snapshot(str(export_record["text"]), cache_binding)


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
        '{"name":"read_file","arguments":"{\\"path\\":\\"a.txt\\"}"}',
        '{"tool":"read_file","parameters":{"path":"a.txt"}}',
        '{"read_file":{"path":"a.txt"}}',
        (
            '{"function_call":{"arguments":"{\\"path\\":\\"a.txt\\"}",'
            '"name":"read_file"}}'
        ),
        (
            '{"function_call":{"name":"read_file",'
            '"arguments":{"path":"a.txt"}}}'
        ),
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


def test_native_tool_call_string_arguments_are_decoded_without_parameter_mutation() -> None:
    arguments = {
        "path": "目录/原样.txt",
        "count": 0,
        "enabled": False,
        "missing": None,
        "nested": {"items": [1, "二", True, None]},
    }
    raw = json.dumps(
        {
            "name": "write_json",
            "arguments": json.dumps(
                arguments,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )
    command, trace = parse_model_command_with_trace(raw)
    assert command == ModelCommand("write_json", arguments)
    assert command.arguments == arguments
    assert trace.input_payload == json.loads(raw)
    assert trace.normalized_payload == {
        "function": "write_json",
        "params": arguments,
    }
    assert trace.transformations == (
        "call_envelope:name.arguments_json_decoded",
        "call_envelope:name+arguments->function+params",
    )
    assert trace.to_dict()["controller_semantic_fields_generated"] is False


def test_structural_escaped_quotes_are_repaired_without_changing_arguments() -> None:
    raw = (
        r'{"name":"write_file","arguments":{"path": \"a.txt\", '
        r'\"content\": \"say \"hello\" now\"}}'
    )
    command, trace = parse_model_command_with_trace(raw)

    assert command == ModelCommand(
        "write_file",
        {"path": "a.txt", "content": 'say "hello" now'},
    )
    assert trace.normalized_payload == {
        "function": "write_file",
        "params": {"path": "a.txt", "content": 'say "hello" now'},
    }
    assert trace.transformations == (
        "surface:structural_escaped_quotes_repaired",
        "call_envelope:name+arguments->function+params",
    )
    assert trace.to_dict()["controller_semantic_fields_generated"] is False


def test_real_chain_search_text_structural_quote_failure_is_recoverable() -> None:
    raw = (
        '{\n  "name": "search_text",\n  "arguments": {"pattern": '
        r'\"status.*paid\", \"path\": \"orders.json\", \"mode\": '
        r'\"regex\", \"case_sensitive\": true, \"recursive\": false, '
        r'\"max_results\": 100, \"start_after\": \"\", \"max_tokens\": '
        r'4096, \"max_file_bytes\": 5000000, \"max_line_chars\": 800}'
        "\n}"
    )
    command, trace = parse_model_command_with_trace(raw)

    assert command == ModelCommand(
        "search_text",
        {
            "pattern": "status.*paid",
            "path": "orders.json",
            "mode": "regex",
            "case_sensitive": True,
            "recursive": False,
            "max_results": 100,
            "start_after": "",
            "max_tokens": 4096,
            "max_file_bytes": 5_000_000,
            "max_line_chars": 800,
        },
    )
    assert trace.transformations == (
        "surface:structural_escaped_quotes_repaired",
        "call_envelope:name+arguments->function+params",
    )


def test_structural_escaped_quote_repair_requires_valid_complete_json() -> None:
    with pytest.raises(ModelIOError):
        parse_model_command(
            r'{"name":"read_file","arguments":{"path": \"a.txt\"}'
        )


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
        '{"function_call":{"name":"read_file","arguments":"not-json"}}',
        '{"function_call":{"name":"read_file","arguments":[]}}',
        (
            '{"function_call":{"name":"read_file","arguments":{},'
            '"extra":true}}'
        ),
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


def test_native_tool_call_bootstrap_uses_only_the_tool_call_json_boundary() -> None:
    prompt = render_bootstrap(
        [FINAL_ANSWER_DEFINITION],
        "return the grounded result",
        native_tool_call_json=True,
    )
    assert prompt.endswith(TOOL_CALL_JSON_CONTINUATION_ANCHOR)
    assert "Assistant: ```json" not in prompt
    assert "\n\nAssistant:\n\n**Tool Call:**" not in prompt
    assert prompt.count("**Tool Call:**") == 1
    assert prompt.count("```json") == 1
    with pytest.raises(ModelIOError, match="not used for tool-menu selection"):
        render_bootstrap(
            [FINAL_ANSWER_DEFINITION],
            "select one tool",
            progressive_tool_disclosure=True,
            native_tool_call_json=True,
        )


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


def test_executor_legacy_disclosure_and_retry_renderers_are_removed() -> None:
    import inspect
    from rwkv_lh import model_io

    assert not hasattr(model_io, "render_independent_executor_tool_disclosure")
    assert "independent_executor_retry_operation" not in inspect.signature(render_event_append).parameters
    for session_type in (ModelSession, NativeRWKVModelSession):
        parameters = inspect.signature(session_type.disclose_tool).parameters
        assert "executor_source" in parameters
        assert "current_requirement" not in parameters
        assert "rendered_prompt" not in parameters


def _executor_input_source():
    contract = executor_args_v5.build_target_contract(
        phase="observe", roots=["README.md"],
        target_descriptors=[{
            "path": "README.md", "type": "file", "target_kind": "text_file", "exists": True,
        }],
        compatible_targets_by_operation={"read_file": ["README.md"]},
    )
    state = executor_args_v5.build_execution_state(
        active_step_id="S1", active_step_revision=1, declared_phase="observe",
        effective_phase="observe", assigned_actions=(),
        mechanical_evidence={"missing_read_roots": ["README.md"]}, target_contract=contract,
    )
    return executor_args_v5.build_prompt_source(
        current_requirement="Read the registered file", execution_state=state,
        selected_operation="read_file",
        selected_tool_contract={"name": "read_file", "parameters": {"type": "object"}},
        committed_fact_refs=(), executor_history=(),
    )


@pytest.mark.parametrize("native", [False, True])
def test_independent_executor_session_requires_current_protocol_source(native: bool) -> None:
    output = '{"function":"read_file","params":{"path":"README.md"}}'
    session = (
        NativeRWKVModelSession(FakeNativeStateClient([output]), settings=settings())
        if native else ModelSession(QueueClient([output]), settings=settings())
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION, "Read the registered file", (),
        independent_tool_selector=True,
    )
    with pytest.raises(ModelIOError, match="current Executor protocol source"):
        session.disclose_tool(checkpoint, FINAL_ANSWER_DEFINITION)
    with pytest.raises(ModelIOError, match="input protocol is required"):
        session.generate(checkpoint)

    source = _executor_input_source()
    disclosed = session.disclose_tool(
        checkpoint, source["selected_tool_contract"], executor_source=source,
    )
    candidate = session.generate(disclosed)
    committed = session.commit(candidate, session.parse(candidate))
    event = ModelEvent(event_type="action_result", event_id="EV-PROTOCOL-REQUIRED",
                       scope_id=checkpoint.lane_id, payload={"action_id": "A1"})
    appended = session.append(committed, event, include_generation_anchor=False)
    with pytest.raises(ModelIOError, match="current Executor protocol source"):
        session.disclose_tool(appended, source["selected_tool_contract"])
    compact = session.rollover(
        appended, source["current_requirement"], (), events=(event,),
        input_limit=10_000, rollover_id="RO-PROTOCOL-REQUIRED", independent_tool_selector=True,
    )
    with pytest.raises(ModelIOError, match="current Executor protocol source"):
        session.disclose_tool(compact, source["selected_tool_contract"])


@pytest.mark.parametrize("native", [False, True])
def test_independent_executor_fork_preserves_the_required_input_contract(native: bool) -> None:
    output = '{"function":"read_file","params":{"path":"README.md"}}'
    session = (
        NativeRWKVModelSession(FakeNativeStateClient([output]), settings=settings())
        if native else ModelSession(QueueClient([output]), settings=settings())
    )
    source = _executor_input_source()
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION, source["current_requirement"], (),
        independent_tool_selector=True,
    )
    assignment = ModelEvent(
        event_type="task_assignment", event_id="EV-EXECUTOR-FORK",
        scope_id=checkpoint.lane_id, payload={"task": "Continue the recorded file read"},
    )
    child = session.fork(checkpoint, ModelLaneKind.ACTION, assignment)
    with pytest.raises(ModelIOError, match="current Executor protocol source"):
        session.disclose_tool(child, source["selected_tool_contract"])
    with pytest.raises(ModelIOError, match="input protocol is required"):
        session.generate(child)
    assert child.native_state_metadata["executor_protocol_required"] is True
    assert not child.transcript.endswith("Assistant: ```json\n")

    disclosed = session.disclose_tool(
        child, source["selected_tool_contract"], executor_source=source,
    )
    candidate = session.generate(disclosed)
    assert session.parse(candidate).name == "read_file"


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


def test_independent_executor_disclosure_uses_only_shared_v4_source() -> None:
    source = _executor_input_source()
    session = ModelSession(QueueClient([]), settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION, source["current_requirement"], (),
        independent_tool_selector=True,
    )
    disclosed = session.disclose_tool(
        checkpoint, source["selected_tool_contract"], executor_source=source,
    )
    assert disclosed.transcript == (
        checkpoint.transcript + "\n\n" + executor_args_v5.render_generation_prompt(source)
    )
    assert disclosed.native_state_metadata["executor_protocol_required"] is True



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


def test_ranked_tool_choice_accepts_executor_native_call_without_action_authority() -> None:
    choice = parse_ranked_tool_choice(
        '{"function":"read_file","params":{"path":"guessed.txt"}}',
        ("read_file", "search_text", "list_directory"),
    )
    assert choice.selected_operation == "read_file"
    assert choice.protocol_form == "direct_candidate_call"
    assert choice.discarded_argument_fields == ("path",)

    name_only = parse_ranked_tool_choice(
        '{"function":"list_directory"}',
        ("read_file", "search_text", "list_directory"),
    )
    assert name_only.selected_operation == "list_directory"
    assert name_only.protocol_form == "direct_candidate_name"


def test_ranked_tool_choice_rejects_outside_top_k_and_repeated_json() -> None:
    with pytest.raises(ModelIOError, match="outside Selector Top-K"):
        parse_ranked_tool_choice(
            '{"function":"write_file","params":{"path":"x","content":"y"}}',
            ("read_file", "search_text", "list_directory"),
        )
    # A trailing second object is dropped by the parser (recorded as a surface
    # transformation) instead of being cut by a "\n{" stop string.
    assert (
        parse_ranked_tool_choice(
            '{"function":"read_file"}\n{"function":"read_file"}',
            ("read_file",),
        ).selected_operation
        == "read_file"
    )


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

    neutral = render_event_append(event, include_generation_anchor=False)
    assert neutral.endswith('"success":true}}}')
    assert "Assistant: ```json" not in neutral
    assert "**Tool Call:**" not in neutral


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
    neutral = render_rollover_event_summary(
        (event,),
        include_generation_anchor=False,
    )
    assert "Assistant: ```json" not in neutral
    assert "**Tool Call:**" not in neutral

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


def test_g1j_executor_history_uses_checkpoint_causal_order(tmp_path) -> None:
    selected_settings = replace(settings(), tool_disclosure_mode="progressive")
    session = ModelSession(QueueClient([]), settings=selected_settings)
    selector = SimpleNamespace()
    model = LongHorizonModel(session, tool_selector=selector)
    goal = model.create_literal_goal(
        "Inspect the fixed project workspace.",
        tmp_path / "causal-history-test",
    )
    state = RunState(run_id="RUN-CAUSAL-HISTORY", goal=goal)
    first = ModelEvent(
        event_type="action_result",
        event_id="EV-Z-FIRST",
        scope_id="LANE:ACTION",
        payload={"action_id": "A1"},
    )
    second = ModelEvent(
        event_type="protocol_rejection",
        event_id="EV-A-SECOND",
        scope_id="LANE:ACTION",
        payload={"selected_operation": "read_file"},
    )
    # Deliberately make lexical order disagree with causal checkpoint order.
    state.model_events = {second.event_id: second, first.event_id: first}
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        goal.request,
        (),
        lane_id=model.ACTION_LANE_ID,
        event_ids=(first.event_id, second.event_id),
        independent_tool_selector=True,
    )
    checkpoint = model._bind_executor_fact_scope(
        state,
        checkpoint,
        (),
        focus_text=goal.request,
    )
    state.model_states[checkpoint.checkpoint_id] = checkpoint
    state.set_lane_head("executor", checkpoint.checkpoint_id)

    disclosed = model._disclose_selected_tool(
        state,
        checkpoint,
        lambda *_args: None,
        model._definitions_by_name["read_file"],
        current_requirement=goal.request,
        execution_state=executor_args_v5.build_execution_state(
            active_step_id="S1", active_step_revision=1,
            declared_phase="observe", effective_phase="observe",
            assigned_actions=(),
            mechanical_evidence={"missing_read_roots": ["README.md"]},
            target_contract=executor_args_v5.build_target_contract(
                phase="observe", roots=["README.md"],
                target_descriptors=[
                    {
                        "path": "README.md",
                        "type": "missing",
                        "target_kind": "missing",
                        "exists": False,
                    }
                ],
                compatible_targets_by_operation={"read_file": []},
            ),
        ),
    )

    payload_text = disclosed.transcript.rsplit("ExecutorArgsPromptV5: ", 1)[1]
    payload = json.loads(payload_text.split("\n\n**Tool Call:**", 1)[0])
    assert [item["event_id"] for item in payload["executor_history"]] == [
        first.event_id,
        second.event_id,
    ]
    assert disclosed.transcript.count("Assistant: ```json") == 0
    assert disclosed.transcript.endswith(TOOL_CALL_JSON_CONTINUATION_ANCHOR)


def test_g1j_executor_retry_does_not_depend_on_compacted_native_transcript() -> None:
    selected_settings = replace(settings(), tool_disclosure_mode="progressive")
    session = ModelSession(QueueClient([]), settings=selected_settings)
    model = LongHorizonModel(session, tool_selector=SimpleNamespace())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "Inspect the fixed project workspace.",
        (),
        lane_id=model.ACTION_LANE_ID,
        independent_tool_selector=True,
    )
    compacted = replace(
        checkpoint,
        transcript='{"function":"search_text","params":{"path":"."}}',
    )
    rejection = ModelEvent(
        event_type="protocol_rejection",
        event_id="EV-NATIVE-COMPACTED-RETRY",
        scope_id=model.ACTION_LANE_ID,
        payload={
            "selection_id": "NSEL-CONSUMED-1",
            "selected_operation": "search_text",
            "error": "path is outside the declared roots",
            "rejected_arguments": {"path": "."},
        },
    )

    assert model._progressive_retry_operation((rejection,), compacted) == "search_text"


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


def test_session_restores_only_token_attested_transport_stop_fence() -> None:
    raw = '```json\n{"function":"read_file","params":{"path":"a.txt"}}'
    full_generated_stream = raw + "\n```"

    class StopStrippingClient(QueueClient):
        def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
            self.prompts.append(prompt)
            return Response(
                raw,
                finish_reason="stop",
                metadata={"token_ids": tokenizer().encode(full_generated_stream)},
            )

    audits: list[dict] = []
    session = ModelSession(
        StopStrippingClient([]),
        settings=settings(),
        audit_hook=audits.append,
    )
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read a.txt",
        [{
            "name": "read_file",
            "description": "read",
            "parameters": {"type": "object", "properties": {}, "required": []},
        }],
    )

    candidate = session.generate(checkpoint, max_output_tokens=100)
    command, trace = session.parse_with_trace(candidate)
    committed = session.commit(candidate, command)

    assert command == ModelCommand("read_file", {"path": "a.txt"})
    assert trace.transformations[:2] == (
        "transport:attested_markdown_stop_suffix_restored",
        "surface:markdown_code_fence_removed",
    )
    assert committed.parent_checkpoint_id == checkpoint.checkpoint_id
    returned = next(
        item for item in audits if item["type"] == "model_session_generation_returned"
    )
    assert returned["raw_output"] == raw


def test_session_reports_attested_empty_fence_as_no_json_body() -> None:
    raw = "```json"

    class EmptyFenceClient(QueueClient):
        def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
            self.prompts.append(prompt)
            return Response(
                raw,
                finish_reason="stop",
                metadata={"token_ids": tokenizer().encode(raw + "\n```")},
            )

    session = ModelSession(EmptyFenceClient([]), settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "read a.txt",
        [FINAL_ANSWER_DEFINITION],
    )
    candidate = session.generate(checkpoint, max_output_tokens=100)

    with pytest.raises(ModelIOError, match="has no JSON body"):
        session.parse(candidate)


def test_generation_keeps_immutable_raw_record_and_profile_identity() -> None:
    raw = '  {"function":"final_answer","params":{"text":"完成"}}\n'

    class RawClient(QueueClient):
        def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
            self.prompts.append(prompt)
            return Response(
                raw,
                finish_reason="length",
                metadata={"token_ids": [1, 2, 3], "prompt_token_ids": [0, 11, 12]},
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
    assert record["prompt_token_ids"] == [0, 11, 12]
    assert record["prompt_token_ids_scope"] == "full_prompt"
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


def test_native_session_advances_only_the_new_delta_and_marks_cache_non_authoritative() -> None:
    client = FakeNativeStateClient([])
    session = NativeRWKVModelSession(client, settings=settings())
    bootstrap = session.bootstrap(
        ModelLaneKind.ACTION,
        "Inspect a real workspace file.",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE:DELTA",
    )
    event = ModelEvent(
        "action_result",
        "EV-DELTA-1",
        "LANE:DELTA",
        {"action_id": "A-1", "result": {"success": True, "output": "ok"}},
    )

    appended = session.append(bootstrap, event)

    assert [name for name, _ in client.calls] == ["create", "append"]
    assert client.calls[1][1] == render_event_append(event)
    assert bootstrap.transcript not in client.calls[1][1]
    assert appended.transcript == client.calls[1][1]
    assert appended.native_state_metadata is not None
    assert appended.native_state_metadata["authoritative"] is False
    assert appended.native_state_metadata["cache_role"] == "disposable_acceleration"
    binding = appended.native_state_metadata["cache_binding"]
    assert binding["parent_state_digest"] == bootstrap.native_state_digest
    assert binding["delta_digest"] == appended.transcript_digest
    assert binding["state_chain_digest"] != (
        bootstrap.native_state_metadata or {}
    )["cache_binding"]["state_chain_digest"]


def test_native_session_rejects_cache_that_claims_authority_before_import() -> None:
    client = FakeNativeStateClient([])
    session = NativeRWKVModelSession(client, settings=settings())
    checkpoint = session.bootstrap(
        ModelLaneKind.ACTION,
        "finish",
        [FINAL_ANSWER_DEFINITION],
    )
    exported = session.export(checkpoint)
    exported["native_state_metadata"]["authoritative"] = True

    with pytest.raises(ModelSessionError, match="cannot be authoritative"):
        session.import_checkpoint(exported)

    assert [name for name, _ in client.calls] == ["create"]


def test_long_horizon_model_rebuilds_missing_native_cache_from_goal_projection(
    tmp_path,
) -> None:
    client = FakeNativeStateClient([])
    session = NativeRWKVModelSession(client, settings=settings())
    model = LongHorizonModel(session)
    state = RunState(
        run_id="RUN-CACHE-REBUILD",
        goal=GoalState.create(
            request="Inspect this workspace and report the result.",
            constraints=[],
            workspace_root=tmp_path,
        ),
    )
    persisted: list[tuple[str, dict]] = []

    def persist(_state, event_type, payload):
        persisted.append((event_type, dict(payload)))

    original = model._checkpoint(state, persist)
    assert original.native_state_metadata is not None
    original.native_state_metadata["authoritative"] = True

    rebuilt = model._checkpoint(state, persist)

    assert rebuilt.checkpoint_id != original.checkpoint_id
    assert state.lane_head("executor") == rebuilt.checkpoint_id
    assert [name for name, _ in client.calls] == ["create", "create"]
    rollover = persisted[-1]
    assert rollover[0] == "action_session_rolled_over"
    assert rollover[1]["reason"] == "wkv_cache_miss_deterministic_rebuild"
    assert rollover[1]["cache_authority"] is False
    assert rollover[1]["semantic_request_count"] == 0


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

    assert checkpoint.native_state_metadata is not None
    assert checkpoint.native_state_metadata["model_sha256"] == "b" * 64
    assert checkpoint.native_state_metadata["state_profile_delivery"] == "request"
    assert checkpoint.native_state_metadata["protocol_version"] == (
        "rwkv-lh.native-state.v1"
    )
    assert checkpoint.native_state_metadata["state_format_version"] == "fake-state-v1"
    assert checkpoint.native_state_metadata["server_build"] == "fake-server-1"
    assert checkpoint.native_state_metadata["tokenizer_build"] == "fake-tokenizer-1"
    assert checkpoint.native_state_metadata["cache_role"] == "disposable_acceleration"
    assert checkpoint.native_state_metadata["authoritative"] is False
    assert checkpoint.native_state_metadata["cache_binding"]["authoritative"] is False
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


def test_session_factory_rejects_incompatible_native_protocol_attestation() -> None:
    class IncompatibleProtocolClient(FakeNativeStateClient):
        def capabilities(self):
            return RuntimeCapabilities(
                recurrent_state_create=True,
                recurrent_state_resume=True,
                recurrent_state_fork=True,
                recurrent_state_commit=True,
                recurrent_state_rollback=True,
                recurrent_state_export=True,
                recurrent_state_import=True,
                recurrent_state_protocol="rwkv-lh.native-state.v0",
            )

    client = IncompatibleProtocolClient([])
    audits: list[dict] = []
    fallback = create_model_session(
        client,
        settings=settings(state_transport="auto"),
        audit_hook=audits.append,
    )
    assert type(fallback) is ModelSession
    assert audits[-1]["selected_transport"] == "prompt_replay"
    assert "incompatible" in audits[-1]["reason"]

    with pytest.raises(NativeStateUnavailableError, match="incompatible"):
        create_model_session(
            client,
            settings=settings(state_transport="native_required"),
        )


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


def test_json_extraction_keeps_first_object_and_survives_leading_newline() -> None:
    from rwkv_lh.model_io import parse_model_command

    nested = (
        '\n{\n"function": "write_file",\n"params":\n{\n"path": "a.txt",'
        '\n"content": "x"\n}\n}'
    )
    command = parse_model_command(nested)
    assert command.name == "write_file"
    assert command.arguments["path"] == "a.txt"
    repeated = parse_model_command(
        '{"function":"read_file","params":{"path":"a"}}\n{"function":"read_file"}'
    )
    assert repeated.arguments == {"path": "a"}
