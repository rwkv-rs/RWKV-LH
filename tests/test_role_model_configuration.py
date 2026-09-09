from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.native_network_client import (
    NativeNetworkSelectorSettings,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.runtime.stack import RuntimeStackSettings
from rwkv_lh.supervisor_openai import SupervisorAPISettings
from scripts.run_rwkv_e2e_benchmark import (
    _build_stateful_goal_role_sessions,
    _close_stateful_goal_role_sessions,
    _goal_role_settings,
)


@pytest.mark.parametrize("supervisor_first", [True, False])
@pytest.mark.parametrize("process_override", [True, False])
def test_planner_and_runtime_share_one_default_env_in_either_load_order(
    tmp_path, monkeypatch, supervisor_first, process_override,
) -> None:
    import rwkv_lh.runtime.settings as runtime_module
    import rwkv_lh.supervisor_openai as supervisor_module

    for key in tuple(os.environ):
        if key.startswith(("RWKV_", "SUPERVISOR_")):
            monkeypatch.delenv(key)
    (tmp_path / ".env.local").write_text("\n".join((
        "RWKV_LH_PLANNER_BASE_URL=https://strong.invalid/v1",
        "RWKV_LH_PLANNER_API_KEY=fixture-key",
        "RWKV_LH_PLANNER_MODEL=strong-planner",
        "RWKV_LH_STAGE_CHECKER_MODEL=strong-stage-checker",
        "RWKV_LH_PLANNER_BACKEND_PROFILE=openai-compatible",
        "RWKV_LH_EXECUTOR_MODEL=rwkv-executor",
        "RWKV_LH_SELECTOR_MODEL=rwkv-selector",
        "SUPERVISOR_MAX_REVIEW_REPAIRS=2",
    )), encoding="utf-8")
    (tmp_path / ".env").write_text("\n".join((
        "RWKV_LH_PLANNER_BASE_URL=http://stale.invalid/v1",
        "RWKV_LH_PLANNER_API_KEY=stale-fixture-key",
        "RWKV_LH_PLANNER_MODEL=stale-rwkv-planner",
        "RWKV_LH_STAGE_CHECKER_MODEL=stale-rwkv-checker",
        "RWKV_LH_PLANNER_BACKEND_PROFILE=vllm-rwkv-native",
    )), encoding="utf-8")
    if process_override:
        monkeypatch.setenv("RWKV_LH_PLANNER_MODEL", "process-planner")
    original_loader = runtime_module.load_local_env
    loaded_paths = []

    def fixture_loader(path=runtime_module.DEFAULT_ENV_FILE, **kwargs):
        loaded_paths.append(Path(path).name)
        original_loader(tmp_path / Path(path).name, **kwargs)

    monkeypatch.setattr(runtime_module, "load_local_env", fixture_loader)
    monkeypatch.setattr(supervisor_module, "load_local_env", fixture_loader)
    if supervisor_first:
        planner = SupervisorAPISettings.from_env()
        runtime = RuntimeSettings.from_env()
    else:
        runtime = RuntimeSettings.from_env()
        planner = SupervisorAPISettings.from_env()
    policy = supervisor_module.supervisor_policy_from_env()

    assert loaded_paths == [".env.local"] * 3
    assert planner.model == ("process-planner" if process_override else "strong-planner")
    assert planner.stage_checker_model == "strong-stage-checker"
    assert planner.backend_profile == "openai-compatible"
    assert runtime.model == "rwkv-executor"
    assert os.environ["RWKV_LH_SELECTOR_MODEL"] == "rwkv-selector"
    assert policy.max_review_repairs == 2


def test_executor_model_can_be_bound_by_role_environment(monkeypatch) -> None:
    monkeypatch.setattr("rwkv_lh.runtime.settings.load_local_env", lambda: None)
    monkeypatch.setenv("RWKV_LH_EXECUTOR_BASE_URL", "http://executor.invalid/v1")
    monkeypatch.setenv("RWKV_LH_EXECUTOR_MODEL", "rwkv-next-executor")
    monkeypatch.setenv("RWKV_LH_EXECUTOR_MODEL_SHA256", "a" * 64)
    monkeypatch.delenv("RWKV_BASE_URL", raising=False)
    monkeypatch.delenv("RWKV_MODEL", raising=False)
    monkeypatch.delenv("RWKV_MODEL_SHA256", raising=False)

    settings = RuntimeSettings.from_env()

    assert settings.base_url == "http://executor.invalid/v1"
    assert settings.model == "rwkv-next-executor"
    assert settings.model_sha256 == "a" * 64


def test_auditor_model_inherits_deployment_only_and_remains_replaceable(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "rwkv_lh.runtime.settings.load_local_env", lambda *args, **kwargs: None
    )
    fallback = RuntimeSettings(
        base_url="http://executor.invalid/v1",
        api_key="executor-key",
        model="rwkv-13.3b-executor",
        model_sha256="a" * 64,
        state_profile_id="executor-task-state",
        state_profile_sha256="e" * 64,
        state_profile_delivery="process_attested",
    )
    monkeypatch.setenv("RWKV_LH_AUDITOR_BASE_URL", "http://auditor.invalid/v1")
    monkeypatch.setenv("RWKV_LH_AUDITOR_MODEL", "rwkv-7.2b-auditor")
    monkeypatch.setenv("RWKV_LH_AUDITOR_MODEL_SHA256", "b" * 64)

    settings = RuntimeSettings.for_role("auditor", fallback=fallback)

    assert settings.base_url == "http://auditor.invalid/v1"
    assert settings.model == "rwkv-7.2b-auditor"
    assert settings.model_sha256 == "b" * 64
    assert settings.max_model_len == fallback.max_model_len
    assert settings.state_profile_id == ""
    assert settings.state_profile_sha256 == ""
    assert settings.state_profile_delivery == "request"
    assert fallback.model == "rwkv-13.3b-executor"


def test_auditor_state_profile_requires_explicit_role_configuration(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "rwkv_lh.runtime.settings.load_local_env", lambda *args, **kwargs: None
    )
    fallback = RuntimeSettings(
        base_url="http://executor.invalid/v1",
        api_key="executor-key",
        model="rwkv-13.3b-executor",
        state_profile_id="executor-task-state",
        state_profile_sha256="e" * 64,
    )
    monkeypatch.setenv("RWKV_LH_AUDITOR_STATE_PROFILE_ID", "auditor-review-state")
    monkeypatch.setenv("RWKV_LH_AUDITOR_STATE_PROFILE_SHA256", "d" * 64)

    settings = RuntimeSettings.for_role("auditor", fallback=fallback)

    assert settings.state_profile_id == "auditor-review-state"
    assert settings.state_profile_sha256 == "d" * 64


def test_benchmark_goal_roles_use_distinct_clients_and_explicit_role_state(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        "rwkv_lh.runtime.settings.load_local_env", lambda *args, **kwargs: None
    )
    fallback = RuntimeSettings(
        base_url="http://executor.invalid/v1",
        api_key="executor-key",
        model="rwkv-13.3b-executor",
        model_sha256="a" * 64,
        state_profile_id="executor-args-v1",
        state_profile_sha256="e" * 64,
    )
    monkeypatch.setenv(
        "RWKV_LH_AUDITOR_STEP_BASE_URL",
        "http://auditor.invalid/v1",
    )
    monkeypatch.setenv("RWKV_LH_AUDITOR_STEP_MODEL", "rwkv-13.3b-auditor")
    monkeypatch.setenv(
        "RWKV_LH_AUDITOR_STEP_STATE_PROFILE_ID",
        "auditor-step-v1",
    )
    monkeypatch.setenv(
        "RWKV_LH_AUDITOR_STEP_STATE_PROFILE_SHA256",
        "d" * 64,
    )

    settings = _goal_role_settings(fallback)

    assert settings["executor_args"] is fallback
    assert settings["auditor_step"].base_url == "http://auditor.invalid/v1"
    assert settings["auditor_step"].state_profile_id == "auditor-step-v1"
    assert settings["finalizer_answer"].state_profile_id == ""
    assert settings["auditor_final"].state_profile_id == ""

    calls = []

    def fake_create_model_session(*args, **kwargs):
        assert not args
        calls.append(dict(kwargs))
        return SimpleNamespace(**kwargs)

    monkeypatch.setattr(
        "scripts.run_rwkv_e2e_benchmark.create_model_session",
        fake_create_model_session,
    )
    trace = []
    sessions = _build_stateful_goal_role_sessions(fallback, trace)

    assert tuple(sessions) == (
        "executor_args",
        "auditor_step",
        "finalizer_answer",
        "auditor_final",
    )
    assert len({id(item) for item in sessions.values()}) == 4
    assert len(calls) == 4
    assert all("client" not in call for call in calls)
    calls[1]["audit_hook"]({"type": "test_event"})
    assert trace == [{"type": "test_event", "model_role": "auditor_step"}]


def test_stateful_goal_cleanup_closes_each_distinct_role_client_once() -> None:
    class FakeClient:
        def __init__(self) -> None:
            self.close_calls = 0

        def close(self) -> None:
            self.close_calls += 1

    executor_client = FakeClient()
    auditor_client = FakeClient()
    sessions = {
        "executor_args": SimpleNamespace(client=executor_client),
        "auditor_step": SimpleNamespace(client=auditor_client),
        "finalizer_answer": SimpleNamespace(client=executor_client),
        "auditor_final": SimpleNamespace(client=auditor_client),
    }

    failures = _close_stateful_goal_role_sessions(sessions)

    assert failures == ()
    assert executor_client.close_calls == 1
    assert auditor_client.close_calls == 1


def test_stateful_goal_cleanup_does_not_mask_a_close_failure() -> None:
    class FailingClient:
        def close(self) -> None:
            raise RuntimeError("close failed")

    failures = _close_stateful_goal_role_sessions(
        {"executor_args": SimpleNamespace(client=FailingClient())}
    )

    assert failures == ("executor_args: RuntimeError: close failed",)


def test_role_environment_conflict_fails_closed(monkeypatch) -> None:
    monkeypatch.setattr("rwkv_lh.runtime.settings.load_local_env", lambda: None)
    monkeypatch.setenv("RWKV_LH_EXECUTOR_MODEL", "rwkv-g1j")
    monkeypatch.setenv("RWKV_MODEL", "rwkv-g1i")

    with pytest.raises(ValueError, match="RWKV_LH_EXECUTOR_MODEL.*RWKV_MODEL"):
        RuntimeSettings.from_env()


def test_executor_has_no_generation_specific_default(monkeypatch) -> None:
    monkeypatch.setattr("rwkv_lh.runtime.settings.load_local_env", lambda: None)
    for name in (
        "RWKV_LH_EXECUTOR_MODEL",
        "RWKV_MODEL",
    ):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ValueError, match="EXECUTOR_MODEL"):
        RuntimeSettings.from_env()


def test_selector_model_can_be_bound_by_role_environment(monkeypatch) -> None:
    values = {
        "BASE_URL": "http://selector.invalid",
        "MODEL": "rwkv-next-selector",
        "MODEL_SHA256": "1" * 64,
        "DECODER_ID": NATIVE_SELECTOR_DECODER_ID,
        "DECODER_SHA256": "2" * 64,
        "DECODER_PROTOCOL": NATIVE_SELECTOR_DECODER_PROTOCOL,
        "STATE_PROFILE_ID": "zero",
        "STATE_PROFILE_SHA256": "0" * 64,
        "STATE_PROFILE_MANIFEST_SHA256": "4" * 64,
        "INPUT_PROTOCOL": CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    }
    for suffix, value in values.items():
        monkeypatch.setenv(f"RWKV_LH_SELECTOR_{suffix}", value)
        monkeypatch.delenv(f"RWKV_SELECTOR_{suffix}", raising=False)

    settings = NativeNetworkSelectorSettings.from_env()

    assert settings is not None
    assert settings.model == "rwkv-next-selector"
    assert settings.state_profile_id == "zero"
    assert settings.decoder_id == NATIVE_SELECTOR_DECODER_ID


def test_selector_partial_identity_fails_closed(monkeypatch) -> None:
    for suffix in (
        "BASE_URL", "MODEL", "MODEL_SHA256", "DECODER_ID", "DECODER_SHA256",
        "DECODER_PROTOCOL", "STATE_PROFILE_ID", "STATE_PROFILE_SHA256",
        "STATE_PROFILE_MANIFEST_SHA256", "INPUT_PROTOCOL",
    ):
        monkeypatch.delenv(f"RWKV_LH_SELECTOR_{suffix}", raising=False)
        monkeypatch.delenv(f"RWKV_SELECTOR_{suffix}", raising=False)
    assert NativeNetworkSelectorSettings.from_env() is None
    # Identity without any DECODER_* value must raise, not silently disable.
    monkeypatch.setenv("RWKV_LH_SELECTOR_BASE_URL", "http://selector.invalid")
    monkeypatch.setenv("RWKV_LH_SELECTOR_MODEL", "rwkv-next-selector")
    with pytest.raises(ValueError, match="missing native Selector identity"):
        NativeNetworkSelectorSettings.from_env()


def test_planner_model_can_be_bound_by_role_environment(
    tmp_path,
    monkeypatch,
) -> None:
    env_path = tmp_path / ".env"
    monkeypatch.setenv("RWKV_LH_PLANNER_BASE_URL", "https://planner.invalid/v1")
    monkeypatch.setenv("RWKV_LH_PLANNER_API_KEY", "test-key")
    monkeypatch.setenv("RWKV_LH_PLANNER_MODEL", "replaceable-planner")
    for suffix in ("BASE_URL", "API_KEY", "MODEL"):
        monkeypatch.delenv(f"SUPERVISOR_{suffix}", raising=False)

    settings = SupervisorAPISettings.from_env(env_path)

    assert settings.base_url == "https://planner.invalid/v1"
    assert settings.api_key == "test-key"
    assert settings.model == "replaceable-planner"


def test_stack_defaults_to_external_without_a_generation_specific_service(
    monkeypatch,
) -> None:
    monkeypatch.setattr("rwkv_lh.runtime.stack.load_local_env", lambda: None)
    for name in (
        "RWKV_RUNTIME_MODE",
        "RWKV_REMOTE_SERVICE",
        "RWKV_LH_EXECUTOR_REMOTE_SERVICE",
        "RWKV_BASE_URL",
        "RWKV_LH_EXECUTOR_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)

    settings = RuntimeStackSettings.from_env()

    assert settings.mode == "external"
    assert settings.remote_service == ""
    assert "g1i" not in repr(settings).casefold()
