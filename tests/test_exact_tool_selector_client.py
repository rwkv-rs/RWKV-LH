from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any

import pytest

from rwkv_lh.exact_tool_selector.client import (
    SELECTOR_SERVICE_RESPONSE_SCHEMA,
    ExactToolSelectorClient,
    ExactToolSelectorError,
    ExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.protocol import (
    EXACT_TOOL_LABELS,
    ExactToolSelection,
    SelectorInput,
    SelectorProgress,
)
from rwkv_lh.schema import ModelLaneKind


class _Response:
    status_code = 200
    text = ""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")


class _SelectorSession:
    def __init__(
        self,
        settings: ExactToolSelectorSettings,
        *,
        wrong_model_sha: bool = False,
    ) -> None:
        self.settings = settings
        self.wrong_model_sha = wrong_model_sha
        self.payloads: list[dict[str, Any]] = []

    def post(
        self,
        _url: str,
        *,
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> _Response:
        assert timeout == (10.0, 120.0)
        payload = dict(json)
        self.payloads.append(payload)
        parent = payload.get("parent")
        parent_value = dict(parent) if isinstance(parent, Mapping) else {}
        token_position = int(parent_value.get("token_position") or 100) + 7
        index = len(self.payloads)
        logits = [float(item) / 100.0 for item in range(len(EXACT_TOOL_LABELS))]
        logits[EXACT_TOOL_LABELS.index("read_file")] = 3.0
        selection = ExactToolSelection(
            selection_id=f"SEL-{index:04d}",
            trace_id=str(payload["trace_id"]),
            selected_operation="read_file",
            logits=tuple(logits),
            temperature=0.8,
            input_digest=str(payload["input_digest"]),
            menu_digest=str(payload["menu_digest"]),
            selector_checkpoint_id=f"SCP-{index:04d}",
            selector_state_ref=f"STATE-{index:04d}",
            selector_state_digest=hashlib.sha256(f"state-{index}".encode()).hexdigest(),
            selector_parent_state_digest=str(parent_value.get("state_digest") or ""),
            token_position=token_position,
            model=self.settings.model,
            model_sha256=(
                "f" * 64 if self.wrong_model_sha else self.settings.model_sha256
            ),
            head_sha256=self.settings.head_sha256,
            profile_id=self.settings.state_profile_id,
            profile_sha256=self.settings.state_profile_sha256,
        )
        return _Response(
            {
                "schema_version": SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "selection": selection.raw_record(),
            }
        )


def _settings() -> ExactToolSelectorSettings:
    return ExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        state_profile_id="selector-base-v1",
        state_profile_sha256="c" * 64,
    )


def _input(action_index: int) -> SelectorInput:
    return SelectorInput.create(
        task_request="Read note.txt and report its exact contents.",
        stage_objective="Observe note.txt before finishing.",
        stage_role="work",
        progress=SelectorProgress(
            action_index=action_index,
            succeeded_operations=("read_file",) if action_index else (),
        ),
    )


def test_selector_client_uses_separate_persistent_state_without_executor_schema() -> (
    None
):
    settings = _settings()
    session = _SelectorSession(settings)
    client = ExactToolSelectorClient(settings, session=session)

    first, first_checkpoint = client.select(
        _input(0),
        run_id="RUN-1",
        trace_id="TRACE-1",
    )
    second, second_checkpoint = client.select(
        _input(1),
        run_id="RUN-1",
        trace_id="TRACE-2",
        parent=first_checkpoint,
    )

    assert first.selected_operation == second.selected_operation == "read_file"
    assert first_checkpoint.lane_kind is ModelLaneKind.SELECTOR
    assert first_checkpoint.model == settings.model
    assert first_checkpoint.parent_checkpoint_id is None
    assert second_checkpoint.parent_checkpoint_id == first_checkpoint.checkpoint_id
    assert second_checkpoint.native_state_ref != first_checkpoint.native_state_ref
    assert second.selector_parent_state_digest == first.selector_state_digest
    assert session.payloads[0]["bootstrap"].startswith("SelectorBootstrap: ")
    assert session.payloads[0]["parent"] is None
    assert session.payloads[1]["bootstrap"] == ""
    assert session.payloads[1]["parent"]["state_ref"] == first.selector_state_ref
    wire = json.dumps(session.payloads, ensure_ascii=False)
    assert '"parameters"' not in wire
    assert '"arguments"' not in wire
    assert '"result"' not in wire


def test_selector_client_rejects_service_artifact_identity_mismatch() -> None:
    settings = _settings()
    client = ExactToolSelectorClient(
        settings,
        session=_SelectorSession(settings, wrong_model_sha=True),
    )

    with pytest.raises(ExactToolSelectorError, match="identity mismatch"):
        client.select(_input(0), run_id="RUN-1", trace_id="TRACE-1")


def test_selector_settings_partial_environment_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    names = (
        "RWKV_SELECTOR_BASE_URL",
        "RWKV_SELECTOR_MODEL",
        "RWKV_SELECTOR_MODEL_SHA256",
        "RWKV_SELECTOR_HEAD_SHA256",
        "RWKV_SELECTOR_STATE_PROFILE_ID",
        "RWKV_SELECTOR_STATE_PROFILE_SHA256",
    )
    for name in names:
        monkeypatch.delenv(name, raising=False)
    assert ExactToolSelectorSettings.from_env() is None
    monkeypatch.setenv("RWKV_SELECTOR_BASE_URL", "http://127.0.0.1:29621")

    with pytest.raises(ValueError, match="all RWKV_SELECTOR"):
        ExactToolSelectorSettings.from_env()
