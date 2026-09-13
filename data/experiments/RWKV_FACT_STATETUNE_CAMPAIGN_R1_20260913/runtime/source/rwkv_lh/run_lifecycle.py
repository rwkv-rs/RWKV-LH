"""Immutable run-lifecycle policy and Goal-mode termination invariants."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.schema import GoalState


RUN_LIFECYCLE_POLICY_KEY = "run_lifecycle"
RUN_LIFECYCLE_POLICY_SCHEMA_VERSION = "rwkv-lh.run-lifecycle-policy.v1"
BOUNDED_EXECUTION_MODE = "bounded"
GOAL_EXECUTION_MODE = "goal"


def run_lifecycle_policy_document(mode: str = BOUNDED_EXECUTION_MODE) -> dict[str, Any]:
    """Return the canonical lifecycle policy persisted with the literal Goal."""

    selected = str(mode or BOUNDED_EXECUTION_MODE).strip().casefold()
    if selected not in {BOUNDED_EXECUTION_MODE, GOAL_EXECUTION_MODE}:
        raise ValueError("execution mode must be bounded or goal")
    self_termination_only = selected == GOAL_EXECUTION_MODE
    return {
        "schema_version": RUN_LIFECYCLE_POLICY_SCHEMA_VERSION,
        "mode": selected,
        "self_termination_only": self_termination_only,
        "budget_boundary": (
            "checkpoint_and_continue"
            if self_termination_only
            else "interrupt"
        ),
        "completion_authority": "rwkv_explicit_final_answer",
    }


def run_lifecycle_policy_from_goal(goal: GoalState) -> dict[str, Any]:
    """Validate and return the Goal-bound lifecycle policy.

    Goals written before this policy existed remain bounded.  New Goal Studio
    runs persist the explicit ``goal`` policy, so resumption cannot silently
    change termination semantics.
    """

    raw = goal.runtime_policy.get(RUN_LIFECYCLE_POLICY_KEY)
    if raw is None:
        return run_lifecycle_policy_document()
    if not isinstance(raw, Mapping):
        raise TypeError("run lifecycle policy must be an object")
    selected = run_lifecycle_policy_document(str(raw.get("mode") or ""))
    if dict(raw) != selected:
        raise ValueError("run lifecycle policy contains non-canonical fields")
    return selected


def goal_self_termination_only(goal: GoalState) -> bool:
    """Return whether this top-level Goal may end only by an RWKV Final."""

    return bool(run_lifecycle_policy_from_goal(goal)["self_termination_only"])


def model_voluntary_completion(payload: Mapping[str, Any]) -> bool:
    """Recognize a completion sourced from an explicit RWKV final decision."""

    source = str(payload.get("output_source") or "")
    decision_id = str(payload.get("decision_id") or "")
    return bool(decision_id) and source in {
        "rwkv_explicit_final_answer_text",
        "rwkv_parallel_finalizer_exact_candidate",
        "rwkv_contract_finalizer_exact_candidate",
    }


__all__ = [
    "BOUNDED_EXECUTION_MODE",
    "GOAL_EXECUTION_MODE",
    "RUN_LIFECYCLE_POLICY_KEY",
    "RUN_LIFECYCLE_POLICY_SCHEMA_VERSION",
    "goal_self_termination_only",
    "model_voluntary_completion",
    "run_lifecycle_policy_document",
    "run_lifecycle_policy_from_goal",
]
