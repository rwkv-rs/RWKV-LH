from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from rwkv_lh.exact_tool_selector.head import NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL
from rwkv_lh.exact_tool_selector.input_protocol import (
    G1J_SELECTOR_INTENT_HEAD_ID,
    G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
    G1J_SELECTOR_RUNTIME_TRAJECTORY_MODE,
)
from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
)
from rwkv_lh.exact_tool_selector.network_service import (
    NetworkSelectorService,
    _extractor_state_profile_settings,
)


class _Response:
    status_code = 200
    text = ""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")


class _LocalSession:
    def __init__(self, service: NetworkSelectorService) -> None:
        self.service = service

    def post(self, _url: str, *, json: Mapping[str, Any], timeout):
        return _Response(self.service.select(json))


class _Extractor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object, bool, str]] = []

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state=None,
        continuation: bool = False,
        feature_protocol: str,
        export_state: bool = True,
    ):
        assert export_state is False
        self.calls.append((text, parent_state, continuation, feature_protocol))
        return [float(len(self.calls))] * 8, ["discarded"], 317, {
            "feature_protocol": feature_protocol,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
            "state_exported": False,
        }


class _Head:
    def __init__(self, settings: NetworkExactToolSelectorSettings) -> None:
        self.head_hash = settings.head_hash
        self.file_sha256 = settings.head_sha256
        self.feature_protocol = settings.feature_protocol
        self.temperature = 0.25
        self.artifact = SimpleNamespace(
            metadata={
                "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
                "compact_input_schema_version": settings.input_protocol,
                "model_weights_sha256": settings.model_sha256,
                "feature_protocol": settings.feature_protocol,
                "labels": list(NETWORK_EXACT_TOOL_LABELS),
                "runtime_trajectory_mode": G1J_SELECTOR_RUNTIME_TRAJECTORY_MODE,
            }
        )

    def raw_logits(self, _features):
        logits = [float(index) / 1000.0 for index in range(len(NETWORK_EXACT_TOOL_LABELS))]
        logits[NETWORK_EXACT_TOOL_LABELS.index("web_search")] = 5.0
        return tuple(logits)


def _settings(
    feature_protocol: str = "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
) -> NetworkExactToolSelectorSettings:
    return NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1j-2.9b-20260818-ctx16384",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        head_hash="c" * 64,
        feature_protocol=feature_protocol,
        state_profile_id="selector-intent-2p9-v2",
        state_profile_sha256="d" * 64,
        state_profile_manifest_sha256="e" * 64,
        input_protocol=G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
    )


def _input(objective: str) -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        current_subtask={
            "objective": objective,
            "phase": "observe",
            "read_roots": [],
            "write_roots": [],
            "success_evidence": ["one public source record"],
            "constraints": ["preserve source identity"],
        }
    )


def test_manifest_free_selector_accepts_only_exact_zero_state() -> None:
    assert _extractor_state_profile_settings(
        profile_manifest=None,
        profile_manifest_sha256="0" * 64,
        profile_id="zero",
        profile_sha256="0" * 64,
    ) == {
        "state_profile_manifest": None,
        "state_profile_manifest_sha256": "",
        "state_profile_id": "",
        "state_profile_sha256": "",
    }


@pytest.mark.parametrize(
    ("manifest_sha256", "profile_id", "profile_sha256"),
    (
        ("1" * 64, "zero", "0" * 64),
        ("0" * 64, "trained", "0" * 64),
        ("0" * 64, "zero", "1" * 64),
    ),
)
def test_manifest_free_selector_rejects_nonzero_identity(
    manifest_sha256: str,
    profile_id: str,
    profile_sha256: str,
) -> None:
    with pytest.raises(ValueError, match="exact zero-State identity"):
        _extractor_state_profile_settings(
            profile_manifest=None,
            profile_manifest_sha256=manifest_sha256,
            profile_id=profile_id,
            profile_sha256=profile_sha256,
        )


def test_service_runs_every_request_as_one_fresh_full_prompt() -> None:
    settings = _settings()
    extractor = _Extractor()
    service = NetworkSelectorService(settings, extractor, _Head(settings))
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    first, first_checkpoint = client.select(
        _input("Search the public web for the project."),
        run_id="RUN-SERVICE",
        trace_id="TRACE-1",
    )
    second, second_checkpoint = client.select(
        _input("Search the public web for the package."),
        run_id="RUN-SERVICE",
        trace_id="TRACE-2",
    )

    assert first.selected_operation == second.selected_operation == "web_search"
    assert len(extractor.calls) == 2
    assert all(call[0].startswith("SelectorIntentMenuV2: ") for call in extractor.calls)
    assert all("\nSelectorIntentRoleV2: " in call[0] for call in extractor.calls)
    assert all("\nSelectorIntentPromptV2: " in call[0] for call in extractor.calls)
    assert all(call[1] is None and call[2] is False for call in extractor.calls)
    assert first.input_token_count == second.input_token_count == 317
    assert first_checkpoint.parent_checkpoint_id is None
    assert second_checkpoint.parent_checkpoint_id is None
    assert first_checkpoint.native_state_ref is None
    assert second_checkpoint.native_state_ref is None


def test_service_repeated_request_does_not_reuse_dynamic_state() -> None:
    settings = _settings()
    extractor = _Extractor()
    service = NetworkSelectorService(settings, extractor, _Head(settings))
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))
    selector_input = _input("Search the public web for the project.")

    first, _ = client.select(
        selector_input,
        run_id="RUN-SERVICE",
        trace_id="TRACE-SAME",
    )
    replay, _ = client.select(
        selector_input,
        run_id="RUN-SERVICE",
        trace_id="TRACE-SAME",
    )

    assert first.selection_id == replay.selection_id
    assert len(extractor.calls) == 2
    assert all(call[1] is None and call[2] is False for call in extractor.calls)


def test_service_rejects_head_without_fresh_trajectory_identity() -> None:
    settings = _settings()
    head = _Head(settings)
    del head.artifact.metadata["runtime_trajectory_mode"]
    with pytest.raises(ValueError, match="identity mismatch"):
        NetworkSelectorService(settings, _Extractor(), head)


def test_service_fuses_mean_then_last_from_one_fresh_forward() -> None:
    torch = pytest.importorskip("torch")
    settings = _settings(NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL)

    class FusionExtractor:
        def __init__(self) -> None:
            self.calls: list[tuple[str, object, bool]] = []

        def advance_hidden_views(
            self,
            text,
            *,
            parent_state=None,
            continuation=False,
            export_state=True,
        ):
            assert export_state is False
            self.calls.append((text, parent_state, continuation))
            return (
                {
                    "mean": torch.full((4,), 1.0),
                    "last": torch.full((4,), 2.0),
                },
                ["discarded"],
                401,
                {
                    "feature_protocols": {
                        "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                        "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                    },
                    "model_weights_sha256": settings.model_sha256,
                    "engine_revision": "1" * 40,
                    "wkv_mode": "fp16",
                    "generated_rwkv_text": False,
                    "sampling_invoked": False,
                    "state_exported": False,
                },
            )

    head = _Head(settings)
    head.artifact.feature_dim = 8
    head.artifact.metadata["portable_feature_identity"] = {
        "batch_size": 1,
        "compact_input_schema_version": settings.input_protocol,
        "engine_revision": "1" * 40,
        "feature_dim": 8,
        "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
        "model_weights_sha256": settings.model_sha256,
        "fresh_initial_state_each_evaluation": True,
        "state_profile": {
            "id": settings.state_profile_id,
            "sha256": settings.state_profile_sha256,
        },
        "runtime_trajectory_mode": G1J_SELECTOR_RUNTIME_TRAJECTORY_MODE,
        "wkv_mode": "fp16",
    }
    extractor = FusionExtractor()
    service = NetworkSelectorService(settings, extractor, head)
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    selection, _ = client.select(
        _input("Search the public web."),
        run_id="RUN-FUSION",
        trace_id="TRACE-1",
    )

    assert selection.input_token_count == 401
    assert len(extractor.calls) == 1
    assert extractor.calls[0][1] is None
    assert extractor.calls[0][2] is False
