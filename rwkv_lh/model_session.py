"""Transactional RWKV sessions with replay and state+delta transports."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Any, Callable, Mapping, Protocol, Sequence
from uuid import uuid4

from rwkv_lh.model_io import (
    JSON_CALL_STOP_SUFFIXES,
    ModelCommand,
    ModelCommandNormalization,
    ModelIOError,
    parse_model_command,
    parse_model_command_with_trace,
    render_bootstrap,
    render_event_append,
    render_independent_executor_bootstrap,
    render_independent_executor_tool_disclosure,
    render_rollover_event_summary,
    render_tool_disclosure,
)
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.native_state import (
    NATIVE_STATE_PROTOCOL_VERSION,
    NativeRWKVStateClient,
    NativeStateCacheBinding,
    NativeStateCandidate,
    NativeStateSnapshot,
)
from rwkv_lh.runtime.sampling import (
    current_model_lane,
    current_task_id,
    sampling_parameters,
)
from rwkv_lh.runtime.settings import RuntimeSettings, get_runtime_settings
from rwkv_lh.schema import (
    ModelCheckpoint,
    ModelCheckpointStatus,
    ModelEvent,
    ModelLaneKind,
)
from rwkv_lh.token_budget import get_token_count, tokenizer


class CompletionClient(Protocol):
    def text_completion(
        self,
        prompt: str,
        max_tokens: int = 768,
        stop: Sequence[str] | None = None,
    ) -> Any: ...


class ModelSessionError(RuntimeError):
    pass


class InputBudgetError(ModelSessionError):
    pass


class NativeStateUnavailableError(ModelSessionError):
    pass


SessionAuditHook = Callable[[Mapping[str, Any]], None]


def _digest_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _digest_items(values: Sequence[str]) -> str:
    return _digest_text("\0".join(str(item) for item in values))


def _next_state_chain_digest(parent_digest: str, delta: str) -> str:
    return _digest_text(f"{parent_digest}\0{_digest_text(delta)}")


@dataclass(frozen=True)
class SessionSampling:
    temperature: float = 0.05
    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    penalty_decay: float = 0.996

    def to_dict(self) -> dict[str, Any]:
        return {
            "temperature": self.temperature,
            "top_p": self.top_p,
            "top_k": self.top_k,
            "presence_penalty": self.presence_penalty,
            "frequency_penalty": self.frequency_penalty,
            "penalty_decay": self.penalty_decay,
        }


@dataclass(frozen=True)
class CandidateGeneration:
    request_id: str
    candidate_id: str
    parent: ModelCheckpoint
    checkpoint: ModelCheckpoint
    raw_output: str
    finish_reason: str
    sampling: SessionSampling
    max_output_tokens: int
    raw_token_ids: tuple[int, ...] = ()
    response_id: str = ""
    response_model: str = ""
    state_profile_id: str = ""
    state_profile_sha256: str = ""

    @property
    def raw_output_sha256(self) -> str:
        return _digest_text(self.raw_output)

    def raw_record(self) -> dict[str, Any]:
        return {
            "schema_version": "rwkv-lh.raw-generation.v1",
            "request_id": self.request_id,
            "candidate_id": self.candidate_id,
            "raw_output": self.raw_output,
            "raw_output_sha256": self.raw_output_sha256,
            "raw_output_utf8_bytes": len(self.raw_output.encode("utf-8")),
            "raw_token_ids": list(self.raw_token_ids),
            "finish_reason": self.finish_reason,
            "response_id": self.response_id,
            "response_model": self.response_model,
            "sampling": self.sampling.to_dict(),
            "max_output_tokens": self.max_output_tokens,
            "state_profile_id": self.state_profile_id,
            "state_profile_sha256": self.state_profile_sha256,
            "postprocessed": False,
        }


def _restore_attested_stop_suffix(
    candidate: CandidateGeneration,
) -> tuple[str, tuple[str, ...]]:
    """Restore only a transport-removed fence attested by generated token IDs.

    The native server omits a matched stop string from ``content`` while keeping
    the complete generated token sequence in ``token_ids``.  Without this
    reconciliation, a fully generated fenced response is misreported as an
    unclosed Markdown fence.  Length-truncated output and unattested text remain
    unchanged.
    """

    raw = candidate.raw_output
    stripped = raw.strip()
    if (
        candidate.finish_reason != "stop"
        or not candidate.raw_token_ids
        or not stripped.startswith("```")
        or stripped.endswith("```")
    ):
        return raw, ()
    full_stream = tokenizer().decode(list(candidate.raw_token_ids))
    for stop in JSON_CALL_STOP_SUFFIXES:
        if not stop.rstrip().endswith("```") or not full_stream.endswith(stop):
            continue
        generated_without_stop = full_stream[: -len(stop)]
        if generated_without_stop.rstrip() != raw.rstrip():
            continue
        return raw.rstrip() + "\n```", (
            "transport:attested_markdown_stop_suffix_restored",
        )
    return raw, ()


class ModelSession:
    """One bounded causal lane.

    Candidate checkpoints are immutable and become visible only through
    ``commit``. This base implementation is the explicit bounded
    prompt-replay ablation; production Goal runs require
    :class:`NativeRWKVModelSession` and its recurrent state+delta transport.
    """

    transport = "prompt_replay"

    def __init__(
        self,
        client: CompletionClient | None = None,
        *,
        settings: RuntimeSettings | None = None,
        audit_hook: SessionAuditHook | None = None,
    ) -> None:
        self.settings = settings or get_runtime_settings()
        self.client = client or OpenAICompatibleRWKVClient(self.settings)
        self.audit_hook = audit_hook

    @property
    def model_name(self) -> str:
        return str(getattr(self.client, "model_name", self.settings.model))

    def _emit(self, event: Mapping[str, Any]) -> None:
        if self.audit_hook is None:
            return
        self.audit_hook(dict(event))

    def _checkpoint(
        self,
        *,
        lane_id: str,
        lane_kind: ModelLaneKind,
        parent_checkpoint_id: str | None,
        transcript: str,
        event_ids: Sequence[str],
        status: ModelCheckpointStatus,
    ) -> ModelCheckpoint:
        return ModelCheckpoint(
            checkpoint_id=f"CP-{uuid4().hex[:16]}",
            lane_id=lane_id,
            lane_kind=lane_kind,
            parent_checkpoint_id=parent_checkpoint_id,
            model=self.model_name,
            transport=self.transport,
            transcript=transcript,
            transcript_digest=_digest_text(transcript),
            token_count=get_token_count(transcript),
            event_ids=list(event_ids),
            native_state_metadata={
                "model_sha256": self.settings.model_sha256,
                "state_profile_delivery": self.settings.state_profile_delivery,
            },
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
            status=status,
        )

    def bootstrap(
        self,
        lane_kind: ModelLaneKind,
        assignment: str,
        visible_definitions: Sequence[Mapping[str, Any]],
        *,
        lane_id: str | None = None,
        event_ids: Sequence[str] = (),
        progressive_tool_disclosure: bool = False,
        independent_tool_selector: bool = False,
        native_tool_call_json: bool = False,
    ) -> ModelCheckpoint:
        identifier = lane_id or f"L-{lane_kind.value.upper()}-{uuid4().hex[:12]}"
        transcript = (
            render_independent_executor_bootstrap(assignment)
            if independent_tool_selector
            else render_bootstrap(
                visible_definitions,
                assignment,
                progressive_tool_disclosure=progressive_tool_disclosure,
                native_tool_call_json=native_tool_call_json,
            )
        )
        checkpoint = self._checkpoint(
            lane_id=identifier,
            lane_kind=lane_kind,
            parent_checkpoint_id=None,
            transcript=transcript,
            event_ids=event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        self._emit(
            {
                "type": "model_session_bootstrapped",
                "lane_id": checkpoint.lane_id,
                "lane_kind": checkpoint.lane_kind.value,
                "checkpoint_id": checkpoint.checkpoint_id,
                "transcript_digest": checkpoint.transcript_digest,
                "token_count": checkpoint.token_count,
                "visible_event_ids": list(checkpoint.event_ids),
                "state_transport": self.transport,
                "model": checkpoint.model,
                "model_sha256": self.settings.model_sha256,
                "state_profile_id": checkpoint.state_profile_id,
                "state_profile_sha256": checkpoint.state_profile_sha256,
                "state_profile_delivery": self.settings.state_profile_delivery,
                "tool_disclosure_mode": (
                    "independent_selector_executor"
                    if independent_tool_selector
                    else ("progressive" if progressive_tool_disclosure else "full")
                ),
                "generation_anchor": (
                    "native_tool_call_json"
                    if native_tool_call_json
                    else "assistant_json"
                ),
            }
        )
        return checkpoint

    def disclose_tool(
        self,
        checkpoint: ModelCheckpoint,
        definition: Mapping[str, Any],
        *,
        current_requirement: str | None = None,
        rendered_prompt: str | None = None,
    ) -> ModelCheckpoint:
        """Append exactly one selected contract outside the system message."""

        self._require_committed(checkpoint)
        if rendered_prompt is not None and current_requirement is not None:
            raise ValueError("pass rendered_prompt or current_requirement, not both")
        disclosure = (
            str(rendered_prompt)
            if rendered_prompt is not None
            else render_independent_executor_tool_disclosure(
                definition,
                current_requirement,
            )
            if current_requirement is not None
            else render_tool_disclosure(definition)
        )
        transcript = checkpoint.transcript + disclosure
        disclosed = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=transcript,
            event_ids=checkpoint.event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        self._emit(
            {
                "type": "model_session_tool_disclosed",
                "lane_id": disclosed.lane_id,
                "operation": str(definition.get("name") or ""),
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": disclosed.checkpoint_id,
                "new_tokens": disclosed.token_count - checkpoint.token_count,
                "token_count": disclosed.token_count,
                "system_tool_definition": False,
                "request_last_closed_payload": (
                    current_requirement is not None or rendered_prompt is not None
                ),
                "goal_state_protocol": (
                    "executor-args-v1" if rendered_prompt is not None else ""
                ),
                "state_transport": self.transport,
            }
        )
        return disclosed

    def append(
        self,
        checkpoint: ModelCheckpoint,
        event: ModelEvent,
        visible_definitions: Sequence[Mapping[str, Any]] = (),
        *,
        progressive_tool_disclosure: bool = False,
        independent_executor_retry_operation: str = "",
        include_generation_anchor: bool = True,
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        transcript = checkpoint.transcript + render_event_append(
            event,
            visible_definitions,
            progressive_tool_disclosure=progressive_tool_disclosure,
            independent_executor_retry_operation=(
                independent_executor_retry_operation
            ),
            include_generation_anchor=include_generation_anchor,
        )
        appended = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=transcript,
            event_ids=(*checkpoint.event_ids, event.event_id),
            status=ModelCheckpointStatus.COMMITTED,
        )
        self._emit(
            {
                "type": "model_session_event_appended",
                "lane_id": appended.lane_id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "event_error_type": str(
                    (
                        event.payload.get("error_record")
                        if isinstance(event.payload.get("error_record"), Mapping)
                        else {}
                    ).get("type")
                    or ""
                ),
                "event_selected_operation": str(
                    event.payload.get("selected_operation") or ""
                ),
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": appended.checkpoint_id,
                "new_event_tokens": appended.token_count - checkpoint.token_count,
                "token_count": appended.token_count,
                "state_transport": self.transport,
            }
        )
        return appended

    def acknowledge_projected_event(
        self,
        checkpoint: ModelCheckpoint,
        event: ModelEvent,
    ) -> ModelCheckpoint:
        """Bind an event ID already represented in a deterministic assignment.

        No text is appended: callers must first verify that the current transcript
        contains the event's authoritative state projection.
        """

        self._require_committed(checkpoint)
        if event.event_id in checkpoint.event_ids:
            raise ModelSessionError(f"event already visible: {event.event_id}")
        projected = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=checkpoint.transcript,
            event_ids=(*checkpoint.event_ids, event.event_id),
            status=ModelCheckpointStatus.COMMITTED,
        )
        self._emit(
            {
                "type": "model_session_projected_event_acknowledged",
                "lane_id": projected.lane_id,
                "event_id": event.event_id,
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": projected.checkpoint_id,
                "new_event_tokens": 0,
                "state_transport": self.transport,
            }
        )
        return projected

    def rollover(
        self,
        checkpoint: ModelCheckpoint,
        assignment: str,
        visible_definitions: Sequence[Mapping[str, Any]],
        *,
        events: Sequence[ModelEvent],
        input_limit: int,
        rollover_id: str,
        progressive_tool_disclosure: bool = False,
        independent_tool_selector: bool = False,
    ) -> ModelCheckpoint:
        """Replace one oversized replay head with a deterministic compact head.

        The source checkpoint is immutable and remains the exact archive.  This
        method performs no generation and accepts only runtime-produced bytes.
        """

        self._require_committed(checkpoint)
        if not str(rollover_id or "").strip():
            raise ModelSessionError("rollover requires a stable rollover id")
        limit = max(1, int(input_limit))
        selected_events = tuple(events)
        transcript = (
            render_independent_executor_bootstrap(assignment)
            if independent_tool_selector
            else render_bootstrap(
                visible_definitions,
                assignment,
                progressive_tool_disclosure=progressive_tool_disclosure,
            )
        ) + render_rollover_event_summary(
            selected_events,
            include_generation_anchor=not independent_tool_selector,
        )
        event_ids = tuple(event.event_id for event in selected_events)
        compact = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=transcript,
            event_ids=event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        if compact.token_count > limit:
            raise InputBudgetError(
                f"lane {checkpoint.lane_id} minimal rollover uses "
                f"{compact.token_count} input tokens; limit is {limit}"
            )
        self._emit(
            {
                "type": "model_session_rolled_over",
                "rollover_id": rollover_id,
                "lane_id": compact.lane_id,
                "lane_kind": compact.lane_kind.value,
                "source_checkpoint_id": checkpoint.checkpoint_id,
                "source_digest": checkpoint.transcript_digest,
                "source_token_count": checkpoint.token_count,
                "checkpoint_id": compact.checkpoint_id,
                "transcript_digest": compact.transcript_digest,
                "token_count": compact.token_count,
                "visible_event_ids": list(compact.event_ids),
                "semantic_request_count": 0,
                "state_transport": self.transport,
                "tool_disclosure_mode": (
                    "independent_selector_executor"
                    if independent_tool_selector
                    else ("progressive" if progressive_tool_disclosure else "full")
                ),
            }
        )
        return compact

    def fork(
        self,
        checkpoint: ModelCheckpoint,
        lane_kind: ModelLaneKind,
        assignment: ModelEvent,
        *,
        lane_id: str | None = None,
        visible_definitions: Sequence[Mapping[str, Any]] = (),
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        identifier = lane_id or f"L-{lane_kind.value.upper()}-{uuid4().hex[:12]}"
        transcript = checkpoint.transcript + render_event_append(
            assignment, visible_definitions
        )
        child = self._checkpoint(
            lane_id=identifier,
            lane_kind=lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=transcript,
            event_ids=(*checkpoint.event_ids, assignment.event_id),
            status=ModelCheckpointStatus.COMMITTED,
        )
        self._emit(
            {
                "type": "model_session_forked",
                "lane_id": child.lane_id,
                "lane_kind": child.lane_kind.value,
                "parent_lane_id": checkpoint.lane_id,
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": child.checkpoint_id,
                "assignment_event_id": assignment.event_id,
                "state_transport": self.transport,
            }
        )
        return child

    def generate(
        self,
        checkpoint: ModelCheckpoint,
        *,
        sampling: SessionSampling | None = None,
        max_output_tokens: int = 900,
        json_output: bool = True,
    ) -> CandidateGeneration:
        self._require_committed(checkpoint)
        selected = sampling or SessionSampling()
        output_limit = max(1, int(max_output_tokens))
        input_limit = self.settings.max_prompt_tokens(output_limit)
        if checkpoint.token_count > input_limit:
            raise InputBudgetError(
                f"lane {checkpoint.lane_id} uses {checkpoint.token_count} input tokens; "
                f"limit is {input_limit} with max_output_tokens={output_limit}"
            )
        request_id = f"MR-{uuid4().hex[:16]}"
        self._emit(
            {
                "type": "model_session_generation_started",
                "request_id": request_id,
                "lane_id": checkpoint.lane_id,
                "lane_kind": checkpoint.lane_kind.value,
                "input_checkpoint_id": checkpoint.checkpoint_id,
                "input_digest": checkpoint.transcript_digest,
                "prompt_tokens_local": checkpoint.token_count,
                "static_replay_tokens": checkpoint.token_count,
                "max_tokens": output_limit,
                "sampling": selected.to_dict(),
                "state_transport": self.transport,
            }
        )
        task_token = current_task_id.set(checkpoint.lane_id)
        lane_token = current_model_lane.set(f"{checkpoint.lane_kind.value}_lane")
        try:
            with sampling_parameters(
                selected.temperature,
                request_id=request_id,
                top_p=selected.top_p,
                top_k=selected.top_k,
                presence_penalty=selected.presence_penalty,
                frequency_penalty=selected.frequency_penalty,
                penalty_decay=selected.penalty_decay,
            ):
                response = self.client.text_completion(
                    checkpoint.transcript,
                    max_tokens=output_limit,
                    stop=JSON_CALL_STOP_SUFFIXES if json_output else None,
                )
        finally:
            current_model_lane.reset(lane_token)
            current_task_id.reset(task_token)
        response_content = getattr(response, "content", response)
        if response_content is None:
            raw = ""
        elif not isinstance(response_content, str):
            raise ModelSessionError("model response content must be a string")
        else:
            raw = response_content
        finish_reason = str(getattr(response, "finish_reason", "") or "")
        response_metadata = getattr(response, "metadata", {})
        raw_token_ids = (
            tuple(int(item) for item in response_metadata.get("token_ids", ()))
            if isinstance(response_metadata, Mapping)
            else ()
        )
        candidate_checkpoint = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=checkpoint.transcript + raw,
            event_ids=checkpoint.event_ids,
            status=ModelCheckpointStatus.CANDIDATE,
        )
        candidate = CandidateGeneration(
            request_id=request_id,
            candidate_id=f"CAND-{uuid4().hex[:16]}",
            parent=checkpoint,
            checkpoint=candidate_checkpoint,
            raw_output=raw,
            finish_reason=finish_reason,
            sampling=selected,
            max_output_tokens=output_limit,
            raw_token_ids=raw_token_ids,
            response_id=str(getattr(response, "response_id", "") or ""),
            response_model=str(getattr(response, "model", "") or ""),
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
        )
        self._emit(
            {
                "type": "model_session_generation_returned",
                "request_id": request_id,
                "lane_id": checkpoint.lane_id,
                "candidate_id": candidate.candidate_id,
                "candidate_checkpoint_id": candidate.checkpoint.checkpoint_id,
                "candidate_digest": candidate.checkpoint.transcript_digest,
                "raw_output": raw,
                "raw_generation": candidate.raw_record(),
                "finish_reason": finish_reason,
                "state_transport": self.transport,
            }
        )
        return candidate

    def parse(self, candidate: CandidateGeneration) -> ModelCommand:
        parse_source, _ = _restore_attested_stop_suffix(candidate)
        return parse_model_command(parse_source)

    def parse_with_trace(
        self,
        candidate: CandidateGeneration,
    ) -> tuple[ModelCommand, ModelCommandNormalization]:
        parse_source, transport_transformations = _restore_attested_stop_suffix(
            candidate
        )
        command, normalization = parse_model_command_with_trace(parse_source)
        if transport_transformations:
            normalization = replace(
                normalization,
                transformations=(
                    *transport_transformations,
                    *normalization.transformations,
                ),
            )
        if normalization.changed:
            self._emit(
                {
                    "type": "model_protocol_normalized",
                    "request_id": candidate.request_id,
                    "candidate_id": candidate.candidate_id,
                    "lane_id": candidate.parent.lane_id,
                    "lane_kind": candidate.parent.lane_kind.value,
                    "request_type": f"{candidate.parent.lane_kind.value}_lane",
                    "field": "model_output",
                    "normalization": normalization.transformations[0],
                    "raw_output": candidate.raw_output,
                    **normalization.to_dict(),
                }
            )
        return command, normalization

    def commit(
        self,
        candidate: CandidateGeneration,
        command: ModelCommand,
    ) -> ModelCheckpoint:
        self._require_committed(candidate.parent)
        if candidate.checkpoint.status != ModelCheckpointStatus.CANDIDATE:
            raise ModelSessionError("only a candidate checkpoint can be committed")
        self._require_checkpoint_identity(candidate.checkpoint)
        if self.parse(candidate) != command:
            raise ModelIOError("accepted command differs from candidate output")
        committed = ModelCheckpoint(
            **{
                **candidate.checkpoint.to_dict(),
                "lane_kind": candidate.checkpoint.lane_kind,
                "status": ModelCheckpointStatus.COMMITTED,
            }
        )
        self._emit(
            {
                "type": "model_session_candidate_committed",
                "lane_id": committed.lane_id,
                "candidate_id": candidate.candidate_id,
                "checkpoint_id": committed.checkpoint_id,
                "command_digest": command.digest,
                "state_transport": self.transport,
            }
        )
        return committed

    def rollback(
        self, candidate: CandidateGeneration, *, error: str = ""
    ) -> ModelCheckpoint:
        self._require_committed(candidate.parent)
        self._require_checkpoint_identity(candidate.checkpoint)
        self._emit(
            {
                "type": "model_session_candidate_rolled_back",
                "lane_id": candidate.parent.lane_id,
                "candidate_id": candidate.candidate_id,
                "candidate_checkpoint_id": candidate.checkpoint.checkpoint_id,
                "restored_checkpoint_id": candidate.parent.checkpoint_id,
                "error": str(error)[:2000],
                "state_transport": self.transport,
            }
        )
        return candidate.parent

    def export(self, checkpoint: ModelCheckpoint) -> dict[str, Any]:
        self._require_committed(checkpoint)
        return checkpoint.to_dict()

    def import_checkpoint(self, value: Mapping[str, Any]) -> ModelCheckpoint:
        checkpoint = ModelCheckpoint.from_dict(value)
        self._require_committed(checkpoint)
        if checkpoint.transport != self.transport:
            raise ModelSessionError(
                f"cannot import {checkpoint.transport} into {self.transport} session"
            )
        if _digest_text(checkpoint.transcript) != checkpoint.transcript_digest:
            raise ModelSessionError("checkpoint transcript digest mismatch")
        if get_token_count(checkpoint.transcript) != checkpoint.token_count:
            raise ModelSessionError("checkpoint token count mismatch")
        return checkpoint

    def _require_committed(self, checkpoint: ModelCheckpoint) -> None:
        if checkpoint.status != ModelCheckpointStatus.COMMITTED:
            raise ModelSessionError("operation requires a committed checkpoint")
        self._require_checkpoint_identity(checkpoint)

    def _require_checkpoint_identity(self, checkpoint: ModelCheckpoint) -> None:
        if checkpoint.transport != self.transport:
            raise ModelSessionError(
                f"checkpoint transport {checkpoint.transport!r} does not match "
                f"session transport {self.transport!r}"
            )
        if checkpoint.model != self.model_name:
            raise ModelSessionError(
                f"checkpoint model {checkpoint.model!r} does not match "
                f"session model {self.model_name!r}"
            )
        expected_profile = (
            self.settings.state_profile_id,
            self.settings.state_profile_sha256,
        )
        observed_profile = (
            checkpoint.state_profile_id,
            checkpoint.state_profile_sha256,
        )
        if observed_profile != expected_profile:
            raise ModelSessionError(
                "checkpoint state profile differs from the immutable session profile"
            )
        metadata = checkpoint.native_state_metadata or {}
        if str(metadata.get("model_sha256") or "") != self.settings.model_sha256:
            raise ModelSessionError(
                "checkpoint base-model SHA-256 differs from the session model"
            )
        if (
            str(metadata.get("state_profile_delivery") or "")
            != self.settings.state_profile_delivery
        ):
            raise ModelSessionError(
                "checkpoint state-profile delivery differs from the session delivery"
            )


class NativeRWKVModelSession(ModelSession):
    """Transactional state+delta session over disposable verified WKV caches."""

    transport = "native_rwkv"

    def __init__(
        self,
        client: NativeRWKVStateClient,
        *,
        settings: RuntimeSettings | None = None,
        audit_hook: SessionAuditHook | None = None,
    ) -> None:
        capabilities = client.capabilities()
        if not capabilities.durable_recurrent_state:
            raise NativeStateUnavailableError(
                "native state requires declared create/resume/fork/commit/rollback/export/import"
            )
        if capabilities.recurrent_state_protocol != NATIVE_STATE_PROTOCOL_VERSION:
            raise NativeStateUnavailableError(
                "native state server did not attest the required cache-binding protocol"
            )
        super().__init__(client, settings=settings, audit_hook=audit_hook)  # type: ignore[arg-type]
        self.native_client = client
        self.capabilities = capabilities

    def _cache_binding(
        self,
        checkpoint: ModelCheckpoint,
        *,
        state_chain_digest: str,
        delta: str,
        parent_state_digest: str = "",
    ) -> NativeStateCacheBinding:
        return NativeStateCacheBinding(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind.value,
            model=checkpoint.model,
            model_sha256=self.settings.model_sha256,
            state_profile_id=checkpoint.state_profile_id,
            state_profile_sha256=checkpoint.state_profile_sha256,
            state_chain_digest=state_chain_digest,
            delta_digest=_digest_text(delta),
            event_ids_digest=_digest_items(checkpoint.event_ids),
            parent_state_digest=parent_state_digest,
        )

    @staticmethod
    def _bind_snapshot(
        checkpoint: ModelCheckpoint,
        snapshot: NativeStateSnapshot,
        cache_binding: NativeStateCacheBinding,
    ) -> ModelCheckpoint:
        if snapshot.cache_binding_digest != cache_binding.digest:
            raise ModelSessionError("native state cache binding mismatch")
        checkpoint.native_state_ref = snapshot.state_ref
        checkpoint.native_state_digest = snapshot.state_digest
        checkpoint.native_state_export = dict(snapshot.export_record)
        checkpoint.native_state_metadata = {
            **dict(checkpoint.native_state_metadata or {}),
            "protocol_version": snapshot.protocol_version,
            "state_format_version": snapshot.state_format_version,
            "server_build": snapshot.server_build,
            "tokenizer_build": snapshot.tokenizer_build,
            "cache_role": "disposable_acceleration",
            "authoritative": False,
            "cache_binding": cache_binding.to_dict(),
            "cache_binding_digest": cache_binding.digest,
        }
        return checkpoint

    def _binding_from_checkpoint(
        self,
        checkpoint: ModelCheckpoint,
    ) -> NativeStateCacheBinding:
        metadata = checkpoint.native_state_metadata or {}
        raw = metadata.get("cache_binding")
        if not isinstance(raw, Mapping):
            raise ModelSessionError("native checkpoint has no cache binding")
        binding = NativeStateCacheBinding.from_mapping(raw)
        if metadata.get("cache_role") != "disposable_acceleration":
            raise ModelSessionError("native checkpoint cache role is invalid")
        if metadata.get("authoritative") is not False:
            raise ModelSessionError("native WKV state cannot be authoritative")
        if str(metadata.get("cache_binding_digest") or "") != binding.digest:
            raise ModelSessionError("native checkpoint cache binding digest mismatch")
        expected = (
            checkpoint.lane_id,
            checkpoint.lane_kind.value,
            checkpoint.model,
            checkpoint.state_profile_id,
            checkpoint.state_profile_sha256,
            _digest_items(checkpoint.event_ids),
        )
        observed = (
            binding.lane_id,
            binding.lane_kind,
            binding.model,
            binding.state_profile_id,
            binding.state_profile_sha256,
            binding.event_ids_digest,
        )
        if observed != expected:
            raise ModelSessionError("native checkpoint cache identity mismatch")
        if binding.delta_digest != checkpoint.transcript_digest:
            raise ModelSessionError("native checkpoint delta window digest mismatch")
        return binding

    def _require_checkpoint_identity(self, checkpoint: ModelCheckpoint) -> None:
        super()._require_checkpoint_identity(checkpoint)
        self._binding_from_checkpoint(checkpoint)

    @staticmethod
    def _state_ref(checkpoint: ModelCheckpoint) -> str:
        value = str(checkpoint.native_state_ref or "")
        if not value or not checkpoint.native_state_digest:
            raise ModelSessionError("native checkpoint has no state ref or digest")
        return value

    def bootstrap(
        self,
        lane_kind: ModelLaneKind,
        assignment: str,
        visible_definitions: Sequence[Mapping[str, Any]],
        *,
        lane_id: str | None = None,
        event_ids: Sequence[str] = (),
        progressive_tool_disclosure: bool = False,
        independent_tool_selector: bool = False,
        native_tool_call_json: bool = False,
    ) -> ModelCheckpoint:
        identifier = lane_id or f"L-{lane_kind.value.upper()}-{uuid4().hex[:12]}"
        transcript = (
            render_independent_executor_bootstrap(assignment)
            if independent_tool_selector
            else render_bootstrap(
                visible_definitions,
                assignment,
                progressive_tool_disclosure=progressive_tool_disclosure,
                native_tool_call_json=native_tool_call_json,
            )
        )
        checkpoint = self._checkpoint(
            lane_id=identifier,
            lane_kind=lane_kind,
            parent_checkpoint_id=None,
            transcript=transcript,
            event_ids=event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        if checkpoint.token_count > self.settings.max_prompt_tokens(1):
            raise InputBudgetError("native RWKV bootstrap exceeds the 16K input boundary")
        binding = self._cache_binding(
            checkpoint,
            state_chain_digest=_next_state_chain_digest("", transcript),
            delta=transcript,
        )
        snapshot = self.native_client.state_create(
            lane_id=identifier,
            text=transcript,
            cache_binding=binding,
        )
        checkpoint = self._bind_snapshot(checkpoint, snapshot, binding)
        self._emit(
            {
                "type": "model_session_bootstrapped",
                "lane_id": identifier,
                "lane_kind": lane_kind.value,
                "checkpoint_id": checkpoint.checkpoint_id,
                "state_digest": snapshot.state_digest,
                "token_count": checkpoint.token_count,
                "visible_event_ids": list(event_ids),
                "state_transport": self.transport,
                "static_replay_tokens": 0,
                "model": checkpoint.model,
                "model_sha256": self.settings.model_sha256,
                "state_profile_id": checkpoint.state_profile_id,
                "state_profile_sha256": checkpoint.state_profile_sha256,
                "state_profile_delivery": self.settings.state_profile_delivery,
                "generation_anchor": (
                    "native_tool_call_json"
                    if native_tool_call_json
                    else "assistant_json"
                ),
            }
        )
        return checkpoint

    def _append_text(
        self,
        checkpoint: ModelCheckpoint,
        suffix: str,
        *,
        event_ids: Sequence[str],
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        if get_token_count(suffix) > self.settings.max_prompt_tokens(1):
            raise InputBudgetError("native RWKV continuation delta exceeds 16K")
        parent_binding = self._binding_from_checkpoint(checkpoint)
        appended = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=suffix,
            event_ids=event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        binding = self._cache_binding(
            appended,
            state_chain_digest=_next_state_chain_digest(
                parent_binding.state_chain_digest,
                suffix,
            ),
            delta=suffix,
            parent_state_digest=str(checkpoint.native_state_digest or ""),
        )
        snapshot = self.native_client.state_append(
            parent_state_ref=self._state_ref(checkpoint),
            lane_id=checkpoint.lane_id,
            text=suffix,
            cache_binding=binding,
        )
        return self._bind_snapshot(appended, snapshot, binding)

    def disclose_tool(
        self,
        checkpoint: ModelCheckpoint,
        definition: Mapping[str, Any],
        *,
        current_requirement: str | None = None,
        rendered_prompt: str | None = None,
    ) -> ModelCheckpoint:
        if rendered_prompt is not None and current_requirement is not None:
            raise ValueError("pass rendered_prompt or current_requirement, not both")
        disclosure = (
            str(rendered_prompt)
            if rendered_prompt is not None
            else render_independent_executor_tool_disclosure(
                definition,
                current_requirement,
            )
            if current_requirement is not None
            else render_tool_disclosure(definition)
        )
        disclosed = self._append_text(
            checkpoint,
            disclosure,
            event_ids=checkpoint.event_ids,
        )
        self._emit(
            {
                "type": "model_session_tool_disclosed",
                "lane_id": disclosed.lane_id,
                "operation": str(definition.get("name") or ""),
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": disclosed.checkpoint_id,
                "new_tokens": get_token_count(disclosure),
                "request_last_closed_payload": (
                    current_requirement is not None or rendered_prompt is not None
                ),
                "goal_state_protocol": (
                    "executor-args-v1" if rendered_prompt is not None else ""
                ),
                "state_transport": self.transport,
            }
        )
        return disclosed

    def append(
        self,
        checkpoint: ModelCheckpoint,
        event: ModelEvent,
        visible_definitions: Sequence[Mapping[str, Any]] = (),
        *,
        progressive_tool_disclosure: bool = False,
        independent_executor_retry_operation: str = "",
        include_generation_anchor: bool = True,
    ) -> ModelCheckpoint:
        suffix = render_event_append(
            event,
            visible_definitions,
            progressive_tool_disclosure=progressive_tool_disclosure,
            independent_executor_retry_operation=(
                independent_executor_retry_operation
            ),
            include_generation_anchor=include_generation_anchor,
        )
        appended = self._append_text(
            checkpoint,
            suffix,
            event_ids=(*checkpoint.event_ids, event.event_id),
        )
        self._emit(
            {
                "type": "model_session_event_appended",
                "lane_id": appended.lane_id,
                "event_id": event.event_id,
                "event_type": event.event_type,
                "event_error_type": str(
                    (
                        event.payload.get("error_record")
                        if isinstance(event.payload.get("error_record"), Mapping)
                        else {}
                    ).get("type")
                    or ""
                ),
                "event_selected_operation": str(
                    event.payload.get("selected_operation") or ""
                ),
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": appended.checkpoint_id,
                "new_event_tokens": get_token_count(suffix),
                "state_transport": self.transport,
                "static_replay_tokens": 0,
            }
        )
        return appended

    def acknowledge_projected_event(
        self,
        checkpoint: ModelCheckpoint,
        event: ModelEvent,
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        if event.event_id in checkpoint.event_ids:
            raise ModelSessionError(f"event already visible: {event.event_id}")
        # The event bytes were already included in a deterministic projection.
        # Append an empty delta so the cache service can attest a new binding for
        # the enlarged authoritative event-ID set without replaying any prompt.
        projected = self._append_text(
            checkpoint,
            "",
            event_ids=(*checkpoint.event_ids, event.event_id),
        )
        self._emit(
            {
                "type": "model_session_projected_event_acknowledged",
                "lane_id": projected.lane_id,
                "event_id": event.event_id,
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": projected.checkpoint_id,
                "new_event_tokens": 0,
                "static_replay_tokens": 0,
                "state_transport": self.transport,
            }
        )
        return projected

    def rollover(
        self,
        checkpoint: ModelCheckpoint,
        assignment: str,
        visible_definitions: Sequence[Mapping[str, Any]],
        *,
        events: Sequence[ModelEvent],
        input_limit: int,
        rollover_id: str,
        progressive_tool_disclosure: bool = False,
        independent_tool_selector: bool = False,
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        selected_events = tuple(events)
        transcript = (
            render_independent_executor_bootstrap(assignment)
            if independent_tool_selector
            else render_bootstrap(
                visible_definitions,
                assignment,
                progressive_tool_disclosure=progressive_tool_disclosure,
            )
        ) + render_rollover_event_summary(
            selected_events,
            include_generation_anchor=not independent_tool_selector,
        )
        event_ids = tuple(event.event_id for event in selected_events)
        if get_token_count(transcript) > max(1, int(input_limit)):
            raise InputBudgetError("minimal native rollover exceeds the input limit")
        compact = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=transcript,
            event_ids=event_ids,
            status=ModelCheckpointStatus.COMMITTED,
        )
        binding = self._cache_binding(
            compact,
            state_chain_digest=_next_state_chain_digest("", transcript),
            delta=transcript,
        )
        snapshot = self.native_client.state_create(
            lane_id=checkpoint.lane_id,
            text=transcript,
            cache_binding=binding,
        )
        compact = self._bind_snapshot(compact, snapshot, binding)
        self._emit(
            {
                "type": "model_session_rolled_over",
                "rollover_id": rollover_id,
                "lane_id": compact.lane_id,
                "source_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": compact.checkpoint_id,
                "visible_event_ids": list(compact.event_ids),
                "state_transport": self.transport,
                "semantic_request_count": 0,
            }
        )
        return compact

    def fork(
        self,
        checkpoint: ModelCheckpoint,
        lane_kind: ModelLaneKind,
        assignment: ModelEvent,
        *,
        lane_id: str | None = None,
        visible_definitions: Sequence[Mapping[str, Any]] = (),
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        identifier = lane_id or f"L-{lane_kind.value.upper()}-{uuid4().hex[:12]}"
        suffix = render_event_append(assignment, visible_definitions)
        parent_binding = self._binding_from_checkpoint(checkpoint)
        child = self._checkpoint(
            lane_id=identifier,
            lane_kind=lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=suffix,
            event_ids=(*checkpoint.event_ids, assignment.event_id),
            status=ModelCheckpointStatus.COMMITTED,
        )
        binding = self._cache_binding(
            child,
            state_chain_digest=_next_state_chain_digest(
                parent_binding.state_chain_digest,
                suffix,
            ),
            delta=suffix,
            parent_state_digest=str(checkpoint.native_state_digest or ""),
        )
        snapshot = self.native_client.state_fork(
            parent_state_ref=self._state_ref(checkpoint),
            lane_id=identifier,
            text=suffix,
            cache_binding=binding,
        )
        child = self._bind_snapshot(
            child,
            snapshot,
            binding,
        )
        self._emit(
            {
                "type": "model_session_forked",
                "lane_id": identifier,
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": child.checkpoint_id,
                "state_transport": self.transport,
            }
        )
        return child

    def generate(
        self,
        checkpoint: ModelCheckpoint,
        *,
        sampling: SessionSampling | None = None,
        max_output_tokens: int = 900,
        json_output: bool = True,
    ) -> CandidateGeneration:
        self._require_committed(checkpoint)
        selected = sampling or SessionSampling()
        output_limit = max(1, int(max_output_tokens))
        request_id = f"MR-{uuid4().hex[:16]}"
        self._emit(
            {
                "type": "model_session_generation_started",
                "request_id": request_id,
                "lane_id": checkpoint.lane_id,
                "input_checkpoint_id": checkpoint.checkpoint_id,
                "input_digest": checkpoint.native_state_digest,
                "prompt_tokens_local": 0,
                "static_replay_tokens": 0,
                "max_tokens": output_limit,
                "sampling": selected.to_dict(),
                "state_transport": self.transport,
            }
        )
        task_token = current_task_id.set(checkpoint.lane_id)
        lane_token = current_model_lane.set(f"{checkpoint.lane_kind.value}_lane")
        try:
            parent_binding = self._binding_from_checkpoint(checkpoint)
            returned = self.native_client.state_generate(
                parent_state_ref=self._state_ref(checkpoint),
                request_id=request_id,
                max_tokens=output_limit,
                stop=JSON_CALL_STOP_SUFFIXES if json_output else (),
                sampling=selected.to_dict(),
                parent_cache_binding_digest=parent_binding.digest,
            )
        finally:
            current_model_lane.reset(lane_token)
            current_task_id.reset(task_token)
        if not isinstance(returned, NativeStateCandidate):
            raise ModelSessionError("native state server returned an invalid candidate")
        if returned.parent_state_digest != checkpoint.native_state_digest:
            raise ModelSessionError("native candidate parent state digest mismatch")
        if returned.parent_cache_binding_digest != parent_binding.digest:
            raise ModelSessionError("native candidate parent cache binding mismatch")
        candidate_checkpoint = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=returned.content,
            event_ids=checkpoint.event_ids,
            status=ModelCheckpointStatus.CANDIDATE,
        )
        candidate_checkpoint.native_state_ref = returned.state_ref
        candidate_checkpoint.native_state_digest = returned.state_digest
        candidate_binding = self._cache_binding(
            candidate_checkpoint,
            state_chain_digest=_next_state_chain_digest(
                parent_binding.state_chain_digest,
                returned.content,
            ),
            delta=returned.content,
            parent_state_digest=str(checkpoint.native_state_digest or ""),
        )
        candidate_checkpoint.native_state_metadata = {
            **dict(checkpoint.native_state_metadata or {}),
            "cache_role": "disposable_acceleration",
            "authoritative": False,
            "cache_binding": candidate_binding.to_dict(),
            "cache_binding_digest": candidate_binding.digest,
        }
        candidate = CandidateGeneration(
            request_id=request_id,
            candidate_id=f"CAND-{uuid4().hex[:16]}",
            parent=checkpoint,
            checkpoint=candidate_checkpoint,
            raw_output=returned.content,
            finish_reason=returned.finish_reason,
            sampling=selected,
            max_output_tokens=output_limit,
            raw_token_ids=tuple(
                int(item) for item in returned.metadata.get("token_ids", ())
            ),
            response_id=str(returned.metadata.get("response_id") or ""),
            response_model=self.model_name,
            state_profile_id=self.settings.state_profile_id,
            state_profile_sha256=self.settings.state_profile_sha256,
        )
        self._emit(
            {
                "type": "model_session_generation_returned",
                "request_id": request_id,
                "lane_id": checkpoint.lane_id,
                "candidate_id": candidate.candidate_id,
                "candidate_checkpoint_id": candidate.checkpoint.checkpoint_id,
                "candidate_digest": returned.state_digest,
                "raw_output": returned.content,
                "raw_generation": candidate.raw_record(),
                "finish_reason": returned.finish_reason,
                "state_transport": self.transport,
            }
        )
        return candidate

    def commit(
        self,
        candidate: CandidateGeneration,
        command: ModelCommand,
    ) -> ModelCheckpoint:
        self._require_committed(candidate.parent)
        if candidate.checkpoint.status != ModelCheckpointStatus.CANDIDATE:
            raise ModelSessionError("only a candidate checkpoint can be committed")
        self._require_checkpoint_identity(candidate.checkpoint)
        if self.parse(candidate) != command:
            raise ModelIOError("accepted command differs from candidate output")
        binding = self._binding_from_checkpoint(candidate.checkpoint)
        snapshot = self.native_client.state_commit(
            candidate_state_ref=self._state_ref(candidate.checkpoint),
            cache_binding=binding,
        )
        if snapshot.state_digest != candidate.checkpoint.native_state_digest:
            raise ModelSessionError("native commit changed candidate state digest")
        committed = ModelCheckpoint.from_dict(
            {**candidate.checkpoint.to_dict(), "status": "committed"}
        )
        self._bind_snapshot(committed, snapshot, binding)
        self._emit(
            {
                "type": "model_session_candidate_committed",
                "lane_id": committed.lane_id,
                "candidate_id": candidate.candidate_id,
                "checkpoint_id": committed.checkpoint_id,
                "command_digest": command.digest,
                "state_digest": snapshot.state_digest,
                "state_transport": self.transport,
            }
        )
        return committed

    def rollback(
        self, candidate: CandidateGeneration, *, error: str = ""
    ) -> ModelCheckpoint:
        self._require_committed(candidate.parent)
        self._require_checkpoint_identity(candidate.checkpoint)
        self.native_client.state_rollback(
            candidate_state_ref=self._state_ref(candidate.checkpoint),
            parent_state_ref=self._state_ref(candidate.parent),
        )
        self._emit(
            {
                "type": "model_session_candidate_rolled_back",
                "lane_id": candidate.parent.lane_id,
                "candidate_id": candidate.candidate_id,
                "candidate_checkpoint_id": candidate.checkpoint.checkpoint_id,
                "restored_checkpoint_id": candidate.parent.checkpoint_id,
                "error": str(error)[:2000],
                "state_transport": self.transport,
            }
        )
        return candidate.parent

    def export(self, checkpoint: ModelCheckpoint) -> dict[str, Any]:
        self._require_committed(checkpoint)
        self._state_ref(checkpoint)
        if not checkpoint.native_state_export or not checkpoint.native_state_metadata:
            raise ModelSessionError("native checkpoint has no durable export record")
        return checkpoint.to_dict()

    def import_checkpoint(self, value: Mapping[str, Any]) -> ModelCheckpoint:
        checkpoint = ModelCheckpoint.from_dict(value)
        self._require_committed(checkpoint)
        if checkpoint.transport != self.transport or not checkpoint.native_state_export:
            raise ModelSessionError("checkpoint is not an exported native RWKV state")
        if _digest_text(checkpoint.transcript) != checkpoint.transcript_digest:
            raise ModelSessionError("checkpoint transcript digest mismatch")
        snapshot = self.native_client.state_import(
            export_record=checkpoint.native_state_export,
            cache_binding=self._binding_from_checkpoint(checkpoint),
        )
        if snapshot.state_digest != checkpoint.native_state_digest:
            raise ModelSessionError("imported native state digest mismatch")
        expected = checkpoint.native_state_metadata or {}
        observed = {
            "protocol_version": snapshot.protocol_version,
            "state_format_version": snapshot.state_format_version,
            "server_build": snapshot.server_build,
            "tokenizer_build": snapshot.tokenizer_build,
        }
        if any(expected.get(key) != value for key, value in observed.items()):
            raise ModelSessionError("imported native state build metadata mismatch")
        return self._bind_snapshot(
            checkpoint,
            snapshot,
            self._binding_from_checkpoint(checkpoint),
        )


def create_model_session(
    client: CompletionClient | NativeRWKVStateClient | None = None,
    *,
    settings: RuntimeSettings | None = None,
    audit_hook: SessionAuditHook | None = None,
) -> ModelSession:
    """Select a truthful transport from explicit settings and capabilities."""

    selected_settings = settings or get_runtime_settings()
    selected_client = client or OpenAICompatibleRWKVClient(selected_settings)
    mode = selected_settings.state_transport
    if mode == "prompt_replay":
        return ModelSession(
            selected_client,  # type: ignore[arg-type]
            settings=selected_settings,
            audit_hook=audit_hook,
        )
    required_methods = (
        "capabilities",
        "state_create",
        "state_append",
        "state_fork",
        "state_generate",
        "state_commit",
        "state_rollback",
        "state_import",
    )
    missing = tuple(
        name
        for name in required_methods
        if not callable(getattr(selected_client, name, None))
    )
    capabilities = None
    if not missing:
        capabilities = selected_client.capabilities()  # type: ignore[attr-defined]
    if (
        not missing
        and capabilities is not None
        and capabilities.durable_recurrent_state
        and capabilities.recurrent_state_protocol == NATIVE_STATE_PROTOCOL_VERSION
    ):
        return NativeRWKVModelSession(
            selected_client,  # type: ignore[arg-type]
            settings=selected_settings,
            audit_hook=audit_hook,
        )
    reason = (
        f"native state client methods unavailable: {', '.join(missing)}"
        if missing
        else "runtime recurrent-state protocol is absent or incompatible"
        if capabilities is not None
        and capabilities.durable_recurrent_state
        and capabilities.recurrent_state_protocol != NATIVE_STATE_PROTOCOL_VERSION
        else "runtime did not declare the complete durable recurrent-state capability"
    )
    if mode == "native_required":
        raise NativeStateUnavailableError(reason)
    if audit_hook is not None:
        audit_hook(
            {
                "type": "model_session_transport_fallback",
                "requested_transport": "native_rwkv",
                "selected_transport": "prompt_replay",
                "reason": reason,
            }
        )
    return ModelSession(
        selected_client,  # type: ignore[arg-type]
        settings=selected_settings,
        audit_hook=audit_hook,
    )


__all__ = [
    "CandidateGeneration",
    "CompletionClient",
    "InputBudgetError",
    "ModelSession",
    "ModelSessionError",
    "NativeRWKVModelSession",
    "NativeStateUnavailableError",
    "create_model_session",
    "SessionSampling",
]
