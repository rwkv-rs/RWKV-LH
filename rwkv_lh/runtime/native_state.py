"""Versioned contracts for a disposable RWKV recurrent-state cache service."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.runtime.protocol import RuntimeCapabilities


NATIVE_STATE_PROTOCOL_VERSION = "rwkv-lh.native-state.v1"


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


@dataclass(frozen=True)
class NativeStateCacheBinding:
    """Identity of one derived cache entry; it grants no execution authority."""

    lane_id: str
    lane_kind: str
    model: str
    model_sha256: str
    state_profile_id: str
    state_profile_sha256: str
    state_chain_digest: str
    delta_digest: str
    event_ids_digest: str
    parent_state_digest: str = ""
    cache_role: str = "disposable_acceleration"

    def __post_init__(self) -> None:
        if not self.lane_id or not self.lane_kind or not self.model:
            raise ValueError("native cache binding identity is incomplete")
        for name in (
            "state_chain_digest",
            "delta_digest",
            "event_ids_digest",
        ):
            value = str(getattr(self, name) or "")
            if len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
                raise ValueError(f"native cache binding {name} must be lowercase SHA-256")
        for name in (
            "model_sha256",
            "state_profile_sha256",
            "parent_state_digest",
        ):
            value = str(getattr(self, name) or "")
            if value and (
                len(value) != 64
                or any(item not in "0123456789abcdef" for item in value)
            ):
                raise ValueError(f"native cache binding {name} must be empty or SHA-256")
        if self.cache_role != "disposable_acceleration":
            raise ValueError("native state may only be registered as disposable cache")

    @property
    def digest(self) -> str:
        return _canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": "rwkv-lh.native-state-cache-binding.v1",
            "lane_id": self.lane_id,
            "lane_kind": self.lane_kind,
            "model": self.model,
            "model_sha256": self.model_sha256,
            "state_profile_id": self.state_profile_id,
            "state_profile_sha256": self.state_profile_sha256,
            "state_chain_digest": self.state_chain_digest,
            "delta_digest": self.delta_digest,
            "event_ids_digest": self.event_ids_digest,
            "parent_state_digest": self.parent_state_digest,
            "cache_role": self.cache_role,
            "authoritative": False,
        }

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "NativeStateCacheBinding":
        if value.get("schema_version") != "rwkv-lh.native-state-cache-binding.v1":
            raise ValueError("unsupported native state cache binding")
        if value.get("authoritative") is not False:
            raise ValueError("native state cache binding cannot be authoritative")
        return cls(
            lane_id=str(value.get("lane_id") or ""),
            lane_kind=str(value.get("lane_kind") or ""),
            model=str(value.get("model") or ""),
            model_sha256=str(value.get("model_sha256") or ""),
            state_profile_id=str(value.get("state_profile_id") or ""),
            state_profile_sha256=str(value.get("state_profile_sha256") or ""),
            state_chain_digest=str(value.get("state_chain_digest") or ""),
            delta_digest=str(value.get("delta_digest") or ""),
            event_ids_digest=str(value.get("event_ids_digest") or ""),
            parent_state_digest=str(value.get("parent_state_digest") or ""),
            cache_role=str(value.get("cache_role") or ""),
        )


@dataclass(frozen=True)
class NativeStateSnapshot:
    state_ref: str
    state_digest: str
    export_record: Mapping[str, Any]
    state_format_version: str
    server_build: str
    tokenizer_build: str
    cache_binding_digest: str
    protocol_version: str = NATIVE_STATE_PROTOCOL_VERSION

    def __post_init__(self) -> None:
        required = {
            "state_ref": self.state_ref,
            "state_digest": self.state_digest,
            "state_format_version": self.state_format_version,
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
            "cache_binding_digest": self.cache_binding_digest,
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
        for name in ("state_digest", "cache_binding_digest"):
            value = str(getattr(self, name) or "")
            if len(value) != 64 or any(
                item not in "0123456789abcdef" for item in value
            ):
                raise ValueError(f"native snapshot {name} must be lowercase SHA-256")


@dataclass(frozen=True)
class NativeStateCandidate:
    state_ref: str
    state_digest: str
    content: str
    finish_reason: str = "stop"
    metadata: Mapping[str, Any] = field(default_factory=dict)
    parent_state_digest: str = ""
    parent_cache_binding_digest: str = ""

    def __post_init__(self) -> None:
        if not self.state_ref or not self.state_digest:
            raise ValueError("native candidate requires a state ref and digest")
        if not isinstance(self.content, str):
            raise TypeError("native candidate content must be a string")
        if not isinstance(self.metadata, Mapping):
            raise TypeError("native candidate metadata must be a mapping")
        for name in (
            "state_digest",
            "parent_state_digest",
            "parent_cache_binding_digest",
        ):
            value = str(getattr(self, name) or "")
            if len(value) != 64 or any(item not in "0123456789abcdef" for item in value):
                raise ValueError(f"native candidate {name} must be lowercase SHA-256")
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
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot: ...

    def state_append(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot: ...

    def state_fork(
        self,
        *,
        parent_state_ref: str,
        lane_id: str,
        text: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot: ...

    def state_generate(
        self,
        *,
        parent_state_ref: str,
        request_id: str,
        max_tokens: int,
        stop: Sequence[str],
        sampling: Mapping[str, Any],
        parent_cache_binding_digest: str,
    ) -> NativeStateCandidate: ...

    def state_commit(
        self,
        *,
        candidate_state_ref: str,
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot: ...

    def state_rollback(
        self,
        *,
        candidate_state_ref: str,
        parent_state_ref: str,
    ) -> None: ...

    def state_import(
        self,
        *,
        export_record: Mapping[str, Any],
        cache_binding: NativeStateCacheBinding,
    ) -> NativeStateSnapshot: ...


__all__ = [
    "NATIVE_STATE_PROTOCOL_VERSION",
    "NativeStateCacheBinding",
    "NativeRWKVStateClient",
    "NativeStateCandidate",
    "NativeStateSnapshot",
]
