"""Versioned contracts for a real durable RWKV recurrent-state service."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.runtime.protocol import RuntimeCapabilities


NATIVE_STATE_PROTOCOL_VERSION = "rwkv-lh.native-state.v1"


@dataclass(frozen=True)
class NativeStateSnapshot:
    state_ref: str
    state_digest: str
    export_record: Mapping[str, Any]
    state_format_version: str
    server_build: str
    tokenizer_build: str
    protocol_version: str = NATIVE_STATE_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        required = {
            "state_ref": self.state_ref,
            "state_digest": self.state_digest,
            "state_format_version": self.state_format_version,
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
        }
        missing = [name for name, value in required.items() if not str(value).strip()]
        if missing:
            raise ValueError(f"native state snapshot is missing: {', '.join(missing)}")
        if self.protocol_version != NATIVE_STATE_PROTOCOL_VERSION:
            raise ValueError(
                f"unsupported native state protocol: {self.protocol_version}"
            )
        if not isinstance(self.export_record, Mapping) or not self.export_record:
            raise ValueError("native state snapshot requires a durable export record")


@dataclass(frozen=True)
class NativeStateCandidate:
    state_ref: str
    state_digest: str
    content: str
    finish_reason: str = "stop"
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.state_ref or not self.state_digest:
            raise ValueError("native candidate requires a state ref and digest")
        if not isinstance(self.content, str):
            raise TypeError("native candidate content must be a string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("native candidate metadata must be a mapping")
        token_ids = self.metadata.get("token_ids", ())
        if not isinstance(token_ids, (list, tuple)) or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0
            for item in token_ids
        ):
            raise ValueError("native candidate token_ids must be non-negative integers")


class NativeRWKVStateClient(Protocol):
    """Adapter boundary; implementations must preserve immutable fork lineage."""

    model_name: str

    def capabilities(self) -> RuntimeCapabilities: ...

    def state_create(
        self,
        *,
        lane_id: str,
        text: str,
    ) -> NativeStateSnapshot: ...

    def state_append(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
    ) -> NativeStateSnapshot: ...

    def state_fork(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
    ) -> NativeStateSnapshot: ...

    def state_generate(
        self,
        *,
        parent_state_ref: str,
        request_id: str,
        max_tokens: int,
        stop: Sequence[str],
        sampling: Mapping[str, Any],
    ) -> NativeStateCandidate: ...

    def state_commit(self, *, candidate_state_ref: str) -> NativeStateSnapshot: ...

    def state_rollback(
        self,
        *,
        candidate_state_ref: str,
        parent_state_ref: str,
    ) -> None: ...

    def state_import(self, *, export_record: Mapping[str, Any]) -> NativeStateSnapshot: ...


__all__ = [
    "NATIVE_STATE_PROTOCOL_VERSION",
    "NativeRWKVStateClient",
    "NativeStateCandidate",
    "NativeStateSnapshot",
]
