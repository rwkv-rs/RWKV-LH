"""Transactional RWKV model sessions with exact prompt-replay semantics."""

from __future__ import annotations

import hashlib
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
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
)
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
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
from rwkv_lh.token_budget import get_token_count


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


class ModelSession:
    """One bounded causal lane.

    The deployed backend currently supports only prompt replay. Candidate
    checkpoints are immutable and become visible only through ``commit``.
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
        self._audit_lock = threading.Lock()

    @property
    def model_name(self) -> str:
        return str(getattr(self.client, "model_name", self.settings.model))

    def _emit(self, event: Mapping[str, Any]) -> None:
        if self.audit_hook is None:
            return
        with self._audit_lock:
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
    ) -> ModelCheckpoint:
        identifier = lane_id or f"L-{lane_kind.value.upper()}-{uuid4().hex[:12]}"
        transcript = render_bootstrap(visible_definitions, assignment)
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
            }
        )
        return checkpoint

    def append(
        self,
        checkpoint: ModelCheckpoint,
        event: ModelEvent,
        visible_definitions: Sequence[Mapping[str, Any]] = (),
    ) -> ModelCheckpoint:
        self._require_committed(checkpoint)
        transcript = checkpoint.transcript + render_event_append(
            event, visible_definitions
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
                "parent_checkpoint_id": checkpoint.checkpoint_id,
                "checkpoint_id": appended.checkpoint_id,
                "new_event_tokens": appended.token_count - checkpoint.token_count,
                "token_count": appended.token_count,
                "state_transport": self.transport,
            }
        )
        return appended

    def rollover(
        self,
        checkpoint: ModelCheckpoint,
        assignment: str,
        visible_definitions: Sequence[Mapping[str, Any]],
        *,
        event_ids: Sequence[str],
        input_limit: int,
        rollover_id: str,
    ) -> ModelCheckpoint:
        """Replace one oversized replay head with a deterministic compact head.

        The source checkpoint is immutable and remains the exact archive.  This
        method performs no generation and accepts only runtime-produced bytes.
        """

        self._require_committed(checkpoint)
        if not str(rollover_id or "").strip():
            raise ModelSessionError("rollover requires a stable rollover id")
        limit = max(1, int(input_limit))
        transcript = render_bootstrap(visible_definitions, assignment)
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
        transcript_override: str | None = None,
    ) -> CandidateGeneration:
        self._require_committed(checkpoint)
        selected = sampling or SessionSampling()
        output_limit = max(1, int(max_output_tokens))
        input_limit = self.settings.max_prompt_tokens(output_limit)
        prompt = (
            checkpoint.transcript
            if transcript_override is None
            else transcript_override
        )
        prompt_tokens = get_token_count(prompt)
        prompt_digest = _digest_text(prompt)
        if prompt_tokens > input_limit:
            raise InputBudgetError(
                f"lane {checkpoint.lane_id} uses {prompt_tokens} input tokens; "
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
                "input_digest": prompt_digest,
                "canonical_input_digest": checkpoint.transcript_digest,
                "prompt_tokens_local": prompt_tokens,
                "static_replay_tokens": prompt_tokens,
                "transcript_override": transcript_override is not None,
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
                    prompt,
                    max_tokens=output_limit,
                    stop=JSON_CALL_STOP_SUFFIXES if json_output else None,
                )
        finally:
            current_model_lane.reset(lane_token)
            current_task_id.reset(task_token)
        raw = str(getattr(response, "content", response) or "")
        finish_reason = str(getattr(response, "finish_reason", "") or "")
        candidate_checkpoint = self._checkpoint(
            lane_id=checkpoint.lane_id,
            lane_kind=checkpoint.lane_kind,
            parent_checkpoint_id=checkpoint.checkpoint_id,
            transcript=prompt + raw,
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
        )
        self._emit(
            {
                "type": "model_session_generation_returned",
                "request_id": request_id,
                "lane_id": checkpoint.lane_id,
                "candidate_id": candidate.candidate_id,
                "candidate_checkpoint_id": candidate.checkpoint.checkpoint_id,
                "candidate_digest": candidate.checkpoint.transcript_digest,
                "input_digest": prompt_digest,
                "transcript_override": transcript_override is not None,
                "raw_output": raw,
                "finish_reason": finish_reason,
                "state_transport": self.transport,
            }
        )
        return candidate

    def generate_many(
        self,
        checkpoint: ModelCheckpoint,
        *,
        transcript_overrides: Sequence[str | None],
        sampling: SessionSampling | None = None,
        max_output_tokens: int = 900,
        json_output: bool = True,
        max_concurrency: int = 16,
    ) -> list[CandidateGeneration]:
        overrides = tuple(transcript_overrides)
        if not overrides:
            return []
        concurrency_enabled = bool(
            getattr(self.client, "supports_concurrent_requests", False)
        )
        worker_count = (
            min(len(overrides), max(1, int(max_concurrency)))
            if concurrency_enabled
            else 1
        )
        if worker_count == 1:
            return [
                self.generate(
                    checkpoint,
                    sampling=sampling,
                    max_output_tokens=max_output_tokens,
                    json_output=json_output,
                    transcript_override=override,
                )
                for override in overrides
            ]
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            futures = [
                executor.submit(
                    self.generate,
                    checkpoint,
                    sampling=sampling,
                    max_output_tokens=max_output_tokens,
                    json_output=json_output,
                    transcript_override=override,
                )
                for override in overrides
            ]
            return [future.result() for future in futures]

    def materialize_candidate(
        self,
        candidate: CandidateGeneration,
        parent: ModelCheckpoint,
    ) -> CandidateGeneration:
        self._require_committed(parent)
        if candidate.checkpoint.status != ModelCheckpointStatus.CANDIDATE:
            raise ModelSessionError("only a candidate generation can be materialized")
        if candidate.parent.checkpoint_id != parent.checkpoint_id:
            raise ModelSessionError("candidate and materialization parent do not match")
        checkpoint = self._checkpoint(
            lane_id=parent.lane_id,
            lane_kind=parent.lane_kind,
            parent_checkpoint_id=parent.checkpoint_id,
            transcript=parent.transcript + candidate.raw_output,
            event_ids=parent.event_ids,
            status=ModelCheckpointStatus.CANDIDATE,
        )
        materialized = CandidateGeneration(
            request_id=candidate.request_id,
            candidate_id=f"CAND-{uuid4().hex[:16]}",
            parent=parent,
            checkpoint=checkpoint,
            raw_output=candidate.raw_output,
            finish_reason=candidate.finish_reason,
            sampling=candidate.sampling,
            max_output_tokens=candidate.max_output_tokens,
        )
        self._emit(
            {
                "type": "model_session_candidate_materialized",
                "request_id": candidate.request_id,
                "source_candidate_id": candidate.candidate_id,
                "candidate_id": materialized.candidate_id,
                "lane_id": parent.lane_id,
                "parent_checkpoint_id": parent.checkpoint_id,
                "checkpoint_id": checkpoint.checkpoint_id,
                "transcript_digest": checkpoint.transcript_digest,
                "state_transport": self.transport,
            }
        )
        return materialized

    def parse(self, candidate: CandidateGeneration) -> ModelCommand:
        return parse_model_command(candidate.raw_output)

    def parse_with_trace(
        self,
        candidate: CandidateGeneration,
    ) -> tuple[ModelCommand, ModelCommandNormalization]:
        command, normalization = parse_model_command_with_trace(candidate.raw_output)
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
        if candidate.checkpoint.status != ModelCheckpointStatus.CANDIDATE:
            raise ModelSessionError("only a candidate checkpoint can be committed")
        if candidate.checkpoint.transcript != candidate.parent.transcript + candidate.raw_output:
            raise ModelSessionError(
                "candidate must be materialized onto its committed parent before commit"
            )
        if parse_model_command(candidate.raw_output) != command:
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

    def rollback(self, candidate: CandidateGeneration, *, error: str = "") -> ModelCheckpoint:
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

    @staticmethod
    def _require_committed(checkpoint: ModelCheckpoint) -> None:
        if checkpoint.status != ModelCheckpointStatus.COMMITTED:
            raise ModelSessionError("operation requires a committed checkpoint")


class NativeRWKVModelSession(ModelSession):
    """Reserved transport; construction fails until the state API is real."""

    transport = "native_rwkv"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        raise NativeStateUnavailableError(
            "the deployed server has no create/resume/fork/commit/rollback/export/import state API"
        )


__all__ = [
    "CandidateGeneration",
    "CompletionClient",
    "InputBudgetError",
    "ModelSession",
    "ModelSessionError",
    "NativeRWKVModelSession",
    "NativeStateUnavailableError",
    "SessionSampling",
]
