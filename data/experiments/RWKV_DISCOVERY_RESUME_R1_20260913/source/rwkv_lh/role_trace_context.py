"""Reconstruct consumed context from checkpoint and session audit evidence.

Native checkpoints contain deltas, including display text that can omit a
generated stop.  A historical parent of a rollover is not a consumed prefix.
This module verifies those distinctions before exposing any reconstructed text.
Locally computed IDs are explicitly separate from unrecorded server input IDs.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import JSON_CALL_STOP_SUFFIXES
from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION, NativeStateCacheBinding
from rwkv_lh.schema import ModelCheckpoint, ModelCheckpointStatus
from rwkv_lh.token_budget import VOCAB_PATH, tokenizer


class TraceContextError(ValueError):
    """The supplied trace cannot prove the requested consumed context."""

    def __init__(self, reason: str, checkpoint_id: str):
        self.reason = reason
        self.checkpoint_id = checkpoint_id
        super().__init__(f"{reason}: {checkpoint_id}")


def _fail(reason: str, checkpoint_id: str) -> None:
    raise TraceContextError(reason, checkpoint_id)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _digest(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _advance(parent: str, delta: str) -> str:
    return _sha(parent + "\0" + _sha(delta))


@lru_cache(maxsize=1)
def _tokenizer_sha() -> str:
    return hashlib.sha256(VOCAB_PATH.read_bytes()).hexdigest()


_CREATION_TYPES = {
    "model_session_bootstrapped",
    "model_session_rolled_over",
    "model_session_event_appended",
    "model_session_tool_disclosed",
    "model_session_projected_event_acknowledged",
    "model_session_forked",
    "model_session_generation_returned",
}
_RESET_TYPES = {"model_session_bootstrapped", "model_session_rolled_over"}


@dataclass(frozen=True)
class _Node:
    checkpoint: ModelCheckpoint
    index: int
    event: Mapping[str, Any]
    binding: NativeStateCacheBinding | None


def _audit_identity(event: Mapping[str, Any], checkpoint: ModelCheckpoint) -> None:
    if event.get("lane_id") != checkpoint.lane_id or event.get("state_transport") != checkpoint.transport:
        _fail("audit_identity_mismatch", checkpoint.checkpoint_id)
    if "lane_kind" in event and event["lane_kind"] != checkpoint.lane_kind.value:
        _fail("audit_lane_kind_mismatch", checkpoint.checkpoint_id)


def _identity(checkpoint: ModelCheckpoint) -> dict[str, str]:
    metadata = checkpoint.native_state_metadata or {}
    model_sha = metadata.get("model_sha256")
    if (
        not checkpoint.model or not _digest(model_sha)
        or not checkpoint.state_profile_id or not _digest(checkpoint.state_profile_sha256)
    ):
        _fail("missing_model_or_initial_state_identity", checkpoint.checkpoint_id)
    return {
        "model": checkpoint.model,
        "model_sha256": model_sha,
        "state_profile_id": checkpoint.state_profile_id,
        "state_profile_sha256": checkpoint.state_profile_sha256,
        "state_profile_delivery": str(metadata.get("state_profile_delivery") or ""),
    }


def _binding(checkpoint: ModelCheckpoint) -> NativeStateCacheBinding:
    key = checkpoint.checkpoint_id
    metadata = checkpoint.native_state_metadata or {}
    try:
        binding = NativeStateCacheBinding.from_mapping(metadata["cache_binding"])
    except (KeyError, ValueError, TypeError, AttributeError) as exc:
        raise TraceContextError("missing_or_invalid_native_binding", key) from exc
    expected = (
        checkpoint.lane_id, checkpoint.lane_kind.value, checkpoint.model,
        metadata.get("model_sha256"), checkpoint.state_profile_id,
        checkpoint.state_profile_sha256, _sha("\0".join(checkpoint.event_ids)),
        checkpoint.transcript_digest,
    )
    observed = (
        binding.lane_id, binding.lane_kind, binding.model, binding.model_sha256,
        binding.state_profile_id, binding.state_profile_sha256,
        binding.event_ids_digest, binding.delta_digest,
    )
    if expected != observed or metadata.get("cache_binding_digest") != binding.digest:
        _fail("native_binding_identity_or_digest_mismatch", key)
    if (
        metadata.get("cache_role") != "disposable_acceleration"
        or metadata.get("authoritative") is not False
        or metadata.get("protocol_version") != NATIVE_STATE_PROTOCOL_VERSION
        or not metadata.get("server_build") or not metadata.get("tokenizer_build")
        or not _digest(checkpoint.native_state_digest) or not checkpoint.native_state_ref
        or not isinstance(checkpoint.native_state_export, Mapping) or not checkpoint.native_state_export
    ):
        _fail("invalid_native_snapshot_evidence", key)
    return binding


class _Evidence:
    def __init__(self, checkpoints: Mapping[str, Any], events: Sequence[Mapping[str, Any]]):
        self.checkpoints = checkpoints
        self.created: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        self.started: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        self.committed: dict[str, list[tuple[int, Mapping[str, Any]]]] = defaultdict(list)
        self.rolled_back: set[str] = set()
        for index, event in enumerate(events):
            if not isinstance(event, Mapping):
                _fail("invalid_audit_event", "")
            kind = event.get("type")
            if kind in _CREATION_TYPES:
                field = "candidate_checkpoint_id" if kind == "model_session_generation_returned" else "checkpoint_id"
                self.created[str(event.get(field) or "")].append((index, event))
            elif kind == "model_session_generation_started":
                self.started[str(event.get("request_id") or "")].append((index, event))
            elif kind == "model_session_candidate_committed":
                self.committed[str(event.get("checkpoint_id") or "")].append((index, event))
            elif kind == "model_session_candidate_rolled_back":
                self.rolled_back.add(str(event.get("candidate_checkpoint_id") or ""))

    @staticmethod
    def unique(items: Sequence[Any], reason: str, checkpoint_id: str):
        if len(items) != 1:
            _fail(reason, checkpoint_id)
        return items[0]

    def node(self, key: str) -> _Node:
        value = self.checkpoints.get(key)
        if value is None:
            _fail("missing_checkpoint", key)
        raw = value.to_dict() if isinstance(value, ModelCheckpoint) else value
        if not isinstance(raw, Mapping):
            _fail("invalid_checkpoint_record", key)
        if (
            not isinstance(raw.get("transcript"), str)
            or not isinstance(raw.get("token_count"), int)
            or isinstance(raw.get("token_count"), bool)
            or raw.get("token_count", -1) < 0
            or raw.get("transport") not in {"native_rwkv", "prompt_replay"}
        ):
            _fail("invalid_checkpoint_fields", key)
        try:
            checkpoint = ModelCheckpoint.from_dict(raw)
        except (ValueError, TypeError) as exc:
            raise TraceContextError("invalid_checkpoint_fields", key) from exc
        if checkpoint.checkpoint_id != key or checkpoint.parent_checkpoint_id == key:
            _fail("checkpoint_key_or_cycle_mismatch", key)
        if checkpoint.status != ModelCheckpointStatus.COMMITTED or key in self.rolled_back:
            _fail("checkpoint_not_committed", key)
        if checkpoint.transcript_digest != _sha(checkpoint.transcript):
            _fail("checkpoint_transcript_digest_mismatch", key)
        if checkpoint.token_count != len(tokenizer().encode(checkpoint.transcript)):
            _fail("checkpoint_token_count_mismatch", key)
        _identity(checkpoint)
        index, event = self.unique(self.created[key], "missing_or_ambiguous_creation_audit", key)
        _audit_identity(event, checkpoint)
        for field, expected in (
            ("transcript_digest", checkpoint.transcript_digest),
            ("state_digest", checkpoint.native_state_digest),
            ("token_count", checkpoint.token_count),
            ("visible_event_ids", checkpoint.event_ids),
        ):
            if field in event and event[field] != expected:
                _fail("creation_audit_checkpoint_mismatch", key)
        binding = _binding(checkpoint) if checkpoint.transport == "native_rwkv" else None
        return _Node(checkpoint, index, event, binding)

    def generation(self, node: _Node, parent: ModelCheckpoint, parent_ready: int) -> tuple[dict[str, Any], int]:
        checkpoint = node.checkpoint
        key = checkpoint.checkpoint_id
        event = node.event
        request = event.get("request_id")
        if not isinstance(request, str) or not request:
            _fail("missing_generation_request_id", key)
        started_index, started = self.unique(self.started[request], "missing_or_ambiguous_generation_start", key)
        committed_index, committed = self.unique(self.committed[key], "missing_or_ambiguous_generation_commit", key)
        _audit_identity(started, parent)
        _audit_identity(committed, checkpoint)
        native = checkpoint.transport == "native_rwkv"
        if (
            not parent_ready < started_index < node.index < committed_index
            or started.get("input_checkpoint_id") != parent.checkpoint_id
            or started.get("input_digest") != (parent.native_state_digest if native else parent.transcript_digest)
            or event.get("candidate_digest") != (checkpoint.native_state_digest if native else checkpoint.transcript_digest)
            or committed.get("candidate_id") != event.get("candidate_id")
            or (native and committed.get("state_digest") != checkpoint.native_state_digest)
        ):
            _fail("generation_lineage_or_order_mismatch", key)
        raw = event.get("raw_generation")
        if not isinstance(raw, Mapping):
            _fail("missing_raw_generation", key)
        output = event.get("raw_output")
        expected_text = checkpoint.transcript if native else checkpoint.transcript[len(parent.transcript):]
        if (
            not isinstance(output, str) or output != expected_text
            or raw.get("raw_output") != output or raw.get("raw_output_sha256") != _sha(output)
            or raw.get("raw_output_utf8_bytes") != len(output.encode("utf-8"))
            or raw.get("request_id") != request or raw.get("candidate_id") != event.get("candidate_id")
            or raw.get("finish_reason") != event.get("finish_reason")
            or raw.get("postprocessed") is not False
            or raw.get("state_profile_id") != checkpoint.state_profile_id
            or raw.get("state_profile_sha256") != checkpoint.state_profile_sha256
            or raw.get("sampling") != started.get("sampling")
            or raw.get("max_output_tokens") != started.get("max_tokens")
            or raw.get("response_model") not in {"", checkpoint.model}
        ):
            _fail("raw_generation_identity_mismatch", key)
        token_ids = raw.get("raw_token_ids")
        if not isinstance(token_ids, (list, tuple)) or any(
            not isinstance(item, int) or isinstance(item, bool) or item < 0 for item in token_ids
        ):
            _fail("invalid_raw_generation_token_ids", key)
        consumed_text = output
        removed_suffix = ""
        if native:
            if not token_ids:
                _fail("missing_native_generation_token_ids", key)
            try:
                consumed_text = tokenizer().decode_bytes(list(token_ids)).decode("utf-8")
            except (KeyError, UnicodeError, ValueError) as exc:
                raise TraceContextError("native_generation_tokens_not_decodable", key) from exc
            if consumed_text != output:
                if not consumed_text.startswith(output):
                    _fail("native_generation_token_text_mismatch", key)
                removed_suffix = consumed_text[len(output):]
                if raw.get("finish_reason") != "stop" or not any(
                    removed_suffix.startswith(stop) for stop in JSON_CALL_STOP_SUFFIXES
                ):
                    _fail("unattested_transport_suffix", key)
        return {
            "text": consumed_text,
            "raw_output": output,
            "raw_output_sha256": raw["raw_output_sha256"],
            "raw_token_ids": list(token_ids),
            "transport_removed_suffix": removed_suffix,
            "request_id": request,
            "candidate_id": event.get("candidate_id"),
            "generation_started_index": started_index,
            "generation_committed_index": committed_index,
        }, committed_index


def reconstruct_context(
    checkpoint_id: str,
    checkpoints: Mapping[str, ModelCheckpoint | Mapping[str, Any]],
    events: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Return proven consumed text and local token reconstruction, or fail.

    ``events`` must contain the original session audit mappings in causal order,
    without merging request IDs or deduplicating distinct events.  All consumed
    checkpoints must be committed.  A rollover's archived parent is explicitly
    excluded from the physical input and need not be present for reconstruction.

    ``reconstructed_token_ids`` excludes unrecorded BOS/special input tokens.
    Native input deltas are encoded separately; generated segments keep original
    token IDs, including a proven transport-removed stop.  Prompt replay encodes
    the single complete request text.  Neither is asserted to be a recorded
    server input token stream: ``token_ids`` is None until that is collected by
    the runtime.  Unknown special output IDs are rejected rather than guessed.
    """
    evidence = _Evidence(checkpoints, events)
    reverse: list[_Node] = []
    visited: set[str] = set()
    key = checkpoint_id
    while True:
        if key in visited:
            _fail("checkpoint_cycle", key)
        visited.add(key)
        node = evidence.node(key)
        reverse.append(node)
        if node.event["type"] in _RESET_TYPES:
            break
        parent_id = node.checkpoint.parent_checkpoint_id
        if not parent_id:
            _fail("missing_checkpoint_parent", key)
        key = parent_id
    nodes = list(reversed(reverse))
    root = nodes[0].checkpoint
    initial_state = {**_identity(root), "reset_checkpoint_id": root.checkpoint_id}
    segments: list[dict[str, Any]] = []
    chain: list[dict[str, Any]] = []
    ready_index = -1
    reconstructed_ids: list[int] = []
    for position, node in enumerate(nodes):
        checkpoint = node.checkpoint
        key = checkpoint.checkpoint_id
        event = node.event
        kind = event["type"]
        parent = nodes[position - 1].checkpoint if position else None
        if _identity(checkpoint) != _identity(root) or checkpoint.transport != root.transport:
            _fail("context_model_or_state_identity_changed", key)
        if node.index <= ready_index:
            _fail("checkpoint_audit_order_mismatch", key)
        operation = kind.removeprefix("model_session_")
        segment: dict[str, Any] = {
            "checkpoint_id": key, "operation": operation, "text": checkpoint.transcript,
            "raw_token_ids": [], "transport_removed_suffix": "",
        }
        record: dict[str, Any] = {
            "checkpoint_id": key, "parent_checkpoint_id": checkpoint.parent_checkpoint_id,
            "operation": operation, "audit_index": node.index,
            "transcript_digest": checkpoint.transcript_digest,
            "state_digest": checkpoint.native_state_digest,
            "event_ids": list(checkpoint.event_ids),
        }
        if parent is None:
            if kind == "model_session_bootstrapped":
                if checkpoint.parent_checkpoint_id is not None:
                    _fail("bootstrap_has_parent", key)
                for field, value in _identity(checkpoint).items():
                    if event.get(field) != value:
                        _fail("bootstrap_initial_identity_mismatch", key)
            elif (
                not checkpoint.parent_checkpoint_id
                or event.get("source_checkpoint_id") != checkpoint.parent_checkpoint_id
                or not event.get("rollover_id") or event.get("semantic_request_count") != 0
            ):
                _fail("invalid_rollover_reset_evidence", key)
            else:
                record["discarded_parent_checkpoint_id"] = checkpoint.parent_checkpoint_id
            if node.binding and (
                node.binding.parent_state_digest
                or node.binding.state_chain_digest != _advance("", checkpoint.transcript)
            ):
                _fail("native_reset_binding_mismatch", key)
        else:
            if kind != "model_session_generation_returned" and event.get("parent_checkpoint_id") != parent.checkpoint_id:
                _fail("audit_parent_checkpoint_mismatch", key)
            if kind != "model_session_forked" and (
                checkpoint.lane_id != parent.lane_id or checkpoint.lane_kind != parent.lane_kind
            ):
                _fail("continuation_changed_lane", key)
            if root.transport == "prompt_replay":
                if not checkpoint.transcript.startswith(parent.transcript):
                    _fail("replay_continuation_prefix_mismatch", key)
                segment["text"] = checkpoint.transcript[len(parent.transcript):]
            if node.binding:
                parent_binding = nodes[position - 1].binding
                if (
                    not parent_binding or node.binding.parent_state_digest != parent.native_state_digest
                    or node.binding.state_chain_digest != _advance(parent_binding.state_chain_digest, checkpoint.transcript)
                ):
                    _fail("native_parent_or_state_chain_mismatch", key)
            if kind == "model_session_generation_returned":
                generated, committed_index = evidence.generation(node, parent, ready_index)
                segment.update(generated)
                record["generation_started_index"] = generated["generation_started_index"]
                record["generation_committed_index"] = committed_index
                ready_index = committed_index
            if kind == "model_session_projected_event_acknowledged" and segment["text"] != "":
                _fail("acknowledgement_changed_input_text", key)
            if kind in {"model_session_generation_returned", "model_session_tool_disclosed"}:
                expected_events = parent.event_ids
            else:
                # Native fork audits identify the checkpoint, whose binding
                # attests the appended event ID; they do not repeat that ID.
                if kind == "model_session_forked" and node.binding:
                    event_id = checkpoint.event_ids[-1] if checkpoint.event_ids else None
                elif kind == "model_session_forked":
                    event_id = event.get("assignment_event_id")
                else:
                    event_id = event.get("event_id")
                if not isinstance(event_id, str) or not event_id:
                    _fail("missing_appended_event_id", key)
                expected_events = parent.event_ids + [event_id]
            if checkpoint.event_ids != expected_events:
                _fail("checkpoint_event_lineage_mismatch", key)
        ready_index = max(ready_index, node.index)
        if node.binding:
            record["cache_binding_digest"] = node.binding.digest
            record["state_chain_digest"] = node.binding.state_chain_digest
            record["parent_state_digest"] = node.binding.parent_state_digest
        segment_ids = (
            segment["raw_token_ids"] if root.transport == "native_rwkv" and kind == "model_session_generation_returned"
            else tokenizer().encode(segment["text"])
        )
        segment["reconstructed_token_ids"] = list(segment_ids)
        segment["text_sha256"] = _sha(segment["text"])
        reconstructed_ids.extend(segment_ids)
        segments.append(segment)
        chain.append(record)
    prompt_text = "".join(segment["text"] for segment in segments)
    if root.transport == "prompt_replay":
        if prompt_text != nodes[-1].checkpoint.transcript:
            _fail("replay_reconstruction_mismatch", checkpoint_id)
        reconstructed_ids = tokenizer().encode(prompt_text)
    return {
        "checkpoint_id": checkpoint_id,
        "transport": root.transport,
        "prompt_text": prompt_text,
        "prompt_sha256": _sha(prompt_text),
        "initial_state": initial_state,
        "segments": segments,
        "chain_evidence": chain,
        "token_ids": None,
        "token_ids_complete": False,
        "token_ids_limitation": "server_input_token_ids_and_bos_not_recorded",
        "reconstructed_token_ids": reconstructed_ids,
        "reconstructed_token_ids_include_bos": False,
        "local_tokenizer_sha256": _tokenizer_sha(),
    }


def bind_server_input_tokens(context: Mapping[str, Any], evidence: Mapping[str, Any]) -> dict[str, Any]:
    """Bind returned full input IDs, keeping absent/delta-only evidence explicit.

    The BOS count is the frozen transport's count. BOS IDs themselves come from
    the server trace; this never prepends a guessed special token to local IDs.
    Native generation must explicitly attest full_context, since /generate has
    no prompt and a delta token list cannot describe the parent recurrent State.
    """
    result = dict(context)
    ids = evidence.get("prompt_token_ids")
    if ids is None:
        return result
    if not isinstance(ids, (list, tuple)) or any(type(token) is not int or token < 0 for token in ids):
        _fail("invalid_server_input_token_ids", str(context.get("checkpoint_id", "")))
    scope = evidence.get("prompt_token_ids_scope")
    if scope not in {"full_prompt", "full_context"} or (
        context.get("transport") == "native_rwkv" and scope != "full_context"
    ):
        result["server_reported_input_token_ids"] = list(ids)
        result["token_ids_limitation"] = "server_input_scope_is_not_full_context"
        return result
    bos_count = evidence.get("input_bos_token_count")
    if type(bos_count) is not int or bos_count < 0:
        _fail("missing_server_input_bos_count", str(context.get("checkpoint_id", "")))
    reconstructed = context["reconstructed_token_ids"]
    if len(ids) != bos_count + len(reconstructed) or list(ids[bos_count:]) != reconstructed:
        _fail("server_input_token_ids_reconstruction_mismatch", str(context.get("checkpoint_id", "")))
    result.update(token_ids=list(ids), token_ids_complete=True, token_ids_source="server_returned",
                  input_bos_token_ids=list(ids[:bos_count]), token_ids_limitation=None)
    return result


__all__ = ["TraceContextError", "reconstruct_context", "bind_server_input_tokens"]
