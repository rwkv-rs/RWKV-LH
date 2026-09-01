"""Deterministic current-Harness projection for the independent Selector lane."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from rwkv_lh.atom_execution import (
    AtomExecutionBinding,
    atom_contract_progress,
    final_answer_eligible,
)

from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.schema import ActionStatus, ModelCheckpoint, RunState


SELECTOR_STAGE_PROJECTION_VERSION = "rwkv-lh.current-direct-selector-stage.v1"
SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION = (
    "rwkv-lh.current-direct-selector-stage.v2"
)
SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION = (
    "rwkv-lh.current-direct-selector-stage.v3"
)


@dataclass(frozen=True)
class SelectorStageContext:
    """One explicit Planner-owned semantic stage passed to the Selector lane."""

    stage_objective: str
    stage_role: str = "work"

    def __post_init__(self) -> None:
        if not self.stage_objective.strip() or not self.stage_role.strip():
            raise ValueError("Selector stage context requires objective and role")


def _latest_action_fact(actions: Sequence[object]) -> dict[str, object] | None:
    latest = actions[-1] if actions else None
    if latest is None:
        return None
    result = dict(getattr(latest, "result", None) or {})
    raw_metadata = result.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    latest_fact: dict[str, object] = {
        "sequence": int(getattr(latest, "sequence", 0) or 0),
        "operation": str(getattr(latest, "action_type", "") or ""),
        "success": bool(result.get("success")),
        "outcome_type": str(
            result.get("outcome_type")
            or getattr(latest, "outcome_type", "")
            or "pending"
        ),
    }
    if "complete" in metadata:
        latest_fact["complete"] = bool(metadata["complete"])
    if "truncated" in metadata:
        latest_fact["truncated"] = bool(metadata["truncated"])
    return latest_fact


def selector_contract_progress(state: RunState) -> dict[str, object] | None:
    """Return bounded Harness progress, never arguments, paths, or result text."""

    binding = AtomExecutionBinding.from_goal(state.goal)
    if binding is None:
        return None
    progress = atom_contract_progress(state, binding=binding)
    if progress is None:  # Defensive: an explicit binding always has progress.
        raise RuntimeError("atom execution binding produced no contract progress")
    projection = progress.selector_projection(binding)
    projection["schema_version"] = SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION
    return projection


def render_selector_stage_objective(
    latest_fact: Mapping[str, object] | None,
) -> str:
    """Render the frozen minimal current-stage envelope."""

    return "CurrentDirectStageV1: " + json.dumps(
        {
            "schema_version": SELECTOR_STAGE_PROJECTION_VERSION,
            "instruction": (
                "Choose exactly one next direct operation for the immutable request, "
                "or final_answer only when no operation is needed."
            ),
            "latest_action": dict(latest_fact) if latest_fact is not None else None,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def selector_stage_objective(state: RunState) -> str:
    """Project only bounded operation/outcome facts, never result content."""

    actions = sorted(state.actions.values(), key=lambda item: item.sequence)
    binding = AtomExecutionBinding.from_goal(state.goal)
    if binding is not None:
        progress = atom_contract_progress(state, binding=binding)
        if progress is None:  # Defensive: an explicit binding always projects.
            raise RuntimeError("atom execution binding produced no contract progress")
        # S60 is an exact raw-logit classifier, not a contract interpreter.  The
        # former V2 envelope placed dozens of bookkeeping counters between the
        # atom meaning and the immutable requirement, causing a real Planner
        # context to shift list_directory into search_text.  Keep completion
        # authority in the eligibility gate and expose only bounded state+1
        # facts plus the immutable Planner-authored atom objective.  No paths,
        # arguments, result text, tool choice, or generated semantic field is
        # introduced here.
        return "CurrentDirectStageV3: " + json.dumps(
            {
                "schema_version": (
                    SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION
                ),
                "action_index": progress.action_count,
                "completion_ready": progress.completion_ready,
                "latest_action": (
                    dict(progress.latest_action)
                    if progress.latest_action is not None
                    else None
                ),
                # Keep the model-owned semantic question last in this stage.
                "atom_objective": binding.contract.atom.objective,
            },
            ensure_ascii=False,
            sort_keys=False,
            separators=(",", ":"),
        )
    return render_selector_stage_objective(_latest_action_fact(actions))


def goal_frontier_selector_context(
    state: RunState,
    frontier: Mapping[str, object],
) -> SelectorStageContext:
    """Expose only the current Planner objective to the tool-intent role."""

    step_id = str(frontier.get("step_id") or "").strip()
    objective = str(frontier.get("objective") or "").strip()
    if not step_id or not objective:
        raise ValueError("Goal frontier Selector context requires step_id and objective")
    step_revision = int(frontier.get("step_revision", 1) or 1)
    if step_revision < 1:
        raise ValueError("Goal frontier Selector context requires a positive revision")
    # The v8 renderer adds bounded progress before this value and places the
    # resulting one-step question at the continuation edge. The complete Goal,
    # other plan nodes, audit gaps, and Executor text are intentionally absent.
    return SelectorStageContext(
        stage_objective=objective,
        stage_role="tool_intent",
    )


def selector_final_answer_eligible(
    state: RunState,
    *,
    legacy_minimum_actions: int = 0,
) -> bool:
    """Close final eligibility over Harness-observed contract progress."""

    return final_answer_eligible(
        state,
        legacy_minimum_actions=legacy_minimum_actions,
    )


def build_network_selector_input(
    state: RunState,
    parent: ModelCheckpoint | None,
    *,
    eligible_labels: Sequence[str] | None = None,
    stage_context: SelectorStageContext | None = None,
) -> NetworkSelectorInput:
    """Create one causal delta for the Selector's independent persistent state."""

    prior_action_index = 0
    if parent is not None:
        metadata = parent.native_state_metadata or {}
        prior_action_index = max(0, int(metadata.get("action_index", 0) or 0))
    actions = sorted(state.actions.values(), key=lambda item: item.sequence)
    new_actions = [item for item in actions if item.sequence > prior_action_index]
    succeeded = tuple(
        item.action_type
        for item in new_actions
        if item.status is ActionStatus.SUCCEEDED
    )
    failed = tuple(
        item.action_type
        for item in new_actions
        if item.status is not ActionStatus.SUCCEEDED
    )
    binding = AtomExecutionBinding.from_goal(state.goal)
    selected_stage_objective = (
        stage_context.stage_objective
        if stage_context is not None
        else selector_stage_objective(state)
    )
    selected_stage_role = (
        stage_context.stage_role
        if stage_context is not None
        else binding.contract.atom.role.value
        if binding
        else "work"
    )
    return NetworkSelectorInput.create(
        task_request=state.goal.request,
        stage_objective=selected_stage_objective,
        stage_role=selected_stage_role,
        progress=NetworkSelectorProgress(
            completed_stage_count=len(actions),
            action_index=(actions[-1].sequence if actions else 0),
            succeeded_operations=succeeded,
            failed_operations=failed,
            protocol_rejection_count=state.protocol_rejections,
        ),
        **(
            {"eligible_labels": tuple(str(item) for item in eligible_labels)}
            if eligible_labels is not None
            else {}
        ),
    )


__all__ = [
    "SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION",
    "SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION",
    "SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION",
    "SELECTOR_STAGE_PROJECTION_VERSION",
    "SelectorStageContext",
    "build_network_selector_input",
    "goal_frontier_selector_context",
    "render_selector_stage_objective",
    "selector_contract_progress",
    "selector_final_answer_eligible",
    "selector_stage_objective",
]
