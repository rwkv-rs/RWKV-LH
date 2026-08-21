"""Versioned contracts for the single RWKV action spine.

The runtime stores literal input, model calls, exact tool observations and
artifact revisions.  It deliberately has no online plan, Task graph,
completion criterion, reviewer state, or controller-authored semantic claim.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


GOAL_SCHEMA_VERSION = "long-horizon.literal-request.v1"
RUN_SCHEMA_VERSION = "long-horizon.run.v18"
CAUSAL_EVENT_SCHEMA_VERSION = "rwkv-lh.causal-event.v2"

CAUSAL_EVENT_PAYLOAD_SCHEMAS: dict[str, str] = {
    "run_created": "rwkv-lh.run-created.v1",
    "run_started": "rwkv-lh.run-started.v1",
    "run_completed": "rwkv-lh.run-terminal.v1",
    "run_interrupted": "rwkv-lh.run-terminal.v1",
    "run_failed": "rwkv-lh.run-terminal.v1",
    "snapshot_recovered": "rwkv-lh.snapshot-recovered.v1",
    "state_saved": "rwkv-lh.state-saved.v1",
    "action_session_started": "rwkv-lh.action-session-started.v1",
    "action_session_rolled_over": "rwkv-lh.action-session-rollover.v1",
    "model_call_accepted": "rwkv-lh.model-decision.v1",
    "model_call_rejected": "rwkv-lh.model-decision.v1",
    "protocol_rejection_recorded": "rwkv-lh.protocol-rejection.v1",
    "action_started": "rwkv-lh.action-started.v1",
    "action_finished": "rwkv-lh.action-finished.v1",
    "action_observation_appended": "rwkv-lh.model-event-appended.v1",
    "stale_active_action_cleared": "rwkv-lh.action-recovery.v1",
    "idempotent_action_recovered": "rwkv-lh.action-recovery.v1",
    "model_transport_failure": "rwkv-lh.model-transport-failure.v1",
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class ActionStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class RunStatus(str, Enum):
    INITIALIZED = "initialized"
    RUNNING = "running"
    COMPLETED = "completed"
    INTERRUPTED = "interrupted"
    BLOCKED = "blocked"
    FAILED = "failed"


class ModelLaneKind(str, Enum):
    ACTION = "action"


class ModelCheckpointStatus(str, Enum):
    COMMITTED = "committed"
    CANDIDATE = "candidate"
    ROLLED_BACK = "rolled_back"


@dataclass(frozen=True)
class GoalState:
    """Literal immutable run input; it is never produced or parsed by a model."""

    goal_id: str
    request: str
    constraints: tuple[str, ...]
    workspace_root: str
    created_at: str
    digest: str
    schema_version: str = GOAL_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        request: str,
        constraints: list[str] | tuple[str, ...],
        workspace_root: str | Path,
        goal_id: str = "G1",
    ) -> "GoalState":
        request_text = str(request or "").strip()
        if not request_text:
            raise ValueError("request must be non-empty")
        constraint_values = tuple(
            dict.fromkeys(
                str(item).strip() for item in constraints if str(item).strip()
            )
        )
        immutable = {
            "schema_version": GOAL_SCHEMA_VERSION,
            "goal_id": str(goal_id or "G1").strip(),
            "request": request_text,
            "constraints": list(constraint_values),
            "workspace_root": str(Path(workspace_root).expanduser().resolve()),
            "created_at": utc_now(),
        }
        return cls(
            schema_version=immutable["schema_version"],
            goal_id=immutable["goal_id"],
            request=immutable["request"],
            constraints=constraint_values,
            workspace_root=immutable["workspace_root"],
            created_at=immutable["created_at"],
            digest=_canonical_digest(immutable),
        )

    def immutable_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "goal_id": self.goal_id,
            "request": self.request,
            "constraints": list(self.constraints),
            "workspace_root": self.workspace_root,
            "created_at": self.created_at,
        }

    def verify_digest(self) -> bool:
        return self.digest == _canonical_digest(self.immutable_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.immutable_payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalState":
        literal = cls(
            schema_version=str(value.get("schema_version") or ""),
            goal_id=str(value.get("goal_id") or "G1"),
            request=str(value.get("request") or ""),
            constraints=tuple(str(item) for item in value.get("constraints") or []),
            workspace_root=str(value.get("workspace_root") or ""),
            created_at=str(value.get("created_at") or ""),
            digest=str(value.get("digest") or ""),
        )
        if literal.schema_version != GOAL_SCHEMA_VERSION:
            raise ValueError(f"unsupported literal request schema: {literal.schema_version}")
        if not literal.request or not literal.verify_digest():
            raise ValueError("literal request digest mismatch")
        return literal


@dataclass
class ValidationSpec:
    """Harness-internal observable contract; never shown as a completion goal."""

    kind: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: bool = True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationSpec":
        parameters = value.get("parameters")
        if not isinstance(parameters, Mapping):
            raise ValueError("validation parameters must be an object")
        return cls(
            kind=str(value.get("kind") or ""),
            parameters=dict(parameters),
            required=bool(value.get("required", True)),
        )


@dataclass
class TaskAction:
    """Exact executable operation selected by RWKV.

    The historical name remains only at the Harness boundary.  It is an action
    value, not an online Task, plan node, or completion claim.
    """

    action_type: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "TaskAction":
        if not isinstance(value, Mapping) or not isinstance(value.get("arguments"), Mapping):
            raise ValueError("action must contain an arguments object")
        return cls(
            action_type=str(value.get("action_type") or "").strip(),
            arguments=dict(value["arguments"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return {"action_type": self.action_type, "arguments": dict(self.arguments)}


def action_fingerprint(action: TaskAction) -> str:
    return _canonical_digest(action.to_dict())


@dataclass(frozen=True)
class ModelEvent:
    event_type: str
    event_id: str
    scope_id: str
    payload: dict[str, Any] = field(default_factory=dict)
    content_refs: tuple[str, ...] = ()
    complete: bool = True
    continuation: dict[str, Any] | None = None
    event_version: str = "rwkv-lh.event.v2"

    def __post_init__(self) -> None:
        if not self.event_type.strip() or not self.event_id.strip():
            raise ValueError("model event requires event_type and event_id")
        if not self.complete and not isinstance(self.continuation, Mapping):
            raise ValueError("incomplete model event requires continuation metadata")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "event_type": self.event_type,
            "event_version": self.event_version,
            "event_id": self.event_id,
            "scope_id": self.scope_id,
            "payload": dict(self.payload),
            "content_refs": list(self.content_refs),
            "complete": self.complete,
        }
        if self.continuation is not None:
            value["continuation"] = dict(self.continuation)
        return value

    def to_model_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "event_type": self.event_type,
            "payload": dict(self.payload),
            "content_refs": list(self.content_refs),
            "complete": self.complete,
        }
        if self.continuation is not None:
            value["continuation"] = dict(self.continuation)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelEvent":
        continuation = value.get("continuation")
        return cls(
            event_type=str(value.get("event_type") or ""),
            event_version=str(value.get("event_version") or "rwkv-lh.event.v2"),
            event_id=str(value.get("event_id") or ""),
            scope_id=str(value.get("scope_id") or ""),
            payload=dict(value.get("payload") or {}),
            content_refs=tuple(str(item) for item in value.get("content_refs") or []),
            complete=bool(value.get("complete", True)),
            continuation=dict(continuation) if isinstance(continuation, Mapping) else None,
        )


@dataclass
class ModelCheckpoint:
    checkpoint_id: str
    lane_id: str
    lane_kind: ModelLaneKind
    parent_checkpoint_id: str | None
    model: str
    transport: str
    transcript: str
    transcript_digest: str
    token_count: int
    event_ids: list[str] = field(default_factory=list)
    native_state_ref: str | None = None
    status: ModelCheckpointStatus = ModelCheckpointStatus.COMMITTED
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["lane_kind"] = self.lane_kind.value
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelCheckpoint":
        return cls(
            checkpoint_id=str(value.get("checkpoint_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            lane_kind=ModelLaneKind(str(value.get("lane_kind") or "")),
            parent_checkpoint_id=(
                str(value["parent_checkpoint_id"])
                if value.get("parent_checkpoint_id") is not None
                else None
            ),
            model=str(value.get("model") or ""),
            transport=str(value.get("transport") or "prompt_replay"),
            transcript=str(value.get("transcript") or ""),
            transcript_digest=str(value.get("transcript_digest") or ""),
            token_count=max(0, int(value.get("token_count", 0) or 0)),
            event_ids=[str(item) for item in value.get("event_ids") or []],
            native_state_ref=(
                str(value["native_state_ref"])
                if value.get("native_state_ref") is not None
                else None
            ),
            status=ModelCheckpointStatus(
                str(value.get("status") or ModelCheckpointStatus.COMMITTED.value)
            ),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class DecisionRecord:
    decision_id: str
    request_id: str
    lane_id: str
    input_checkpoint_id: str
    input_digest: str
    visible_event_ids: tuple[str, ...]
    raw_output: str
    command_digest: str
    output_checkpoint_id: str
    output_digest: str
    sampling: dict[str, Any]
    model: str
    transport: str
    accepted: bool
    error: str = ""
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["visible_event_ids"] = list(self.visible_event_ids)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "DecisionRecord":
        return cls(
            decision_id=str(value.get("decision_id") or ""),
            request_id=str(value.get("request_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            input_checkpoint_id=str(value.get("input_checkpoint_id") or ""),
            input_digest=str(value.get("input_digest") or ""),
            visible_event_ids=tuple(str(item) for item in value.get("visible_event_ids") or []),
            raw_output=str(value.get("raw_output") or ""),
            command_digest=str(value.get("command_digest") or ""),
            output_checkpoint_id=str(value.get("output_checkpoint_id") or ""),
            output_digest=str(value.get("output_digest") or ""),
            sampling=dict(value.get("sampling") or {}),
            model=str(value.get("model") or ""),
            transport=str(value.get("transport") or "prompt_replay"),
            accepted=bool(value.get("accepted", False)),
            error=str(value.get("error") or ""),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass(frozen=True)
class ModelRolloverRecord:
    rollover_id: str
    lane_id: str
    source_checkpoint_id: str
    source_digest: str
    source_token_count: int
    output_checkpoint_id: str
    output_digest: str
    output_token_count: int
    retained_event_ids: tuple[str, ...]
    archived_event_ids: tuple[str, ...]
    input_limit: int
    semantic_request_count: int = 0
    created_at: str = field(default_factory=utc_now)

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["retained_event_ids"] = list(self.retained_event_ids)
        value["archived_event_ids"] = list(self.archived_event_ids)
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelRolloverRecord":
        return cls(
            rollover_id=str(value.get("rollover_id") or ""),
            lane_id=str(value.get("lane_id") or ""),
            source_checkpoint_id=str(value.get("source_checkpoint_id") or ""),
            source_digest=str(value.get("source_digest") or ""),
            source_token_count=int(value.get("source_token_count", 0) or 0),
            output_checkpoint_id=str(value.get("output_checkpoint_id") or ""),
            output_digest=str(value.get("output_digest") or ""),
            output_token_count=int(value.get("output_token_count", 0) or 0),
            retained_event_ids=tuple(str(item) for item in value.get("retained_event_ids") or []),
            archived_event_ids=tuple(str(item) for item in value.get("archived_event_ids") or []),
            input_limit=int(value.get("input_limit", 1) or 1),
            semantic_request_count=int(value.get("semantic_request_count", 0) or 0),
            created_at=str(value.get("created_at") or utc_now()),
        )


@dataclass
class ActionRecord:
    action_id: str
    sequence: int
    status: ActionStatus
    action_type: str
    arguments: dict[str, Any]
    wire_arguments: dict[str, Any]
    action_fingerprint: str
    idempotency_key: str
    decision_id: str
    request_id: str
    started_at: str
    ended_at: str | None = None
    result: dict[str, Any] | None = None
    artifact_refs: list[str] = field(default_factory=list)
    workspace_digest_before: str = ""
    workspace_digest_after: str = ""
    failure_key: str = ""
    observation_fingerprint: str = ""
    error: dict[str, Any] | None = None
    outcome_type: str = "pending"

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActionRecord":
        return cls(
            action_id=str(value.get("action_id") or ""),
            sequence=max(1, int(value.get("sequence", 1) or 1)),
            status=ActionStatus(str(value.get("status") or ActionStatus.RUNNING.value)),
            action_type=str(value.get("action_type") or ""),
            arguments=dict(value.get("arguments") or {}),
            wire_arguments=dict(value.get("wire_arguments") or {}),
            action_fingerprint=str(value.get("action_fingerprint") or ""),
            idempotency_key=str(value.get("idempotency_key") or ""),
            decision_id=str(value.get("decision_id") or ""),
            request_id=str(value.get("request_id") or ""),
            started_at=str(value.get("started_at") or ""),
            ended_at=str(value["ended_at"]) if value.get("ended_at") else None,
            result=dict(value["result"]) if isinstance(value.get("result"), Mapping) else None,
            artifact_refs=[str(item) for item in value.get("artifact_refs") or []],
            workspace_digest_before=str(value.get("workspace_digest_before") or ""),
            workspace_digest_after=str(value.get("workspace_digest_after") or ""),
            failure_key=str(value.get("failure_key") or ""),
            observation_fingerprint=str(value.get("observation_fingerprint") or ""),
            error=dict(value["error"]) if isinstance(value.get("error"), Mapping) else None,
            outcome_type=str(value.get("outcome_type") or "pending"),
        )


@dataclass
class ArtifactRecord:
    artifact_id: str
    action_id: str
    path: str
    sha256: str
    media_type: str = "application/octet-stream"
    size_bytes: int = 0
    summary: str = ""
    observed_at: str = field(default_factory=utc_now)


@dataclass
class ArtifactRevision:
    revision_id: str
    target: str
    artifact_id: str
    action_id: str
    sha256: str
    outcome_type: str
    supersedes_revision_ids: list[str] = field(default_factory=list)
    observed_at: str = field(default_factory=utc_now)


@dataclass(frozen=True)
class CausalEventDraft:
    """One explicit, typed event submitted by a runtime stage."""

    event_type: str
    payload_schema: str
    payload: dict[str, Any]
    subject_id: str
    cause_id: str | None = None

    @classmethod
    def create(
        cls,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        subject_id: str,
        cause_id: str | None = None,
    ) -> "CausalEventDraft":
        name = str(event_type or "")
        payload_schema = CAUSAL_EVENT_PAYLOAD_SCHEMAS.get(name)
        if payload_schema is None:
            raise ValueError(f"unregistered causal event type: {name}")
        subject = str(subject_id or "").strip()
        if not subject:
            raise ValueError("causal event subject_id must be non-empty")
        return cls(
            event_type=name,
            payload_schema=payload_schema,
            payload=dict(payload),
            subject_id=subject,
            cause_id=str(cause_id) if cause_id else None,
        )


@dataclass(frozen=True)
class CausalEvent:
    """The single append-only fact interface shared by every runtime stage."""

    event_id: str
    run_id: str
    sequence: int
    parent_id: str | None
    cause_id: str | None
    subject_id: str
    event_type: str
    payload_schema: str
    payload: dict[str, Any]
    digest: str
    created_at: str
    schema_version: str = CAUSAL_EVENT_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        event_id: str,
        run_id: str,
        sequence: int,
        parent_id: str | None,
        draft: CausalEventDraft,
        created_at: str | None = None,
    ) -> "CausalEvent":
        timestamp = str(created_at or utc_now())
        immutable = {
            "schema_version": CAUSAL_EVENT_SCHEMA_VERSION,
            "event_id": str(event_id),
            "run_id": str(run_id),
            "sequence": int(sequence),
            "parent_id": str(parent_id) if parent_id is not None else None,
            "cause_id": draft.cause_id,
            "subject_id": draft.subject_id,
            "event_type": draft.event_type,
            "payload_schema": draft.payload_schema,
            "payload": dict(draft.payload),
            "created_at": timestamp,
        }
        return cls(**immutable, digest=_canonical_digest(immutable))

    def immutable_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "run_id": self.run_id,
            "sequence": self.sequence,
            "parent_id": self.parent_id,
            "cause_id": self.cause_id,
            "subject_id": self.subject_id,
            "event_type": self.event_type,
            "payload_schema": self.payload_schema,
            "payload": dict(self.payload),
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, Any]:
        return {**self.immutable_payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CausalEvent":
        record = cls(
            schema_version=str(value.get("schema_version") or ""),
            event_id=str(value.get("event_id") or ""),
            run_id=str(value.get("run_id") or ""),
            sequence=int(value.get("sequence", 0) or 0),
            parent_id=(str(value["parent_id"]) if value.get("parent_id") is not None else None),
            cause_id=(str(value["cause_id"]) if value.get("cause_id") is not None else None),
            subject_id=str(value.get("subject_id") or ""),
            event_type=str(value.get("event_type") or ""),
            payload_schema=str(value.get("payload_schema") or ""),
            payload=dict(value.get("payload") or {}),
            digest=str(value.get("digest") or ""),
            created_at=str(value.get("created_at") or ""),
        )
        expected_schema = CAUSAL_EVENT_PAYLOAD_SCHEMAS.get(record.event_type)
        if record.schema_version != CAUSAL_EVENT_SCHEMA_VERSION:
            raise ValueError("unsupported causal event schema")
        if expected_schema is None or record.payload_schema != expected_schema:
            raise ValueError("causal event payload schema mismatch")
        if not record.event_id or not record.run_id or not record.subject_id:
            raise ValueError("causal event identity is incomplete")
        if record.digest != _canonical_digest(record.immutable_payload()):
            raise ValueError("causal event digest mismatch")
        return record


@dataclass
class TempDecision:
    request_id: str
    task_id: str
    request_type: str
    temperature: float
    policy_reason: str
    attempt: int
    started_at: str
    top_p: float = 1.0
    top_k: int = 0
    presence_penalty: float = 0.0
    frequency_penalty: float = 0.0
    penalty_decay: float = 0.996
    max_tokens: int = 0
    backend_profile: str = "vllm-rwkv-rapid"
    seed_supported: bool = False
    ended_at: str | None = None
    outcome: str = "running"
    result_summary: str = ""
    error: str | None = None


@dataclass(frozen=True)
class ChunkDescriptor:
    """Tokenizer cursor utility used by read_file/read_json observations."""

    chunk_id: str
    source_ref: str
    source_sha256: str
    media_type: str
    byte_start: int
    byte_end: int
    core_start: int
    core_end: int
    overlap_before: int
    overlap_after: int
    chunk_sha256: str
    split_strategy_version: str
    previous_chunk_id: str | None = None
    next_chunk_id: str | None = None
    complete_source: bool = False
    token_start: int = 0
    token_end: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ChunkDescriptor":
        return cls(**dict(value))


@dataclass
class RunState:
    run_id: str
    goal: GoalState
    revision: int = 0
    status: RunStatus = RunStatus.INITIALIZED
    actions: dict[str, ActionRecord] = field(default_factory=dict)
    active_action_id: str | None = None
    next_action_sequence: int = 1
    artifacts: dict[str, ArtifactRecord] = field(default_factory=dict)
    artifact_revisions: dict[str, list[ArtifactRevision]] = field(default_factory=dict)
    causal_records: dict[str, CausalEvent] = field(default_factory=dict)
    causal_order: list[str] = field(default_factory=list)
    model_states: dict[str, ModelCheckpoint] = field(default_factory=dict)
    action_lane_checkpoint_id: str = ""
    model_events: dict[str, ModelEvent] = field(default_factory=dict)
    decisions: dict[str, DecisionRecord] = field(default_factory=dict)
    rollovers: dict[str, ModelRolloverRecord] = field(default_factory=dict)
    temp_decisions: list[TempDecision] = field(default_factory=list)
    failure_budgets: dict[str, int] = field(default_factory=dict)
    observation_counts: dict[str, int] = field(default_factory=dict)
    protocol_rejections: int = 0
    final_output: str = ""
    final_decision_id: str = ""
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: str = RUN_SCHEMA_VERSION

    def projection_payload(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "actions": {key: value.to_dict() for key, value in self.actions.items()},
            "active_action_id": self.active_action_id,
            "next_action_sequence": self.next_action_sequence,
            "artifacts": {key: asdict(value) for key, value in self.artifacts.items()},
            "artifact_revisions": {
                key: [asdict(item) for item in revisions]
                for key, revisions in self.artifact_revisions.items()
            },
            "model_events": {key: value.to_dict() for key, value in self.model_events.items()},
            "decisions": {key: value.to_dict() for key, value in self.decisions.items()},
            "rollovers": {key: value.to_dict() for key, value in self.rollovers.items()},
            "temp_decisions": [asdict(value) for value in self.temp_decisions],
            "failure_budgets": dict(self.failure_budgets),
            "observation_counts": dict(self.observation_counts),
            "protocol_rejections": self.protocol_rejections,
            "final_output": self.final_output,
            "final_decision_id": self.final_decision_id,
            "errors": list(self.errors),
        }

    @property
    def projection_digest(self) -> str:
        return _canonical_digest(self.projection_payload())

    def rebuild_projection(self) -> None:
        """Fold the immutable causal chain into disposable runtime projections."""

        self.status = RunStatus.INITIALIZED
        self.actions = {}
        self.active_action_id = None
        self.next_action_sequence = 1
        self.artifacts = {}
        self.artifact_revisions = {}
        self.model_events = {}
        self.decisions = {}
        self.rollovers = {}
        self.temp_decisions = []
        self.failure_budgets = {}
        self.observation_counts = {}
        self.protocol_rejections = 0
        self.final_output = ""
        self.final_decision_id = ""
        self.errors = []

        previous_id: str | None = None
        seen: set[str] = set()
        for expected_sequence, event_id in enumerate(self.causal_order, start=1):
            event = self.causal_records.get(event_id)
            if event is None:
                raise ValueError(f"causal order references missing event: {event_id}")
            if event.event_id != event_id or event.run_id != self.run_id:
                raise ValueError("causal event identity mismatch")
            if event.sequence != expected_sequence or event.parent_id != previous_id:
                raise ValueError("causal event sequence or parent mismatch")
            if event.cause_id is not None and event.cause_id not in seen:
                raise ValueError("causal event cause must reference an earlier event")
            previous_id = event_id
            seen.add(event_id)
            payload = event.payload

            if event.event_type == "run_started":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.RUNNING
            elif event.event_type == "run_completed":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.COMPLETED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "run_interrupted":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.INTERRUPTED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "run_failed":
                if event.subject_id != self.run_id:
                    raise ValueError("run event subject mismatch")
                self.status = RunStatus.FAILED
                self.final_output = str(payload.get("final_output") or "")
                self.final_decision_id = str(payload.get("decision_id") or "")
            elif event.event_type == "action_started":
                action_value = payload.get("action")
                if not isinstance(action_value, Mapping):
                    raise ValueError("action_started requires a complete action")
                action = ActionRecord.from_dict(action_value)
                if event.subject_id != action.action_id:
                    raise ValueError("action_started subject mismatch")
                if action.status != ActionStatus.RUNNING:
                    raise ValueError("action_started must carry running status")
                if action.action_id in self.actions:
                    raise ValueError("action id was started more than once")
                if action.sequence != self.next_action_sequence:
                    raise ValueError("action sequence is not contiguous")
                if self.active_action_id is not None:
                    raise ValueError("more than one action is active")
                self.actions[action.action_id] = action
                self.active_action_id = action.action_id
                self.next_action_sequence += 1
            elif event.event_type == "action_finished":
                action_value = payload.get("action")
                if not isinstance(action_value, Mapping):
                    raise ValueError("action_finished requires a complete action")
                action = ActionRecord.from_dict(action_value)
                if event.subject_id != action.action_id:
                    raise ValueError("action_finished subject mismatch")
                started = self.actions.get(action.action_id)
                if started is None or started.status != ActionStatus.RUNNING:
                    raise ValueError("action_finished has no matching running action")
                immutable_fields = (
                    "action_id", "sequence", "action_type", "arguments", "wire_arguments",
                    "action_fingerprint", "idempotency_key", "decision_id", "request_id",
                    "started_at", "workspace_digest_before",
                )
                if any(
                    getattr(started, name) != getattr(action, name)
                    for name in immutable_fields
                ):
                    raise ValueError("action_finished changed started action identity")
                if action.status == ActionStatus.RUNNING or action.result is None:
                    raise ValueError("action_finished requires terminal status and result")
                if str(action.result.get("action_type") or "") != action.action_type:
                    raise ValueError("action result operation mismatch")
                result_success = bool(action.result.get("success", False))
                if result_success != (action.status == ActionStatus.SUCCEEDED):
                    raise ValueError("action result success/status mismatch")
                artifact_values = payload.get("artifacts") or []
                artifact_ids = [str(item.get("artifact_id") or "") for item in artifact_values]
                if action.artifact_refs != artifact_ids:
                    raise ValueError("action artifact projection mismatch")
                self.actions[action.action_id] = action
                if self.active_action_id == action.action_id:
                    self.active_action_id = None
                for item in artifact_values:
                    artifact = ArtifactRecord(**dict(item))
                    if artifact.action_id != action.action_id:
                        raise ValueError("artifact action mismatch")
                    self.artifacts[artifact.artifact_id] = artifact
                for item in payload.get("artifact_revisions") or []:
                    revision = ArtifactRevision(**dict(item))
                    if (
                        revision.action_id != action.action_id
                        or revision.artifact_id not in artifact_ids
                    ):
                        raise ValueError("artifact revision action mismatch")
                    self.artifact_revisions.setdefault(revision.target, []).append(revision)
                if action.observation_fingerprint:
                    self.observation_counts[action.observation_fingerprint] = (
                        self.observation_counts.get(action.observation_fingerprint, 0) + 1
                    )
                if action.failure_key:
                    self.failure_budgets[action.failure_key] = (
                        self.failure_budgets.get(action.failure_key, 0) + 1
                    )
            elif event.event_type in {"model_call_accepted", "model_call_rejected"}:
                decision_value = payload.get("decision")
                if not isinstance(decision_value, Mapping):
                    raise ValueError("model decision event requires the complete decision")
                decision = DecisionRecord.from_dict(decision_value)
                if event.subject_id != decision.decision_id:
                    raise ValueError("model decision subject mismatch")
                if decision.decision_id in self.decisions:
                    raise ValueError("model decision id was recorded more than once")
                self.decisions[decision.decision_id] = decision
                temp_value = payload.get("temp_decision")
                if isinstance(temp_value, Mapping):
                    self.temp_decisions.append(TempDecision(**dict(temp_value)))
            elif event.event_type == "action_observation_appended":
                model_event_value = payload.get("model_event")
                if not isinstance(model_event_value, Mapping):
                    raise ValueError("observation append requires the complete model event")
                model_event = ModelEvent.from_dict(model_event_value)
                if event.subject_id != model_event.event_id:
                    raise ValueError("model event subject mismatch")
                if model_event.event_id in self.model_events:
                    raise ValueError("model event id was recorded more than once")
                self.model_events[model_event.event_id] = model_event
            elif event.event_type == "action_session_rolled_over":
                rollover_value = payload.get("rollover")
                if not isinstance(rollover_value, Mapping):
                    raise ValueError("rollover event requires the complete rollover")
                rollover = ModelRolloverRecord.from_dict(rollover_value)
                self.rollovers[rollover.rollover_id] = rollover
            elif event.event_type == "protocol_rejection_recorded":
                self.protocol_rejections += 1
                error_record = payload.get("error_record")
                if isinstance(error_record, Mapping):
                    self.errors.append(dict(error_record))

        if len(seen) != len(self.causal_records):
            raise ValueError("causal record set contains unordered events")

    def to_dict(self, *, include_projections: bool = True) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "revision": self.revision,
            "goal": self.goal.to_dict(),
            "causal_records": {
                key: value.to_dict() for key, value in self.causal_records.items()
            },
            "causal_order": list(self.causal_order),
            "model_states": {key: value.to_dict() for key, value in self.model_states.items()},
            "action_lane_checkpoint_id": self.action_lane_checkpoint_id,
            "projection_digest": self.projection_digest,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        if include_projections:
            value.update(self.projection_payload())
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunState":
        schema_version = str(value.get("schema_version") or "")
        if schema_version != RUN_SCHEMA_VERSION:
            raise ValueError(f"unsupported run schema: {schema_version}")
        state = cls(
            schema_version=schema_version,
            run_id=str(value.get("run_id") or ""),
            revision=int(value.get("revision", 0) or 0),
            goal=GoalState.from_dict(value.get("goal") or {}),
            causal_records={
                str(key): CausalEvent.from_dict(item)
                for key, item in (value.get("causal_records") or {}).items()
                if isinstance(item, Mapping)
            },
            causal_order=[str(item) for item in value.get("causal_order") or []],
            model_states={
                str(key): ModelCheckpoint.from_dict(item)
                for key, item in (value.get("model_states") or {}).items()
                if isinstance(item, Mapping)
            },
            action_lane_checkpoint_id=str(value.get("action_lane_checkpoint_id") or ""),
            created_at=str(value.get("created_at") or ""),
            updated_at=str(value.get("updated_at") or ""),
        )
        state.rebuild_projection()
        expected_projection_digest = str(value.get("projection_digest") or "")
        if expected_projection_digest and expected_projection_digest != state.projection_digest:
            raise ValueError("run projection digest mismatch")
        return state


__all__ = [
    "ActionRecord",
    "ActionStatus",
    "ArtifactRecord",
    "ArtifactRevision",
    "CAUSAL_EVENT_PAYLOAD_SCHEMAS",
    "CAUSAL_EVENT_SCHEMA_VERSION",
    "CausalEvent",
    "CausalEventDraft",
    "ChunkDescriptor",
    "DecisionRecord",
    "GOAL_SCHEMA_VERSION",
    "GoalState",
    "ModelCheckpoint",
    "ModelCheckpointStatus",
    "ModelEvent",
    "ModelLaneKind",
    "ModelRolloverRecord",
    "RUN_SCHEMA_VERSION",
    "RunState",
    "RunStatus",
    "TaskAction",
    "TempDecision",
    "ValidationSpec",
    "action_fingerprint",
    "utc_now",
]
