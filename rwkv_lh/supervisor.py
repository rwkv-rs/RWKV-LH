"""Provider-neutral contracts for an optional strong-model supervisor.

The supervisor may plan and review, but it never executes Harness operations and
never rewrites RWKV output.  An API adapter only needs to implement the two
methods in :class:`SupervisorClient` and return the validated value objects here.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.capability_projection import (
    AtomKind,
    CAPABILITY_PROJECTION_VERSION,
    EffectCeiling,
    SUPPORTED_CAPABILITY_PROJECTION_VERSIONS,
)
from rwkv_lh.model_io import canonical_digest


PLAN_SCHEMA_VERSION = "rwkv-lh.supervisor-plan.v1"
REVIEW_SCHEMA_VERSION = "rwkv-lh.supervisor-review.v1"
DIRECTIVE_SCHEMA_VERSION = "rwkv-lh.supervisor-directive.v1"
ATOM_SCHEMA_VERSION = "rwkv-lh.supervisor-atom.v4"
CAPABILITY_ATOM_SCHEMA_VERSION = "rwkv-lh.supervisor-atom.v5"
STAGE_SCHEMA_VERSION = "rwkv-lh.supervisor-stage.v4"


_ATOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")
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


def _identifier(name: str, value: Any) -> str:
    result = str(value or "").strip()
    if not _ATOM_ID_PATTERN.fullmatch(result):
        raise ValueError(
            f"{name} must match {_ATOM_ID_PATTERN.pattern}"
        )
    return result


def _path_roots(name: str, values: Sequence[Any]) -> tuple[str, ...]:
    roots = _items(
        name,
        values,
        required=False,
        max_items=16,
        max_chars=512,
    )
    normalized: list[str] = []
    for index, value in enumerate(roots):
        raw = value.replace("\\", "/").rstrip("/") or "."
        path = PurePosixPath(raw)
        if path.is_absolute() or ".." in path.parts or "\x00" in raw:
            raise ValueError(f"{name}[{index}] must be a workspace-relative root")
        canonical = path.as_posix()
        if canonical.startswith("./"):
            canonical = canonical[2:]
        normalized.append(canonical or ".")
    if len(set(normalized)) != len(normalized):
        raise ValueError(f"{name} contains duplicate roots")
    return tuple(normalized)


def _roots_overlap(left: str, right: str) -> bool:
    if left == "." or right == ".":
        return True
    left_parts = PurePosixPath(left).parts
    right_parts = PurePosixPath(right).parts
    shared = min(len(left_parts), len(right_parts))
    return left_parts[:shared] == right_parts[:shared]


def _completed_atom_contract(value: Mapping[str, Any]) -> Mapping[str, Any]:
    """Read the exact persisted execution contract, with legacy recovery only."""

    raw_contract = value.get("execution_contract")
    if raw_contract is None:
        return value
    if not isinstance(raw_contract, Mapping):
        raise ValueError("completed atom execution_contract must be an object")
    raw_atom = raw_contract.get("atom")
    if not isinstance(raw_atom, Mapping):
        raise ValueError("completed atom execution_contract lacks its Planner atom")
    if str(raw_atom.get("atom_id") or "") != str(value.get("atom_id") or ""):
        raise ValueError("completed atom execution contract changed atom identity")
    if str(raw_atom.get("role") or "") != str(value.get("role") or ""):
        raise ValueError("completed atom execution contract changed atom role")
    if tuple(str(item) for item in raw_atom.get("write_roots") or ()) != tuple(
        str(item) for item in value.get("write_roots") or ()
    ):
        raise ValueError("completed atom execution contract changed write roots")
    if str(raw_contract.get("contract_digest") or "") != str(
        value.get("contract_digest") or ""
    ):
        raise ValueError("completed atom execution contract changed contract digest")
    return raw_atom


def _unrecovered_failed_work_ids(
    completed_atoms: Sequence[Mapping[str, Any]],
) -> list[str]:
    unresolved: list[str] = []
    for failed_index, failed in enumerate(completed_atoms):
        if (
            str(failed.get("role") or "") != "work"
            or str(failed.get("status") or "") == "completed"
        ):
            continue
        failed_contract = _completed_atom_contract(failed)
        failed_roots = tuple(
            str(item) for item in failed_contract.get("write_roots") or ()
        )
        recovered = any(
            str(later.get("role") or "") == "work"
            and str(later.get("status") or "") == "completed"
            and (
                not failed_roots
                or any(
                    _roots_overlap(left, right)
                    for left in failed_roots
                    for right in _completed_atom_contract(later).get(
                        "write_roots"
                    ) or ()
                )
            )
            for later in completed_atoms[failed_index + 1 :]
        )
        if not recovered:
            unresolved.append(str(failed.get("atom_id") or ""))
    return unresolved


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


class AtomRole(str, Enum):
    WORK = "work"
    FINALIZER = "finalizer"


@dataclass(frozen=True)
class SupervisorAtom:
    """One independently executable RWKV assignment in a ready stage batch."""

    atom_id: str
    role: AtomRole
    objective: str
    request_clauses: tuple[str, ...]
    depends_on: tuple[str, ...]
    read_roots: tuple[str, ...]
    write_roots: tuple[str, ...]
    exclusive: bool
    allowed_operations: tuple[str, ...]
    action_budget: int
    completion_checks: tuple[str, ...]
    constraints: tuple[str, ...] = ()
    atom_kind: str = ""
    effect_ceiling: str = ""
    evidence_kinds: tuple[str, ...] = ()
    freshness: str = ""
    source_preferences: tuple[str, ...] = ()
    operation_allowset_source: str = ""
    minimum_actions: int = 0
    schema_version: str = ATOM_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        immutable_request: str,
        atom_id: str,
        role: AtomRole | str,
        objective: str,
        request_clauses: Sequence[str],
        depends_on: Sequence[str] = (),
        read_roots: Sequence[str] = (),
        write_roots: Sequence[str] = (),
        exclusive: bool = False,
        allowed_operations: Sequence[str],
        action_budget: int,
        completion_checks: Sequence[str],
        constraints: Sequence[str] = (),
        atom_kind: AtomKind | str = "",
        effect_ceiling: EffectCeiling | str = "",
        evidence_kinds: Sequence[str] = (),
        freshness: str = "",
        source_preferences: Sequence[str] = (),
        operation_allowset_source: str = "",
        minimum_actions: int = 0,
    ) -> "SupervisorAtom":
        request = str(immutable_request or "")
        if not request:
            raise ValueError("immutable_request must be non-empty")
        selected_role = role if isinstance(role, AtomRole) else AtomRole(str(role))
        clauses = _items(
            "request_clauses",
            request_clauses,
            required=True,
            max_items=8,
            max_chars=2000,
        )
        missing = [clause for clause in clauses if clause not in request]
        if missing:
            raise ValueError(
                "request_clauses must be verbatim substrings of the immutable request"
            )
        dependencies = tuple(
            _identifier(f"depends_on[{index}]", value)
            for index, value in enumerate(depends_on)
        )
        if len(set(dependencies)) != len(dependencies):
            raise ValueError("depends_on contains duplicate atom ids")
        reads = _path_roots("read_roots", read_roots)
        writes = _path_roots("write_roots", write_roots)
        if not isinstance(exclusive, bool):
            raise ValueError("exclusive must be a boolean")
        identifier = _identifier("atom_id", atom_id)
        if identifier in dependencies:
            raise ValueError("an atom cannot depend on itself")
        if selected_role == AtomRole.FINALIZER and writes:
            raise ValueError("a finalizer atom must be read-only")
        if selected_role == AtomRole.FINALIZER and exclusive:
            raise ValueError("a read-only finalizer atom cannot be exclusive")
        if "." in writes and not exclusive:
            raise ValueError("workspace-wide write scope requires an exclusive atom")
        operations = tuple(
            _identifier(f"allowed_operations[{index}]", value)
            for index, value in enumerate(allowed_operations)
        )
        if not operations:
            raise ValueError("allowed_operations must be non-empty")
        projection_source = str(operation_allowset_source or "").strip()
        operation_limit = 32 if projection_source else 4
        if len(operations) > operation_limit:
            raise ValueError(
                f"allowed_operations must contain at most {operation_limit} operations"
            )
        if len(set(operations)) != len(operations):
            raise ValueError("allowed_operations contains duplicate items")
        action_budget_limit = 12 if projection_source else 4
        if (
            isinstance(action_budget, bool)
            or not isinstance(action_budget, int)
            or not 1 <= action_budget <= action_budget_limit
        ):
            raise ValueError(
                f"action_budget must be between 1 and {action_budget_limit}"
            )
        selected_kind = ""
        selected_ceiling = ""
        selected_evidence_kinds: tuple[str, ...] = ()
        selected_freshness = ""
        selected_preferences: tuple[str, ...] = ()
        selected_minimum_actions = 0
        selected_schema = ATOM_SCHEMA_VERSION
        if projection_source:
            if projection_source not in SUPPORTED_CAPABILITY_PROJECTION_VERSIONS:
                raise ValueError("unsupported operation allowset source")
            selected_kind = (
                atom_kind.value
                if isinstance(atom_kind, AtomKind)
                else AtomKind(str(atom_kind)).value
            )
            selected_ceiling = (
                effect_ceiling.value
                if isinstance(effect_ceiling, EffectCeiling)
                else EffectCeiling(str(effect_ceiling)).value
            )
            selected_evidence_kinds = _items(
                "evidence_kinds",
                evidence_kinds,
                required=True,
                max_items=8,
                max_chars=160,
            )
            selected_freshness = _text(
                "freshness", freshness, max_chars=160
            )
            if selected_freshness not in {
                "not_applicable",
                "historical",
                "current_at_run_time",
                "current_workspace",
            }:
                raise ValueError("unsupported atom evidence freshness")
            selected_preferences = _items(
                "source_preferences",
                source_preferences,
                required=True,
                max_items=8,
                max_chars=160,
            )
            minimum_floor = 0 if selected_role == AtomRole.FINALIZER else 1
            if (
                isinstance(minimum_actions, bool)
                or not isinstance(minimum_actions, int)
                or not minimum_floor <= minimum_actions <= action_budget
            ):
                raise ValueError(
                    "minimum_actions is outside the role/action budget"
                )
            selected_minimum_actions = minimum_actions
            selected_schema = CAPABILITY_ATOM_SCHEMA_VERSION
        elif any(
            (
                str(atom_kind or ""),
                str(effect_ceiling or ""),
                tuple(evidence_kinds),
                str(freshness or ""),
                tuple(source_preferences),
                int(minimum_actions or 0),
            )
        ):
            raise ValueError(
                "capability atom metadata requires operation_allowset_source"
            )
        return cls(
            atom_id=identifier,
            role=selected_role,
            objective=_text("objective", objective, max_chars=2400),
            request_clauses=clauses,
            depends_on=dependencies,
            read_roots=reads,
            write_roots=writes,
            exclusive=exclusive,
            allowed_operations=operations,
            action_budget=action_budget,
            completion_checks=_items(
                "completion_checks",
                completion_checks,
                required=True,
                max_items=8,
                max_chars=1200,
            ),
            constraints=_items(
                "constraints",
                constraints,
                required=False,
                max_items=8,
                max_chars=1000,
            ),
            atom_kind=selected_kind,
            effect_ceiling=selected_ceiling,
            evidence_kinds=selected_evidence_kinds,
            freshness=selected_freshness,
            source_preferences=selected_preferences,
            operation_allowset_source=projection_source,
            minimum_actions=selected_minimum_actions,
            schema_version=selected_schema,
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "atom_id": self.atom_id,
            "role": self.role.value,
            "objective": self.objective,
            "request_clauses": list(self.request_clauses),
            "depends_on": list(self.depends_on),
            "read_roots": list(self.read_roots),
            "write_roots": list(self.write_roots),
            "exclusive": self.exclusive,
            "allowed_operations": list(self.allowed_operations),
            "action_budget": self.action_budget,
            "completion_checks": list(self.completion_checks),
            "constraints": list(self.constraints),
        }
        if self.operation_allowset_source:
            value.update(
                {
                    "atom_kind": self.atom_kind,
                    "effect_ceiling": self.effect_ceiling,
                    "evidence_kinds": list(self.evidence_kinds),
                    "freshness": self.freshness,
                    "source_preferences": list(self.source_preferences),
                    "operation_allowset_source": self.operation_allowset_source,
                    "minimum_actions": self.minimum_actions,
                }
            )
        return value

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        immutable_request: str,
    ) -> "SupervisorAtom":
        schema_version = str(
            value.get("schema_version")
            or (
                CAPABILITY_ATOM_SCHEMA_VERSION
                if value.get("operation_allowset_source")
                else ATOM_SCHEMA_VERSION
            )
        )
        if schema_version not in {
            ATOM_SCHEMA_VERSION,
            CAPABILITY_ATOM_SCHEMA_VERSION,
        }:
            raise ValueError("unsupported supervisor atom schema")
        atom = cls.create(
            immutable_request=immutable_request,
            atom_id=str(value.get("atom_id") or ""),
            role=str(value.get("role") or ""),
            objective=str(value.get("objective") or ""),
            request_clauses=value.get("request_clauses") or (),
            depends_on=value.get("depends_on") or (),
            read_roots=value.get("read_roots") or (),
            write_roots=value.get("write_roots") or (),
            exclusive=value.get("exclusive", False),
            allowed_operations=value.get("allowed_operations") or (),
            action_budget=value.get("action_budget", 0),
            completion_checks=value.get("completion_checks") or (),
            constraints=value.get("constraints") or (),
            atom_kind=str(value.get("atom_kind") or ""),
            effect_ceiling=str(value.get("effect_ceiling") or ""),
            evidence_kinds=value.get("evidence_kinds") or (),
            freshness=str(value.get("freshness") or ""),
            source_preferences=value.get("source_preferences") or (),
            operation_allowset_source=str(
                value.get("operation_allowset_source") or ""
            ),
            minimum_actions=int(value.get("minimum_actions", 0) or 0),
        )
        if atom.schema_version != schema_version:
            raise ValueError("supervisor atom schema does not match its authority")
        return atom


class StageDisposition(str, Enum):
    DISPATCH = "dispatch"
    ACCEPT_FINAL = "accept_final"


@dataclass(frozen=True)
class SupervisorStageRequest:
    """Public state boundary for one low-frequency parallel planning stage."""

    run_id: str
    request: str
    request_digest: str
    constraints: tuple[str, ...]
    stage_index: int
    max_parallel_atoms: int
    previous_stage_id: str
    completed_atoms: tuple[Mapping[str, Any], ...]
    available_operations: tuple[Mapping[str, Any], ...]
    workspace_manifest: Mapping[str, Any]
    causal_evidence: tuple[Mapping[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        eligible_dependency_atom_ids = [
            str(item.get("atom_id") or "")
            for item in self.completed_atoms
            if str(item.get("status") or "") == "completed"
            and str(item.get("atom_id") or "")
        ]
        failed_atom_ids = [
            str(item.get("atom_id") or "")
            for item in self.completed_atoms
            if str(item.get("status") or "") != "completed"
            and str(item.get("atom_id") or "")
        ]
        return {
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "constraints": list(self.constraints),
            "stage_index": self.stage_index,
            "max_parallel_atoms": self.max_parallel_atoms,
            "previous_stage_id": self.previous_stage_id,
            "completed_atoms": [dict(item) for item in self.completed_atoms],
            "eligible_dependency_atom_ids": eligible_dependency_atom_ids,
            "failed_atom_ids": failed_atom_ids,
            "available_operations": [
                dict(item) for item in self.available_operations
            ],
            "workspace_manifest": dict(self.workspace_manifest),
            "causal_evidence": [dict(item) for item in self.causal_evidence],
        }


@dataclass(frozen=True)
class SupervisorStage:
    """A validated batch of ready atoms or acceptance of one RWKV finalizer."""

    stage_id: str
    stage_index: int
    request_digest: str
    disposition: StageDisposition
    review_summary: str
    issues: tuple[str, ...]
    atoms: tuple[SupervisorAtom, ...]
    accepted_candidate_atom_id: str
    schema_version: str = STAGE_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        request: SupervisorStageRequest,
        *,
        disposition: StageDisposition | str,
        review_summary: str,
        issues: Sequence[str] = (),
        atoms: Sequence[SupervisorAtom | Mapping[str, Any]] = (),
        accepted_candidate_atom_id: str = "",
    ) -> "SupervisorStage":
        if (
            isinstance(request.stage_index, bool)
            or not isinstance(request.stage_index, int)
            or request.stage_index < 1
        ):
            raise ValueError("stage_index must be a positive integer")
        if (
            isinstance(request.max_parallel_atoms, bool)
            or not isinstance(request.max_parallel_atoms, int)
            or not 1 <= request.max_parallel_atoms <= 8
        ):
            raise ValueError("max_parallel_atoms must be between 1 and 8")
        selected = (
            disposition
            if isinstance(disposition, StageDisposition)
            else StageDisposition(str(disposition))
        )
        normalized_issues = _items(
            "issues",
            issues,
            required=False,
            max_items=16,
            max_chars=1600,
        )
        completed_by_id = {
            str(item.get("atom_id") or ""): item
            for item in request.completed_atoms
            if str(item.get("atom_id") or "")
        }
        # Every current-format result may expose a few top-level index fields,
        # but they are never an alternate authority.  Validate all of them
        # against the exact nested execution contract before planning/review.
        for item in request.completed_atoms:
            _completed_atom_contract(item)
        satisfied_atom_ids = {
            atom_id
            for atom_id, item in completed_by_id.items()
            if str(item.get("status") or "") == "completed"
        }
        parsed_atoms = tuple(
            atom
            if isinstance(atom, SupervisorAtom)
            else SupervisorAtom.from_dict(
                atom,
                immutable_request=request.request,
            )
            for atom in atoms
        )
        accepted_id = str(accepted_candidate_atom_id or "").strip()
        operation_catalog = {
            str(item.get("name") or ""): item
            for item in request.available_operations
            if str(item.get("name") or "")
        }
        if not operation_catalog:
            raise ValueError("stage request has no available operation catalog")
        for atom in parsed_atoms:
            unknown_operations = set(atom.allowed_operations) - set(
                operation_catalog
            )
            if unknown_operations:
                raise ValueError(
                    f"atom {atom.atom_id} selected unavailable operations: "
                    f"{sorted(unknown_operations)}"
                )
            incompatible: list[str] = []
            selected_modes: list[str] = []
            for name in atom.allowed_operations:
                mode = str(operation_catalog[name].get("scope_mode") or "")
                selected_modes.append(mode)
                if atom.role == AtomRole.FINALIZER and mode != "read_only":
                    incompatible.append(name)
                elif mode == "path_mutation" and not atom.write_roots:
                    incompatible.append(name)
                elif mode == "exclusive_side_effect" and not atom.exclusive:
                    incompatible.append(name)
            if incompatible:
                raise ValueError(
                    f"atom {atom.atom_id} selected scope-incompatible operations: "
                    f"{sorted(incompatible)}"
                )
            if any(mode == "path_mutation" for mode in selected_modes):
                minimum_budget = 2 if len(atom.allowed_operations) > 1 else 1
                if not minimum_budget <= atom.action_budget <= 4:
                    raise ValueError(
                        f"mutating atom {atom.atom_id} has an invalid transaction budget"
                    )
                if not 1 <= len(atom.write_roots) <= 2:
                    raise ValueError(
                        f"mutating atom {atom.atom_id} must declare one or two write_roots"
                    )
            if any(mode == "exclusive_side_effect" for mode in selected_modes):
                if atom.action_budget != 1 or len(atom.allowed_operations) != 1:
                    raise ValueError(
                        f"exclusive atom {atom.atom_id} must be a one-action transaction"
                    )
            visible_paths = {
                str(item.get("path") or "")
                for item in request.workspace_manifest.get("entries") or ()
                if isinstance(item, Mapping) and str(item.get("path") or "")
            }
            visible_paths.update(
                str(artifact.get("path") or "")
                for outcome in request.completed_atoms
                for artifact in outcome.get("artifacts") or ()
                if isinstance(artifact, Mapping)
                and str(artifact.get("path") or "")
            )
            # Path authority comes from the structured scope fields consumed by
            # ScopedAtomHarness, not from heuristic token matching in prose.
            # Tokens such as ``before/after``, ``TaskQueue.pop`` and JSON shape
            # descriptions are not filesystem authority and must not make an
            # otherwise valid graph fail after it has been committed.
            def authorized_scope(root: str) -> bool:
                if root == "." or root in request.request or root in visible_paths:
                    return True
                parts = root.replace("\\", "/").strip("/").split("/")
                parents = ["/".join(parts[:index]) for index in range(1, len(parts))]
                return any(
                    parent in visible_paths
                    or re.search(
                        rf"(?<![A-Za-z0-9_.-]){re.escape(parent)}(?:/|(?=$|[^A-Za-z0-9_.-]))",
                        request.request,
                    )
                    for parent in parents
                )

            invented_paths = {
                root
                for root in (*atom.read_roots, *atom.write_roots)
                if not authorized_scope(root)
            }
            if invented_paths:
                raise ValueError(
                    f"atom {atom.atom_id} introduced scope roots absent from the "
                    "immutable request and public workspace: "
                    f"{sorted(invented_paths)}"
                )

        if selected == StageDisposition.DISPATCH:
            if not parsed_atoms:
                raise ValueError("a dispatch stage requires at least one atom")
            if len(parsed_atoms) > request.max_parallel_atoms:
                raise ValueError(
                    "a dispatch stage exceeds the configured parallel atom limit"
                )
            if accepted_id:
                raise ValueError("a dispatch stage cannot accept a final candidate")
            atom_ids = [atom.atom_id for atom in parsed_atoms]
            if len(set(atom_ids)) != len(atom_ids):
                raise ValueError("a dispatch stage contains duplicate atom ids")
            overlap = set(atom_ids) & set(completed_by_id)
            if overlap:
                raise ValueError(
                    f"atom ids must be globally unique; already completed: {sorted(overlap)}"
                )
            for atom in parsed_atoms:
                missing = set(atom.depends_on) - satisfied_atom_ids
                if missing:
                    raise ValueError(
                        "every dispatched atom dependency must already be completed: "
                        f"{atom.atom_id} missing {sorted(missing)}"
                    )
            exclusive_atoms = [atom.atom_id for atom in parsed_atoms if atom.exclusive]
            if exclusive_atoms and len(parsed_atoms) != 1:
                raise ValueError(
                    "an exclusive atom must be the only atom in its stage"
                )
            finalizers = [
                atom.atom_id for atom in parsed_atoms if atom.role == AtomRole.FINALIZER
            ]
            if finalizers and len(parsed_atoms) != 1:
                raise ValueError("a finalizer must be the only atom in its stage")
            if finalizers:
                finalizer = parsed_atoms[0]
                completed_work_ids = [
                    str(item.get("atom_id") or "")
                    for item in request.completed_atoms
                    if str(item.get("status") or "") == "completed"
                    and str(item.get("role") or "") == AtomRole.WORK.value
                ]
                missing_work_dependencies = set(completed_work_ids) - set(
                    finalizer.depends_on
                )
                if missing_work_dependencies:
                    raise ValueError(
                        "a finalizer must depend on every completed work atom: "
                        f"missing {sorted(missing_work_dependencies)}"
                    )
                completed_roles = [
                    str(item.get("role") or "")
                    for item in request.completed_atoms
                    if str(item.get("status") or "") == "completed"
                ]
                if AtomRole.FINALIZER.value in completed_roles:
                    latest_finalizer = max(
                        index
                        for index, item in enumerate(request.completed_atoms)
                        if str(item.get("status") or "") == "completed"
                        and str(item.get("role") or "")
                        == AtomRole.FINALIZER.value
                    )
                    new_work_exists = any(
                        str(item.get("status") or "") == "completed"
                        and str(item.get("role") or "") == AtomRole.WORK.value
                        for item in request.completed_atoms[latest_finalizer + 1 :]
                    )
                    if not new_work_exists:
                        raise ValueError(
                            "a new finalizer requires new completed work after the prior "
                            "finalizer"
                        )
                unresolved_failures = _unrecovered_failed_work_ids(
                    request.completed_atoms
                )
                if unresolved_failures:
                    raise ValueError(
                        "a finalizer cannot run while failed work remains unrecovered: "
                        f"{sorted(unresolved_failures)}"
                    )
            for index, atom in enumerate(parsed_atoms):
                for other in parsed_atoms[index + 1 :]:
                    conflicts = [
                        (left, right)
                        for left in atom.write_roots
                        for right in other.write_roots
                        if _roots_overlap(left, right)
                    ]
                    if conflicts:
                        raise ValueError(
                            "parallel atoms have overlapping write roots: "
                            f"{atom.atom_id} and {other.atom_id}: {conflicts}"
                        )
        else:
            if parsed_atoms:
                raise ValueError("an accept_final stage cannot dispatch atoms")
            if normalized_issues:
                raise ValueError("an accept_final stage cannot contain issues")
            accepted_id = _identifier(
                "accepted_candidate_atom_id",
                accepted_id,
            )
            outcome = completed_by_id.get(accepted_id)
            if outcome is None:
                raise ValueError("accepted finalizer outcome is not completed")
            if str(outcome.get("role") or "") != AtomRole.FINALIZER.value:
                raise ValueError("only a finalizer atom can provide the top-level Final")
            if str(outcome.get("status") or "") != "completed":
                raise ValueError("accepted finalizer atom is not completed")
            if not str(outcome.get("candidate_output") or "").strip():
                raise ValueError("accepted finalizer has no RWKV candidate output")
            completed_finalizer_ids = [
                str(item.get("atom_id") or "")
                for item in request.completed_atoms
                if str(item.get("role") or "") == AtomRole.FINALIZER.value
                and str(item.get("status") or "") == "completed"
                and str(item.get("candidate_output") or "").strip()
            ]
            if not completed_finalizer_ids or completed_finalizer_ids[-1] != accepted_id:
                raise ValueError("only the latest completed finalizer can be accepted")
            accepted_index = next(
                index
                for index, item in enumerate(request.completed_atoms)
                if str(item.get("atom_id") or "") == accepted_id
            )
            if any(
                str(item.get("role") or "") == AtomRole.WORK.value
                for item in request.completed_atoms[accepted_index + 1 :]
            ):
                raise ValueError("a finalizer cannot be accepted after newer work")
            completed_work_ids = {
                str(item.get("atom_id") or "")
                for item in request.completed_atoms
                if str(item.get("role") or "") == AtomRole.WORK.value
                and str(item.get("status") or "") == "completed"
            }
            accepted_contract = _completed_atom_contract(outcome)
            missing_work_dependencies = completed_work_ids - {
                str(item) for item in accepted_contract.get("depends_on") or ()
            }
            if missing_work_dependencies:
                raise ValueError(
                    "an accepted finalizer must depend on every completed work atom: "
                    f"missing {sorted(missing_work_dependencies)}"
                )
            unresolved_failures = _unrecovered_failed_work_ids(
                request.completed_atoms
            )
            if unresolved_failures:
                raise ValueError(
                    "a finalizer cannot be accepted while failed work remains "
                    f"unrecovered: {sorted(unresolved_failures)}"
                )

        payload = {
            "schema_version": STAGE_SCHEMA_VERSION,
            "stage_index": request.stage_index,
            "request_digest": request.request_digest,
            "disposition": selected.value,
            "review_summary": _text(
                "review_summary",
                review_summary,
                max_chars=3000,
            ),
            "issues": normalized_issues,
            "atoms": [atom.to_dict() for atom in parsed_atoms],
            "accepted_candidate_atom_id": accepted_id,
        }
        return cls(
            stage_id=f"STAGE-{canonical_digest(payload)[:20]}",
            stage_index=request.stage_index,
            request_digest=request.request_digest,
            disposition=selected,
            review_summary=payload["review_summary"],
            issues=normalized_issues,
            atoms=parsed_atoms,
            accepted_candidate_atom_id=accepted_id,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage_id": self.stage_id,
            "stage_index": self.stage_index,
            "request_digest": self.request_digest,
            "disposition": self.disposition.value,
            "review_summary": self.review_summary,
            "issues": list(self.issues),
            "atoms": [atom.to_dict() for atom in self.atoms],
            "accepted_candidate_atom_id": self.accepted_candidate_atom_id,
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        request: SupervisorStageRequest,
    ) -> "SupervisorStage":
        if str(value.get("schema_version") or "") != STAGE_SCHEMA_VERSION:
            raise ValueError("unsupported supervisor stage schema")
        if int(value.get("stage_index", 0) or 0) != request.stage_index:
            raise ValueError("supervisor stage index does not match request")
        if str(value.get("request_digest") or "") != request.request_digest:
            raise ValueError("supervisor stage request digest does not match request")
        stage = cls.create(
            request,
            disposition=str(value.get("disposition") or ""),
            review_summary=str(value.get("review_summary") or ""),
            issues=value.get("issues") or (),
            atoms=value.get("atoms") or (),
            accepted_candidate_atom_id=str(
                value.get("accepted_candidate_atom_id") or ""
            ),
        )
        if str(value.get("stage_id") or "") != stage.stage_id:
            raise ValueError("supervisor stage id does not match its content")
        return stage

    @classmethod
    def restore(
        cls,
        value: Mapping[str, Any],
        *,
        immutable_request: str,
    ) -> "SupervisorStage":
        """Restore one already-committed stage without re-evaluating later outcomes."""

        if str(value.get("schema_version") or "") != STAGE_SCHEMA_VERSION:
            raise ValueError("unsupported supervisor stage schema")
        atoms = tuple(
            SupervisorAtom.from_dict(item, immutable_request=immutable_request)
            for item in value.get("atoms") or ()
            if isinstance(item, Mapping)
        )
        selected = StageDisposition(str(value.get("disposition") or ""))
        stage_index = int(value.get("stage_index", 0) or 0)
        request_digest = str(value.get("request_digest") or "")
        review_summary = _text(
            "review_summary",
            str(value.get("review_summary") or ""),
            max_chars=3000,
        )
        issues = _items(
            "issues",
            value.get("issues") or (),
            required=False,
            max_items=16,
            max_chars=1600,
        )
        accepted_id = str(value.get("accepted_candidate_atom_id") or "")
        payload = {
            "schema_version": STAGE_SCHEMA_VERSION,
            "stage_index": stage_index,
            "request_digest": request_digest,
            "disposition": selected.value,
            "review_summary": review_summary,
            "issues": issues,
            "atoms": [atom.to_dict() for atom in atoms],
            "accepted_candidate_atom_id": accepted_id,
        }
        stage_id = f"STAGE-{canonical_digest(payload)[:20]}"
        if str(value.get("stage_id") or "") != stage_id:
            raise ValueError("committed supervisor stage id does not match its content")
        return cls(
            stage_id=stage_id,
            stage_index=stage_index,
            request_digest=request_digest,
            disposition=selected,
            review_summary=review_summary,
            issues=issues,
            atoms=atoms,
            accepted_candidate_atom_id=accepted_id,
        )


class DirectiveDisposition(str, Enum):
    CONTINUE = "continue"
    ACCEPT_FINAL = "accept_final"


class DirectiveReviewStatus(str, Enum):
    INITIAL = "initial"
    SATISFIED = "satisfied"
    NEEDS_CORRECTION = "needs_correction"


@dataclass(frozen=True)
class SupervisorDirectiveRequest:
    """One public state boundary for the online planner/reviewer."""

    run_id: str
    request: str
    request_digest: str
    constraints: tuple[str, ...]
    directive_index: int
    outcome_ref: str
    previous_directive: Mapping[str, Any] | None
    worker_outcome: Mapping[str, Any] | None
    action_count: int
    actions: tuple[Mapping[str, Any], ...]
    artifacts: tuple[Mapping[str, Any], ...]
    workspace_manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "constraints": list(self.constraints),
            "directive_index": self.directive_index,
            "outcome_ref": self.outcome_ref,
            "previous_directive": (
                dict(self.previous_directive)
                if isinstance(self.previous_directive, Mapping)
                else None
            ),
            "worker_outcome": (
                dict(self.worker_outcome)
                if isinstance(self.worker_outcome, Mapping)
                else None
            ),
            "action_count": self.action_count,
            "actions": [dict(item) for item in self.actions],
            "artifacts": [dict(item) for item in self.artifacts],
            "workspace_manifest": dict(self.workspace_manifest),
        }


@dataclass(frozen=True)
class SupervisorDirective:
    """Review one worker outcome and assign at most one next microtask."""

    directive_id: str
    directive_index: int
    outcome_ref: str
    disposition: DirectiveDisposition
    review_status: DirectiveReviewStatus
    review_summary: str
    issues: tuple[str, ...]
    microtask_objective: str
    completion_checks: tuple[str, ...]
    constraints: tuple[str, ...]
    schema_version: str = DIRECTIVE_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        directive_index: int,
        outcome_ref: str,
        disposition: DirectiveDisposition | str,
        review_status: DirectiveReviewStatus | str,
        review_summary: str,
        issues: Sequence[str] = (),
        microtask_objective: str = "",
        completion_checks: Sequence[str] = (),
        constraints: Sequence[str] = (),
    ) -> "SupervisorDirective":
        if (
            isinstance(directive_index, bool)
            or not isinstance(directive_index, int)
            or directive_index < 1
        ):
            raise ValueError("directive_index must be a positive integer")
        normalized_ref = _text("outcome_ref", outcome_ref, max_chars=256)
        selected_disposition = (
            disposition
            if isinstance(disposition, DirectiveDisposition)
            else DirectiveDisposition(str(disposition))
        )
        selected_review = (
            review_status
            if isinstance(review_status, DirectiveReviewStatus)
            else DirectiveReviewStatus(str(review_status))
        )
        normalized_issues = _items(
            "issues", issues, required=False, max_items=12, max_chars=1200
        )
        if selected_review == DirectiveReviewStatus.NEEDS_CORRECTION:
            if not normalized_issues:
                raise ValueError("needs_correction requires at least one issue")
        elif normalized_issues:
            raise ValueError("initial/satisfied directive review cannot contain issues")
        if normalized_ref == "initial" and selected_review != DirectiveReviewStatus.INITIAL:
            raise ValueError("initial outcome requires initial review status")
        if normalized_ref != "initial" and selected_review == DirectiveReviewStatus.INITIAL:
            raise ValueError("initial review status is only valid for the initial outcome")

        if selected_disposition == DirectiveDisposition.CONTINUE:
            objective = _text(
                "microtask_objective", microtask_objective, max_chars=2400
            )
            checks = _items(
                "completion_checks",
                completion_checks,
                required=True,
                max_items=8,
                max_chars=1000,
            )
            normalized_constraints = _items(
                "constraints",
                constraints,
                required=False,
                max_items=8,
                max_chars=1000,
            )
        else:
            if selected_review != DirectiveReviewStatus.SATISFIED:
                raise ValueError("accept_final requires a satisfied review")
            if microtask_objective or completion_checks or constraints:
                raise ValueError("accept_final cannot assign another microtask")
            objective = ""
            checks = ()
            normalized_constraints = ()

        payload = {
            "schema_version": DIRECTIVE_SCHEMA_VERSION,
            "directive_index": directive_index,
            "outcome_ref": normalized_ref,
            "disposition": selected_disposition.value,
            "review_status": selected_review.value,
            "review_summary": _text(
                "review_summary", review_summary, max_chars=2400
            ),
            "issues": normalized_issues,
            "microtask_objective": objective,
            "completion_checks": checks,
            "constraints": normalized_constraints,
        }
        return cls(
            directive_id=f"DIRECTIVE-{canonical_digest(payload)[:20]}",
            directive_index=directive_index,
            outcome_ref=normalized_ref,
            disposition=selected_disposition,
            review_status=selected_review,
            review_summary=payload["review_summary"],
            issues=normalized_issues,
            microtask_objective=objective,
            completion_checks=checks,
            constraints=normalized_constraints,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "directive_id": self.directive_id,
            "directive_index": self.directive_index,
            "outcome_ref": self.outcome_ref,
            "disposition": self.disposition.value,
            "review_status": self.review_status.value,
            "review_summary": self.review_summary,
            "issues": list(self.issues),
            "microtask_objective": self.microtask_objective,
            "completion_checks": list(self.completion_checks),
            "constraints": list(self.constraints),
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "SupervisorDirective":
        if str(value.get("schema_version") or "") != DIRECTIVE_SCHEMA_VERSION:
            raise ValueError("unsupported supervisor directive schema")
        directive = cls.create(
            directive_index=value.get("directive_index"),
            outcome_ref=str(value.get("outcome_ref") or ""),
            disposition=str(value.get("disposition") or ""),
            review_status=str(value.get("review_status") or ""),
            review_summary=str(value.get("review_summary") or ""),
            issues=value.get("issues") or (),
            microtask_objective=str(value.get("microtask_objective") or ""),
            completion_checks=value.get("completion_checks") or (),
            constraints=value.get("constraints") or (),
        )
        if str(value.get("directive_id") or "") != directive.directive_id:
            raise ValueError("supervisor directive id does not match its content")
        return directive


class SupervisorClient(Protocol):
    """Boundary implemented by a future strong-model API adapter."""

    def create_plan(self, request: SupervisorPlanRequest) -> SupervisorPlan: ...

    def review_final(self, request: SupervisorReviewRequest) -> SupervisorReview: ...

    def next_directive(
        self, request: SupervisorDirectiveRequest
    ) -> SupervisorDirective: ...

    def next_stage(self, request: SupervisorStageRequest) -> SupervisorStage: ...


@dataclass(frozen=True)
class SupervisorPolicy:
    """Bounded static or online hybrid behavior."""

    max_review_repairs: int = 1
    mode: str = "static"
    max_online_directives: int = 64
    online_actions_per_directive: int = 6
    online_protocol_rejections_per_directive: int = 2
    max_parallel_stages: int = 16
    max_parallel_atoms: int = 4
    atom_max_transitions: int = 40
    max_graph_patches: int = 12
    max_reviewer_rounds: int = 12
    max_graph_atoms: int = 64
    max_graph_stagnant_rounds: int = 2

    def __post_init__(self) -> None:
        if isinstance(self.max_review_repairs, bool) or not isinstance(
            self.max_review_repairs, int
        ):
            raise ValueError("max_review_repairs must be an integer")
        if not 0 <= self.max_review_repairs <= 3:
            raise ValueError("max_review_repairs must be between 0 and 3")
        if self.mode not in {
            "static",
            "online_microtask",
            "parallel_atoms",
            "contract_graph",
        }:
            raise ValueError(
                "supervisor mode must be static, online_microtask, parallel_atoms, "
                "or contract_graph"
            )
        if (
            isinstance(self.max_online_directives, bool)
            or not isinstance(self.max_online_directives, int)
            or not 1 <= self.max_online_directives <= 256
        ):
            raise ValueError("max_online_directives must be between 1 and 256")
        if (
            isinstance(self.online_actions_per_directive, bool)
            or not isinstance(self.online_actions_per_directive, int)
            or not 1 <= self.online_actions_per_directive <= 32
        ):
            raise ValueError("online_actions_per_directive must be between 1 and 32")
        if (
            isinstance(self.online_protocol_rejections_per_directive, bool)
            or not isinstance(
                self.online_protocol_rejections_per_directive, int
            )
            or not 1 <= self.online_protocol_rejections_per_directive <= 12
        ):
            raise ValueError(
                "online_protocol_rejections_per_directive must be between 1 and 12"
            )
        if (
            isinstance(self.max_parallel_stages, bool)
            or not isinstance(self.max_parallel_stages, int)
            or not 1 <= self.max_parallel_stages <= 64
        ):
            raise ValueError("max_parallel_stages must be between 1 and 64")
        if (
            isinstance(self.max_parallel_atoms, bool)
            or not isinstance(self.max_parallel_atoms, int)
            or not 1 <= self.max_parallel_atoms <= 8
        ):
            raise ValueError("max_parallel_atoms must be between 1 and 8")
        if (
            isinstance(self.atom_max_transitions, bool)
            or not isinstance(self.atom_max_transitions, int)
            or not 1 <= self.atom_max_transitions <= 200
        ):
            raise ValueError("atom_max_transitions must be between 1 and 200")
        if (
            isinstance(self.max_graph_patches, bool)
            or not isinstance(self.max_graph_patches, int)
            or not 1 <= self.max_graph_patches <= 64
        ):
            raise ValueError("max_graph_patches must be between 1 and 64")
        if (
            isinstance(self.max_reviewer_rounds, bool)
            or not isinstance(self.max_reviewer_rounds, int)
            or not 1 <= self.max_reviewer_rounds <= 64
        ):
            raise ValueError("max_reviewer_rounds must be between 1 and 64")
        if (
            isinstance(self.max_graph_atoms, bool)
            or not isinstance(self.max_graph_atoms, int)
            or not 1 <= self.max_graph_atoms <= 256
        ):
            raise ValueError("max_graph_atoms must be between 1 and 256")
        if (
            isinstance(self.max_graph_stagnant_rounds, bool)
            or not isinstance(self.max_graph_stagnant_rounds, int)
            or not 1 <= self.max_graph_stagnant_rounds <= 8
        ):
            raise ValueError("max_graph_stagnant_rounds must be between 1 and 8")


def supervisor_identity(client: SupervisorClient) -> dict[str, str]:
    return {
        "provider": str(getattr(client, "provider_name", "unconfigured")),
        "model": str(getattr(client, "model_name", "unconfigured")),
    }


__all__ = [
    "ATOM_SCHEMA_VERSION",
    "CAPABILITY_ATOM_SCHEMA_VERSION",
    "DIRECTIVE_SCHEMA_VERSION",
    "PLAN_SCHEMA_VERSION",
    "REVIEW_SCHEMA_VERSION",
    "STAGE_SCHEMA_VERSION",
    "AtomRole",
    "DirectiveDisposition",
    "DirectiveReviewStatus",
    "ReviewDisposition",
    "StageDisposition",
    "SupervisorClient",
    "SupervisorAtom",
    "SupervisorDirective",
    "SupervisorDirectiveRequest",
    "SupervisorPlan",
    "SupervisorPlanRequest",
    "SupervisorPolicy",
    "SupervisorReview",
    "SupervisorReviewRequest",
    "SupervisorStage",
    "SupervisorStageRequest",
    "supervisor_identity",
]
