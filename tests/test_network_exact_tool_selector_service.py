from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
import torch

from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.input_protocol import (
    G1J_SELECTOR_INTENT_HEAD_ID,
    G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
    G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.head import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.network_service import (
    NetworkSelectorService,
    NetworkSelectorStateStore,
    _extractor_state_profile_settings,
)


class _Extractor:
    def __init__(self) -> None:
        self.calls = 0

    def advance_hidden_last(
        self,
        text: str,
        *,
        parent_state=None,
        continuation: bool = False,
    ):
        self.calls += 1
        assert continuation == (parent_state is not None)
        assert text.startswith("\nSelectorIntentPromptV1: ") if continuation else text.startswith(
            "SelectorIntentMenuV1: "
        )
        if not continuation:
            assert "\nSelectorIntentRoleV1: " in text
            assert "\nSelectorIntentPromptV1: " in text
        if parent_state is None:
            state = [
                torch.zeros((2, 2, 1, 8), dtype=torch.float16),
                torch.zeros((2, 1, 3, 2, 2), dtype=torch.float16),
                torch.zeros((1,), dtype=torch.int32),
            ]
        else:
            state = [value.clone() for value in parent_state]
        state[0].add_(1)
        state[1].add_(1)
        state[2].add_(10)
        feature = torch.full((2560,), float(self.calls), dtype=torch.float32)
        return feature, state, 17, {
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        }


class _Response:
    status_code = 200
    text = ""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")


class _MeanExtractor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool, str]] = []

    def advance_hidden_feature(
        self,
        text: str,
        *,
        parent_state=None,
        continuation: bool = False,
        feature_protocol: str,
    ):
        self.calls.append((text, continuation, feature_protocol))
        if parent_state is None:
            state = [
                torch.zeros((2, 2, 1, 8), dtype=torch.float16),
                torch.zeros((2, 1, 3, 2, 2), dtype=torch.float16),
                torch.zeros((1,), dtype=torch.int32),
            ]
        else:
            state = [value.clone() for value in parent_state]
        state[0].add_(1)
        state[1].add_(1)
        state[2].add_(10)
        feature = torch.full((2560,), float(len(self.calls)), dtype=torch.float32)
        return feature, state, 11, {
            "feature_protocol": feature_protocol,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        }


class _MeanHead:
    def __init__(self, settings: NetworkExactToolSelectorSettings) -> None:
        self.head_hash = settings.head_hash
        self.file_sha256 = settings.head_sha256
        self.feature_protocol = settings.feature_protocol
        self.temperature = 0.25

    def raw_logits(self, _features):
        logits = [float(index) / 1000.0 for index in range(25)]
        logits[18] = 5.0
        return tuple(logits)


class _G1JHead(_MeanHead):
    def __init__(self, settings: NetworkExactToolSelectorSettings) -> None:
        super().__init__(settings)
        self.artifact = SimpleNamespace(
            metadata={
                "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
                "compact_input_schema_version": settings.input_protocol,
                "model_weights_sha256": settings.model_sha256,
                "feature_protocol": settings.feature_protocol,
                "labels": list(NETWORK_EXACT_TOOL_LABELS),
                "training_trajectory_mode": (
                    G1J_SELECTOR_TRAINING_TRAJECTORY_MODE
                ),
            }
        )


class _FusionExtractor(_MeanExtractor):
    def __init__(self) -> None:
        super().__init__()
        self.view_calls: list[tuple[str, bool]] = []

    def advance_hidden_views(
        self,
        text: str,
        *,
        parent_state=None,
        continuation: bool = False,
    ):
        self.view_calls.append((text, continuation))
        assert text.startswith("\nSelectorIntentPromptV1: ")
        assert continuation is True
        assert parent_state is not None
        state = [value.clone() for value in parent_state]
        state[0].add_(1)
        state[1].add_(1)
        state[2].add_(10)
        value = float(len(self.view_calls))
        return (
            {
                "mean": torch.full((2560,), value, dtype=torch.float32),
                "last": torch.full((2560,), value + 10.0, dtype=torch.float32),
            },
            state,
            13,
            {
                "feature_protocols": {
                    "mean": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
                    "last": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
                },
                "model_weights_sha256": "a" * 64,
                "engine_revision": "1" * 40,
                "wkv_mode": "fp16",
                "generated_rwkv_text": False,
                "sampling_invoked": False,
            },
        )


class _FusionHead(_MeanHead):
    def __init__(self, settings: NetworkExactToolSelectorSettings) -> None:
        super().__init__(settings)
        metadata = {
            "portable_feature_identity": {
                "batch_size": 1,
                "compact_input_schema_version": settings.input_protocol,
                "engine_revision": "1" * 40,
                "feature_dim": 5120,
                "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
                "model_weights_sha256": settings.model_sha256,
                "persistent_history_replayed": True,
                "state_profile": {
                    "id": settings.state_profile_id,
                    "sha256": settings.state_profile_sha256,
                },
                "wkv_mode": "fp16",
            }
        }
        metadata.update({
            "head_id": G1J_SELECTOR_INTENT_HEAD_ID,
            "compact_input_schema_version": settings.input_protocol,
            "model_weights_sha256": settings.model_sha256,
            "feature_protocol": settings.feature_protocol,
            "labels": list(NETWORK_EXACT_TOOL_LABELS),
            "training_trajectory_mode": G1J_SELECTOR_TRAINING_TRAJECTORY_MODE,
        })
        metadata["portable_feature_identity"][
            "training_trajectory_mode"
        ] = G1J_SELECTOR_TRAINING_TRAJECTORY_MODE
        self.artifact = SimpleNamespace(
            feature_dim=5120,
            metadata=metadata,
        )
        self.seen: list[torch.Tensor] = []

    def raw_logits(self, features):
        values = torch.as_tensor(features, dtype=torch.float32)
        call = len(self.seen) + 1
        assert tuple(values.shape) == (5120,)
        assert torch.equal(values[:2560], torch.full((2560,), float(call)))
        assert torch.equal(
            values[2560:], torch.full((2560,), float(call) + 10.0)
        )
        self.seen.append(values.clone())
        return super().raw_logits(values)


class _LocalSession:
    def __init__(self, service: NetworkSelectorService) -> None:
        self.service = service

    def post(self, _url: str, *, json: Mapping[str, Any], timeout):
        return _Response(self.service.select(json))


def _settings() -> NetworkExactToolSelectorSettings:
    return NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1i-2.9b-20260805-ctx16384",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        head_hash="c" * 64,
        feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        state_profile_id="selector-zero-s0",
        state_profile_sha256="b" * 64,
        state_profile_manifest_sha256="c" * 64,
        input_protocol=G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
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


def _input(index: int) -> NetworkSelectorInput:
    return NetworkSelectorInput.create(
        task_request="Find current public information for the requested project.",
        stage_objective="Search the public web and preserve source evidence.",
        stage_role="work",
        progress=NetworkSelectorProgress(action_index=index),
    )


def test_service_persists_dynamic_selector_state_and_replays_idempotently(
    tmp_path: Path,
) -> None:
    settings = _settings()
    extractor = _Extractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _G1JHead(settings),
        NetworkSelectorStateStore(tmp_path / "dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(
        settings, session=_LocalSession(service)
    )
    first, first_checkpoint = client.select(
        _input(0), run_id="RUN-SERVICE", trace_id="TRACE-1"
    )
    replay, replay_checkpoint = client.select(
        _input(0), run_id="RUN-SERVICE", trace_id="TRACE-1"
    )
    second, second_checkpoint = client.select(
        _input(1),
        run_id="RUN-SERVICE",
        trace_id="TRACE-2",
        parent=first_checkpoint,
    )

    assert extractor.calls == 2
    assert replay == first
    assert replay_checkpoint.checkpoint_id == first_checkpoint.checkpoint_id
    assert replay_checkpoint.native_state_digest == first_checkpoint.native_state_digest
    assert replay_checkpoint.transcript_digest == first_checkpoint.transcript_digest
    assert second.selector_parent_state_digest == first.selector_state_digest
    assert second.token_position == first.token_position + 17
    assert second_checkpoint.parent_checkpoint_id == first_checkpoint.checkpoint_id
    assert len(list((tmp_path / "dynamic-selector-state").glob("NST-*.pth"))) == 2
    assert first.raw_record()["generated_text"] is False
    assert first.raw_record()["postprocessed"] is False


def test_service_mean_feature_uses_step_segment_and_one_persistent_state(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        }
    )
    extractor = _MeanExtractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _G1JHead(settings),
        NetworkSelectorStateStore(tmp_path / "mean-dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(
        settings, session=_LocalSession(service)
    )

    first, first_checkpoint = client.select(
        _input(0), run_id="RUN-MEAN", trace_id="TRACE-1"
    )
    second, _ = client.select(
        _input(1),
        run_id="RUN-MEAN",
        trace_id="TRACE-2",
        parent=first_checkpoint,
    )

    assert first.selected_operation == second.selected_operation == "web_search"
    assert len(extractor.calls) == 3
    assert extractor.calls[0][0].startswith("SelectorIntentMenuV1: ")
    assert "\nSelectorIntentRoleV1: " in extractor.calls[0][0]
    assert extractor.calls[0][1:] == (
        False,
        "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
    )
    assert extractor.calls[1][0].startswith("\nSelectorIntentPromptV1: ")
    assert extractor.calls[1][1:] == (
        True,
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
    )
    assert extractor.calls[2][0].startswith("\nSelectorIntentPromptV1: ")
    assert extractor.calls[2][1:] == (
        True,
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
    )
    assert first.token_position == 22
    assert second.token_position == 33


def test_g1j_service_continues_selector_state_after_initial_bootstrap(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "input_protocol": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        }
    )
    extractor = _MeanExtractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _G1JHead(settings),
        NetworkSelectorStateStore(tmp_path / "g1j-persistent-selector-state"),
    )
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    first, checkpoint = client.select(
        _input(0), run_id="RUN-G1J", trace_id="TRACE-G1J-1"
    )
    second, continued = client.select(
        _input(1),
        run_id="RUN-G1J",
        trace_id="TRACE-G1J-2",
        parent=checkpoint,
    )

    assert len(extractor.calls) == 3
    assert extractor.calls[0][0].startswith("SelectorIntentMenuV1: ")
    assert extractor.calls[1][0].startswith("\nSelectorIntentPromptV1: ")
    assert extractor.calls[2][0].startswith("\nSelectorIntentPromptV1: ")
    assert extractor.calls[2][1] is True
    assert second.selector_parent_state_digest == first.selector_state_digest
    assert continued.parent_checkpoint_id == checkpoint.checkpoint_id
    assert continued.token_count > checkpoint.token_count


def test_g1j_service_rejects_head_without_persistent_trajectory_training(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "input_protocol": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        }
    )
    head = _G1JHead(settings)
    del head.artifact.metadata["training_trajectory_mode"]

    with pytest.raises(ValueError, match="identity mismatch"):
        NetworkSelectorService(
            settings,
            _MeanExtractor(),
            head,
            NetworkSelectorStateStore(tmp_path / "invalid-g1j-head"),
        )


def test_g1j_fusion_service_rejects_portable_identity_without_trajectory_mode(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "input_protocol": G1J_SELECTOR_INTENT_INPUT_PROTOCOL,
            "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
        }
    )
    head = _FusionHead(settings)
    del head.artifact.metadata["portable_feature_identity"][
        "training_trajectory_mode"
    ]

    with pytest.raises(ValueError, match="portable identity mismatch"):
        NetworkSelectorService(
            settings,
            _FusionExtractor(),
            head,
            NetworkSelectorStateStore(tmp_path / "invalid-g1j-fusion-head"),
        )


def test_service_fuses_mean_then_last_from_one_current_forward(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "feature_protocol": NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
        }
    )
    extractor = _FusionExtractor()
    head = _FusionHead(settings)
    service = NetworkSelectorService(
        settings,
        extractor,
        head,
        NetworkSelectorStateStore(tmp_path / "fusion-dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(
        settings, session=_LocalSession(service)
    )

    first, first_checkpoint = client.select(
        _input(0), run_id="RUN-FUSION", trace_id="TRACE-1"
    )
    second, _ = client.select(
        _input(1),
        run_id="RUN-FUSION",
        trace_id="TRACE-2",
        parent=first_checkpoint,
    )

    assert first.selected_operation == second.selected_operation == "web_search"
    assert len(extractor.calls) == 1
    assert len(extractor.view_calls) == 2
    assert len(head.seen) == 2
    assert first.token_position == 24
    assert second.token_position == 37
    assert first.raw_record()["postprocessed"] is False
    assert first.raw_record()["generated_text"] is False
