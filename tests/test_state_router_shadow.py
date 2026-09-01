from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.harness import ActionHarness
from rwkv_lh.product_runtime import build_product_controller
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    build_product_harness,
    runtime_policy_document,
)
from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    CausalEvent,
    CausalEventDraft,
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.state_router.model import MultiHeadMLPArtifact
from rwkv_lh.state_router.protocol import HEAD_LABELS, resolve_router_output
from rwkv_lh.state_router.shadow import (
    DEFAULT_SHADOW_HEAD,
    LocalShadowObserver,
    ShadowController,
    ShadowPrediction,
    _router_input,
    observed_main_behavior,
    read_shadow_records,
    shadow_enabled,
    shadow_log_path,
    shadow_policy,
    wrap_controller_for_shadow,
)
from rwkv_lh.store import LongHorizonStore
from scripts.run_state_router_shadow_canary_v1 import (
    artifact_manifest,
    logical_state_manifest,
)


def _state(tmp_path: Path, *, mode: str = "shadow", run_id: str = "SHADOW-TEST") -> RunState:
    workspace = tmp_path / f"workspace-{run_id}"
    workspace.mkdir()
    policy = runtime_policy_document(
        RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE),
        state_router_mode=mode,
    )
    return RunState(
        run_id=run_id,
        goal=GoalState.create(
            request="Read input.txt.",
            constraints=[],
            workspace_root=workspace,
            runtime_policy=policy,
        ),
    )


def _successful_action(operation: str, sequence: int = 1) -> ActionRecord:
    action = TaskAction(operation, {})
    return ActionRecord(
        action_id=f"A{sequence:05d}",
        sequence=sequence,
        status=ActionStatus.SUCCEEDED,
        action_type=operation,
        arguments={},
        wire_arguments={},
        action_fingerprint=action_fingerprint(action),
        idempotency_key=f"idem-{sequence}",
        decision_id=f"D-{sequence}",
        request_id=f"MR-{sequence}",
        started_at=utc_now(),
        ended_at=utc_now(),
        result={"success": True, "output": "SECRET TOOL BODY"},
        outcome_type="success",
    )


def _probabilities(router_input) -> dict[str, dict[str, float]]:
    winners = {
        "context_mode": router_input.mode.value,
        "execution_phase": "evidence_missing",
        "route_family": "local",
        "network_recommendation": "network_not_required",
    }
    return {
        head: {
            label: 0.99 if label == winners[head] else 0.01 / (len(labels) - 1)
            for label in labels
        }
        for head, labels in HEAD_LABELS.items()
    }


def _runner(router_input):
    artifact = MultiHeadMLPArtifact.load(DEFAULT_SHADOW_HEAD)
    return resolve_router_output(
        router_input,
        _probabilities(router_input),
        model_hash=artifact.model_hash,
        head_hash=artifact.head_hash,
    ).to_dict()


def test_shadow_runtime_policy_is_explicit_and_default_policy_is_unchanged() -> None:
    config = RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE)
    baseline = runtime_policy_document(config)
    assert "state_router" not in baseline
    assert shadow_policy() is None
    enabled = runtime_policy_document(config, state_router_mode="shadow")
    assert enabled["state_router"] == {
        "schema_version": "rwkv-lh.state-router-runtime-policy.v1",
        "mode": "shadow",
    }
    with pytest.raises(ValueError, match="disabled or shadow"):
        runtime_policy_document(config, state_router_mode="active")


def test_shadow_input_projection_is_mechanical_and_excludes_tool_outputs(tmp_path: Path) -> None:
    state = _state(tmp_path)
    fresh = _router_input(state, "SHADOW-ONE")
    assert fresh.mode.value == "fresh"
    assert fresh.summary is None
    assert fresh.policy_state.value == "network_denied"
    state.status = RunStatus.RUNNING
    state.actions["A00001"] = _successful_action("read_file")
    continued = _router_input(state, "SHADOW-TWO", force_continuation=True)
    assert continued.mode.value == "continuation"
    assert continued.evidence_state.value == "evidence_partial"
    assert "read_file" in str(continued.summary)
    assert "SECRET TOOL BODY" not in str(continued.summary)


def test_observed_behavior_uses_harness_metadata_not_tool_result_body(tmp_path: Path) -> None:
    state = _state(tmp_path)
    state.status = RunStatus.COMPLETED
    state.actions["A00001"] = _successful_action("read_file")
    state.actions["A00002"] = _successful_action("calculator", 2)
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE),
        snapshot_root=tmp_path / "snapshots",
        sandbox_commands=False,
    )
    behavior = observed_main_behavior(state, harness)
    assert behavior["route_family"] == "mixed"
    assert behavior["network_recommendation"] == "network_not_required"
    assert "SECRET TOOL BODY" not in str(behavior)


def test_contract_graph_child_actions_drive_shadow_input_and_observed_route(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path)
    state.status = RunStatus.COMPLETED
    draft = CausalEventDraft.create(
        "atom_outcome_committed",
        {
            "atom_id": "NODE-web",
            "outcome": {
                "stage_id": "BATCH-1",
                "atom_id": "NODE-web",
                "model_request_count": 2,
                "actions": [
                    {
                        "action_id": "A00001",
                        "sequence": 1,
                        "operation": "web_search",
                        "status": "failed",
                        "result": {
                            "success": False,
                            "output": "SECRET CHILD TOOL BODY",
                            "outcome_type": "policy_rejected",
                            "error": {"type": "NetworkPolicyRejected"},
                        },
                        "artifact_refs": [],
                    }
                ],
            },
        },
        subject_id="NODE-web",
    )
    event = CausalEvent.create(
        event_id="CE-000001",
        run_id=state.run_id,
        sequence=1,
        parent_id=None,
        draft=draft,
    )
    state.causal_records[event.event_id] = event
    state.causal_order.append(event.event_id)
    harness = build_product_harness(
        config=RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
        snapshot_root=tmp_path / "snapshots-child",
        sandbox_commands=False,
    )

    routed = _router_input(state, "SHADOW-CHILD", force_continuation=True)
    behavior = observed_main_behavior(state, harness)

    assert routed.mode.value == "continuation"
    assert "web_search" in str(routed.summary)
    assert "SECRET CHILD TOOL BODY" not in str(routed.summary)
    assert behavior["route_family"] == "web"
    assert behavior["network_policy_rejections"] == 1
    assert behavior["actions"][0]["origin"] == "atom"


def test_shadow_wrapper_preserves_result_and_writes_non_authoritative_pair(tmp_path: Path) -> None:
    state = _state(tmp_path)
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(state.goal, state.run_id)
    harness = ActionHarness()
    result = SimpleNamespace(state=state, final_output="exact", transitions=0)

    class Controller:
        def __init__(self):
            self.store = store
            self.harness = harness

        def run(self, run_id: str):
            assert run_id == state.run_id
            return result

    observer = LocalShadowObserver(tmp_path, runner=_runner)
    wrapped = wrap_controller_for_shadow(
        Controller(), state, state_root=tmp_path, observer=observer
    )
    assert isinstance(wrapped, ShadowController)
    assert wrapped.run(state.run_id) is result
    records = read_shadow_records(tmp_path, state.run_id)["events"]
    assert [item["event_type"] for item in records] == ["prediction", "outcome"]
    assert records[0]["invocation_id"] == records[1]["invocation_id"]
    assert records[1]["comparison"]["tool_menu_unchanged"] is True
    assert all(value is False for item in records for value in item["influence"].values())
    assert all(item["shadow_only"] is True for item in records)
    assert "SECRET TOOL BODY" not in str(records)


def test_shadow_prediction_failure_does_not_change_controller_result(tmp_path: Path) -> None:
    state = _state(tmp_path)
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(state.goal, state.run_id)
    harness = ActionHarness()
    result = SimpleNamespace(state=state, final_output="still exact", transitions=0)

    class Controller:
        def __init__(self):
            self.store = store
            self.harness = harness

        def run(self, run_id: str):
            return result

    def failing_runner(_router_input):
        raise RuntimeError("router unavailable")

    wrapped = ShadowController(
        Controller(), LocalShadowObserver(tmp_path, runner=failing_runner)
    )
    assert wrapped.run(state.run_id) is result
    records = read_shadow_records(tmp_path, state.run_id)["events"]
    assert [item["event_type"] for item in records] == ["prediction_error", "outcome"]
    assert records[1]["comparison"]["router_available"] is False


def test_disabled_wrapper_returns_original_and_invalid_policy_is_rejected(tmp_path: Path) -> None:
    state = _state(tmp_path, mode="disabled")
    controller = object()
    assert wrap_controller_for_shadow(controller, state, state_root=tmp_path) is controller
    broken = state.goal.to_dict()
    broken["runtime_policy"]["state_router"] = {"mode": "shadow"}
    broken_goal = GoalState.create(
        request=state.goal.request,
        constraints=[],
        workspace_root=state.goal.workspace_root,
        runtime_policy=broken["runtime_policy"],
    )
    with pytest.raises(ValueError, match="schema"):
        shadow_enabled(RunState(run_id="BROKEN", goal=broken_goal))


def test_product_controller_rejects_retired_shadow_architecture(tmp_path: Path) -> None:
    state = _state(tmp_path, run_id="PRODUCT-SHADOW")
    store = LongHorizonStore(tmp_path / "product-state")
    state = store.create_run(state.goal, state.run_id)
    with pytest.raises(ValueError, match="state_router shadow is retired"):
        build_product_controller(store, state, state_root=tmp_path)


def test_shadow_logs_are_run_isolated_and_concurrent_appends_are_valid(tmp_path: Path) -> None:
    observer = LocalShadowObserver(tmp_path, runner=_runner)
    state_a = _state(tmp_path, run_id="RUN-A")
    state_b = _state(tmp_path, run_id="RUN-B")
    harness = ActionHarness()

    def write(state: RunState) -> ShadowPrediction:
        return observer.predict(state, harness)

    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(write, [state_a, state_a, state_b, state_b]))
    records_a = read_shadow_records(tmp_path, state_a.run_id)["events"]
    records_b = read_shadow_records(tmp_path, state_b.run_id)["events"]
    assert len(records_a) == len(records_b) == 2
    assert {item["run_id"] for item in records_a} == {state_a.run_id}
    assert {item["run_id"] for item in records_b} == {state_b.run_id}
    assert shadow_log_path(tmp_path, state_a.run_id) != shadow_log_path(tmp_path, state_b.run_id)
    assert all(len(item["record_digest"]) == 64 for item in records_a + records_b)


def test_canary_manifest_uses_logical_sqlite_identity_not_physical_wal(tmp_path: Path) -> None:
    state = _state(tmp_path, run_id="MANIFEST-RUN")
    run_root = tmp_path / "runs" / state.run_id
    store = LongHorizonStore(run_root / "state")
    store.create_run(state.goal, state.run_id)
    (run_root / "state" / "long_horizon.db-wal").touch(exist_ok=True)
    (tmp_path / "results.json").write_text("{}\n", encoding="utf-8")

    logical = logical_state_manifest(tmp_path)
    assert len(logical["databases"]) == 1
    assert logical["databases"][0]["integrity_check"] == "ok"
    stable = artifact_manifest(tmp_path)
    paths = {item["path"] for item in stable["files"]}
    assert "results.json" in paths
    assert not any("long_horizon.db" in path for path in paths)
