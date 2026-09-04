"""Fail-closed client for the independent fresh-state Selector service."""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import requests

from rwkv_lh.exact_tool_selector.input_protocol import (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.head import NETWORK_SELECTOR_FEATURE_PROTOCOLS
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkExactToolSelection,
    NetworkSelectorInput,
)
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.runtime.role_config import role_env, role_float
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus, ModelLaneKind


NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-request.v5"
)
NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-response.v4"
)
NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL = CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
NETWORK_SELECTOR_LANE_ID = "LANE:SELECTOR"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class NetworkExactToolSelectorError(RWKVRuntimeError):
    """The Selector service violated its frozen identity or wire contract."""


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
class NetworkExactToolSelectorSettings:
    base_url: str
    model: str
    model_sha256: str
    head_sha256: str
    head_hash: str
    feature_protocol: str
    state_profile_id: str
    state_profile_sha256: str
    state_profile_manifest_sha256: str
    input_protocol: str = NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_SELECTOR_BASE_URL must be absolute HTTP(S)")
        if not self.model.strip():
            raise ValueError("RWKV_SELECTOR_MODEL must be non-empty")
        for name, value in (
            ("model", self.model_sha256),
            ("head file", self.head_sha256),
            ("head", self.head_hash),
            ("state profile", self.state_profile_sha256),
            ("state manifest", self.state_profile_manifest_sha256),
        ):
            if not _SHA256_PATTERN.fullmatch(value):
                raise ValueError(f"network Selector {name} SHA-256 is invalid")
        if not _PROFILE_ID_PATTERN.fullmatch(self.state_profile_id):
            raise ValueError("RWKV_SELECTOR_STATE_PROFILE_ID is invalid")
        if self.feature_protocol not in NETWORK_SELECTOR_FEATURE_PROTOCOLS:
            raise ValueError("network Selector feature protocol is invalid")
        network_selector_input_protocol(self.input_protocol)
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("network Selector timeouts must be positive")

    @classmethod
    def from_env(cls) -> "NetworkExactToolSelectorSettings | None":
        names = {
            "base_url": ("BASE_URL", "RWKV_SELECTOR_BASE_URL"),
            "model": ("MODEL", "RWKV_SELECTOR_MODEL"),
            "model_sha256": ("MODEL_SHA256", "RWKV_SELECTOR_MODEL_SHA256"),
            "head_sha256": ("HEAD_SHA256", "RWKV_SELECTOR_HEAD_SHA256"),
            "head_hash": ("HEAD_HASH", "RWKV_SELECTOR_HEAD_HASH"),
            "feature_protocol": ("FEATURE_PROTOCOL", "RWKV_SELECTOR_FEATURE_PROTOCOL"),
            "state_profile_id": ("STATE_PROFILE_ID", "RWKV_SELECTOR_STATE_PROFILE_ID"),
            "state_profile_sha256": (
                "STATE_PROFILE_SHA256",
                "RWKV_SELECTOR_STATE_PROFILE_SHA256",
            ),
            "state_profile_manifest_sha256": (
                "STATE_PROFILE_MANIFEST_SHA256",
                "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256",
            ),
        }
        configured = any(
            os.environ.get(env_name, "").strip()
            for suffix, legacy in names.values()
            for env_name in (f"RWKV_LH_SELECTOR_{suffix}", legacy)
        )
        if not configured:
            return None
        values = {
            key: role_env("selector", suffix, legacy=legacy)
            for key, (suffix, legacy) in names.items()
        }
        values["base_url"] = values["base_url"].rstrip("/")
        missing = [
            f"RWKV_LH_SELECTOR_{names[key][0]}"
            for key, value in values.items()
            if not value
        ]
        if missing:
            raise ValueError("missing Selector identity settings: " + ", ".join(missing))
        return cls(
            **values,
            input_protocol=role_env(
                "selector",
                "input_protocol",
                legacy="RWKV_SELECTOR_INPUT_PROTOCOL",
                default=NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL,
            )
            or NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL,
            connect_timeout_seconds=role_float(
                "selector",
                "connect_timeout",
                legacy="RWKV_SELECTOR_CONNECT_TIMEOUT",
                default=10.0,
            ),
            read_timeout_seconds=role_float(
                "selector",
                "read_timeout",
                legacy="RWKV_SELECTOR_READ_TIMEOUT",
                default=120.0,
            ),
        )

    def runtime_identity(self) -> dict[str, str]:
        return {
            "input_protocol": self.input_protocol,
            "model": self.model,
            "model_sha256": self.model_sha256,
            "head_sha256": self.head_sha256,
            "head_hash": self.head_hash,
            "feature_protocol": self.feature_protocol,
            "profile_id": self.state_profile_id,
            "profile_sha256": self.state_profile_sha256,
            "profile_manifest_sha256": self.state_profile_manifest_sha256,
        }


class NetworkExactToolSelectorClient:
    """Evaluate each current subtask from the fixed learned initial profile."""

    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        *,
        session: _HTTPSession | None = None,
    ) -> None:
        self.settings = settings
        self.input_protocol = network_selector_input_protocol(settings.input_protocol)
        self._session = session or requests.Session()

    def _request_payload(
        self,
        selector_input: NetworkSelectorInput,
        *,
        run_id: str,
        trace_id: str,
    ) -> dict[str, Any]:
        if not str(run_id).strip() or not str(trace_id).strip():
            raise ValueError("network Selector request requires run_id and trace_id")
        return {
            "schema_version": NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA,
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
    ) -> tuple[NetworkExactToolSelection, ModelCheckpoint]:
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
            raise NetworkExactToolSelectorError(
                "network Selector transport failed with unknown outcome: "
                f"{type(exc).__name__}: {exc}"
            ) from exc
        if response.status_code != 200:
            raise NetworkExactToolSelectorError(
                f"network Selector HTTP {response.status_code}: {response.text[:1000]}"
            )
        try:
            value = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise NetworkExactToolSelectorError(
                "network Selector returned invalid UTF-8 JSON"
            ) from exc
        if not isinstance(value, Mapping):
            raise NetworkExactToolSelectorError("network Selector response must be an object")
        if value.get("schema_version") != NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA:
            raise NetworkExactToolSelectorError(
                "unsupported network Selector service response schema"
            )
        if value.get("runtime_identity") != self.settings.runtime_identity():
            raise NetworkExactToolSelectorError("network Selector runtime identity mismatch")
        raw_selection = value.get("selection")
        if not isinstance(raw_selection, Mapping):
            raise NetworkExactToolSelectorError(
                "network Selector response has no selection object"
            )
        try:
            selection = NetworkExactToolSelection.from_dict(raw_selection)
        except (TypeError, ValueError) as exc:
            raise NetworkExactToolSelectorError(str(exc)) from exc
        self._validate_selection(selection, payload)
        return selection, self._checkpoint(selection, selector_input)

    def _validate_selection(
        self,
        selection: NetworkExactToolSelection,
        payload: Mapping[str, Any],
    ) -> None:
        expected = {
            "trace_id": payload["trace_id"],
            "input_digest": payload["input_digest"],
            "menu_digest": payload["menu_digest"],
            "model": self.settings.model,
            "model_sha256": self.settings.model_sha256,
            "head_sha256": self.settings.head_sha256,
            "profile_id": self.settings.state_profile_id,
            "profile_sha256": self.settings.state_profile_sha256,
        }
        if any(getattr(selection, key) != value for key, value in expected.items()):
            raise NetworkExactToolSelectorError("network Selector response identity mismatch")
        if selection.eligible_labels != tuple(payload["eligible_labels"]):
            raise NetworkExactToolSelectorError(
                "network Selector response eligibility mismatch"
            )

    def _checkpoint(
        self,
        selection: NetworkExactToolSelection,
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
            lane_id=NETWORK_SELECTOR_LANE_ID,
            lane_kind=ModelLaneKind.SELECTOR,
            parent_checkpoint_id=None,
            model=self.settings.model,
            transport="native_rwkv_hidden_mlp_selector_g1j_selector_intent_v2",
            transcript=transcript,
            transcript_digest=transcript_digest,
            token_count=selection.input_token_count,
            native_state_metadata={
                **self.settings.runtime_identity(),
                "menu_digest": selection.menu_digest,
                "menu_order_id": selector_input.menu_order_id,
                "input_digest": selection.input_digest,
                "logits_sha256": selection.logits_sha256,
                "eligible_labels": list(selection.eligible_labels),
                "selection_rule": "eligible_raw_logit_argmax",
                "input_token_count": selection.input_token_count,
                "state_policy": "fresh_initial_state_per_evaluation",
                "generated_rwkv_text": False,
                "postprocessed": False,
                "authoritative": False,
            },
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
            status=ModelCheckpointStatus.COMMITTED,
        )


__all__ = [
    "NETWORK_SELECTOR_LANE_ID",
    "NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA",
    "NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA",
    "NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL",
    "NetworkExactToolSelectorClient",
    "NetworkExactToolSelectorError",
    "NetworkExactToolSelectorSettings",
]
