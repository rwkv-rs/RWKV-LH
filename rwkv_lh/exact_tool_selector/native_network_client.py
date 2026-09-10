"""Fail-closed client for the progress-aware native G1J Selector service."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import requests

from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
    NativeNetworkToolSelection,
)
from rwkv_lh.exact_tool_selector.network_protocol import NetworkSelectorInput
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.runtime.role_config import role_env, role_float
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus, ModelLaneKind


NATIVE_SELECTOR_SERVICE_REQUEST_SCHEMA = (
    "rwkv-lh.native-exact-tool-selector-service-request.v2"
)
NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA = (
    "rwkv-lh.native-exact-tool-selector-service-response.v2"
)
NATIVE_SELECTOR_LANE_ID = "LANE:SELECTOR"
NATIVE_SELECTOR_WKV_MODE = "fp32io16"
NATIVE_SELECTOR_CHECKPOINT_TRANSPORT = "native_rwkv_lm_head_suffix_trie_selector_intent_v6"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class NativeNetworkSelectorError(RWKVRuntimeError):
    """The native Selector service violated its frozen wire identity."""


class _HTTPResponse(Protocol):
    status_code: int
    content: bytes
    text: str


class _HTTPSession(Protocol):
    def post(
        self,
        url: str,
        *,
        json: Mapping[str, Any],
        timeout: tuple[float, float],
    ) -> _HTTPResponse: ...


@dataclass(frozen=True)
class NativeNetworkSelectorSettings:
    base_url: str
    model: str
    model_sha256: str
    decoder_id: str
    decoder_sha256: str
    decoder_protocol: str
    state_profile_id: str
    state_profile_sha256: str
    state_profile_manifest_sha256: str
    input_protocol: str = CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 120.0
    context_tokens: int = 16384

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_LH_SELECTOR_BASE_URL must be absolute HTTP(S)")
        if not self.model.strip():
            raise ValueError("RWKV_LH_SELECTOR_MODEL must be non-empty")
        for name, value in (
            ("model", self.model_sha256),
            ("decoder", self.decoder_sha256),
            ("state profile", self.state_profile_sha256),
            ("state manifest", self.state_profile_manifest_sha256),
        ):
            if not _SHA256_PATTERN.fullmatch(value):
                raise ValueError(f"native Selector {name} SHA-256 is invalid")
        if self.decoder_id != NATIVE_SELECTOR_DECODER_ID:
            raise ValueError("native Selector decoder ID is unsupported")
        if self.decoder_protocol != NATIVE_SELECTOR_DECODER_PROTOCOL:
            raise ValueError("native Selector decoder protocol is unsupported")
        if self.input_protocol != CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL:
            raise ValueError("native Selector requires the current feedback-aware input")
        network_selector_input_protocol(self.input_protocol)
        if not _PROFILE_ID_PATTERN.fullmatch(self.state_profile_id):
            raise ValueError("native Selector State profile ID is invalid")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("native Selector timeouts must be positive")
        if type(self.context_tokens) is not int or self.context_tokens < 8:
            raise ValueError("native Selector context must be an integer of at least 8 tokens")

    @classmethod
    def from_env(cls) -> "NativeNetworkSelectorSettings | None":
        names = {
            "base_url": "BASE_URL",
            "model": "MODEL",
            "model_sha256": "MODEL_SHA256",
            "decoder_id": "DECODER_ID",
            "decoder_sha256": "DECODER_SHA256",
            "decoder_protocol": "DECODER_PROTOCOL",
            "state_profile_id": "STATE_PROFILE_ID",
            "state_profile_sha256": "STATE_PROFILE_SHA256",
            "state_profile_manifest_sha256": "STATE_PROFILE_MANIFEST_SHA256",
        }
        # Any identity variable marks the Selector as configured; a partial
        # identity must fail closed below rather than silently disable the
        # independent Selector while the stack still reports healthy.
        configured = any(
            os.environ.get(f"RWKV_LH_SELECTOR_{suffix}", "").strip()
            for suffix in names.values()
        )
        if not configured:
            return None
        values = {
            key: role_env("selector", suffix)
            for key, suffix in names.items()
        }
        values["base_url"] = values["base_url"].rstrip("/")
        missing = [
            f"RWKV_LH_SELECTOR_{names[key]}"
            for key, value in values.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "missing native Selector identity settings: " + ", ".join(missing)
            )
        return cls(
            **values,
            context_tokens=int(role_env("selector", "context_tokens", default="16384")),
            input_protocol=role_env(
                "selector",
                "input_protocol",
                default=CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
            )
            or CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
            connect_timeout_seconds=role_float(
                "selector", "connect_timeout", default=10.0
            ),
            read_timeout_seconds=role_float(
                "selector", "read_timeout", default=120.0
            ),
        )

    def runtime_identity(self) -> dict[str, Any]:
        return {
            "input_protocol": self.input_protocol,
            "model": self.model,
            "model_sha256": self.model_sha256,
            "decoder_id": self.decoder_id,
            "decoder_sha256": self.decoder_sha256,
            "decoder_protocol": self.decoder_protocol,
            "profile_id": self.state_profile_id,
            "profile_sha256": self.state_profile_sha256,
            "profile_manifest_sha256": self.state_profile_manifest_sha256,
            "wkv_mode": NATIVE_SELECTOR_WKV_MODE,
            "state_dtype": "float32",
            "context_tokens": self.context_tokens,
        }


class NativeNetworkSelectorClient:
    """Evaluate each progress-aware menu lane from one learned initial State."""

    def __init__(
        self,
        settings: NativeNetworkSelectorSettings,
        *,
        session: _HTTPSession | None = None,
        audit_hook: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self.settings = settings
        self.input_protocol = network_selector_input_protocol(settings.input_protocol)
        self._session = session or requests.Session()
        self.audit_hook = audit_hook

    def _emit(self, event: Mapping[str, Any]) -> None:
        if self.audit_hook is None:
            return
        try:
            self.audit_hook(dict(event))
        except Exception:
            # An observer must never change Selector request semantics.
            return

    def _request_payload(
        self,
        selector_input: NetworkSelectorInput,
        *,
        run_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        if selector_input.current_progress is None:
            raise ValueError("native Selector request requires current_progress")
        if not str(run_id).strip() or not str(trace_id).strip():
            raise ValueError("native Selector request requires run and trace identity")
        return {
            "schema_version": NATIVE_SELECTOR_SERVICE_REQUEST_SCHEMA,
            "run_id": str(run_id),
            "trace_id": str(trace_id),
            "input_digest": self.input_protocol.input_digest(selector_input),
            "menu_digest": self.input_protocol.menu_digest(selector_input),
            "menu_order_id": selector_input.menu_order_id,
            "eligible_labels": list(selector_input.eligible_labels),
            "bootstrap": self.input_protocol.render_bootstrap(selector_input),
            "step": self.input_protocol.render_step(selector_input),
            "expected_identity": self.settings.runtime_identity(),
        }

    def select(
        self,
        selector_input: NetworkSelectorInput,
        *,
        run_id: str,
        trace_id: str | None = None,
    ) -> tuple[NativeNetworkToolSelection, ModelCheckpoint]:
        payload = self._request_payload(
            selector_input,
            run_id=run_id,
            trace_id=str(trace_id or f"SELTRACE-{uuid4().hex[:16]}"),
        )
        try:
            response = self._session.post(
                self.settings.base_url.rstrip("/") + self.input_protocol.endpoint,
                json=payload,
                timeout=(
                    self.settings.connect_timeout_seconds,
                    self.settings.read_timeout_seconds,
                ),
            )
        except requests.RequestException as exc:
            # The first cause is audited before the typed error propagates, so
            # a Selector transport failure is never a zero-event interruption.
            self._emit({
                "type": "selector_transport_error",
                "run_id": payload["run_id"], "trace_id": payload["trace_id"],
                "menu_order_id": payload["menu_order_id"],
                "error_type": type(exc).__name__,
                "error_message": str(exc)[:500],
            })
            raise NativeNetworkSelectorError(
                "native Selector transport failed with unknown outcome: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if response.status_code != 200:
            self._emit({
                "type": "selector_transport_error",
                "run_id": payload["run_id"], "trace_id": payload["trace_id"],
                "menu_order_id": payload["menu_order_id"],
                "error_type": "HTTPStatus",
                "error_message": f"HTTP {response.status_code}: {response.text[:500]}",
            })
            raise NativeNetworkSelectorError(
                f"native Selector HTTP {response.status_code}: {response.text[:1000]}"
            )
        try:
            value = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NativeNetworkSelectorError(
                "native Selector returned invalid UTF-8 JSON"
            ) from exc
        if not isinstance(value, Mapping):
            raise NativeNetworkSelectorError("native Selector response must be an object")
        if value.get("schema_version") != NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA:
            raise NativeNetworkSelectorError("unsupported native Selector response")
        if value.get("runtime_identity") != self.settings.runtime_identity():
            raise NativeNetworkSelectorError("native Selector runtime identity mismatch")
        raw_selection = value.get("selection")
        if not isinstance(raw_selection, Mapping):
            raise NativeNetworkSelectorError("native Selector response lacks selection")
        try:
            selection = NativeNetworkToolSelection.from_dict(raw_selection)
        except (TypeError, ValueError) as exc:
            raise NativeNetworkSelectorError(str(exc)) from exc
        expected = {
            "trace_id": payload["trace_id"],
            "input_digest": payload["input_digest"],
            "menu_digest": payload["menu_digest"],
            "model": self.settings.model,
            "model_sha256": self.settings.model_sha256,
            "decoder_id": self.settings.decoder_id,
            "decoder_sha256": self.settings.decoder_sha256,
            "decoder_protocol": self.settings.decoder_protocol,
            "profile_id": self.settings.state_profile_id,
            "profile_sha256": self.settings.state_profile_sha256,
        }
        if any(getattr(selection, key) != item for key, item in expected.items()):
            raise NativeNetworkSelectorError("native Selector response identity mismatch")
        if selection.eligible_labels != tuple(payload["eligible_labels"]):
            raise NativeNetworkSelectorError("native Selector eligibility mismatch")
        return selection, self._checkpoint(selection, selector_input)

    def _checkpoint(
        self,
        selection: NativeNetworkToolSelection,
        selector_input: NetworkSelectorInput,
    ) -> ModelCheckpoint:
        transcript = (
            self.input_protocol.render_bootstrap(selector_input)
            + "\n"
            + self.input_protocol.render_step(selector_input)
        )
        transcript_digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        return ModelCheckpoint(
            checkpoint_id=selection.selector_checkpoint_id,
            lane_id=NATIVE_SELECTOR_LANE_ID,
            lane_kind=ModelLaneKind.SELECTOR,
            parent_checkpoint_id=None,
            model=self.settings.model,
            transport=NATIVE_SELECTOR_CHECKPOINT_TRANSPORT,
            transcript=transcript,
            transcript_digest=transcript_digest,
            token_count=selection.input_token_count,
            native_state_metadata={
                **self.settings.runtime_identity(),
                "menu_digest": selection.menu_digest,
                "menu_order_id": selector_input.menu_order_id,
                "input_digest": selection.input_digest,
                "decoder_trace_sha256": selection.decoder_trace_sha256,
                "eligible_labels": list(selection.eligible_labels),
                "selection_rule": "native_eligible_suffix_trie_vocab_argmax",
                "state_policy": "fresh_initial_state_per_evaluation",
                "generated_rwkv_text": False,
                "downstream_decoder_trained": False,
                "postprocessed": False,
                "authoritative": False,
            },
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
            status=ModelCheckpointStatus.COMMITTED,
        )


__all__ = [
    "NATIVE_SELECTOR_LANE_ID",
    "NATIVE_SELECTOR_CHECKPOINT_TRANSPORT",
    "NATIVE_SELECTOR_SERVICE_REQUEST_SCHEMA",
    "NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA",
    "NativeNetworkSelectorClient",
    "NativeNetworkSelectorError",
    "NativeNetworkSelectorSettings",
]
