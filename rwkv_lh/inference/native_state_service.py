# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: Copyright contributors to the vLLM project
"""Opt-in HTTP lifecycle for RWKV recurrent-state cache entries."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
from collections import OrderedDict
from dataclasses import asdict, dataclass, replace
from typing import Any
from uuid import uuid4

import vllm
from fastapi import FastAPI, HTTPException, Request
from starlette.datastructures import State
from vllm import TokensPrompt
from vllm.engine.protocol import EngineClient
from vllm.sampling_params import RequestOutputKind, SamplingParams

from rwkv_lh.inference.native_source_identity import verify_native_source_identity
from rwkv_lh.runtime.native_request_recovery import (
    NATIVE_REQUEST_RECOVERY_VERSION,
    NativeRequestConflict,
    NativeRequestInProgress,
    NativeRequestJournal,
    NativeRequestOutcomeUnknown,
    NativeRequestResult,
    NativeStateRetired,
    prepare_native_request,
)
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION, NATIVE_STATE_PROTOCOL_VERSION

PROTOCOL_VERSION = NATIVE_STATE_PROTOCOL_VERSION
EXPORT_VERSION = "rwkv-lh.native-state-export.v1"
STATE_FORMAT_VERSION = "rwkv7-native-state-cache.v1"
_SHA256_ZERO = "0" * 64


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True)
class _StateRecord:
    state_ref: str
    state_digest: str
    cache_binding_digest: str
    state_profile_id: str
    state_profile_sha256: str
    pending_token_id: int
    processed_token_count: int
    parent_state_ref: str = ""
    committed: bool = True
    export_record: dict[str, Any] | None = None
    import_origin_state_ref: str = ""
    input_token_ids: list[int] | None = None
    input_bos_token_count: int | None = None


class RWKVNativeStateService:
    """API-process metadata for worker-owned disposable state snapshots."""

    def __init__(self, engine_client: EngineClient | None, args: Any) -> None:
        self.engine_client = engine_client
        self.args = args
        self.lock = asyncio.Lock()
        self.request_lock = asyncio.Lock()
        self._active_request_id = ""
        journal_path = getattr(args, "rwkv_native_request_journal", None) or os.getenv("RWKV_NATIVE_REQUEST_JOURNAL")
        self.journal = NativeRequestJournal(journal_path) if journal_path else None
        self.records: OrderedDict[str, _StateRecord] = OrderedDict()
        self.registry_capacity = 4096
        self.ready = False
        self.error = "engine client is unavailable"
        self.model_name = ""
        self.server_build = str(getattr(vllm, "__version__", "unknown"))
        self.tokenizer_build = ""
        self.worker_capabilities: dict[str, Any] = {}
        self.source_identity: dict[str, Any] = {}
        self.gc_last_error = ""

    async def initialize(self) -> None:
        if self.engine_client is None:
            return
        try:
            self.source_identity = verify_native_source_identity(engine_file=getattr(vllm, "__file__", None))
            self.model_name = str(self.engine_client.model_config.served_model_name)
            tokenizer = self.engine_client.renderer.get_tokenizer()
            self.tokenizer_build = _digest(
                {
                    "class": f"{type(tokenizer).__module__}.{type(tokenizer).__name__}",
                    "name": str(getattr(tokenizer, "name_or_path", "")),
                    "vocab_size": int(getattr(tokenizer, "vocab_size", 0)),
                }
            )
            results = await self._collective("capabilities")
            capabilities = self._consensus(results)
            if capabilities.get("source_identity") != self.source_identity:
                raise RuntimeError("worker Native source identity differs from the verified API source identity")
            if capabilities.get("state_format_version") != STATE_FORMAT_VERSION:
                raise RuntimeError("worker state format is incompatible")
            if not capabilities.get("store_configured"):
                raise RuntimeError("worker state store is not configured")
            if self.journal is None:
                raise RuntimeError("RWKV_NATIVE_REQUEST_JOURNAL must name a persistent journal")
            if capabilities.get("store_persistent") is not True:
                raise RuntimeError("request recovery requires persistent worker state storage (capacity=0)")
            if capabilities.get("state_lifecycle_protocol") != NATIVE_STATE_LIFECYCLE_VERSION:
                raise RuntimeError("worker State lifecycle protocol is unavailable")
            self.worker_capabilities = capabilities
            self.server_build = f"{getattr(vllm, '__version__', 'unknown')}+native.{self.source_identity['identity_sha256']}"
            self.ready = True
            self.error = ""
            await self._collect_garbage()
        except Exception as exc:
            self.error = f"{type(exc).__name__}: {exc}"[:500]

    async def _collective(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        if self.engine_client is None:
            raise RuntimeError("RWKV native state requires an engine")
        results = await self.engine_client.collective_rpc(
            "rwkv_native_state_action",
            args=(action, payload or {}),
        )
        if not isinstance(results, list) or not results:
            raise RuntimeError("RWKV native state workers returned no result")
        if any(not isinstance(item, dict) for item in results):
            raise RuntimeError("RWKV native state worker result is invalid")
        return results

    @staticmethod
    def _consensus(results: list[dict[str, Any]]) -> dict[str, Any]:
        comparable = [
            {key: value for key, value in item.items() if key != "worker_rank"}
            for item in results
        ]
        if any(item != comparable[0] for item in comparable[1:]):
            raise RuntimeError("RWKV native state workers disagree")
        return comparable[0]

    def capabilities(self) -> dict[str, Any]:
        enabled = self.ready
        return {
            "schema_version": PROTOCOL_VERSION,
            "model": self.model_name,
            "prompt_replay": False,
            "tools": {"native_tool_calls": False},
            "recurrent_state": {
                "protocol": PROTOCOL_VERSION if enabled else "",
                "create": enabled,
                "resume": enabled,
                "fork": enabled,
                "commit": enabled,
                "rollback": enabled,
                "release": enabled,
                "state_lifecycle_protocol": NATIVE_STATE_LIFECYCLE_VERSION if enabled else "",
                "export": enabled,
                "import": enabled,
                "chunked_prefill": enabled,
                "full_input_token_ids": enabled,
                "request_recovery": enabled and self.journal is not None,
                "request_recovery_protocol": NATIVE_REQUEST_RECOVERY_VERSION if enabled and self.journal is not None else "",
                "authoritative": False,
                "cache_role": "disposable_acceleration",
                "state_format_version": STATE_FORMAT_VERSION,
                "pending_token_policy": "state_before_exactly_one_pending_token",
                "cache_capacity_per_worker": self.worker_capabilities.get(
                    "cache_capacity", 0
                ),
                "persistent_store": self.worker_capabilities.get("store_persistent") is True,
                "gc_pending_blobs": self.journal.gc_pending_count() if self.journal is not None else 0,
                "gc_last_error": self.gc_last_error,
            },
            "max_model_len": int(
                getattr(
                    getattr(self.engine_client, "model_config", None),
                    "max_model_len",
                    0,
                )
                or 0
            ),
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
            "error": self.error,
        }

    def _require_ready(self) -> None:
        if not self.ready:
            raise HTTPException(status_code=503, detail=self.error)

    def _validate_model(self, payload: dict[str, Any]) -> None:
        if payload.get("schema_version") != PROTOCOL_VERSION:
            raise HTTPException(status_code=400, detail="unsupported state protocol")
        if payload.get("model") != self.model_name:
            raise HTTPException(status_code=409, detail="served model mismatch")

    @staticmethod
    def _binding(payload: dict[str, Any]) -> tuple[dict[str, Any], str]:
        binding = payload.get("cache_binding")
        if not isinstance(binding, dict):
            raise HTTPException(status_code=400, detail="cache_binding is required")
        if (
            binding.get("schema_version") != "rwkv-lh.native-state-cache-binding.v1"
            or binding.get("authoritative") is not False
            or binding.get("cache_role") != "disposable_acceleration"
        ):
            raise HTTPException(status_code=400, detail="cache binding is invalid")
        return binding, _digest(binding)

    @staticmethod
    def _profile(payload: dict[str, Any], binding: dict[str, Any]) -> tuple[str, str]:
        xargs = payload.get("vllm_xargs")
        values = xargs if isinstance(xargs, dict) else {}
        requested_id = values.get("rwkv_state_profile")
        requested_sha256 = values.get("rwkv_state_profile_sha256")
        if (requested_id is None) != (requested_sha256 is None):
            raise HTTPException(status_code=400, detail="state profile is incomplete")
        profile_id = str(
            requested_id
            if requested_id is not None
            else binding.get("state_profile_id") or "zero"
        )
        profile_sha256 = str(
            requested_sha256
            if requested_sha256 is not None
            else binding.get("state_profile_sha256") or _SHA256_ZERO
        )
        if profile_id != str(
            binding.get("state_profile_id") or "zero"
        ) or profile_sha256 != str(binding.get("state_profile_sha256") or _SHA256_ZERO):
            raise HTTPException(status_code=409, detail="state profile mismatch")
        return profile_id, profile_sha256

    def _tokens(self, text: str, *, initial: bool) -> list[int]:
        assert self.engine_client is not None
        tokenizer = self.engine_client.renderer.get_tokenizer()
        token_ids = tokenizer.encode(text, add_special_tokens=initial)
        if not isinstance(token_ids, list) or any(
            not isinstance(item, int) or item < 0 for item in token_ids
        ):
            raise RuntimeError("tokenizer returned invalid token IDs")
        return token_ids

    @staticmethod
    def _new_ref() -> str:
        return f"WKV-{uuid4().hex}"

    def _remember(self, record: _StateRecord) -> None:
        self.records[record.state_ref] = record
        self.records.move_to_end(record.state_ref)
        while len(self.records) > self.registry_capacity:
            self.records.popitem(last=False)

    def _record(self, state_ref: str) -> _StateRecord:
        if self.journal is not None:
            try:
                metadata = self.journal.lookup_state_metadata(state_ref, allow_request_id=self._active_request_id)
            except NativeRequestOutcomeUnknown as exc:
                raise HTTPException(status_code=503, detail="State has an unresolved mutation") from exc
            if metadata is not None:
                if metadata.get("dropped") is True or metadata.get("released") is True:
                    self.records.pop(state_ref, None)
                    raise HTTPException(status_code=410, detail="state cache was retired")
                record = _StateRecord(**metadata)
                exported = record.export_record
                expected = {
                    "schema_version": EXPORT_VERSION, "protocol_version": PROTOCOL_VERSION,
                    "state_format_version": STATE_FORMAT_VERSION, "model": self.model_name,
                    "server_build": self.server_build, "tokenizer_build": self.tokenizer_build,
                    "state_digest": record.state_digest, "cache_binding_digest": record.cache_binding_digest,
                    "state_profile_id": record.state_profile_id, "state_profile_sha256": record.state_profile_sha256,
                    "pending_token_id": record.pending_token_id, "processed_token_count": record.processed_token_count,
                }
                if not isinstance(exported, dict) or any(exported.get(key) != value for key, value in expected.items()):
                    raise HTTPException(status_code=409, detail="durable state recovery identity mismatch")
                self._remember(record)
        record = self.records.get(state_ref)
        if record is None:
            raise HTTPException(status_code=410, detail="state cache reference expired")
        self.records.move_to_end(state_ref)
        return record

    async def _ensure_loaded(self, record: _StateRecord) -> None:
        try:
            result = self._consensus(
                await self._collective("get", {"state_ref": record.state_ref})
            )
            self._validate_worker_record(record, result)
            return
        except Exception:
            pass
        export_record = record.export_record
        if not isinstance(export_record, dict):
            raise HTTPException(status_code=410, detail="state cache entry was evicted")
        await self._import_workers(record, export_record)

    async def _recover_current_states(self, record) -> None:
        """Replay original response bytes while loading only the latest State facts."""
        assert self.journal is not None
        async with self.request_lock:
            for old in record.recovery_metadata.get("states", []):
                try:
                    latest = self.journal.lookup_state_metadata(old["state_ref"])
                except NativeRequestOutcomeUnknown as exc:
                    raise HTTPException(status_code=503, detail="State has an unresolved mutation") from exc
                if latest is not None and (latest.get("dropped") is True or latest.get("released") is True):
                    continue
                await self._ensure_loaded(self._record(old["state_ref"]))

    async def _collect_garbage(self) -> None:
        """Deletion follows durable retirement; a crash leaves a retryable queue."""
        if self.journal is None:
            return
        async with self.request_lock:
            try:
                for ref in self.journal.pending_retirements():
                    await self._collective("drop", {"state_ref": ref})
                    self.records.pop(ref, None)
                    self.journal.mark_cache_dropped(ref)
                for key in self.journal.reclaimable_store_keys():
                    # All executing operations use request_lock. Queued inputs
                    # were durably pinned before waiting for this same lock.
                    result = self._consensus(await self._collective("delete_export", {"store_key": key}))
                    if result.get("store_key") != key or result.get("deleted") is not True:
                        raise RuntimeError("worker did not confirm durable State deletion")
                    self.journal.mark_blob_deleted(key)
                self.gc_last_error = ""
            except Exception as exc:
                # The immutable operation receipt is already durable. Keep its
                # result queryable and expose deferred GC instead of resampling.
                self.gc_last_error = type(exc).__name__

    async def dispatch(self, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        if self.journal is None:
            raise HTTPException(status_code=503, detail="persistent request journal is unavailable")
        try:
            if prepare_native_request(operation, payload) != payload:
                raise ValueError("request identity is incomplete")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="invalid request recovery identity") from exc

        async def invoke():
            self._active_request_id = payload["request_id"]
            try:
                try:
                    if operation == "fork":
                        body = await self.append(payload, fork=True)
                    else:
                        method = self.import_state if operation == "import" else getattr(self, operation)
                        body = await method(payload)
                except HTTPException as exc:
                    return NativeRequestResult({"detail": exc.detail}, status_code=exc.status_code)
                if operation == "rollback":
                    metadata = {"states": [], "dropped_state_refs": [payload["candidate_state_ref"]]}
                elif operation == "release":
                    metadata = {"states": [], "released_state_refs": sorted(
                        body["released_state_refs"] + body.get("released_alias_state_refs", []))}
                else:
                    selected = body.get("candidate", body)
                    current = self.records[selected["state_ref"]]
                    if current.export_record is None:
                        raise RuntimeError("Native result has no durable State export")
                    metadata = {"states": [asdict(current)], "dropped_state_refs": []}
                return NativeRequestResult(body, recovery_metadata=metadata)
            finally:
                self._active_request_id = ""

        try:
            record = await self.journal.execute(operation, payload, invoke, execution_lock=self.request_lock)
        except NativeRequestConflict as exc:
            raise HTTPException(status_code=409, detail="request ID has a different payload") from exc
        except NativeStateRetired as exc:
            raise HTTPException(status_code=410, detail="State handle was explicitly retired") from exc
        except (NativeRequestInProgress, NativeRequestOutcomeUnknown) as exc:
            raise HTTPException(status_code=503, detail="request outcome requires result query") from exc
        if record.status_code >= 400:
            raise HTTPException(status_code=record.status_code, detail=record.body.get("detail", "Native request failed"))
        await self._collect_garbage()
        await self._recover_current_states(record)
        return dict(record.body)

    async def request_result(self, request_id: str, request_digest: str) -> dict[str, Any]:
        self._require_ready()
        if self.journal is None:
            raise HTTPException(status_code=503, detail="persistent request journal is unavailable")
        try:
            record = self.journal.lookup(request_id, request_digest)
        except NativeRequestConflict as exc:
            raise HTTPException(status_code=409, detail="request ID has a different payload") from exc
        if record is None:
            raise HTTPException(status_code=404, detail="request ID is not recorded")
        if record.status == "completed":
            await self._collect_garbage()
            await self._recover_current_states(record)
        return record.to_response()

    async def _seed(self, record: _StateRecord) -> None:
        result = self._consensus(
            await self._collective(
                "seed",
                {
                    "state_ref": record.state_ref,
                    "state_digest": record.state_digest,
                    "cache_binding_digest": record.cache_binding_digest,
                    "state_profile_id": record.state_profile_id,
                    "state_profile_sha256": record.state_profile_sha256,
                    "pending_token_id": record.pending_token_id,
                },
            )
        )
        self._validate_worker_record(record, result)

    async def _clone(self, source: _StateRecord, target: _StateRecord) -> None:
        await self._ensure_loaded(source)
        result = self._consensus(
            await self._collective(
                "clone",
                {
                    "source_ref": source.state_ref,
                    "source_digest": source.state_digest,
                    "source_cache_binding_digest": source.cache_binding_digest,
                    "target_ref": target.state_ref,
                    "target_digest": target.state_digest,
                    "target_cache_binding_digest": target.cache_binding_digest,
                },
            )
        )
        self._validate_worker_record(target, result)

    @staticmethod
    def _validate_worker_record(record: _StateRecord, result: dict[str, Any]) -> None:
        expected = {
            "state_ref": record.state_ref,
            "state_digest": record.state_digest,
            "cache_binding_digest": record.cache_binding_digest,
            "state_profile_id": record.state_profile_id,
            "state_profile_sha256": record.state_profile_sha256,
            "pending_token_id": record.pending_token_id,
            "authoritative": False,
        }
        if any(result.get(key) != value for key, value in expected.items()):
            raise RuntimeError("RWKV native state worker metadata mismatch")

    def _xargs(
        self,
        source: _StateRecord,
        target: _StateRecord,
        pending_token_id: int | None,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {
            "rwkv_state_profile": source.state_profile_id,
            "rwkv_state_profile_sha256": source.state_profile_sha256,
            "rwkv_native_state_read_ref": source.state_ref,
            "rwkv_native_state_read_digest": source.state_digest,
            "rwkv_native_state_read_binding_digest": source.cache_binding_digest,
            "rwkv_native_state_write_ref": target.state_ref,
            "rwkv_native_state_write_digest": target.state_digest,
            "rwkv_native_state_write_binding_digest": target.cache_binding_digest,
        }
        if pending_token_id is not None:
            values["rwkv_native_state_write_pending_token_id"] = pending_token_id
        return values

    async def _generate_tokens(
        self,
        *,
        source: _StateRecord,
        target: _StateRecord,
        prompt_token_ids: list[int],
        request_id: str,
        max_tokens: int,
        stop: list[str],
        sampling: dict[str, Any],
        pending_token_id: int | None,
    ) -> tuple[str, list[int], str]:
        assert self.engine_client is not None
        await self._ensure_loaded(source)
        params = SamplingParams(
            max_tokens=max_tokens,
            temperature=float(sampling.get("temperature", 0.05)),
            top_p=float(sampling.get("top_p", 1.0)),
            top_k=int(sampling.get("top_k", 0)),
            presence_penalty=float(sampling.get("presence_penalty", 0.0)),
            frequency_penalty=float(sampling.get("frequency_penalty", 0.0)),
            penalty_decay=float(sampling.get("penalty_decay", 0.996)),
            stop=stop or None,
            output_kind=RequestOutputKind.FINAL_ONLY,
            extra_args=self._xargs(source, target, pending_token_id),
        )
        final = None
        captured = None
        async for output in self.engine_client.generate(
            TokensPrompt(prompt_token_ids=prompt_token_ids),
            params,
            request_id,
        ):
            final = output
            outputs = getattr(output, "outputs", None)
            selected = outputs[0] if outputs else None
            selected_token_ids = getattr(selected, "token_ids", None)
            if (
                captured is None
                and selected_token_ids
                and getattr(selected, "finish_reason", None) is not None
            ):
                # Capture while the engine iterator is paused on its terminal
                # output.  Resuming/exhausting it may let the scheduler discard
                # the recurrent row before a following utility RPC runs,
                # especially for text-stop termination.
                captured = self._consensus(
                    await self._collective(
                        "capture",
                        {
                            "request_id": request_id,
                            "state_ref": target.state_ref,
                            "sampled_token_id": int(selected_token_ids[-1]),
                        },
                    )
                )
        if final is None or not final.outputs:
            raise RuntimeError("RWKV native generation returned no output")
        selected = final.outputs[0]
        token_ids = [int(item) for item in selected.token_ids]
        if not token_ids:
            raise RuntimeError("RWKV native generation returned no token IDs")
        result = captured
        if result is None:
            result = self._consensus(
                await self._collective(
                    "capture",
                    {
                        "request_id": request_id,
                        "state_ref": target.state_ref,
                        "sampled_token_id": token_ids[-1],
                    },
                )
            )
        actual = replace(
            target,
            pending_token_id=int(result["pending_token_id"]),
            processed_token_count=int(result["processed_token_count"]),
        )
        self._validate_worker_record(actual, result)
        return str(selected.text), token_ids, str(selected.finish_reason or "stop")

    async def _materialize_delta(
        self,
        source: _StateRecord,
        target: _StateRecord,
        delta_tokens: list[int],
    ) -> _StateRecord:
        if not delta_tokens:
            target = replace(
                target,
                pending_token_id=source.pending_token_id,
                processed_token_count=source.processed_token_count,
            )
            await self._clone(source, target)
            return target
        # Tokenize the logical delta once. Intermediate cache entries are private;
        # only the complete logical operation receives the caller's binding.
        window = int(self.engine_client.model_config.max_model_len)
        chunk_size = min(4096, window - 1)
        if chunk_size < 1:
            raise HTTPException(status_code=503, detail="no Native prefill capacity")
        current = source
        temporary_refs: set[str] = set()
        completed = False
        try:
            for offset in range(0, len(delta_tokens), chunk_size):
                chunk = delta_tokens[offset:offset + chunk_size]
                last = offset + len(chunk) == len(delta_tokens)
                step = replace(target, pending_token_id=chunk[-1])
                if not last:
                    ref = self._new_ref()
                    step = replace(
                        step, state_ref=ref,
                        state_digest=_digest({"logical_target": target.state_digest,
                                              "prefill_offset": offset}),
                        cache_binding_digest=_digest({"logical_binding": target.cache_binding_digest,
                                                       "prefill_offset": offset}),
                    )
                    temporary_refs.add(ref)
                await self._generate_tokens(
                    source=current, target=step,
                    prompt_token_ids=[current.pending_token_id, *chunk[:-1]],
                    request_id=f"native-materialize-{uuid4().hex}",
                    max_tokens=1, stop=[],
                    sampling={"temperature": 0.05, "top_k": 1},
                    pending_token_id=step.pending_token_id,
                )
                metadata = self._consensus(
                    await self._collective("get", {"state_ref": step.state_ref}))
                expected_count = current.processed_token_count + len(chunk)
                if (int(metadata["pending_token_id"]) != step.pending_token_id
                        or int(metadata["processed_token_count"]) != expected_count):
                    raise RuntimeError("RWKV native prefill boundary mismatch")
                step = replace(step, processed_token_count=expected_count)
                if current.state_ref in temporary_refs:
                    await self._collective("drop", {"state_ref": current.state_ref})
                    temporary_refs.remove(current.state_ref)
                current = step
            completed = True
            return current
        finally:
            if not completed:
                temporary_refs.add(target.state_ref)
            for ref in temporary_refs:
                await self._collective("drop", {"state_ref": ref})

    async def _export(self, record: _StateRecord) -> _StateRecord:
        store_key = record.state_digest
        results = await self._collective(
            "export",
            {"state_ref": record.state_ref, "store_key": store_key},
        )
        self._consensus(results)
        export_record = {
            "schema_version": EXPORT_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "state_format_version": STATE_FORMAT_VERSION,
            "model": self.model_name,
            "state_ref": record.state_ref,
            "state_digest": record.state_digest,
            "cache_binding_digest": record.cache_binding_digest,
            "state_profile_id": record.state_profile_id,
            "state_profile_sha256": record.state_profile_sha256,
            "pending_token_id": record.pending_token_id,
            "processed_token_count": record.processed_token_count,
            "store_key": store_key,
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
            "authoritative": False,
            "cache_role": "disposable_acceleration",
        }
        return replace(record, export_record=export_record)

    async def _import_workers(
        self, record: _StateRecord, export_record: dict[str, Any]
    ) -> None:
        result = self._consensus(
            await self._collective(
                "import",
                {
                    "state_ref": record.state_ref,
                    "state_digest": record.state_digest,
                    "cache_binding_digest": record.cache_binding_digest,
                    "state_profile_id": record.state_profile_id,
                    "state_profile_sha256": record.state_profile_sha256,
                    "pending_token_id": record.pending_token_id,
                    "processed_token_count": record.processed_token_count,
                    "store_key": export_record["store_key"],
                },
            )
        )
        self._validate_worker_record(record, result)

    def _snapshot(self, record: _StateRecord) -> dict[str, Any]:
        if record.export_record is None:
            raise RuntimeError("RWKV native state has no export record")
        return {
            "state_ref": record.state_ref,
            "state_digest": record.state_digest,
            "export_record": record.export_record,
            "state_format_version": STATE_FORMAT_VERSION,
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
            "cache_binding_digest": record.cache_binding_digest,
            "protocol_version": PROTOCOL_VERSION,
        }

    @staticmethod
    def _input_evidence(record: _StateRecord) -> dict[str, Any]:
        ids = record.input_token_ids
        if ids is None or record.input_bos_token_count is None:
            return {"prompt_token_ids_scope": "unavailable"}
        if (any(type(item) is not int or item < 0 for item in ids)
                or type(record.input_bos_token_count) is not int
                or not 0 <= record.input_bos_token_count <= len(ids)
                or len(ids) != record.processed_token_count + 1
                or not ids or ids[-1] != record.pending_token_id):
            raise RuntimeError("Native token evidence differs from the consumed worker State")
        return {"prompt_token_ids": list(ids), "prompt_token_ids_scope": "full_context",
                "input_bos_token_count": record.input_bos_token_count}

    async def create(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        binding, binding_digest = self._binding(payload)
        if binding.get("model") != self.model_name:
            raise HTTPException(status_code=409, detail="cache binding model mismatch")
        profile_id, profile_sha256 = self._profile(payload, binding)
        token_ids = self._tokens(str(payload.get("delta") or ""), initial=True)
        plain_ids = self._tokens(str(payload.get("delta") or ""), initial=False)
        bos_count = len(token_ids) - len(plain_ids)
        if bos_count < 0 or token_ids[bos_count:] != plain_ids:
            raise HTTPException(status_code=409, detail="initial token encoding has an unsupported special-token layout")
        if not token_ids:
            raise HTTPException(status_code=400, detail="initial state delta is empty")
        state_ref = self._new_ref()
        state_digest = _digest(
            {
                "protocol": PROTOCOL_VERSION,
                "model": self.model_name,
                "cache_binding_digest": binding_digest,
                "token_ids": token_ids,
            }
        )
        target = _StateRecord(
            state_ref=state_ref,
            state_digest=state_digest,
            cache_binding_digest=binding_digest,
            state_profile_id=profile_id,
            state_profile_sha256=profile_sha256,
            pending_token_id=token_ids[-1],
            processed_token_count=0,
            input_token_ids=list(token_ids),
            input_bos_token_count=bos_count,
        )
        async with self.lock:
            if len(token_ids) == 1:
                await self._seed(target)
            else:
                temporary = replace(
                    target,
                    state_ref=self._new_ref(),
                    state_digest=_digest({"temporary": state_ref}),
                    cache_binding_digest=_digest({"temporary_binding": state_ref}),
                    pending_token_id=token_ids[0],
                )
                await self._seed(temporary)
                try:
                    target = await self._materialize_delta(
                        temporary,
                        target,
                        token_ids[1:],
                    )
                finally:
                    await self._collective("drop", {"state_ref": temporary.state_ref})
            target = await self._export(target)
            self._remember(target)
            return self._snapshot(target)

    async def append(
        self, payload: dict[str, Any], *, fork: bool = False
    ) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        binding, binding_digest = self._binding(payload)
        if binding.get("model") != self.model_name:
            raise HTTPException(status_code=409, detail="cache binding model mismatch")
        profile_id, profile_sha256 = self._profile(payload, binding)
        parent = self._record(str(payload.get("parent_state_ref") or ""))
        if not parent.committed:
            raise HTTPException(status_code=409, detail="parent state is a candidate")
        if (
            profile_id != parent.state_profile_id
            or profile_sha256 != parent.state_profile_sha256
        ):
            raise HTTPException(status_code=409, detail="parent state profile mismatch")
        delta_tokens = self._tokens(str(payload.get("delta") or ""), initial=False)
        target = _StateRecord(
            state_ref=self._new_ref(),
            state_digest=_digest(
                {
                    "protocol": PROTOCOL_VERSION,
                    "model": self.model_name,
                    "cache_binding_digest": binding_digest,
                    "parent_state_digest": parent.state_digest,
                    "delta_token_ids": delta_tokens,
                    "fork": fork,
                }
            ),
            cache_binding_digest=binding_digest,
            state_profile_id=profile_id,
            state_profile_sha256=profile_sha256,
            pending_token_id=parent.pending_token_id,
            processed_token_count=parent.processed_token_count,
            parent_state_ref=parent.state_ref,
            input_token_ids=([*parent.input_token_ids, *delta_tokens]
                             if parent.input_token_ids is not None else None),
            input_bos_token_count=parent.input_bos_token_count,
        )
        async with self.lock:
            target = await self._materialize_delta(parent, target, delta_tokens)
            target = await self._export(target)
            self._remember(target)
            return self._snapshot(target)

    async def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        parent = self._record(str(payload.get("parent_state_ref") or ""))
        parent_binding = str(payload.get("parent_cache_binding_digest") or "")
        if parent_binding != parent.cache_binding_digest:
            raise HTTPException(status_code=409, detail="parent cache binding mismatch")
        request_id = str(payload.get("request_id") or uuid4().hex)
        target = _StateRecord(
            state_ref=self._new_ref(),
            state_digest=_digest(
                {
                    "protocol": PROTOCOL_VERSION,
                    "parent_state_digest": parent.state_digest,
                    "request_id": request_id,
                }
            ),
            cache_binding_digest=parent.cache_binding_digest,
            state_profile_id=parent.state_profile_id,
            state_profile_sha256=parent.state_profile_sha256,
            pending_token_id=parent.pending_token_id,
            processed_token_count=parent.processed_token_count,
            parent_state_ref=parent.state_ref,
            committed=False,
        )
        sampling = payload.get("sampling")
        stop = payload.get("stop")
        input_evidence = self._input_evidence(parent) if payload.get("return_token_ids") is True else {}
        async with self.lock:
            content, token_ids, finish_reason = await self._generate_tokens(
                source=parent,
                target=target,
                prompt_token_ids=[parent.pending_token_id],
                request_id=f"native-generate-{request_id}",
                max_tokens=max(1, int(payload.get("max_tokens") or 1)),
                stop=[str(item) for item in stop] if isinstance(stop, list) else [],
                sampling=dict(sampling) if isinstance(sampling, dict) else {},
                pending_token_id=None,
            )
            metadata = self._consensus(
                await self._collective("get", {"state_ref": target.state_ref})
            )
            target = replace(
                target,
                pending_token_id=int(metadata["pending_token_id"]),
                processed_token_count=int(metadata["processed_token_count"]),
                input_token_ids=([*parent.input_token_ids, *token_ids]
                                 if parent.input_token_ids is not None else None),
                input_bos_token_count=parent.input_bos_token_count,
            )
            target = await self._export(target)
            self._remember(target)
        return {
            "candidate": {
                "state_ref": target.state_ref,
                "state_digest": target.state_digest,
                "content": content,
                "finish_reason": finish_reason,
                "metadata": {
                    "token_ids": token_ids,
                    "response_id": request_id,
                    **input_evidence,
                },
                "parent_state_digest": parent.state_digest,
                "parent_cache_binding_digest": parent.cache_binding_digest,
            }
        }

    async def commit(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        binding, binding_digest = self._binding(payload)
        if binding.get("model") != self.model_name:
            raise HTTPException(status_code=409, detail="cache binding model mismatch")
        candidate = self._record(str(payload.get("candidate_state_ref") or ""))
        if candidate.committed:
            raise HTTPException(status_code=409, detail="state is already committed")
        if (
            str(binding.get("parent_state_digest") or "")
            != self._record(candidate.parent_state_ref).state_digest
        ):
            raise HTTPException(status_code=409, detail="candidate lineage mismatch")
        async with self.lock:
            await self._ensure_loaded(candidate)
            result = self._consensus(
                await self._collective(
                    "rebind",
                    {
                        "state_ref": candidate.state_ref,
                        "state_digest": candidate.state_digest,
                        "old_cache_binding_digest": candidate.cache_binding_digest,
                        "new_cache_binding_digest": binding_digest,
                    },
                )
            )
            candidate = replace(
                candidate,
                cache_binding_digest=binding_digest,
                committed=True,
            )
            self._validate_worker_record(candidate, result)
            candidate = await self._export(candidate)
            self._remember(candidate)
            return self._snapshot(candidate)

    async def rollback(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        candidate = self._record(str(payload.get("candidate_state_ref") or ""))
        parent_ref = str(payload.get("parent_state_ref") or "")
        if candidate.committed or candidate.parent_state_ref != parent_ref:
            raise HTTPException(status_code=409, detail="candidate lineage mismatch")
        # GPU and disk deletion happen only after this result and the tombstone
        # commit together in the journal. An uncertain result cannot lose State.
        return {"rolled_back": True, "parent_state_ref": parent_ref}

    async def release(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        if payload.get("lifecycle_protocol") != NATIVE_STATE_LIFECYCLE_VERSION:
            raise HTTPException(status_code=400, detail="unsupported State lifecycle protocol")
        states = payload.get("states")
        release_aliases = payload.get("release_import_aliases", False)
        if not isinstance(release_aliases, bool):
            raise HTTPException(status_code=400, detail="release_import_aliases must be boolean")
        if not isinstance(states, list) or not states:
            raise HTTPException(status_code=400, detail="State release requires a nonempty identity batch")
        refs = set()
        assert self.journal is not None
        for identity in states:
            if (not isinstance(identity, dict)
                    or set(identity) != {"state_ref", "state_digest", "cache_binding_digest"}
                    or not isinstance(identity["state_ref"], str)
                    or not re.fullmatch(r"WKV-[0-9a-f]{32}", identity["state_ref"])
                    or any(not isinstance(identity[key], str) or not re.fullmatch(r"[0-9a-f]{64}", identity[key])
                           for key in ("state_digest", "cache_binding_digest"))):
                raise HTTPException(status_code=400, detail="invalid State release identity")
            ref = identity["state_ref"]
            if ref in refs:
                raise HTTPException(status_code=400, detail="duplicate State release identity")
            refs.add(ref)
            try:
                current = self.journal.lookup_state_metadata(ref, allow_request_id=self._active_request_id)
            except NativeRequestOutcomeUnknown as exc:
                raise HTTPException(status_code=503, detail="State has an unresolved mutation") from exc
            if current is None:
                raise HTTPException(status_code=410, detail="State release handle is unknown")
            if any(current.get(key) != value for key, value in identity.items()):
                raise HTTPException(status_code=409, detail="State release identity mismatch")
            if current.get("committed") is not True or current.get("dropped") is True:
                raise HTTPException(status_code=409, detail="uncommitted candidates require rollback")
        alias_refs = set()
        if release_aliases:
            for alias in self.journal.import_aliases_for(refs):
                if alias.get("committed") is not True or alias.get("dropped") is True:
                    raise HTTPException(status_code=409, detail="uncommitted imported State requires rollback")
                alias_refs.add(alias["state_ref"])
        try:
            self.journal.validate_release(refs | alias_refs, allow_request_id=self._active_request_id)
        except NativeRequestConflict as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except NativeRequestOutcomeUnknown as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        body = {"released_state_refs": sorted(refs)}
        if release_aliases:
            body["released_alias_state_refs"] = sorted(alias_refs)
        return body

    async def import_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        self._require_ready()
        self._validate_model(payload)
        binding, binding_digest = self._binding(payload)
        if binding.get("model") != self.model_name:
            raise HTTPException(status_code=409, detail="cache binding model mismatch")
        export_record = payload.get("export_record")
        if not isinstance(export_record, dict):
            raise HTTPException(status_code=400, detail="export_record is required")
        # Import creates an alias, not an escape from explicit retirement.
        original_ref = export_record.get("state_ref")
        if not isinstance(original_ref, str) or not original_ref:
            raise HTTPException(status_code=400, detail="export record requires its original State handle")
        original = self._record(original_ref)
        if not original.committed:
            raise HTTPException(status_code=409, detail="only committed State exports may create import aliases")
        if original.export_record != export_record:
            raise HTTPException(status_code=409, detail="export differs from the current State identity")
        expected = {
            "schema_version": EXPORT_VERSION,
            "protocol_version": PROTOCOL_VERSION,
            "state_format_version": STATE_FORMAT_VERSION,
            "model": self.model_name,
            "cache_binding_digest": binding_digest,
            "server_build": self.server_build,
            "tokenizer_build": self.tokenizer_build,
            "authoritative": False,
            "cache_role": "disposable_acceleration",
        }
        if any(export_record.get(key) != value for key, value in expected.items()):
            raise HTTPException(status_code=409, detail="export record is incompatible")
        profile_id, profile_sha256 = self._profile(payload, binding)
        record = _StateRecord(
            state_ref=self._new_ref(),
            state_digest=str(export_record.get("state_digest") or ""),
            cache_binding_digest=binding_digest,
            state_profile_id=profile_id,
            state_profile_sha256=profile_sha256,
            pending_token_id=int(export_record.get("pending_token_id")),
            processed_token_count=int(export_record.get("processed_token_count")),
            export_record=dict(export_record),
            import_origin_state_ref=original.import_origin_state_ref or original.state_ref,
            input_token_ids=list(original.input_token_ids) if original.input_token_ids is not None else None,
            input_bos_token_count=original.input_bos_token_count,
        )
        async with self.lock:
            await self._import_workers(record, export_record)
            self._remember(record)
        return self._snapshot(record)


class RWKVNativeStateEndpointPlugin:
    """Register the explicit RWKV-LH native-state protocol under ``/v1``."""

    name = "rwkv_lh_native_state"
    required_tasks = ("generate",)

    def attach_router(self, app: FastAPI) -> None:
        @app.get("/v1/capabilities")
        async def capabilities(raw_request: Request):
            return raw_request.app.state.rwkv_native_state.capabilities()

        @app.post("/v1/state/create")
        async def create(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("create", payload)

        @app.post("/v1/state/append")
        async def append(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("append", payload)

        @app.post("/v1/state/fork")
        async def fork(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("fork", payload)

        @app.post("/v1/state/generate")
        async def generate(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("generate", payload)

        @app.post("/v1/state/commit")
        async def commit(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("commit", payload)

        @app.post("/v1/state/rollback")
        async def rollback(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("rollback", payload)

        @app.post("/v1/state/import")
        async def import_state(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("import", payload)

        @app.post("/v1/state/release")
        async def release(payload: dict[str, Any], raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.dispatch("release", payload)

        @app.get("/v1/state/requests/{request_id}")
        async def request_result(request_id: str, request_digest: str, raw_request: Request):
            return await raw_request.app.state.rwkv_native_state.request_result(request_id, request_digest)

    async def init_state(
        self,
        engine_client: EngineClient | None,
        state: State,
        args: Any,
    ) -> None:
        service = RWKVNativeStateService(engine_client, args)
        state.rwkv_native_state = service
        await service.initialize()


__all__ = ["RWKVNativeStateEndpointPlugin", "RWKVNativeStateService"]
