"""Provider-neutral contracts for an optional strong-model supervisor.

The supervisor may plan and review, but it never executes Harness operations and
never rewrites RWKV output.  An API adapter only needs to implement the two
methods in :class:`SupervisorClient` and return the validated value objects here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.model_io import canonical_digest


PLAN_SCHEMA_VERSION = "rwkv-lh.supervisor-plan.v1"
REVIEW_SCHEMA_VERSION = "rwkv-lh.supervisor-review.v1"


def _text(name: str, value: Any, *, max_chars: int) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{name} must be non-empty")
    if len(result) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return result


def _items(
    name: str,
    values: Sequence[Any],
    *,
    required: bool,
    max_items: int,
    max_chars: int,
) -> tuple[str, ...]:
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        raise ValueError(f"{name} must be a sequence of strings")
    result = tuple(
        _text(f"{name}[{index}]", value, max_chars=max_chars)
        for index, value in enumerate(values)
    )
    if required and not result:
        raise ValueError(f"{name} must be non-empty")
    if len(result) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicate items")
    return result


@dataclass(frozen=True)
class SupervisorPlanRequest:
    run_id: str
    request: str
    request_digest: str
    constraints: tuple[str, ...]
    workspace_manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "constraints": list(self.constraints),
            "workspace_manifest": dict(self.workspace_manifest),
        }


@dataclass(frozen=True)
class SupervisorPlan:
    plan_id: str
    objective: str
    constraints: tuple[str, ...]
    steps: tuple[str, ...]
    completion_checks: tuple[str, ...]
    risks: tuple[str, ...] = ()
    schema_version: str = PLAN_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        objective: str,
        constraints: Sequence[str] = (),
        steps: Sequence[str],
        completion_checks: Sequence[str],
        risks: Sequence[str] = (),
    ) -> "SupervisorPlan":
        payload = {
            "schema_version": PLAN_SCHEMA_VERSION,
            "objective": _text("objective", objective, max_chars=4000),
            "constraints": _items(
                "constraints",
                constraints,
                required=False,
                max_items=32,
                max_chars=1000,
            ),
            "steps": _items(
                "steps", steps, required=True, max_items=32, max_chars=2000
            ),
            "completion_checks": _items(
                "completion_checks",
                completion_checks,
                required=True,
                max_items=32,
                max_chars=2000,
            ),
            "risks": _items(
                "risks", risks, required=False, max_items=24, max_chars=1500
            ),
        }
        return cls(
            plan_id=f"PLAN-{canonical_digest(payload)[:20]}",
            objective=payload["objective"],
            constraints=payload["constraints"],
            steps=payload["steps"],
            completion_checks=payload["completion_checks"],
            risks=payload["risks"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "plan_id": self.plan_id,
            "objective": self.objective,
            "constraints": list(self.constraints),
            "steps": list(self.steps),
            "completion_checks": list(self.completion_checks),
            "risks": list(self.risks),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SupervisorPlan":
        if str(value.get("schema_version") or "") != PLAN_SCHEMA_VERSION:
            raise ValueError("unsupported supervisor plan schema")
        plan = cls.create(
            objective=str(value.get("objective") or ""),
            constraints=value.get("constraints") or (),
            steps=value.get("steps") or (),
            completion_checks=value.get("completion_checks") or (),
            risks=value.get("risks") or (),
        )
        if str(value.get("plan_id") or "") != plan.plan_id:
            raise ValueError("supervisor plan id does not match its content")
        return plan


class ReviewDisposition(str, Enum):
    PASS = "pass"
    REVISE = "revise"


@dataclass(frozen=True)
class SupervisorReviewRequest:
    run_id: str
    request: str
    request_digest: str
    plan: SupervisorPlan
    candidate_output: str
    candidate_decision_id: str
    action_count: int
    actions: tuple[Mapping[str, Any], ...]
    artifacts: tuple[Mapping[str, Any], ...]
    workspace_manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "plan": self.plan.to_dict(),
            "candidate_output": self.candidate_output,
            "candidate_decision_id": self.candidate_decision_id,
            "action_count": self.action_count,
            "actions": [dict(item) for item in self.actions],
            "artifacts": [dict(item) for item in self.artifacts],
            "workspace_manifest": dict(self.workspace_manifest),
        }


@dataclass(frozen=True)
class SupervisorReview:
    review_id: str
    disposition: ReviewDisposition
    summary: str
    issues: tuple[str, ...] = ()
    schema_version: str = REVIEW_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        disposition: ReviewDisposition | str,
        *,
        summary: str,
        issues: Sequence[str] = (),
    ) -> "SupervisorReview":
        selected = (
            disposition
            if isinstance(disposition, ReviewDisposition)
            else ReviewDisposition(str(disposition))
        )
        normalized_issues = _items(
            "issues", issues, required=False, max_items=24, max_chars=2000
        )
        if selected == ReviewDisposition.PASS and normalized_issues:
            raise ValueError("passing supervisor review cannot contain issues")
        if selected == ReviewDisposition.REVISE and not normalized_issues:
            raise ValueError("revision supervisor review requires at least one issue")
        payload = {
            "schema_version": REVIEW_SCHEMA_VERSION,
            "disposition": selected.value,
            "summary": _text("summary", summary, max_chars=4000),
            "issues": normalized_issues,
        }
        return cls(
            review_id=f"REVIEW-{canonical_digest(payload)[:20]}",
            disposition=selected,
            summary=payload["summary"],
            issues=normalized_issues,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "disposition": self.disposition.value,
            "summary": self.summary,
            "issues": list(self.issues),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SupervisorReview":
        if str(value.get("schema_version") or "") != REVIEW_SCHEMA_VERSION:
            raise ValueError("unsupported supervisor review schema")
        review = cls.create(
            str(value.get("disposition") or ""),
            summary=str(value.get("summary") or ""),
            issues=value.get("issues") or (),
        )
        if str(value.get("review_id") or "") != review.review_id:
            raise ValueError("supervisor review id does not match its content")
        return review


class SupervisorClient(Protocol):
    """Boundary implemented by a future strong-model API adapter."""

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan: ...

    def review_final(self, request: SupervisorReviewRequest) -> SupervisorReview: ...


@dataclass(frozen=True)
class SupervisorPolicy:
    """Bounded hybrid behavior; there is no unbounded reviewer loop."""

    max_review_repairs: int = 1

    def __post_init__(self) -> None:
        if isinstance(self.max_review_repairs, bool) or not isinstance(
            self.max_review_repairs, int
        ):
            raise ValueError("max_review_repairs must be an integer")
        if not 0 <= self.max_review_repairs <= 3:
            raise ValueError("max_review_repairs must be between 0 and 3")


def supervisor_identity(client: SupervisorClient) -> dict[str, str]:
    return {
        "provider": str(getattr(client, "provider_name", "unconfigured")),
        "model": str(getattr(client, "model_name", "unconfigured")),
    }


__all__ = [
    "PLAN_SCHEMA_VERSION",
    "REVIEW_SCHEMA_VERSION",
    "ReviewDisposition",
    "SupervisorClient",
    "SupervisorPlan",
    "SupervisorPlanRequest",
    "SupervisorPolicy",
    "SupervisorReview",
    "SupervisorReviewRequest",
    "supervisor_identity",
]
