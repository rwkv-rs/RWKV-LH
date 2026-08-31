"""Versioned contracts for the advisory RWKV State Router.

The router is deliberately separated from authorization and execution.  It may
recommend a route, but controller evidence and Network Gate facts remain the
mechanical authority.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence
from uuid import uuid4


ROUTER_INPUT_SCHEMA_VERSION = "rwkv-lh.state-router-input.v1"
ROUTER_OUTPUT_SCHEMA_VERSION = "rwkv-lh.state-router-output.v1"
ROUTER_VERSION = "state-router-v1"


class _StringEnum(str, Enum):
    def __str__(self) -> str:
        return self.value


class ContextMode(_StringEnum):
    FRESH = "fresh"
    CONTINUATION = "continuation"


class EvidenceState(_StringEnum):
    NONE = "none"
    MISSING = "evidence_missing"
    PARTIAL = "evidence_partial"
    COMMITTED = "evidence_committed"


class PolicyState(_StringEnum):
    NETWORK_ALLOWED = "network_allowed"
    NETWORK_DENIED = "network_denied"


class ExecutionPhase(_StringEnum):
    EVIDENCE_MISSING = "evidence_missing"
    EVIDENCE_PARTIAL = "evidence_partial"
    EVIDENCE_COMMITTED = "evidence_committed"
    POLICY_REJECTED = "policy_rejected"


class RouteFamily(_StringEnum):
    LOCAL = "local"
    DETERMINISTIC = "deterministic"
    WEB = "web"
    CONNECTOR = "connector"
    MIXED = "mixed"
    FINAL = "final"
    ABSTAIN = "abstain"


class NetworkRecommendation(_StringEnum):
    REQUIRED = "network_required"
    NOT_REQUIRED = "network_not_required"


CONTEXT_LABELS = tuple(item.value for item in ContextMode)
PHASE_LABELS = tuple(item.value for item in ExecutionPhase)
ROUTE_LABELS = tuple(item.value for item in RouteFamily)
NETWORK_LABELS = tuple(item.value for item in NetworkRecommendation)
HEAD_LABELS: dict[str, tuple[str, ...]] = {
    "context_mode": CONTEXT_LABELS,
    "execution_phase": PHASE_LABELS,
    "route_family": ROUTE_LABELS,
    "network_recommendation": NETWORK_LABELS,
}

NETWORK_ROUTE_FAMILIES = frozenset(
    {RouteFamily.WEB, RouteFamily.CONNECTOR, RouteFamily.MIXED}
)
STATE_PROFILES = frozenset(
    {
        "S_base",
        "S_local",
        "S_web",
        "S_connector",
        "S_mixed",
        "S_completion",
    }
)


def canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RouterInput:
    """One normalized classification input.

    ``mode``, ``evidence_state`` and ``policy_state`` are controller facts.  A
    Summary is untrusted descriptive context and cannot override those fields.
    """

    mode: ContextMode
    summary: str | None
    evidence_state: EvidenceState
    policy_state: PolicyState
    request: str
    trace_id: str = field(default_factory=lambda: f"RTR-{uuid4().hex[:16]}")
    schema_version: str = ROUTER_INPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ROUTER_INPUT_SCHEMA_VERSION:
            raise ValueError(f"unsupported router input schema: {self.schema_version}")
        if not self.request.strip():
            raise ValueError("router request must be non-empty")
        if self.mode is ContextMode.FRESH:
            if self.summary is not None:
                raise ValueError("fresh router input cannot carry a Summary")
            if self.evidence_state is not EvidenceState.NONE:
                raise ValueError("fresh router input must use EvidenceState=none")
        if self.summary is not None and not self.summary.strip():
            raise ValueError("router Summary must be null or non-empty")
        if not self.trace_id.strip():
            raise ValueError("router trace_id must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "trace_id": self.trace_id,
            "mode": self.mode.value,
            "summary": self.summary,
            "evidence_state": self.evidence_state.value,
            "policy_state": self.policy_state.value,
            "request": self.request,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RouterInput":
        summary = value.get("summary")
        return cls(
            schema_version=str(
                value.get("schema_version") or ROUTER_INPUT_SCHEMA_VERSION
            ),
            trace_id=str(value.get("trace_id") or f"RTR-{uuid4().hex[:16]}"),
            mode=ContextMode(str(value.get("mode") or "")),
            summary=None if summary is None else str(summary),
            evidence_state=EvidenceState(str(value.get("evidence_state") or "")),
            policy_state=PolicyState(str(value.get("policy_state") or "")),
            request=str(value.get("request") or ""),
        )

    def render(self) -> str:
        """Render the frozen, injection-resistant feature extraction protocol."""

        summary = "<none>" if self.summary is None else canonical_json(self.summary)
        return "\n".join(
            (
                f"Mode: {self.mode.value}",
                f"Summary: {summary}",
                f"EvidenceState: {self.evidence_state.value}",
                f"PolicyState: {self.policy_state.value}",
                f"Request: {canonical_json(self.request)}",
            )
        )


@dataclass(frozen=True)
class AbstainThresholds:
    route_confidence: float = 0.92
    route_margin: float = 0.30
    ood_score: float = 0.50

    def __post_init__(self) -> None:
        for name, value in (
            ("route_confidence", self.route_confidence),
            ("route_margin", self.route_margin),
            ("ood_score", self.ood_score),
        ):
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be in [0, 1]")


def _validated_probabilities(
    head: str,
    probabilities: Mapping[str, float],
) -> dict[str, float]:
    expected = HEAD_LABELS[head]
    if set(probabilities) != set(expected):
        raise ValueError(
            f"{head} probabilities must contain exactly {', '.join(expected)}"
        )
    values = {label: float(probabilities[label]) for label in expected}
    if any(not math.isfinite(value) or value < 0.0 for value in values.values()):
        raise ValueError(f"{head} probabilities must be finite and non-negative")
    total = sum(values.values())
    if not math.isclose(total, 1.0, rel_tol=1e-5, abs_tol=1e-5):
        raise ValueError(f"{head} probabilities must sum to 1, got {total}")
    return values


def _top_two(probabilities: Mapping[str, float]) -> tuple[str, float, float]:
    ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
    return ranked[0][0], ranked[0][1], ranked[0][1] - ranked[1][1]


def mechanical_execution_phase(
    router_input: RouterInput,
    *,
    candidate_route: RouteFamily,
    network_recommendation: NetworkRecommendation,
) -> ExecutionPhase:
    """Resolve phase from controller/Gate facts before any learned phase head."""

    if (
        router_input.policy_state is PolicyState.NETWORK_DENIED
        and network_recommendation is NetworkRecommendation.REQUIRED
    ):
        return ExecutionPhase.POLICY_REJECTED
    if router_input.evidence_state is EvidenceState.COMMITTED:
        return ExecutionPhase.EVIDENCE_COMMITTED
    if router_input.evidence_state is EvidenceState.PARTIAL:
        return ExecutionPhase.EVIDENCE_PARTIAL
    if (
        candidate_route is RouteFamily.FINAL
        and network_recommendation is NetworkRecommendation.NOT_REQUIRED
    ):
        return ExecutionPhase.EVIDENCE_COMMITTED
    return ExecutionPhase.EVIDENCE_MISSING


def state_profile_for(route: RouteFamily, phase: ExecutionPhase) -> str:
    if phase in {
        ExecutionPhase.EVIDENCE_COMMITTED,
        ExecutionPhase.POLICY_REJECTED,
    }:
        return "S_completion"
    return {
        RouteFamily.LOCAL: "S_local",
        RouteFamily.WEB: "S_web",
        RouteFamily.CONNECTOR: "S_connector",
        RouteFamily.MIXED: "S_mixed",
    }.get(route, "S_base")


@dataclass(frozen=True)
class RouterOutput:
    context_mode: ContextMode
    execution_phase: ExecutionPhase
    route_family: RouteFamily
    network_recommendation: NetworkRecommendation
    state_profile: str
    confidence: Mapping[str, float]
    abstain: bool
    router_version: str
    model_hash: str
    head_hash: str
    trace_id: str
    abstain_reasons: tuple[str, ...] = ()
    candidate_route_family: RouteFamily | None = None
    schema_version: str = ROUTER_OUTPUT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != ROUTER_OUTPUT_SCHEMA_VERSION:
            raise ValueError(f"unsupported router output schema: {self.schema_version}")
        if self.router_version != ROUTER_VERSION:
            raise ValueError(f"unsupported router version: {self.router_version}")
        if self.state_profile not in STATE_PROFILES:
            raise ValueError(f"unknown state profile: {self.state_profile}")
        if set(self.confidence) != set(HEAD_LABELS):
            raise ValueError("router confidence must contain all classification heads")
        if any(
            not math.isfinite(float(value)) or not 0.0 <= float(value) <= 1.0
            for value in self.confidence.values()
        ):
            raise ValueError("router confidence values must be in [0, 1]")
        if not self.model_hash or not self.head_hash or not self.trace_id:
            raise ValueError("router output requires model, head and trace identifiers")
        if self.abstain:
            if self.route_family is not RouteFamily.ABSTAIN:
                raise ValueError("abstaining output must use route_family=abstain")
            if self.state_profile != "S_base":
                raise ValueError("abstaining output must fall back to S_base")
            if not self.abstain_reasons:
                raise ValueError("abstaining output requires at least one reason")
        elif self.route_family is RouteFamily.ABSTAIN:
            raise ValueError("route_family=abstain requires abstain=true")

    def to_dict(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": self.schema_version,
            "context_mode": self.context_mode.value,
            "execution_phase": self.execution_phase.value,
            "route_family": self.route_family.value,
            "network_recommendation": self.network_recommendation.value,
            "state_profile": self.state_profile,
            "confidence": {
                name: float(self.confidence[name]) for name in HEAD_LABELS
            },
            "abstain": self.abstain,
            "router_version": self.router_version,
            "model_hash": self.model_hash,
            "head_hash": self.head_hash,
            "trace_id": self.trace_id,
        }
        if self.abstain_reasons:
            value["abstain_reasons"] = list(self.abstain_reasons)
        if self.candidate_route_family is not None:
            value["candidate_route_family"] = self.candidate_route_family.value
        return value


def resolve_router_output(
    router_input: RouterInput,
    probabilities: Mapping[str, Mapping[str, float]],
    *,
    model_hash: str,
    head_hash: str,
    thresholds: AbstainThresholds = AbstainThresholds(),
    ood_score: float = 0.0,
    extra_conflicts: Sequence[str] = (),
) -> RouterOutput:
    """Apply confidence, conflict, OOD and deterministic-authority rules."""

    if set(probabilities) != set(HEAD_LABELS):
        raise ValueError("probabilities must contain all State Router heads")
    checked = {
        name: _validated_probabilities(name, probabilities[name])
        for name in HEAD_LABELS
    }
    winners: dict[str, str] = {}
    confidence: dict[str, float] = {}
    route_margin = 0.0
    for name, values in checked.items():
        winner, score, margin = _top_two(values)
        winners[name] = winner
        confidence[name] = score
        if name == "route_family":
            route_margin = margin

    candidate_route = RouteFamily(winners["route_family"])
    network = NetworkRecommendation(winners["network_recommendation"])
    mechanical_phase = mechanical_execution_phase(
        router_input,
        candidate_route=candidate_route,
        network_recommendation=network,
    )
    conflicts = list(str(item) for item in extra_conflicts if str(item))
    if winners["context_mode"] != router_input.mode.value:
        conflicts.append("context_mode_conflicts_with_controller")
    if winners["execution_phase"] != mechanical_phase.value:
        conflicts.append("execution_phase_conflicts_with_controller")
    expected_network = (
        NetworkRecommendation.REQUIRED
        if candidate_route in NETWORK_ROUTE_FAMILIES
        else NetworkRecommendation.NOT_REQUIRED
    )
    policy_stop = mechanical_phase is ExecutionPhase.POLICY_REJECTED
    if (
        candidate_route not in {RouteFamily.ABSTAIN, RouteFamily.FINAL}
        and network is not expected_network
    ):
        conflicts.append("route_network_heads_conflict")
    if candidate_route is RouteFamily.FINAL and not policy_stop:
        if network is not NetworkRecommendation.NOT_REQUIRED:
            conflicts.append("final_route_still_requests_network")

    reasons: list[str] = []
    if candidate_route is RouteFamily.ABSTAIN:
        reasons.append("route_head_abstained")
    if confidence["route_family"] < thresholds.route_confidence:
        reasons.append("route_confidence_below_threshold")
    if route_margin < thresholds.route_margin:
        reasons.append("route_margin_below_threshold")
    if not math.isfinite(float(ood_score)) or float(ood_score) < 0.0:
        raise ValueError("ood_score must be finite and non-negative")
    if float(ood_score) >= thresholds.ood_score:
        reasons.append("out_of_distribution")
    reasons.extend(conflicts)
    reasons = list(dict.fromkeys(reasons))
    abstain = bool(reasons)
    resolved_route = RouteFamily.ABSTAIN if abstain else candidate_route
    profile = (
        "S_base"
        if abstain
        else state_profile_for(resolved_route, mechanical_phase)
    )
    return RouterOutput(
        context_mode=router_input.mode,
        execution_phase=mechanical_phase,
        route_family=resolved_route,
        candidate_route_family=candidate_route if abstain else None,
        network_recommendation=network,
        state_profile=profile,
        confidence=confidence,
        abstain=abstain,
        abstain_reasons=tuple(reasons),
        router_version=ROUTER_VERSION,
        model_hash=str(model_hash),
        head_hash=str(head_hash),
        trace_id=router_input.trace_id,
    )


__all__ = [
    "AbstainThresholds",
    "CONTEXT_LABELS",
    "ContextMode",
    "EvidenceState",
    "ExecutionPhase",
    "HEAD_LABELS",
    "NETWORK_LABELS",
    "NETWORK_ROUTE_FAMILIES",
    "NetworkRecommendation",
    "PHASE_LABELS",
    "PolicyState",
    "ROUTE_LABELS",
    "ROUTER_INPUT_SCHEMA_VERSION",
    "ROUTER_OUTPUT_SCHEMA_VERSION",
    "ROUTER_VERSION",
    "RouteFamily",
    "RouterInput",
    "RouterOutput",
    "canonical_digest",
    "canonical_json",
    "mechanical_execution_phase",
    "resolve_router_output",
    "state_profile_for",
]
