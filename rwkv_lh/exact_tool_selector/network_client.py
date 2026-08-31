"""Fail-closed client for the independent stateful 25-class Selector service."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urlparse
from uuid import uuid4

import requests

from rwkv_lh.exact_tool_selector.input_protocol import (
    DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.model_v2 import (
    NETWORK_SELECTOR_FEATURE_PROTOCOLS,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkExactToolSelection,
    NetworkSelectorInput,
)
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus, ModelLaneKind


NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-request.v3"
)
NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-response.v3"
)
NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL = DEFAULT_NETWORK_SELECTOR_INPUT_PROTOCOL
NETWORK_SELECTOR_LANE_ID = "LANE:SELECTOR"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class NetworkExactToolSelectorError(RWKVRuntimeError):
    """The 25-class Selector service violated its frozen contract."""


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
            "base_url": "RWKV_SELECTOR_BASE_URL",
            "model": "RWKV_SELECTOR_MODEL",
            "model_sha256": "RWKV_SELECTOR_MODEL_SHA256",
            "head_sha256": "RWKV_SELECTOR_HEAD_SHA256",
            "head_hash": "RWKV_SELECTOR_HEAD_HASH",
            "feature_protocol": "RWKV_SELECTOR_FEATURE_PROTOCOL",
            "state_profile_id": "RWKV_SELECTOR_STATE_PROFILE_ID",
            "state_profile_sha256": "RWKV_SELECTOR_STATE_PROFILE_SHA256",
            "state_profile_manifest_sha256": (
                "RWKV_SELECTOR_STATE_PROFILE_MANIFEST_SHA256"
            ),
        }
        values = {key: os.environ.get(name, "").strip() for key, name in names.items()}
        values["base_url"] = values["base_url"].rstrip("/")
        if not any(values.values()):
            return None
        if any(not value for value in values.values()):
            raise ValueError(
                "all 25-class RWKV_SELECTOR_* identity settings are required"
            )
        try:
            connect_timeout = float(
                os.environ.get("RWKV_SELECTOR_CONNECT_TIMEOUT", "10")
            )
            read_timeout = float(os.environ.get("RWKV_SELECTOR_READ_TIMEOUT", "120"))
        except ValueError as exc:
            raise ValueError("RWKV Selector timeouts must be numbers") from exc
        return cls(
            **values,
            input_protocol=os.environ.get(
                "RWKV_SELECTOR_INPUT_PROTOCOL",
                NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL,
            ).strip()
            or NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL,
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=read_timeout,
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
    """Append one causal selector step in a lane separate from the Executor."""

    def __init__(
        self,
        settings: NetworkExactToolSelectorSettings,
        *,
        session: _HTTPSession | None = None,
    ) -> None:
        self.settings = settings
        self.input_protocol = network_selector_input_protocol(
            settings.input_protocol
        )
        self._session = session or requests.Session()

    def _validate_parent(self, parent: ModelCheckpoint) -> None:
        metadata = parent.native_state_metadata or {}
        if (
            parent.lane_id != NETWORK_SELECTOR_LANE_ID
            or parent.lane_kind is not ModelLaneKind.SELECTOR
            or parent.status is not ModelCheckpointStatus.COMMITTED
            or parent.model != self.settings.model
            or parent.state_profile_id != self.settings.state_profile_id
            or parent.state_profile_sha256 != self.settings.state_profile_sha256
            or not parent.native_state_ref
            or not parent.native_state_digest
            or metadata.get("input_protocol") != self.settings.input_protocol
            or metadata.get("model_sha256") != self.settings.model_sha256
            or metadata.get("head_sha256") != self.settings.head_sha256
            or metadata.get("head_hash") != self.settings.head_hash
            or metadata.get("feature_protocol") != self.settings.feature_protocol
            or metadata.get("profile_manifest_sha256")
            != self.settings.state_profile_manifest_sha256
        ):
            raise NetworkExactToolSelectorError(
                "network Selector parent checkpoint identity mismatch"
            )

    def _request_payload(
        self,
        selector_input: NetworkSelectorInput,
        *,
        run_id: str,
        trace_id: str,
        parent: ModelCheckpoint | None,
    ) -> dict[str, Any]:
        if not str(run_id).strip() or not str(trace_id).strip():
            raise ValueError("network Selector request requires run_id and trace_id")
        bootstrap = self.input_protocol.render_bootstrap(selector_input)
        parent_value: dict[str, Any] | None = None
        if parent is not None:
            self._validate_parent(parent)
            bootstrap = ""
            parent_value = {
                "checkpoint_id": parent.checkpoint_id,
                "state_ref": parent.native_state_ref,
                "state_digest": parent.native_state_digest,
                "token_position": parent.token_count,
            }
        return {
            "schema_version": NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA,
            "run_id": str(run_id),
            "trace_id": str(trace_id),
            "input_digest": self.input_protocol.input_digest(selector_input),
            "menu_digest": self.input_protocol.menu_digest(),
            "eligible_labels": list(selector_input.eligible_labels),
            "bootstrap": bootstrap,
            "step": self.input_protocol.render_step(selector_input),
            "parent": parent_value,
            "expected_identity": self.settings.runtime_identity(),
        }

    def select(
        self,
        selector_input: NetworkSelectorInput,
        *,
        run_id: str,
        parent: ModelCheckpoint | None = None,
        trace_id: str | None = None,
    ) -> tuple[NetworkExactToolSelection, ModelCheckpoint]:
        selected_trace_id = str(trace_id or f"SELTRACE-{uuid4().hex[:16]}")
        payload = self._request_payload(
            selector_input,
            run_id=run_id,
            trace_id=selected_trace_id,
            parent=parent,
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
            raise NetworkExactToolSelectorError(
                "network Selector runtime identity mismatch"
            )
        raw_selection = value.get("selection")
        if not isinstance(raw_selection, Mapping):
            raise NetworkExactToolSelectorError(
                "network Selector response has no selection object"
            )
        try:
            selection = NetworkExactToolSelection.from_dict(raw_selection)
        except (TypeError, ValueError) as exc:
            raise NetworkExactToolSelectorError(str(exc)) from exc
        self._validate_selection(selection, payload, parent)
        return selection, self._checkpoint(selection, selector_input, parent)

    def _validate_selection(
        self,
        selection: NetworkExactToolSelection,
        payload: Mapping[str, Any],
        parent: ModelCheckpoint | None,
    ) -> None:
        expected_parent_digest = "" if parent is None else str(parent.native_state_digest)
        expected = {
            "trace_id": payload["trace_id"],
            "input_digest": payload["input_digest"],
            "menu_digest": payload["menu_digest"],
            "selector_parent_state_digest": expected_parent_digest,
            "model": self.settings.model,
            "model_sha256": self.settings.model_sha256,
            "head_sha256": self.settings.head_sha256,
            "profile_id": self.settings.state_profile_id,
            "profile_sha256": self.settings.state_profile_sha256,
        }
        if any(getattr(selection, key) != value for key, value in expected.items()):
            raise NetworkExactToolSelectorError(
                "network Selector response identity mismatch"
            )
        if selection.eligible_labels != tuple(payload["eligible_labels"]):
            raise NetworkExactToolSelectorError(
                "network Selector response eligibility mismatch"
            )
        if parent is not None and selection.token_position <= parent.token_count:
            raise NetworkExactToolSelectorError(
                "network Selector state token position did not advance"
            )

    def _checkpoint(
        self,
        selection: NetworkExactToolSelection,
        selector_input: NetworkSelectorInput,
        parent: ModelCheckpoint | None,
    ) -> ModelCheckpoint:
        suffix = self.input_protocol.render_step(selector_input)
        transcript = (
            self.input_protocol.render_bootstrap(selector_input) + "\n" + suffix
            if parent is None
            else parent.transcript + "\n" + suffix
        )
        transcript_digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        if not math.isfinite(selection.confidence):
            raise NetworkExactToolSelectorError(
                "network Selector confidence is non-finite"
            )
        return ModelCheckpoint(
            checkpoint_id=selection.selector_checkpoint_id,
            lane_id=NETWORK_SELECTOR_LANE_ID,
            lane_kind=ModelLaneKind.SELECTOR,
            parent_checkpoint_id=(parent.checkpoint_id if parent is not None else None),
            model=self.settings.model,
            transport=(
                "native_rwkv_hidden_mlp_selector_"
                + (
                    "v7_requirement_byte_tail"
                    if self.settings.input_protocol.endswith(
                        "v7-requirement-byte-tail"
                    )
                    else "v6_current_question_last"
                    if self.settings.input_protocol.endswith("v6-current-question-last")
                    else "v5_full_request_last"
                    if self.settings.input_protocol.endswith("v5-full-request-last")
                    else "v4_request_last"
                    if self.settings.input_protocol.endswith("v4-request-last")
                    else "v3"
                )
            ),
            transcript=transcript,
            transcript_digest=transcript_digest,
            token_count=selection.token_position,
            event_ids=list(parent.event_ids) if parent is not None else [],
            native_state_ref=selection.selector_state_ref,
            native_state_digest=selection.selector_state_digest,
            native_state_export={
                "schema_version": "rwkv-lh.network-selector-state-ref.v1",
                "state_ref": selection.selector_state_ref,
                "state_digest": selection.selector_state_digest,
                "parent_state_digest": selection.selector_parent_state_digest,
                "token_position": selection.token_position,
            },
            native_state_metadata={
                **self.settings.runtime_identity(),
                "menu_digest": selection.menu_digest,
                "input_digest": selection.input_digest,
                "logits_sha256": selection.logits_sha256,
                "eligible_labels": list(selection.eligible_labels),
                "selection_rule": "eligible_raw_logit_argmax",
                "token_position": selection.token_position,
                "action_index": selector_input.progress.action_index,
                "completed_stage_count": (
                    selector_input.progress.completed_stage_count
                ),
                "generated_rwkv_text": False,
                "postprocessed": False,
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
