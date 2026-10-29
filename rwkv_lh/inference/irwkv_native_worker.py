# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Persistent State lifecycle on irwkv's native FlashRWKV2 state pools.

irwkv owns scheduling, kernels, model loading and sampling. This adapter owns
only immutable cross-request snapshots and the existing transactional RPCs.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import torch
from irwkv.v1.worker.gpu.model_states.rwkv import RwkvModelState
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION
from rwkv_lh.inference.irwkv_state_profiles_v1 import (
    RWKV7InitialStateProfile, RWKV7InitialStateProfiles, RWKV7_ZERO_STATE_PROFILE,
    resolve_request_profile, sha256_file,
)
from rwkv_lh.inference import native_settings as envs

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

class RWKV7ModelState(RwkvModelState):
    def __init__(self, irwkv_config, model, encoder_cache, device):
        super().__init__(irwkv_config, model, encoder_cache, device)
        if (irwkv_config.cache_config.enable_prefix_caching
                or irwkv_config.cache_config.mamba_cache_mode != 'none'):
            raise ValueError('Native explicit State requires prefix caching off and mamba_cache_mode=none')
        if irwkv_config.parallel_config.tensor_parallel_size != 1 or irwkv_config.parallel_config.pipeline_parallel_size != 1:
            raise ValueError('This persistent Executor deployment requires one GPU')
        cfg = self.model_config.hf_config
        self.num_layers = int(cfg.num_hidden_layers)
        self.num_heads = int(cfg.hidden_size // cfg.head_size)
        self.head_size = int(cfg.head_size)
        self.hidden_size = int(cfg.hidden_size)
        self.model = model
        # Small geometry templates; live recurrent tensors stay owned by irwkv.
        self.shift_state = torch.zeros((self.num_layers,2,1,self.hidden_size),dtype=torch.bfloat16,device=device)
        self.wkv_state = torch.zeros((self.num_layers,1,self.num_heads,self.head_size,self.head_size),dtype=torch.float32,device=device)
        if self._state_layer.state_dtype != torch.float32:
            raise ValueError('Native Executor requires FP32 recurrent State')
        self.native_state_cache = RWKV7NativeStateCache(envs.IRWKV_RWKV7_NATIVE_STATE_CACHE_CAPACITY)
        self.req_native_state_writes = {}
        self.staged_native_state_snapshots = OrderedDict()
        self.pending_sampled_native_state_refs = set()
        self.req_id_to_index = {}
        self.req_slot_to_row = {}
        self._requests = {}
        self._elapsed_by_row = {}
        self._initialize_native_source_identity()
        self._prefix_identity_fields = {
            'model_artifact': str(self.model_config.model),
            'model_revision': self._native_weight_identity['tensors_sha256'],
            'backend_provider': 'irwkv-native',
            'backend_revision': self._native_source_identity['engine_manifest_sha256'],
            'wkv_mode': 'fp32io16', 'gemm_policy': 'fp32',
        }
        manifest=envs.IRWKV_RWKV7_STATE_PROFILE_MANIFEST
        if manifest:
            self.initial_state_profiles=RWKV7InitialStateProfiles.load(
                manifest,envs.IRWKV_RWKV7_STATE_PROFILE_MANIFEST_SHA256,
                model_artifact=str(self.model_config.model),
                model_revision=self._prefix_identity_fields['model_revision'],
                total_num_layers=self.num_layers,total_num_heads=self.num_heads,
                layer_offset=0,num_layers=self.num_layers,tp_size=1,tp_rank=0,
                num_heads=self.num_heads,head_size=self.head_size,device=device,dtype=torch.float32)
        else:
            if envs.IRWKV_RWKV7_STATE_PROFILE_MANIFEST_SHA256:
                raise ValueError('State profile digest requires its manifest')
            self.initial_state_profiles=RWKV7InitialStateProfiles.zero_only()

    def _snapshot_row(self, row):
        layer=self._state_layer
        layer.materialize_state_slots([row])
        return RWKV7PrefixStateSnapshot(
            torch.stack((layer._tmix_shift_pool[:,row],layer._cmix_shift_pool[:,row]),dim=1).clone(),
            layer._wkv_state_pool[:,row].clone(), self._elapsed_by_row[row])

    def _restore_row(self, row, snapshot):
        self._validate_native_snapshot(snapshot)
        layer=self._state_layer
        # Materialize before modifying the canonical pool so no deferred update
        # can later overwrite the restored tensors.
        layer.materialize_state_slots([row])
        layer._tmix_shift_pool[:,row].copy_(snapshot.shift_state[:,0])
        layer._cmix_shift_pool[:,row].copy_(snapshot.shift_state[:,1])
        layer._wkv_state_pool[:,row].copy_(snapshot.wkv_state)
        self._elapsed_by_row[row]=snapshot.elapsed

    def add_request(self, req_index, new_req_data):
        req_id=new_req_data.req_id
        if req_id in self._requests or req_index in self.req_id_to_index.values():
            raise ValueError('Native request slot is already owned')
        if new_req_data.num_computed_tokens:
            raise ValueError('Native request cannot resume an unregistered scheduler prefix')
        profile=resolve_request_profile(self.initial_state_profiles,new_req_data.sampling_params)
        extra=getattr(new_req_data.sampling_params,'extra_args',None) or {}
        read=[extra.get(k) for k in (RWKV7_NATIVE_STATE_READ_REF_XARG,RWKV7_NATIVE_STATE_READ_DIGEST_XARG,RWKV7_NATIVE_STATE_READ_BINDING_XARG)]
        write=[extra.get(k) for k in (RWKV7_NATIVE_STATE_WRITE_REF_XARG,RWKV7_NATIVE_STATE_WRITE_DIGEST_XARG,RWKV7_NATIVE_STATE_WRITE_BINDING_XARG)]
        snapshot=None
        if any(v is not None for v in read+write):
            if not all(isinstance(v,str) and v for v in read+write):
                raise ValueError('Native read/write identity is incomplete')
            parent=self._require_native_cache().get(read[0],state_digest=read[1],cache_binding_digest=read[2])
            tokens=new_req_data.prompt_token_ids
            if not tokens or tokens[0]!=parent.pending_token_id:
                raise ValueError('Native continuation pending token mismatch')
            if (parent.state_profile_id,parent.state_profile_sha256)!=(profile.profile_id,profile.state_sha256):
                raise ValueError('Native State profile differs')
            pending=extra.get(RWKV7_NATIVE_STATE_WRITE_PENDING_XARG)
            if pending is not None and (type(pending) is not int or pending<0):
                raise ValueError('Native write pending token is invalid')
            snapshot=parent.snapshot
            self.req_native_state_writes[req_id]=_RWKV7NativeStateWrite(*write,profile.profile_id,profile.state_sha256,pending)
        super().add_request(req_index,new_req_data)
        self.req_id_to_index[req_id]=req_index
        self._requests[req_id]={'profile':profile,'snapshot':snapshot,'started':False,'tokens':0,
                                'base_tokens':0 if snapshot is None else snapshot.elapsed}

    def preprocess_state(self, input_batch, block_tables, kv_cache_config, num_computed_tokens):
        super().preprocess_state(input_batch,block_tables,kv_cache_config,num_computed_tokens)
        table=block_tables[self._get_rwkv_group_id(kv_cache_config)]
        indices=list(input_batch.idx_mapping_np[:input_batch.num_reqs])
        owners={index:req for req,index in self.req_id_to_index.items()}
        for batch_row,index in enumerate(indices):
            req_id=owners[int(index)]; request=self._requests[req_id]
            row=int(table[batch_row,0].item())
            previous=self.req_slot_to_row.get(int(index))
            if request['started'] and previous!=row:
                raise RuntimeError('Native recurrent slot changed without an explicit copy')
            self.req_slot_to_row[int(index)]=row
            if not request['started']:
                self._state_layer.reset_state_slots([row])
                if request['snapshot'] is not None:self._restore_row(row,request['snapshot'])
                elif request['profile'].wkv_state is not None:
                    self._state_layer.materialize_state_slots([row])
                    self._state_layer._wkv_state_pool[:,row].copy_(request['profile'].wkv_state)
                request['started']=True
            request['tokens']+=int(input_batch.num_scheduled_tokens[batch_row])
            self._elapsed_by_row[row]=request['base_tokens']+request['tokens']

    def capture_native_request(self, request_id, sampled_token_id):
        write=self.req_native_state_writes.get(request_id)
        if write is None:raise KeyError('Native request is no longer active')
        index=self.req_id_to_index[request_id]
        return self._finalize_native_snapshot(write,self._snapshot_row(self.req_slot_to_row[index]),sampled_token_id)

    def reset_kv_cache_blocks(self, block_ids):
        # Scheduler zeroing must not destroy an owned, materialized recurrence.
        # Free/reassigned slots still take the upstream reset path; preprocess
        # restores a new request's immutable snapshot after that reset.
        owned = set(self.req_slot_to_row.values())
        free = [int(row) for row in block_ids if int(row) not in owned]
        if free:
            return super().reset_kv_cache_blocks(free)
        return True

    def remove_request(self, req_id):
        index=self.req_id_to_index.get(req_id)
        if index is not None:
            write=self.req_native_state_writes.pop(req_id,None)
            row=self.req_slot_to_row.pop(index,None)
            if write is not None and row is not None and not self._require_native_cache().contains(write.state_ref):
                self._finalize_native_snapshot(write,self._snapshot_row(row),0)
                if write.pending_token_id is None:self.pending_sampled_native_state_refs.add(write.state_ref)
            self.req_id_to_index.pop(req_id)
            self._requests.pop(req_id)
            if row is not None:self._elapsed_by_row.pop(row,None)
        super().remove_request(req_id)

    def preempt_request(self, req_id):
        # Replaying a partial request would duplicate recurrent history.
        if req_id in self.req_native_state_writes:
            raise RuntimeError('Native persistent State cannot be preempted; reduce concurrency')
        super().preempt_request(req_id)


    def _initialize_native_source_identity(self) -> None:
        self._native_source_identity: dict[str, Any] = {}
        self._native_weight_identity: dict[str, Any] = {}
        if self.native_state_cache is not None:
            import irwkv
            from rwkv_lh.inference.native_source_identity import (
                verify_native_source_identity,
            )
            self._native_source_identity = verify_native_source_identity(
                engine_file=getattr(irwkv, "__file__", None), project_file=__file__,
            )
            from rwkv_lh.inference.native_weight_identity import fingerprint_model
            self._native_weight_identity = fingerprint_model(self.model)

    def _require_native_cache(self) -> RWKV7NativeStateCache:
        if self.native_state_cache is None:
            raise NotImplementedError("RWKV7 native state cache is disabled")
        return self.native_state_cache

    def native_state_capabilities(self) -> dict[str, Any]:
        cache = self._require_native_cache()
        store = self._tensor_store()
        from rwkv_lh.inference.native_weight_identity import fingerprint_model
        actual_weights = fingerprint_model(self.model)
        if actual_weights != self._native_weight_identity:
            raise RuntimeError('Native resident weights changed; existing State identity is invalid')
        return {
            "state_format_version": RWKV7_NATIVE_STATE_FORMAT,
            "cache_capacity": cache.capacity,
            "store_configured": store.mode == 'memory' or bool(envs.IRWKV_RWKV7_NATIVE_STATE_DIR),
            "store_persistent": store.mode == 'disk' and envs.IRWKV_RWKV7_NATIVE_STATE_STORE_CAPACITY == 0,
            "tensor_storage": store.mode,
            "memory_store_capacity_bytes": store.capacity_bytes if store.mode == 'memory' else 0,
            "state_lifecycle_protocol": NATIVE_STATE_LIFECYCLE_VERSION,
            "model_identity": dict(self._prefix_identity_fields),
            "source_identity": dict(self._native_source_identity),
            "loaded_weight_identity": actual_weights,
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
        root_value = envs.IRWKV_RWKV7_NATIVE_STATE_DIR
        if not root_value:
            raise NotImplementedError("RWKV7 native state store is not configured")
        root = Path(root_value).resolve()
        rank_dir = root / f"rank-{worker_rank}"
        self._ensure_native_store_directory(rank_dir)
        return rank_dir / f"{store_key}.pt"

    def _tensor_store(self):
        from rwkv_lh.inference.native_tensor_store import NativeTensorStore
        if not hasattr(self, '_native_tensor_store'):
            self._native_tensor_store = NativeTensorStore.from_environment()
        return self._native_tensor_store

    def export_native_state(
        self,
        *,
        state_ref: str,
        store_key: str,
        worker_rank: int,
    ) -> dict[str, Any]:
        entry = self._require_native_cache().get(state_ref)
        # A durable receipt must never make a poisoned live State resumable.
        self._validate_native_snapshot(entry.snapshot)
        if not _SHA256_PATTERN.fullmatch(store_key) or type(worker_rank) is not int or worker_rank < 0:
            raise ValueError('invalid Native State store key or worker rank')
        payload = {
            "schema_version": RWKV7_NATIVE_STATE_FORMAT,
            "execution_identity": self._native_execution_identity(),
            **entry.metadata(),
            "shift_state": entry.snapshot.shift_state.detach().cpu(),
            "wkv_state": entry.snapshot.wkv_state.detach().cpu(),
        }
        if self._tensor_store().mode == 'memory':
            self._tensor_store().put(worker_rank, store_key, payload)
            return {**entry.metadata(), "store_key": store_key, "worker_rank": worker_rank}
        path = self._native_store_path(store_key, worker_rank)
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
            "allow_fp16_accumulation": getattr(self.model, 'allow_fp16_accumulation', False),
            "source_identity": dict(self._native_source_identity),
            "loaded_weight_identity": dict(self._native_weight_identity),
        }

    def delete_native_state_export(self, *, store_key: str, worker_rank: int) -> dict[str, Any]:
        """Only the API's durable, reference-checked GC may call this action."""
        if isinstance(worker_rank, bool) or not isinstance(worker_rank, int) or worker_rank < 0:
            raise ValueError("invalid Native State worker rank")
        if not _SHA256_PATTERN.fullmatch(store_key):
            raise ValueError('invalid Native State store key')
        if self._tensor_store().mode == 'memory':
            self._tensor_store().delete(worker_rank, store_key)
            return {"store_key": store_key, "worker_rank": worker_rank, "deleted": True}
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
        if not _SHA256_PATTERN.fullmatch(store_key) or type(worker_rank) is not int or worker_rank < 0:
            raise ValueError('invalid Native State store key or worker rank')
        memory = self._tensor_store().mode == 'memory'
        if memory:
            payload = self._tensor_store().get(worker_rank, store_key)
        else:
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
                device=self.device, dtype=self.shift_state.dtype, copy=memory
            ),
            wkv_state=wkv_state.to(device=self.device, dtype=self.wkv_state.dtype, copy=memory),
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
        if not memory:
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
        if (not bool(torch.isfinite(snapshot.shift_state).all())
                or not bool(torch.isfinite(snapshot.wkv_state).all())):
            raise ValueError("RWKV7 native state snapshot contains nonfinite tensors")

    @staticmethod
    def _trim_native_store(rank_dir: Path) -> None:
        capacity = envs.IRWKV_RWKV7_NATIVE_STATE_STORE_CAPACITY
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
