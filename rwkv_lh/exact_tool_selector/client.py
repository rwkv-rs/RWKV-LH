"""Fail-closed client for the independent stateful 2.9B Selector service."""

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

from rwkv_lh.exact_tool_selector.protocol import (
    ExactToolSelection,
    SelectorInput,
    canonical_digest,
)
from rwkv_lh.schema import (
    ModelCheckpoint,
    ModelCheckpointStatus,
    ModelLaneKind,
)

SELECTOR_SERVICE_REQUEST_SCHEMA = "rwkv-lh.exact-tool-selector-service-request.v1"
SELECTOR_SERVICE_RESPONSE_SCHEMA = "rwkv-lh.exact-tool-selector-service-response.v1"
SELECTOR_LANE_ID = "LANE:SELECTOR"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_PROFILE_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


class ExactToolSelectorError(RuntimeError):
    """The independent Selector service violated its frozen contract."""


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
class ExactToolSelectorSettings:
    base_url: str
    model: str
    model_sha256: str
    head_sha256: str
    state_profile_id: str
    state_profile_sha256: str
    connect_timeout_seconds: float = 10.0
    read_timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        parsed = urlparse(self.base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("RWKV_SELECTOR_BASE_URL must be absolute HTTP(S)")
        if not self.model.strip():
            raise ValueError("RWKV_SELECTOR_MODEL must be non-empty")
        for name, value in (
            ("RWKV_SELECTOR_MODEL_SHA256", self.model_sha256),
            ("RWKV_SELECTOR_HEAD_SHA256", self.head_sha256),
            ("RWKV_SELECTOR_STATE_PROFILE_SHA256", self.state_profile_sha256),
        ):
            if not _SHA256_PATTERN.fullmatch(value):
                raise ValueError(f"{name} must be lowercase SHA-256")
        if not _PROFILE_ID_PATTERN.fullmatch(self.state_profile_id):
            raise ValueError("RWKV_SELECTOR_STATE_PROFILE_ID is invalid")
        if self.connect_timeout_seconds <= 0 or self.read_timeout_seconds <= 0:
            raise ValueError("Selector timeouts must be positive")

    @classmethod
    def from_env(cls) -> ExactToolSelectorSettings | None:
        base_url = os.environ.get("RWKV_SELECTOR_BASE_URL", "").strip().rstrip("/")
        configured = {
            "model": os.environ.get("RWKV_SELECTOR_MODEL", "").strip(),
            "model_sha256": os.environ.get("RWKV_SELECTOR_MODEL_SHA256", "").strip(),
            "head_sha256": os.environ.get("RWKV_SELECTOR_HEAD_SHA256", "").strip(),
            "state_profile_id": os.environ.get(
                "RWKV_SELECTOR_STATE_PROFILE_ID", ""
            ).strip(),
            "state_profile_sha256": os.environ.get(
                "RWKV_SELECTOR_STATE_PROFILE_SHA256", ""
            ).strip(),
        }
        if not base_url and not any(configured.values()):
            return None
        if not base_url or any(not value for value in configured.values()):
            raise ValueError(
                "all RWKV_SELECTOR_* identity settings are required when enabled"
            )
        try:
            connect_timeout = float(
                os.environ.get("RWKV_SELECTOR_CONNECT_TIMEOUT", "10")
            )
            read_timeout = float(os.environ.get("RWKV_SELECTOR_READ_TIMEOUT", "120"))
        except ValueError as exc:
            raise ValueError("RWKV Selector timeouts must be numbers") from exc
        return cls(
            base_url=base_url,
            connect_timeout_seconds=connect_timeout,
            read_timeout_seconds=read_timeout,
            **configured,
        )


class ExactToolSelectorClient:
    """Append one causal step to a separate Selector state and classify it."""

    def __init__(
        self,
        settings: ExactToolSelectorSettings,
        *,
        session: _HTTPSession | None = None,
    ) -> None:
        self.settings = settings
        self._session = session or requests.Session()

    def _validate_parent(self, parent: ModelCheckpoint) -> None:
        if (
            parent.lane_id != SELECTOR_LANE_ID
            or parent.lane_kind is not ModelLaneKind.SELECTOR
            or parent.status is not ModelCheckpointStatus.COMMITTED
            or parent.model != self.settings.model
            or parent.state_profile_id != self.settings.state_profile_id
            or parent.state_profile_sha256 != self.settings.state_profile_sha256
            or not parent.native_state_ref
            or not parent.native_state_digest
        ):
            raise ExactToolSelectorError("Selector parent checkpoint identity mismatch")
        metadata = parent.native_state_metadata or {}
        if (
            metadata.get("model_sha256") != self.settings.model_sha256
            or metadata.get("head_sha256") != self.settings.head_sha256
        ):
            raise ExactToolSelectorError("Selector parent artifact identity mismatch")

    def _request_payload(
        self,
        selector_input: SelectorInput,
        *,
        run_id: str,
        trace_id: str,
        parent: ModelCheckpoint | None,
    ) -> dict[str, Any]:
        if not str(run_id).strip() or not str(trace_id).strip():
            raise ValueError("Selector request requires run_id and trace_id")
        parent_value: dict[str, Any] | None = None
        bootstrap = selector_input.render_bootstrap()
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
            "schema_version": SELECTOR_SERVICE_REQUEST_SCHEMA,
            "run_id": str(run_id),
            "trace_id": str(trace_id),
            "input_digest": canonical_digest(selector_input.to_dict()),
            "menu_digest": selector_input.menu_digest,
            "bootstrap": bootstrap,
            "step": selector_input.render_step(),
            "parent": parent_value,
            "expected_identity": {
                "model": self.settings.model,
                "model_sha256": self.settings.model_sha256,
                "head_sha256": self.settings.head_sha256,
                "profile_id": self.settings.state_profile_id,
                "profile_sha256": self.settings.state_profile_sha256,
            },
        }

    def select(
        self,
        selector_input: SelectorInput,
        *,
        run_id: str,
        parent: ModelCheckpoint | None = None,
        trace_id: str | None = None,
    ) -> tuple[ExactToolSelection, ModelCheckpoint]:
        selected_trace_id = str(trace_id or f"SELTRACE-{uuid4().hex[:16]}")
        payload = self._request_payload(
            selector_input,
            run_id=run_id,
            trace_id=selected_trace_id,
            parent=parent,
        )
        try:
            response = self._session.post(
                self.settings.base_url.rstrip("/") + "/v1/select",
                json=payload,
                timeout=(
                    self.settings.connect_timeout_seconds,
                    self.settings.read_timeout_seconds,
                ),
            )
        except requests.RequestException as exc:
            raise ExactToolSelectorError(
                f"Selector transport failed with unknown outcome: {type(exc).__name__}: {exc}"
            ) from exc
        if response.status_code != 200:
            raise ExactToolSelectorError(
                f"Selector HTTP {response.status_code}: {response.text[:1000]}"
            )
        try:
            value = json.loads(response.content.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ExactToolSelectorError(
                "Selector returned invalid UTF-8 JSON"
            ) from exc
        if not isinstance(value, Mapping):
            raise ExactToolSelectorError("Selector response must be a JSON object")
        if value.get("schema_version") != SELECTOR_SERVICE_RESPONSE_SCHEMA:
            raise ExactToolSelectorError("unsupported Selector service response schema")
        raw_selection = value.get("selection")
        if not isinstance(raw_selection, Mapping):
            raise ExactToolSelectorError("Selector response has no selection object")
        try:
            selection = ExactToolSelection.from_dict(raw_selection)
        except (TypeError, ValueError) as exc:
            raise ExactToolSelectorError(str(exc)) from exc
        self._validate_selection(selection, payload, parent)
        checkpoint = self._checkpoint(selection, selector_input, parent)
        return selection, checkpoint

    def _validate_selection(
        self,
        selection: ExactToolSelection,
        payload: Mapping[str, Any],
        parent: ModelCheckpoint | None,
    ) -> None:
        expected_parent_digest = (
            "" if parent is None else str(parent.native_state_digest)
        )
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
            raise ExactToolSelectorError("Selector response identity mismatch")
        if parent is not None and selection.token_position <= parent.token_count:
            raise ExactToolSelectorError(
                "Selector state token position did not advance"
            )

    def _checkpoint(
        self,
        selection: ExactToolSelection,
        selector_input: SelectorInput,
        parent: ModelCheckpoint | None,
    ) -> ModelCheckpoint:
        suffix = selector_input.render_step()
        transcript = (
            selector_input.render_bootstrap() + "\n" + suffix
            if parent is None
            else parent.transcript + "\n" + suffix
        )
        transcript_digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
        if not math.isfinite(selection.confidence):
            raise ExactToolSelectorError("Selector confidence is non-finite")
        return ModelCheckpoint(
            checkpoint_id=selection.selector_checkpoint_id,
            lane_id=SELECTOR_LANE_ID,
            lane_kind=ModelLaneKind.SELECTOR,
            parent_checkpoint_id=(parent.checkpoint_id if parent is not None else None),
            model=self.settings.model,
            transport="native_rwkv_selector",
            transcript=transcript,
            transcript_digest=transcript_digest,
            token_count=selection.token_position,
            event_ids=list(parent.event_ids) if parent is not None else [],
            native_state_ref=selection.selector_state_ref,
            native_state_digest=selection.selector_state_digest,
            native_state_export={
                "schema_version": "rwkv-lh.exact-tool-selector-state-ref.v1",
                "state_ref": selection.selector_state_ref,
                "state_digest": selection.selector_state_digest,
                "parent_state_digest": selection.selector_parent_state_digest,
                "token_position": selection.token_position,
            },
            native_state_metadata={
                "model_sha256": self.settings.model_sha256,
                "head_sha256": self.settings.head_sha256,
                "menu_digest": selection.menu_digest,
                "input_digest": selection.input_digest,
                "logits_sha256": selection.logits_sha256,
                "token_position": selection.token_position,
            },
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
            status=ModelCheckpointStatus.COMMITTED,
        )


__all__ = [
    "SELECTOR_LANE_ID",
    "SELECTOR_SERVICE_REQUEST_SCHEMA",
    "SELECTOR_SERVICE_RESPONSE_SCHEMA",
    "ExactToolSelectorClient",
    "ExactToolSelectorError",
    "ExactToolSelectorSettings",
]
