from __future__ import annotations

import pytest

from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.runtime.stack import RuntimeStackSettings
from rwkv_lh.supervisor_openai import SupervisorAPISettings


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
        "HEAD_SHA256": "2" * 64,
        "HEAD_HASH": "3" * 64,
        "FEATURE_PROTOCOL": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "STATE_PROFILE_ID": "zero",
        "STATE_PROFILE_SHA256": "0" * 64,
        "STATE_PROFILE_MANIFEST_SHA256": "4" * 64,
        "INPUT_PROTOCOL": (
            "rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v2"
        ),
    }
    for suffix, value in values.items():
        monkeypatch.setenv(f"RWKV_LH_SELECTOR_{suffix}", value)
        monkeypatch.delenv(f"RWKV_SELECTOR_{suffix}", raising=False)

    settings = NetworkExactToolSelectorSettings.from_env()

    assert settings is not None
    assert settings.model == "rwkv-next-selector"
    assert settings.state_profile_id == "zero"


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
