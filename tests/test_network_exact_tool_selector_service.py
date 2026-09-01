from __future__ import annotations

import json
from collections.abc import Mapping
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import torch

from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_QUESTION_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
    DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL,
    FULL_REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
    REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.network_service import (
    NetworkSelectorService,
    NetworkSelectorStateStore,
    TorchNetworkSelectorHead,
)


ROOT = Path(__file__).resolve().parents[1]
HEAD = (
    ROOT
    / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
    / "run_r1/last/selector_head.json"
)
HEAD_SHA256 = "911f30a01f492a4df8183ed1ce8b6de3b8d40a7b690971250fec22820edf3095"
HEAD_HASH = "df856c6fcf482eac1fa48f817c931e6a078959993d15112ddf48502cf496e1c0"


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
        assert text.startswith("\nSelectorStepV3: ") if continuation else text.startswith(
            "SelectorMenuV3: "
        )
        if not continuation:
            assert "\nSelectorTaskV3: " in text
            assert "\nSelectorStepV3: " in text
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
        assert text.startswith(("\nSelectorStepV3: ", "\nSelectorStepV4: "))
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
        self.artifact = SimpleNamespace(
            feature_dim=5120,
            metadata={
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
            },
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
        head_sha256=HEAD_SHA256,
        head_hash=HEAD_HASH,
        feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        state_profile_id="selector-zero-s0",
        state_profile_sha256="b" * 64,
        state_profile_manifest_sha256="c" * 64,
        input_protocol=DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL,
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
        TorchNetworkSelectorHead(HEAD, HEAD_SHA256),
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
        _MeanHead(settings),
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
    assert extractor.calls[0][0].startswith("SelectorMenuV3: ")
    assert "\nSelectorTaskV3: " in extractor.calls[0][0]
    assert extractor.calls[0][1:] == (
        False,
        "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
    )
    assert extractor.calls[1][0].startswith("\nSelectorStepV3: ")
    assert extractor.calls[1][1:] == (
        True,
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
    )
    assert extractor.calls[2][0].startswith("\nSelectorStepV3: ")
    assert extractor.calls[2][1:] == (
        True,
        "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
    )
    assert first.token_position == 22
    assert second.token_position == 33


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


def test_service_v4_advances_on_request_last_step_without_text_generation(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            "input_protocol": REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
        }
    )
    extractor = _MeanExtractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _MeanHead(settings),
        NetworkSelectorStateStore(tmp_path / "v4-dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    first, checkpoint = client.select(
        _input(0), run_id="RUN-V4", trace_id="TRACE-V4"
    )

    step_text = extractor.calls[1][0]
    payload = json.loads(step_text.removeprefix("\nSelectorStepV4: "))
    assert list(payload)[-1] == "stage_objective"
    assert first.raw_record()["generated_text"] is False
    assert checkpoint.native_state_metadata["postprocessed"] is False


def test_service_v5_repeats_full_requirement_at_each_continuation_edge(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            "input_protocol": FULL_REQUEST_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
        }
    )
    extractor = _MeanExtractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _MeanHead(settings),
        NetworkSelectorStateStore(tmp_path / "v5-dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    _, checkpoint = client.select(_input(0), run_id="RUN-V5", trace_id="TRACE-V5-1")
    _, continued = client.select(
        _input(1),
        run_id="RUN-V5",
        trace_id="TRACE-V5-2",
        parent=checkpoint,
    )

    first_step = json.loads(extractor.calls[1][0].removeprefix("\nSelectorStepV5: "))
    second_step = json.loads(extractor.calls[2][0].removeprefix("\nSelectorStepV5: "))
    assert list(first_step)[-1] == list(second_step)[-1] == "current_requirement"
    assert first_step["current_requirement"] == second_step["current_requirement"] == (
        _input(0).task_request
    )
    assert continued.transport == "native_rwkv_hidden_mlp_selector_v5_full_request_last"


def test_service_v6_repeats_complete_live_question_at_each_continuation_edge(
    tmp_path: Path,
) -> None:
    base = _settings()
    settings = NetworkExactToolSelectorSettings(
        **{
            **base.__dict__,
            "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
            "input_protocol": CURRENT_QUESTION_LAST_NETWORK_SELECTOR_INPUT_PROTOCOL,
        }
    )
    extractor = _MeanExtractor()
    service = NetworkSelectorService(
        settings,
        extractor,
        _MeanHead(settings),
        NetworkSelectorStateStore(tmp_path / "v6-dynamic-selector-state"),
    )
    client = NetworkExactToolSelectorClient(settings, session=_LocalSession(service))

    _, checkpoint = client.select(_input(0), run_id="RUN-V6", trace_id="TRACE-V6-1")
    _, continued = client.select(
        _input(1),
        run_id="RUN-V6",
        trace_id="TRACE-V6-2",
        parent=checkpoint,
    )

    first = json.loads(extractor.calls[1][0].removeprefix("\nSelectorStepV6: "))
    second = json.loads(extractor.calls[2][0].removeprefix("\nSelectorStepV6: "))
    for step in (first, second):
        assert list(step)[-1] == "current_question"
        assert list(step["current_question"])[-1] == "question"
        assert step["current_question"]["complete_requirement"] == _input(0).task_request
    assert continued.transport == "native_rwkv_hidden_mlp_selector_v6_current_question_last"
