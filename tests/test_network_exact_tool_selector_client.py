from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

import pytest

from rwkv_lh.exact_tool_selector.input_protocol import network_selector_input_protocol
from rwkv_lh.exact_tool_selector.network_client import (
    NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL,
    NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorError,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkExactToolSelection,
    NetworkSelectorInput,
)
from rwkv_lh.schema import ModelLaneKind


class _Response:
    status_code = 200
    text = ""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")


class _Session:
    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        *,
        wrong_runtime_identity: bool = False,
    ) -> None:
        self.settings = settings
        self.wrong_runtime_identity = wrong_runtime_identity
        self.payloads: list[dict[str, Any]] = []

    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> _Response:
        assert url.endswith(
            network_selector_input_protocol(self.settings.input_protocol).endpoint
        )
        assert timeout == (10.0, 120.0)
        payload = dict(json)
        self.payloads.append(payload)
        logits = [float(index) / 100.0 for index in range(len(NETWORK_EXACT_TOOL_LABELS))]
        logits[NETWORK_EXACT_TOOL_LABELS.index("connector_lookup")] = 5.0
        index = len(self.payloads)
        selection = NetworkExactToolSelection(
            selection_id=f"NSEL-{index}",
            trace_id=str(payload["trace_id"]),
            selected_operation="connector_lookup",
            logits=tuple(logits),
            temperature=0.25,
            input_digest=str(payload["input_digest"]),
            menu_digest=str(payload["menu_digest"]),
            selector_checkpoint_id=f"NSCP-{index}",
            input_token_count=920,
            model=self.settings.model,
            model_sha256=self.settings.model_sha256,
            head_sha256=self.settings.head_sha256,
            profile_id=self.settings.state_profile_id,
            profile_sha256=self.settings.state_profile_sha256,
        )
        identity = self.settings.runtime_identity()
        if self.wrong_runtime_identity:
            identity = {**identity, "profile_manifest_sha256": "f" * 64}
        return _Response(
            {
                "schema_version": NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": identity,
                "selection": selection.raw_record(),
            }
        )


def _settings() -> NetworkExactToolSelectorSettings:
    return NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1j-2.9b-20260818-ctx16384",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        head_hash="c" * 64,
        feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        state_profile_id="selector-intent-2p9-v2",
        state_profile_sha256="d" * 64,
        state_profile_manifest_sha256="e" * 64,
    )


def _input(objective: str) -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        current_subtask={
            "objective": objective,
            "phase": "observe",
            "read_roots": [],
            "write_roots": [],
            "success_evidence": ["one structured public record"],
            "constraints": ["preserve source identity"],
        }
    )


def test_network_selector_client_sends_every_evaluation_fresh() -> None:
    settings = _settings()
    session = _Session(settings)
    client = NetworkExactToolSelectorClient(settings, session=session)
    first, first_checkpoint = client.select(
        _input("Query the exact repository release record."),
        run_id="RUN-1",
        trace_id="TRACE-1",
    )
    second, second_checkpoint = client.select(
        _input("Query the exact package release record."),
        run_id="RUN-1",
        trace_id="TRACE-2",
    )

    assert first.selected_operation == second.selected_operation == "connector_lookup"
    assert first_checkpoint.lane_kind is ModelLaneKind.SELECTOR
    assert second_checkpoint.parent_checkpoint_id is None
    assert first_checkpoint.native_state_ref is None
    assert second_checkpoint.native_state_ref is None
    assert all("parent" not in payload for payload in session.payloads)
    assert all(payload["bootstrap"].startswith("SelectorIntentMenuV2: ") for payload in session.payloads)
    assert all("\nSelectorIntentRoleV2: " in payload["bootstrap"] for payload in session.payloads)
    assert all(payload["step"].startswith("SelectorIntentPromptV2: ") for payload in session.payloads)
    assert first_checkpoint.native_state_metadata["state_policy"] == (
        "fresh_initial_state_per_evaluation"
    )
    assert first_checkpoint.native_state_metadata["generated_rwkv_text"] is False
    assert first_checkpoint.native_state_metadata["input_protocol"] == (
        NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL
    )
    assert first_checkpoint.transport == (
        "native_rwkv_hidden_mlp_selector_g1j_selector_intent_v2"
    )
    assert first_checkpoint.token_count == second_checkpoint.token_count == 920
    wire = json.dumps(session.payloads, ensure_ascii=False)
    assert '"arguments"' not in wire
    assert '"result"' not in wire
    assert '"progress"' not in wire
    assert '"latest_action"' not in wire


def test_network_selector_client_rejects_manifest_identity_mismatch() -> None:
    settings = _settings()
    client = NetworkExactToolSelectorClient(
        settings,
        session=_Session(settings, wrong_runtime_identity=True),
    )
    with pytest.raises(NetworkExactToolSelectorError, match="runtime identity"):
        client.select(_input("Read one record."), run_id="RUN-1", trace_id="TRACE-1")


def test_network_selector_settings_partial_environment_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = (
        "RWKV_SELECTOR_BASE_URL",
        "RWKV_SELECTOR_MODEL",
        "RWKV_SELECTOR_MODEL_SHA256",
        "RWKV_SELECTOR_HEAD_SHA256",
        "RWKV_SELECTOR_HEAD_HASH",
        "RWKV_SELECTOR_FEATURE_PROTOCOL",
        "RWKV_SELECTOR_STATE_PROFILE_ID",
        "RWKV_SELECTOR_STATE_PROFILE_SHA256",
        "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)
        monkeypatch.delenv(
            name.replace("RWKV_SELECTOR_", "RWKV_LH_SELECTOR_"),
            raising=False,
        )
    assert NetworkExactToolSelectorSettings.from_env() is None
    monkeypatch.setenv("RWKV_SELECTOR_BASE_URL", "http://127.0.0.1:29621")
    with pytest.raises(ValueError, match="missing Selector") as exc_info:
        NetworkExactToolSelectorSettings.from_env()
    assert "RWKV_LH_SELECTOR_HEAD_SHA256" in str(exc_info.value)
    assert "RWKV_LH_SELECTOR_STATE_PROFILE_MANIFEST_SHA256" in str(exc_info.value)
