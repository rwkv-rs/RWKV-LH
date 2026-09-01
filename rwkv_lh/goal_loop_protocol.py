"""Frozen structured protocol for the RWKV Stateful Goal Loop v2.

The protocol is deliberately small.  It records a rolling plan and one
evidence-bound audit verdict; it does not introduce another execution graph or
grant a model output authority over Harness facts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import (
    ModelIOError,
    canonical_digest,
    parse_model_command_with_trace,
)
from rwkv_lh.operation_contracts import (
    PATH_MUTATION_ARGUMENTS,
    PATH_MUTATION_OPERATIONS,
)
from rwkv_lh.schema import ActionStatus, RunState


GOAL_AUDIT_SCHEMA_VERSION = "rwkv-lh.goal-audit-decision.v1"
GOAL_AUDIT_OPERATION = "audit_decision"
LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION = "rwkv-lh.goal-plan-patch.v1"
GOAL_PLAN_PATCH_SCHEMA_VERSION = "rwkv-lh.goal-plan-patch.v2"
GOAL_STAGE_REVIEW_SCHEMA_VERSION = "rwkv-lh.goal-stage-review.v1"
GOAL_AUDIT_DEFINITION: dict[str, Any] = {
    "name": GOAL_AUDIT_OPERATION,
    "description": (
        "Audit one committed Goal boundary. This reports evidence and gaps only; "
        "it never executes an action or changes Harness facts."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["continue", "repair", "ready_for_final"],
            },
            "step_id": {"type": "string"},
            "step_complete": {"type": "boolean"},
            "evidence_refs": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
                "maxItems": 8,
            },
            "gaps": {
                "type": "array",
                "items": {"type": "string", "minLength": 1},
                "uniqueItems": True,
                "maxItems": 8,
            },
            "reason": {"type": "string", "minLength": 1, "maxLength": 800},
        },
        "required": [
            "verdict",
            "step_id",
            "step_complete",
            "evidence_refs",
            "gaps",
            "reason",
        ],
        "additionalProperties": False,
    },
}


def _non_empty(value: Any, field_name: str) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{field_name} must be non-empty")
    return text


def _root_parts(value: str) -> tuple[str, ...]:
    raw = str(value or "").strip().replace("\\", "/")
    if raw == ".":
        return ()
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\x00" in raw:
        raise ValueError(f"plan root must be workspace-relative: {value!r}")
    return tuple(part for part in path.parts if part not in {"", "."})


def _roots_overlap(left: str, right: str) -> bool:
    if left == "." or right == ".":
        return True
    left_parts = _root_parts(left)
    right_parts = _root_parts(right)
    width = min(len(left_parts), len(right_parts))
    return bool(width and left_parts[:width] == right_parts[:width])


def parse_json_object(raw_output: str) -> dict[str, Any]:
    """Parse one model JSON object, allowing only a surrounding Markdown fence."""

    text = str(raw_output or "").strip()
    if text.startswith("```") and text.endswith("```"):
        lines = text.splitlines()
        if len(lines) < 3:
            raise ValueError("structured model output fence is incomplete")
        text = "\n".join(lines[1:-1]).strip()
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ValueError("structured model output is not one JSON object") from exc
    if not isinstance(value, Mapping):
        raise ValueError("structured model output must be a JSON object")
    return dict(value)


@dataclass(frozen=True)
class GoalPlanStep:
    step_id: str
    objective: str
    stage: int = 1
    depends_on: tuple[str, ...] = ()
    success_evidence: tuple[str, ...] = ()
    obligation_ids: tuple[str, ...] = ()
    read_roots: tuple[str, ...] = ()
    write_roots: tuple[str, ...] = ()
    allowed_operations: tuple[str, ...] = ()
    constraints: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _non_empty(self.step_id, "step_id"))
        object.__setattr__(self, "objective", _non_empty(self.objective, "objective"))
        if (
            isinstance(self.stage, bool)
            or not isinstance(self.stage, int)
            or self.stage < 1
        ):
            raise ValueError("plan step stage must be a positive integer")
        dependencies = tuple(_non_empty(item, "depends_on item") for item in self.depends_on)
        evidence = tuple(
            _non_empty(item, "success_evidence item") for item in self.success_evidence
        )
        obligation_ids = tuple(
            _non_empty(item, "obligation_id") for item in self.obligation_ids
        )
        read_roots = tuple(_non_empty(item, "read_root") for item in self.read_roots)
        write_roots = tuple(
            _non_empty(item, "write_root") for item in self.write_roots
        )
        for root in (*read_roots, *write_roots):
            _root_parts(root)
        allowed_operations = tuple(
            _non_empty(item, "allowed_operation") for item in self.allowed_operations
        )
        constraints = tuple(
            _non_empty(item, "constraint") for item in self.constraints
        )
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("plan step dependencies must be unique")
        for field_name, selected in (
            ("obligation_ids", obligation_ids),
            ("read_roots", read_roots),
            ("write_roots", write_roots),
            ("allowed_operations", allowed_operations),
            ("constraints", constraints),
        ):
            if len(set(selected)) != len(selected):
                raise ValueError(f"plan step {field_name} must be unique")
        if self.step_id in dependencies:
            raise ValueError("plan step cannot depend on itself")
        if not evidence:
            raise ValueError("plan step requires at least one success evidence criterion")
        object.__setattr__(self, "depends_on", dependencies)
        object.__setattr__(self, "success_evidence", evidence)
        object.__setattr__(self, "obligation_ids", obligation_ids)
        object.__setattr__(self, "read_roots", read_roots)
        object.__setattr__(self, "write_roots", write_roots)
        object.__setattr__(self, "allowed_operations", allowed_operations)
        object.__setattr__(self, "constraints", constraints)

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_id": self.step_id,
            "objective": self.objective,
            "stage": self.stage,
            "depends_on": list(self.depends_on),
            "success_evidence": list(self.success_evidence),
            "obligation_ids": list(self.obligation_ids),
            "read_roots": list(self.read_roots),
            "write_roots": list(self.write_roots),
            "allowed_operations": list(self.allowed_operations),
            "constraints": list(self.constraints),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalPlanStep":
        return cls(
            step_id=str(value.get("step_id") or ""),
            objective=str(value.get("objective") or ""),
            stage=int(value.get("stage", 1) or 1),
            depends_on=tuple(str(item) for item in value.get("depends_on") or ()),
            success_evidence=tuple(
                str(item) for item in value.get("success_evidence") or ()
            ),
            obligation_ids=tuple(
                str(item) for item in value.get("obligation_ids") or ()
            ),
            read_roots=tuple(str(item) for item in value.get("read_roots") or ()),
            write_roots=tuple(str(item) for item in value.get("write_roots") or ()),
            allowed_operations=tuple(
                str(item) for item in value.get("allowed_operations") or ()
            ),
            constraints=tuple(str(item) for item in value.get("constraints") or ()),
        )


@dataclass(frozen=True)
class GoalPlanPatch:
    """One native rolling-plan delta produced by the Strong Planner.

    The model supplies only the semantic change.  The Controller binds the
    patch identity and base revision, so retries cannot invent graph history.
    Completed steps are immutable; open steps may be replaced or discarded.
    """

    patch_id: str
    base_revision: int
    add_steps: tuple[GoalPlanStep, ...]
    replace_steps: tuple[GoalPlanStep, ...]
    discard_step_ids: tuple[str, ...]
    reason: str
    schema_version: str = GOAL_PLAN_PATCH_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GOAL_PLAN_PATCH_SCHEMA_VERSION:
            raise ValueError("unsupported Goal PlanPatch schema")
        object.__setattr__(self, "patch_id", _non_empty(self.patch_id, "patch_id"))
        object.__setattr__(self, "reason", _non_empty(self.reason, "reason"))
        if isinstance(self.base_revision, bool) or self.base_revision < 0:
            raise ValueError("Goal PlanPatch base_revision must be non-negative")
        added_ids = tuple(item.step_id for item in self.add_steps)
        replaced_ids = tuple(item.step_id for item in self.replace_steps)
        discarded_ids = tuple(
            _non_empty(item, "discard_step_id") for item in self.discard_step_ids
        )
        for name, values in (
            ("add_steps", added_ids),
            ("replace_steps", replaced_ids),
            ("discard_step_ids", discarded_ids),
        ):
            if len(set(values)) != len(values):
                raise ValueError(f"Goal PlanPatch {name} contains duplicate ids")
        if set(replaced_ids) & set(discarded_ids):
            raise ValueError("Goal PlanPatch cannot replace and discard the same step")
        if set(added_ids) & set(replaced_ids):
            raise ValueError("Goal PlanPatch add/replace step ids must be disjoint")
        if not (self.add_steps or self.replace_steps or discarded_ids):
            raise ValueError("Goal PlanPatch must change at least one open step")
        if len(self.add_steps) + len(self.replace_steps) > 5:
            raise ValueError("Goal PlanPatch may introduce at most five current steps")
        object.__setattr__(self, "discard_step_ids", discarded_ids)

    @classmethod
    def from_model_value(
        cls,
        value: Mapping[str, Any],
        *,
        patch_id: str,
        base_revision: int,
    ) -> "GoalPlanPatch":
        expected = {"add_stages", "replace_stages", "discard_step_ids", "reason"}
        if set(value) != expected:
            raise ValueError(
                "Goal PlanPatch requires exactly add_stages, replace_stages, "
                "discard_step_ids, and reason"
            )

        def steps(field_name: str) -> tuple[GoalPlanStep, ...]:
            raw = value.get(field_name)
            if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes)):
                raise ValueError(f"Goal PlanPatch {field_name} must be an array")
            flattened: list[GoalPlanStep] = []
            seen_stages: set[int] = set()
            for item in raw:
                if not isinstance(item, Mapping) or set(item) != {"stage", "steps"}:
                    raise ValueError(
                        f"Goal PlanPatch {field_name} stages require stage and steps"
                    )
                stage = item.get("stage")
                if isinstance(stage, bool) or not isinstance(stage, int) or stage < 1:
                    raise ValueError(
                        f"Goal PlanPatch {field_name} stage must be positive"
                    )
                if stage in seen_stages:
                    raise ValueError(
                        f"Goal PlanPatch {field_name} contains duplicate stage {stage}"
                    )
                seen_stages.add(stage)
                raw_steps = item.get("steps")
                if not isinstance(raw_steps, Sequence) or isinstance(
                    raw_steps, (str, bytes)
                ):
                    raise ValueError(
                        f"Goal PlanPatch {field_name} stage steps must be an array"
                    )
                if not raw_steps:
                    raise ValueError(
                        f"Goal PlanPatch {field_name} cannot contain an empty stage"
                    )
                for raw_step in raw_steps:
                    if not isinstance(raw_step, Mapping):
                        raise ValueError(
                            f"Goal PlanPatch {field_name} steps must be objects"
                        )
                    if "stage" in raw_step:
                        raise ValueError("nested Goal plan step must not repeat stage")
                    flattened.append(
                        GoalPlanStep.from_dict({**dict(raw_step), "stage": stage})
                    )
            return tuple(flattened)

        raw_discarded = value.get("discard_step_ids")
        if not isinstance(raw_discarded, Sequence) or isinstance(
            raw_discarded, (str, bytes)
        ):
            raise ValueError("Goal PlanPatch discard_step_ids must be an array")
        return cls(
            patch_id=patch_id,
            base_revision=base_revision,
            add_steps=steps("add_stages"),
            replace_steps=steps("replace_stages"),
            discard_step_ids=tuple(str(item) for item in raw_discarded),
            reason=str(value.get("reason") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        def stages(steps: Sequence[GoalPlanStep]) -> list[dict[str, Any]]:
            selected: list[dict[str, Any]] = []
            for stage in sorted({step.stage for step in steps}):
                selected.append(
                    {
                        "stage": stage,
                        "steps": [
                            {
                                key: item
                                for key, item in step.to_dict().items()
                                if key != "stage"
                            }
                            for step in steps
                            if step.stage == stage
                        ],
                    }
                )
            return selected

        return {
            "schema_version": self.schema_version,
            "patch_id": self.patch_id,
            "base_revision": self.base_revision,
            "add_stages": stages(self.add_steps),
            "replace_stages": stages(self.replace_steps),
            "discard_step_ids": list(self.discard_step_ids),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalPlanPatch":
        schema_version = str(value.get("schema_version") or "")
        if schema_version not in {
            LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION,
            GOAL_PLAN_PATCH_SCHEMA_VERSION,
        }:
            raise ValueError("unsupported Goal PlanPatch schema")
        # Durable v1 events used flat arrays before the model-visible protocol
        # became nested by stage. Keep replay compatibility without exposing the
        # old shape to the Planner.
        if schema_version == LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION:
            raw_added = value.get("add_steps") or ()
            raw_replaced = value.get("replace_steps") or ()
            if any(not isinstance(item, Mapping) for item in (*raw_added, *raw_replaced)):
                raise ValueError("durable Goal PlanPatch steps must be objects")
            return cls(
                patch_id=str(value.get("patch_id") or ""),
                base_revision=int(value.get("base_revision", -1)),
                add_steps=tuple(GoalPlanStep.from_dict(item) for item in raw_added),
                replace_steps=tuple(
                    GoalPlanStep.from_dict(item) for item in raw_replaced
                ),
                discard_step_ids=tuple(
                    str(item) for item in value.get("discard_step_ids") or ()
                ),
                reason=str(value.get("reason") or ""),
            )
        return cls.from_model_value(
            {
                key: value.get(key)
                for key in (
                    "add_stages",
                    "replace_stages",
                    "discard_step_ids",
                    "reason",
                )
            },
            patch_id=str(value.get("patch_id") or ""),
            base_revision=int(value.get("base_revision", -1)),
        )


@dataclass(frozen=True)
class GoalPlanRequest:
    """Bounded materials for one Strong-Planner call."""

    run_id: str
    immutable_request: str
    goal_digest: str
    plan_revision: int
    active_plan: Mapping[str, Any]
    latest_audit: Mapping[str, Any] | None
    workspace_manifest: Mapping[str, Any]
    latest_stage_review: Mapping[str, Any] | None = None
    recent_action_facts: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.run_id, "run_id")
        _non_empty(self.immutable_request, "immutable_request")
        _non_empty(self.goal_digest, "goal_digest")
        if isinstance(self.plan_revision, bool) or self.plan_revision < 0:
            raise ValueError("Goal plan revision must be non-negative")
        if len(self.recent_action_facts) > 12:
            raise ValueError("Goal Planner request exposes at most twelve action facts")

    def to_dict(self) -> dict[str, Any]:
        # Materials first; the one current planning requirement is deliberately
        # the final field next to the strong model's continuation point.
        return {
            "run_id": self.run_id,
            "goal_digest": self.goal_digest,
            "plan_revision": self.plan_revision,
            "active_plan": dict(self.active_plan),
            "latest_audit": (
                dict(self.latest_audit) if self.latest_audit is not None else None
            ),
            "latest_stage_review": (
                dict(self.latest_stage_review)
                if self.latest_stage_review is not None
                else None
            ),
            "workspace_manifest": dict(self.workspace_manifest),
            "recent_action_facts": [dict(item) for item in self.recent_action_facts],
            "current_requirement": self.immutable_request,
        }


class GoalStageReviewVerdict(str, Enum):
    ADVANCE = "advance"
    REPAIR = "repair"


@dataclass(frozen=True)
class GoalStageReviewRequest:
    """Evidence-bound material for one read-only Strong stage check."""

    run_id: str
    immutable_request: str
    goal_digest: str
    stage: int
    stage_steps: tuple[Mapping[str, Any], ...]
    workspace_manifest: Mapping[str, Any]
    recent_action_facts: tuple[Mapping[str, Any], ...] = ()

    def __post_init__(self) -> None:
        _non_empty(self.run_id, "run_id")
        _non_empty(self.immutable_request, "immutable_request")
        _non_empty(self.goal_digest, "goal_digest")
        if (
            isinstance(self.stage, bool)
            or not isinstance(self.stage, int)
            or self.stage < 1
        ):
            raise ValueError("Goal stage review requires a positive stage")
        if not self.stage_steps:
            raise ValueError("Goal stage review requires completed stage steps")
        if len(self.stage_steps) > 5:
            raise ValueError("Goal stage review exposes at most five steps")
        if len(self.recent_action_facts) > 12:
            raise ValueError("Goal stage review exposes at most twelve action facts")

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "goal_digest": self.goal_digest,
            "stage": self.stage,
            "stage_steps": [dict(item) for item in self.stage_steps],
            "workspace_manifest": dict(self.workspace_manifest),
            "recent_action_facts": [dict(item) for item in self.recent_action_facts],
            # Materials first; the goal remains next to the continuation point.
            "current_requirement": self.immutable_request,
        }


@dataclass(frozen=True)
class GoalStageReview:
    """One Strong-model stage verdict with Controller-bound provenance."""

    review_id: str
    stage: int
    verdict: GoalStageReviewVerdict
    reviewed_step_ids: tuple[str, ...]
    evidence_refs: tuple[str, ...]
    gaps: tuple[str, ...]
    reason: str
    schema_version: str = GOAL_STAGE_REVIEW_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GOAL_STAGE_REVIEW_SCHEMA_VERSION:
            raise ValueError("unsupported Goal stage review schema")
        object.__setattr__(self, "review_id", _non_empty(self.review_id, "review_id"))
        object.__setattr__(self, "reason", _non_empty(self.reason, "reason"))
        if (
            isinstance(self.stage, bool)
            or not isinstance(self.stage, int)
            or self.stage < 1
        ):
            raise ValueError("Goal stage review requires a positive stage")
        step_ids = tuple(
            _non_empty(item, "reviewed_step_id") for item in self.reviewed_step_ids
        )
        refs = tuple(_non_empty(item, "evidence_ref") for item in self.evidence_refs)
        gaps = tuple(_non_empty(item, "gap") for item in self.gaps)
        if not step_ids or len(set(step_ids)) != len(step_ids):
            raise ValueError("Goal stage review requires unique reviewed steps")
        if not refs or len(set(refs)) != len(refs):
            raise ValueError("Goal stage review requires unique evidence refs")
        if len(set(gaps)) != len(gaps):
            raise ValueError("Goal stage review gaps must be unique")
        if self.verdict is GoalStageReviewVerdict.ADVANCE and gaps:
            raise ValueError("advance stage review cannot retain gaps")
        if self.verdict is GoalStageReviewVerdict.REPAIR and not gaps:
            raise ValueError("repair stage review requires at least one gap")
        object.__setattr__(self, "reviewed_step_ids", step_ids)
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "gaps", gaps)

    @classmethod
    def from_model_value(
        cls,
        value: Mapping[str, Any],
        *,
        review_id: str,
        stage: int,
        reviewed_step_ids: Sequence[str],
        evidence_refs: Sequence[str],
    ) -> "GoalStageReview":
        if set(value) != {"verdict", "gaps", "reason"}:
            raise ValueError(
                "Goal stage review requires exactly verdict, gaps, and reason"
            )
        raw_gaps = value.get("gaps")
        if not isinstance(raw_gaps, Sequence) or isinstance(raw_gaps, (str, bytes)):
            raise ValueError("Goal stage review gaps must be an array")
        return cls(
            review_id=review_id,
            stage=stage,
            verdict=GoalStageReviewVerdict(str(value.get("verdict") or "")),
            reviewed_step_ids=tuple(str(item) for item in reviewed_step_ids),
            evidence_refs=tuple(str(item) for item in evidence_refs),
            gaps=tuple(str(item) for item in raw_gaps),
            reason=str(value.get("reason") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "stage": self.stage,
            "verdict": self.verdict.value,
            "reviewed_step_ids": list(self.reviewed_step_ids),
            "evidence_refs": list(self.evidence_refs),
            "gaps": list(self.gaps),
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalStageReview":
        if str(value.get("schema_version") or "") != GOAL_STAGE_REVIEW_SCHEMA_VERSION:
            raise ValueError("unsupported Goal stage review schema")
        return cls(
            review_id=str(value.get("review_id") or ""),
            stage=int(value.get("stage", 0) or 0),
            verdict=GoalStageReviewVerdict(str(value.get("verdict") or "")),
            reviewed_step_ids=tuple(
                str(item) for item in value.get("reviewed_step_ids") or ()
            ),
            evidence_refs=tuple(
                str(item) for item in value.get("evidence_refs") or ()
            ),
            gaps=tuple(str(item) for item in value.get("gaps") or ()),
            reason=str(value.get("reason") or ""),
        )


class GoalAuditVerdict(str, Enum):
    CONTINUE = "continue"
    REPAIR = "repair"
    READY_FOR_FINAL = "ready_for_final"


@dataclass(frozen=True)
class AuditedStep:
    step_id: str
    evidence_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "step_id", _non_empty(self.step_id, "step_id"))
        refs = tuple(_non_empty(item, "evidence_ref") for item in self.evidence_refs)
        if not refs or len(set(refs)) != len(refs):
            raise ValueError("completed audit step requires unique evidence refs")
        object.__setattr__(self, "evidence_refs", refs)

    def to_dict(self) -> dict[str, Any]:
        return {"step_id": self.step_id, "evidence_refs": list(self.evidence_refs)}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "AuditedStep":
        return cls(
            step_id=str(value.get("step_id") or ""),
            evidence_refs=tuple(str(item) for item in value.get("evidence_refs") or ()),
        )


@dataclass(frozen=True)
class GoalAuditDecision:
    audit_id: str
    verdict: GoalAuditVerdict
    step_id: str
    evidence_refs: tuple[str, ...]
    gaps: tuple[str, ...]
    completed_steps: tuple[AuditedStep, ...]
    reason: str
    schema_version: str = GOAL_AUDIT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != GOAL_AUDIT_SCHEMA_VERSION:
            raise ValueError("unsupported Goal AuditDecision schema")
        object.__setattr__(self, "audit_id", _non_empty(self.audit_id, "audit_id"))
        object.__setattr__(self, "reason", _non_empty(self.reason, "reason"))
        refs = tuple(_non_empty(item, "evidence_ref") for item in self.evidence_refs)
        gaps = tuple(_non_empty(item, "gap") for item in self.gaps)
        if len(set(refs)) != len(refs) or len(set(gaps)) != len(gaps):
            raise ValueError("audit evidence refs and gaps must be unique")
        step_ids = tuple(item.step_id for item in self.completed_steps)
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("audit completed step ids must be unique")
        if self.verdict is GoalAuditVerdict.READY_FOR_FINAL and gaps:
            raise ValueError("ready_for_final audit cannot retain gaps")
        if self.verdict is GoalAuditVerdict.REPAIR and not gaps:
            raise ValueError("repair audit requires at least one gap")
        object.__setattr__(self, "step_id", str(self.step_id or "").strip())
        object.__setattr__(self, "evidence_refs", refs)
        object.__setattr__(self, "gaps", gaps)

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "audit_id": self.audit_id,
            "verdict": self.verdict.value,
            "step_id": self.step_id,
            "evidence_refs": list(self.evidence_refs),
            "gaps": list(self.gaps),
            "completed_steps": [item.to_dict() for item in self.completed_steps],
            "reason": self.reason,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "GoalAuditDecision":
        raw_completed = value.get("completed_steps") or ()
        if not isinstance(raw_completed, Sequence) or isinstance(
            raw_completed, (str, bytes)
        ):
            raise ValueError("audit completed_steps must be an array")
        if any(not isinstance(item, Mapping) for item in raw_completed):
            raise ValueError("audit completed_steps must contain objects")
        return cls(
            schema_version=str(value.get("schema_version") or ""),
            audit_id=str(value.get("audit_id") or ""),
            verdict=GoalAuditVerdict(str(value.get("verdict") or "")),
            step_id=str(value.get("step_id") or ""),
            evidence_refs=tuple(str(item) for item in value.get("evidence_refs") or ()),
            gaps=tuple(str(item) for item in value.get("gaps") or ()),
            completed_steps=tuple(AuditedStep.from_dict(item) for item in raw_completed),
            reason=str(value.get("reason") or ""),
        )

    @classmethod
    def parse(cls, raw_output: str) -> "GoalAuditDecision":
        return cls.from_dict(parse_json_object(raw_output))

    @classmethod
    def parse_with_bindings(
        cls,
        raw_output: str,
        *,
        audit_id: str,
    ) -> tuple["GoalAuditDecision", tuple[str, ...]]:
        """Parse the minimal RWKV audit call and bind kernel-owned identity."""

        bound_audit_id = _non_empty(audit_id, "audit_id")
        value = parse_json_object(raw_output)
        bindings: list[str] = []
        if any(key in value for key in ("function", "name", "tool", "function_call")):
            try:
                command, _normalization = parse_model_command_with_trace(raw_output)
            except ModelIOError as exc:
                raise ValueError(str(exc)) from exc
            if command.name != GOAL_AUDIT_OPERATION:
                raise ValueError(
                    f"audit fork must call {GOAL_AUDIT_OPERATION!r}"
                )
            value = dict(command.arguments)
            bindings.append("audit_decision_function_envelope")

        expected = {
            "verdict",
            "step_id",
            "step_complete",
            "evidence_refs",
            "gaps",
            "reason",
        }
        if set(value) != expected:
            raise ValueError(
                "audit decision requires exactly verdict, step_id, step_complete, "
                "evidence_refs, gaps, and reason"
            )
        if not isinstance(value.get("step_complete"), bool):
            raise ValueError("audit step_complete must be boolean")
        step_id = str(value.get("step_id") or "").strip()
        refs = tuple(str(item) for item in value.get("evidence_refs") or ())
        completed: tuple[AuditedStep, ...] = ()
        if value["step_complete"]:
            if not step_id or not refs:
                raise ValueError(
                    "completed audit step requires step_id and evidence_refs"
                )
            completed = (AuditedStep(step_id=step_id, evidence_refs=refs),)
            bindings.append("completed_steps_projection")
        verdict = GoalAuditVerdict(str(value.get("verdict") or ""))
        if verdict is GoalAuditVerdict.REPAIR and value["step_complete"]:
            raise ValueError("repair audit cannot mark the active step complete")
        if verdict is GoalAuditVerdict.READY_FOR_FINAL and (
            step_id or value["step_complete"]
        ):
            raise ValueError(
                "ready_for_final audit requires empty step_id and incomplete step flag"
            )
        bindings.extend(("audit_id", "schema_version"))
        return (
            cls(
                audit_id=bound_audit_id,
                verdict=verdict,
                step_id=step_id,
                evidence_refs=refs,
                gaps=tuple(str(item) for item in value.get("gaps") or ()),
                completed_steps=completed,
                reason=str(value.get("reason") or ""),
            ),
            tuple(bindings),
        )


@dataclass
class RollingGoalPlan:
    goal_digest: str
    steps: dict[str, GoalPlanStep] = field(default_factory=dict)
    completed_evidence: dict[str, tuple[str, ...]] = field(default_factory=dict)
    patch_ids: list[str] = field(default_factory=list)
    step_revisions: dict[str, int] = field(default_factory=dict)
    discarded_step_ids: set[str] = field(default_factory=set)
    obligation_ids: set[str] = field(default_factory=set)
    contract_node_ids: set[str] = field(default_factory=set)

    @property
    def completed_step_ids(self) -> frozenset[str]:
        return frozenset(self.completed_evidence)

    @property
    def open_step_ids(self) -> tuple[str, ...]:
        return tuple(
            step_id
            for step_id in self.steps
            if step_id not in self.completed_evidence
        )

    @property
    def current_stage(self) -> int | None:
        stages = [self.steps[step_id].stage for step_id in self.open_step_ids]
        return min(stages) if stages else None

    @property
    def frontier(self) -> tuple[GoalPlanStep, ...]:
        completed = self.completed_step_ids
        current_stage = self.current_stage
        return tuple(
            self.steps[step_id]
            for step_id in self.open_step_ids
            if self.steps[step_id].stage == current_stage
            if set(self.steps[step_id].depends_on) <= completed
        )

    @property
    def completed_stages(self) -> tuple[int, ...]:
        stages = sorted({step.stage for step in self.steps.values()})
        return tuple(
            stage
            for stage in stages
            if all(
                step.step_id in self.completed_evidence
                for step in self.steps.values()
                if step.stage == stage
            )
        )

    def stage_steps(self, stage: int) -> tuple[GoalPlanStep, ...]:
        return tuple(step for step in self.steps.values() if step.stage == stage)

    def stage_boundary_key(self, stage: int) -> str:
        steps = self.stage_steps(stage)
        if not steps or any(
            step.step_id not in self.completed_evidence for step in steps
        ):
            raise ValueError("Goal stage boundary requires evidence-complete steps")
        return canonical_digest(
            {
                "stage": stage,
                "steps": [
                    {
                        "step_id": step.step_id,
                        "step_revision": self.step_revisions.get(step.step_id, 1),
                        "evidence_refs": list(self.completed_evidence[step.step_id]),
                    }
                    for step in steps
                ],
            }
        )

    @property
    def complete(self) -> bool:
        return bool(self.steps) and not self.open_step_ids

    def apply_goal_patch(self, patch: GoalPlanPatch) -> None:
        """Atomically apply one native add/replace/discard plan delta."""

        if patch.patch_id in self.patch_ids:
            raise ValueError("Goal PlanPatch id was committed more than once")
        if patch.base_revision != len(self.patch_ids):
            raise ValueError("Goal PlanPatch base revision is stale")

        completed = set(self.completed_step_ids)
        open_ids = set(self.open_step_ids)
        replace_ids = {item.step_id for item in patch.replace_steps}
        add_ids = {item.step_id for item in patch.add_steps}
        discard_ids = set(patch.discard_step_ids)
        if not replace_ids <= open_ids:
            raise ValueError(
                "Goal PlanPatch may replace only currently open steps: "
                f"{sorted(replace_ids - open_ids)}"
            )
        if not discard_ids <= open_ids:
            raise ValueError(
                "Goal PlanPatch may discard only currently open steps: "
                f"{sorted(discard_ids - open_ids)}"
            )
        known_ids = set(self.steps) | set(self.discarded_step_ids)
        if add_ids & known_ids:
            raise ValueError(
                "Goal PlanPatch cannot reuse an existing or discarded step id: "
                f"{sorted(add_ids & known_ids)}"
            )
        if completed & (replace_ids | discard_ids):
            raise ValueError("Goal PlanPatch cannot change an evidence-complete step")

        candidate_steps = dict(self.steps)
        candidate_revisions = dict(self.step_revisions)
        for step_id in discard_ids:
            candidate_steps.pop(step_id)
            candidate_revisions.pop(step_id, None)
        for step in patch.replace_steps:
            candidate_steps[step.step_id] = step
            candidate_revisions[step.step_id] = (
                candidate_revisions.get(step.step_id, 1) + 1
            )
        for step in patch.add_steps:
            candidate_steps[step.step_id] = step
            candidate_revisions[step.step_id] = 1

        active_ids = set(candidate_steps)
        unknown_dependencies = {
            dependency
            for step in candidate_steps.values()
            for dependency in step.depends_on
            if dependency not in active_ids
        }
        if unknown_dependencies:
            raise ValueError(
                "Goal PlanPatch leaves active steps dependent on discarded or "
                f"unknown steps: {sorted(unknown_dependencies)}"
            )
        if len(
            [step_id for step_id in candidate_steps if step_id not in completed]
        ) > 5:
            raise ValueError("rolling Goal plan may expose at most five open steps")

        prior_steps = self.steps
        self.steps = candidate_steps
        try:
            self._validate_acyclic(active_ids)
            self._validate_stages(active_ids)
        except Exception:
            self.steps = prior_steps
            raise
        self.step_revisions = candidate_revisions
        self.discarded_step_ids.update(discard_ids)
        self.patch_ids.append(patch.patch_id)

    def apply_contract_patch(self, raw_patch: Mapping[str, Any], state: RunState) -> None:
        """Project the existing validated Strong Planner patch into one RWKV frontier."""

        from rwkv_lh.contract_graph import ContractGraphPatch
        from rwkv_lh.supervisor import AtomRole

        patch = ContractGraphPatch.from_dict(
            raw_patch,
            immutable_request=state.goal.request,
            request_digest=state.goal.digest,
            existing_obligation_ids=tuple(self.obligation_ids),
            existing_node_ids=tuple(self.contract_node_ids),
        )
        if patch.patch_id in self.patch_ids:
            raise ValueError("Strong Planner patch id was committed more than once")
        work_nodes = tuple(
            node for node in patch.new_nodes if node.atom.role is AtomRole.WORK
        )
        work_ids = set(self.steps) | {node.node_id for node in work_nodes}
        for node in work_nodes:
            if node.node_id in self.steps:
                raise ValueError("Strong Planner patch cannot redefine a plan step")
            dependencies = tuple(
                item for item in node.atom.depends_on if item in work_ids
            )
            self.steps[node.node_id] = GoalPlanStep(
                step_id=node.node_id,
                objective=node.atom.objective,
                depends_on=dependencies,
                success_evidence=node.atom.completion_checks,
                obligation_ids=node.obligation_ids,
                read_roots=node.atom.read_roots,
                write_roots=node.atom.write_roots,
                allowed_operations=node.atom.allowed_operations,
                constraints=node.atom.constraints,
            )
            self.step_revisions[node.node_id] = 1
        self._validate_acyclic(set(self.steps))
        self.obligation_ids.update(
            item.obligation_id for item in patch.new_obligations
        )
        self.contract_node_ids.update(item.node_id for item in patch.new_nodes)
        self.patch_ids.append(patch.patch_id)

    def apply_audit(self, audit: GoalAuditDecision) -> None:
        for completed in audit.completed_steps:
            if completed.step_id not in self.steps:
                raise ValueError("audit completed an unknown plan step")
            prior = self.completed_evidence.get(completed.step_id)
            if prior is not None and prior != completed.evidence_refs:
                raise ValueError("audit changed evidence for a completed plan step")
            self.completed_evidence[completed.step_id] = completed.evidence_refs

    def _validate_acyclic(self, active_ids: set[str]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_id: str) -> None:
            if step_id in visiting:
                raise ValueError("Goal PlanPatch introduced a dependency cycle")
            if step_id in visited:
                return
            visiting.add(step_id)
            for dependency in self.steps[step_id].depends_on:
                visit(dependency)
            visiting.remove(step_id)
            visited.add(step_id)

        for step_id in active_ids:
            visit(step_id)

    def _validate_stages(self, active_ids: set[str]) -> None:
        for step_id in active_ids:
            step = self.steps[step_id]
            wrong_stage_dependencies = [
                dependency
                for dependency in step.depends_on
                if self.steps[dependency].stage >= step.stage
            ]
            if wrong_stage_dependencies:
                raise ValueError(
                    "Goal PlanPatch dependencies must come from an earlier stage: "
                    f"{step_id!r} -> {wrong_stage_dependencies!r}"
                )

        for stage in sorted({self.steps[item].stage for item in active_ids}):
            selected = [
                self.steps[item]
                for item in active_ids
                if self.steps[item].stage == stage
            ]
            for index, left in enumerate(selected):
                for right in selected[index + 1 :]:
                    conflicts = [
                        (left_root, right_root)
                        for left_root in left.write_roots
                        for right_root in (*right.read_roots, *right.write_roots)
                        if _roots_overlap(left_root, right_root)
                    ]
                    conflicts.extend(
                        (left_root, right_root)
                        for left_root in left.read_roots
                        for right_root in right.write_roots
                        if _roots_overlap(left_root, right_root)
                    )
                    if conflicts:
                        raise ValueError(
                            "same-stage Goal steps have conflicting read/write roots: "
                            f"{left.step_id!r}, {right.step_id!r}, {conflicts!r}"
                        )

    def to_model_dict(self) -> dict[str, Any]:
        stages: list[dict[str, Any]] = []
        for stage in sorted({step.stage for step in self.steps.values()}):
            stages.append(
                {
                    "stage": stage,
                    "steps": [
                        {
                            **{
                                key: item
                                for key, item in step.to_dict().items()
                                if key != "stage"
                            },
                            "step_revision": self.step_revisions.get(
                                step.step_id, 1
                            ),
                            "status": (
                                "completed"
                                if step.step_id in self.completed_evidence
                                else "open"
                            ),
                            "accepted_evidence_refs": list(
                                self.completed_evidence.get(step.step_id, ())
                            ),
                        }
                        for step in self.steps.values()
                        if step.stage == stage
                    ],
                }
            )
        return {
            "goal_digest": self.goal_digest,
            "stages": stages,
            "frontier_step_ids": [item.step_id for item in self.frontier],
            "current_stage": self.current_stage,
            "completed_stages": list(self.completed_stages),
            "discarded_step_ids": sorted(self.discarded_step_ids),
            "plan_revision": len(self.patch_ids),
        }


def rolling_goal_plan(state: RunState) -> RollingGoalPlan:
    plan = RollingGoalPlan(goal_digest=state.goal.digest)
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type == "goal_plan_patch_committed":
            raw_patch = event.payload.get("patch")
            if not isinstance(raw_patch, Mapping):
                raise ValueError("committed Goal PlanPatch is incomplete")
            plan.apply_goal_patch(GoalPlanPatch.from_dict(raw_patch))
        elif event.event_type == "contract_graph_patch_committed":
            # Read-only replay compatibility for runs created before the native
            # rolling-plan protocol. Product planning never emits this event.
            raw_patch = event.payload.get("patch")
            if not isinstance(raw_patch, Mapping):
                raise ValueError("committed Strong Planner patch is incomplete")
            plan.apply_contract_patch(raw_patch, state)
        elif event.event_type == "goal_audit_accepted":
            raw_audit = event.payload.get("audit")
            if not isinstance(raw_audit, Mapping):
                raise ValueError("accepted audit event has no complete decision")
            plan.apply_audit(GoalAuditDecision.from_dict(raw_audit))
    return plan


def available_evidence_refs(state: RunState) -> frozenset[str]:
    """Return Harness-grounded facts that may cross an Audit evidence boundary."""

    revisions = {
        revision.revision_id
        for values in state.artifact_revisions.values()
        for revision in values
    }
    return frozenset(
        set(state.actions)
        | set(state.artifacts)
        | revisions
    )


def goal_step_action_bindings(state: RunState) -> dict[str, tuple[str, int]]:
    """Replay the durable action→plan-step-revision relation."""

    bindings: dict[str, tuple[str, int]] = {}
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type != "goal_action_plan_step_assigned":
            continue
        action_id = str(event.payload.get("action_id") or "")
        step_id = str(event.payload.get("step_id") or "")
        step_revision = int(event.payload.get("step_revision", 1) or 1)
        if (
            not action_id
            or not step_id
            or action_id not in state.actions
            or step_revision < 1
        ):
            raise ValueError("goal action assignment is incomplete")
        binding = (step_id, step_revision)
        prior = bindings.get(action_id)
        if prior is not None and prior != binding:
            raise ValueError("goal action was reassigned to another plan step")
        bindings[action_id] = binding
    return bindings


def goal_step_action_assignments(state: RunState) -> dict[str, str]:
    """Compatibility projection without the step revision."""

    return {
        action_id: binding[0]
        for action_id, binding in goal_step_action_bindings(state).items()
    }


def _relative_parts(value: object) -> tuple[str, ...]:
    raw = str(value or "").strip().replace("\\", "/")
    path = PurePosixPath(raw)
    if not raw or path.is_absolute() or ".." in path.parts or "\x00" in raw:
        return ()
    return tuple(part for part in path.parts if part not in {"", "."})


def _path_covers_root(path: object, root: str) -> bool:
    normalized_path = str(path or "").strip().replace("\\", "/")
    normalized_root = str(root or "").strip().replace("\\", "/")
    if normalized_root == ".":
        return normalized_path in {"", "."} or bool(_relative_parts(path))
    target = _relative_parts(path)
    root_parts = _relative_parts(root)
    return bool(target and root_parts and target[: len(root_parts)] == root_parts)


def _evidence_action_ids(state: RunState, refs: Sequence[str]) -> frozenset[str]:
    revisions = {
        revision.revision_id: revision
        for values in state.artifact_revisions.values()
        for revision in values
    }
    action_ids: set[str] = set()
    for ref in refs:
        if ref in state.actions:
            action_ids.add(ref)
        elif (artifact := state.artifacts.get(ref)) is not None:
            action_ids.add(artifact.action_id)
        elif (revision := revisions.get(ref)) is not None:
            action_ids.add(revision.action_id)
        else:
            raise ValueError(f"audit evidence {ref!r} is not a Harness action fact")
    return frozenset(action_ids)


def _validate_completed_step_evidence(
    state: RunState,
    plan: RollingGoalPlan,
    *,
    step_id: str,
    evidence_refs: Sequence[str],
) -> None:
    """Veto status, provenance, operation, and scope contradictions.

    The RWKV Audit remains the semantic reviewer of the Planner's natural-language
    completion checks.  This kernel proves only facts the Harness can establish.
    """

    step = plan.steps[step_id]
    bindings = goal_step_action_bindings(state)
    expected_binding = (step_id, plan.step_revisions.get(step_id, 1))
    action_ids = _evidence_action_ids(state, evidence_refs)
    if not action_ids:
        raise ValueError("completed plan step requires Harness action evidence")
    actions = [state.actions[action_id] for action_id in sorted(action_ids)]
    wrong_step = [
        action.action_id
        for action in actions
        if bindings.get(action.action_id) != expected_binding
    ]
    if wrong_step:
        raise ValueError(
            "audit evidence actions are not assigned to the current revision of "
            f"step {step_id!r}: {wrong_step}"
        )
    unsuccessful = [
        action.action_id
        for action in actions
        if action.status is not ActionStatus.SUCCEEDED
        or not bool((action.result or {}).get("success"))
    ]
    if unsuccessful:
        raise ValueError(
            f"completed plan step cites unsuccessful actions: {unsuccessful}"
        )
    unauthorized = [
        action.action_id
        for action in actions
        if step.allowed_operations
        and action.action_type not in step.allowed_operations
    ]
    if unauthorized:
        raise ValueError(
            f"completed plan step cites operations outside its allowset: {unauthorized}"
        )

    uncovered_writes: list[str] = []
    for root in step.write_roots:
        covered = False
        for action in actions:
            argument_names = PATH_MUTATION_ARGUMENTS.get(action.action_type, ())
            if action.action_type not in PATH_MUTATION_OPERATIONS:
                continue
            if any(
                _path_covers_root(action.arguments.get(name), root)
                for name in argument_names
            ):
                covered = True
                break
        if not covered:
            uncovered_writes.append(root)
    if uncovered_writes:
        raise ValueError(
            "completed plan step lacks successful mutation evidence for write_roots="
            f"{uncovered_writes!r}"
        )

    uncovered_reads: list[str] = []
    for root in step.read_roots:
        covered = False
        for action in actions:
            if action.action_type == "check_command":
                covered = True
                break
            if action.action_type == "list_directory":
                raw_path = action.arguments.get("path", ".")
                if str(root).replace("\\", "/") == ".":
                    covered = str(raw_path or ".").replace("\\", "/") == "."
                else:
                    covered = _relative_parts(raw_path) == _relative_parts(root)
            elif action.action_type in {
                "bind_evidence",
                "file_digest",
                "read_file",
                "read_json",
                "search_text",
            }:
                covered = _path_covers_root(
                    action.arguments.get("path", action.arguments.get("root", "")),
                    root,
                )
            if covered:
                break
        if not covered:
            uncovered_reads.append(root)
    if uncovered_reads:
        raise ValueError(
            "completed plan step lacks successful observation evidence for read_roots="
            f"{uncovered_reads!r}"
        )


def validate_audit_authority(
    state: RunState,
    plan: RollingGoalPlan,
    audit: GoalAuditDecision,
    *,
    final_candidate: bool,
    active_step_id: str = "",
    allowed_evidence_refs: Sequence[str] | None = None,
) -> None:
    available = available_evidence_refs(state)
    completed_refs = {
        ref for completed in audit.completed_steps for ref in completed.evidence_refs
    }
    all_audit_refs = set(audit.evidence_refs) | completed_refs
    selected_active_step_id = str(active_step_id or "").strip()
    if (
        selected_active_step_id
        and audit.step_id
        and audit.step_id != selected_active_step_id
    ):
        raise ValueError("audit step_id differs from the assigned plan frontier")
    if allowed_evidence_refs is not None:
        allowed = frozenset(str(item) for item in allowed_evidence_refs)
        outside_projection = all_audit_refs - allowed
        if outside_projection:
            raise ValueError(
                "audit references evidence outside its bounded input: "
                f"{sorted(outside_projection)}"
            )
    if audit.step_id and audit.step_id not in plan.steps:
        raise ValueError("audit step_id is outside the committed Strong Planner graph")
    unknown_global = all_audit_refs - available
    if unknown_global:
        raise ValueError(f"audit references unknown evidence: {sorted(unknown_global)}")
    frontier_ids = {item.step_id for item in plan.frontier}
    for completed in audit.completed_steps:
        if completed.step_id not in frontier_ids and (
            completed.step_id not in plan.completed_step_ids
        ):
            raise ValueError("audit may complete only a frontier plan step")
        unknown = set(completed.evidence_refs) - available
        if unknown:
            raise ValueError(
                f"audit step {completed.step_id!r} references unknown evidence: {sorted(unknown)}"
            )
        if not set(completed.evidence_refs) <= set(audit.evidence_refs):
            raise ValueError("completed step evidence is absent from the audit evidence list")
        _validate_completed_step_evidence(
            state,
            plan,
            step_id=completed.step_id,
            evidence_refs=completed.evidence_refs,
        )
    projected_completed = plan.completed_step_ids | {
        item.step_id for item in audit.completed_steps
    }
    active_ids = set(plan.open_step_ids) | set(plan.completed_step_ids)
    if audit.verdict is GoalAuditVerdict.READY_FOR_FINAL:
        if not final_candidate:
            raise ValueError("ready_for_final is legal only at a pre-final boundary")
        if active_ids - projected_completed:
            raise ValueError("ready_for_final requires every active plan step to be complete")
        if state.actions and not audit.evidence_refs:
            raise ValueError("ready_for_final requires evidence refs after tool execution")
        accepted_step_refs = {
            ref for refs in plan.completed_evidence.values() for ref in refs
        }
        if set(audit.evidence_refs) - accepted_step_refs:
            raise ValueError(
                "ready_for_final may cite only evidence already accepted for completed steps"
            )
        final_actions = _evidence_action_ids(state, audit.evidence_refs)
        if any(
            state.actions[action_id].status is not ActionStatus.SUCCEEDED
            for action_id in final_actions
        ):
            raise ValueError("ready_for_final cites an unsuccessful action")
    elif final_candidate:
        if audit.verdict is GoalAuditVerdict.CONTINUE and not audit.gaps:
            raise ValueError("rejected final audit must identify at least one gap")


__all__ = [
    "AuditedStep",
    "GOAL_AUDIT_SCHEMA_VERSION",
    "GOAL_AUDIT_DEFINITION",
    "GOAL_AUDIT_OPERATION",
    "GOAL_PLAN_PATCH_SCHEMA_VERSION",
    "LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION",
    "GOAL_STAGE_REVIEW_SCHEMA_VERSION",
    "GoalAuditDecision",
    "GoalAuditVerdict",
    "GoalPlanPatch",
    "GoalPlanRequest",
    "GoalPlanStep",
    "GoalStageReview",
    "GoalStageReviewRequest",
    "GoalStageReviewVerdict",
    "RollingGoalPlan",
    "available_evidence_refs",
    "goal_step_action_bindings",
    "goal_step_action_assignments",
    "parse_json_object",
    "rolling_goal_plan",
    "validate_audit_authority",
]
