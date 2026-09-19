# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
import hashlib
import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import torch
import torch.nn as nn
from vllm import envs
from vllm.config import VllmConfig
from vllm.config.compilation import CUDAGraphMode
from vllm.logger import init_logger
from vllm.tasks import GenerationTask
from vllm.v1.core.sched.output import NewRequestData
from vllm.v1.kv_cache_interface import KVCacheConfig
from vllm.v1.worker.gpu.input_batch import InputBatch
from vllm.v1.worker.gpu.mm.encoder_cache import EncoderCache
from vllm.v1.worker.gpu.model_states.interface import ModelState
from vllm.v1.worker.gpu.states import RequestState
from vllm.v1.worker.utils import AttentionGroup
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION
from rwkv_lh.inference.vllm_rwkv_state_profiles_v1 import (
    RWKV7InitialStateProfile,
    RWKV7InitialStateProfiles,
    RWKV7_ZERO_STATE_PROFILE,
    resolve_request_profile,
    sha256_file,
)

logger = init_logger(__name__)

DEFAULT_RWKV7_PREFIX_CACHE_CAPACITY = 8
RWKV7_NATIVE_STATE_FORMAT = "rwkv7-native-state-cache.v1"
RWKV7_NATIVE_EXECUTION_IDENTITY_VERSION = "rwkv7-native-export-execution.v2"
RWKV7_NATIVE_STATE_READ_REF_XARG = "rwkv_native_state_read_ref"
RWKV7_NATIVE_STATE_READ_DIGEST_XARG = "rwkv_native_state_read_digest"
RWKV7_NATIVE_STATE_READ_BINDING_XARG = "rwkv_native_state_read_binding_digest"
RWKV7_NATIVE_STATE_WRITE_REF_XARG = "rwkv_native_state_write_ref"
RWKV7_NATIVE_STATE_WRITE_DIGEST_XARG = "rwkv_native_state_write_digest"
RWKV7_NATIVE_STATE_WRITE_BINDING_XARG = "rwkv_native_state_write_binding_digest"
RWKV7_NATIVE_STATE_WRITE_PENDING_XARG = "rwkv_native_state_write_pending_token_id"
_SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")
_NATIVE_STATE_REF_PATTERN = re.compile(r"^WKV-[0-9a-f]{32}$")


@dataclass(frozen=True)
class RWKV7PrefixStateIdentity:
    """Compatibility identity for one recurrent prefix state."""

    token_ids: tuple[int, ...]
    model_artifact: str
    model_revision: str
    backend_provider: str
    backend_revision: str
    wkv_mode: str
    gemm_policy: str
    state_profile_id: str
    state_profile_sha256: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "token_ids", tuple(self.token_ids))
        if not self.token_ids:
            raise ValueError("RWKV7 prefix identity requires at least one token")
        if any(token_id < 0 for token_id in self.token_ids):
            raise ValueError("RWKV7 prefix token ids must be non-negative")
        for field_name in (
            "model_artifact",
            "model_revision",
            "backend_provider",
            "backend_revision",
            "wkv_mode",
            "gemm_policy",
            "state_profile_id",
            "state_profile_sha256",
        ):
            if not getattr(self, field_name):
                raise ValueError(f"RWKV7 prefix identity requires {field_name}")


@dataclass(frozen=True)
class RWKV7PrefixStateSnapshot:
    """A request-independent copy of all state needed to resume a prefix."""

    shift_state: torch.Tensor
    wkv_state: torch.Tensor
    elapsed: int

    def clone(self) -> "RWKV7PrefixStateSnapshot":
        return RWKV7PrefixStateSnapshot(
            shift_state=self.shift_state.clone(),
            wkv_state=self.wkv_state.clone(),
            elapsed=self.elapsed,
        )

    def is_identical(self, other: "RWKV7PrefixStateSnapshot") -> bool:
        return (
            self.elapsed == other.elapsed
            and self.shift_state.dtype == other.shift_state.dtype
            and self.shift_state.device == other.shift_state.device
            and torch.equal(self.shift_state, other.shift_state)
            and self.wkv_state.dtype == other.wkv_state.dtype
            and self.wkv_state.device == other.wkv_state.device
            and torch.equal(self.wkv_state, other.wkv_state)
        )


class RWKV7PrefixStateCache:
    """Bounded LRU cache for recurrent state owned by the RWKV model state.

    Capacity is measured in snapshots. Stored values and cache hits are cloned,
    so a resumed request cannot mutate the cached state.
    """

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("RWKV7 prefix cache capacity must be positive")
        self.capacity = capacity
        self._entries: OrderedDict[
            RWKV7PrefixStateIdentity, RWKV7PrefixStateSnapshot
        ] = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def get(
        self, identity: RWKV7PrefixStateIdentity
    ) -> RWKV7PrefixStateSnapshot | None:
        snapshot = self._entries.get(identity)
        if snapshot is not None:
            self._entries.move_to_end(identity)
            return snapshot.clone()
        self._reject_stale_identity(identity)
        return None

    def get_longest_prefix(
        self,
        identity: RWKV7PrefixStateIdentity,
        *,
        max_prefix_length: int,
    ) -> tuple[int, RWKV7PrefixStateSnapshot] | None:
        if max_prefix_length <= 0:
            return None

        best: RWKV7PrefixStateIdentity | None = None
        for cached in self._entries:
            prefix_length = len(cached.token_ids)
            if (
                prefix_length > max_prefix_length
                or identity.token_ids[:prefix_length] != cached.token_ids
            ):
                continue
            if cached.model_artifact != identity.model_artifact:
                continue
            if cached.state_profile_id != identity.state_profile_id:
                continue
            if cached.state_profile_sha256 != identity.state_profile_sha256:
                raise ValueError("RWKV7 prefix state has a stale state profile")
            if cached.model_revision != identity.model_revision:
                raise ValueError("RWKV7 prefix state has a stale model revision")
            if (
                cached.backend_provider != identity.backend_provider
                or cached.backend_revision != identity.backend_revision
                or cached.wkv_mode != identity.wkv_mode
                or cached.gemm_policy != identity.gemm_policy
            ):
                raise ValueError("RWKV7 prefix state has a stale backend configuration")
            if best is None or prefix_length > len(best.token_ids):
                best = cached

        if best is None:
            return None
        snapshot = self._entries[best]
        self._entries.move_to_end(best)
        return len(best.token_ids), snapshot.clone()

    def put(
        self,
        identity: RWKV7PrefixStateIdentity,
        snapshot: RWKV7PrefixStateSnapshot,
    ) -> None:
        existing = self._entries.get(identity)
        if existing is not None:
            if not existing.is_identical(snapshot):
                raise ValueError("RWKV7 prefix identity maps to conflicting state")
            self._entries.move_to_end(identity)
            return
        self._reject_stale_identity(identity)
        self._entries[identity] = snapshot.clone()
        if len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def _reject_stale_identity(self, identity: RWKV7PrefixStateIdentity) -> None:
        for cached in self._entries:
            if (
                cached.token_ids != identity.token_ids
                or cached.model_artifact != identity.model_artifact
                or cached.state_profile_id != identity.state_profile_id
            ):
                continue
            if cached.state_profile_sha256 != identity.state_profile_sha256:
                raise ValueError("RWKV7 prefix state has a stale state profile")
            if cached.model_revision != identity.model_revision:
                raise ValueError("RWKV7 prefix state has a stale model revision")
            raise ValueError("RWKV7 prefix state has a stale backend configuration")


@dataclass(frozen=True)
class RWKV7NativeStateEntry:
    """One non-authoritative recurrent cache entry."""

    state_ref: str
    state_digest: str
    cache_binding_digest: str
    state_profile_id: str
    state_profile_sha256: str
    pending_token_id: int
    snapshot: RWKV7PrefixStateSnapshot

    def __post_init__(self) -> None:
        if not _NATIVE_STATE_REF_PATTERN.fullmatch(self.state_ref):
            raise ValueError("RWKV7 native state ref is invalid")
        for name in (
            "state_digest",
            "cache_binding_digest",
            "state_profile_sha256",
        ):
            value = getattr(self, name)
            if not _SHA256_PATTERN.fullmatch(value):
                raise ValueError(f"RWKV7 native state {name} must be SHA-256")
        if not self.state_profile_id:
            raise ValueError("RWKV7 native state profile ID is required")
        if self.pending_token_id < 0:
            raise ValueError("RWKV7 native pending token must be non-negative")

    def clone(self, **changes: Any) -> "RWKV7NativeStateEntry":
        values = {
            "state_ref": self.state_ref,
            "state_digest": self.state_digest,
            "cache_binding_digest": self.cache_binding_digest,
            "state_profile_id": self.state_profile_id,
            "state_profile_sha256": self.state_profile_sha256,
            "pending_token_id": self.pending_token_id,
            "snapshot": self.snapshot.clone(),
        }
        values.update(changes)
        return RWKV7NativeStateEntry(**values)

    def metadata(self) -> dict[str, Any]:
        return {
            "state_ref": self.state_ref,
            "state_digest": self.state_digest,
            "cache_binding_digest": self.cache_binding_digest,
            "state_profile_id": self.state_profile_id,
            "state_profile_sha256": self.state_profile_sha256,
            "pending_token_id": self.pending_token_id,
            "processed_token_count": self.snapshot.elapsed,
            "state_format_version": RWKV7_NATIVE_STATE_FORMAT,
            "authoritative": False,
        }


class RWKV7NativeStateCache:
    """Bounded copy-on-read LRU for transactional recurrent snapshots."""

    def __init__(self, capacity: int) -> None:
        if capacity <= 0:
            raise ValueError("RWKV7 native state cache capacity must be positive")
        self.capacity = capacity
        self._entries: OrderedDict[str, RWKV7NativeStateEntry] = OrderedDict()

    def __len__(self) -> int:
        return len(self._entries)

    def clear(self) -> None:
        self._entries.clear()

    def contains(self, state_ref: str) -> bool:
        return state_ref in self._entries

    def get(
        self,
        state_ref: str,
        *,
        state_digest: str | None = None,
        cache_binding_digest: str | None = None,
    ) -> RWKV7NativeStateEntry:
        entry = self._entries.get(state_ref)
        if entry is None:
            raise KeyError(f"Unknown RWKV7 native state {state_ref!r}")
        if state_digest is not None and entry.state_digest != state_digest:
            raise ValueError("RWKV7 native state digest mismatch")
        if (
            cache_binding_digest is not None
            and entry.cache_binding_digest != cache_binding_digest
        ):
            raise ValueError("RWKV7 native state cache binding mismatch")
        self._entries.move_to_end(state_ref)
        return entry.clone()

    def put(self, entry: RWKV7NativeStateEntry, *, replace: bool = False) -> None:
        existing = self._entries.get(entry.state_ref)
        if existing is not None and not replace:
            raise ValueError(f"RWKV7 native state {entry.state_ref!r} already exists")
        self._entries[entry.state_ref] = entry.clone()
        self._entries.move_to_end(entry.state_ref)
        while len(self._entries) > self.capacity:
            self._entries.popitem(last=False)

    def drop(self, state_ref: str) -> bool:
        return self._entries.pop(state_ref, None) is not None


@dataclass(frozen=True)
class _RWKV7NativeStateWrite:
    state_ref: str
    state_digest: str
    cache_binding_digest: str
    state_profile_id: str
    state_profile_sha256: str
    pending_token_id: int | None


class RWKV7ModelState(ModelState):
    """Dense batched recurrent state for RWKV7."""

    def __init__(
        self,
        vllm_config: VllmConfig,
        model: nn.Module,
        encoder_cache: EncoderCache | None,
        device: torch.device,
    ) -> None:
        self.vllm_config = vllm_config
        self.model_config = vllm_config.model_config
        self.scheduler_config = vllm_config.scheduler_config
        self.model = model
        self.device = device
        self.max_num_reqs = self.scheduler_config.max_num_seqs

        cfg = self.model_config.hf_config
        total_num_layers = int(
            getattr(cfg, "num_hidden_layers", getattr(cfg, "n_layer", 0))
        )
        self.layer_offset = int(getattr(model, "start_layer", 0))
        self.num_layers = (
            int(getattr(model, "end_layer", total_num_layers)) - self.layer_offset
        )
        self.hidden_size = int(cfg.hidden_size)
        self.head_size = int(getattr(cfg, "head_size", 64))
        total_num_heads = int(
            getattr(
                cfg,
                "num_attention_heads",
                self.hidden_size // self.head_size,
            )
        )
        self.num_heads = int(getattr(model, "tp_num_heads", total_num_heads))
        wkv_dtype = getattr(model, "wkv_state_dtype", None)
        if wkv_dtype is None:
            wkv_dtype = (
                torch.float32
                if getattr(model, "wkv_mode", "fp16") == "fp32io16"
                else torch.float16
            )

        self.shift_state = torch.zeros(
            (self.num_layers, 2, self.max_num_reqs, self.hidden_size),
            dtype=torch.float16,
            device=device,
        )
        self.wkv_state = torch.zeros(
            (
                self.num_layers,
                self.max_num_reqs,
                self.num_heads,
                self.head_size,
                self.head_size,
            ),
            dtype=wkv_dtype,
            device=device,
        )
        self.elapsed = torch.zeros(
            (self.max_num_reqs,), dtype=torch.int32, device=device
        )
        self.execution_idx_mapping = torch.arange(
            self.max_num_reqs, dtype=torch.int32, device=device
        )
        self.decode_query_start_loc = torch.arange(
            self.max_num_reqs + 1, dtype=torch.int32, device=device
        )
        self.decode_slot_indices = torch.empty(
            (self.max_num_reqs,), dtype=torch.int32, device=device
        )
        self.decode_token_positions = torch.empty(
            (self.max_num_reqs,), dtype=torch.long, device=device
        )
        # Maps request ids to stable RWKV state slots. A vLLM request index can
        # change after request metadata is condensed, but this slot must not.
        self.req_id_to_index: dict[str, int] = {}
        self.req_slot_owners: list[str | None] = [None] * self.max_num_reqs
        self.req_slot_to_row = [-1] * self.max_num_reqs
        self.row_to_req_slot = [-1] * self.max_num_reqs
        self.free_rows = set(range(self.max_num_reqs))
        self.decode_req_slots: set[int] = set()
        self._prefill_req_slots: list[int] = []
        self._prefill_becomes_decode: list[bool] = []
        self._prefill_cache_targets: list[int] = []
        self.req_prompt_token_ids: dict[str, tuple[int, ...]] = {}
        self.req_prefix_cache_hit_lengths: dict[str, int] = {}
        self.prefix_cache_eligible_req_ids: set[str] = set()
        self.req_state_profile_ids: dict[str, str] = {}
        self.req_native_state_writes: dict[str, _RWKV7NativeStateWrite] = {}
        self.staged_native_state_snapshots: OrderedDict[
            str, tuple[_RWKV7NativeStateWrite, RWKV7PrefixStateSnapshot]
        ] = OrderedDict()
        # A terminal scheduler cleanup can precede the serving process's
        # capture RPC.  Such rows are cached immediately with a provisional
        # pending token and finalized by that RPC before the state ref is
        # returned to callers.
        self.pending_sampled_native_state_refs: set[str] = set()

        self.native_state_cache = (
            RWKV7NativeStateCache(envs.VLLM_RWKV7_NATIVE_STATE_CACHE_CAPACITY)
            if envs.VLLM_RWKV7_NATIVE_STATE_ENABLED
            else None
        )
        self._initialize_native_source_identity()

        cache_config = getattr(vllm_config, "cache_config", None)
        prefix_cache_enabled = bool(
            cache_config is not None
            and getattr(cache_config, "rwkv_recurrent_prefix_caching", False)
        )
        self.prefix_state_cache = (
            RWKV7PrefixStateCache(capacity=DEFAULT_RWKV7_PREFIX_CACHE_CAPACITY)
            if prefix_cache_enabled
            else None
        )
        self._prefix_identity_fields = self._build_prefix_identity_fields()
        manifest_path = envs.VLLM_RWKV7_STATE_PROFILE_MANIFEST
        manifest_sha256 = envs.VLLM_RWKV7_STATE_PROFILE_MANIFEST_SHA256
        if manifest_path is None:
            if manifest_sha256 is not None:
                raise ValueError(
                    "RWKV7 state-profile manifest SHA-256 requires a manifest"
                )
            self.initial_state_profiles = RWKV7InitialStateProfiles.zero_only()
        else:
            tp_size = int(getattr(self.model, "tp_size", 1))
            tp_rank = int(getattr(self.model, "tp_rank", 0))
            self.initial_state_profiles = RWKV7InitialStateProfiles.load(
                manifest_path,
                manifest_sha256,
                model_artifact=self._prefix_identity_fields["model_artifact"],
                model_revision=self._prefix_identity_fields["model_revision"],
                total_num_layers=total_num_layers,
                total_num_heads=total_num_heads,
                layer_offset=self.layer_offset,
                num_layers=self.num_layers,
                tp_size=tp_size,
                tp_rank=tp_rank,
                num_heads=self.num_heads,
                head_size=self.head_size,
                device=self.device,
                dtype=self.wkv_state.dtype,
            )

    def _initialize_native_source_identity(self) -> None:
        self._native_source_identity: dict[str, Any] = {}
        if self.native_state_cache is not None:
            import vllm
            from rwkv_lh.inference.native_source_identity import (
                verify_native_source_identity,
            )
            self._native_source_identity = verify_native_source_identity(
                engine_file=getattr(vllm, "__file__", None), project_file=__file__,
            )

    def _reset_mappings(self) -> None:
        self.req_slot_owners = [None] * self.max_num_reqs
        self.req_slot_to_row = [-1] * self.max_num_reqs
        self.row_to_req_slot = [-1] * self.max_num_reqs
        self.free_rows = set(range(self.max_num_reqs))
        self.decode_req_slots = set()
        self._prefill_req_slots = []
        self._prefill_becomes_decode = []
        self._prefill_cache_targets = []
        self.req_prompt_token_ids.clear()
        self.req_prefix_cache_hit_lengths.clear()
        self.prefix_cache_eligible_req_ids.clear()
        self.req_state_profile_ids.clear()
        self.req_native_state_writes.clear()

    def _build_prefix_identity_fields(self) -> dict[str, str]:
        """Return content-addressed runtime identity fields for state isolation."""
        cfg = self.model_config.hf_config
        model_artifact = str(
            getattr(self.model_config, "model", None)
            or getattr(cfg, "name_or_path", None)
            or getattr(cfg, "_name_or_path", None)
            or type(self.model).__qualname__
        )
        model_artifact_path = Path(model_artifact).expanduser()
        if model_artifact_path.is_file():
            model_revision = sha256_file(model_artifact_path.resolve())
        else:
            model_revision = str(
                getattr(self.model_config, "revision", None)
                or getattr(cfg, "_commit_hash", None)
                or getattr(cfg, "rwkv_model_revision", None)
                or "runtime"
            )
        backend_provider = str(
            getattr(self.model, "rwkv_backend_provider", None) or "vllm-rwkv-native"
        )
        backend_revision = str(
            getattr(self.model, "rwkv_backend_revision", None)
            or getattr(cfg, "rwkv_backend_revision", None)
            or f"{type(self.model).__module__}.{type(self.model).__qualname__}"
        )
        wkv_mode = str(getattr(self.model, "wkv_mode", "fp16"))
        execution_profile = getattr(self.model, "execution_profile", None)
        gemm_policy = str(
            getattr(execution_profile, "gemm_accumulation_policy", None)
            or (
                "fp16"
                if getattr(self.model, "allow_fp16_accumulation", False)
                else "fp32"
            )
        )
        return {
            "model_artifact": model_artifact,
            "model_revision": model_revision,
            "backend_provider": backend_provider,
            "backend_revision": backend_revision,
            "wkv_mode": wkv_mode,
            "gemm_policy": gemm_policy,
        }

    def _prefix_identity(
        self,
        token_ids: tuple[int, ...],
        profile: RWKV7InitialStateProfile,
    ) -> RWKV7PrefixStateIdentity:
        return RWKV7PrefixStateIdentity(
            token_ids=token_ids,
            state_profile_id=profile.profile_id,
            state_profile_sha256=profile.state_sha256,
            **self._prefix_identity_fields,
        )

    def _restore_row(
        self,
        row: int,
        snapshot: RWKV7PrefixStateSnapshot,
    ) -> None:
        shift_row = self.shift_state[:, :, row]
        wkv_row = self.wkv_state[:, row]
        if (
            snapshot.shift_state.shape != shift_row.shape
            or snapshot.shift_state.dtype != shift_row.dtype
            or snapshot.shift_state.device != shift_row.device
            or snapshot.wkv_state.shape != wkv_row.shape
            or snapshot.wkv_state.dtype != wkv_row.dtype
            or snapshot.wkv_state.device != wkv_row.device
            or snapshot.elapsed < 0
        ):
            raise ValueError("RWKV7 cached prefix state is incompatible with runtime")
        shift_row.copy_(snapshot.shift_state)
        wkv_row.copy_(snapshot.wkv_state)
        self.elapsed[row].fill_(snapshot.elapsed)

    def _snapshot_row(self, row: int) -> RWKV7PrefixStateSnapshot:
        return RWKV7PrefixStateSnapshot(
            shift_state=self.shift_state[:, :, row].clone(),
            wkv_state=self.wkv_state[:, row].clone(),
            elapsed=int(self.elapsed[row].item()),
        )

    def _require_native_cache(self) -> RWKV7NativeStateCache:
        if self.native_state_cache is None:
            raise NotImplementedError("RWKV7 native state cache is disabled")
        return self.native_state_cache

    def native_state_capabilities(self) -> dict[str, Any]:
        cache = self._require_native_cache()
        return {
            "state_format_version": RWKV7_NATIVE_STATE_FORMAT,
            "cache_capacity": cache.capacity,
            "store_configured": bool(envs.VLLM_RWKV7_NATIVE_STATE_DIR),
            "store_persistent": envs.VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY == 0,
            "state_lifecycle_protocol": NATIVE_STATE_LIFECYCLE_VERSION,
            "model_identity": dict(self._prefix_identity_fields),
            "source_identity": dict(self._native_source_identity),
            "authoritative": False,
        }

    def seed_native_state(
        self,
        *,
        state_ref: str,
        state_digest: str,
        cache_binding_digest: str,
        state_profile_id: str,
        state_profile_sha256: str,
        pending_token_id: int,
    ) -> dict[str, Any]:
        cache = self._require_native_cache()
        profile = self.initial_state_profiles.resolve(state_profile_id)
        if profile.state_sha256 != state_profile_sha256:
            raise ValueError("RWKV7 native seed state-profile SHA-256 mismatch")
        shift_state = torch.zeros_like(self.shift_state[:, :, 0])
        wkv_state = torch.zeros_like(self.wkv_state[:, 0])
        if profile.wkv_state is not None:
            wkv_state.copy_(profile.wkv_state)
        entry = RWKV7NativeStateEntry(
            state_ref=state_ref,
            state_digest=state_digest,
            cache_binding_digest=cache_binding_digest,
            state_profile_id=profile.profile_id,
            state_profile_sha256=profile.state_sha256,
            pending_token_id=pending_token_id,
            snapshot=RWKV7PrefixStateSnapshot(
                shift_state=shift_state,
                wkv_state=wkv_state,
                elapsed=0,
            ),
        )
        cache.put(entry)
        return entry.metadata()

    def clone_native_state(
        self,
        *,
        source_ref: str,
        source_digest: str,
        source_cache_binding_digest: str,
        target_ref: str,
        target_digest: str,
        target_cache_binding_digest: str,
    ) -> dict[str, Any]:
        cache = self._require_native_cache()
        source = cache.get(
            source_ref,
            state_digest=source_digest,
            cache_binding_digest=source_cache_binding_digest,
        )
        target = source.clone(
            state_ref=target_ref,
            state_digest=target_digest,
            cache_binding_digest=target_cache_binding_digest,
        )
        cache.put(target)
        return target.metadata()

    def get_native_state(self, state_ref: str) -> dict[str, Any]:
        return self._require_native_cache().get(state_ref).metadata()

    def drop_native_state(self, state_ref: str) -> dict[str, Any]:
        dropped = self._require_native_cache().drop(state_ref)
        self.staged_native_state_snapshots.pop(state_ref, None)
        self.pending_sampled_native_state_refs.discard(state_ref)
        return {"state_ref": state_ref, "dropped": dropped}

    def rebind_native_state(
        self,
        *,
        state_ref: str,
        state_digest: str,
        old_cache_binding_digest: str,
        new_cache_binding_digest: str,
    ) -> dict[str, Any]:
        cache = self._require_native_cache()
        entry = cache.get(
            state_ref,
            state_digest=state_digest,
            cache_binding_digest=old_cache_binding_digest,
        ).clone(cache_binding_digest=new_cache_binding_digest)
        cache.put(entry, replace=True)
        return entry.metadata()

    def capture_native_request(
        self,
        request_id: str,
        sampled_token_id: int,
    ) -> dict[str, Any]:
        write = self.req_native_state_writes.get(request_id)
        if write is None:
            raise KeyError(f"RWKV7 native request {request_id!r} is not active")
        req_slot = self.req_id_to_index.get(request_id)
        if req_slot is None:
            raise KeyError(f"RWKV7 native request {request_id!r} has no state row")
        row = self.req_slot_to_row[req_slot]
        if row < 0:
            raise RuntimeError("RWKV7 native request state row is missing")
        return self._finalize_native_snapshot(
            write,
            self._snapshot_row(row),
            sampled_token_id,
        )

    def finalize_staged_native_state(
        self,
        state_ref: str,
        sampled_token_id: int,
    ) -> dict[str, Any]:
        cache = self._require_native_cache()
        if cache.contains(state_ref):
            entry = cache.get(state_ref)
            if state_ref in self.pending_sampled_native_state_refs:
                entry = entry.clone(pending_token_id=sampled_token_id)
                cache.put(entry, replace=True)
                self.pending_sampled_native_state_refs.discard(state_ref)
            return entry.metadata()
        staged = self.staged_native_state_snapshots.pop(state_ref, None)
        if staged is None:
            raise KeyError(f"RWKV7 native state {state_ref!r} was not captured")
        write, snapshot = staged
        return self._finalize_native_snapshot(write, snapshot, sampled_token_id)

    def _finalize_native_snapshot(
        self,
        write: _RWKV7NativeStateWrite,
        snapshot: RWKV7PrefixStateSnapshot,
        sampled_token_id: int,
    ) -> dict[str, Any]:
        pending_token_id = (
            write.pending_token_id
            if write.pending_token_id is not None
            else sampled_token_id
        )
        entry = RWKV7NativeStateEntry(
            state_ref=write.state_ref,
            state_digest=write.state_digest,
            cache_binding_digest=write.cache_binding_digest,
            state_profile_id=write.state_profile_id,
            state_profile_sha256=write.state_profile_sha256,
            pending_token_id=pending_token_id,
            snapshot=snapshot,
        )
        cache = self._require_native_cache()
        if cache.contains(write.state_ref):
            existing = cache.get(write.state_ref)
            if existing.metadata() != entry.metadata():
                raise ValueError("RWKV7 native state ref has conflicting metadata")
            return existing.metadata()
        cache.put(entry)
        self.staged_native_state_snapshots.pop(write.state_ref, None)
        self.pending_sampled_native_state_refs.discard(write.state_ref)
        return entry.metadata()

    def _sync_native_directory(self, path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _ensure_native_store_directory(self, path: Path) -> None:
        missing = []
        ancestor = path
        while not ancestor.exists():
            missing.append(ancestor)
            ancestor = ancestor.parent
        path.mkdir(mode=0o700, parents=True, exist_ok=True)
        # Each newly created directory entry must reach stable storage too.
        for created in missing:
            self._sync_native_directory(created.parent)

    def _native_store_path(self, store_key: str, worker_rank: int) -> Path:
        if not _SHA256_PATTERN.fullmatch(store_key):
            raise ValueError("RWKV7 native state store key must be SHA-256")
        root_value = envs.VLLM_RWKV7_NATIVE_STATE_DIR
        if not root_value:
            raise NotImplementedError("RWKV7 native state store is not configured")
        root = Path(root_value).resolve()
        rank_dir = root / f"rank-{worker_rank}"
        self._ensure_native_store_directory(rank_dir)
        return rank_dir / f"{store_key}.pt"

    def export_native_state(
        self,
        *,
        state_ref: str,
        store_key: str,
        worker_rank: int,
    ) -> dict[str, Any]:
        entry = self._require_native_cache().get(state_ref)
        path = self._native_store_path(store_key, worker_rank)
        payload = {
            "schema_version": RWKV7_NATIVE_STATE_FORMAT,
            "execution_identity": self._native_execution_identity(),
            **entry.metadata(),
            "shift_state": entry.snapshot.shift_state.detach().cpu(),
            "wkv_state": entry.snapshot.wkv_state.detach().cpu(),
        }
        temporary = path.with_suffix(f".tmp-{os.getpid()}")
        created = False
        try:
            with temporary.open("xb") as handle:
                created = True
                torch.save(payload, handle)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        except BaseException:
            # Remove only the private file created by this attempt. Never
            # replace the original storage failure with a cleanup exception.
            if created:
                try:
                    temporary.unlink(missing_ok=True)
                except OSError:
                    pass
            raise
        # The service may only journal a successful receipt after both the
        # complete State bytes and the published filename are durable.
        self._sync_native_directory(path.parent)
        self._trim_native_store(path.parent)
        return {**entry.metadata(), "store_key": store_key, "worker_rank": worker_rank}

    def _native_execution_identity(self) -> dict[str, Any]:
        return {
            "schema_version": RWKV7_NATIVE_EXECUTION_IDENTITY_VERSION,
            "model_identity": dict(self._prefix_identity_fields),
            "shift_state_dtype": str(self.shift_state.dtype),
            "wkv_state_dtype": str(self.wkv_state.dtype),
            "allow_fp16_accumulation": self.model.allow_fp16_accumulation,
            "source_identity": dict(self._native_source_identity),
        }

    def delete_native_state_export(self, *, store_key: str, worker_rank: int) -> dict[str, Any]:
        """Only the API's durable, reference-checked GC may call this action."""
        if isinstance(worker_rank, bool) or not isinstance(worker_rank, int) or worker_rank < 0:
            raise ValueError("invalid Native State worker rank")
        path = self._native_store_path(store_key, worker_rank)
        # Do not follow a substituted entry or accept a directory as a blob.
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError("invalid Native State store entry for deletion")
        path.unlink(missing_ok=True)
        # Also fsync when absent: a retry after unlink-before-fsync must finish
        # the original durable deletion, never just acknowledge an absent name.
        self._sync_native_directory(path.parent)
        return {"store_key": store_key, "worker_rank": worker_rank, "deleted": True}

    def import_native_state(
        self,
        *,
        state_ref: str,
        state_digest: str,
        cache_binding_digest: str,
        state_profile_id: str,
        state_profile_sha256: str,
        pending_token_id: int,
        processed_token_count: int,
        store_key: str,
        worker_rank: int,
    ) -> dict[str, Any]:
        path = self._native_store_path(store_key, worker_rank)
        if not path.is_file():
            raise KeyError(f"RWKV7 native state store entry {store_key!r} is absent")
        payload = torch.load(path, map_location="cpu", weights_only=True)
        if not isinstance(payload, dict):
            raise ValueError("RWKV7 native state store entry is invalid")
        if payload.get("execution_identity") != self._native_execution_identity():
            raise ValueError("RWKV7 native state store execution identity mismatch")
        expected = {
            "schema_version": RWKV7_NATIVE_STATE_FORMAT,
            "state_digest": state_digest,
            "cache_binding_digest": cache_binding_digest,
            "state_profile_id": state_profile_id,
            "state_profile_sha256": state_profile_sha256,
            "pending_token_id": pending_token_id,
            "processed_token_count": processed_token_count,
            "authoritative": False,
        }
        for name, value in expected.items():
            if payload.get(name) != value:
                raise ValueError(f"RWKV7 native state store {name} mismatch")
        shift_state = payload.get("shift_state")
        wkv_state = payload.get("wkv_state")
        if not isinstance(shift_state, torch.Tensor) or not isinstance(
            wkv_state, torch.Tensor
        ):
            raise ValueError("RWKV7 native state store tensors are invalid")
        if (shift_state.dtype != self.shift_state.dtype
                or wkv_state.dtype != self.wkv_state.dtype):
            raise ValueError("RWKV7 native state store tensor dtype mismatch")
        snapshot = RWKV7PrefixStateSnapshot(
            shift_state=shift_state.to(
                device=self.device, dtype=self.shift_state.dtype
            ),
            wkv_state=wkv_state.to(device=self.device, dtype=self.wkv_state.dtype),
            elapsed=processed_token_count,
        )
        self._validate_native_snapshot(snapshot)
        entry = RWKV7NativeStateEntry(
            state_ref=state_ref,
            state_digest=state_digest,
            cache_binding_digest=cache_binding_digest,
            state_profile_id=state_profile_id,
            state_profile_sha256=state_profile_sha256,
            pending_token_id=pending_token_id,
            snapshot=snapshot,
        )
        self._require_native_cache().put(entry, replace=True)
        os.utime(path, None)
        return entry.metadata()

    def _validate_native_snapshot(self, snapshot: RWKV7PrefixStateSnapshot) -> None:
        if (
            snapshot.shift_state.shape != self.shift_state[:, :, 0].shape
            or snapshot.shift_state.dtype != self.shift_state.dtype
            or snapshot.shift_state.device != self.device
            or snapshot.wkv_state.shape != self.wkv_state[:, 0].shape
            or snapshot.wkv_state.dtype != self.wkv_state.dtype
            or snapshot.wkv_state.device != self.device
            or snapshot.elapsed < 0
        ):
            raise ValueError("RWKV7 native state snapshot is incompatible")

    @staticmethod
    def _trim_native_store(rank_dir: Path) -> None:
        capacity = envs.VLLM_RWKV7_NATIVE_STATE_STORE_CAPACITY
        if capacity < 0:
            raise ValueError("RWKV7 native state store capacity must be nonnegative")
        # A durable request journal can still reference any earlier export.
        # Persistent mode leaves reclamation to an explicit lifecycle operation.
        if capacity == 0:
            return
        entries = sorted(
            rank_dir.glob("[0-9a-f]" * 64 + ".pt"),
            key=lambda item: item.stat().st_mtime_ns,
            reverse=True,
        )
        for stale in entries[capacity:]:
            stale.unlink(missing_ok=True)

    def _cache_row(self, req_slot: int, prefix_length: int) -> None:
        cache = self.prefix_state_cache
        req_id = self.req_slot_owners[req_slot]
        if (
            cache is None
            or req_id is None
            or req_id not in self.prefix_cache_eligible_req_ids
            or prefix_length <= 0
        ):
            return
        token_ids = self.req_prompt_token_ids[req_id]
        if prefix_length > len(token_ids):
            raise RuntimeError("RWKV7 prefix cache target exceeds prompt length")
        profile_id = self.req_state_profile_ids.get(req_id)
        if profile_id is None:
            raise RuntimeError("RWKV7 prefix cache target has no state profile")
        profile = self.initial_state_profiles.resolve(profile_id)
        row = self.req_slot_to_row[req_slot]
        if row < 0:
            raise RuntimeError("RWKV7 prefix cache target has no resident state row")
        cache.put(
            self._prefix_identity(token_ids[:prefix_length], profile),
            RWKV7PrefixStateSnapshot(
                shift_state=self.shift_state[:, :, row].clone(),
                wkv_state=self.wkv_state[:, row].clone(),
                elapsed=prefix_length,
            ),
        )

    def _state_slot_for_batch_entry(
        self,
        input_batch: InputBatch,
        batch_idx: int,
    ) -> int:
        req_ids = getattr(input_batch, "req_ids", None)
        if req_ids is None or batch_idx >= len(req_ids):
            raise RuntimeError("RWKV7 requires request ids for state lookup")
        req_id = req_ids[batch_idx]
        if req_id is None:
            raise RuntimeError("RWKV7 request id cannot be None")
        req_slot = self.req_id_to_index.get(req_id)
        if req_slot is None:
            raise RuntimeError(f"RWKV state for request id {req_id!r} missing")
        return req_slot

    @staticmethod
    def _is_contiguous_decode_context(
        decode_rows: list[int],
        decode_token_positions: list[int],
    ) -> bool:
        if not decode_rows:
            return False
        decode_len = len(decode_rows)
        if decode_rows != list(range(decode_len)):
            return False
        start = decode_token_positions[0]
        return decode_token_positions == list(range(start, start + decode_len))

    def _new_dummy_state_tensors(self, num_reqs: int) -> dict[str, torch.Tensor]:
        return {
            "shift_state": torch.zeros(
                (self.num_layers, 2, num_reqs, self.hidden_size),
                dtype=self.shift_state.dtype,
                device=self.device,
            ),
            "wkv_state": torch.zeros(
                (
                    self.num_layers,
                    num_reqs,
                    self.num_heads,
                    self.head_size,
                    self.head_size,
                ),
                dtype=self.wkv_state.dtype,
                device=self.device,
            ),
            "elapsed": torch.zeros(
                (num_reqs,),
                dtype=self.elapsed.dtype,
                device=self.device,
            ),
        }

    def _packed_prefill_inputs(
        self,
        prefill_ranges: list[tuple[int, int, int]],
        prefill_rows: list[int],
    ) -> dict[str, torch.Tensor]:
        if len(prefill_ranges) != len(prefill_rows):
            raise RuntimeError("RWKV7 prefill range/row metadata mismatch")
        query_offsets = [0]
        token_positions: list[int] = []
        req_id: list[int] = []
        for local_req, (_batch_idx, start, end) in enumerate(prefill_ranges):
            length = end - start
            if length <= 0:
                raise RuntimeError(
                    "RWKV7 packed prefill requires positive request lengths"
                )
            token_positions.extend(range(start, end))
            req_id.extend([local_req] * length)
            query_offsets.append(query_offsets[-1] + length)
        return {
            "rwkv_prefill_query_start_loc": torch.tensor(
                query_offsets,
                dtype=torch.int32,
                device=self.device,
            ),
            "rwkv_prefill_slot_indices": torch.tensor(
                prefill_rows,
                dtype=torch.int32,
                device=self.device,
            ),
            "rwkv_prefill_token_positions": torch.tensor(
                token_positions,
                dtype=torch.long,
                device=self.device,
            ),
            "rwkv_prefill_req_id": torch.tensor(
                req_id,
                dtype=torch.int32,
                device=self.device,
            ),
        }

    @staticmethod
    def _set_sampling_logits_fast_path(
        input_batch: InputBatch,
        enabled: bool,
    ) -> None:
        try:
            input_batch.rwkv_sampling_logits_contiguous = (  # type: ignore[attr-defined]
                enabled
            )
        except Exception:
            return

    def get_supported_generation_tasks(self) -> tuple[GenerationTask, ...]:
        return ("generate",)

    def get_v2_kernel_warmup_skip_reason(self) -> str | None:
        return "uniform recurrent decode waves do not support mixed warmup batches"

    def custom_sampler(self, sampler: Any) -> tuple[Any, None]:
        # Sampling consumes logits and is independent from recurrent-state
        # ownership. Keep the native sampler available for greedy decoding and
        # per-request seeds when the rapid sampler is disabled.
        sampler.require_rapid = False
        return sampler, None

    def sort_scheduled_req_ids(
        self,
        req_ids: list[str],
        num_scheduled_tokens: dict[str, int],
        req_states: RequestState,
    ) -> list[str]:
        def key(item: tuple[int, str]) -> tuple[int, int, int]:
            order, req_id = item
            current_req_index = req_states.req_id_to_index.get(req_id)
            req_slot = self.req_id_to_index.get(req_id)
            if current_req_index is None or req_slot is None:
                return (num_scheduled_tokens[req_id], 1, order)
            is_prefilling = (
                req_states.num_computed_prefill_tokens[current_req_index]
                < req_states.prefill_len.np[current_req_index]
            )
            row = self.req_slot_to_row[req_slot]
            if (
                num_scheduled_tokens[req_id] == 1
                and not bool(is_prefilling)
                and row >= 0
            ):
                return (1, 0, row)
            return (num_scheduled_tokens[req_id], 1, order)

        return [req_id for _order, req_id in sorted(enumerate(req_ids), key=key)]

    def add_request(self, req_index: int, new_req_data: NewRequestData) -> None:
        if req_index < 0 or req_index >= self.max_num_reqs:
            raise RuntimeError(f"RWKV7 request slot {req_index} is out of range")
        req_id = new_req_data.req_id
        if req_id in self.req_id_to_index:
            raise RuntimeError(f"RWKV7 request id {req_id!r} already owns state")
        current_owner = self.req_slot_owners[req_index]
        if current_owner is not None:
            raise RuntimeError(
                f"RWKV7 request slot {req_index} is already owned by {current_owner!r}"
            )
        if not self.free_rows:
            raise RuntimeError("RWKV7 state pool is full")

        sampling_params = new_req_data.sampling_params
        profile = resolve_request_profile(self.initial_state_profiles, sampling_params)
        extra_args = getattr(sampling_params, "extra_args", None) or {}
        prompt_token_ids = tuple(new_req_data.prompt_token_ids or ())
        native_read_values = (
            extra_args.get(RWKV7_NATIVE_STATE_READ_REF_XARG),
            extra_args.get(RWKV7_NATIVE_STATE_READ_DIGEST_XARG),
            extra_args.get(RWKV7_NATIVE_STATE_READ_BINDING_XARG),
        )
        native_write_values = (
            extra_args.get(RWKV7_NATIVE_STATE_WRITE_REF_XARG),
            extra_args.get(RWKV7_NATIVE_STATE_WRITE_DIGEST_XARG),
            extra_args.get(RWKV7_NATIVE_STATE_WRITE_BINDING_XARG),
        )
        native_requested = any(
            value is not None for value in native_read_values
        ) or any(
            value is not None for value in native_write_values
        )
        native_snapshot = None
        native_write = None
        if native_requested:
            if not all(
                isinstance(value, str) and value for value in native_read_values
            ):
                raise ValueError("RWKV7 native state read identity is incomplete")
            if not all(
                isinstance(value, str) and value for value in native_write_values
            ):
                raise ValueError("RWKV7 native state write identity is incomplete")
            if not prompt_token_ids:
                raise ValueError("RWKV7 native continuation requires prompt tokens")
            cache = self._require_native_cache()
            native_read = cache.get(
                native_read_values[0],
                state_digest=native_read_values[1],
                cache_binding_digest=native_read_values[2],
            )
            if (
                native_read.state_profile_id != profile.profile_id
                or native_read.state_profile_sha256 != profile.state_sha256
            ):
                raise ValueError("RWKV7 native state profile mismatch")
            if prompt_token_ids[0] != native_read.pending_token_id:
                raise ValueError("RWKV7 native continuation pending token mismatch")
            pending_value = extra_args.get(RWKV7_NATIVE_STATE_WRITE_PENDING_XARG)
            if pending_value is not None and (
                not isinstance(pending_value, int)
                or isinstance(pending_value, bool)
                or pending_value < 0
            ):
                raise ValueError("RWKV7 native write pending token is invalid")
            native_snapshot = native_read.snapshot
            native_write = _RWKV7NativeStateWrite(
                state_ref=native_write_values[0],
                state_digest=native_write_values[1],
                cache_binding_digest=native_write_values[2],
                state_profile_id=profile.profile_id,
                state_profile_sha256=profile.state_sha256,
                pending_token_id=pending_value,
            )
        prefix_state_cache = self.prefix_state_cache
        cache_eligible = bool(
            not native_requested
            and prefix_state_cache is not None
            and prompt_token_ids
            and (
                sampling_params is None
                or getattr(sampling_params, "prompt_logprobs", None) is None
            )
        )
        cache_hit_length = 0
        cached_snapshot = None
        if cache_eligible:
            assert prefix_state_cache is not None
            hit = prefix_state_cache.get_longest_prefix(
                self._prefix_identity(prompt_token_ids, profile),
                max_prefix_length=len(prompt_token_ids) - 1,
            )
            if hit is not None:
                cache_hit_length, cached_snapshot = hit
        if new_req_data.num_computed_tokens > cache_hit_length:
            raise RuntimeError(
                "RWKV7 cannot restore scheduler-computed prefix state: "
                f"request has {new_req_data.num_computed_tokens} computed tokens "
                f"but recurrent cache restored {cache_hit_length}."
            )

        row = min(self.free_rows)
        if self.row_to_req_slot[row] != -1:
            raise RuntimeError(f"RWKV7 free state row {row} still has an owner")
        self.free_rows.remove(row)
        self.req_id_to_index[req_id] = req_index
        self.req_slot_owners[req_index] = req_id
        self.req_slot_to_row[req_index] = row
        self.row_to_req_slot[row] = req_index
        self.req_state_profile_ids[req_id] = profile.profile_id
        self._initialize_row(row, profile)
        try:
            if native_snapshot is not None:
                self._restore_row(row, native_snapshot)
            elif cached_snapshot is not None:
                self._restore_row(row, cached_snapshot)
        except Exception:
            self.req_id_to_index.pop(req_id)
            self.req_slot_owners[req_index] = None
            self.req_slot_to_row[req_index] = -1
            self.row_to_req_slot[row] = -1
            self.req_state_profile_ids.pop(req_id, None)
            self.free_rows.add(row)
            self._zero_row(row)
            raise
        self.req_prompt_token_ids[req_id] = prompt_token_ids
        self.req_prefix_cache_hit_lengths[req_id] = cache_hit_length
        if native_write is not None:
            self.req_native_state_writes[req_id] = native_write
        if cache_eligible:
            self.prefix_cache_eligible_req_ids.add(req_id)

    def remove_request(self, req_id: str) -> None:
        req_index = self.req_id_to_index.get(req_id)
        if req_index is None:
            return
        if self.req_slot_owners[req_index] != req_id:
            raise RuntimeError(
                f"RWKV7 request slot {req_index} has stale owner "
                f"{self.req_slot_owners[req_index]!r}, expected {req_id!r}"
            )
        row = self.req_slot_to_row[req_index]
        if row == -1:
            raise RuntimeError(f"RWKV state for request id {req_id!r} missing")
        native_write = self.req_native_state_writes.pop(req_id, None)
        if native_write is not None:
            cache = self._require_native_cache()
            if not cache.contains(native_write.state_ref):
                snapshot = self._snapshot_row(row)
                if native_write.pending_token_id is None:
                    # The sampled token is owned by the serving process.  Keep
                    # the expensive recurrent tensors safe across scheduler
                    # cleanup now, then bind the exact pending token in the
                    # immediately following capture RPC.
                    self._finalize_native_snapshot(
                        native_write,
                        snapshot,
                        0,
                    )
                    self.pending_sampled_native_state_refs.add(
                        native_write.state_ref
                    )
                else:
                    self._finalize_native_snapshot(native_write, snapshot, 0)
        self.req_id_to_index.pop(req_id)
        if req_index in self.decode_req_slots:
            self._remove_decode_row(req_index, row)
        else:
            self._zero_row(row)
            self.req_slot_to_row[req_index] = -1
            self.row_to_req_slot[row] = -1
            self.req_slot_owners[req_index] = None
            self.free_rows.add(row)
        self.req_prompt_token_ids.pop(req_id, None)
        self.req_prefix_cache_hit_lengths.pop(req_id, None)
        self.prefix_cache_eligible_req_ids.discard(req_id)
        self.req_state_profile_ids.pop(req_id, None)

    def _remove_decode_row(self, req_index: int, row: int) -> None:
        self._zero_row(row)
        self.decode_req_slots.remove(req_index)
        self.req_slot_to_row[req_index] = -1
        self.row_to_req_slot[row] = -1
        self.req_slot_owners[req_index] = None
        self.free_rows.add(row)

    def _mark_resident_row_decode(self, req_slot: int) -> int:
        current_row = self.req_slot_to_row[req_slot]
        if current_row == -1:
            raise RuntimeError(f"RWKV state for request slot {req_slot} missing")
        self.decode_req_slots.add(req_slot)
        return current_row

    def _validate_decode_membership(self) -> None:
        for req_slot in self.decode_req_slots:
            owner = self.req_slot_owners[req_slot]
            if owner is None or self.req_id_to_index.get(owner) != req_slot:
                raise RuntimeError("RWKV7 decode request slot has a stale owner")
            row = self.req_slot_to_row[req_slot]
            if row < 0 or row >= self.max_num_reqs:
                raise RuntimeError("RWKV7 live decode resident row is out of range")
            if self.row_to_req_slot[row] != req_slot:
                raise RuntimeError("RWKV7 decode resident mapping is inconsistent")

    def _zero_row(self, row: int) -> None:
        self.shift_state[:, :, row].zero_()
        self.wkv_state[:, row].zero_()
        self.elapsed[row].zero_()

    def _initialize_row(
        self,
        row: int,
        profile: RWKV7InitialStateProfile,
    ) -> None:
        self._zero_row(row)
        if profile.wkv_state is not None:
            self.wkv_state[:, row].copy_(profile.wkv_state)

    def reset_after_weight_update(self) -> None:
        active_rows = self.max_num_reqs - len(self.free_rows)
        if active_rows:
            logger.warning(
                "Resetting RWKV7 state after weight update with %d active rows. "
                "The trainer should quiesce requests before updating weights.",
                active_rows,
            )
        self.shift_state.zero_()
        self.wkv_state.zero_()
        self.elapsed.zero_()
        if self.prefix_state_cache is not None:
            self.prefix_state_cache.clear()
        if self.native_state_cache is not None:
            self.native_state_cache.clear()
        self.req_native_state_writes.clear()
        self.staged_native_state_snapshots.clear()
        self.pending_sampled_native_state_refs.clear()
        self.req_prefix_cache_hit_lengths = {
            req_id: 0 for req_id in self.req_id_to_index
        }
        # Level-2 sleep discards allocator-backed tensors. Rebuild the static
        # decode metadata that is not restored by checkpoint weight streaming.
        torch.arange(self.max_num_reqs, out=self.execution_idx_mapping)
        torch.arange(
            self.max_num_reqs + 1,
            out=self.decode_query_start_loc,
        )

    def get_mm_embeddings(
        self,
        scheduled_encoder_inputs: dict[str, list[int]],
        input_batch: InputBatch,
        req_states: RequestState,
    ) -> torch.Tensor | None:
        return None

    def prepare_inputs(
        self, input_batch: InputBatch, req_states: RequestState
    ) -> dict[str, Any]:
        self._set_sampling_logits_fast_path(input_batch, False)
        self._prefill_req_slots = []
        self._prefill_becomes_decode = []
        self._prefill_cache_targets = []
        req_ids = getattr(input_batch, "req_ids", None)
        is_dummy_batch = (
            req_ids is not None
            and bool(req_ids)
            and all(req_id not in self.req_id_to_index for req_id in req_ids)
        )
        if is_dummy_batch:
            if not self.req_id_to_index:
                self._reset_mappings()
            query_start_loc_np = getattr(
                input_batch,
                "query_start_loc_np",
                None,
            )
            if query_start_loc_np is None:
                query_start_loc = input_batch.query_start_loc
                if (
                    not isinstance(query_start_loc, torch.Tensor)
                    or query_start_loc.device.type != "cpu"
                ):
                    raise RuntimeError("RWKV7 dummy prefill requires CPU query offsets")
                query_offsets = [int(offset) for offset in query_start_loc.tolist()]
            else:
                query_offsets = [int(offset) for offset in query_start_loc_np]
            prefill_ranges = [
                (batch_idx, query_offsets[batch_idx], query_offsets[batch_idx + 1])
                for batch_idx in range(input_batch.num_reqs)
            ]
            dummy_prefill_rows = list(range(input_batch.num_reqs))
            return {
                "query_start_loc": input_batch.query_start_loc,
                "idx_mapping": self.execution_idx_mapping[: input_batch.num_reqs],
                "rwkv_prefill_token_ranges": prefill_ranges,
                "rwkv_prefill_rows": dummy_prefill_rows,
                **self._packed_prefill_inputs(prefill_ranges, dummy_prefill_rows),
                **self._new_dummy_state_tensors(input_batch.num_reqs),
            }

        query_start_loc_np = getattr(input_batch, "query_start_loc_np", None)
        if query_start_loc_np is None:
            raise RuntimeError("RWKV7 requires CPU query_start_loc metadata")
        is_prefilling_np = getattr(input_batch, "is_prefilling_np", None)
        if is_prefilling_np is None:
            raise RuntimeError("RWKV7 requires CPU prefill metadata")

        batch_entries: list[tuple[int, int, bool, int, int]] = []
        for batch_idx in range(len(input_batch.idx_mapping_np)):
            req_slot = self._state_slot_for_batch_entry(input_batch, batch_idx)
            current_row = self.req_slot_to_row[req_slot]
            if current_row == -1:
                raise RuntimeError(f"RWKV state for request slot {req_slot} missing")
            start = int(query_start_loc_np[batch_idx])
            end = int(query_start_loc_np[batch_idx + 1])
            query_len = end - start
            is_prefill = bool(is_prefilling_np[batch_idx]) or query_len > 1
            batch_entries.append((batch_idx, req_slot, is_prefill, start, end))

        decode_entries: list[tuple[int, int, int, int]] = []
        live_decode_req_slots = set(self.decode_req_slots)
        scheduled_decode_req_slots: set[int] = set()
        prefill_entries: list[tuple[int, int, int, bool, int, int, int]] = []
        for batch_idx, req_slot, is_prefill, start, end in batch_entries:
            current_row = self.req_slot_to_row[req_slot]
            if current_row == -1:
                raise RuntimeError(f"RWKV state for request slot {req_slot} missing")
            if is_prefill:
                if start >= end:
                    raise RuntimeError(
                        "RWKV7 fast prefill requires positive request lengths."
                    )
                num_computed_prefill = getattr(
                    input_batch, "num_computed_prefill_tokens_np", None
                )
                prefill_len = getattr(input_batch, "prefill_len_np", None)
                scheduled_tokens = getattr(input_batch, "num_scheduled_tokens", None)
                becomes_decode = False
                if (
                    num_computed_prefill is not None
                    and prefill_len is not None
                    and scheduled_tokens is not None
                ):
                    becomes_decode = int(num_computed_prefill[batch_idx]) + int(
                        scheduled_tokens[batch_idx]
                    ) >= int(prefill_len[batch_idx])
                effective_start = start
                cache_target = 0
                req_id = self.req_slot_owners[req_slot]
                cache_hit_length = (
                    self.req_prefix_cache_hit_lengths.get(req_id, 0)
                    if req_id is not None
                    else 0
                )
                if cache_hit_length:
                    if num_computed_prefill is None:
                        raise RuntimeError(
                            "RWKV7 prefix cache requires computed-token metadata"
                        )
                    computed = int(num_computed_prefill[batch_idx])
                    effective_start += min(
                        max(cache_hit_length - computed, 0), end - start
                    )
                if req_id in self.prefix_cache_eligible_req_ids:
                    if num_computed_prefill is None:
                        raise RuntimeError(
                            "RWKV7 prefix cache requires computed-token metadata"
                        )
                    cache_target = int(num_computed_prefill[batch_idx]) + (end - start)
                if effective_start < end:
                    prefill_entries.append(
                        (
                            batch_idx,
                            req_slot,
                            current_row,
                            becomes_decode,
                            effective_start,
                            end,
                            cache_target,
                        )
                    )
            else:
                decode_row = self._mark_resident_row_decode(req_slot)
                scheduled_decode_req_slots.add(req_slot)
                decode_entries.append((batch_idx, req_slot, decode_row, start))
        if scheduled_decode_req_slots:
            missing_decode_req_slots = (
                live_decode_req_slots - scheduled_decode_req_slots
            )
            if missing_decode_req_slots:
                raise RuntimeError(
                    "RWKV7 native decode requires scheduling all live decode "
                    "rows; missing request slots "
                    f"{sorted(missing_decode_req_slots)}"
                )
        if decode_entries:
            self._validate_decode_membership()
        scheduled_rows = [
            self.req_slot_to_row[req_slot]
            for _batch_idx, req_slot, _is_prefill, _start, _end in batch_entries
        ]
        idx_mapping = torch.tensor(
            scheduled_rows,
            dtype=torch.int32,
            device=self.device,
        )
        source_decode_rows = [
            row for _batch_idx, _req_slot, row, _start in decode_entries
        ]
        decode_token_positions = [
            start for _batch_idx, _req_slot, _row, start in decode_entries
        ]
        use_contiguous_decode = self._is_contiguous_decode_context(
            source_decode_rows,
            decode_token_positions,
        )
        if decode_entries and not use_contiguous_decode:
            decode_len = len(decode_entries)
            self.decode_slot_indices[:decode_len].copy_(
                torch.tensor(
                    source_decode_rows,
                    dtype=torch.int32,
                    device=self.device,
                )
            )
            self.decode_token_positions[:decode_len].copy_(
                torch.tensor(
                    decode_token_positions,
                    dtype=torch.long,
                    device=self.device,
                )
            )
            slot_indices = self.decode_slot_indices[:decode_len]
            decode_token_position_tensor = self.decode_token_positions[:decode_len]
        elif decode_entries:
            slot_indices = None
            decode_token_position_tensor = decode_token_positions
        else:
            slot_indices = None
            decode_token_position_tensor = None
        decode_rows = source_decode_rows if decode_entries else []
        decode_context_size = len(decode_rows)
        decode_state_tensors = {
            "shift_state": self.shift_state,
            "wkv_state": self.wkv_state,
            "elapsed": self.elapsed,
        }

        if not prefill_entries:
            self._set_sampling_logits_fast_path(
                input_batch,
                bool(decode_entries and len(decode_entries) == input_batch.num_reqs),
            )
            return {
                "query_start_loc": input_batch.query_start_loc,
                "idx_mapping": idx_mapping,
                **decode_state_tensors,
                "rwkv_decode_batch_size": decode_context_size,
                "rwkv_decode_rows": decode_rows,
                "rwkv_decode_token_positions": decode_token_position_tensor,
                "rwkv_decode_query_start_loc": self.decode_query_start_loc[
                    : decode_context_size + 1
                ],
                "slot_indices": slot_indices,
            }

        prefill_rows: list[int] = []
        for (
            _batch_idx,
            req_slot,
            _decode_row,
            becomes_decode,
            _start,
            _end,
            cache_target,
        ) in prefill_entries:
            prefill_rows.append(self.req_slot_to_row[req_slot])
            self._prefill_req_slots.append(req_slot)
            self._prefill_becomes_decode.append(becomes_decode)
            self._prefill_cache_targets.append(cache_target)

        prefill_ranges = [
            (batch_idx, start, end)
            for (
                batch_idx,
                _req_slot,
                _row,
                _becomes_decode,
                start,
                end,
                _cache_target,
            ) in prefill_entries
        ]
        prefill_lengths = [end - start for _batch_idx, start, end in prefill_ranges]
        has_positive_prefill_lengths = all(length > 0 for length in prefill_lengths)
        if not has_positive_prefill_lengths:
            raise RuntimeError("RWKV7 fast prefill requires positive request lengths.")
        prefill_varlen_inputs = self._packed_prefill_inputs(
            prefill_ranges,
            prefill_rows,
        )
        if len(prefill_entries) == input_batch.num_reqs:
            return {
                "query_start_loc": input_batch.query_start_loc,
                "idx_mapping": idx_mapping,
                "rwkv_prefill_token_ranges": prefill_ranges,
                "rwkv_prefill_rows": prefill_rows,
                **prefill_varlen_inputs,
                "shift_state": self.shift_state,
                "wkv_state": self.wkv_state,
                "elapsed": self.elapsed,
            }
        mixed_inputs = {
            "query_start_loc": input_batch.query_start_loc,
            "idx_mapping": idx_mapping,
            **decode_state_tensors,
            "rwkv_decode_batch_size": decode_context_size,
            "rwkv_decode_rows": decode_rows,
            "rwkv_decode_token_positions": decode_token_position_tensor,
            "rwkv_decode_query_start_loc": self.decode_query_start_loc[
                : decode_context_size + 1
            ],
            "slot_indices": slot_indices,
            "rwkv_prefill_token_ranges": prefill_ranges,
            "rwkv_prefill_rows": prefill_rows,
            **prefill_varlen_inputs,
        }
        if decode_entries:
            mixed_inputs.update(
                {
                    "prefill_shift_state": self.shift_state,
                    "prefill_wkv_state": self.wkv_state,
                    "prefill_elapsed": self.elapsed,
                }
            )
        return mixed_inputs

    def postprocess_state(
        self,
        idx_mapping: torch.Tensor,
        num_sampled: torch.Tensor | int,
        num_computed_tokens: torch.Tensor | None = None,
    ) -> None:
        if not self._prefill_req_slots:
            return
        for scratch_row, req_slot in enumerate(self._prefill_req_slots):
            self._cache_row(req_slot, self._prefill_cache_targets[scratch_row])
            if self._prefill_becomes_decode[scratch_row]:
                self._mark_resident_row_decode(req_slot)
        self._validate_decode_membership()
        self._prefill_req_slots = []
        self._prefill_becomes_decode = []
        self._prefill_cache_targets = []

    def has_pending_postprocess_state(self) -> bool:
        return bool(self._prefill_req_slots)

    @staticmethod
    def can_replay_full_cudagraph(model_inputs: dict[str, Any]) -> bool:
        """Return whether runtime decode matches the static contiguous graph."""
        decode_batch_size = model_inputs.get("rwkv_decode_batch_size")
        decode_rows = model_inputs.get("rwkv_decode_rows")
        positions = model_inputs.get("positions")
        if (
            not isinstance(decode_batch_size, int)
            or decode_batch_size <= 0
            or not isinstance(decode_rows, list)
            or not isinstance(positions, torch.Tensor)
        ):
            return False
        return (
            model_inputs.get("slot_indices") is None
            and decode_batch_size == positions.shape[0]
            and decode_rows == list(range(decode_batch_size))
        )

    def prepare_dummy_inputs(self, num_reqs: int, num_tokens: int) -> dict[str, Any]:
        lengths = torch.full(
            (num_reqs,),
            num_tokens // num_reqs,
            dtype=torch.int32,
            device="cpu",
        )
        lengths[: num_tokens % num_reqs] += 1
        query_start_loc = torch.empty((num_reqs + 1,), dtype=torch.int32)
        query_start_loc[0] = 0
        query_start_loc[1:] = lengths.cumsum(dim=0)
        idx_mapping = self.execution_idx_mapping[:num_reqs]
        # Full CUDAGraph replay binds captured state pointers, so decode capture
        # uses resident buffers. Request-level dummy profiling uses scratch.
        state_tensors = {
            "shift_state": self.shift_state,
            "wkv_state": self.wkv_state,
            "elapsed": self.elapsed,
        }
        if num_tokens == num_reqs:
            return {
                "query_start_loc": query_start_loc,
                "idx_mapping": idx_mapping,
                **state_tensors,
                "rwkv_decode_batch_size": num_reqs,
                "rwkv_decode_rows": list(range(num_reqs)),
                "rwkv_decode_token_positions": list(range(num_reqs)),
                "rwkv_decode_query_start_loc": self.decode_query_start_loc[
                    : num_reqs + 1
                ],
                "slot_indices": None,
            }
        prefill_ranges = [
            (
                request,
                int(query_start_loc[request]),
                int(query_start_loc[request + 1]),
            )
            for request in range(num_reqs)
        ]
        prefill_rows = list(range(num_reqs))
        return {
            "query_start_loc": query_start_loc,
            "idx_mapping": idx_mapping,
            **state_tensors,
            "rwkv_prefill_token_ranges": prefill_ranges,
            "rwkv_prefill_rows": prefill_rows,
            **self._packed_prefill_inputs(prefill_ranges, prefill_rows),
        }

    def prepare_attn(
        self,
        input_batch: InputBatch,
        cudagraph_mode: CUDAGraphMode,
        block_tables: tuple[torch.Tensor, ...],
        slot_mappings: torch.Tensor,
        attn_groups: list[list[AttentionGroup]],
        kv_cache_config: KVCacheConfig,
        for_capture: bool = False,
    ) -> dict[str, Any]:
        return {}
