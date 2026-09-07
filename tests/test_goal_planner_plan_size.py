"""Planner plan size is task driven across parsing, revision and stage review."""
from dataclasses import replace

import pytest

from rwkv_lh.goal_loop_protocol import (
    AuditedStep,
    GoalAuditDecision,
    GoalAuditVerdict,
    GoalObligation,
    GoalPlanPatch,
    GoalPlanStep,
    GoalStageReviewRequest,
    RollingGoalPlan,
)
from rwkv_lh.supervisor_openai import OpenAICompatibleSupervisorClient


def _steps(count: int, *, serial: bool = False) -> tuple[GoalPlanStep, ...]:
    return tuple(
        GoalPlanStep(
            step_id=f"S{index}",
            objective=f"Inspect source {index}",
            phase="observe",
            stage=index if serial else 1,
            depends_on=(f"S{index - 1}",) if serial and index > 1 else (),
            obligation_ids=("O1",),
            success_evidence=(f"Source {index} is observed",),
            read_roots=(f"source-{index}.txt",),
        )
        for index in range(1, count + 1)
    )


def _initial_patch(steps: tuple[GoalPlanStep, ...]) -> GoalPlanPatch:
    return GoalPlanPatch(
        patch_id="GPP-initial",
        base_revision=0,
        add_steps=steps,
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect all requested sources",
        goal_obligations=(GoalObligation(
            obligation_id="O1",
            predicate="All requested sources are inspected",
            required_phases=("observe",),
        ),),
    )


@pytest.mark.parametrize("count,serial", [(6, False), (19, True), (64, False)])
def test_large_plan_round_trip_preserves_every_step_and_stage(count, serial):
    patch = _initial_patch(_steps(count, serial=serial))
    # Derive the model form from the sole production serializer.
    value = patch.to_dict()
    for key in ("schema_version", "patch_id", "base_revision"):
        value.pop(key)
    for stage in value["add_stages"]:
        for step in stage["steps"]:
            step.pop("allowed_operations")
    parsed = GoalPlanPatch.from_model_value(
        value, patch_id=patch.patch_id, base_revision=patch.base_revision,
    )
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(parsed)

    assert parsed == patch
    assert GoalPlanPatch.from_dict(parsed.to_dict()) == patch
    assert tuple(plan.steps) == tuple(step.step_id for step in patch.add_steps)
    projected = plan.to_model_dict()
    assert sum(len(stage["steps"]) for stage in projected["stages"]) == count
    assert len(plan.frontier) == (1 if serial else count)


def test_continuation_can_grow_existing_open_plan_and_replace_or_discard_many():
    steps = _steps(9)
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(_initial_patch(steps[:4]))
    plan.apply_goal_patch(GoalPlanPatch(
        patch_id="GPP-extend", base_revision=1, add_steps=steps[4:],
        replace_steps=(), discard_step_ids=(), reason="Include remaining sources",
    ))
    assert tuple(plan.open_step_ids) == tuple(step.step_id for step in steps)
    plan.apply_goal_patch(GoalPlanPatch(
        patch_id="GPP-replace", base_revision=2, add_steps=(),
        replace_steps=tuple(replace(step, objective=f"Reinspect {step.step_id}") for step in steps),
        discard_step_ids=(), reason="Replace the complete open frontier",
    ))
    assert all(plan.step_revisions[step.step_id] == 2 for step in steps)
    plan.apply_goal_patch(GoalPlanPatch(
        patch_id="GPP-discard", base_revision=3, add_steps=(), replace_steps=(),
        discard_step_ids=tuple(step.step_id for step in steps[1:]),
        reason="Discard all superseded sources",
    ))
    assert tuple(plan.open_step_ids) == ("S1",)


def test_large_completed_stage_delivers_every_step_to_stage_checker():
    steps = _steps(8)
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(_initial_patch(steps))
    for step in steps:
        refs = (f"A-{step.step_id}",)
        plan.apply_audit(GoalAuditDecision(
            audit_id=f"AUD-{step.step_id}", verdict=GoalAuditVerdict.CONTINUE,
            step_id=step.step_id, evidence_refs=refs, gaps=(),
            completed_steps=(AuditedStep(step.step_id, refs),), reason="Observed",
        ))
    request = GoalStageReviewRequest(
        run_id="RUN-large-stage", immutable_request="Inspect every source",
        goal_digest=plan.goal_digest, stage=1,
        stage_steps=tuple(step.to_dict() for step in steps), workspace_manifest={},
    )
    assert plan.batch_complete
    assert [step["step_id"] for step in request.to_dict()["stage_steps"]] == [step.step_id for step in steps]


def test_stage_review_has_no_independent_step_ceiling():
    request = GoalStageReviewRequest(
        run_id="RUN-review", immutable_request="Inspect every source",
        goal_digest="goal", stage=1,
        stage_steps=tuple(step.to_dict() for step in _steps(8)),
        workspace_manifest={},
    )
    assert len(request.to_dict()["stage_steps"]) == 8


def test_later_step_can_depend_on_every_step_of_a_large_prior_stage():
    prior = _steps(8)
    dependent = GoalPlanStep(
        step_id="S9", objective="Inspect the combined report", phase="observe",
        stage=2, depends_on=tuple(step.step_id for step in prior),
        obligation_ids=("O1",), success_evidence=("Combined report observed",),
        read_roots=("report.txt",),
    )
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(_initial_patch((*prior, dependent)))
    assert plan.steps["S9"].depends_on == tuple(step.step_id for step in prior)
    assert "S9" not in {step.step_id for step in plan.frontier}
    for step in prior:
        refs = (f"A-{step.step_id}",)
        plan.apply_audit(GoalAuditDecision(
            audit_id=f"AUD-{step.step_id}", verdict=GoalAuditVerdict.CONTINUE,
            step_id=step.step_id, evidence_refs=refs, gaps=(),
            completed_steps=(AuditedStep(step.step_id, refs),), reason="Observed",
        ))
    assert tuple(step.step_id for step in plan.frontier) == ("S9",)
    assert not plan.complete


def test_plan_does_not_complete_at_a_former_step_boundary():
    steps = _steps(19, serial=True)
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(_initial_patch(steps))
    for index, step in enumerate(steps, start=1):
        assert not plan.complete
        refs = (f"A-{step.step_id}",)
        plan.apply_audit(GoalAuditDecision(
            audit_id=f"AUD-{step.step_id}", verdict=GoalAuditVerdict.CONTINUE,
            step_id=step.step_id, evidence_refs=refs, gaps=(),
            completed_steps=(AuditedStep(step.step_id, refs),), reason="Observed",
        ))
        assert plan.batch_complete == (index == len(steps))
    assert plan.complete


@pytest.mark.parametrize("fault", ["unknown_dependency", "same_stage_dependency", "root_conflict"])
def test_large_plan_still_rejects_invalid_dependencies_and_conflicting_roots(fault):
    steps = _steps(8)
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(_initial_patch(steps))
    before = plan.to_model_dict()
    changed = replace(steps[-1], depends_on=("missing",))
    if fault == "same_stage_dependency":
        changed = replace(steps[-1], depends_on=(steps[0].step_id,))
    elif fault == "root_conflict":
        changed = replace(steps[-1], phase="mutate", read_roots=(), write_roots=steps[0].read_roots)
    with pytest.raises(ValueError):
        plan.apply_goal_patch(GoalPlanPatch(
            patch_id="GPP-invalid", base_revision=1, add_steps=(),
            replace_steps=(changed,), discard_step_ids=(), reason="Invalid revision",
        ))
    assert plan.to_model_dict() == before


def test_planner_schema_does_not_cap_plan_size_or_dependency_count():
    properties = OpenAICompatibleSupervisorClient._goal_plan_patch_schema()["properties"]
    for name in ("add_stages", "replace_stages"):
        stages = properties[name]
        stage = stages["items"]["properties"]
        steps = stage["steps"]
        assert "maxItems" not in stages
        assert "maximum" not in stage["stage"]
        assert "maxItems" not in steps
        assert "maxItems" not in steps["items"]["properties"]["depends_on"]
    assert "maxItems" not in properties["discard_step_ids"]
