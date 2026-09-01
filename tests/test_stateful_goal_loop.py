from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.goal_loop_protocol import (
    GOAL_AUDIT_SCHEMA_VERSION,
    LEGACY_GOAL_PLAN_PATCH_SCHEMA_VERSION,
    AuditedStep,
    GoalAuditDecision,
    GoalAuditVerdict,
    GoalPlanPatch,
    GoalPlanStep,
    GoalStageReview,
    GoalStageReviewVerdict,
    RollingGoalPlan,
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

    def text_completion(self, prompt: str, max_tokens: int = 768, stop=None):
        return _Response(self.outputs.pop(0))


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

    def post(self, url: str, *, json: dict, timeout: tuple[float, float]):
        del timeout
        assert url.endswith("/v8/select")
        self.payloads.append(dict(json))
        operation = self.operations.pop(0)
        index = len(self.payloads)
        logits = [0.0] * len(NETWORK_EXACT_TOOL_LABELS)
        logits[NETWORK_EXACT_TOOL_LABELS.index(operation)] = 10.0
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
            eligible_labels=tuple(str(item) for item in json["eligible_labels"]),
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
                            "depends_on": [],
                            "success_evidence": ["left.json observed"],
                            "read_roots": ["left.json"],
                            "write_roots": [],
                            "constraints": [],
                        },
                        {
                            "step_id": "S2",
                            "objective": "Inspect right.json",
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
    assert patch.to_dict()["schema_version"].endswith(".v2")
    assert patch.to_dict()["add_stages"][0]["steps"][0]["step_id"] == "S1"


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

    context = goal_frontier_selector_context(state, plan.frontier[0].to_dict())

    assert context.stage_objective == "Create result.txt with verified content"
    assert context.stage_role == "tool_intent"
    assert state.goal.request not in context.stage_objective


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


def test_invalid_audit_retries_same_durable_boundary_without_new_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-DURABLE")
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                *(["{}"] * 6),
            ]
        ),
        settings=_settings(progressive=True),
    )
    selector = _selector(["write_file"])
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
    controller._MAX_PROTOCOL_REJECTIONS = 2

    result = controller.run(state.run_id)

    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert len(result.state.actions) == 1
    assert event_types.count("goal_audit_boundary_opened") == 1
    assert event_types.count("goal_audit_boundary_resolved") == 0
    assert event_types.count("protocol_rejection_recorded") == 2
    assert len(selector._session.payloads) == 1
    assert result.state.status.value == "interrupted"


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
            [json.dumps(rejected_audit_output), json.dumps(audit_output)],
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
        checkpoint.lane_kind is ModelLaneKind.AUDIT
        and checkpoint.model == "test-rwkv-7.2b-auditor"
        for checkpoint in state.model_states.values()
    )
    assert any(
        item["type"] == "model_session_bootstrapped"
        and item["lane_kind"] == "audit"
        for item in audits
    )
    assert not any(item["type"] == "model_session_forked" for item in audits)
    assert sum(item["type"].endswith("candidate_committed") for item in audits) == 1
    event_types = [
        state.causal_records[event_id].event_type for event_id in state.causal_order
    ]
    assert event_types.count("goal_audit_recorded") == 2
    assert event_types.count("goal_audit_rejected") == 1
    assert not any(
        item.event_type == "goal_audit_retry_feedback"
        for item in state.model_events.values()
    )
    executor_transcript = state.model_states[state.lane_head("executor")].transcript
    assert "MODEL-MUST-NOT-BIND" not in executor_transcript
    audit_checkpoint = next(
        checkpoint
        for checkpoint in state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.AUDIT
    )
    audit_payload = json.loads(
        audit_checkpoint.transcript.split("\n\nUser: ", 1)[1].split(
            "\n\nAssistant:", 1
        )[0]
    )
    assert list(audit_payload)[-1] == "current_question"
    assert state.goal.request not in audit_checkpoint.transcript
    assert audit_payload["active_step"]["step_id"] == "S1"
    assert "kernel_bound_fields" not in audit_checkpoint.transcript
    assert "audit_boundary_id" not in audit_payload
    assert audit_payload["evidence_records"][0]["action"]["action_id"] == "A00001"
    assert audit_payload["evidence_records"][0]["action"]["status"] == "succeeded"
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
            _QueueClient([]), settings=_settings(progressive=True), audit_hook=audit_hook
        ),
    )
    planner = _StrongPlanner()
    monkeypatch.setattr(
        "rwkv_lh.product_runtime.OpenAICompatibleSupervisorClient",
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
    assert controller.model.auditor_session is not controller.model.session
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
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": "result.txt", "content": "verified"},
                    }
                ),
                json.dumps(first_audit),
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": "Created and verified result.txt."},
                    }
                ),
                json.dumps(final_audit),
            ]
        ),
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
    assert (Path(state.goal.workspace_root) / "result.txt").read_text() == "verified"
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("goal_audit_accepted") == 2
    assert event_types.count("goal_plan_patch_committed") == 1
    assert event_types.count("goal_stage_review_committed") == 1
    assert planner.requests and planner.requests[0].plan_revision == 0
    assert len(planner.stage_review_requests) == 1
    stage_fact = planner.stage_review_requests[0].recent_action_facts[0]
    assert stage_fact["operation"] == "write_file"
    assert '"success":true' in stage_fact["result_projection"]
    assert event_types[-1] == "run_completed"
    completed = result.state.causal_records[result.state.causal_order[-1]].payload
    assert completed["audit_id"].startswith("AUD-")
    assert completed["rwkv_audit_accepted"] is True


def test_rwkv_repair_audit_requests_strong_planner_correction_without_reviewer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-STRONG-REPLAN")
    repair_audit = _audit_call(
        "repair",
        step_id="S1",
        step_complete=False,
        evidence_refs=["A00001"],
        gaps=["the requested artifact was not created"],
        reason="the mutation failed and the frontier still lacks evidence",
    )
    session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    {
                        "function": "write_file",
                        "params": {"path": ".", "content": "cannot replace a directory"},
                    }
                ),
                json.dumps(repair_audit),
            ]
        ),
        settings=_settings(progressive=True),
    )
    model = LongHorizonModel(session, tool_selector=_selector(["write_file"]))
    planner = _StrongPlanner(
        (_strong_patch(state), _strong_correction_patch(state))
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
        max_transitions=4,
    )

    result = controller.run(state.run_id)

    assert [request.plan_revision for request in planner.requests] == [0, 1]
    assert planner.requests[1].latest_audit is not None
    assert planner.requests[1].latest_audit["verdict"] == "repair"
    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert event_types.count("goal_plan_patch_committed") == 2
    assert event_types.count("rwkv_contract_review_projected") == 0
    assert event_types.count("contract_graph_review_committed") == 0
    assert rolling_goal_plan(result.state).step_revisions["S1"] == 2


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
