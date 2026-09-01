from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION
from rwkv_lh.model_session import ModelSession
from rwkv_lh.product_runtime import build_product_controller
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    runtime_policy_document,
)
from rwkv_lh.runtime.executor_profiles import executor_profile_binding_for_run
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import GoalState, ModelLaneKind, RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy


GENERAL_SHA = "a" * 64
NETWORK_SHA = "b" * 64
MODEL_SHA = "c" * 64


class _Client:
    model_name = "rwkv-13.3b"


def _settings() -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:29613/v1",
        api_key="",
        model="rwkv-13.3b",
        model_sha256=MODEL_SHA,
        state_transport="prompt_replay",
        state_profile_id="executor-general",
        state_profile_sha256=GENERAL_SHA,
        state_profile_delivery="request",
    )


def _state(tmp_path: Path, mode: NetworkPolicyMode) -> RunState:
    workspace = tmp_path / mode.value
    workspace.mkdir()
    goal = GoalState.create(
        request="Complete the fixed task.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(mode=mode)
        ),
    )
    return RunState(run_id=f"RUN-{mode.value}", goal=goal)


def _active_environment() -> dict[str, str]:
    return {
        "RWKV_EXECUTOR_PROFILE_ROUTING": "retrieval-policy-v1",
        "RWKV_NETWORK_EXECUTOR_STATE_PROFILE_ID": "executor-network",
        "RWKV_NETWORK_EXECUTOR_STATE_PROFILE_SHA256": NETWORK_SHA,
    }


def test_disabled_routing_preserves_configured_profile_for_network_goal(
    tmp_path: Path,
) -> None:
    binding = executor_profile_binding_for_run(
        _state(tmp_path, NetworkPolicyMode.AUTO_PUBLIC),
        base_settings=_settings(),
        environ={},
    )

    assert binding.routing_mode == "disabled"
    assert binding.role == "configured_default"
    assert binding.settings.state_profile_id == "executor-general"
    assert binding.profile_switches_within_run == 0


@pytest.mark.parametrize(
    ("mode", "expected_role", "expected_id", "expected_sha"),
    [
        (NetworkPolicyMode.OFFLINE, "general", "executor-general", GENERAL_SHA),
        (
            NetworkPolicyMode.AUTO_PUBLIC,
            "network",
            "executor-network",
            NETWORK_SHA,
        ),
        (
            NetworkPolicyMode.EXPLICIT_EGRESS,
            "network",
            "executor-network",
            NETWORK_SHA,
        ),
    ],
)
def test_active_routing_binds_one_profile_from_immutable_goal_policy(
    tmp_path: Path,
    mode: NetworkPolicyMode,
    expected_role: str,
    expected_id: str,
    expected_sha: str,
) -> None:
    binding = executor_profile_binding_for_run(
        _state(tmp_path, mode),
        base_settings=_settings(),
        environ=_active_environment(),
    )

    assert binding.role == expected_role
    assert binding.settings.state_profile_id == expected_id
    assert binding.settings.state_profile_sha256 == expected_sha
    assert binding.settings.state_profile_delivery == "request"
    assert binding.profile_switches_within_run == 0


def test_active_routing_rejects_partial_network_identity(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="configured together"):
        executor_profile_binding_for_run(
            _state(tmp_path, NetworkPolicyMode.AUTO_PUBLIC),
            base_settings=_settings(),
            environ={
                "RWKV_EXECUTOR_PROFILE_ROUTING": "retrieval-policy-v1",
                "RWKV_NETWORK_EXECUTOR_STATE_PROFILE_ID": "executor-network",
            },
        )


def test_resume_rejects_task_level_profile_switch_before_model_use(
    tmp_path: Path,
) -> None:
    state = _state(tmp_path, NetworkPolicyMode.AUTO_PUBLIC)
    checkpoint = ModelSession(_Client(), settings=_settings()).bootstrap(
        ModelLaneKind.ACTION,
        "Complete the fixed task.",
        [FINAL_ANSWER_DEFINITION],
        lane_id="LANE-ACTION",
    )
    state.model_states[checkpoint.checkpoint_id] = checkpoint
    state.action_lane_checkpoint_id = checkpoint.checkpoint_id

    with pytest.raises(ValueError, match="task-level profile binding"):
        executor_profile_binding_for_run(
            state,
            base_settings=_settings(),
            environ=_active_environment(),
        )


def test_product_executor_and_auditor_share_deployment_binding_not_state(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for key, value in _active_environment().items():
        monkeypatch.setenv(key, value)
    monkeypatch.setattr(
        "rwkv_lh.runtime.executor_profiles.get_runtime_settings",
        _settings,
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime._product_tool_selector",
        lambda: object(),
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.RuntimeSettings.for_role",
        lambda role, *, fallback: replace(
            fallback,
            state_profile_id="",
            state_profile_sha256="",
            state_profile_delivery="request",
        ),
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.OpenAICompatibleSupervisorClient",
        lambda audit_hook=None: object(),
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.supervisor_policy_from_env",
        lambda mode: SupervisorPolicy(mode=mode),
    )
    workspace = tmp_path / "product-workspace"
    workspace.mkdir()
    goal = GoalState.create(
        request="Find public evidence and save it.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(mode=NetworkPolicyMode.AUTO_PUBLIC),
            supervisor_mode="stateful_goal",
        ),
    )
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(goal, "RUN-PRODUCT-PROFILE")
    controller = build_product_controller(
        store,
        state,
        state_root=tmp_path / "runtime",
    )
    assert controller.model.session.settings.state_profile_id == "executor-network"
    assert controller.model.auditor_session.settings is not (
        controller.model.session.settings
    )
    assert controller.model.auditor_session.settings.state_profile_id == ""
    assert controller.model.auditor_session.settings.state_profile_sha256 == ""
    assert controller.model.auditor_session is not controller.model.session
    assert controller.atom_worker_pool is None
