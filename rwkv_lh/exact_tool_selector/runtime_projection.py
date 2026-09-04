"""Deterministic current-Harness projection for the independent Selector lane."""

from __future__ import annotations

import hashlib
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
    network_selector_tool_menu,
)
from rwkv_lh.goal_loop_protocol import (
    goal_step_action_bindings,
    rolling_goal_plan,
)
from rwkv_lh.schema import ActionStatus, ModelCheckpoint, RunState


SELECTOR_STAGE_PROJECTION_VERSION = "rwkv-lh.current-direct-selector-stage.v1"
SELECTOR_CONTRACT_STAGE_PROJECTION_VERSION = (
    "rwkv-lh.current-direct-selector-stage.v2"
)
SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION = (
    "rwkv-lh.current-direct-selector-stage.v3"
)
SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION = (
    "rwkv-lh.goal-frontier-selector-stage.v2"
)
_SELECTOR_RESULT_PROJECTION_LIMIT = 1800


@dataclass(frozen=True)
class SelectorStageContext:
    """One explicit Planner-owned semantic stage passed to the Selector lane."""

    stage_objective: str
    stage_role: str = "work"
    state_scope_id: str = ""
    action_ids: tuple[str, ...] | None = None

    def __post_init__(self) -> None:
        if not self.stage_objective.strip() or not self.stage_role.strip():
            raise ValueError("Selector stage context requires objective and role")
        if self.action_ids is not None:
            if not self.state_scope_id.strip():
                raise ValueError("scoped Selector context requires a state scope id")
            selected = tuple(str(item) for item in self.action_ids)
            if len(set(selected)) != len(selected) or any(
                not item for item in selected
            ):
                raise ValueError("Selector context action ids must be unique and non-empty")
            object.__setattr__(self, "action_ids", selected)


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
    *,
    eligible_labels: Sequence[str] | None = None,
) -> SelectorStageContext:
    """Project one complete, bounded next-state frontier to the Selector role.

    The projection keeps the G1J outer prompt schema unchanged. It carries only
    the active Planner step, Harness facts assigned to that step, the latest
    audit feedback for that step, and descriptions for the currently eligible
    labels. It never carries the workspace's absolute root or another plan node.
    """

    step_id = str(frontier.get("step_id") or "").strip()
    objective = str(frontier.get("objective") or "").strip()
    if not step_id or not objective:
        raise ValueError("Goal frontier Selector context requires step_id and objective")
    step_revision = int(frontier.get("step_revision", 1) or 1)
    if step_revision < 1:
        raise ValueError("Goal frontier Selector context requires a positive revision")

    selected_labels = tuple(
        dict.fromkeys(str(item) for item in (eligible_labels or ()) if str(item))
    )
    descriptions = {
        str(item["name"]): str(item["description"])
        for item in network_selector_tool_menu()
    }
    unknown_labels = set(selected_labels) - set(descriptions)
    if unknown_labels:
        raise ValueError(
            f"Goal frontier has unknown Selector labels: {sorted(unknown_labels)}"
        )

    plan = rolling_goal_plan(state)
    bindings = goal_step_action_bindings(state)
    assigned_actions = sorted(
        (
            action
            for action_id, action in state.actions.items()
            if bindings.get(action_id) == (step_id, step_revision)
        ),
        key=lambda item: item.sequence,
    )
    latest_action = assigned_actions[-1] if assigned_actions else None

    def bounded(value: object, limit: int) -> object:
        rendered = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        if len(rendered) <= limit:
            return value
        return {
            "json_preview": rendered[:limit],
            "sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            "truncated": True,
        }

    action_projection: dict[str, object] | None = None
    if latest_action is not None:
        action_projection = {
            "action_id": latest_action.action_id,
            "sequence": latest_action.sequence,
            "operation": latest_action.action_type,
            "status": latest_action.status.value,
            "arguments": bounded(dict(latest_action.arguments), 800),
            "result": bounded(
                dict(latest_action.result or {}),
                _SELECTOR_RESULT_PROJECTION_LIMIT,
            ),
            "error": bounded(dict(latest_action.error or {}), 600),
        }

    boundary_steps: dict[str, str] = {}
    for event_id in state.causal_order:
        event = state.causal_records[event_id]
        if event.event_type == "goal_audit_boundary_opened":
            boundary_steps[event.subject_id] = str(
                event.payload.get("active_step_id") or ""
            )

    audit_projection: dict[str, object] | None = None
    for event_id in reversed(state.causal_order):
        event = state.causal_records[event_id]
        payload = event.payload
        if event.event_type == "goal_step_evidence_gap_recorded":
            if (
                str(payload.get("active_step_id") or "") != step_id
                or int(payload.get("active_step_revision", 0) or 0)
                != step_revision
            ):
                continue
            audit_projection = {
                "status": "mechanically_incomplete",
                "gaps": list(payload.get("gaps") or ()),
                "successful_action_ids": list(
                    payload.get("successful_action_ids") or ()
                ),
                "missing_read_roots": list(
                    payload.get("missing_read_roots") or ()
                ),
                "missing_write_roots": list(
                    payload.get("missing_write_roots") or ()
                ),
            }
            break
        if event.event_type == "goal_audit_accepted":
            raw_audit = payload.get("audit")
            if not isinstance(raw_audit, Mapping):
                continue
            audit_step_id = str(raw_audit.get("step_id") or "")
            boundary_id = str(payload.get("audit_boundary_id") or "")
            if audit_step_id != step_id and boundary_steps.get(boundary_id) != step_id:
                continue
            audit_projection = {
                "status": "accepted",
                "verdict": str(raw_audit.get("verdict") or ""),
                "evidence_refs": list(raw_audit.get("evidence_refs") or ()),
                "gaps": list(raw_audit.get("gaps") or ()),
                "reason": str(raw_audit.get("reason") or ""),
            }
            break
        if event.event_type == "goal_audit_rejected":
            boundary_id = str(payload.get("audit_boundary_id") or "")
            if boundary_steps.get(boundary_id) != step_id:
                continue
            audit_projection = {
                "status": "protocol_rejected",
                "error": str(payload.get("error") or ""),
                "retry_scheduled": bool(payload.get("retry_scheduled")),
            }
            break
        if (
            event.event_type == "goal_audit_boundary_resolved"
            and str(payload.get("verdict") or "") == "protocol_invalid"
            and str(payload.get("active_step_id") or "") == step_id
        ):
            audit_projection = {
                "status": "protocol_invalid",
                "error": str(payload.get("protocol_error") or ""),
            }
            break

    active_step = {
        "step_id": step_id,
        "step_revision": step_revision,
        "stage": int(frontier.get("stage", 1) or 1),
        "planned_phase": str(frontier.get("phase") or ""),
        "effective_phase": str(
            frontier.get("effective_phase") or frontier.get("phase") or ""
        ),
        "depends_on": list(frontier.get("depends_on") or ()),
        "read_roots": list(frontier.get("read_roots") or ()),
        "write_roots": list(frontier.get("write_roots") or ()),
        "success_evidence": list(frontier.get("success_evidence") or ()),
        "constraints": list(frontier.get("constraints") or ()),
    }
    stage_objective = "GoalFrontierStateV2: " + json.dumps(
        {
            "schema_version": SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION,
            "active_step": active_step,
            "progress": {
                "completed_step_ids": sorted(plan.completed_step_ids),
                "completed_stage_count": len(plan.completed_stages),
                "current_step_action_count": len(assigned_actions),
            },
            "latest_action": action_projection,
            "latest_audit_feedback": audit_projection,
            "eligible_tools": [
                {"name": label, "description": descriptions[label]}
                for label in selected_labels
            ],
            "instruction": (
                "Choose exactly one eligible next operation for this active step. "
                "Use the latest Harness result and audit gaps; do not plan, fill "
                "parameters, audit, or answer the user."
            ),
            "current_objective": objective,
        },
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )
    return SelectorStageContext(
        stage_objective=stage_objective,
        stage_role="tool_intent",
        state_scope_id=f"planner-step:{step_id}:revision:{step_revision}",
        action_ids=tuple(action.action_id for action in assigned_actions),
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
    menu_order_id: str = "canonical",
) -> NetworkSelectorInput:
    """Create one causal delta for the Selector's independent persistent state."""

    prior_action_index = 0
    prior_protocol_rejections = 0
    if parent is not None:
        metadata = parent.native_state_metadata or {}
        prior_action_index = max(0, int(metadata.get("action_index", 0) or 0))
        prior_protocol_rejections = max(
            0,
            int(
                metadata.get(
                    "run_protocol_rejection_count",
                    metadata.get("protocol_rejection_count", 0),
                )
                or 0
            ),
        )
    elif stage_context is not None and stage_context.action_ids is not None:
        # A new local Selector lane must not replay rejection counts from other
        # step revisions.  This run-total baseline is stored on the checkpoint;
        # later calls in the same scope receive only their causal delta.
        prior_protocol_rejections = state.protocol_rejections
    scoped_action_ids = (
        None
        if stage_context is None or stage_context.action_ids is None
        else set(stage_context.action_ids)
    )
    actions = sorted(
        (
            action
            for action in state.actions.values()
            if scoped_action_ids is None or action.action_id in scoped_action_ids
        ),
        key=lambda item: item.sequence,
    )
    new_actions = [item for item in actions if item.sequence > prior_action_index]
    # These fields describe newly observed operation kinds, not one entry per
    # action. The parent checkpoint's action_index makes this a causal delta;
    # cache reconstruction with parent=None deterministically reprojects the
    # complete observed history. Preserve first-observation order while keeping
    # the protocol's set-like uniqueness invariant.
    succeeded = tuple(
        dict.fromkeys(
            item.action_type
            for item in new_actions
            if item.status is ActionStatus.SUCCEEDED
        )
    )
    failed = tuple(
        dict.fromkeys(
            item.action_type
            for item in new_actions
            if item.status is not ActionStatus.SUCCEEDED
        )
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
    completed_stage_count = len(actions)
    if stage_context is not None and stage_context.stage_role == "tool_intent":
        completed_stage_count = len(rolling_goal_plan(state).completed_stages)
    return NetworkSelectorInput.create(
        task_request=state.goal.request,
        stage_objective=selected_stage_objective,
        stage_role=selected_stage_role,
        progress=NetworkSelectorProgress(
            completed_stage_count=completed_stage_count,
            action_index=(actions[-1].sequence if actions else 0),
            succeeded_operations=succeeded,
            failed_operations=failed,
            protocol_rejection_count=max(
                0,
                state.protocol_rejections - prior_protocol_rejections,
            ),
        ),
        **(
            {"eligible_labels": tuple(str(item) for item in eligible_labels)}
            if eligible_labels is not None
            else {}
        ),
        menu_order_id=menu_order_id,
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
