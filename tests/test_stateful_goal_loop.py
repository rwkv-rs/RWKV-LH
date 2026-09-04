from __future__ import annotations

import json
import hashlib
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.goal_loop_protocol import (
    GOAL_AUDIT_SCHEMA_VERSION,
    GOAL_AUDIT_INPUT_PROTOCOL,
    GOAL_PLAN_PATCH_SCHEMA_VERSION,
    LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION,
    LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION_V2,
    AuditedStep,
    GoalAuditDecision,
    GoalAuditVerdict,
    GoalPlanPatch,
    GoalPlanStep,
    GoalStageReview,
    GoalStageReviewVerdict,
    RollingGoalPlan,
    goal_audit_output_constraints,
    rolling_goal_plan,
    validate_audit_authority,
)
from rwkv_lh.exact_tool_selector.network_client import (
    NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NetworkExactToolSelectorClient,
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkExactToolSelection,
)
from rwkv_lh.exact_tool_selector.runtime_projection import (
    goal_frontier_selector_context,
)
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.model_session import ModelSession
from rwkv_lh.product_runtime import (
    build_product_controller,
    supervisor_mode_from_policy,
)
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    runtime_policy_document,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import GoalState, ModelLaneKind
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy


def test_role_pure_audit_v2_discloses_every_parser_field_invariant() -> None:
    assert GOAL_AUDIT_INPUT_PROTOCOL == "rwkv-lh.role-pure-goal-audit.v2"
    final_constraints = goal_audit_output_constraints(final_candidate=True)
    assert "at pre_final step_id is always the empty string" in final_constraints
    assert "at pre_final step_complete is always false" in final_constraints
    assert "ready_for_final requires an empty gaps array" in final_constraints
    active_constraints = goal_audit_output_constraints(final_candidate=False)
    assert "step_id must exactly equal active_step.step_id" in active_constraints
    assert any(
        "continue requires step_complete true" in item
        for item in active_constraints
    )


@dataclass
class _Response:
    content: str
    finish_reason: str = "stop"


class _QueueClient:
    def __init__(
        self,
        outputs: list[str],
        *,
        model_name: str = "test-rwkv-13.3b",
    ):
        self.outputs = list(outputs)
        self.model_name = model_name
        self.prompts: list[str] = []

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        self.prompts.append(prompt)
        content = self.outputs.pop(0)
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            pass
        else:
            if isinstance(value, dict) and set(value) == {"function", "params"}:
                content = ModelCommand(
                    str(value["function"]), dict(value["params"])
                ).canonical
        return _Response(content)


class _SelectorResponse:
    status_code = 200

    def __init__(self, value: dict) -> None:
        self.content = json.dumps(value).encode("utf-8")
        self.text = self.content.decode("utf-8")


class _SelectorHTTP:
    def __init__(self, settings: NetworkExactToolSelectorSettings, operations: list[str]):
        self.settings = settings
        self.operations = list(operations)
        self.payloads: list[dict] = []
        self.current_operation = ""

    def post(self, url: str, *, json: dict, timeout: tuple[float, float]):
        del timeout
        assert url.endswith("/selector-intent-v1/select")
        self.payloads.append(dict(json))
        menu_order_id = str(json.get("menu_order_id") or "")
        if menu_order_id == "canonical":
            self.current_operation = self.operations.pop(0)
        if not self.current_operation:
            raise AssertionError("non-canonical Selector lane ran before canonical")
        global_peak = self.current_operation
        index = len(self.payloads)
        logits = [0.0] * len(NETWORK_EXACT_TOOL_LABELS)
        logits[NETWORK_EXACT_TOOL_LABELS.index(global_peak)] = 10.0
        eligible_labels = tuple(str(item) for item in json["eligible_labels"])
        selected_index = max(
            (
                NETWORK_EXACT_TOOL_LABELS.index(label)
                for label in eligible_labels
            ),
            key=lambda item: (logits[item], -item),
        )
        operation = NETWORK_EXACT_TOOL_LABELS[selected_index]
        parent = dict(json.get("parent") or {})
        selection = NetworkExactToolSelection(
            selection_id=f"NSEL-{index:04d}",
            trace_id=str(json["trace_id"]),
            selected_operation=operation,
            logits=tuple(logits),
            temperature=0.25,
            input_digest=str(json["input_digest"]),
            menu_digest=str(json["menu_digest"]),
            selector_checkpoint_id=f"NSCP-{index:04d}",
            selector_state_ref=f"NSTATE-{index:04d}",
            selector_state_digest=hashlib.sha256(
                f"selector-state-{index}".encode()
            ).hexdigest(),
            selector_parent_state_digest=str(parent.get("state_digest") or ""),
            token_position=int(parent.get("token_position") or 0) + 20,
            model=self.settings.model,
            model_sha256=self.settings.model_sha256,
            head_sha256=self.settings.head_sha256,
            profile_id=self.settings.state_profile_id,
            profile_sha256=self.settings.state_profile_sha256,
            eligible_labels=eligible_labels,
        )
        return _SelectorResponse(
            {
                "schema_version": NETWORK_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }
        )


def _selector(operations: list[str]) -> NetworkExactToolSelectorClient:
    settings = NetworkExactToolSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="test-rwkv-2.9b",
        model_sha256="a" * 64,
        head_sha256="b" * 64,
        head_hash="c" * 64,
        feature_protocol="rwkv-lh.vllm-rwkv-final-hidden-mean.v1",
        state_profile_id="selector-zero-v1",
        state_profile_sha256="d" * 64,
        state_profile_manifest_sha256="e" * 64,
    )
    return NetworkExactToolSelectorClient(
        settings,
        session=_SelectorHTTP(settings, operations),
    )


class _StrongPlanner:
    provider_name = "test-strong-planner"
    model_name = "test-planner-model"

    def __init__(
        self,
        patch: GoalPlanPatch | tuple[GoalPlanPatch, ...] | None = None,
        *,
        stage_verdict: GoalStageReviewVerdict = GoalStageReviewVerdict.ADVANCE,
    ):
        self.patches = (
            ()
            if patch is None
            else patch
            if isinstance(patch, tuple)
            else (patch,)
        )
        self.requests = []
        self.stage_review_requests = []
        self.stage_verdict = stage_verdict

    def plan_goal_patch(self, request):
        self.requests.append(request)
        index = len(self.requests) - 1
        if index >= len(self.patches):
            raise AssertionError("test planner has no configured patch")
        return self.patches[index]

    def review_goal_stage(self, request):
        self.stage_review_requests.append(request)
        refs = tuple(
            dict.fromkeys(
                str(ref)
                for step in request.stage_steps
                for ref in step.get("accepted_evidence_refs") or ()
            )
        )
        return GoalStageReview(
            review_id=f"GSR-test-{len(self.stage_review_requests)}",
            stage=request.stage,
            verdict=self.stage_verdict,
            reviewed_step_ids=tuple(
                str(step.get("step_id") or "") for step in request.stage_steps
            ),
            evidence_refs=refs,
            gaps=(
                ()
                if self.stage_verdict is GoalStageReviewVerdict.ADVANCE
                else ("stage evidence is internally inconsistent",)
            ),
            reason=(
                "completed stage facts are coherent"
                if self.stage_verdict is GoalStageReviewVerdict.ADVANCE
                else "the stage requires a repair plan"
            ),
        )


class _ScriptedStrongPlanner(_StrongPlanner):
    def __init__(self, outcomes: tuple[GoalPlanPatch | Exception, ...]):
        super().__init__()
        self.outcomes = outcomes

    def plan_goal_patch(self, request):
        self.requests.append(request)
        index = len(self.requests) - 1
        if index >= len(self.outcomes):
            raise AssertionError("test planner has no configured outcome")
        outcome = self.outcomes[index]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class _ScriptedStagePlanner(_ScriptedStrongPlanner):
    def __init__(
        self,
        outcomes: tuple[GoalPlanPatch | Exception, ...],
        stage_verdicts: tuple[GoalStageReviewVerdict, ...],
    ) -> None:
        super().__init__(outcomes)
        self.stage_verdicts = stage_verdicts

    def review_goal_stage(self, request):
        index = len(self.stage_review_requests)
        if index >= len(self.stage_verdicts):
            raise AssertionError("test stage checker has no configured verdict")
        self.stage_verdict = self.stage_verdicts[index]
        return super().review_goal_stage(request)


def _strong_patch(state) -> GoalPlanPatch:
    return GoalPlanPatch(
        patch_id="GPP-initial",
        base_revision=0,
        add_steps=(GoalPlanStep(
            step_id="S1",
            objective="Create result.txt with verified content",
            success_evidence=("result.txt has a committed artifact revision",),
            write_roots=("result.txt",),
        ),),
        replace_steps=(),
        discard_step_ids=(),
        reason="Create and verify the requested result",
    )


def _strong_observe_patch(state, root: str = ".") -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-observe",
        base_revision=0,
        add_steps=(GoalPlanStep(
            step_id="S1",
            objective=f"Observe {root}",
            phase="observe",
            success_evidence=(f"{root} has successful observation evidence",),
            read_roots=(root,),
        ),),
        replace_steps=(),
        discard_step_ids=(),
        reason="Observe the requested workspace scope",
    )


def _strong_write_and_readback_patch(state) -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-write-and-readback",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Create result.txt",
                phase="mutate",
                success_evidence=("result.txt is written",),
                write_roots=("result.txt",),
            ),
            GoalPlanStep(
                step_id="S2",
                objective="Read back result.txt",
                phase="observe",
                stage=2,
                depends_on=("S1",),
                success_evidence=("result.txt is observed",),
                read_roots=("result.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Require mutation and direct readback evidence",
    )


def _strong_correction_patch(state) -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-correction",
        base_revision=1,
        add_steps=(),
        replace_steps=(GoalPlanStep(
            step_id="S1",
            objective="Inspect the workspace after the failed mutation",
            success_evidence=("the current workspace is observed",),
            read_roots=(".",),
        ),),
        discard_step_ids=(),
        reason="Replace the failed unfinished step with one bounded observation",
    )


def _strong_readback_correction_patch(state) -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-readback-correction",
        base_revision=1,
        add_steps=(),
        replace_steps=(GoalPlanStep(
            step_id="S1",
            objective="Read result.txt after the mutation",
            success_evidence=("the current result.txt content is observed",),
            read_roots=("result.txt",),
        ),),
        discard_step_ids=(),
        reason="Replace the unfinished mutation step with one bounded readback",
    )


def _strong_stage_readback_patch(state) -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-stage-readback",
        base_revision=1,
        add_steps=(GoalPlanStep(
            step_id="S2",
            objective="Read result.txt after the completed mutation stage",
            stage=2,
            depends_on=("S1",),
            success_evidence=("the current result.txt content is observed",),
            read_roots=("result.txt",),
        ),),
        replace_steps=(),
        discard_step_ids=(),
        reason="Add one new repair stage after the immutable completed step",
    )


def _strong_invalid_dependency_correction_patch(state) -> GoalPlanPatch:
    del state
    return GoalPlanPatch(
        patch_id="GPP-invalid-dependency-correction",
        base_revision=1,
        add_steps=(GoalPlanStep(
            step_id="S2",
            objective="Read result.txt after an unknown prerequisite",
            depends_on=("missing-prerequisite",),
            success_evidence=("the current result.txt content is observed",),
            read_roots=("result.txt",),
        ),),
        replace_steps=(),
        discard_step_ids=(),
        reason="Intentionally invalid controller-validation regression fixture",
    )


def _settings(*, progressive: bool = False) -> RuntimeSettings:
    return RuntimeSettings(
        base_url="http://127.0.0.1:1/v1",
        api_key="",
        model="test-rwkv-13.3b",
        model_sha256="f" * 64,
        max_model_len=16_384,
        context_safety_margin=8,
        bos_token_count=1,
        tool_disclosure_mode="progressive" if progressive else "full",
        state_transport="prompt_replay",
        state_profile_id="executor-zero-v1",
        state_profile_sha256="1" * 64,
    )


def _audit_call(
    verdict: str,
    *,
    step_id: str,
    step_complete: bool,
    evidence_refs: list[str],
    gaps: list[str],
    reason: str,
) -> dict:
    return {
        "function": "audit_decision",
        "params": {
            "verdict": verdict,
            "step_id": step_id,
            "step_complete": step_complete,
            "evidence_refs": evidence_refs,
            "gaps": gaps,
            "reason": reason,
        },
    }


def _native_tool_call(
    name: str,
    arguments: dict,
    *,
    stringify_arguments: bool = False,
) -> dict:
    return {
        "name": name,
        "arguments": (
            json.dumps(arguments, ensure_ascii=False, separators=(",", ":"))
            if stringify_arguments
            else arguments
        ),
    }


def _goal(tmp_path: Path) -> GoalState:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return GoalState.create(
        request="Inspect the project and report verified completion.",
        constraints=[],
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE),
            supervisor_mode="stateful_goal",
            execution_mode="bounded",
        ),
    )


def test_audit_accepts_exact_function_and_binds_identity_and_completion() -> None:
    raw = json.dumps(
        _audit_call(
            "continue",
            step_id="S1",
            step_complete=True,
            evidence_refs=["A00001"],
            gaps=[],
            reason="The committed action completes the active step",
        )
    )

    audit, bindings = GoalAuditDecision.parse_with_bindings(
        raw, audit_id="AUD-BOUND"
    )

    assert audit.schema_version == GOAL_AUDIT_SCHEMA_VERSION
    assert audit.audit_id == "AUD-BOUND"
    assert audit.completed_steps[0].step_id == "S1"
    assert bindings == (
        "audit_decision_function_envelope",
        "completed_steps_projection",
        "audit_id",
        "schema_version",
    )


def test_audit_rejects_extra_fields_and_wrong_operation() -> None:
    decision = {
        "verdict": "continue",
        "step_id": "S1",
        "step_complete": False,
        "evidence_refs": [],
        "gaps": [],
        "reason": "Continue",
    }
    with pytest.raises(ValueError, match="requires exactly"):
        GoalAuditDecision.parse_with_bindings(
            json.dumps({**decision, "commentary": "not allowed"}),
            audit_id="AUD-CONFLICT",
        )
    with pytest.raises(ValueError, match="must call"):
        GoalAuditDecision.parse_with_bindings(
            json.dumps({"function": "read_file", "params": decision}),
            audit_id="AUD-CONFLICT",
        )


def test_native_goal_patch_can_replace_open_steps_but_not_completed_steps(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STRONG-PLAN-PROJECTION")
    patch = _strong_patch(state)
    plan = RollingGoalPlan(goal_digest=state.goal.digest)
    plan.apply_goal_patch(patch)

    assert tuple(plan.steps) == ("S1",)
    assert plan.frontier[0].objective == "Create result.txt with verified content"
    assert plan.frontier[0].allowed_operations == ()
    assert plan.frontier[0].write_roots == ("result.txt",)
    assert plan.patch_ids == [patch.patch_id]

    replacement = _strong_correction_patch(state)
    plan.apply_goal_patch(replacement)
    assert plan.frontier[0].objective.startswith("Inspect the workspace")
    assert plan.step_revisions["S1"] == 2

    audit = GoalAuditDecision.from_dict(
        {
            "schema_version": GOAL_AUDIT_SCHEMA_VERSION,
            "audit_id": "AUD-1",
            "verdict": "continue",
            "step_id": "S1",
            "evidence_refs": ["A00001"],
            "gaps": [],
            "completed_steps": [
                {"step_id": "S1", "evidence_refs": ["A00001"]}
            ],
            "reason": "observed",
        }
    )
    plan.apply_audit(audit)
    assert plan.complete is True

    completed_replacement = GoalPlanPatch(
        patch_id="GPP-illegal-completed-replacement",
        base_revision=2,
        add_steps=(),
        replace_steps=replacement.replace_steps,
        discard_step_ids=(),
        reason="must be rejected",
    )
    with pytest.raises(ValueError, match="currently open"):
        plan.apply_goal_patch(completed_replacement)


def test_nested_plan_stages_are_peer_batches_with_a_real_barrier() -> None:
    patch = GoalPlanPatch.from_model_value(
        {
            "add_stages": [
                {
                    "stage": 1,
                    "steps": [
                        {
                                "step_id": "S1",
                                "objective": "Inspect left.json",
                                "phase": "observe",
                            "depends_on": [],
                            "success_evidence": ["left.json observed"],
                            "read_roots": ["left.json"],
                            "write_roots": [],
                            "constraints": [],
                        },
                        {
                                "step_id": "S2",
                                "objective": "Inspect right.json",
                                "phase": "observe",
                            "depends_on": [],
                            "success_evidence": ["right.json observed"],
                            "read_roots": ["right.json"],
                            "write_roots": [],
                            "constraints": [],
                        },
                    ],
                },
                {
                    "stage": 2,
                    "steps": [
                        {
                                "step_id": "S3",
                                "objective": "Report both observations",
                                "phase": "mutate",
                            "depends_on": ["S1"],
                            "success_evidence": ["combined report exists"],
                            "read_roots": [],
                            "write_roots": ["report.txt"],
                            "constraints": [],
                        }
                    ],
                },
            ],
            "replace_stages": [],
            "discard_step_ids": [],
            "reason": "Inspect independent inputs before combining them.",
        },
        patch_id="GPP-nested",
        base_revision=0,
    )
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(patch)

    assert [step.step_id for step in plan.frontier] == ["S1", "S2"]
    durable_patch = patch.to_dict()
    assert "add_stages" in durable_patch
    assert "add_steps" not in durable_patch
    assert GoalPlanPatch.from_dict(durable_patch) == patch
    assert plan.to_model_dict()["stages"][0]["stage"] == 1
    assert "stage" not in plan.to_model_dict()["stages"][0]["steps"][0]
    plan.apply_audit(
        GoalAuditDecision(
            audit_id="AUD-S1",
            verdict=GoalAuditVerdict.CONTINUE,
            step_id="S1",
            evidence_refs=("A1",),
            gaps=(),
            completed_steps=(AuditedStep("S1", ("A1",)),),
            reason="observed",
        )
    )
    assert [step.step_id for step in plan.frontier] == ["S2"]
    plan.apply_audit(
        GoalAuditDecision(
            audit_id="AUD-S2",
            verdict=GoalAuditVerdict.CONTINUE,
            step_id="S2",
            evidence_refs=("A2",),
            gaps=(),
            completed_steps=(AuditedStep("S2", ("A2",)),),
            reason="observed",
        )
    )
    assert [step.step_id for step in plan.frontier] == ["S3"]


def test_stage_repair_cannot_append_behind_an_unchanged_open_frontier() -> None:
    initial = GoalPlanPatch(
        patch_id="GPP-stage-repair-initial",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Inspect the verifier",
                stage=1,
                success_evidence=("verifier observed",),
                read_roots=("verify.py",),
            ),
            GoalPlanStep(
                step_id="S2",
                objective="Implement the feature",
                stage=2,
                depends_on=("S1",),
                success_evidence=("feature written",),
                write_roots=("feature.py",),
            ),
            GoalPlanStep(
                step_id="S3",
                objective="Run verification",
                stage=3,
                depends_on=("S2",),
                success_evidence=("verification passes",),
                read_roots=("verify.py",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect, implement, and verify",
    )
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(initial)
    plan.apply_audit(
        GoalAuditDecision(
            audit_id="AUD-stage-one",
            verdict=GoalAuditVerdict.CONTINUE,
            step_id="S1",
            evidence_refs=("A00001",),
            gaps=(),
            completed_steps=(AuditedStep("S1", ("A00001",)),),
            reason="verifier observed",
        )
    )
    review = GoalStageReview(
        review_id="GSR-stage-one-repair",
        stage=1,
        verdict=GoalStageReviewVerdict.REPAIR,
        reviewed_step_ids=("S1",),
        evidence_refs=("A00001",),
        gaps=("the verifier contract observation is incomplete",),
        reason="repair the evidence gap before implementation",
    )
    append_only = GoalPlanPatch(
        patch_id="GPP-stage-repair-appended-too-late",
        base_revision=1,
        add_steps=(GoalPlanStep(
            step_id="S4",
            objective="Repair the verifier mismatch later",
            stage=4,
            depends_on=("S3",),
            success_evidence=("mismatch repaired",),
            read_roots=("verify.py",),
        ),),
        replace_steps=(),
        discard_step_ids=(),
        reason="Append a repair after all existing work",
    )
    invalid_candidate = deepcopy(plan)
    invalid_candidate.apply_goal_patch(append_only)

    with pytest.raises(ValueError, match="appending only later work"):
        StatefulGoalLoopController._validate_stage_repair_patch(
            plan,
            invalid_candidate,
            append_only,
            review,
        )

    assert plan.patch_ids == [initial.patch_id]
    assert [step.step_id for step in plan.frontier] == ["S2"]

    replace_frontier = GoalPlanPatch(
        patch_id="GPP-stage-repair-frontier",
        base_revision=1,
        add_steps=(),
        replace_steps=(GoalPlanStep(
            step_id="S2",
            objective="Complete the verifier inspection, then implement the feature",
            stage=2,
            depends_on=("S1",),
            success_evidence=("contract observed and feature written",),
            read_roots=("verify.py",),
            write_roots=("feature.py",),
        ),),
        discard_step_ids=(),
        reason="Repair the gap in the next executable work",
    )
    valid_candidate = deepcopy(plan)
    valid_candidate.apply_goal_patch(replace_frontier)

    StatefulGoalLoopController._validate_stage_repair_patch(
        plan,
        valid_candidate,
        replace_frontier,
        review,
    )


def test_flat_v1_goal_plan_patch_remains_read_only_replay_compatible() -> None:
    patch = GoalPlanPatch.from_dict(
        {
            "schema_version": LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION,
            "patch_id": "GPP-legacy-flat",
            "base_revision": 0,
            "add_steps": [
                {
                    "step_id": "S1",
                    "objective": "Inspect legacy input",
                    "depends_on": [],
                    "success_evidence": ["legacy input observed"],
                    "read_roots": ["legacy.txt"],
                    "write_roots": [],
                    "constraints": [],
                }
            ],
            "replace_steps": [],
            "discard_step_ids": [],
            "reason": "legacy replay",
        }
    )

    assert patch.add_steps[0].stage == 1
    assert patch.to_dict()["schema_version"].endswith(".v3")
    assert patch.to_dict()["add_stages"][0]["steps"][0]["step_id"] == "S1"


def test_nested_v2_goal_plan_patch_infers_phase_only_for_replay() -> None:
    patch = GoalPlanPatch.from_dict(
        {
            "schema_version": LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION_V2,
            "patch_id": "GPP-legacy-v2",
            "base_revision": 0,
            "add_stages": [
                {
                    "stage": 1,
                    "steps": [
                        {
                            "step_id": "S1",
                            "objective": "Write legacy.txt",
                            "depends_on": [],
                            "success_evidence": ["legacy.txt is written"],
                            "read_roots": [],
                            "write_roots": ["legacy.txt"],
                            "constraints": [],
                        }
                    ],
                }
            ],
            "replace_stages": [],
            "discard_step_ids": [],
            "reason": "legacy nested replay",
        }
    )

    assert patch.add_steps[0].phase == "mutate"
    assert patch.to_dict()["schema_version"] == GOAL_PLAN_PATCH_SCHEMA_VERSION


def test_same_stage_conflicting_roots_are_rejected() -> None:
    plan = RollingGoalPlan(goal_digest="goal")
    patch = GoalPlanPatch(
        patch_id="GPP-conflict",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Write a configuration",
                success_evidence=("configuration written",),
                write_roots=("config",),
            ),
            GoalPlanStep(
                step_id="S2",
                objective="Read the same configuration tree",
                success_evidence=("configuration observed",),
                read_roots=("config/app.json",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="invalid parallel stage",
    )

    with pytest.raises(ValueError, match="conflicting read/write roots"):
        plan.apply_goal_patch(patch)


def test_audit_kernel_rejects_invented_evidence(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-AUTHORITY")
    plan = RollingGoalPlan(goal_digest=state.goal.digest)
    plan.apply_goal_patch(_strong_patch(state))
    audit = GoalAuditDecision.from_dict(
        {
            "schema_version": GOAL_AUDIT_SCHEMA_VERSION,
            "audit_id": "AUD-UNKNOWN",
            "verdict": "continue",
            "step_id": "S1",
            "evidence_refs": ["REV-INVENTED"],
            "gaps": [],
            "completed_steps": [],
            "reason": "invented evidence",
        }
    )

    with pytest.raises(ValueError, match="unknown evidence"):
        validate_audit_authority(state, plan, audit, final_candidate=False)


def test_selector_receives_active_strong_planner_frontier_without_goal_fallback(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "SELECTOR-FRONTIER")
    plan = RollingGoalPlan(goal_digest=state.goal.digest)
    plan.apply_goal_patch(_strong_patch(state))

    context = goal_frontier_selector_context(
        state,
        plan.frontier[0].to_dict(),
        eligible_labels=("write_file", "read_file"),
    )

    assert context.stage_objective.startswith("GoalFrontierStateV2: ")
    assert context.state_scope_id == "planner-step:S1:revision:1"
    assert context.action_ids == ()
    payload = json.loads(context.stage_objective.removeprefix("GoalFrontierStateV2: "))
    assert payload["active_step"] == {
        "step_id": "S1",
        "step_revision": 1,
        "stage": 1,
        "planned_phase": "mutate",
        "effective_phase": "mutate",
        "depends_on": [],
        "read_roots": [],
        "write_roots": ["result.txt"],
        "success_evidence": ["result.txt has a committed artifact revision"],
        "constraints": [],
    }
    assert payload["current_objective"] == (
        "Create result.txt with verified content"
    )
    assert payload["eligible_tools"] == [
        {
            "name": "write_file",
            "description": "Create or replace one complete local non-JSON UTF-8 file.",
        },
        {
            "name": "read_file",
            "description": "Read a bounded byte range from one local non-JSON UTF-8 file.",
        },
    ]
    assert payload["latest_action"] is None
    assert payload["latest_audit_feedback"] is None
    assert context.stage_role == "tool_intent"
    assert state.goal.request not in context.stage_objective
    assert state.goal.workspace_root not in context.stage_objective


def test_read_only_goal_step_menu_excludes_workspace_mutations(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "READ-ONLY-GOAL-MENU")
    session = ModelSession(_QueueClient([]), settings=_settings(progressive=True))
    model = LongHorizonModel(session, tool_selector=_selector([]))
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=1,
    )
    read_only = GoalPlanStep(
        step_id="READ",
        objective="Inspect result.txt without changing the workspace",
        success_evidence=("result.txt is observed",),
        read_roots=("result.txt",),
    )
    mutation = GoalPlanStep(
        step_id="WRITE",
        objective="Update result.txt",
        success_evidence=("result.txt is updated",),
        write_roots=("result.txt",),
    )
    check = GoalPlanStep(
        step_id="CHECK",
        objective="Run the read-only project verifier",
        phase="execute",
        success_evidence=("the verifier exits successfully",),
    )
    command_mutation = GoalPlanStep(
        step_id="RUN",
        objective="Run the project generator",
        phase="execute",
        success_evidence=("generated.txt is produced",),
        write_roots=("generated.txt",),
    )

    read_operations = controller._goal_step_operations(state, read_only)
    write_operations = controller._goal_step_operations(state, mutation)
    check_operations = controller._goal_step_operations(state, check)
    command_mutation_operations = controller._goal_step_operations(
        state, command_mutation
    )

    assert "read_file" in read_operations
    assert "web_search" not in read_operations
    assert "connector_lookup" not in read_operations
    assert "check_command" not in read_operations
    assert "run_command" not in read_operations
    assert "write_file" not in read_operations
    assert "remove_line" not in read_operations
    assert "delete_file" not in read_operations
    assert "write_file" in write_operations
    assert check_operations == ("check_command",)
    assert command_mutation_operations == ("run_command",)


def test_goal_selector_excludes_abstain_from_an_executable_frontier(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-SELECTOR-ABSTAIN")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )
                ),
                json.dumps(
                    {"function": "final_answer", "params": {"text": "done"}}
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the plan has accepted evidence",
                    )
                ),
            ]
        ),
        settings=_settings(progressive=True),
    )
    selector = _selector(["ABSTAIN", "final_answer"])
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=10,
    )

    result = controller.run(state.run_id)

    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "completed"
    assert len(result.state.actions) == 1
    assert result.state.protocol_rejections == 0
    assert len(selector._session.payloads) == 4
    assert all(
        "ABSTAIN" not in payload["eligible_labels"]
        for payload in selector._session.payloads
    )
    rejected = [
        event
        for event in events
        if event.event_type == "exact_tool_selection_rejected"
    ]
    assert rejected == []
    assert not any(
        event.event_type == "protocol_rejection_recorded" for event in events
    )


def test_audit_evidence_projection_keeps_root_facts_after_unrelated_actions(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "ROOT-EVIDENCE-WINDOW")
    workspace = Path(state.goal.workspace_root)
    (workspace / "pricing.py").write_text("PRICE = 1\n", encoding="utf-8")
    (workspace / "verify_project.py").write_text("print('ok')\n", encoding="utf-8")
    patch = GoalPlanPatch(
        patch_id="GPP-root-evidence",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="READ",
                objective="Read pricing.py and verify_project.py",
                success_evidence=("both files are observed",),
                read_roots=("pricing.py", "verify_project.py"),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect both files",
    )
    outputs = [
        json.dumps(
            {
                "function": "read_file",
                "params": {"path": "pricing.py"},
            }
        ),
        json.dumps(
            {
                "function": "read_file",
                "params": {"path": "verify_project.py"},
            }
        ),
        *(
            json.dumps(
                {
                    "function": "list_directory",
                    "params": {"path": ".", "recursive": False},
                }
            )
            for _ in range(10)
        ),
    ]
    session = ModelSession(_QueueClient(outputs), settings=_settings())
    model = LongHorizonModel(session)
    controller = LongHorizonController(store, model=model, harness=model.harness)
    controller._persist(
        state,
        "goal_plan_patch_committed",
        {
            "patch_id": patch.patch_id,
            "patch": patch.to_dict(),
            "plan_revision": 1,
            "request_digest": state.goal.digest,
            "supervisor": {"provider": "test", "model": "test-planner"},
        },
        subject_id=patch.patch_id,
    )
    action_ids = []
    for operation in ("read_file", "read_file", *("list_directory",) * 10):
        decision = model.next_command(
            state,
            controller._persist_callback,
            eligible_operations=(operation,),
        )
        action = controller._execute_decision(state, decision)
        action_ids.append(action.action_id)
        controller._persist(
            state,
            "goal_action_plan_step_assigned",
            {
                "action_id": action.action_id,
                "step_id": "READ",
                "step_revision": 1,
                "strong_planner_patch_ids": [patch.patch_id],
            },
            subject_id=action.action_id,
        )

    refs = StatefulGoalLoopController._step_audit_evidence_refs(
        state, "READ", 1
    )

    assert action_ids[0] in refs
    assert action_ids[1] in refs
    assert action_ids[-1] in refs
    assert len(refs) == 3


def test_audit_kernel_rejects_successful_but_wrong_scope_action(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-WRONG-SCOPE")
    patch = _strong_patch(state)
    controller = LongHorizonController(
        store,
        model=(
            model := LongHorizonModel(
                ModelSession(
                    _QueueClient(
                        [
                            json.dumps(
                                {
                                    "function": "write_file",
                                    "params": {
                                        "path": "unrelated.txt",
                                        "content": "irrelevant",
                                    },
                                }
                            )
                        ]
                    ),
                    settings=_settings(),
                )
            )
        ),
        harness=model.harness,
    )
    controller._persist(
        state,
        "goal_plan_patch_committed",
        {
            "patch_id": patch.patch_id,
            "patch": patch.to_dict(),
            "plan_revision": 1,
            "request_digest": state.goal.digest,
            "supervisor": {"provider": "test", "model": "test-planner"},
        },
        subject_id=patch.patch_id,
    )
    decision = model.next_command(
        state,
        controller._persist_callback,
        eligible_operations=("write_file",),
    )
    action = controller._execute_decision(state, decision)
    controller._persist(
        state,
        "goal_action_plan_step_assigned",
        {
            "action_id": action.action_id,
            "step_id": "S1",
            "step_revision": 1,
            "strong_planner_patch_ids": [patch.patch_id],
        },
        subject_id=action.action_id,
    )
    audit = GoalAuditDecision.from_dict(
        {
            "schema_version": GOAL_AUDIT_SCHEMA_VERSION,
            "audit_id": "AUD-WRONG-SCOPE",
            "verdict": "continue",
            "step_id": "S1",
            "evidence_refs": [action.action_id],
            "gaps": [],
            "completed_steps": [
                {"step_id": "S1", "evidence_refs": [action.action_id]}
            ],
            "reason": "successful but unrelated mutation",
        }
    )

    with pytest.raises(ValueError, match="write_roots"):
        validate_audit_authority(
            state,
            rolling_goal_plan(state),
            audit,
            final_candidate=False,
            active_step_id="S1",
            allowed_evidence_refs=(action.action_id,),
        )


def test_planner_separates_mutation_and_readback_into_stateful_steps(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-DURABLE")
    queue = _QueueClient(
        [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation succeeded",
                    )
                ),
                json.dumps(
                    {
                        "function": "read_file",
                        "params": {"path": "result.txt"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S2",
                        step_complete=True,
                        evidence_refs=["A00002"],
                        gaps=[],
                        reason="the readback succeeded",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Created and read back result.txt."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001", "A00002"],
                        gaps=[],
                        reason="the completed plan has mutation and readback evidence",
                    )
                ),
            ]
    )
    session = ModelSession(
        queue,
        settings=_settings(progressive=True),
    )
    selector = _selector(["write_file", "read_file", "final_answer"])
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_write_and_readback_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20,
    )

    result = controller.run(state.run_id)

    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "completed"
    assert result.final_output == "Created and read back result.txt."
    assert len(result.state.actions) == 2
    assert event_types.count("goal_audit_boundary_opened") == 3
    assert event_types.count("goal_audit_boundary_resolved") == 3
    assert event_types.count("goal_audit_recorded") == 3
    assert event_types.count("goal_audit_rejected") == 0
    assert event_types.count("goal_audit_accepted") == 3
    assert event_types.count("protocol_rejection_recorded") == 0
    assert event_types.count("goal_step_evidence_gap_recorded") == 0
    assert event_types.count("goal_stage_review_committed") == 2
    assert "run_yielded" not in event_types
    assert len(selector._session.payloads) == 7
    second_selector_step = json.loads(
        selector._session.payloads[3]["step"].removeprefix(
            "SelectorIntentPromptV1: "
        )
    )
    second_frontier = json.loads(
        second_selector_step["stage_objective"].removeprefix(
            "GoalFrontierStateV2: "
        )
    )
    assert second_frontier["active_step"]["planned_phase"] == "observe"
    assert second_frontier["active_step"]["effective_phase"] == "observe"
    assert second_frontier["latest_action"] is None
    executor_starts = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "action_session_started"
    ]
    assert executor_starts[1].payload["causal_fact_scope"] == (
        "controller_step_and_dependencies"
    )
    assert executor_starts[1].payload["causal_fact_action_ids"] == ["A00001"]
    assert rolling_goal_plan(result.state).complete is True


def test_identical_goal_action_failures_block_at_existing_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-IDENTICAL-FAILURE")
    (Path(state.goal.workspace_root) / "invalid.json").write_text(
        "{not-json\n",
        encoding="utf-8",
    )
    failed_command = json.dumps(
        {
            "function": "read_json",
            "params": {"path": "invalid.json"},
        }
    )
    session = ModelSession(
        _QueueClient([failed_command] * 5),
        settings=_settings(progressive=True),
    )
    selector = _selector(["read_json"] * 5)
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_observe_patch(state, "invalid.json")),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=30,
    )

    result = controller.run(state.run_id)

    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "blocked"
    assert len(result.state.actions) == 5
    assert len(selector._session.payloads) == 15
    assert sum(event.event_type == "goal_audit_boundary_opened" for event in events) == 4
    assert sum(event.event_type == "goal_audit_boundary_resolved" for event in events) == 4
    blocked = next(event for event in reversed(events) if event.event_type == "run_blocked")
    assert blocked.payload["reason"] == "identical_failure_budget_exhausted"
    assert controller._pending_audit_boundary(result.state) is None


def test_identical_goal_read_only_zero_progress_blocks_at_existing_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-IDENTICAL-SUCCESS")
    (Path(state.goal.workspace_root) / "other.txt").write_text(
        "unrelated\n", encoding="utf-8"
    )
    zero_progress_command = json.dumps(
        {
            "function": "read_file",
            "params": {"path": "other.txt"},
        }
    )
    session = ModelSession(
        _QueueClient([zero_progress_command] * 3),
        settings=_settings(progressive=True),
    )
    selector = _selector(["read_file"] * 3)
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_observe_patch(state, "missing.txt")),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20,
    )

    result = controller.run(state.run_id)

    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "blocked"
    assert len(result.state.actions) == 3
    assert len(selector._session.payloads) == 9
    assert sum(event.event_type == "goal_audit_boundary_opened" for event in events) == 2
    assert sum(event.event_type == "goal_audit_boundary_resolved" for event in events) == 2
    blocked = next(event for event in reversed(events) if event.event_type == "run_blocked")
    assert blocked.payload["reason"] == "identical_success_budget_exhausted"
    assert controller._pending_audit_boundary(result.state) is None


def test_invalid_pre_final_audit_rejects_candidate_and_requires_new_audited_final(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PRE-FINAL-PROTOCOL-INVALID")
    queue = _QueueClient(
        [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "First unaudited candidate."},
                    }
                ),
                    "{}",
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Second audited candidate."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="all plan steps have accepted evidence",
                    )
                ),
            ]
    )
    session = ModelSession(
        queue,
        settings=_settings(progressive=True),
    )
    selector = _selector(["write_file", "final_answer", "final_answer"])
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20,
    )

    result = controller.run(state.run_id)

    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "completed"
    assert result.final_output == "Second audited candidate."
    assert event_types.count("goal_final_rejected") == 1
    assert event_types.count("run_completed") == 1
    assert "run_yielded" not in event_types
    rejected = next(
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type == "goal_final_rejected"
    )
    assert rejected.payload["verdict"] == "protocol_invalid"
    assert rejected.payload["step_completed"] is False
    assert rejected.payload["kernel_validated"] is False
    failed_resolution = next(
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_audit_boundary_resolved"
        and result.state.causal_records[event_id].payload["verdict"]
        == "protocol_invalid"
    )
    assert failed_resolution.payload["boundary_kind"] == "pre_final"
    assert failed_resolution.subject_id == rejected.payload["audit_boundary_id"]
    assert result.state.causal_records[result.state.causal_order[-1]].event_type == (
        "run_completed"
    )


def test_rwkv_audit_uses_clean_role_state_and_never_contaminates_executor(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-MODEL")
    patch = _strong_patch(state)
    audit_output = _audit_call(
        "continue",
        step_id="S1",
        step_complete=True,
        evidence_refs=["A00001"],
        gaps=[],
        reason="evidence is present",
    )
    rejected_audit_output = {
        "function": "audit_decision",
        "params": {
            "audit_id": "MODEL-MUST-NOT-BIND",
            "verdict": "ready_for_final",
            "step_id": "S1",
            "step_complete": True,
            "evidence_refs": ["A00001"],
            "gaps": [],
            "reason": "premature final",
            "repair": [],
        },
    }
    audits: list[dict] = []
    session = ModelSession(
        _QueueClient(
            [json.dumps(
                {
                    "function": "write_file",
                    "params": {"path": "result.txt", "content": "verified"},
                }
            )]
        ),
        settings=_settings(),
        audit_hook=audits.append,
    )
    auditor_settings = RuntimeSettings(
        **{**_settings().__dict__, "model": "test-rwkv-7.2b-auditor"}
    )
    auditor_session = ModelSession(
        _QueueClient(
            [json.dumps(audit_output)],
            model_name="test-rwkv-7.2b-auditor",
        ),
        settings=auditor_settings,
        audit_hook=audits.append,
    )
    model = LongHorizonModel(session, auditor_session=auditor_session)
    controller = LongHorizonController(store, model=model, harness=model.harness)

    controller._persist(
        state,
        "goal_plan_patch_committed",
        {
            "patch_id": patch.patch_id,
            "patch": patch.to_dict(),
            "plan_revision": 1,
            "request_digest": state.goal.digest,
            "supervisor": {"provider": "test", "model": "test-planner"},
            "planner_can_accept": False,
            "supervisor_action_executed": False,
            "rwkv_action_authority": True,
        },
        subject_id=patch.patch_id,
    )
    action_decision = model.next_command(
        state,
        controller._persist_callback,
        eligible_operations=("write_file",),
    )
    action = controller._execute_decision(state, action_decision)
    controller._persist(
        state,
        "goal_action_plan_step_assigned",
        {
            "action_id": action.action_id,
            "step_id": "S1",
            "step_revision": 1,
            "strong_planner_patch_ids": [patch.patch_id],
            "assignment_source": "test_committed_frontier",
            "completion_authority": False,
        },
        subject_id=action.action_id,
    )
    decision = model.audit_goal_boundary(
        state,
        controller._persist_callback,
        boundary="observation_complete",
        event=controller._action_observation_event(state, action),
        active_step_id="S1",
        relevant_evidence_refs=(action.action_id,),
    )

    assert decision.audit_id.startswith("AUD-")
    assert rolling_goal_plan(state).complete is True
    assert state.model_states[state.lane_head("executor")].lane_kind is ModelLaneKind.ACTION
    assert any(
        checkpoint.lane_kind is ModelLaneKind.STEP_AUDIT
        and checkpoint.model == "test-rwkv-7.2b-auditor"
        for checkpoint in state.model_states.values()
    )
    assert any(
        item["type"] == "model_session_bootstrapped"
        and item["lane_kind"] == "auditor_step"
        for item in audits
    )
    assert not any(item["type"] == "model_session_forked" for item in audits)
    assert sum(item["type"].endswith("candidate_committed") for item in audits) == 1
    event_types = [
        state.causal_records[event_id].event_type for event_id in state.causal_order
    ]
    assert event_types.count("goal_audit_recorded") == 1
    assert event_types.count("goal_audit_rejected") == 0
    assert not any(
        item.event_type == "goal_audit_retry_feedback"
        for item in state.model_events.values()
    )
    executor_transcript = state.model_states[state.lane_head("executor")].transcript
    assert "MODEL-MUST-NOT-BIND" not in executor_transcript
    audit_checkpoint = next(
        checkpoint
        for checkpoint in state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.STEP_AUDIT
    )
    audit_prompt = audit_checkpoint.transcript.split("\n\nUser: ", 1)[1].split(
        "\n\n**Tool Call:**", 1
    )[0]
    audit_payload = json.loads(
        audit_prompt.removeprefix("AuditorStepPromptV1: ")
    )
    assert list(audit_payload)[-1] == "current_question"
    assert state.goal.request not in audit_checkpoint.transcript
    assert audit_payload["active_step"]["step_id"] == "S1"
    assert "kernel_bound_fields" not in audit_checkpoint.transcript
    assert "audit_boundary_id" not in audit_payload
    assert audit_payload["evidence_records"][0]["action"]["action_id"] == "A00001"
    assert audit_payload["evidence_records"][0]["action"]["status"] == "succeeded"
    audit_arguments = audit_payload["evidence_records"][0]["action"]["arguments"]
    assert audit_arguments["path"] == "result.txt"
    assert audit_arguments["content"] == "verified"
    assert any(
        state.causal_records[event_id].event_type == "goal_audit_accepted"
        for event_id in state.causal_order
    )


def test_product_stateful_goal_fails_closed_without_selector_then_builds_with_it(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PRODUCT-STATEFUL")
    monkeypatch.setattr(
        "rwkv_lh.product_runtime._product_tool_selector",
        lambda: None,
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.create_model_session",
        lambda settings, audit_hook=None: ModelSession(
            _QueueClient([]), settings=settings, audit_hook=audit_hook
        ),
    )
    planner = _StrongPlanner()
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.OpenAIGoalSupervisorClient",
        lambda audit_hook=None: planner,
    )
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.supervisor_policy_from_env",
        lambda mode: SupervisorPolicy(mode=mode),
    )

    with pytest.raises(ValueError, match="requires complete RWKV_LH_SELECTOR"):
        build_product_controller(store, state, state_root=tmp_path / "runtime")

    monkeypatch.setattr(
        "rwkv_lh.product_runtime._product_tool_selector",
        lambda: _selector([]),
    )
    controller = build_product_controller(store, state, state_root=tmp_path / "runtime")

    assert isinstance(controller, StatefulGoalLoopController)
    assert controller.supervisor is planner
    assert controller.atom_worker_pool is None
    role_sessions = (
        controller.model.session,
        controller.model.step_auditor_session,
        controller.model.finalizer_session,
        controller.model.final_auditor_session,
    )
    assert len({id(item) for item in role_sessions}) == 4
    assert supervisor_mode_from_policy(state.goal.runtime_policy) == "stateful_goal"
    with pytest.raises(ValueError, match="only the latest stateful_goal"):
        supervisor_mode_from_policy({"supervisor": {"mode": "contract_graph"}})


def test_stateful_goal_loop_completes_only_after_rwkv_audit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-END-TO-END")
    first_audit = _audit_call(
        "continue",
        step_id="S1",
        step_complete=True,
        evidence_refs=["A00001"],
        gaps=[],
        reason="the mutation action succeeded",
    )
    final_audit = _audit_call(
        "ready_for_final",
        step_id="",
        step_complete=False,
        evidence_refs=["A00001"],
        gaps=[],
        reason="all plan steps have committed evidence",
    )
    queue = _QueueClient(
        [
                json.dumps(
                    _native_tool_call(
                        "write_file",
                        {"path": "result.txt", "content": "verified"},
                        stringify_arguments=True,
                    )
                ),
                json.dumps(
                    _native_tool_call(
                        "audit_decision",
                        first_audit["params"],
                    )
                ),
                json.dumps(
                    _native_tool_call(
                        "final_answer",
                        {"text": "Created and verified result.txt."},
                        stringify_arguments=True,
                    )
                ),
                json.dumps(
                    _native_tool_call(
                        "audit_decision",
                        final_audit["params"],
                    )
                ),
            ]
    )
    session = ModelSession(
        queue,
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["write_file", "final_answer"]),
    )
    planner = _StrongPlanner(_strong_patch(state))
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=10,
    )

    result = controller.run(state.run_id)

    assert result.state.status.value == "completed"
    assert result.final_output == "Created and verified result.txt."
    assert len(queue.prompts) == 4
    assert all(
        prompt.endswith("\n\n**Tool Call:**\n\n```json\n")
        for prompt in queue.prompts
    )
    assert all("Assistant: ```json" not in prompt for prompt in queue.prompts)
    assert all(
        "\n\nAssistant:\n\n**Tool Call:**" not in prompt
        for prompt in queue.prompts
    )
    assert (Path(state.goal.workspace_root) / "result.txt").read_text() == "verified"
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("goal_audit_accepted") == 2
    assert event_types.count("goal_finalizer_session_started") == 1
    assert event_types.count("goal_plan_patch_committed") == 1
    assert event_types.count("goal_stage_review_committed") == 1
    accepted_calls = [
        result.state.causal_records[event_id].payload
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type == "model_call_accepted"
    ]
    assert len(accepted_calls) == 2
    for payload in accepted_calls:
        normalization = payload["model_output_normalization"]
        input_arguments = normalization["input_payload"]["arguments"]
        assert isinstance(input_arguments, str)
        assert normalization["normalized_payload"]["params"] == json.loads(
            input_arguments
        )
        assert normalization["controller_semantic_fields_generated"] is False
    audit_records = [
        result.state.causal_records[event_id].payload
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type == "goal_audit_recorded"
    ]
    assert len(audit_records) == 2
    assert all(
        item["model_output_normalization"]["normalized_payload"]["function"]
        == "audit_decision"
        for item in audit_records
    )
    assert planner.requests and planner.requests[0].plan_revision == 0
    assert len(planner.stage_review_requests) == 1
    stage_fact = planner.stage_review_requests[0].recent_action_facts[0]
    assert stage_fact["operation"] == "write_file"
    assert '"success":true' in stage_fact["result_projection"]
    assert event_types[-1] == "run_completed"
    finalizer_index = event_types.index("goal_finalizer_session_started")
    final_auditor_index = next(
        index
        for index, event_id in enumerate(result.state.causal_order)
        if result.state.causal_records[event_id].event_type
        == "goal_auditor_session_started"
        and result.state.causal_records[event_id].payload["auditor_role"]
        == "auditor_final"
    )
    assert finalizer_index < final_auditor_index < len(event_types) - 1
    finalizer_event = next(
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_finalizer_session_started"
    )
    assert finalizer_event.payload["completion_authority"] is False
    assert finalizer_event.payload["executor_state_inherited"] is False
    assert finalizer_event.payload["selector_state_inherited"] is False
    assert len(finalizer_event.payload["protocol_sha256"]) == 64
    final_decision = result.state.decisions[result.state.final_decision_id]
    assert final_decision.lane_id.startswith("LANE:FINALIZER:")
    assert final_decision.model == model.finalizer_session.model_name
    assert result.state.model_states[
        result.state.lane_head("executor")
    ].lane_kind is ModelLaneKind.ACTION
    assert result.state.model_states[
        result.state.lane_head("finalizer_answer")
    ].lane_kind is ModelLaneKind.FINALIZER
    auditor_starts = [
        result.state.causal_records[event_id].payload
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_auditor_session_started"
    ]
    assert {item["auditor_role"] for item in auditor_starts} == {
        "auditor_step",
        "auditor_final",
    }
    assert all(len(item["protocol_sha256"]) == 64 for item in auditor_starts)
    assert all(item["executor_state_inherited"] is False for item in auditor_starts)
    selector_payloads = model.tool_selector._session.payloads
    assert selector_payloads[0]["parent"] is None
    assert selector_payloads[3]["parent"] is None
    selector_checkpoints = [
        checkpoint
        for checkpoint in result.state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.SELECTOR
    ]
    assert {
        (checkpoint.native_state_metadata or {}).get("selector_state_scope_id")
        for checkpoint in selector_checkpoints
    } == {"planner-step:S1:revision:1", "goal-final-candidate"}
    completed = result.state.causal_records[result.state.causal_order[-1]].payload
    assert completed["audit_id"].startswith("AUD-")
    assert completed["rwkv_audit_accepted"] is True


def test_stateful_executor_protocol_retry_reuses_consumed_selection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-SAME-TOOL-RETRY")
    queue = _QueueClient(
        [
            json.dumps(
                _native_tool_call(
                    "write_file",
                    {"path": "result.txt"},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "write_file",
                    {"path": "result.txt", "content": "verified"},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "audit_decision",
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )["params"],
                )
            ),
            json.dumps(
                _native_tool_call(
                    "final_answer",
                    {"text": "Created and verified result.txt."},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "audit_decision",
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="all plan steps have committed evidence",
                    )["params"],
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    selector = _selector(["write_file", "final_answer"])
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=12,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert len(result.state.actions) == 1
    assert len(selector._session.payloads) == 4
    assert selector._session.payloads[0]["parent"] is None
    assert selector._session.payloads[3]["parent"] is None
    rejection = next(
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "protocol_rejection_recorded"
    )
    assert rejection.payload["protocol_scope"] == "action"
    assert rejection.payload["selected_operation"] == "write_file"
    assert rejection.payload["schema_already_disclosed"] is True
    retry_events = [
        event
        for event in result.state.model_events.values()
        if event.event_type == "protocol_rejection"
    ]
    assert len(retry_events) == 1
    assert retry_events[0].payload["selection_id"] == rejection.payload["selection_id"]
    accepted_write = next(
        record
        for record in result.state.decisions.values()
        if record.accepted and record.selected_operation == "write_file"
    )
    assert accepted_write.tool_selection_id == rejection.payload["selection_id"]
    assert accepted_write.tool_selection_binding_kind == "non_authoritative_lineage"
    assert len(queue.prompts) == 5


def test_stateful_executor_reselects_after_one_failed_same_tool_retry(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-BOUNDED-TOOL-RETRY")
    queue = _QueueClient(
        [
            json.dumps(
                _native_tool_call(
                    "write_file",
                    {"path": "result.txt"},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "move_file",
                    {"source": "old.txt", "destination": "result.txt"},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "write_file",
                    {"path": "result.txt", "content": "verified"},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "audit_decision",
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )["params"],
                )
            ),
            json.dumps(
                _native_tool_call(
                    "final_answer",
                    {"text": "Created and verified result.txt."},
                    stringify_arguments=True,
                )
            ),
            json.dumps(
                _native_tool_call(
                    "audit_decision",
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="all plan steps have committed evidence",
                    )["params"],
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    selector = _selector(["write_file", "write_file", "final_answer"])
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=16,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert result.state.protocol_rejections == 2
    assert len(selector._session.payloads) == 7
    second_selection = json.loads(
        selector._session.payloads[3]["step"].removeprefix(
            "SelectorIntentPromptV1: "
        )
    )
    assert second_selection["progress"]["protocol_rejection_count"] == 2
    retry_events = [
        event
        for event in result.state.model_events.values()
        if event.event_type == "protocol_rejection"
    ]
    assert len(retry_events) == 1
    assert queue.prompts[2].count("ExecutorArgsPromptV1: ") == 1
    assert "protocol_rejection" not in queue.prompts[2]
    executor_starts = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "action_session_started"
    ]
    assert len(executor_starts) == 2
    assert executor_starts[1].payload["session_scope"] == "one_selected_action"
    assert executor_starts[1].payload["executor_state_inherited"] is False


def test_stateful_protocol_budget_blocks_across_controller_slices(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-DURABLE-PROTOCOL-BUDGET")
    queue = _QueueClient(["{}"] * 13)
    session = ModelSession(queue, settings=_settings(progressive=True))
    selector = _selector(["write_file"] * 7)
    model = LongHorizonModel(session, tool_selector=selector)
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=1,
    )

    result = controller.run(state.run_id)
    for _ in range(11):
        result = controller.resume(state.run_id)

    assert result.state.status.value == "blocked"
    assert result.state.protocol_rejections == 12
    assert len(queue.prompts) == 12
    terminal = result.state.causal_records[result.state.causal_order[-1]]
    assert terminal.event_type == "run_blocked"
    assert terminal.payload["reason"] == "protocol_rejection_budget_exhausted"

    resumed = controller.resume(state.run_id)

    assert resumed.state.status.value == "interrupted"
    assert len(queue.prompts) == 13
    latest_start = next(
        resumed.state.causal_records[event_id]
        for event_id in reversed(resumed.state.causal_order)
        if resumed.state.causal_records[event_id].event_type == "run_started"
    )
    assert latest_start.payload["protocol_rejection_budget_reset"] is True


def test_final_auditor_repair_returns_to_goal_loop_before_completion(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "FINAL-AUDIT-REPAIR")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Unsupported first candidate."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=["candidate does not report the committed artifact"],
                        reason="the final candidate is not evidence-complete",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Created and verified result.txt."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the revised candidate covers committed evidence",
                    )
                ),
            ]
        ),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["write_file", "final_answer", "final_answer"]),
    )
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=12,
    )

    result = controller.run(state.run_id)

    assert result.state.status.value == "completed"
    assert result.final_output == "Created and verified result.txt."
    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    event_types = [item.event_type for item in events]
    assert event_types.count("goal_finalizer_session_started") == 2
    assert event_types.count("goal_final_rejected") == 1
    rejected_index = event_types.index("goal_final_rejected")
    completed_index = event_types.index("run_completed")
    assert rejected_index < completed_index
    rejected = events[rejected_index]
    assert rejected.payload["verdict"] == "repair"
    assert rejected.payload["controller_rewritten"] is False
    assert all(
        item.event_type != "run_completed" for item in events[:rejected_index]
    )


def test_planner_semantic_repair_reaches_stage_checker(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PLANNER-SEMANTIC-REPAIR")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation stage completed",
                    )
                ),
                json.dumps(
                    {
                        "function": "read_file",
                        "params": {"path": "result.txt"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S2",
                        step_complete=True,
                        evidence_refs=["A00002"],
                        gaps=[],
                        reason="the current result.txt bytes were observed",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Created and read back result.txt."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00001", "A00002"],
                        gaps=[],
                        reason="the repaired plan and final candidate are evidence-bound",
                    )
                ),
            ]
        ),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["write_file", "read_file", "final_answer"]),
    )
    planner = _ScriptedStagePlanner(
        (
            _strong_patch(state),
            _strong_invalid_dependency_correction_patch(state),
            _strong_stage_readback_patch(state),
        ),
        (
            GoalStageReviewVerdict.REPAIR,
            GoalStageReviewVerdict.ADVANCE,
        ),
    )
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20,
    )

    result = controller.run(state.run_id)

    assert result.state.status.value == "completed"
    assert [request.plan_revision for request in planner.requests] == [0, 1, 1]
    assert planner.requests[1].local_validation_repair is None
    repair = planner.requests[2].local_validation_repair
    assert repair is not None
    assert repair["attempt"] == 1
    assert "dependent on discarded or unknown steps" in repair["error"]
    assert repair["rejected_patch"]["patch_id"] == (
        "GPP-invalid-dependency-correction"
    )
    assert planner.requests[1].latest_audit is None
    assert planner.requests[1].latest_stage_review is not None
    assert planner.requests[1].latest_stage_review["verdict"] == "repair"
    assert len(planner.stage_review_requests) == 2
    assert [
        fact["action_id"]
        for fact in planner.stage_review_requests[0].recent_action_facts
    ] == ["A00001"]
    assert [
        fact["action_id"]
        for fact in planner.stage_review_requests[1].recent_action_facts
    ] == ["A00002"]
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("strong_planner_patch_rejected") == 1
    assert event_types.count("strong_planner_call_failed") == 0
    assert event_types.count("goal_plan_patch_committed") == 2
    assert event_types.count("goal_stage_review_committed") == 2
    assert event_types.index("goal_stage_review_committed") < event_types.index(
        "strong_planner_patch_rejected"
    )


def test_planner_semantic_repair_is_bounded_and_not_reported_unavailable(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PLANNER-SEMANTIC-REPAIR-EXHAUSTED")
    session = ModelSession(
        _QueueClient([]),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(session, tool_selector=_selector([]))
    planner = _ScriptedStrongPlanner(
        (
            ValueError("Goal PlanPatch cannot replace and discard the same step"),
            ValueError("Goal PlanPatch cannot reuse an existing step id"),
        )
    )
    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=4,
    ).run(state.run_id)

    assert result.state.status.value == "interrupted"
    assert len(planner.requests) == 2
    assert planner.requests[1].local_validation_repair is not None
    rejected = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "strong_planner_patch_rejected"
    ]
    assert len(rejected) == 2
    assert rejected[0].payload["repair_scheduled"] is True
    assert rejected[1].payload["repair_scheduled"] is False
    assert not any(
        result.state.causal_records[event_id].event_type
        == "strong_planner_call_failed"
        for event_id in result.state.causal_order
    )
    terminal = result.state.causal_records[result.state.causal_order[-1]]
    assert terminal.payload["reason"] == "strong_planner_semantic_invalid"


def test_goal_planner_zero_semantic_repairs_never_makes_a_second_call(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PLANNER-ZERO-SEMANTIC-REPAIR")
    session = ModelSession(
        _QueueClient([]),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(session, tool_selector=_selector([]))
    planner = _ScriptedStrongPlanner(
        (ValueError("plan root must be workspace-relative"),)
    )
    planner.semantic_repair_attempts = 0

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=4,
    ).run(state.run_id)

    assert result.state.status.value == "interrupted"
    assert len(planner.requests) == 1
    rejected = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "strong_planner_patch_rejected"
    ]
    assert len(rejected) == 1
    assert rejected[0].payload["repair_scheduled"] is False
    assert rejected[0].payload["configured_semantic_repair_attempts"] == 0
    assert result.state.causal_records[result.state.causal_order[-1]].payload[
        "reason"
    ] == "strong_planner_semantic_invalid"


def test_rwkv_repair_audit_continues_same_step_without_replanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-STRONG-REPLAN")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": ".", "content": "cannot replace a directory"},
                    }
                ),
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00002"],
                        gaps=[],
                        reason="the requested artifact now exists",
                    )
                ),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Recovered and created result.txt."},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "ready_for_final",
                        step_id="",
                        step_complete=False,
                        evidence_refs=["A00002"],
                        gaps=[],
                        reason="the completed plan has accepted mutation evidence",
                    )
                ),
            ]
        ),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["write_file", "write_file", "final_answer"]),
    )
    planner = _StrongPlanner(_strong_patch(state))
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=12,
    )

    result = controller.run(state.run_id)

    assert result.state.status.value == "completed"
    assert result.final_output == "Recovered and created result.txt."
    assert [request.plan_revision for request in planner.requests] == [0]
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("goal_plan_patch_committed") == 1
    assert event_types.count("goal_audit_accepted") == 2
    assert event_types.count("goal_step_evidence_gap_recorded") == 1
    assert event_types.count("goal_stage_review_committed") == 1
    assert event_types.count("rwkv_contract_review_projected") == 0
    assert event_types.count("contract_graph_review_committed") == 0
    assert len(result.state.actions) == 2
    assert rolling_goal_plan(result.state).step_revisions["S1"] == 1
    assert rolling_goal_plan(result.state).complete is True
    eligible_labels = [
        payload["eligible_labels"] for payload in model.tool_selector._session.payloads
    ]
    assert "final_answer" not in eligible_labels[0]
    assert "final_answer" not in eligible_labels[3]
    assert eligible_labels[6] == ["final_answer"]
    selector_payloads = model.tool_selector._session.payloads
    assert selector_payloads[0]["parent"] is None
    assert selector_payloads[3]["parent"] is not None
    second_step = json.loads(
        selector_payloads[3]["step"].removeprefix("SelectorIntentPromptV1: ")
    )
    frontier_state = json.loads(
        second_step["stage_objective"].removeprefix("GoalFrontierStateV2: ")
    )
    assert frontier_state["progress"] == {
        "completed_step_ids": [],
        "completed_stage_count": 0,
        "current_step_action_count": 1,
    }
    assert frontier_state["latest_action"]["operation"] == "write_file"
    assert frontier_state["latest_action"]["status"] == "failed"
    assert frontier_state["latest_action"]["arguments"]["path"] == "."
    assert frontier_state["latest_audit_feedback"] == {
        "status": "mechanically_incomplete",
        "gaps": [
            "missing successful mutation evidence for write_root 'result.txt'"
        ],
        "successful_action_ids": [],
        "missing_read_roots": [],
        "missing_write_roots": ["result.txt"],
    }
    assert any(
        item["name"] == "write_file" and item["description"]
        for item in frontier_state["eligible_tools"]
    )
    second_executor_prompt = session.client.prompts[1]
    assert '"missing_write_roots":["result.txt"]' in second_executor_prompt
    assert '"completion_preconditions_satisfied":false' in second_executor_prompt
    assert '"completion_authority":false' in second_executor_prompt


def test_stage_repair_survives_planner_outage_and_resumes_before_final(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STAGE-REPAIR-RESUME")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(
                    _audit_call(
                        "continue",
                        step_id="S1",
                        step_complete=True,
                        evidence_refs=["A00001"],
                        gaps=[],
                        reason="the mutation action succeeded",
                    )
                ),
            ]
        ),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["write_file"]),
    )
    first_planner = _StrongPlanner(
        _strong_patch(state),
        stage_verdict=GoalStageReviewVerdict.REPAIR,
    )
    first = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=first_planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=10,
    ).run(state.run_id)

    assert first.state.status.value == "interrupted"
    assert len(first_planner.stage_review_requests) == 1
    assert len(first_planner.requests) == 2
    repair_review_id = next(
        str(first.state.causal_records[event_id].payload["review"]["review_id"])
        for event_id in first.state.causal_order
        if first.state.causal_records[event_id].event_type
        == "goal_stage_review_committed"
    )

    repair_patch = GoalPlanPatch(
        patch_id="GPP-stage-repair",
        base_revision=1,
        add_steps=(
            GoalPlanStep(
                step_id="S2",
                objective="Inspect the repaired workspace",
                stage=2,
                depends_on=("S1",),
                success_evidence=("workspace is observed after repair",),
                read_roots=(".",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Add the smallest later repair stage",
    )
    resumed_planner = _StrongPlanner(repair_patch)
    resumed = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=resumed_planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=1,
    ).run(state.run_id)

    assert len(resumed_planner.requests) == 1
    assert resumed_planner.requests[0].latest_stage_review["review_id"] == repair_review_id
    committed = [
        resumed.state.causal_records[event_id]
        for event_id in resumed.state.causal_order
        if resumed.state.causal_records[event_id].event_type
        == "goal_plan_patch_committed"
    ][-1]
    assert committed.payload["source_stage_review_id"] == repair_review_id
    assert rolling_goal_plan(resumed.state).current_stage == 2
