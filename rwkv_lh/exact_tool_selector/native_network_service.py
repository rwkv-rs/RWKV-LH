"""Native G1J Selector service using only the frozen LM head and token trie."""

from __future__ import annotations

import argparse
import hashlib
import json
import threading
from collections.abc import Mapping
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Protocol

from rwkv_lh.exact_tool_selector.input_protocol import (
    G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.native_network_client import (
    NATIVE_SELECTOR_SERVICE_REQUEST_SCHEMA,
    NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NativeNetworkSelectorSettings,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
    NativeNetworkToolSelection,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
)
from rwkv_lh.inference.vllm_rwkv import PersistentVLLMRWKVExtractor
from rwkv_lh.goal_state_protocols import selector_intent_v4
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings


NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA = (
    "rwkv-lh.native-selector-decoder-manifest.v1"
)
_REQUEST_KEYS = {
    "schema_version",
    "run_id",
    "trace_id",
    "input_digest",
    "menu_digest",
    "menu_order_id",
    "eligible_labels",
    "bootstrap",
    "step",
    "expected_identity",
}
_MANIFEST_KEYS = {
    "schema_version",
    "decoder_id",
    "decoder_protocol",
    "input_protocol",
    "target_prefix",
    "labels",
    "algorithm",
    "token_tie_break",
    "state_policy",
    "menu_aggregation",
    "downstream_decoder_trained",
    "generated_text",
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class NativeNetworkSelectorServiceError(ValueError):
    """A native Selector request or artifact violated the frozen contract."""


class _NativeSuffixExtractor(Protocol):
    def select_suffix_choices(
        self,
        prompt: str,
        *,
        candidate_suffixes: Mapping[str, str],
    ) -> tuple[Mapping[str, Any], Mapping[str, Any]]: ...


def load_native_selector_decoder_manifest(
    path: Path,
    expected_sha256: str,
) -> dict[str, Any]:
    """Load the non-learned decoder identity and reject contract drift."""

    resolved = path.resolve()
    if not resolved.is_file() or _sha256_file(resolved) != expected_sha256:
        raise ValueError("native Selector decoder manifest SHA-256 mismatch")
    value = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(value, dict) or set(value) != _MANIFEST_KEYS:
        raise ValueError("native Selector decoder manifest fields mismatch")
    expected = {
        "schema_version": NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA,
        "decoder_id": NATIVE_SELECTOR_DECODER_ID,
        "decoder_protocol": NATIVE_SELECTOR_DECODER_PROTOCOL,
        "input_protocol": G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL,
        "target_prefix": selector_intent_v4.TARGET_PREFIX,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "algorithm": "eligible_token_sequence_trie_vocab_logit_argmax",
        "token_tie_break": "lowest_token_id",
        "state_policy": "fresh_initial_state_per_evaluation",
        "menu_aggregation": "majority_then_registered_class_order",
        "downstream_decoder_trained": False,
        "generated_text": False,
    }
    if value != expected:
        raise ValueError("native Selector decoder manifest identity mismatch")
    return value


class NativeNetworkSelectorService:
    """Select one eligible operation from a fresh G1J initial State."""

    def __init__(
        self,
        settings: NativeNetworkSelectorSettings,
        extractor: _NativeSuffixExtractor,
        decoder_manifest: Mapping[str, Any],
    ) -> None:
        expected_manifest = {
            "schema_version": NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA,
            "decoder_id": settings.decoder_id,
            "decoder_protocol": settings.decoder_protocol,
            "input_protocol": settings.input_protocol,
            "target_prefix": selector_intent_v4.TARGET_PREFIX,
            "labels": list(NETWORK_EXACT_TOOL_LABELS),
            "algorithm": "eligible_token_sequence_trie_vocab_logit_argmax",
            "token_tie_break": "lowest_token_id",
            "state_policy": "fresh_initial_state_per_evaluation",
            "menu_aggregation": "majority_then_registered_class_order",
            "downstream_decoder_trained": False,
            "generated_text": False,
        }
        if dict(decoder_manifest) != expected_manifest:
            raise ValueError("native Selector decoder manifest differs from settings")
        self.settings = settings
        self.input_protocol = network_selector_input_protocol(settings.input_protocol)
        self.extractor = extractor
        self._lock = threading.Lock()

    @staticmethod
    def _parse_prefixed_json(text: str, prefix: str) -> dict[str, Any]:
        if not text.startswith(prefix):
            raise NativeNetworkSelectorServiceError(
                f"native Selector input lacks {prefix.rstrip()!r}"
            )
        try:
            value = json.loads(text[len(prefix) :])
        except json.JSONDecodeError as exc:
            raise NativeNetworkSelectorServiceError(
                "native Selector rendered input is invalid JSON"
            ) from exc
        if not isinstance(value, dict):
            raise NativeNetworkSelectorServiceError(
                "native Selector rendered payload must be an object"
            )
        return value

    def _parse_bootstrap(self, text: str) -> dict[str, Any]:
        marker = self.input_protocol.task_marker
        if text.count(marker) != 1:
            raise NativeNetworkSelectorServiceError(
                "native Selector bootstrap must contain one menu and role"
            )
        menu_text, role_json = text.split(marker, 1)
        menu = self._parse_prefixed_json(
            menu_text, self.input_protocol.menu_prefix
        )
        role = self._parse_prefixed_json(
            self.input_protocol.task_prefix + role_json,
            self.input_protocol.task_prefix,
        )
        if set(role) != {"schema_version"} or role.get("schema_version") != (
            G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL
        ):
            raise NativeNetworkSelectorServiceError(
                "native Selector role fields changed"
            )
        return menu

    def _input(self, request: Mapping[str, Any]) -> NetworkSelectorInput:
        step_text = str(request["step"])
        step = self._parse_prefixed_json(
            step_text, self.input_protocol.step_prefix
        )
        if set(step) != {
            "schema_version",
            "role",
            "eligible_labels",
            "current_subtask",
            "current_progress",
            "current_question",
        }:
            raise NativeNetworkSelectorServiceError(
                "G1J Selector-Intent v4 prompt fields changed"
            )
        if (
            step.get("schema_version") != G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL
            or step.get("role") != "selector_intent"
            or list(step.get("eligible_labels") or ())
            != list(request.get("eligible_labels") or ())
            or not isinstance(step.get("current_subtask"), Mapping)
            or not isinstance(step.get("current_progress"), Mapping)
        ):
            raise NativeNetworkSelectorServiceError(
                "G1J Selector-Intent v4 prompt identity changed"
            )
        selector_input = NetworkSelectorInput.create(
            current_subtask=dict(step["current_subtask"]),
            current_progress=dict(step["current_progress"]),
            eligible_labels=tuple(request.get("eligible_labels") or ()),
            menu_order_id=str(request.get("menu_order_id") or ""),
        )
        bootstrap = self._parse_bootstrap(str(request["bootstrap"]))
        if self.input_protocol.bootstrap_payload(selector_input) != bootstrap:
            raise NativeNetworkSelectorServiceError(
                "native Selector bootstrap payload is not canonical"
            )
        if self.input_protocol.render_bootstrap(selector_input) != request["bootstrap"]:
            raise NativeNetworkSelectorServiceError(
                "native Selector bootstrap is not canonical"
            )
        if self.input_protocol.render_step(selector_input) != step_text:
            raise NativeNetworkSelectorServiceError(
                "native Selector step is not canonical"
            )
        if self.input_protocol.menu_digest(selector_input) != request["menu_digest"]:
            raise NativeNetworkSelectorServiceError(
                "native Selector menu digest mismatch"
            )
        if self.input_protocol.input_digest(selector_input) != request["input_digest"]:
            raise NativeNetworkSelectorServiceError(
                "native Selector input digest mismatch"
            )
        return selector_input

    def _validate_extractor_identity(self, identity: Mapping[str, Any]) -> None:
        expected = {
            "model_weights_sha256": self.settings.model_sha256,
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
        if any(identity.get(key) != value for key, value in expected.items()):
            raise NativeNetworkSelectorServiceError(
                "native Selector extractor identity mismatch"
            )
        state_profile = identity.get("state_profile")
        if self.settings.state_profile_id == "zero":
            if state_profile is not None:
                raise NativeNetworkSelectorServiceError(
                    "zero native Selector unexpectedly loaded a State profile"
                )
            return
        expected_profile = {
            "manifest_sha256": self.settings.state_profile_manifest_sha256,
            "id": self.settings.state_profile_id,
            "sha256": self.settings.state_profile_sha256,
        }
        if not isinstance(state_profile, Mapping) or any(
            state_profile.get(key) != value
            for key, value in expected_profile.items()
        ):
            raise NativeNetworkSelectorServiceError(
                "native Selector loaded State profile identity mismatch"
            )

    def select(self, request: Mapping[str, Any]) -> dict[str, Any]:
        if set(request) != _REQUEST_KEYS:
            raise NativeNetworkSelectorServiceError(
                "native Selector request fields mismatch"
            )
        if request.get("schema_version") != NATIVE_SELECTOR_SERVICE_REQUEST_SCHEMA:
            raise NativeNetworkSelectorServiceError(
                "unsupported native Selector request schema"
            )
        if request.get("expected_identity") != self.settings.runtime_identity():
            raise NativeNetworkSelectorServiceError(
                "native Selector expected runtime identity mismatch"
            )
        if not str(request.get("run_id") or "").strip() or not str(
            request.get("trace_id") or ""
        ).strip():
            raise NativeNetworkSelectorServiceError(
                "native Selector run/trace identity is missing"
            )
        request_digest = canonical_digest(dict(request))
        with self._lock:
            selector_input = self._input(request)
            full_text = (
                self.input_protocol.render_bootstrap(selector_input)
                + "\n"
                + self.input_protocol.render_step(selector_input)
            )
            suffixes = {
                label: selector_intent_v4.TARGET_PREFIX + label
                for label in selector_input.eligible_labels
            }
            decoder_trace, extractor_identity = self.extractor.select_suffix_choices(
                full_text,
                candidate_suffixes=suffixes,
            )
            self._validate_extractor_identity(extractor_identity)
            if (
                decoder_trace.get("schema_version")
                != "rwkv-lh.native-role-suffix-selection.v1"
                or list(decoder_trace.get("candidate_labels") or ())
                != list(selector_input.eligible_labels)
                or decoder_trace.get("selected_label")
                not in selector_input.eligible_labels
            ):
                raise NativeNetworkSelectorServiceError(
                    "native Selector decoder result is inconsistent"
                )
            suffix = request_digest[:24]
            selection = NativeNetworkToolSelection(
                selection_id=f"NSEL-{suffix}",
                trace_id=str(request["trace_id"]),
                selected_operation=str(decoder_trace["selected_label"]),
                input_digest=str(request["input_digest"]),
                menu_digest=str(request["menu_digest"]),
                selector_checkpoint_id=f"NSCP-{suffix}",
                input_token_count=int(decoder_trace["prompt_token_count"]),
                model=self.settings.model,
                model_sha256=self.settings.model_sha256,
                decoder_id=self.settings.decoder_id,
                decoder_sha256=self.settings.decoder_sha256,
                decoder_protocol=self.settings.decoder_protocol,
                profile_id=self.settings.state_profile_id,
                profile_sha256=self.settings.state_profile_sha256,
                decoder_trace=dict(decoder_trace),
                eligible_labels=selector_input.eligible_labels,
            )
            return {
                "schema_version": NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }


def _handler(service: NativeNetworkSelectorService):
    class Handler(BaseHTTPRequestHandler):
        def _json(self, status: int, value: Mapping[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_GET(self) -> None:  # noqa: N802
            if self.path != "/healthz":
                self._json(404, {"error": "not_found"})
                return
            self._json(
                200,
                {
                    "status": "ok",
                    "runtime_identity": service.settings.runtime_identity(),
                },
            )

        def do_POST(self) -> None:  # noqa: N802
            if self.path != service.input_protocol.endpoint:
                self._json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length") or "0")
                if length < 2 or length > 2_000_000:
                    raise NativeNetworkSelectorServiceError(
                        "invalid request body size"
                    )
                value = json.loads(self.rfile.read(length).decode("utf-8"))
                if not isinstance(value, Mapping):
                    raise NativeNetworkSelectorServiceError(
                        "request body must be an object"
                    )
                response = service.select(value)
            except (NativeNetworkSelectorServiceError, TypeError, ValueError) as exc:
                self._json(
                    400,
                    {"error": type(exc).__name__, "message": str(exc)[:2000]},
                )
                return
            except Exception as exc:
                self._json(
                    500,
                    {"error": type(exc).__name__, "message": str(exc)[:1000]},
                )
                return
            self._json(200, response)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


def _extractor_state_profile_settings(
    *,
    profile_manifest: Path | None,
    profile_manifest_sha256: str,
    profile_id: str,
    profile_sha256: str,
) -> dict[str, object]:
    zero_sha256 = "0" * 64
    if profile_manifest is None:
        if (
            profile_manifest_sha256 != zero_sha256
            or profile_id != "zero"
            or profile_sha256 != zero_sha256
        ):
            raise ValueError(
                "a manifest-free native Selector must use exact zero-State identity"
            )
        return {
            "state_profile_manifest": None,
            "state_profile_manifest_sha256": "",
            "state_profile_id": "",
            "state_profile_sha256": "",
        }
    return {
        "state_profile_manifest": profile_manifest,
        "state_profile_manifest_sha256": profile_manifest_sha256,
        "state_profile_id": profile_id,
        "state_profile_sha256": profile_sha256,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=29621)
    parser.add_argument("--engine-root", type=Path, required=True)
    parser.add_argument("--engine-revision", required=True)
    parser.add_argument("--engine-python", type=Path, required=True)
    parser.add_argument("--model-artifact", type=Path, required=True)
    parser.add_argument("--model-name", required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--decoder-manifest", type=Path, required=True)
    parser.add_argument("--decoder-sha256", required=True)
    parser.add_argument(
        "--input-protocol", default=G1J_SELECTOR_INTENT_V4_INPUT_PROTOCOL
    )
    parser.add_argument("--profile-manifest", type=Path)
    parser.add_argument("--profile-manifest-sha256", default="0" * 64)
    parser.add_argument("--profile-id", default="zero")
    parser.add_argument("--profile-sha256", default="0" * 64)
    parser.add_argument("--runtime-temp", type=Path, required=True)
    args = parser.parse_args()

    manifest = load_native_selector_decoder_manifest(
        args.decoder_manifest,
        args.decoder_sha256,
    )
    settings = NativeNetworkSelectorSettings(
        base_url=f"http://{args.host}:{args.port}",
        model=args.model_name,
        model_sha256=args.model_sha256,
        decoder_id=NATIVE_SELECTOR_DECODER_ID,
        decoder_sha256=args.decoder_sha256,
        decoder_protocol=NATIVE_SELECTOR_DECODER_PROTOCOL,
        state_profile_id=args.profile_id,
        state_profile_sha256=args.profile_sha256,
        state_profile_manifest_sha256=args.profile_manifest_sha256,
        input_protocol=args.input_protocol,
    )
    extractor_profile_settings = _extractor_state_profile_settings(
        profile_manifest=args.profile_manifest,
        profile_manifest_sha256=args.profile_manifest_sha256,
        profile_id=args.profile_id,
        profile_sha256=args.profile_sha256,
    )
    extractor = PersistentVLLMRWKVExtractor(
        LocalVLLMRWKVSettings(
            engine_root=args.engine_root,
            engine_revision=args.engine_revision,
            engine_python=args.engine_python,
            model=args.model_artifact,
            batch_size=1,
            max_tokens=4096,
            wkv_mode="fp16",
            runtime_temp=args.runtime_temp,
            compatibility_sha256="0" * 64,
            **extractor_profile_settings,
        )
    )
    service = NativeNetworkSelectorService(settings, extractor, manifest)
    extractor.load()
    server = ThreadingHTTPServer((args.host, args.port), _handler(service))
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "NATIVE_SELECTOR_DECODER_MANIFEST_SCHEMA",
    "NativeNetworkSelectorService",
    "NativeNetworkSelectorServiceError",
    "load_native_selector_decoder_manifest",
]
