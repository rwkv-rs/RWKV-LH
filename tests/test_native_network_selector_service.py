from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import pytest

from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.native_network_client import (
    NativeNetworkSelectorClient,
    NativeNetworkSelectorSettings,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
)
from rwkv_lh.exact_tool_selector.native_network_service import (
    NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA,
    NativeNetworkSelectorService,
    NativeNetworkSelectorServiceError,
    load_native_selector_decoder_manifest,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
)
from rwkv_lh.schema import ActionRecord, ModelLaneKind
from rwkv_lh.goal_state_protocols import selector_intent_v6
from rwkv_lh.goal_loop_protocol import action_mutates_root, action_observes_root


def _manifest() -> dict[str, Any]:
    return {
        "schema_version": NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA,
        "decoder_id": NATIVE_SELECTOR_DECODER_ID,
        "decoder_protocol": NATIVE_SELECTOR_DECODER_PROTOCOL,
        "input_protocol": CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
        "target_prefix": selector_intent_v6.TARGET_PREFIX,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "algorithm": "eligible_token_sequence_trie_vocab_logit_argmax",
        "token_tie_break": "lowest_token_id",
        "state_policy": "fresh_initial_state_per_evaluation",
        "menu_aggregation": "majority_then_registered_class_order",
        "downstream_decoder_trained": False,
        "generated_text": False,
    }


def _settings(*, zero: bool = False) -> NativeNetworkSelectorSettings:
    return NativeNetworkSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="rwkv7-g1j-2.9b-20260831-ctx16384",
        model_sha256="a" * 64,
        decoder_id=NATIVE_SELECTOR_DECODER_ID,
        decoder_sha256="b" * 64,
        decoder_protocol=NATIVE_SELECTOR_DECODER_PROTOCOL,
        state_profile_id="zero" if zero else "selector-progress-2p9-v4",
        state_profile_sha256=("0" if zero else "d") * 64,
        state_profile_manifest_sha256=("0" if zero else "e") * 64,
    )


def _input() -> NetworkSelectorInput:
    action = ActionRecord.from_dict(
        {
            "action_id": "A1",
            "sequence": 1,
            "action_type": "read_json",
            "status": "succeeded",
            "arguments": {"path": "left.json"},
            "result": {"success": True, "outcome_type": "success"},
        }
    )
    progress = selector_intent_v6.build_current_progress(
        assigned_actions=[action],
        read_roots=("left.json", "right.json"),
        write_roots=(),
        mechanical_evidence={
            "missing_read_roots": ["right.json"],
            "missing_write_roots": [],
            "completion_preconditions_satisfied": False,
        },
        target_descriptors=[
            {"path": "left.json", "target_kind": "json_file"},
            {"path": "right.json", "target_kind": "json_file"},
        ],
        action_observes_root=action_observes_root,
        action_mutates_root=action_mutates_root,
    )
    return NetworkSelectorInput.create(
        current_subtask={
            "objective": "Inspect both structured records before deriving evidence.",
            "phase": "observe",
            "read_roots": ["left.json", "right.json"],
            "write_roots": [],
            "success_evidence": ["both canonical JSON values were observed"],
            "constraints": ["do not modify local files"],
        },
        current_progress=progress,
        eligible_labels=("read_file", "read_json", "file_digest"),
    )


class _Extractor:
    def __init__(self, settings: NativeNetworkSelectorSettings) -> None:
        self.settings = settings
        self.calls: list[tuple[str, dict[str, str]]] = []

    def select_suffix_choices(self, prompt: str, *, candidate_suffixes):
        suffixes = dict(candidate_suffixes)
        self.calls.append((prompt, suffixes))
        selected = "read_json"
        identity: dict[str, Any] = {
            "model_weights_sha256": self.settings.model_sha256,
            "wkv_mode": "fp32io16",
            "max_tokens": self.settings.context_tokens,
            "runtime": {"wkv_mode": "fp32io16", "wkv_state_dtype": "torch.float32", "runtime_compute_dtype": "torch.float16"},
            "feature_protocol": "rwkv-lh.native-role-suffix-selection.v1",
            "fresh_initial_state": True,
            "one_prompt_forward": True,
            "post_prompt_state_clones": 0,
            "token_sequence_exact": True,
            "expected_label_supplied": False,
            "teacher_forcing_invoked": False,
            "unrestricted_generation_invoked": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
            "downstream_decoder_trained": False,
        }
        if self.settings.state_profile_id != "zero":
            identity["state_profile"] = {
                "manifest": "/fixture/manifest.json",
                "manifest_sha256": self.settings.state_profile_manifest_sha256,
                "id": self.settings.state_profile_id,
                "sha256": self.settings.state_profile_sha256,
            }
        return (
            {
                "schema_version": "rwkv-lh.native-role-suffix-selection.v1",
                "candidate_labels": list(suffixes),
                "prompt_token_count": 811,
                "selected_label": selected,
                "token_ids": [1, 2],
                "decisions": [
                    {
                        "position": 0,
                        "allowed_token_ids": [1, 3],
                        "allowed_token_logits": {"1": 2.0, "3": 1.0},
                        "chosen_token_id": 1,
                        "chosen_token_logit": 2.0,
                        "chosen_vs_runner_up_margin": 1.0,
                    }
                ],
            },
            identity,
        )


def test_native_selector_rejects_serving_state_precision_drift():
    settings = _settings(zero=True)
    extractor = _Extractor(settings)
    service = NativeNetworkSelectorService(settings, extractor, _manifest())
    _, identity = extractor.select_suffix_choices("mechanism", candidate_suffixes={"read_json": "read_json"})
    identity.update(wkv_mode="fp16", wkv_state_dtype="torch.float16")
    with pytest.raises(NativeNetworkSelectorServiceError, match="identity mismatch"):
        service._validate_extractor_identity(identity)


def test_native_selector_attests_context_and_arithmetic():
    identity = _settings(zero=True).runtime_identity()
    assert identity["wkv_mode"] == "fp32io16"
    assert identity["state_dtype"] == "float32"
    assert identity["context_tokens"] == 16384


def test_native_selector_context_comes_from_artifact_and_rejects_overflow(tmp_path):
    from rwkv_lh.exact_tool_selector.native_network_service import model_context_tokens
    (tmp_path / "config.json").write_text(json.dumps({"context_length": 8192, "max_position_embeddings": 8192}))
    assert model_context_tokens(tmp_path, None) == 8192
    assert model_context_tokens(tmp_path, 4096) == 4096
    with pytest.raises(ValueError, match="context"):
        model_context_tokens(tmp_path, 16384)


class _Response:
    status_code = 200
    text = ""

    def __init__(self, value: Mapping[str, Any]) -> None:
        self.content = json.dumps(value, ensure_ascii=False).encode("utf-8")


class _LocalSession:
    def __init__(self, service: NativeNetworkSelectorService) -> None:
        self.service = service

    def post(self, _url: str, *, json: Mapping[str, Any], timeout):
        return _Response(self.service.select(json))


def test_native_service_uses_progress_v4_and_no_external_head() -> None:
    settings = _settings()
    extractor = _Extractor(settings)
    service = NativeNetworkSelectorService(settings, extractor, _manifest())
    client = NativeNetworkSelectorClient(settings, session=_LocalSession(service))

    selection, checkpoint = client.select(
        _input(), run_id="RUN-NATIVE", trace_id="TRACE-NATIVE"
    )

    assert selection.selected_operation == "read_json"
    assert selection.decoder_id == NATIVE_SELECTOR_DECODER_ID
    assert checkpoint.lane_kind is ModelLaneKind.SELECTOR
    assert checkpoint.parent_checkpoint_id is None
    assert checkpoint.transport == (
        "native_rwkv_lm_head_suffix_trie_selector_intent_v6"
    )
    assert checkpoint.native_state_metadata["downstream_decoder_trained"] is False
    assert checkpoint.native_state_metadata["generated_rwkv_text"] is False
    assert "decoder_trace_sha256" in checkpoint.native_state_metadata
    assert len(extractor.calls) == 1
    prompt, suffixes = extractor.calls[0]
    assert prompt.startswith(selector_intent_v6.MENU_PREFIX)
    assert selector_intent_v6.ROLE_MARKER in prompt
    assert "\n" + selector_intent_v6.PROMPT_PREFIX in prompt
    assert '"current_progress"' in prompt
    assert list(suffixes) == ["read_file", "read_json", "file_digest"]
    assert all(
        value.startswith(selector_intent_v6.TARGET_PREFIX)
        for value in suffixes.values()
    )
    wire = json.dumps(selection.raw_record(), ensure_ascii=False)
    assert "head_sha256" not in wire
    assert "head_hash" not in wire
    assert "expected_label" not in wire


def test_native_service_rejects_noncanonical_progress() -> None:
    settings = _settings()
    service = NativeNetworkSelectorService(
        settings, _Extractor(settings), _manifest()
    )
    client = NativeNetworkSelectorClient(settings, session=_LocalSession(service))
    request = client._request_payload(
        _input(), run_id="RUN-NATIVE", trace_id="TRACE-NATIVE"
    )
    step = json.loads(
        request["step"].removeprefix("SelectorIntentPromptV6: ")
    )
    step["current_progress"]["missing_read_roots"] = []
    request["step"] = "SelectorIntentPromptV6: " + json.dumps(
        step, ensure_ascii=False, separators=(",", ":")
    )

    with pytest.raises(
        (NativeNetworkSelectorServiceError, ValueError),
        match="canonical|digest|completion",
    ):
        service.select(request)


def test_native_decoder_manifest_is_exact_and_hash_bound(tmp_path: Path) -> None:
    path = tmp_path / "native_decoder_manifest.json"
    path.write_text(
        json.dumps(_manifest(), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    sha256 = hashlib.sha256(path.read_bytes()).hexdigest()

    assert load_native_selector_decoder_manifest(path, sha256) == _manifest()
    with pytest.raises(ValueError, match="SHA-256"):
        load_native_selector_decoder_manifest(path, "0" * 64)


def test_native_decoder_and_suffixes_share_selector_target_prefix(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    prefix = "\nSelectorAuthorityProbe: "
    monkeypatch.setattr(selector_intent_v6, "TARGET_PREFIX", prefix)
    manifest = _manifest()
    manifest["target_prefix"] = prefix
    path = tmp_path / "decoder.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    loaded = load_native_selector_decoder_manifest(
        path, hashlib.sha256(path.read_bytes()).hexdigest()
    )
    settings = _settings()
    extractor = _Extractor(settings)
    service = NativeNetworkSelectorService(settings, extractor, loaded)
    client = NativeNetworkSelectorClient(settings, session=_LocalSession(service))
    client.select(_input(), run_id="RUN-PREFIX", trace_id="TRACE-PREFIX")
    assert all(
        suffix == prefix + label
        for label, suffix in extractor.calls[0][1].items()
    )


@pytest.mark.parametrize("version", ("", "unknown", "v2", "v3", "v4", "v999"))
def test_selector_rejects_every_noncurrent_protocol(version: str) -> None:
    schema = selector_intent_v6.INPUT_SCHEMA_VERSION.rsplit(".", 1)[0] + "." + version
    with pytest.raises(ValueError, match="unsupported network Selector input protocol"):
        network_selector_input_protocol(schema)


def test_native_zero_service_rejects_accidental_state_profile() -> None:
    settings = _settings(zero=True)
    extractor = _Extractor(settings)

    class BadZeroExtractor(_Extractor):
        def select_suffix_choices(self, prompt: str, *, candidate_suffixes):
            result, identity = super().select_suffix_choices(
                prompt, candidate_suffixes=candidate_suffixes
            )
            identity = {
                **identity,
                "state_profile": {
                    "manifest_sha256": "0" * 64,
                    "id": "zero",
                    "sha256": "0" * 64,
                },
            }
            return result, identity

    service = NativeNetworkSelectorService(
        settings, BadZeroExtractor(settings), _manifest()
    )
    client = NativeNetworkSelectorClient(settings, session=_LocalSession(service))
    with pytest.raises(Exception, match="unexpectedly loaded"):
        client.select(_input(), run_id="RUN-NATIVE", trace_id="TRACE-NATIVE")
