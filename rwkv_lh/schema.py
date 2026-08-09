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
RUN_SCHEMA_VERSION = "long-horizon.run.v1"


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
    goal_criteria: list[str] = field(default_factory=list)
    priority: int = 50
    inputs: list[dict[str, Any]] = field(default_factory=list)
    action: TaskAction = field(default_factory=lambda: TaskAction(""))
    completion_criteria: list[ValidationSpec] = field(default_factory=list)
    retry_policy: RetryPolicy = field(default_factory=RetryPolicy)
    attempt_ids: list[str] = field(default_factory=list)
    output_refs: list[str] = field(default_factory=list)
    error: dict[str, Any] | None = None
    superseded_by: str | None = None
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
            insertion_order=int(value.get("insertion_order", 0) or 0),
        )


@dataclass
class ValidationResult:
    kind: str
    passed: bool
    required: bool
    message: str = ""
    evidence: dict[str, Any] = field(default_factory=dict)
    checked_at: str = field(default_factory=utc_now)


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
                ValidationResult(**dict(item))
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
            "temp_decisions": [asdict(value) for value in self.temp_decisions],
            "errors": list(self.errors),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RunState":
        schema_version = str(value.get("schema_version") or "")
        if schema_version != RUN_SCHEMA_VERSION:
            raise ValueError(f"unsupported run schema: {schema_version}")
        return cls(
            schema_version=schema_version,
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
            temp_decisions=[
                TempDecision(**dict(item))
                for item in value.get("temp_decisions") or []
                if isinstance(item, Mapping)
            ],
            errors=[dict(item) for item in value.get("errors") or [] if isinstance(item, Mapping)],
            created_at=str(value.get("created_at") or ""),
            updated_at=str(value.get("updated_at") or ""),
        )


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
    "GOAL_SCHEMA_VERSION",
    "GoalCriterion",
    "GoalState",
    "MemoryEntry",
    "RUN_SCHEMA_VERSION",
    "RetryPolicy",
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
