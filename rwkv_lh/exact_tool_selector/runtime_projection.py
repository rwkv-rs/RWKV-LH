"""Deterministic current-Harness projection for the independent Selector lane."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence

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
    progress = selector_contract_progress(state)
    if progress is not None:
        return "CurrentDirectStageV2: " + json.dumps(
            progress,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    return render_selector_stage_objective(_latest_action_fact(actions))


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
    return NetworkSelectorInput.create(
        task_request=state.goal.request,
        stage_objective=selector_stage_objective(state),
        stage_role=(binding.contract.atom.role.value if binding else "work"),
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
    "SELECTOR_STAGE_PROJECTION_VERSION",
    "build_network_selector_input",
    "render_selector_stage_objective",
    "selector_contract_progress",
    "selector_final_answer_eligible",
    "selector_stage_objective",
]
