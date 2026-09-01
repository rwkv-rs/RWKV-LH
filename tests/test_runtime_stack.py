from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from rwkv_lh.runtime.stack import RuntimeStackManager, RuntimeStackSettings
from rwkv_lh.runtime.settings import PROJECT_ROOT


class _HealthResponse:
    def __init__(self, value: dict[str, Any]) -> None:
        self.value = value

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.value).encode("utf-8")


def settings(tmp_path: Path) -> RuntimeStackSettings:
    return RuntimeStackSettings(
        mode="external",
        state_dir=tmp_path / "runtime",
        remote_ssh_alias="rwkv-8222",
        remote_service="rwkv.service",
        remote_port=18070,
        main_base_url="http://127.0.0.1:29610/v1",
    )


def test_stack_stops_only_exact_owned_process(tmp_path: Path) -> None:
    manager = RuntimeStackManager(settings(tmp_path))
    record = manager._spawn(
        "test",
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        environment=os.environ.copy(),
    )
    try:
        assert manager._record_alive(record)
        assert manager._stop_owned("test") is True
        assert not manager._record_alive(record)
    finally:
        if manager._record_alive(record):
            os.kill(int(record["pid"]), 9)


def test_stack_never_kills_process_when_record_identity_is_tampered(
    tmp_path: Path,
) -> None:
    manager = RuntimeStackManager(settings(tmp_path))
    record = manager._spawn(
        "test",
        [sys.executable, "-c", "import time; time.sleep(60)"],
        cwd=tmp_path,
        environment=os.environ.copy(),
    )
    path = manager._record_path("test")
    tampered = dict(record)
    tampered["command_digest"] = "0" * 64
    path.write_text(json.dumps(tampered), encoding="utf-8")
    try:
        assert manager._stop_owned("test") is False
        assert manager._record_alive(record)
    finally:
        os.killpg(int(record["pid"]), 15)


def test_stack_refreshes_only_same_owned_process_after_launcher_exec(
    tmp_path: Path,
) -> None:
    manager = RuntimeStackManager(settings(tmp_path))
    record = manager._spawn(
        "test",
        [
            sys.executable,
            "-c",
            (
                "import os,time; time.sleep(0.2); "
                "os.execv('/bin/sleep', ['sleep', '60'])"
            ),
        ],
        cwd=tmp_path,
        environment=os.environ.copy(),
    )
    try:
        deadline = time.monotonic() + 3
        while manager._record_alive(record) and time.monotonic() < deadline:
            time.sleep(0.05)
        assert not manager._record_alive(record)
        refreshed = manager._refresh_reexecuted_record("test", record)
        assert refreshed is not None
        assert refreshed["pid"] == record["pid"]
        assert refreshed["start_ticks"] == record["start_ticks"]
        assert refreshed["command_digest"] != record["command_digest"]
        assert manager._record_alive(refreshed)
        assert manager._stop_owned("test") is True
    finally:
        if (refreshed := manager._owned_record("test")) is not None:
            if manager._record_alive(refreshed):
                os.killpg(int(refreshed["pid"]), 15)


def test_runtime_stack_settings_reject_invalid_main_url(tmp_path: Path) -> None:
    value = settings(tmp_path)
    changed = RuntimeStackSettings(**{**value.__dict__, "main_base_url": "not-a-url"})
    try:
        changed.validate()
    except ValueError as exc:
        assert "absolute HTTP" in str(exc)
    else:
        raise AssertionError("invalid main RWKV URL was accepted")


def test_stack_prepare_and_goal_studio_web_binding(
    tmp_path: Path,
    monkeypatch,
) -> None:
    manager = RuntimeStackManager(settings(tmp_path))
    assert manager.prepare() == {
        "schema_version": "rwkv-lh.runtime-stack.v1",
        "component": "product runtime stack",
        "status": "no_prepare_required",
        "reused": True,
    }
    captured = {}

    def capture(name, command, *, cwd, environment):
        captured.update(
            name=name,
            command=command,
            cwd=cwd,
            environment=environment,
        )
        return {"pid": 1}

    monkeypatch.setattr(manager, "_spawn", capture)
    manager._ensure_product_process("web", "scripts.run_web_ui")

    assert captured["command"][-6:] == [
        "--host",
        "127.0.0.1",
        "--port",
        "8766",
        "--data-root",
        str(PROJECT_ROOT / "data/goal_ui_preview"),
    ]
    assert captured["environment"]["RWKV_LH_WEB_ASSET_ROOT"].endswith(
        "/rwkv_lh/goal_web_assets"
    )


def test_stack_attests_configured_independent_selector_health(
    tmp_path: Path,
    monkeypatch,
) -> None:
    selector_env = {
        "RWKV_SELECTOR_BASE_URL": "http://127.0.0.1:29621",
        "RWKV_SELECTOR_MODEL": "rwkv7-g1i-2.9b-test",
        "RWKV_SELECTOR_MODEL_SHA256": "1" * 64,
        "RWKV_SELECTOR_HEAD_SHA256": "2" * 64,
        "RWKV_SELECTOR_HEAD_HASH": "3" * 64,
        "RWKV_SELECTOR_FEATURE_PROTOCOL": (
            "rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1"
        ),
        "RWKV_SELECTOR_INPUT_PROTOCOL": (
            "rwkv-lh.exact-tool-selector-input.v6-current-question-last"
        ),
        "RWKV_SELECTOR_STATE_PROFILE_ID": "zero",
        "RWKV_SELECTOR_STATE_PROFILE_SHA256": "0" * 64,
        "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256": "4" * 64,
    }
    for name, value in selector_env.items():
        monkeypatch.setenv(name, value)
    expected = {
        "input_protocol": selector_env["RWKV_SELECTOR_INPUT_PROTOCOL"],
        "model": selector_env["RWKV_SELECTOR_MODEL"],
        "model_sha256": selector_env["RWKV_SELECTOR_MODEL_SHA256"],
        "head_sha256": selector_env["RWKV_SELECTOR_HEAD_SHA256"],
        "head_hash": selector_env["RWKV_SELECTOR_HEAD_HASH"],
        "feature_protocol": selector_env["RWKV_SELECTOR_FEATURE_PROTOCOL"],
        "profile_id": selector_env["RWKV_SELECTOR_STATE_PROFILE_ID"],
        "profile_sha256": selector_env["RWKV_SELECTOR_STATE_PROFILE_SHA256"],
        "profile_manifest_sha256": selector_env[
            "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256"
        ],
    }
    monkeypatch.setattr(
        "rwkv_lh.runtime.stack.urllib.request.urlopen",
        lambda *_args, **_kwargs: _HealthResponse(
            {"status": "ok", "runtime_identity": expected}
        ),
    )

    health = RuntimeStackManager(settings(tmp_path))._selector_health()

    assert health == {
        "available": True,
        "enabled": True,
        "runtime_identity": expected,
    }


def test_main_health_fails_closed_when_native_state_protocol_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _Client:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(state_transport="native_required")
            self.closed = False

        def health(self):
            return SimpleNamespace(to_dict=lambda: {"available": True})

        def capabilities(self):
            return SimpleNamespace(
                durable_recurrent_state=False,
                recurrent_state_protocol="",
                to_dict=lambda: {
                    "durable_recurrent_state": False,
                    "recurrent_state_protocol": "",
                },
            )

        def close(self) -> None:
            self.closed = True

    client = _Client()
    monkeypatch.setattr(
        "rwkv_lh.runtime.stack.OpenAICompatibleRWKVClient",
        lambda: client,
    )

    health = RuntimeStackManager(settings(tmp_path))._main_health()

    assert health["available"] is False
    assert "native state+delta" in health["error"]
    assert health["capabilities"]["recurrent_state_protocol"] == ""
    assert client.closed is True


def test_main_health_accepts_exact_native_state_protocol(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class _Client:
        def __init__(self) -> None:
            self.settings = SimpleNamespace(state_transport="native_required")

        def health(self):
            return SimpleNamespace(to_dict=lambda: {"available": True})

        def capabilities(self):
            return SimpleNamespace(
                durable_recurrent_state=True,
                recurrent_state_protocol="rwkv-lh.native-state.v1",
                to_dict=lambda: {
                    "durable_recurrent_state": True,
                    "recurrent_state_protocol": "rwkv-lh.native-state.v1",
                },
            )

        def close(self) -> None:
            return None

    monkeypatch.setattr(
        "rwkv_lh.runtime.stack.OpenAICompatibleRWKVClient",
        _Client,
    )

    health = RuntimeStackManager(settings(tmp_path))._main_health()

    assert health["available"] is True
    assert "error" not in health
