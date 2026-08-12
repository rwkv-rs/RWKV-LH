"""Versioned state contracts for the Long-Horizon Agent."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Mapping


GOAL_SCHEMA_VERSION = "long-horizon.goal.v1"
LEGACY_RUN_SCHEMA_VERSION = "long-horizon.run.v1"
RUN_SCHEMA_VERSION = "long-horizon.run.v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def _canonical_digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        dict(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AttemptStatus(str, Enum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    BLOCKED = "blocked"


class RunStatus(str, Enum):
    INITIALIZED = "initialized"
    PLANNING = "planning"
    RUNNING = "running"
    VALIDATING = "validating"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"
    INTERRUPTED = "interrupted"


class CriterionEvidenceStatus(str, Enum):
    VERIFIED = "verified"
    INVALIDATED = "invalidated"
    LEGACY_UNVERIFIED = "legacy_unverified"


@dataclass(frozen=True)
class GoalCriterion:
    criterion_id: str
    description: str
    required: bool = True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalCriterion":
        return cls(
            criterion_id=str(value.get("criterion_id") or value.get("id") or "").strip(),
            description=str(value.get("description") or "").strip(),
            required=bool(value.get("required", True)),
        )


@dataclass(frozen=True)
class GoalState:
    goal_id: str
    objective: str
    original_request: str
    constraints: tuple[str, ...]
    success_criteria: tuple[GoalCriterion, ...]
    workspace_root: str
    created_at: str
    digest: str
    schema_version: str = GOAL_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        original_request: str,
        constraints: list[str] | tuple[str, ...],
        success_criteria: list[GoalCriterion] | tuple[GoalCriterion, ...],
        workspace_root: str | Path,
        goal_id: str = "G1",
    ) -> "GoalState":
        normalized_constraints = tuple(
            str(item).strip() for item in constraints if str(item).strip()
        )
        normalized_criteria = tuple(success_criteria)
        root = str(Path(workspace_root).expanduser().resolve())
        created_at = utc_now()
        immutable = {
            "schema_version": GOAL_SCHEMA_VERSION,
            "goal_id": str(goal_id or "G1").strip(),
            "objective": str(objective or "").strip(),
            "original_request": str(original_request or "").strip(),
            "constraints": list(normalized_constraints),
            "success_criteria": [asdict(item) for item in normalized_criteria],
            "workspace_root": root,
            "created_at": created_at,
        }
        if not immutable["objective"] or not immutable["original_request"]:
            raise ValueError("goal requires objective and original_request")
        if not normalized_criteria:
            raise ValueError("goal requires at least one success criterion")
        return cls(
            goal_id=immutable["goal_id"],
            objective=immutable["objective"],
            original_request=immutable["original_request"],
            constraints=normalized_constraints,
            success_criteria=normalized_criteria,
            workspace_root=root,
            created_at=created_at,
            digest=_canonical_digest(immutable),
        )

    def immutable_payload(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "goal_id": self.goal_id,
            "objective": self.objective,
            "original_request": self.original_request,
            "constraints": list(self.constraints),
            "success_criteria": [asdict(item) for item in self.success_criteria],
            "workspace_root": self.workspace_root,
            "created_at": self.created_at,
        }

    def verify_digest(self) -> bool:
        return self.digest == _canonical_digest(self.immutable_payload())

    def to_dict(self) -> dict[str, Any]:
        return {**self.immutable_payload(), "digest": self.digest}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalState":
        goal = cls(
            schema_version=str(value.get("schema_version") or GOAL_SCHEMA_VERSION),
            goal_id=str(value.get("goal_id") or "G1"),
            objective=str(value.get("objective") or ""),
            original_request=str(value.get("original_request") or ""),
            constraints=tuple(str(item) for item in value.get("constraints") or []),
            success_criteria=tuple(
                GoalCriterion.from_dict(item)
                for item in value.get("success_criteria") or []
                if isinstance(item, Mapping)
            ),
            workspace_root=str(value.get("workspace_root") or ""),
            created_at=str(value.get("created_at") or ""),
            digest=str(value.get("digest") or ""),
        )
        if goal.schema_version != GOAL_SCHEMA_VERSION:
            raise ValueError(f"unsupported goal schema: {goal.schema_version}")
        if not goal.verify_digest():
            raise ValueError("goal digest mismatch")
        return goal


@dataclass
class ValidationSpec:
    kind: str
    parameters: dict[str, Any] = field(default_factory=dict)
    required: bool = True

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationSpec":
        parameters = value.get("parameters")
        if not isinstance(parameters, Mapping):
            parameters = {
                key: item
                for key, item in value.items()
                if key not in {"kind", "required"}
            }
        return cls(
            kind=str(value.get("kind") or "").strip(),
            parameters=dict(parameters),
            required=bool(value.get("required", True)),
        )


@dataclass
class RetryPolicy:
    max_attempts: int = 3
    backoff_seconds: float = 0.2
    replan_after: int = 2

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "RetryPolicy":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            max_attempts=max(1, int(raw.get("max_attempts", 3) or 3)),
            backoff_seconds=max(0.0, float(raw.get("backoff_seconds", 0.2) or 0.0)),
            replan_after=max(1, int(raw.get("replan_after", 2) or 2)),
        )


@dataclass
class TaskAction:
    action_type: str
    arguments: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "TaskAction":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            action_type=str(raw.get("action_type") or raw.get("type") or "").strip(),
            arguments=dict(raw.get("arguments") or {}),
        )


@dataclass
class TaskNode:
    task_id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    required: bool = True
    active: bool = True
    dependencies: list[str] = field(default_factory=list)
    # Legacy planning relevance. This field may describe criteria that a task
    # advances, but it is never completion evidence in run schema v2.
    goal_criteria: list[str] = field(default_factory=list)
    # Direct Goal-satisfaction claims. A claim only becomes effective after
    # the Controller commits typed CriterionEvidence from a passed attempt.
    satisfies_criteria: list[str] = field(default_factory=list)
    priority: int = 50
    inputs: list[dict[str, Any]] = field(default_factory=list)
    action: TaskAction = field(default_factory=lambda: TaskAction(""))
    completion_criteria: list[ValidationSpec] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempt_ids: list[str] = field(default_factory=list)
    output_refs: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    superseded_by: str | None = None
    recovery_lineage_id: str | None = None
    subject_task_id: str | None = None
    insertion_order: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "required": self.required,
            "active": self.active,
            "dependencies": list(self.dependencies),
            "goal_criteria": list(self.goal_criteria),
            "satisfies_criteria": list(self.satisfies_criteria),
            "priority": self.priority,
            "inputs": list(self.inputs),
            "action": {
                "type": self.action.action_type,
                "arguments": self.action.arguments,
            },
            "completion_criteria": [asdict(item) for item in self.completion_criteria],
            "retry_policy": asdict(self.retry_policy),
            "attempt_ids": list(self.attempt_ids),
            "output_refs": list(self.output_refs),
            "error": self.error,
            "superseded_by": self.superseded_by,
            "recovery_lineage_id": self.recovery_lineage_id,
            "subject_task_id": self.subject_task_id,
            "insertion_order": self.insertion_order,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "TaskNode":
        return cls(
            task_id=str(value.get("task_id") or value.get("id") or "").strip(),
            title=str(value.get("title") or "").strip(),
            description=str(value.get("description") or "").strip(),
            status=TaskStatus(str(value.get("status") or TaskStatus.PENDING.value)),
            required=bool(value.get("required", True)),
            active=bool(value.get("active", True)),
            dependencies=[str(item) for item in value.get("dependencies") or []],
            goal_criteria=[str(item) for item in value.get("goal_criteria") or []],
            satisfies_criteria=[
                str(item) for item in value.get("satisfies_criteria") or []
            ],
            priority=int(value.get("priority", 50) or 50),
            inputs=[dict(item) for item in value.get("inputs") or [] if isinstance(item, Mapping)],
            action=TaskAction.from_dict(value.get("action")),
            completion_criteria=[
                ValidationSpec.from_dict(item)
                for item in value.get("completion_criteria") or []
                if isinstance(item, Mapping)
            ],
            retry_policy=RetryPolicy.from_dict(value.get("retry_policy")),
            attempt_ids=[str(item) for item in value.get("attempt_ids") or []],
            output_refs=[str(item) for item in value.get("output_refs") or []],
            error=dict(value["error"]) if isinstance(value.get("error"), Mapping) else None,
            superseded_by=(
                str(value.get("superseded_by"))
                if value.get("superseded_by") is not None
                else None
            ),
            recovery_lineage_id=(
                str(value.get("recovery_lineage_id"))
                if value.get("recovery_lineage_id") is not None
                else None
            ),
            subject_task_id=(
                str(value.get("subject_task_id"))
                if value.get("subject_task_id") is not None
                else None
            ),
            insertion_order=int(value.get("insertion_order", 0) or 0),
        )


@dataclass
class ValidationResult:
    kind: str
    passed: bool
    required: bool
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    subject_task_id: str = ""
    criterion_ids: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    failure_fingerprint: str = ""
    checked_at: str = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ValidationResult":
        return cls(
            kind=str(value.get("kind") or ""),
            passed=bool(value.get("passed", False)),
            required=bool(value.get("required", True)),
            message=str(value.get("message") or ""),
            evidence=dict(value.get("evidence") or {}),
            subject_task_id=str(value.get("subject_task_id") or ""),
            criterion_ids=[str(item) for item in value.get("criterion_ids") or []],
            evidence_refs=[str(item) for item in value.get("evidence_refs") or []],
            failure_fingerprint=str(value.get("failure_fingerprint") or ""),
            checked_at=str(value.get("checked_at") or utc_now()),
        )


@dataclass
class CriterionEvidence:
    evidence_id: str
    criterion_id: str
    status: CriterionEvidenceStatus
    owner_task_id: str
    attempt_id: str
    validation_refs: list[str] = field(default_factory=list)
    artifact_refs: list[str] = field(default_factory=list)
    state_ref: str | None = None
    verified_at: str = field(default_factory=utc_now)
    invalidated_by: str | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CriterionEvidence":
        return cls(
            evidence_id=str(value.get("evidence_id") or ""),
            criterion_id=str(value.get("criterion_id") or ""),
            status=CriterionEvidenceStatus(
                str(value.get("status") or CriterionEvidenceStatus.LEGACY_UNVERIFIED.value)
            ),
            owner_task_id=str(value.get("owner_task_id") or ""),
            attempt_id=str(value.get("attempt_id") or ""),
            validation_refs=[str(item) for item in value.get("validation_refs") or []],
            artifact_refs=[str(item) for item in value.get("artifact_refs") or []],
            state_ref=(
                str(value.get("state_ref"))
                if value.get("state_ref") is not None
                else None
            ),
            verified_at=str(value.get("verified_at") or utc_now()),
            invalidated_by=(
                str(value.get("invalidated_by"))
                if value.get("invalidated_by") is not None
                else None
            ),
        )


@dataclass
class RecoveryState:
    lineage_id: str
    root_task_id: str
    failed_task_id: str
    subject_task_id: str
    failure_fingerprint: str = ""
    same_failure_count: int = 0
    decision_history: list[dict[str, Any]] = field(default_factory=list)
    remaining_budget: int = 0
    task_ids: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RecoveryState":
        return cls(
            lineage_id=str(value.get("lineage_id") or ""),
            root_task_id=str(value.get("root_task_id") or ""),
            failed_task_id=str(value.get("failed_task_id") or ""),
            subject_task_id=str(value.get("subject_task_id") or ""),
            failure_fingerprint=str(value.get("failure_fingerprint") or ""),
            same_failure_count=max(0, int(value.get("same_failure_count", 0) or 0)),
            decision_history=[
                dict(item)
                for item in value.get("decision_history") or []
                if isinstance(item, Mapping)
            ],
            remaining_budget=max(0, int(value.get("remaining_budget", 0) or 0)),
            task_ids=[str(item) for item in value.get("task_ids") or []],
            created_at=str(value.get("created_at") or utc_now()),
            updated_at=str(value.get("updated_at") or utc_now()),
        )


@dataclass
class ModelStateRef:
    state_id: str
    parent_state_id: str | None
    lane: str
    model: str
    digest: str
    token_count: int
    durable_ref: str | None
    created_at: str = field(default_factory=utc_now)
    status: str = "active"
    transport: str = "recurrent_handle"

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelStateRef":
        return cls(
            state_id=str(value.get("state_id") or ""),
            parent_state_id=(
                str(value.get("parent_state_id"))
                if value.get("parent_state_id") is not None
                else None
            ),
            lane=str(value.get("lane") or ""),
            model=str(value.get("model") or ""),
            digest=str(value.get("digest") or ""),
            token_count=max(0, int(value.get("token_count", 0) or 0)),
            durable_ref=(
                str(value.get("durable_ref"))
                if value.get("durable_ref") is not None
                else None
            ),
            created_at=str(value.get("created_at") or utc_now()),
            status=str(value.get("status") or "active"),
            transport=str(value.get("transport") or "recurrent_handle"),
        )


@dataclass
class Attempt:
    attempt_id: str
    task_id: str
    status: AttemptStatus
    action_fingerprint: str
    idempotency_key: str
    started_at: str
    ended_at: str | None = None
    request_ids: list[str] = field(default_factory=list)
    tool_result: dict[str, Any] | None = None
    artifact_refs: list[str] = field(default_factory=list)
    validation_results: list[ValidationResult] = field(default_factory=list)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        value = asdict(self)
        value["status"] = self.status.value
        return value

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "Attempt":
        return cls(
            attempt_id=str(value.get("attempt_id") or ""),
            task_id=str(value.get("task_id") or ""),
            status=AttemptStatus(str(value.get("status") or AttemptStatus.RUNNING.value)),
            action_fingerprint=str(value.get("action_fingerprint") or ""),
            idempotency_key=str(value.get("idempotency_key") or ""),
            started_at=str(value.get("started_at") or ""),
            ended_at=str(value.get("ended_at")) if value.get("ended_at") else None,
            request_ids=[str(item) for item in value.get("request_ids") or []],
            tool_result=(
                dict(value["tool_result"])
                if isinstance(value.get("tool_result"), Mapping)
                else None
            ),
            artifact_refs=[str(item) for item in value.get("artifact_refs") or []],
            validation_results=[
                ValidationResult.from_dict(item)
                for item in value.get("validation_results") or []
                if isinstance(item, Mapping)
            ],
            error=dict(value["error"]) if isinstance(value.get("error"), Mapping) else None,
        )


@dataclass
class ArtifactRecord:
    artifact_id: str
    task_id: str
    path: str
    sha256: str
    media_type: str = "application/octet-stream"
    summary: str = ""
    created_at: str = field(default_factory=utc_now)


@dataclass
class MemoryEntry:
    memory_id: str
    kind: str
    task_id: str
    summary: str
    content: str = ""
    artifact_refs: list[str] = field(default_factory=list)
    evidence_refs: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    token_estimate: int = 0
    created_at: str = field(default_factory=utc_now)


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


@dataclass
class RunState:
    run_id: str
    goal: GoalState
    revision: int = 0
    status: RunStatus = RunStatus.INITIALIZED
    tasks: dict[str, TaskNode] = field(default_factory=dict)
    attempts: dict[str, Attempt] = field(default_factory=dict)
    active_task_id: str | None = None
    plan_generation: int = 0
    memory_index: dict[str, MemoryEntry] = field(default_factory=dict)
    artifacts: dict[str, ArtifactRecord] = field(default_factory=dict)
    criterion_evidence: dict[str, CriterionEvidence] = field(default_factory=dict)
    recovery_states: dict[str, RecoveryState] = field(default_factory=dict)
    model_states: dict[str, ModelStateRef] = field(default_factory=dict)
    next_task_sequence: int = 1
    temp_decisions: list[TempDecision] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: str = RUN_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "revision": self.revision,
            "status": self.status.value,
            "goal": self.goal.to_dict(),
            "tasks": {key: value.to_dict() for key, value in self.tasks.items()},
            "attempts": {key: value.to_dict() for key, value in self.attempts.items()},
            "active_task_id": self.active_task_id,
            "plan_generation": self.plan_generation,
            "memory_index": {key: asdict(value) for key, value in self.memory_index.items()},
            "artifacts": {key: asdict(value) for key, value in self.artifacts.items()},
            "criterion_evidence": {
                key: value.to_dict() for key, value in self.criterion_evidence.items()
            },
            "recovery_states": {
                key: asdict(value) for key, value in self.recovery_states.items()
            },
            "model_states": {
                key: asdict(value) for key, value in self.model_states.items()
            },
            "next_task_sequence": self.next_task_sequence,
            "temp_decisions": [asdict(value) for value in self.temp_decisions],
            "errors": list(self.errors),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunState":
        schema_version = str(value.get("schema_version") or "")
        if schema_version not in {LEGACY_RUN_SCHEMA_VERSION, RUN_SCHEMA_VERSION}:
            raise ValueError(f"unsupported run schema: {schema_version}")
        state = cls(
            schema_version=RUN_SCHEMA_VERSION,
            run_id=str(value.get("run_id") or ""),
            revision=int(value.get("revision", 0) or 0),
            status=RunStatus(str(value.get("status") or RunStatus.INITIALIZED.value)),
            goal=GoalState.from_dict(value.get("goal") or {}),
            tasks={
                str(key): TaskNode.from_dict(item)
                for key, item in (value.get("tasks") or {}).items()
                if isinstance(item, Mapping)
            },
            attempts={
                str(key): Attempt.from_dict(item)
                for key, item in (value.get("attempts") or {}).items()
                if isinstance(item, Mapping)
            },
            active_task_id=(
                str(value.get("active_task_id"))
                if value.get("active_task_id") is not None
                else None
            ),
            plan_generation=int(value.get("plan_generation", 0) or 0),
            memory_index={
                str(key): MemoryEntry(**dict(item))
                for key, item in (value.get("memory_index") or {}).items()
                if isinstance(item, Mapping)
            },
            artifacts={
                str(key): ArtifactRecord(**dict(item))
                for key, item in (value.get("artifacts") or {}).items()
                if isinstance(item, Mapping)
            },
            criterion_evidence={
                str(key): CriterionEvidence.from_dict(item)
                for key, item in (value.get("criterion_evidence") or {}).items()
                if isinstance(item, Mapping)
            },
            recovery_states={
                str(key): RecoveryState.from_dict(item)
                for key, item in (value.get("recovery_states") or {}).items()
                if isinstance(item, Mapping)
            },
            model_states={
                str(key): ModelStateRef.from_dict(item)
                for key, item in (value.get("model_states") or {}).items()
                if isinstance(item, Mapping)
            },
            next_task_sequence=max(1, int(value.get("next_task_sequence", 1) or 1)),
            temp_decisions=[
                TempDecision(**dict(item))
                for item in value.get("temp_decisions") or []
                if isinstance(item, Mapping)
            ],
            errors=[dict(item) for item in value.get("errors") or [] if isinstance(item, Mapping)],
            created_at=str(value.get("created_at") or ""),
            updated_at=str(value.get("updated_at") or ""),
        )
        if schema_version == LEGACY_RUN_SCHEMA_VERSION:
            # V1 task goal_criteria were ambiguous planning declarations. They
            # are deliberately not promoted to verified completion evidence.
            # Already-completed runs remain readable; unfinished runs fail
            # closed until new v2 evidence is established.
            for task in state.tasks.values():
                task.satisfies_criteria = []
            state.next_task_sequence = _next_task_sequence(state.tasks)
        return state


def _next_task_sequence(tasks: Mapping[str, TaskNode]) -> int:
    highest = 0
    for task_id in tasks:
        if task_id.startswith("T") and task_id[1:].isdigit():
            highest = max(highest, int(task_id[1:]))
    return highest + 1


def action_fingerprint(action: TaskAction) -> str:
    return _canonical_digest(
        {
            "type": action.action_type,
            "arguments": action.arguments,
        }
    )


__all__ = [
    "ArtifactRecord",
    "Attempt",
    "AttemptStatus",
    "CriterionEvidence",
    "CriterionEvidenceStatus",
    "GOAL_SCHEMA_VERSION",
    "GoalCriterion",
    "GoalState",
    "MemoryEntry",
    "ModelStateRef",
    "LEGACY_RUN_SCHEMA_VERSION",
    "RUN_SCHEMA_VERSION",
    "RetryPolicy",
    "RecoveryState",
    "RunState",
    "RunStatus",
    "TaskAction",
    "TaskNode",
    "TaskStatus",
    "TempDecision",
    "ValidationResult",
    "ValidationSpec",
    "action_fingerprint",
    "utc_now",
]
