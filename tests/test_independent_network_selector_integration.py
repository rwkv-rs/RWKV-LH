from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.exact_tool_selector.network_client import (
    NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkExactToolSelection,
)
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.parallel_atoms import (
    _project_atom_actions,
    _project_tool_selection_decision_bindings,
)
from rwkv_lh.retrieval import (
    RetrievalRuntimeConfig,
    build_product_harness,
    runtime_policy_document,
)
from rwkv_lh.retrieval.policy import NetworkPolicyMode
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ModelLaneKind, RunStatus, ToolSelectionStatus
from rwkv_lh.store import LongHorizonStore


@dataclass
class _CompletionResponse:
    content: str
    finish_reason: str = "stop"


class _ExecutorQueue:
    model_name = "rwkv7-g1i-13.3b-test"

    def __init__(self, outputs: list[Mapping[str, Any]]) -> None:
        self.raw_outputs = [
            json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            for item in outputs
        ]
        self.remaining = list(self.raw_outputs)
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        if not self.remaining:
            raise AssertionError("unexpected Executor generation")
        return _CompletionResponse(self.remaining.pop(0))


class _SelectorResponse:
    def __init__(
        self,
        value: Mapping[str, Any],
        *,
        status_code: int = 200,
    ) -> None:
        self.status_code = status_code
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")
        self.text = self.content.decode("utf-8")


class _SelectorHTTP:
    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        operations: list[str],
        *,
        missing_parent_once: bool = False,
    ) -> None:
        self.settings = settings
        self.operations = list(operations)
        self.payloads: list[dict[str, Any]] = []
        self.missing_parent_once = bool(missing_parent_once)
        self.parent_miss_emitted = False
        self.current_operation = ""

    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> _SelectorResponse:
        assert url.endswith(
            network_selector_input_protocol(self.settings.input_protocol).endpoint
        )
        payload = dict(json)
        self.payloads.append(payload)
        if (
            self.missing_parent_once
            and payload.get("parent") is not None
            and not self.parent_miss_emitted
        ):
            self.parent_miss_emitted = True
            return _SelectorResponse(
                {
                    "error": "NetworkSelectorServiceError",
                    "message": "network Selector parent state is missing",
                },
                status_code=400,
            )
        if not self.operations:
            raise AssertionError("unexpected Selector call")
        menu_order_id = str(payload.get("menu_order_id") or "")
        if menu_order_id == "canonical":
            global_peak = self.operations.pop(0)
            self.current_operation = global_peak
        else:
            if not self.current_operation:
                raise AssertionError("non-canonical Selector lane ran before canonical")
            global_peak = self.current_operation
        parent = payload.get("parent")
        parent_value = dict(parent) if isinstance(parent, Mapping) else {}
        logits = [float(index) / 1000.0 for index in range(25)]
        logits[NETWORK_EXACT_TOOL_LABELS.index(global_peak)] = 10.0
        eligible_labels = tuple(str(item) for item in payload["eligible_labels"])
        selected_index = max(
            (
                NETWORK_EXACT_TOOL_LABELS.index(label)
                for label in eligible_labels
            ),
            key=lambda index: (logits[index], -index),
        )
        operation = NETWORK_EXACT_TOOL_LABELS[selected_index]
        index = len(self.payloads)
        selection = NetworkExactToolSelection(
            selection_id=f"NSEL-{index:04d}",
            trace_id=str(payload["trace_id"]),
            selected_operation=operation,
            logits=tuple(logits),
            temperature=0.25,
            input_digest=str(payload["input_digest"]),
            menu_digest=str(payload["menu_digest"]),
            selector_checkpoint_id=f"NSCP-{index:04d}",
            selector_state_ref=f"NSTATE-{index:04d}",
            selector_state_digest=hashlib.sha256(
                f"selector-state-{index}".encode()
            ).hexdigest(),
            selector_parent_state_digest=str(parent_value.get("state_digest") or ""),
            token_position=int(parent_value.get("token_position") or 0) + 20,
            model=self.settings.model,
            model_sha256=self.settings.model_sha256,
            head_sha256=self.settings.head_sha256,
            profile_id=self.settings.state_profile_id,
            profile_sha256=self.settings.state_profile_sha256,
            eligible_labels=eligible_labels,
        )
        return _SelectorResponse(
            {
                "schema_version": NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }
        )


class _ScopedHarnessSubset:
    """Test the same least-privilege menu projection used by atom Harnesses."""

    operation_order_authority = "controller_capability_projection"

    def __init__(
        self,
        base: ActionHarness,
        allowed_operations: tuple[str, ...],
    ) -> None:
        self.base = base
        self.allowed_operations = allowed_operations

    def __getattr__(self, name: str) -> Any:
        return getattr(self.base, name)

    def g1i_tool_definitions(
        self,
        action_types: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        requested = (
            self.allowed_operations
            if action_types is None
            else tuple(
                str(item)
                for item in action_types
                if str(item) in self.allowed_operations
            )
        )
        return self.base.g1i_tool_definitions(list(requested))


class _UnknownOperationHarness:
    operation_order_authority = "test_unknown_operation"

    @staticmethod
    def g1i_tool_definitions(
        action_types: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, str]]:
        del action_types
        return [
            {
                "name": "private_unknown_operation",
                "description": "An operation outside the frozen Selector protocol.",
            }
        ]


def _call(name: str, **arguments: Any) -> dict[str, Any]:
    return {"function": name, "params": arguments}


def _selector_settings(
    input_protocol: str = CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
) -> NetworkExactToolSelectorSettings:
    return NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1i-2.9b-test",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        head_hash="c" * 64,
        feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        state_profile_id="selector-zero-v1",
        state_profile_sha256="d" * 64,
        state_profile_manifest_sha256="e" * 64,
        input_protocol=input_protocol,
    )


def _executor_settings() -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="rwkv7-g1i-13.3b-test",
        model_sha256="f" * 64,
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="progressive",
        state_profile_id="executor-base-v1",
        state_profile_sha256="1" * 64,
    )


def _build(
    tmp_path: Path,
    *,
    selector_operations: list[str],
    model_class: type[LongHorizonModel] = LongHorizonModel,
    executor_outputs: list[Mapping[str, Any]] | None = None,
    active_operations: tuple[str, ...] | None = None,
    selector_min_actions: int = 0,
    goal_retrieval_mode: NetworkPolicyMode = NetworkPolicyMode.OFFLINE,
    missing_selector_parent_once: bool = False,
    selector_input_protocol: str = CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    base_harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "retrieval-snapshots",
        sandbox_commands=False,
    )
    harness = (
        _ScopedHarnessSubset(base_harness, active_operations)
        if active_operations is not None
        else base_harness
    )
    executor = _ExecutorQueue(
        executor_outputs
        or [
            _call("write_file", path="hello.txt", content="hello"),
            _call("final_answer", text="Created hello.txt."),
        ]
    )
    selector_settings = _selector_settings(selector_input_protocol)
    selector_http = _SelectorHTTP(
        selector_settings,
        selector_operations,
        missing_parent_once=missing_selector_parent_once,
    )
    selector = NetworkExactToolSelectorClient(
        selector_settings,
        session=selector_http,
    )
    model = model_class(
        ModelSession(executor, settings=_executor_settings()),
        harness=harness,
        tool_selector=selector,
        selector_min_actions=selector_min_actions,
    )
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    state = store.create_run(
        model.create_literal_goal(
            "Create hello.txt containing exactly hello.",
            str(workspace),
            runtime_policy=runtime_policy_document(
                RetrievalRuntimeConfig(mode=goal_retrieval_mode)
            ),
        ),
        "RUN",
    )
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=20,
    )
    return controller, store, workspace, executor, selector_http


def test_independent_selector_accepts_stage_scoped_harness_subset(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        active_operations=("write_file",),
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(executor.prompts) == 2
    assert all(
        '"selected_operation":"read_file"' not in prompt
        for prompt in executor.prompts
    )
    bootstrap = selector_http.payloads[0]["bootstrap"]
    menu_text = bootstrap.split("\nSelectorIntentRoleV1: ", 1)[0]
    menu = json.loads(menu_text.removeprefix("SelectorIntentMenuV1: "))
    assert tuple(item["name"] for item in menu["tools"]) == (
        NETWORK_EXACT_TOOL_LABELS
    )
    assert selector_http.payloads[0]["eligible_labels"] == [
        "write_file",
        "final_answer",
    ]


def test_independent_selector_rejects_unknown_active_harness_operation() -> None:
    settings = _selector_settings()
    selector = NetworkExactToolSelectorClient(
        settings,
        session=_SelectorHTTP(settings, []),
    )
    executor = _ExecutorQueue([])

    with pytest.raises(
        ValueError,
        match=r"outside the frozen menu; extra=\['private_unknown_operation'\]",
    ):
        LongHorizonModel(
            ModelSession(executor, settings=_executor_settings()),
            harness=_UnknownOperationHarness(),
            tool_selector=selector,
        )


def test_selector_eligibility_excludes_final_until_minimum_actions_are_observed(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["final_answer", "final_answer"],
        active_operations=("write_file",),
        selector_min_actions=1,
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(executor.prompts) == 2
    assert selector_http.payloads[0]["eligible_labels"] == [
        "write_file",
    ]
    assert selector_http.payloads[1]["eligible_labels"] == [
        "write_file",
        "final_answer",
    ]
    rejected = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "exact_tool_selection_rejected"
    ]
    assert rejected == []
    first_raw = next(iter(result.state.tool_selections.values())).raw_selection
    assert first_raw["logits"][NETWORK_EXACT_TOOL_LABELS.index("final_answer")] == 10.0
    assert first_raw["selected_operation"] == "write_file"


def test_stage_unauthorized_global_peak_is_eligibility_masked_with_logits_preserved(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["run_command", "final_answer"],
        active_operations=("write_file",),
        selector_min_actions=1,
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(selector_http.payloads) == 2
    assert len(executor.prompts) == 2
    assert len(result.state.actions) == 1
    rejected = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "exact_tool_selection_rejected"
    ]
    assert rejected == []
    first_selection = next(iter(result.state.tool_selections.values()))
    raw = first_selection.raw_selection
    expected_logits = [float(index) / 1000.0 for index in range(25)]
    expected_logits[NETWORK_EXACT_TOOL_LABELS.index("run_command")] = 10.0
    assert raw["selection_id"] == "NSEL-0001"
    assert raw["selected_operation"] == "write_file"
    assert raw["logits"] == expected_logits
    assert raw["eligible_labels"] == ["write_file"]
    assert raw["selection_rule"] == "eligible_raw_logit_argmax"
    assert raw["postprocessed"] is False
    assert raw["generated_text"] is False
    assert set(result.state.tool_selections) == {"NSEL-0001", "NSEL-0002"}


def test_independent_selector_preserves_current_harness_and_raw_outputs(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(executor.prompts) == 2
    for prompt in executor.prompts:
        assert "independent-selector-executor.v2-request-last" in prompt
        assert "Available operation menu" not in prompt
        assert '"function":"select_tool"' not in prompt
        assert "Select exactly one displayed operation" not in prompt
        assert prompt.count("Create hello.txt containing exactly hello.") == 1
        if "ExecutorArgsPromptV1: " in prompt:
            prefix, payload_text = prompt.rsplit("ExecutorArgsPromptV1: ", 1)
            assert not prefix.rstrip().endswith("Assistant: ```json")
            payload_text = payload_text.split("\n\n**Tool Call:**", 1)[0]
            payload = json.loads(payload_text)
            assert payload["role"] == "executor_args"
            assert payload["current_requirement"] == (
                "Create hello.txt containing exactly hello."
            )
        else:
            payload_text = prompt.rsplit(
                "\n\nUser: Executor continuation input: ", 1
            )[1].split("\n\nAssistant:", 1)[0]
            assert list(json.loads(payload_text))[-1] == "current_requirement"
    assert '"selected_operation":"write_file"' in executor.prompts[0]
    assert '"selected_operation":"final_answer"' in executor.prompts[1]
    assert '"selected_operation":"read_file"' not in executor.prompts[0]
    assert [item.raw_output for item in result.state.decisions.values()] == (
        executor.raw_outputs
    )
    assert len(selector_http.payloads) == 2
    assert "web_search" not in selector_http.payloads[0]["eligible_labels"]
    assert "connector_lookup" not in selector_http.payloads[0]["eligible_labels"]
    planner_catalog = {
        str(item["name"])
        for item in controller._contract_operation_catalog(result.state.goal)
    }
    assert "web_search" not in planner_catalog
    assert "connector_lookup" not in planner_catalog
    assert selector_http.payloads[0]["bootstrap"].startswith(
        "SelectorIntentMenuV1: "
    )
    assert "\nSelectorIntentRoleV1: " in selector_http.payloads[0]["bootstrap"]
    assert selector_http.payloads[1]["bootstrap"] == ""
    selector_wire = json.dumps(selector_http.payloads, ensure_ascii=False)
    assert '"parameters"' not in selector_wire
    assert '"arguments"' not in selector_wire
    assert '"result"' not in selector_wire
    second_step = json.loads(
        selector_http.payloads[1]["step"].removeprefix("SelectorIntentPromptV1: ")
    )
    stage = json.loads(
        second_step["stage_objective"].removeprefix("CurrentDirectStageV1: ")
    )
    assert stage["latest_action"]["operation"] == "write_file"
    assert stage["latest_action"]["success"] is True

    selector_head = result.state.model_states[result.state.lane_head("selector")]
    executor_head = result.state.model_states[result.state.lane_head("executor")]
    assert selector_head.lane_kind is ModelLaneKind.SELECTOR
    assert selector_head.model == "rwkv7-g1i-2.9b-test"
    assert executor_head.lane_kind is ModelLaneKind.ACTION
    assert executor_head.model == "rwkv7-g1i-13.3b-test"
    assert selector_head.checkpoint_id != executor_head.checkpoint_id

    selections = list(result.state.tool_selections.values())
    assert len(selections) == 2
    assert all(item.status is ToolSelectionStatus.CONSUMED for item in selections)
    assert all(len(item.raw_selection["logits"]) == 25 for item in selections)
    assert all(item.raw_selection["postprocessed"] is False for item in selections)
    assert all(item.raw_selection["generated_text"] is False for item in selections)
    projected_actions = _project_atom_actions(result.state)
    assert len(projected_actions) == 1
    selected_action = projected_actions[0]
    write_selection = next(
        item for item in selections if item.selected_operation == "write_file"
    )
    assert selected_action["decision_id"] == write_selection.consumed_decision_id
    assert selected_action["selection_id"] == write_selection.selection_id
    assert selected_action["selected_operation"] == selected_action["operation"]
    assert selected_action["contract_digest"] == (
        write_selection.atom_execution_contract_digest
    )
    decision_bindings = _project_tool_selection_decision_bindings(result.state)
    assert len(decision_bindings) == 2
    write_binding = next(
        item for item in decision_bindings if item["selected_operation"] == "write_file"
    )
    final_binding = next(
        item for item in decision_bindings if item["selected_operation"] == "final_answer"
    )
    assert write_binding["decision_accepted"] is True
    assert write_binding["action_id"] == selected_action["action_id"]
    assert final_binding["decision_accepted"] is True
    assert final_binding["action_id"] == ""
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("exact_tool_selection_staged") == 2
    assert event_types.count("exact_tool_selection_committed") == 0
    assert all(item.authorizes_execution is False for item in selections)
    assert event_types.count("tool_selection_accepted") == 0
    assert event_types.count("tool_schema_disclosed") == 2
    assert event_types.count("model_call_accepted") == 2


def test_selector_cache_miss_rebuilds_from_current_authoritative_projection(
    tmp_path: Path,
) -> None:
    controller, _, workspace, _, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        active_operations=("write_file",),
        missing_selector_parent_once=True,
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(selector_http.payloads) == 3
    assert selector_http.payloads[1]["parent"] is not None
    assert selector_http.payloads[2]["parent"] is None
    assert selector_http.payloads[2]["bootstrap"].startswith(
        "SelectorIntentMenuV1: "
    )
    rebuilt = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "selector_state_cache_rebuilt"
    ]
    assert len(rebuilt) == 1
    assert rebuilt[0].payload["source"] == (
        "authoritative_goal_action_projection"
    )
    assert rebuilt[0].payload["historical_prompt_replayed"] is False
    assert rebuilt[0].payload["cache_authority"] is False


def test_goal_policy_enables_network_selector_classes_without_changing_class_order(
    tmp_path: Path,
) -> None:
    controller, _, workspace, _, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        goal_retrieval_mode=NetworkPolicyMode.AUTO_PUBLIC,
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert {"web_search", "connector_lookup"} <= set(
        selector_http.payloads[0]["eligible_labels"]
    )
    planner_catalog = {
        str(item["name"])
        for item in controller._contract_operation_catalog(result.state.goal)
    }
    assert {"web_search", "connector_lookup"} <= planner_catalog
    bootstrap = selector_http.payloads[0]["bootstrap"]
    menu_text = bootstrap.split("\nSelectorIntentRoleV1: ", 1)[0]
    menu = json.loads(menu_text.removeprefix("SelectorIntentMenuV1: "))
    assert tuple(item["name"] for item in menu["tools"]) == (
        NETWORK_EXACT_TOOL_LABELS
    )


def test_g1j_executor_retry_uses_only_executor_args_tool_call_format(
    tmp_path: Path,
) -> None:
    requirement = "Create hello.txt containing exactly hello."
    controller, _, workspace, executor, _ = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        executor_outputs=[
            _call(
                "write_file",
                path="hello.txt",
                content="hello",
                invented=True,
            ),
            _call("write_file", path="hello.txt", content="hello"),
            _call("final_answer", text="Created hello.txt."),
        ],
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert result.state.protocol_rejections == 1
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    retry_prompt = executor.prompts[1]
    prefix, payload_text = retry_prompt.rsplit("ExecutorArgsPromptV1: ", 1)
    assert not prefix.rstrip().endswith("Assistant: ```json")
    assert prefix.endswith("\n\n")
    payload_text = payload_text.split("\n\n**Tool Call:**", 1)[0]
    payload = json.loads(payload_text)
    assert payload["role"] == "executor_args"
    assert payload["current_requirement"] == requirement
    assert payload["selected_operation"] == "write_file"
    assert retry_prompt.endswith("\n\n**Tool Call:**\n\n```json\n")
    assert "\n\nUser: Executor retry input: " not in retry_prompt


def test_action_budget_terminal_answer_uses_independent_selector_handoff(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        active_operations=("write_file",),
    )
    controller.max_actions = 1

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(executor.prompts) == 2
    assert len(selector_http.payloads) == 2
    assert selector_http.payloads[1]["eligible_labels"] == ["final_answer"]
    assert [
        result.state.tool_selections[selection_id].selected_operation
        for selection_id in sorted(result.state.tool_selections)
    ] == ["write_file", "final_answer"]
    disclosures = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "tool_schema_disclosed"
    ]
    assert len(disclosures) == 2
    assert all(item.payload.get("selection_id") for item in disclosures)


class _CrashBeforeDisclosureModel(LongHorizonModel):
    crash_once = True

    def _disclose_selected_tool(self, *args, **kwargs):
        if self.crash_once and kwargs.get("selection") is not None:
            self.crash_once = False
            raise RuntimeError("injected crash after committed selection")
        return super()._disclose_selected_tool(*args, **kwargs)


def test_committed_selection_resumes_without_reselecting(tmp_path: Path) -> None:
    controller, store, workspace, _, selector_http = _build(
        tmp_path,
        selector_operations=["write_file", "final_answer"],
        model_class=_CrashBeforeDisclosureModel,
    )

    with pytest.raises(RuntimeError, match="injected crash"):
        controller.run("RUN")
    interrupted = store.load("RUN")
    assert interrupted.pending_selection_id == "NSEL-0001"
    assert len(selector_http.payloads) == 1

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(selector_http.payloads) == 2
    first = result.state.tool_selections["NSEL-0001"]
    assert first.status is ToolSelectionStatus.CONSUMED


def test_selector_abstain_logit_is_masked_outside_eligible_contract(
    tmp_path: Path,
) -> None:
    controller, _, workspace, executor, selector_http = _build(
        tmp_path,
        selector_operations=["ABSTAIN", "final_answer"],
        active_operations=("write_file",),
        selector_min_actions=1,
    )

    result = controller.run("RUN")

    assert result.state.status is RunStatus.COMPLETED
    assert (workspace / "hello.txt").read_text(encoding="utf-8") == "hello"
    assert len(selector_http.payloads) == 2
    assert len(executor.prompts) == 2
    rejected = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "exact_tool_selection_rejected"
    ]
    assert rejected == []
    assert all(
        "ABSTAIN" not in payload["eligible_labels"]
        for payload in selector_http.payloads
    )
    first = next(iter(result.state.tool_selections.values()))
    assert first.selected_operation == "write_file"
    assert first.raw_selection["postprocessed"] is False
    assert len(first.raw_selection["logits"]) == 25
