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
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL,
    network_selector_input_protocol,
)
from rwkv_lh.exact_tool_selector.head import (
    NETWORK_SELECTOR_FEATURE_PROTOCOLS,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkExactToolSelection,
    NetworkSelectorInput,
)
from rwkv_lh.runtime.protocol import RWKVRuntimeError
from rwkv_lh.runtime.role_config import role_env, role_float
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus, ModelLaneKind


NETWORK_SELECTOR_SERVICE_REQUEST_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-request.v3"
)
NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA = (
    "rwkv-lh.network-exact-tool-selector-service-response.v3"
)
NETWORK_SELECTOR_RUNTIME_INPUT_PROTOCOL = (
    CURRENT_G1J_NETWORK_SELECTOR_INPUT_PROTOCOL
)
NETWORK_SELECTOR_LANE_ID = "LANE:SELECTOR"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class NetworkExactToolSelectorError(RWKVRuntimeError):
    """The 25-class Selector service violated its frozen contract."""

    def __init__(
        self,
        message: str,
        *,
        cache_rebuild_allowed: bool = False,
    ) -> None:
        super().__init__(message)
        self.cache_rebuild_allowed = bool(cache_rebuild_allowed)


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
            "feature_protocol": (
                "FEATURE_PROTOCOL",
                "RWKV_SELECTOR_FEATURE_PROTOCOL",
            ),
            "state_profile_id": (
                "STATE_PROFILE_ID",
                "RWKV_SELECTOR_STATE_PROFILE_ID",
            ),
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
            env_name in os.environ and os.environ[env_name].strip()
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
            raise ValueError(
                "missing 25-class Selector identity settings: "
                + ", ".join(missing)
            )
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
            or metadata.get("cache_role") != "disposable_acceleration"
            or metadata.get("authoritative") is not False
            or metadata.get("delta_digest") != parent.transcript_digest
            or not _SHA256_PATTERN.fullmatch(
                str(metadata.get("state_chain_digest") or "")
            )
        ):
            raise NetworkExactToolSelectorError(
                "network Selector parent checkpoint identity mismatch",
                cache_rebuild_allowed=True,
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
            parent_cache_failure = (
                response.status_code == 400
                and "network Selector parent " in response.text
            )
            raise NetworkExactToolSelectorError(
                f"network Selector HTTP {response.status_code}: {response.text[:1000]}",
                cache_rebuild_allowed=parent_cache_failure,
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
        delta = (
            self.input_protocol.render_bootstrap(selector_input) + "\n" + suffix
            if parent is None
            else suffix
        )
        delta_digest = hashlib.sha256(delta.encode("utf-8")).hexdigest()
        parent_chain_digest = (
            str((parent.native_state_metadata or {}).get("state_chain_digest") or "")
            if parent is not None
            else ""
        )
        state_chain_digest = hashlib.sha256(
            json.dumps(
                {
                    "parent_state_chain_digest": parent_chain_digest,
                    "delta_digest": delta_digest,
                },
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
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
            transport="native_rwkv_hidden_mlp_selector_g1j_selector_intent_v1",
            # This is the bounded delta sent for this transition, not a replayable
            # semantic transcript.  The WKV tensor is disposable acceleration.
            transcript=delta,
            transcript_digest=delta_digest,
            token_count=selection.token_position,
            event_ids=list(parent.event_ids) if parent is not None else [],
            native_state_ref=selection.selector_state_ref,
            native_state_digest=selection.selector_state_digest,
            native_state_export={
                "schema_version": "rwkv-lh.network-selector-state-ref.v1",
                "state_ref": selection.selector_state_ref,
                "state_digest": selection.selector_state_digest,
                "parent_state_digest": selection.selector_parent_state_digest,
                "state_chain_digest": state_chain_digest,
                "delta_digest": delta_digest,
                "cache_role": "disposable_acceleration",
                "authoritative": False,
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
                "protocol_rejection_count": (
                    selector_input.progress.protocol_rejection_count
                    + int(
                        (parent.native_state_metadata or {}).get(
                            "protocol_rejection_count",
                            0,
                        )
                        if parent is not None
                        else 0
                    )
                ),
                "generated_rwkv_text": False,
                "postprocessed": False,
                "cache_role": "disposable_acceleration",
                "authoritative": False,
                "parent_state_digest": selection.selector_parent_state_digest,
                "parent_state_chain_digest": parent_chain_digest,
                "state_chain_digest": state_chain_digest,
                "delta_digest": delta_digest,
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
