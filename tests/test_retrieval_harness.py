from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness, ActionResult, HarnessError
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.retrieval import (
    EgressProvenance,
    EvidenceRecord,
    EvidenceSpan,
    ExternalEvidenceEnvelope,
    ExternalEvidenceRequestMismatch,
    FrozenRetrievalBackend,
    NetworkPolicy,
    NetworkPolicyMode,
    SourceObject,
    build_retrieval_actions,
    fold_retrieval_ledger,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import ActionStatus, GoalState, TaskAction
from rwkv_lh.store import LongHorizonStore


def _goal(tmp_path: Path) -> GoalState:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return GoalState.create(
        request="Find the public frozen record.",
        constraints=("workspace only",),
        workspace_root=workspace,
    )


def _envelope(
    *,
    tool: str = "web_search",
    arguments: dict | None = None,
) -> ExternalEvidenceEnvelope:
    request = arguments or {"query": "Opal Garden status", "max_results": 5}
    snapshot = "Official ledger: build-3134 is ready for staged deployment."
    span = EvidenceSpan.create(
        text="build-3134 is ready for staged deployment",
        locator={"start_char": 17, "end_char": 59},
    )
    record = EvidenceRecord.create(
        source_object=SourceObject.create(
            source_object_id="https://records.example.invalid/deployment-ledger",
            source_object_type="frozen_web_record",
            source_record_id="build-3134",
        ),
        snapshot_digest=hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
        exact_spans=(span,),
        url="https://records.example.invalid/deployment-ledger",
        title="routing metadata",
        retrieved_at="2026-08-25T00:00:00Z",
    )
    assert record.verify_snapshot(snapshot)
    return ExternalEvidenceEnvelope.create(
        tool=tool,
        request=request,
        status="evidence_committed",
        records=(record,),
        as_of="2026-08-25T00:00:00Z",
        provider_attempts=({"provider": "frozen", "status": "ok"},),
    )


def _public_provenance(_goal, _tool, arguments):
    return {
        key: EgressProvenance.MODEL_PUBLIC_QUERY
        for key, value in arguments.items()
        if isinstance(value, str) and value
    }


def _actions(
    envelope: ExternalEvidenceEnvelope | None = None,
    *,
    policy: NetworkPolicy | None = None,
    provenance_resolver=_public_provenance,
):
    selected = envelope or _envelope()
    backend = FrozenRetrievalBackend(
        {
            FrozenRetrievalBackend.request_key(
                selected.tool,
                {"query": "Opal Garden status", "max_results": 5},
            ): selected
        }
    )
    return build_retrieval_actions(
        backend=backend,
        network_policy=policy
        or NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=provenance_resolver,
        clock=lambda: datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
    )


def test_action_definition_keeps_capability_metadata_in_authoritative_contract(
    tmp_path: Path,
) -> None:
    harness = ActionHarness(
        sandbox_commands=False,
        actions=_actions(),
    )
    local = harness.action_definition_contract("read_file")
    web = harness.action_definition_contract("web_search")
    tool = {
        item["name"]: item for item in harness.g1i_tool_definitions()
    }["web_search"]

    assert local["capability_class"] == "local.workspace_read"
    assert local["network_access"] == "none"
    assert {
        key: web[key]
        for key in (
            "capability_class",
            "network_access",
            "data_boundary",
            "side_effect_class",
            "result_schema",
            "cache_policy",
            "recovery_policy",
            "evidence_output",
        )
    } == {
        "capability_class": "network.public_web",
        "network_access": "public_web",
        "data_boundary": "public_external",
        "side_effect_class": "external_read_only",
        "result_schema": "rwkv-lh.external-evidence.v1",
        "cache_policy": "per_run_immutable_snapshot",
        "recovery_policy": "resume_committed_snapshot_or_do_not_replay_unknown",
        "evidence_output": True,
    }
    assert tool["parameters"] == harness.definition(
        "web_search"
    ).parameters_schema()
    assert "capability_class" not in tool


def test_external_evidence_round_trip_is_content_addressed_and_exact() -> None:
    envelope = _envelope()
    restored = ExternalEvidenceEnvelope.from_dict(envelope.to_dict())
    assert restored == envelope
    assert restored.action_id == ""
    assert restored.bind_action("A00001").action_id == "A00001"

    damaged = envelope.to_dict()
    damaged["records"][0]["exact_spans"][0]["text"] = "invented"
    with pytest.raises(ValueError, match="span id"):
        ExternalEvidenceEnvelope.from_dict(damaged)

    rerouted = envelope.to_dict()
    rerouted["route_id"] = "ROUTE-invented"
    with pytest.raises(ValueError, match="route id"):
        ExternalEvidenceEnvelope.from_dict(rerouted)

    retitled = envelope.to_dict()
    retitled["records"][0]["title"] = "tampered routing metadata"
    with pytest.raises(ValueError, match="record id"):
        ExternalEvidenceEnvelope.from_dict(retitled)

    malformed = envelope.to_dict()
    malformed["records"].append("not-an-object")
    with pytest.raises(ValueError, match="records must contain only objects"):
        ExternalEvidenceEnvelope.from_dict(malformed)


def test_action_boundary_rejects_mismatched_execute_and_recovery_envelopes(
    tmp_path: Path,
) -> None:
    class MismatchedBackend:
        provider_name = "mismatched-fixture"

        def __init__(self) -> None:
            self.execute_calls = 0
            self.recover_calls = 0

        def execute(self, _tool: str, _arguments: dict) -> ExternalEvidenceEnvelope:
            self.execute_calls += 1
            return _envelope(arguments={"query": "request B", "max_results": 5})

        def recover(self, _tool: str, _arguments: dict) -> ExternalEvidenceEnvelope:
            self.recover_calls += 1
            return _envelope(arguments={"query": "request B", "max_results": 5})

    backend = MismatchedBackend()
    harness = ActionHarness(
        sandbox_commands=False,
        actions=build_retrieval_actions(
            backend=backend,
            network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
            provenance_resolver=_public_provenance,
        ),
    )
    action = TaskAction("web_search", {"query": "request A"})

    executed = harness.execute(action, _goal(tmp_path))
    recovered = harness.recover_committed_action(action, _goal(tmp_path))

    assert executed.success is False
    assert executed.error["type"] == ExternalEvidenceRequestMismatch.__name__
    assert recovered is not None and recovered.success is False
    assert recovered.error["type"] == ExternalEvidenceRequestMismatch.__name__
    assert recovered.metadata["committed_snapshot_recovery_attempted"] is True
    assert "recovered_committed_snapshot" not in recovered.metadata
    assert backend.execute_calls == 1
    assert backend.recover_calls == 1


def test_exact_evidence_preserves_literal_whitespace_and_snapshot_digest() -> None:
    snapshot = "prefix  exact evidence  suffix"
    literal = "  exact evidence  "
    span = EvidenceSpan.create(text=literal, locator={"start_char": 6})
    record = EvidenceRecord.create(
        source_object=SourceObject.create(
            source_object_id="fixture:literal",
            source_object_type="frozen_fixture",
        ),
        snapshot_digest=hashlib.sha256(snapshot.encode("utf-8")).hexdigest(),
        exact_spans=(span,),
    )

    assert span.text == literal
    assert record.verify_snapshot(snapshot)
    assert not record.verify_snapshot(snapshot + " changed")


def test_network_policy_is_fail_closed_and_never_rewrites() -> None:
    arguments = {"query": "public status", "max_results": 5}
    public = {"query": EgressProvenance.MODEL_PUBLIC_QUERY}
    secret = {"query": EgressProvenance.SECRET}

    offline = NetworkPolicy(NetworkPolicyMode.OFFLINE).authorize(
        tool="web_search", arguments=arguments, provenance=public
    )
    assert not offline.allowed and offline.reason == "network_disabled"

    allowed = NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC).authorize(
        tool="web_search", arguments=arguments, provenance=public
    )
    assert allowed.allowed and not allowed.controller_rewritten

    missing = NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC).authorize(
        tool="web_search", arguments=arguments, provenance={}
    )
    assert not missing.allowed and missing.reason == "egress_provenance_missing"

    invalid = NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC).authorize(
        tool="web_search", arguments=arguments, provenance={"query": "invented"}
    )
    assert not invalid.allowed and invalid.reason == "egress_provenance_invalid"

    approval_required = NetworkPolicy(
        NetworkPolicyMode.EXPLICIT_EGRESS,
    ).authorize(
        tool="web_search",
        arguments=arguments,
        provenance={"query": EgressProvenance.WORKSPACE_PUBLIC},
    )
    assert not approval_required.allowed
    assert approval_required.reason == "explicit_egress_approval_required"

    approved = NetworkPolicy(
        NetworkPolicyMode.EXPLICIT_EGRESS,
        explicit_approval=True,
    ).authorize(
        tool="web_search",
        arguments=arguments,
        provenance={"query": EgressProvenance.WORKSPACE_PUBLIC},
    )
    assert approved.allowed

    rejected = NetworkPolicy(
        NetworkPolicyMode.EXPLICIT_EGRESS,
        explicit_approval=True,
    ).authorize(tool="web_search", arguments=arguments, provenance=secret)
    assert not rejected.allowed
    assert rejected.reason == "sensitive_egress_forbidden"
    assert rejected.rejected_fields == ("query",)

    assert NetworkPolicy("auto_public").mode == NetworkPolicyMode.AUTO_PUBLIC
    with pytest.raises(ValueError):
        NetworkPolicy("invented")


def test_fake_retrieval_executes_through_normal_harness_boundary(
    tmp_path: Path,
) -> None:
    harness = ActionHarness(sandbox_commands=False, actions=_actions())
    normalized = harness.normalize_action(
        TaskAction("web_search", {"query": "Opal Garden status"})
    )
    result = harness.execute(normalized, _goal(tmp_path))

    assert normalized.arguments == {
        "query": "Opal Garden status",
        "max_results": 5,
    }
    assert result.success
    assert result.metadata["provider"] == "frozen-fixture"
    assert result.metadata["external_evidence"]["action_id"] == ""
    assert len(result.evidence) == 1

    with pytest.raises(HarnessError, match="must be one of"):
        harness.normalize_action(
            TaskAction(
                "connector_lookup",
                {"operation": "invented", "query": "x"},
            )
        )


@pytest.mark.parametrize(
    "forbidden_label",
    [
        EgressProvenance.SECRET,
        EgressProvenance.WORKSPACE_SENSITIVE,
        EgressProvenance.TOOL_UNTRUSTED,
        EgressProvenance.UNKNOWN,
    ],
)
def test_forbidden_egress_is_rejected_before_backend_execution(
    tmp_path: Path,
    forbidden_label: EgressProvenance,
) -> None:
    def sensitive(_goal, _tool, arguments):
        return {
            key: forbidden_label
            for key, value in arguments.items()
            if isinstance(value, str) and value
        }

    harness = ActionHarness(
        sandbox_commands=False,
        actions=_actions(provenance_resolver=sensitive),
    )
    action = harness.normalize_action(
        TaskAction("web_search", {"query": "sk-local-secret"})
    )
    result = harness.execute(action, _goal(tmp_path))

    assert not result.success
    assert result.outcome_type == "policy_rejected"
    assert result.error == {
        "type": "NetworkPolicyRejected",
        "message": "sensitive_egress_forbidden",
        "rejected_fields": ["query"],
    }
    assert result.metadata["network_policy"]["controller_rewritten"] is False


def test_deterministic_tools_are_explicit_and_bounded(tmp_path: Path) -> None:
    harness = ActionHarness(sandbox_commands=False, actions=_actions())
    goal = _goal(tmp_path)

    calculator = harness.execute(
        harness.normalize_action(
            TaskAction("calculator", {"expression": "(17 * 23 + 11) / 2"})
        ),
        goal,
    )
    assert json.loads(calculator.output)["value"] == 201

    unsafe = harness.execute(
        harness.normalize_action(
            TaskAction("calculator", {"expression": "__import__('os')"})
        ),
        goal,
    )
    assert not unsafe.success

    date_result = harness.execute(
        harness.normalize_action(
            TaskAction(
                "date_diff",
                {"date_a": "2024-02-28", "date_b": "2024-03-01"},
            )
        ),
        goal,
    )
    assert json.loads(date_result.output)["value"] == 2

    clock_result = harness.execute(
        harness.normalize_action(
            TaskAction("current_time", {"timezone": "Asia/Shanghai"})
        ),
        goal,
    )
    assert json.loads(clock_result.output)["value"] == "2026-08-25T20:00:00+08:00"


@dataclass
class _Response:
    content: str
    finish_reason: str = "stop"


class _QueueClient:
    model_name = "test-rwkv"

    def __init__(self, calls: list[dict]):
        self.calls = [
            json.dumps(item, ensure_ascii=False, separators=(",", ":"))
            for item in calls
        ]
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        del max_tokens, stop
        self.prompts.append(prompt)
        return _Response(self.calls.pop(0))


class _RetrievalProcessLoss(RuntimeError):
    rwkv_lh_process_loss = True


class _RecoverableRetrievalBackend:
    provider_name = "recoverable-fixture"

    def __init__(self, envelope: ExternalEvidenceEnvelope) -> None:
        self.envelope = envelope
        self.execute_calls = 0
        self.recover_calls = 0

    def execute(self, tool: str, arguments: dict) -> ExternalEvidenceEnvelope:
        self.execute_calls += 1
        assert tool == self.envelope.tool
        assert FrozenRetrievalBackend.request_key(tool, arguments) == (
            self.envelope.request_digest
        )
        return self.envelope

    def recover(
        self, tool: str, arguments: dict
    ) -> ExternalEvidenceEnvelope | None:
        self.recover_calls += 1
        assert FrozenRetrievalBackend.request_key(tool, arguments) == (
            self.envelope.request_digest
        )
        return self.envelope


class _CrashAfterCommittedRetrievalHarness(ActionHarness):
    def __init__(self, *, actions) -> None:
        super().__init__(sandbox_commands=False, actions=actions)
        self.crashed = False

    def execute(self, action: TaskAction, goal: GoalState) -> ActionResult:
        result = super().execute(action, goal)
        if action.action_type == "web_search" and not self.crashed:
            self.crashed = True
            raise _RetrievalProcessLoss("crash after route snapshot commit")
        return result


class _CrashBeforeRetrievalHarness(ActionHarness):
    def __init__(self, *, actions) -> None:
        super().__init__(sandbox_commands=False, actions=actions)
        self.crashed = False

    def execute(self, action: TaskAction, goal: GoalState) -> ActionResult:
        if action.action_type == "web_search" and not self.crashed:
            self.crashed = True
            raise _RetrievalProcessLoss("crash before route snapshot commit")
        return super().execute(action, goal)


def test_progressive_controller_binds_external_evidence_to_rwkv_action_id(
    tmp_path: Path,
) -> None:
    harness = ActionHarness(sandbox_commands=False, actions=_actions())
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="progressive",
    )
    client = _QueueClient(
        [
            {"function": "select_tool", "params": {"name": "web_search"}},
            {
                "function": "web_search",
                "params": {"query": "Opal Garden status"},
            },
            {"function": "select_tool", "params": {"name": "final_answer"}},
            {"function": "final_answer", "params": {"text": "Done."}},
        ]
    )
    model = LongHorizonModel(
        ModelSession(client, settings=settings),
        harness=harness,
    )
    store = LongHorizonStore(tmp_path / "state")
    goal = model.create_literal_goal(
        "Find the frozen public status.",
        str(workspace),
    )
    store.create_run(goal, "RUN")
    result = LongHorizonController(
        store,
        model=model,
        harness=harness,
    ).run("RUN")

    action = result.state.actions["A00001"]
    assert action.status == ActionStatus.SUCCEEDED
    assert action.result is not None
    envelope = action.result["metadata"]["external_evidence"]
    assert envelope["action_id"] == action.action_id
    assert envelope["tool"] == "web_search"
    assert json.loads(action.result["output"]) == envelope
    assert result.final_output == "Done."
    assert [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ].count("tool_selection_accepted") == 2
    assert client.calls == []
    assert '"selected_operation":"web_search"' in client.prompts[1]
    assert '"required":["query"]' in client.prompts[1]
    ledger = fold_retrieval_ledger(result.state)
    assert ledger["routes"] == [
        {
            "action_id": action.action_id,
            "route_id": envelope["route_id"],
            "tool": "web_search",
            "request_digest": envelope["request_digest"],
            "status": "evidence_committed",
            "as_of": envelope["as_of"],
            "record_ids": [envelope["records"][0]["evidence_record_id"]],
        }
    ]
    assert set(ledger["records"]) == {envelope["records"][0]["evidence_record_id"]}


def test_recovery_reads_committed_retrieval_snapshot_without_provider_replay(
    tmp_path: Path,
) -> None:
    envelope = _envelope()
    backend = _RecoverableRetrievalBackend(envelope)
    actions = build_retrieval_actions(
        backend=backend,
        network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=_public_provenance,
        clock=lambda: datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc),
    )
    harness = _CrashAfterCommittedRetrievalHarness(actions=actions)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="progressive",
    )
    client = _QueueClient(
        [
            {"function": "select_tool", "params": {"name": "web_search"}},
            {
                "function": "web_search",
                "params": {"query": "Opal Garden status"},
            },
            {"function": "select_tool", "params": {"name": "final_answer"}},
            {"function": "final_answer", "params": {"text": "Recovered."}},
        ]
    )
    model = LongHorizonModel(ModelSession(client, settings=settings), harness=harness)
    store = LongHorizonStore(tmp_path / "state")
    goal = model.create_literal_goal("Find the frozen public status.", str(workspace))
    store.create_run(goal, "RUN")
    controller = LongHorizonController(store, model=model, harness=harness)

    with pytest.raises(_RetrievalProcessLoss):
        controller.run("RUN")
    crashed = store.load("RUN")
    assert crashed.actions["A00001"].status == ActionStatus.RUNNING

    resumed = controller.resume("RUN")

    assert resumed.state.status.value == "completed"
    assert resumed.final_output == "Recovered."
    assert backend.execute_calls == 1
    assert backend.recover_calls == 1
    action = resumed.state.actions["A00001"]
    assert action.status == ActionStatus.SUCCEEDED
    assert action.result is not None
    assert action.result["metadata"]["recovered_committed_snapshot"] is True
    assert any(
        event.event_type == "committed_snapshot_action_recovered"
        for event in resumed.state.causal_records.values()
    )


def test_recovery_never_replays_retrieval_when_snapshot_is_missing(tmp_path: Path) -> None:
    envelope = _envelope()

    class MissingSnapshotBackend(_RecoverableRetrievalBackend):
        def recover(self, tool: str, arguments: dict):
            self.recover_calls += 1
            return None

    backend = MissingSnapshotBackend(envelope)
    actions = build_retrieval_actions(
        backend=backend,
        network_policy=NetworkPolicy(NetworkPolicyMode.AUTO_PUBLIC),
        provenance_resolver=_public_provenance,
    )
    harness = _CrashBeforeRetrievalHarness(actions=actions)
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="progressive",
    )
    client = _QueueClient(
        [
            {"function": "select_tool", "params": {"name": "web_search"}},
            {
                "function": "web_search",
                "params": {"query": "Opal Garden status"},
            },
            {"function": "select_tool", "params": {"name": "final_answer"}},
            {
                "function": "final_answer",
                "params": {"text": "Snapshot was unavailable."},
            },
        ]
    )
    model = LongHorizonModel(ModelSession(client, settings=settings), harness=harness)
    store = LongHorizonStore(tmp_path / "state")
    goal = model.create_literal_goal("Find the frozen public status.", str(workspace))
    store.create_run(goal, "RUN")
    controller = LongHorizonController(store, model=model, harness=harness)

    with pytest.raises(_RetrievalProcessLoss):
        controller.run("RUN")
    resumed = controller.resume("RUN")

    assert resumed.state.status.value == "completed"
    assert backend.execute_calls == 0
    assert backend.recover_calls == 1
    action = resumed.state.actions["A00001"]
    assert action.status == ActionStatus.INTERRUPTED
    assert action.result is not None
    assert action.result["error"]["type"] == "InterruptedNonIdempotentAction"


def test_progressive_worker_reselects_after_typed_network_policy_rejection(
    tmp_path: Path,
) -> None:
    def sensitive(_goal, _tool, arguments):
        return {
            key: EgressProvenance.SECRET
            for key, value in arguments.items()
            if isinstance(value, str) and value
        }

    harness = ActionHarness(
        sandbox_commands=False,
        actions=_actions(provenance_resolver=sensitive),
    )
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    settings = RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv",
        max_model_len=16384,
        context_safety_margin=32,
        bos_token_count=1,
        tool_disclosure_mode="progressive",
    )
    client = _QueueClient(
        [
            {"function": "select_tool", "params": {"name": "web_search"}},
            {
                "function": "web_search",
                "params": {"query": "sk-local-secret"},
            },
            {"function": "select_tool", "params": {"name": "final_answer"}},
            {
                "function": "final_answer",
                "params": {"text": "I did not send the secret."},
            },
        ]
    )
    model = LongHorizonModel(ModelSession(client, settings=settings), harness=harness)
    store = LongHorizonStore(tmp_path / "state")
    goal = model.create_literal_goal("Do not leak this secret.", str(workspace))
    store.create_run(goal, "RUN")

    result = LongHorizonController(store, model=model, harness=harness).run("RUN")

    rejected = result.state.actions["A00001"]
    assert rejected.status == ActionStatus.FAILED
    assert rejected.result is not None
    assert rejected.result["outcome_type"] == "policy_rejected"
    assert result.final_output == "I did not send the secret."
    assert "NetworkPolicyRejected" in client.prompts[2]
    assert '"controller_rewritten": false' in client.prompts[2]
