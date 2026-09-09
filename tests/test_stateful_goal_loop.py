from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.goal_loop_protocol import (
    GOAL_AUDIT_SCHEMA_VERSION,
    GOAL_AUDIT_INPUT_PROTOCOL,
    GOAL_PLAN_PATCH_SCHEMA_VERSION,
    AuditedStep,
    GoalAuditDecision,
    GoalAuditVerdict,
    GoalObligation,
    GoalPlanPatch,
    GoalPlanStep,
    GoalStageReview,
    GoalStageReviewVerdict,
    RollingGoalPlan,
    action_mutates_root,
    goal_audit_output_constraints,
    rolling_goal_plan,
    validate_audit_authority,
)
from rwkv_lh.exact_tool_selector.native_network_client import (
    NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA,
    NativeNetworkSelectorClient,
    NativeNetworkSelectorSettings,
)
from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
    NativeNetworkToolSelection,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.exact_tool_selector.runtime_projection import (
    goal_frontier_selector_context,
)
from rwkv_lh.model import LongHorizonModel, ModelProtocolError
from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.model_session import InputBudgetError, ModelSession
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
from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    GoalState,
    ModelLaneKind,
    TaskAction,
    utc_now,
)
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy
from rwkv_lh.trace_projection import unresolved_supervisor_pending
from rwkv_lh.goal_state_protocols import selector_intent_v5, executor_args_v5, finalizer_answer, auditor_final


def _role_prompt_payload(prompt: str, prefix: str) -> dict:
    return json.JSONDecoder().raw_decode(prompt.split(prefix, 1)[1])[0]


@pytest.mark.parametrize("version", ["v1", "v2", "v3", "v999"])
def test_plan_patch_rejects_every_noncurrent_version(version: str) -> None:
    current = GoalPlanPatch(patch_id="CURRENT", base_revision=0,
        add_steps=(GoalPlanStep(step_id="S1", objective="Inspect", phase="observe",
            read_roots=(".",), success_evidence=("workspace observed",)),),
        replace_steps=(), discard_step_ids=(), reason="current contract").to_dict()
    current["schema_version"] = GOAL_PLAN_PATCH_SCHEMA_VERSION.rsplit(".", 1)[0] + "." + version
    with pytest.raises(ValueError, match="unsupported Goal PlanPatch schema"):
        GoalPlanPatch.from_dict(current)


def test_plan_step_requires_an_explicit_phase() -> None:
    with pytest.raises(ValueError, match="phase"):
        GoalPlanStep(step_id="S1", objective="Inspect", read_roots=(".",),
            success_evidence=("workspace observed",))


@pytest.mark.parametrize("accepted_role", ["auditor_step", "auditor_final"])
def test_accepted_audit_is_committed_without_regeneration_after_process_loss(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, accepted_role: str,
) -> None:
    class ProcessLoss(BaseException):
        pass

    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-COMMIT-RECOVERY")
    queue = _QueueClient([
        ModelCommand("write_file", {"path": "result.txt", "content": "verified"}).canonical,
        json.dumps(_audit_call("continue", step_id="S1", step_complete=True,
            evidence_refs=["A00001"], gaps=[], reason="written")),
        ModelCommand("final_answer", {"text": "Created result.txt."}).canonical,
        json.dumps(_audit_call("ready_for_final", step_id="", step_complete=False,
            evidence_refs=["A00001"], gaps=[], reason="complete")),
    ])
    model = LongHorizonModel(ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["write_file"]))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=20)
    monkeypatch.setattr(StatefulGoalLoopController, "_validate_contract_patch_semantics",
        staticmethod(lambda *a, **kw: None))
    original_save = store.save
    interrupted = False

    def lose_process_after_durable_accept(*args, **kwargs):
        nonlocal interrupted
        saved = original_save(*args, **kwargs)
        event = saved.causal_records[saved.causal_order[-1]]
        if event.event_type == "goal_audit_accepted":
            role = "auditor_step" if event.payload["audit"]["step_id"] else "auditor_final"
            if role == accepted_role and not interrupted:
                interrupted = True
                raise ProcessLoss()
        return saved

    monkeypatch.setattr(store, "save", lose_process_after_durable_accept)
    with pytest.raises(ProcessLoss):
        controller.run(state.run_id)
    recovered = controller.run(state.run_id).state
    assert recovered.status.value == "completed"
    events = [recovered.causal_records[key] for key in recovered.causal_order]
    assert sum(event.event_type == "goal_auditor_session_started" for event in events) == 2
    assert sum(event.event_type == "goal_audit_accepted" for event in events) == 2
    assert sum(event.event_type == "goal_audit_boundary_resolved" for event in events) == 2
    assert len(recovered.actions) == 1


@pytest.mark.parametrize("suffix", [".json", ".data", ""])
def test_json_diagnostic_eligibility_is_independent_of_filename(tmp_path: Path, suffix: str) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "RENAME-INVARIANT")
    name = "payload" + suffix
    (Path(state.goal.workspace_root) / name).write_text("{ broken json")
    model = LongHorizonModel(ModelSession(_QueueClient([]), settings=_settings(progressive=True)), tool_selector=_selector([]))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(), supervisor_policy=SupervisorPolicy(mode="static"))
    step = GoalPlanStep(step_id="S1", objective="Diagnose the resource format", phase="observe",
        read_roots=(name,), success_evidence=("actual parse result",))
    assert "read_json" in controller._goal_step_operations(state, step)


def test_directory_projection_cannot_hide_compatible_tools(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "DISCOVERY-INVARIANT")
    root = Path(state.goal.workspace_root)
    for index in range(256):
        (root / f"a{index:04d}").write_bytes(b"\xff\x00")
    (root / "z_readable").write_text("observed text")
    model = LongHorizonModel(ModelSession(_QueueClient([]), settings=_settings(progressive=True)), tool_selector=_selector([]))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(), supervisor_policy=SupervisorPolicy(mode="static"))
    step = GoalPlanStep(step_id="S1", objective="Inspect the workspace", phase="observe",
        read_roots=(".",), success_evidence=("required source content",))
    operations, contract = controller._goal_step_operation_contract(state, step)
    assert "read_file" in operations
    assert contract["discovery_complete"] is False
    descriptors, complete = model.harness.workspace_target_descriptors(
        state.goal, (".", "z_readable"), expand_directories=True, max_entries=16,
    )
    assert complete is False
    assert {".", "z_readable"} <= {item["path"] for item in descriptors}


@pytest.mark.parametrize("resume_after_repair", [False, True])
def test_final_evidence_gap_reopens_execution_with_bound_feedback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, resume_after_repair: bool,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "FINAL-EVIDENCE-REPAIR")
    gap = next(item["code"] for item in auditor_final.build_gap_catalog(state.goal.request, (), ())
        if item["code"].startswith("goal_requirement_unproved:"))
    queue = _QueueClient([
        ModelCommand("write_file", {"path": "result.txt", "content": "verified"}).canonical,
        json.dumps(_audit_call("continue", step_id="S1", step_complete=True, evidence_refs=["A00001"], gaps=[], reason="written")),
        ModelCommand("final_answer", {"text": "Initial candidate."}).canonical,
        json.dumps(_audit_call("repair", step_id="", step_complete=False, evidence_refs=["A00001"], gaps=[gap], reason="needs readback")),
        ModelCommand("read_file", {"path": "result.txt"}).canonical,
        json.dumps(_audit_call("continue", step_id="S2", step_complete=True, evidence_refs=["A00002"], gaps=[], reason="observed")),
        ModelCommand("final_answer", {"text": "Written and read back."}).canonical,
        json.dumps(_audit_call("ready_for_final", step_id="", step_complete=False, evidence_refs=["A00001", "A00002"], gaps=[], reason="all proved")),
    ])
    model = LongHorizonModel(ModelSession(queue, settings=_settings(progressive=True)), tool_selector=_selector(["write_file", "read_file"]))
    repair = GoalPlanPatch(patch_id="GPP-final-evidence", base_revision=1,
        add_steps=(GoalPlanStep(step_id="S2", objective="Read back the committed result", phase="observe", stage=2,
            depends_on=("S1",), read_roots=("result.txt",), success_evidence=("result bytes read back",)),),
        replace_steps=(), discard_step_ids=(), reason="Close the final evidence gap")
    planner = _StrongPlanner((_strong_patch(state), repair))
    monkeypatch.setattr(StatefulGoalLoopController, "_validate_contract_patch_semantics", staticmethod(lambda *a, **kw: None))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=planner, supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=5 if resume_after_repair else 20)
    result = controller.run(state.run_id)
    if resume_after_repair:
        assert result.state.status.value == "interrupted"
        controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
            supervisor=planner, supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=20)
        result = controller.run(state.run_id)
    assert result.state.status.value == "completed"
    assert [action.action_type for action in result.state.actions.values()] == ["write_file", "read_file"]
    assert len(planner.requests) == 2
    feedback = planner.requests[1].repair_feedback
    assert feedback["recipient_roles"] == ["planner"]
    assert feedback["issues"][0]["criterion"] == state.goal.request
    assert feedback["issues"][0]["code"] == gap
    assert len(rolling_goal_plan(result.state).patch_ids) == 2


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


def test_recent_action_funnel_preserves_complete_negative_json_fact(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "primary.json").write_text('{"value":', encoding="utf-8")
    goal = LongHorizonModel.create_literal_goal(
        "Use backup.json when primary.json is not readable JSON.",
        str(workspace),
    )
    result = ActionHarness(sandbox_commands=False).execute(
        TaskAction("read_json", {"path": "primary.json"}),
        goal,
    )
    state = SimpleNamespace(
        goal=goal,
        actions={
            "A00001": SimpleNamespace(
                action_id="A00001",
                sequence=1,
                action_type="read_json",
                status=ActionStatus.SUCCEEDED,
                arguments={"path": "primary.json"},
                result=result.to_dict(),
                artifact_refs=(),
                workspace_digest_after="digest",
                error=None,
            )
        },
    )

    fact = StatefulGoalLoopController._recent_action_facts(state)[0]
    packet = json.loads(fact["result_projection"])

    assert len(fact["result_projection"].encode("utf-8")) <= 2400
    assert packet["metadata"]["valid_json"] is False
    assert packet["metadata"]["parse_outcome_complete"] is True
    assert packet["metadata"]["parse_error"]["source_span"]["content"] == '{"value":'
    assert packet["fact_authority"] == "literal_fields_and_exact_spans_only"
    assert "digest_and_outcome_only" not in fact["result_projection"]

    # Stage evidence may bind an action, an artifact, or its revision. All three
    # must expose exactly the same producing Harness fact, without duplication.
    state.artifacts = {"ART1": SimpleNamespace(action_id="A00001")}
    state.artifact_revisions = {"primary.json": [SimpleNamespace(revision_id="REV1", action_id="A00001")]}
    for refs in (("A00001",), ("ART1",), ("REV1",), ("A00001", "ART1", "REV1")):
        assert StatefulGoalLoopController._recent_action_facts(state, action_ids=refs, max_actions=None) == (fact,)
    state.artifacts["ART1"].action_id = "MISSING"
    with pytest.raises(ValueError, match="producing action"):
        StatefulGoalLoopController._recent_action_facts(state, action_ids=("ART1",), max_actions=None)


def test_recent_action_facts_bound_multibyte_arguments_instead_of_crashing(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    goal = LongHorizonModel.create_literal_goal("写入中文说明文件。", str(workspace))
    content = "发布说明：" * 120  # ~600 characters, ~1800 UTF-8 bytes
    result = ActionHarness(sandbox_commands=False).execute(
        TaskAction("write_file", {"path": "说明.txt", "content": content}),
        goal,
    )
    state = SimpleNamespace(
        goal=goal,
        actions={
            "A00001": SimpleNamespace(
                action_id="A00001",
                sequence=1,
                action_type="write_file",
                status=ActionStatus.SUCCEEDED,
                arguments={"path": "说明.txt", "content": content},
                result=result.to_dict(),
                artifact_refs=(),
                workspace_digest_after="digest",
                error=None,
            )
        },
    )

    fact = StatefulGoalLoopController._recent_action_facts(state)[0]

    assert len(fact["arguments_projection"].encode("utf-8")) <= 1200
    assert fact["arguments_truncated"] is True
    assert "说明.txt" in fact["arguments_projection"]


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
    def __init__(self, settings: NativeNetworkSelectorSettings, operations: list[str]):
        self.settings = settings
        self.operations = list(operations)
        self.payloads: list[dict] = []
        self.current_operation = ""

    def post(self, url: str, *, json: dict, timeout: tuple[float, float]):
        del timeout
        assert url.endswith("/selector-intent-v5/select")
        self.payloads.append(dict(json))
        menu_order_id = str(json.get("menu_order_id") or "")
        if menu_order_id == "canonical":
            self.current_operation = self.operations.pop(0)
        if not self.current_operation:
            raise AssertionError("non-canonical Selector lane ran before canonical")
        global_peak = self.current_operation
        index = len(self.payloads)
        eligible_labels = tuple(str(item) for item in json["eligible_labels"])
        selected_index = max(
            (
                NETWORK_EXACT_TOOL_LABELS.index(label)
                for label in eligible_labels
            ),
            key=lambda item: (
                item == NETWORK_EXACT_TOOL_LABELS.index(global_peak),
                -item,
            ),
        )
        operation = NETWORK_EXACT_TOOL_LABELS[selected_index]
        eligible_token_ids = [
            100 + NETWORK_EXACT_TOOL_LABELS.index(label)
            for label in eligible_labels
        ]
        selected_token_id = 100 + selected_index
        selection = NativeNetworkToolSelection(
            selection_id=f"NSEL-{index:04d}",
            trace_id=str(json["trace_id"]),
            selected_operation=operation,
            input_digest=str(json["input_digest"]),
            menu_digest=str(json["menu_digest"]),
            selector_checkpoint_id=f"NSCP-{index:04d}",
            input_token_count=20,
            model=self.settings.model,
            model_sha256=self.settings.model_sha256,
            decoder_id=self.settings.decoder_id,
            decoder_sha256=self.settings.decoder_sha256,
            decoder_protocol=self.settings.decoder_protocol,
            profile_id=self.settings.state_profile_id,
            profile_sha256=self.settings.state_profile_sha256,
            eligible_labels=eligible_labels,
            decoder_trace={
                "schema_version": "rwkv-lh.native-role-suffix-selection.v1",
                "candidate_labels": list(eligible_labels),
                "prompt_token_count": 20,
                "selected_label": operation,
                "token_ids": [selected_token_id],
                "decisions": [
                    {
                        "position": 0,
                        "allowed_token_ids": eligible_token_ids,
                        "allowed_token_logits": {
                            str(token_id): (
                                10.0 if token_id == selected_token_id else 0.0
                            )
                            for token_id in eligible_token_ids
                        },
                        "chosen_token_id": selected_token_id,
                        "chosen_token_logit": 10.0,
                        "chosen_vs_runner_up_margin": (
                            None if len(eligible_token_ids) == 1 else 10.0
                        ),
                    }
                ],
            },
        )
        return _SelectorResponse(
            {
                "schema_version": NATIVE_SELECTOR_SERVICE_RESPONSE_SCHEMA,
                "runtime_identity": self.settings.runtime_identity(),
                "selection": selection.raw_record(),
            }
        )


def _selector(operations: list[str]) -> NativeNetworkSelectorClient:
    settings = NativeNetworkSelectorSettings(
        base_url="http://127.0.0.1:29621",
        model="test-rwkv-g1j-2.9b",
        model_sha256="a" * 64,
        decoder_id=NATIVE_SELECTOR_DECODER_ID,
        decoder_sha256="b" * 64,
        decoder_protocol=NATIVE_SELECTOR_DECODER_PROTOCOL,
        state_profile_id="selector-zero-v1",
        state_profile_sha256="d" * 64,
        state_profile_manifest_sha256="e" * 64,
    )
    return NativeNetworkSelectorClient(
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
        add_steps=(GoalPlanStep(phase="mutate",
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
        replace_steps=(GoalPlanStep(phase="observe",
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
        replace_steps=(GoalPlanStep(phase="observe",
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
        add_steps=(GoalPlanStep(phase="observe",
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
        add_steps=(GoalPlanStep(phase="observe",
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
    if step_id and verdict in {"continue", "repair"}:
        reason = (
            "evidence_complete" if verdict == "continue" else "evidence_incomplete"
        )
    elif not step_id and verdict in {"ready_for_final", "repair"}:
        reason = (
            "final_evidence_complete"
            if verdict == "ready_for_final"
            else "final_evidence_incomplete"
        )
        if verdict == "repair" and gaps and not all(
            code.startswith("goal_requirement_unproved:") or code in {
                "candidate_omits_required_result", "candidate_unsupported_claim"
            } for code in gaps
        ):
            gaps = ["candidate_omits_required_result"]
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
        {"goal_obligations": [],
            "add_stages": [
                {
                    "stage": 1,
                    "steps": [
                        {"obligation_ids": [],
                                "step_id": "S1",
                                "objective": "Inspect left.json",
                                "phase": "observe",
                            "depends_on": [],
                            "success_evidence": ["left.json observed"],
                            "read_roots": ["left.json"],
                            "write_roots": [],
                            "constraints": [],
                        },
                        {"obligation_ids": [],
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
                        {"obligation_ids": [],
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


def test_goal_obligation_phases_require_continuation_before_final() -> None:
    obligation = GoalObligation(
        obligation_id="O1",
        predicate="the requested report is grounded and written",
        required_phases=("observe", "mutate"),
    )
    initial = GoalPlanPatch(
        patch_id="GPP-obligation-observe",
        base_revision=0,
        goal_obligations=(obligation,),
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Inspect the source",
                phase="observe",
                obligation_ids=("O1",),
                success_evidence=("source observed",),
                read_roots=("source.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Observe before writing",
    )
    plan = RollingGoalPlan(goal_digest="goal")
    plan.apply_goal_patch(initial)
    plan.apply_audit(
        GoalAuditDecision(
            audit_id="AUD-observe",
            verdict=GoalAuditVerdict.CONTINUE,
            step_id="S1",
            evidence_refs=("A1",),
            gaps=(),
            completed_steps=(AuditedStep("S1", ("A1",)),),
            reason="source observed",
        )
    )

    assert plan.batch_complete is True
    assert plan.complete is False
    assert plan.uncovered_obligation_phases == {"O1": ("mutate",)}

    continuation = GoalPlanPatch(
        patch_id="GPP-obligation-mutate",
        base_revision=1,
        add_steps=(
            GoalPlanStep(
                step_id="S2",
                objective="Write the grounded report",
                phase="mutate",
                stage=2,
                depends_on=("S1",),
                obligation_ids=("O1",),
                success_evidence=("report written",),
                write_roots=("report.md",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Cover the remaining mutation phase",
    )
    plan.apply_goal_patch(continuation)
    assert [step.step_id for step in plan.frontier] == ["S2"]
    plan.apply_audit(
        GoalAuditDecision(
            audit_id="AUD-mutate",
            verdict=GoalAuditVerdict.CONTINUE,
            step_id="S2",
            evidence_refs=("A2",),
            gaps=(),
            completed_steps=(AuditedStep("S2", ("A2",)),),
            reason="report written",
        )
    )
    assert plan.complete is True
    assert plan.uncovered_obligation_phases == {}


def test_workspace_target_kinds_compile_exact_observe_menus(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "TYPED-OBSERVE-MENUS")
    workspace = Path(state.goal.workspace_root)
    (workspace / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    (workspace / "config.json").write_text('{"ok": true}\n', encoding="utf-8")
    (workspace / "invalid.json").write_text("{not-json\n", encoding="utf-8")
    (workspace / "folder").mkdir()
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

    python_operations = controller._goal_step_operations(
        state,
        GoalPlanStep(
            step_id="PY",
            objective="Inspect tool.py",
            phase="observe",
            success_evidence=("tool.py observed",),
            read_roots=("tool.py",),
        ),
    )
    json_operations = controller._goal_step_operations(
        state,
        GoalPlanStep(
            step_id="JSON",
            objective="Inspect config.json",
            phase="observe",
            success_evidence=("config.json observed",),
            read_roots=("config.json",),
        ),
    )
    directory_operations = controller._goal_step_operations(
        state,
        GoalPlanStep(
            step_id="DIR",
            objective="Inspect folder",
            phase="observe",
            success_evidence=("folder observed",),
            read_roots=("folder",),
        ),
    )
    invalid_json_operations = controller._goal_step_operations(
        state,
        GoalPlanStep(
            step_id="INVALID-JSON",
            objective="Attempt to parse invalid.json and preserve fallback evidence",
            phase="observe",
            success_evidence=("invalid.json parse outcome is observed",),
            read_roots=("invalid.json",),
        ),
    )

    assert "read_file" in python_operations
    assert "read_json" in python_operations
    assert "list_directory" not in python_operations
    assert "read_json" in json_operations
    assert "read_file" in json_operations
    assert "list_directory" not in json_operations
    assert "list_directory" in directory_operations
    assert "read_file" not in directory_operations
    assert "read_json" not in directory_operations
    assert "file_digest" not in directory_operations
    assert "read_json" in invalid_json_operations
    assert "read_file" in invalid_json_operations
    assert model.harness.workspace_target_descriptor(
        state.goal, "invalid.json"
    )["target_kind"] == "text_file"


def test_scalar_format_hint_and_directory_write_scope_keep_structural_mutations(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "TYPED-MUTATE-MENUS")
    workspace = Path(state.goal.workspace_root)
    (workspace / "VERSION").write_text("2\n", encoding="utf-8")
    (workspace / "flag.txt").write_text("true\n", encoding="utf-8")
    (workspace / "data.json").write_text("[1, 2]\n", encoding="utf-8")
    (workspace / "src").mkdir()
    (workspace / "src" / "app.py").write_text("print('ok')\n", encoding="utf-8")
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

    # Actual JSON scalars have the same format hint regardless of their name.
    assert model.harness.workspace_target_descriptor(state.goal, "VERSION")[
        "target_kind"
    ] == "json_file"
    assert model.harness.workspace_target_descriptor(state.goal, "flag.txt")[
        "target_kind"
    ] == "json_file"
    assert model.harness.workspace_target_descriptor(state.goal, "data.json")[
        "target_kind"
    ] == "json_file"
    version_operations = controller._goal_step_operations(
        state,
        GoalPlanStep(
            step_id="VER",
            objective="Bump VERSION",
            phase="mutate",
            success_evidence=("VERSION updated",),
            write_roots=("VERSION",),
        ),
    )
    assert "append_file" in version_operations
    assert "replace_text" in version_operations

    # A directory write root authorises creating new files under it, so the
    # file-writing operations stay eligible and the existing child is typed.
    operations, contract = controller._goal_step_operation_contract(
        state,
        GoalPlanStep(
            step_id="SRC",
            objective="Create src/util.py",
            phase="mutate",
            success_evidence=("src/util.py exists",),
            write_roots=("src",),
        ),
        mechanical_evidence=None,
    )
    assert "write_file" in operations
    assert "write_json" in operations
    assert "make_directory" in operations
    assert "patch_json" in operations
    assert contract["compatible_targets_by_operation"]["write_file"] == ["src/app.py"]
    # Existing file paths are hints for all structural file writers.
    assert contract["compatible_targets_by_operation"]["write_json"] == ["src/app.py"]
    assert {"path": "src/app.py", "target_kind": "text_file"} in [
        {"path": item["path"], "target_kind": item["target_kind"]}
        for item in contract["target_descriptors"]
    ]


@pytest.mark.parametrize(
    ("declared_phase", "missing_reads", "missing_writes", "expected_phase"),
    (
        ("observe", ("verify_project.py",), (), "observe"),
        ("mutate", ("verify_project.py",), ("pricing.py",), "observe"),
        ("mutate", (), ("verify_project.py",), "mutate"),
    ),
)
def test_target_contract_excludes_mechanically_completed_roots(
    tmp_path: Path,
    declared_phase: str,
    missing_reads: tuple[str, ...],
    missing_writes: tuple[str, ...],
    expected_phase: str,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "REMAINING-TARGET-CONTRACT")
    workspace = Path(state.goal.workspace_root)
    (workspace / "pricing.py").write_text("PRICE = 1\n", encoding="utf-8")
    (workspace / "verify_project.py").write_text(
        "print('ok')\n", encoding="utf-8"
    )
    model = LongHorizonModel(
        ModelSession(_QueueClient([]), settings=_settings(progressive=True)),
        tool_selector=_selector([]),
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=1,
    )
    step = GoalPlanStep(
        step_id="MULTI",
        objective="Inspect and update the relevant implementation files",
        phase=declared_phase,
        success_evidence=("both roots have the required evidence",),
        read_roots=("pricing.py", "verify_project.py"),
        write_roots=(
            ("pricing.py", "verify_project.py")
            if declared_phase == "mutate"
            else ()
        ),
    )

    _operations, contract = controller._goal_step_operation_contract(
        state,
        step,
        mechanical_evidence={
            "missing_read_roots": list(missing_reads),
            "missing_write_roots": list(missing_writes),
        },
    )

    assert contract["phase"] == expected_phase
    assert contract["roots"] == ["verify_project.py"]
    assert {item["path"] for item in contract["target_descriptors"]} == {
        "verify_project.py"
    }
    non_empty_candidates = [
        candidates
        for candidates in contract["compatible_targets_by_operation"].values()
        if candidates
    ]
    assert non_empty_candidates
    assert all(
        candidates == ["verify_project.py"]
        for candidates in non_empty_candidates
    )


@pytest.mark.parametrize(
    ("operation", "invalid_path", "valid_path"),
    (
        ("read_json", ".", "config.json"),
        ("read_file", ".", "tool.py"),
        ("list_directory", "tool.py", "."),
    ),
)
def test_operation_target_mismatch_is_repaired_before_harness(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    operation: str,
    invalid_path: str,
    valid_path: str,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), f"TARGET-PREFLIGHT-{operation}")
    workspace = Path(state.goal.workspace_root)
    (workspace / "tool.py").write_text("print('ok')\n", encoding="utf-8")
    (workspace / "config.json").write_text('{"ok": true}\n', encoding="utf-8")
    queue = _QueueClient(
        [
            json.dumps({"function": operation, "params": {"path": invalid_path}}),
            json.dumps({"function": operation, "params": {"path": valid_path}}),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the compatible observation succeeded",
                )
            ),
            json.dumps(
                {"function": "final_answer", "params": {"text": "Observed."}}
            ),
            json.dumps(
                _audit_call(
                    "ready_for_final",
                    step_id="",
                    step_complete=False,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the completed plan has accepted evidence",
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    model = LongHorizonModel(session, tool_selector=_selector([operation]))
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=_StrongPlanner(_strong_observe_patch(state, ".")),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=16,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert len(result.state.actions) == 1
    assert next(iter(result.state.actions.values())).arguments["path"] == valid_path
    rejections = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "protocol_rejection_recorded"
    ]
    assert len(rejections) == 1
    assert rejections[0].payload["error"].startswith(
        "[operation_target_contract]"
    )
    assert invalid_path in rejections[0].payload["error"]
    assert valid_path in rejections[0].payload["error"]


def test_new_non_observe_step_reports_exact_mixed_read_contract() -> None:
    with pytest.raises(
        ValueError,
        match=(
            r"Goal plan step 'S2' with phase='mutate' must set read_roots=\[\]; "
            r"move inspection into a prior phase='observe' step"
        ),
    ):
        GoalPlanPatch.from_model_value(
            {"goal_obligations": [],
                "add_stages": [
                    {
                        "stage": 1,
                        "steps": [
                            {"obligation_ids": [],
                                "step_id": "S2",
                                "objective": "Inspect and update pricing.py",
                                "phase": "mutate",
                                "depends_on": [],
                                "success_evidence": ["pricing.py is updated"],
                                "read_roots": ["pricing.py"],
                                "write_roots": ["pricing.py"],
                                "constraints": [],
                            }
                        ],
                    }
                ],
                "replace_stages": [],
                "discard_step_ids": [],
                "reason": "incorrectly mixes observation and mutation",
            },
            patch_id="GPP-mixed-read",
            base_revision=0,
        )


def test_stage_repair_cannot_append_behind_an_unchanged_open_frontier() -> None:
    initial = GoalPlanPatch(
        patch_id="GPP-stage-repair-initial",
        base_revision=0,
        add_steps=(
            GoalPlanStep(phase="observe",
                step_id="S1",
                objective="Inspect the verifier",
                stage=1,
                success_evidence=("verifier observed",),
                read_roots=("verify.py",),
            ),
            GoalPlanStep(phase="mutate",
                step_id="S2",
                objective="Implement the feature",
                stage=2,
                depends_on=("S1",),
                success_evidence=("feature written",),
                write_roots=("feature.py",),
            ),
            GoalPlanStep(phase="observe",
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
        add_steps=(GoalPlanStep(phase="observe",
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
        replace_steps=(GoalPlanStep(phase="mutate",
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


def test_same_stage_conflicting_roots_are_rejected() -> None:
    plan = RollingGoalPlan(goal_digest="goal")
    patch = GoalPlanPatch(
        patch_id="GPP-conflict",
        base_revision=0,
        add_steps=(
            GoalPlanStep(phase="mutate",
                step_id="S1",
                objective="Write a configuration",
                success_evidence=("configuration written",),
                write_roots=("config",),
            ),
            GoalPlanStep(phase="observe",
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
        plan.frontier[0].to_dict(),
    )

    assert context.current_subtask == {
        "objective": "Create result.txt with verified content",
        "phase": "mutate",
        "read_roots": [],
        "write_roots": ["result.txt"],
        "success_evidence": ["result.txt has a committed artifact revision"],
        "constraints": [],
    }
    assert state.goal.request not in context.current_subtask["objective"]
    assert state.goal.workspace_root not in json.dumps(
        context.current_subtask, ensure_ascii=False
    )


def test_read_only_goal_step_menu_excludes_workspace_mutations(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "READ-ONLY-GOAL-MENU")
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        "current\n",
        encoding="utf-8",
    )
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
    read_only = GoalPlanStep(phase="observe",
        step_id="READ",
        objective="Inspect result.txt without changing the workspace",
        success_evidence=("result.txt is observed",),
        read_roots=("result.txt",),
    )
    mutation = GoalPlanStep(phase="mutate",
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
    _command_operations, command_contract = (
        controller._goal_step_operation_contract(state, command_mutation)
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
    assert command_contract["phase"] == "execute"
    assert command_contract["roots"] == ["generated.txt"]
    assert command_contract["target_descriptors"] == [
        {
            "path": "generated.txt",
            "type": "missing",
            "target_kind": "missing",
            "exists": False,
        }
    ]


def test_controller_derives_exact_workspace_path_delta_for_mutating_command() -> None:
    before = {
        "cacheable": True,
        "entries": [
            {"path": "keep.txt", "type": "file", "size_bytes": 4, "sha256": "a"},
            {"path": "old.txt", "type": "file", "size_bytes": 3, "sha256": "b"},
        ],
    }
    after = {
        "cacheable": True,
        "entries": [
            {"path": "keep.txt", "type": "file", "size_bytes": 5, "sha256": "c"},
            {"path": "output", "type": "directory"},
            {"path": "output/new.txt", "type": "file", "size_bytes": 3, "sha256": "d"},
        ],
    }

    changes = LongHorizonController._workspace_change_metadata(before, after)

    assert changes == {
        "schema_version": "rwkv-lh.workspace-changes.v1",
        "complete": True,
        "reason": "",
        "changed_paths": ["keep.txt", "old.txt", "output", "output/new.txt"],
        "created_paths": ["output", "output/new.txt"],
        "modified_paths": ["keep.txt"],
        "deleted_paths": ["old.txt"],
    }


def test_run_command_root_coverage_and_scope_use_observed_workspace_delta() -> None:
    action = SimpleNamespace(
        action_type="run_command",
        arguments={"argv": ["python", "generate.py"]},
        result={
            "success": True,
            "metadata": {
                "workspace_changes": {
                    "complete": True,
                    "reason": "",
                    "changed_paths": ["output", "output/generated.txt"],
                }
            },
        },
    )

    assert action_mutates_root(action, "output/generated.txt") is True
    assert action_mutates_root(action, "other.txt") is False
    assert StatefulGoalLoopController._run_command_write_scope_gaps(
        action, ("output/generated.txt",)
    ) == ()

    action.result["metadata"]["workspace_changes"]["changed_paths"].append(
        "outside.txt"
    )
    assert StatefulGoalLoopController._run_command_write_scope_gaps(
        action, ("output/generated.txt",)
    ) == (
        "run_command changed paths outside declared write_roots: ['outside.txt']",
    )


def test_run_command_without_complete_workspace_delta_fails_closed() -> None:
    action = SimpleNamespace(
        action_type="run_command",
        arguments={"argv": ["python", "generate.py"]},
        result={
            "success": True,
            "metadata": {
                "workspace_changes": {
                    "complete": False,
                    "reason": "workspace_entry_limit_exceeded",
                    "changed_paths": [],
                }
            },
        },
    )

    assert action_mutates_root(action, "generated.txt") is False
    assert StatefulGoalLoopController._run_command_write_scope_gaps(
        action, ("generated.txt",)
    ) == (
        "run_command workspace changes are not fully observable: "
        "workspace_entry_limit_exceeded",
    )


def test_stateful_mutating_command_completes_from_observed_path_delta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-RUN-COMMAND-DELTA")
    patch = GoalPlanPatch(
        patch_id="GPP-command-delta",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Generate generated.txt with a local command",
                phase="execute",
                success_evidence=("generated.txt contains generated",),
                write_roots=("generated.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Exercise a declared mutating command boundary",
    )
    queue = _QueueClient(
        [
            json.dumps(
                {
                    "function": "run_command",
                    "params": {
                        "argv": [
                            "python",
                            "-c",
                            "from pathlib import Path; Path('generated.txt').write_text('generated\\n')",
                        ],
                        "expected_exit_code": 0,
                    },
                }
            ),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the command created the declared artifact",
                )
            ),
            json.dumps(
                {
                    "function": "final_answer",
                    "params": {"text": "generated.txt was created."},
                }
            ),
            json.dumps(
                _audit_call(
                    "ready_for_final",
                    step_id="",
                    step_complete=False,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the completed step has exact command mutation evidence",
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(
        session,
        harness=harness,
        tool_selector=_selector(["run_command"]),
    )
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=harness,
        supervisor=_StrongPlanner(patch),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=12,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert (Path(state.goal.workspace_root) / "generated.txt").read_text(
        encoding="utf-8"
    ) == "generated\n"
    action = result.state.actions["A00001"]
    changes = action.result["metadata"]["workspace_changes"]
    assert changes["complete"] is True
    assert changes["changed_paths"] == ["generated.txt"]
    assert action_mutates_root(action, "generated.txt") is True
    boundaries = [
        result.state.causal_records[event_id].payload.get("boundary")
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_audit_boundary_opened"
    ]
    assert "mutation_transaction_complete" in boundaries


def test_stateful_mutating_command_blocks_on_out_of_scope_path_delta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-RUN-COMMAND-SCOPE")
    patch = GoalPlanPatch(
        patch_id="GPP-command-scope",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Generate only generated.txt",
                phase="execute",
                success_evidence=("generated.txt exists",),
                write_roots=("generated.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Keep command mutation inside its declared root",
    )
    queue = _QueueClient(
        [
            json.dumps(
                {
                    "function": "run_command",
                    "params": {
                        "argv": [
                            "python",
                            "-c",
                            (
                                "from pathlib import Path; "
                                "Path('generated.txt').write_text('ok'); "
                                "Path('outside.txt').write_text('not allowed')"
                            ),
                        ],
                        "expected_exit_code": 0,
                    },
                }
            )
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    harness = ActionHarness(sandbox_commands=False)
    model = LongHorizonModel(
        session,
        harness=harness,
        tool_selector=_selector(["run_command"]),
    )
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=harness,
        supervisor=_StrongPlanner(patch),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=6,
    ).run(state.run_id)

    assert result.state.status.value == "blocked"
    violations = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_command_write_scope_violation"
    ]
    assert len(violations) == 1
    assert violations[0].payload["write_roots"] == ["generated.txt"]
    assert "outside.txt" in violations[0].payload["gaps"][0]
    terminal = result.state.causal_records[result.state.causal_order[-1]]
    assert terminal.payload["reason"] == "run_command_write_scope_violation"
    assert len(queue.prompts) == 1


def test_goal_selector_uses_three_fresh_evaluations_for_executable_frontier(
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
    assert len(selector._session.payloads) == 3
    assert all(
        "parent" not in payload
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


def test_incomplete_goal_obligation_coverage_requests_a_continuation_patch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "GOAL-COVERAGE-CONTINUATION")
    workspace = Path(state.goal.workspace_root)
    (workspace / "source.txt").write_text("ground truth\n", encoding="utf-8")
    obligation = GoalObligation(
        obligation_id="O1",
        predicate="source.txt is observed and report.md is written",
        required_phases=("observe", "mutate"),
    )
    initial = GoalPlanPatch(
        patch_id="GPP-coverage-initial",
        base_revision=0,
        goal_obligations=(obligation,),
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Read source.txt",
                phase="observe",
                obligation_ids=("O1",),
                success_evidence=("source.txt observed",),
                read_roots=("source.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Start with grounded observation",
    )
    continuation = GoalPlanPatch(
        patch_id="GPP-coverage-continuation",
        base_revision=1,
        add_steps=(
            GoalPlanStep(
                step_id="S2",
                objective="Write report.md with the observed result",
                phase="mutate",
                stage=2,
                depends_on=("S1",),
                obligation_ids=("O1",),
                success_evidence=("report.md written",),
                write_roots=("report.md",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Cover the remaining mutation obligation",
    )
    queue = _QueueClient(
        [
            json.dumps({"function": "read_file", "params": {"path": "source.txt"}}),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="source observed",
                )
            ),
            json.dumps(
                {
                    "function": "write_file",
                    "params": {"path": "report.md", "content": "ground truth\n"},
                }
            ),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S2",
                    step_complete=True,
                    evidence_refs=["A00002"],
                    gaps=[],
                    reason="report written",
                )
            ),
            json.dumps(
                {"function": "final_answer", "params": {"text": "Report written."}}
            ),
            json.dumps(
                _audit_call(
                    "ready_for_final",
                    step_id="",
                    step_complete=False,
                    evidence_refs=["A00001", "A00002"],
                    gaps=[],
                    reason="every obligation phase has accepted evidence",
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    model = LongHorizonModel(
        session,
        tool_selector=_selector(["read_file", "write_file"]),
    )
    planner = _StrongPlanner((initial, continuation))
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=24,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert [request.plan_revision for request in planner.requests] == [0, 1]
    assert (workspace / "report.md").read_text(encoding="utf-8") == "ground truth\n"
    plan = rolling_goal_plan(result.state)
    assert plan.batch_complete is True
    assert plan.complete is True
    assert plan.uncovered_obligation_phases == {}


@pytest.mark.parametrize("root_count", [2, 9])
def test_audit_evidence_projection_keeps_root_facts_after_unrelated_actions(
    tmp_path: Path,
    root_count: int,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "ROOT-EVIDENCE-WINDOW")
    workspace = Path(state.goal.workspace_root)
    roots = tuple(f"source-{index}.py" for index in range(root_count))
    for index, root in enumerate(roots):
        (workspace / root).write_text(f"VALUE = {index}\n", encoding="utf-8")
    patch = GoalPlanPatch(
        patch_id="GPP-root-evidence",
        base_revision=0,
        add_steps=(
            GoalPlanStep(phase="observe",
                step_id="READ",
                objective="Read pricing.py and verify_project.py",
                success_evidence=("both files are observed",),
                read_roots=roots,
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect both files",
    )
    outputs = [
        *(json.dumps({"function": "read_file", "params": {"path": root}}) for root in roots),
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
    for operation in (*("read_file",) * root_count, *("list_directory",) * 10):
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

    assert set(action_ids[:root_count]) <= set(refs)
    assert action_ids[-1] in refs
    assert len(refs) == root_count + 1


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
    selector = _selector(["write_file", "read_file"])
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
    assert len(selector._session.payloads) == 6
    second_selector_step = json.loads(
        selector._session.payloads[3]["step"].removeprefix(
            "SelectorIntentPromptV5: "
        )
    )
    assert second_selector_step["current_subtask"]["phase"] == "observe"
    assert second_selector_step["current_subtask"]["objective"] == (
        "Read back result.txt"
    )
    progress = second_selector_step["current_progress"]
    assert progress["assigned_action_count"] == 0
    assert progress["successful_action_count"] == 0
    assert progress["failed_action_count"] == 0
    assert progress["last_action"] is None
    assert progress["missing_read_roots"] == ["result.txt"]
    assert progress["missing_write_roots"] == []
    assert progress["workspace_targets"] == [{"path": "result.txt", "target_kind": "text_file"}]
    assert progress["completion_preconditions_satisfied"] is False
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


def test_clean_executor_turn_reduces_causal_facts_to_fit_input_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "EXECUTOR-BOOTSTRAP-BUDGET-FALLBACK")
    session = ModelSession(_QueueClient([]), settings=_settings(progressive=True))
    model = LongHorizonModel(session)
    previous = session.bootstrap(
        ModelLaneKind.ACTION,
        model._assignment(state, recent_limit=0, executor_only=True),
        model._menu_definitions,
        lane_id=model.ACTION_LANE_ID,
        progressive_tool_disclosure=True,
        independent_tool_selector=True,
    )
    state.model_states[previous.checkpoint_id] = previous
    state.set_lane_head("executor", previous.checkpoint_id)
    fact_action_ids: list[str] = []
    for sequence in range(1, 13):
        action_id = f"A{sequence:05d}"
        fact_action_ids.append(action_id)
        state.actions[action_id] = ActionRecord(
            action_id=action_id,
            sequence=sequence,
            status=ActionStatus.SUCCEEDED,
            action_type="read_file",
            arguments={"path": f"input-{sequence}.txt"},
            wire_arguments={"path": f"input-{sequence}.txt"},
            action_fingerprint=f"fingerprint-{sequence}",
            idempotency_key=f"idem-{sequence}",
            decision_id=f"D-{sequence}",
            request_id=f"MR-{sequence}",
            started_at=utc_now(),
            ended_at=utc_now(),
            result={"success": True, "output": f"fact-{sequence}"},
            outcome_type="success",
        )

    real_bootstrap = session.bootstrap
    attempted_counts: list[int] = []

    def budgeted_bootstrap(lane_kind, assignment, definitions, **kwargs):
        count = int(
            json.loads(assignment)["recent_action_sequence_range"]["count"]
        )
        attempted_counts.append(count)
        if count > 4:
            raise InputBudgetError(f"injected count {count} exceeds budget")
        return real_bootstrap(lane_kind, assignment, definitions, **kwargs)

    monkeypatch.setattr(session, "bootstrap", budgeted_bootstrap)
    persisted: list[tuple[str, dict]] = []

    checkpoint = model._start_clean_executor_turn(
        state,
        previous,
        lambda _state, event_type, payload: persisted.append(
            (event_type, dict(payload))
        ),
        fact_action_ids=fact_action_ids,
    )

    assert attempted_counts == [12, 8, 4]
    assert state.lane_heads["executor"] == checkpoint.checkpoint_id
    event_type, payload = persisted[-1]
    assert event_type == "action_session_started"
    assert payload["causal_fact_recent_limit"] == 4
    assert payload["causal_fact_action_ids"] == fact_action_ids[-4:]
    assert payload["causal_fact_requested_action_ids"] == fact_action_ids
    assert checkpoint.native_state_metadata["executor_fact_action_ids"] == (
        fact_action_ids[-4:]
    )
    assert (
        checkpoint.native_state_metadata["executor_fact_projection_sha256"]
        == payload["causal_fact_projection_sha256"]
    )
    assert (
        checkpoint.native_state_metadata["executor_fact_scope_digest"]
        == payload["causal_fact_scope_digest"]
    )
    assert payload["input_budget_fallback_used"] is True
    assert [item["recent_limit"] for item in payload["input_budget_fallbacks"]] == [
        12,
        8,
    ]


def test_stateful_input_budget_exhaustion_records_root_cause_and_blocks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-INPUT-BUDGET-BLOCK")
    session = ModelSession(_QueueClient([]), settings=_settings(progressive=True))
    model = LongHorizonModel(session, tool_selector=_selector(["write_file"]))

    def exceed_input_budget(*args, **kwargs):
        del args, kwargs
        raise InputBudgetError("injected irreducible bootstrap")

    monkeypatch.setattr(model, "next_command", exceed_input_budget)
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
        max_transitions=4,
    ).run(state.run_id)

    assert result.state.status.value == "blocked"
    assert result.state.actions == {}
    budget_events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "model_input_budget_exceeded"
    ]
    assert len(budget_events) == 1
    assert budget_events[0].payload["error_record"]["type"] == "InputBudgetError"
    terminal = result.state.causal_records[result.state.causal_order[-1]]
    assert terminal.event_type == "run_blocked"
    assert terminal.payload["reason"] == "model_input_budget_unresolvable"


def test_repeated_goal_io_failures_keep_step_until_actual_failure_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-IDENTICAL-FAILURE")
    (Path(state.goal.workspace_root) / "invalid.json").write_text("{}\n", encoding="utf-8")
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

    def injected_read_failure(*_args, **_kwargs):
        raise OSError("injected persistent read failure")

    model.harness._handlers["read_json"] = injected_read_failure
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
    assert len(result.state.actions) == controller._MAX_IDENTICAL_FAILURES
    assert len(selector._session.payloads) == 15
    assert sum(event.event_type == "goal_audit_boundary_opened" for event in events) == 4
    assert sum(event.event_type == "goal_audit_boundary_resolved" for event in events) == 4
    assert len(controller.supervisor.requests) == 1
    assert events[-1].event_type == "run_blocked"
    assert events[-1].payload["reason"] == "identical_failure_budget_exhausted"
    assert not any(event.event_type == "strong_planner_call_failed" for event in events)
    assert controller._pending_audit_boundary(result.state) is None


@pytest.mark.parametrize("resume_at_boundary", [False, True])
def test_transient_tool_failures_recover_on_same_step(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resume_at_boundary: bool,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "TRANSIENT-FAILURE-RECOVERY")
    (Path(state.goal.workspace_root) / "result.txt").write_text("verified\n")
    command = json.dumps({"function": "read_file", "params": {"path": "result.txt"}})
    queue = _QueueClient([command] * 3 + [
        json.dumps(_audit_call(
            "continue", step_id="S1", step_complete=True,
            evidence_refs=["A00003"], gaps=[], reason="the source was finally observed",
        )),
        json.dumps({"function": "final_answer", "params": {"text": "Recovered."}}),
        json.dumps(_audit_call(
            "ready_for_final", step_id="", step_complete=False,
            evidence_refs=["A00003"], gaps=[], reason="the successful read supports the answer",
        )),
    ])
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["read_file"] * 3),
    )
    original_handler = model.harness._handlers["read_file"]
    calls = 0

    def read_after_two_failures(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls <= 2:
            raise OSError("injected transient read failure")
        return original_handler(*args, **kwargs)

    model.harness._handlers["read_file"] = read_after_two_failures
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )
    planner = _StrongPlanner(_strong_observe_patch(state, "result.txt"))
    controller = StatefulGoalLoopController(
        store, model=model, harness=model.harness, supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=5 if resume_at_boundary else 20,
    )
    result = controller.run(state.run_id)
    if resume_at_boundary:
        assert result.state.status.value == "interrupted"
        assert len(result.state.actions) == 2
        controller = StatefulGoalLoopController(
            store, model=model, harness=model.harness, supervisor=planner,
            supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=20,
        )
        result = controller.run(state.run_id)
    assert result.state.status.value == "completed"
    assert len(result.state.actions) == 3
    assert len(planner.requests) == 1
    plan = rolling_goal_plan(result.state)
    assert len(plan.patch_ids) == 1
    assert plan.step_revisions["S1"] == 1
    assert controller._step_mechanical_evidence_coverage(
        result.state, "S1", 1,
    )["successful_action_ids"] == ["A00003"]


def test_read_only_step_repair_keeps_same_step_and_bounds_identical_repeats(
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
        _QueueClient(
            [
                zero_progress_command,
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="S1",
                        step_complete=False,
                        evidence_refs=["A00001"],
                        gaps=["phase_evidence_unproved:observe"],
                        reason="more evidence is required",
                    )
                ),
                zero_progress_command,
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="S1",
                        step_complete=False,
                        evidence_refs=["A00002"],
                        gaps=["phase_evidence_unproved:observe"],
                        reason="more evidence is required",
                    )
                ),
                zero_progress_command,
            ]
        ),
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
        supervisor=_StrongPlanner(_strong_observe_patch(state, "other.txt")),
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
    assert len(controller.supervisor.requests) == 1
    assert any(event.event_type == "run_blocked" and
               event.payload["reason"] == "identical_success_budget_exhausted"
               for event in events)
    assert controller._pending_audit_boundary(result.state) is None


def test_mutation_noop_repair_keeps_same_step_and_bounds_identical_repeats(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-IDENTICAL-MUTATION-NOOP")
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        "unchanged\n", encoding="utf-8"
    )
    zero_progress_command = json.dumps(
        {
            "function": "write_file",
            "params": {
                "path": "result.txt",
                "content": "unchanged\n",
                "overwrite": True,
                "create_parents": True,
            },
        }
    )
    session = ModelSession(
        _QueueClient(
            [
                zero_progress_command,
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="S1",
                        step_complete=False,
                        evidence_refs=[],
                        gaps=["phase_evidence_unproved:mutate"],
                        reason="the workspace did not change",
                    )
                ),
                zero_progress_command,
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="S1",
                        step_complete=False,
                        evidence_refs=[],
                        gaps=["phase_evidence_unproved:mutate"],
                        reason="the workspace did not change",
                    )
                ),
                zero_progress_command,
            ]
        ),
        settings=_settings(progressive=True),
    )
    selector = _selector(["write_file"] * 3)
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

    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "blocked"
    assert len(result.state.actions) == 3
    assert len(selector._session.payloads) == 9
    assert sum(event.event_type == "goal_audit_boundary_opened" for event in events) == 2
    assert sum(event.event_type == "goal_audit_boundary_resolved" for event in events) == 2
    assert len(controller.supervisor.requests) == 1
    assert any(event.event_type == "run_blocked" and
               event.payload["reason"] == "identical_success_budget_exhausted"
               for event in events)
    assert controller._pending_audit_boundary(result.state) is None


def test_successful_directory_observation_repair_can_read_next_without_replanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "ACTION-REPAIR-RECOVERY")
    (Path(state.goal.workspace_root) / "result.txt").write_text("verified content", encoding="utf-8")
    queue = _QueueClient(
        [
            json.dumps(
                {
                    "function": "list_directory",
                    "params": {"path": "."},
                }
            ),
            json.dumps(
                _audit_call(
                    "repair",
                    step_id="S1",
                    step_complete=False,
                    evidence_refs=["A00001"],
                    gaps=["phase_evidence_unproved:observe"],
                    reason="readback is required",
                )
            ),
            json.dumps(
                {"function": "read_file", "params": {"path": "result.txt"}}
            ),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00002"],
                    gaps=[],
                    reason="the current bytes were observed",
                )
            ),
            json.dumps(
                {"function": "final_answer", "params": {"text": "Recovered."}}
            ),
            json.dumps(
                _audit_call(
                    "ready_for_final",
                    step_id="",
                    step_complete=False,
                    evidence_refs=["A00002"],
                    gaps=[],
                    reason="the repaired plan is complete",
                )
            ),
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    selector = _selector(["list_directory", "read_file"])
    model = LongHorizonModel(session, tool_selector=selector)
    planner = _StrongPlanner(_strong_observe_patch(state))
    monkeypatch.setattr(
        StatefulGoalLoopController,
        "_validate_contract_patch_semantics",
        staticmethod(lambda *args, **kwargs: None),
    )

    result = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20,
    ).run(state.run_id)

    assert result.state.status.value == "completed"
    assert result.final_output == "Recovered."
    assert len(planner.requests) == 1
    assert [action.action_type for action in result.state.actions.values()] == ["list_directory", "read_file"]
    committed = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_plan_patch_committed"
    ]
    assert len(committed) == 1
    assert rolling_goal_plan(result.state).step_revisions["S1"] == 1

    selector_input = _role_prompt_payload(selector._session.payloads[3]["step"], selector_intent_v5.PROMPT_PREFIX)
    feedback = selector_input["current_progress"]["feedback"]
    assert feedback["issues"][0]["code"] == "phase_evidence_unproved:observe"
    assert feedback["issues"][0]["criterion"]
    executor_input = _role_prompt_payload(queue.prompts[2], executor_args_v5.PROMPT_PREFIX)
    assert executor_input["execution_state"]["feedback"] == feedback


@pytest.mark.parametrize("resume_at_boundary", [False, True])
def test_protocol_invalid_step_audit_keeps_plan_and_recovers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    resume_at_boundary: bool,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "AUDIT-PROTOCOL-REPAIR-RECOVERY")
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        "verified\n", encoding="utf-8"
    )
    queue = _QueueClient(
        [
            json.dumps(
                {"function": "read_file", "params": {"path": "result.txt"}}
            ),
            "{}",
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the exact bytes were observed",
                )
            ),
            json.dumps(
                {"function": "final_answer", "params": {"text": "Recovered."}}
            ),
            json.dumps(
                _audit_call(
                    "ready_for_final",
                    step_id="",
                    step_complete=False,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the repaired audit path is complete",
                )
            ),
        ]
    )
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["read_file"]),
    )
    planner = _StrongPlanner(_strong_observe_patch(state, "result.txt"))
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
        max_transitions=3 if resume_at_boundary else 20,
    )
    result = controller.run(state.run_id)
    if resume_at_boundary:
        assert result.state.status.value == "interrupted"
        assert result.state.protocol_rejections == 1
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
    assert len(planner.requests) == 1
    committed = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
        if result.state.causal_records[event_id].event_type
        == "goal_plan_patch_committed"
    ]
    assert len(committed) == 1
    assert rolling_goal_plan(result.state).step_revisions["S1"] == 1
    assert result.state.protocol_rejections == 1
    assert len(result.state.actions) == 1
    audit_starts = [event for event in result.state.causal_records.values() if event.event_type == "goal_auditor_session_started" and event.payload["auditor_role"] == "auditor_step"]
    assert len(audit_starts) == 2
    assert audit_starts[0].payload["audit_boundary_id"] == audit_starts[1].payload["audit_boundary_id"]
    assert audit_starts[0].payload["prompt_sha256"] != audit_starts[1].payload["prompt_sha256"]


def test_repeated_executor_provenance_rejection_recovers_without_replanning(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PROVENANCE-REPAIR-ROUTING")
    source = "VALUE = 'old'\n"
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        source, encoding="utf-8"
    )
    base_sha256 = hashlib.sha256(source.encode("utf-8")).hexdigest()
    initial = GoalPlanPatch(
        patch_id="GPP-provenance-initial",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Inspect result.txt",
                phase="observe",
                stage=1,
                success_evidence=("result.txt exact bytes are observed",),
                read_roots=("result.txt",),
            ),
            GoalPlanStep(
                step_id="S2",
                objective="Update result.txt from the observed exact bytes",
                phase="mutate",
                stage=2,
                depends_on=("S1",),
                success_evidence=("result.txt is updated",),
                write_roots=("result.txt",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect before exact read-modify-write",
    )
    invalid_replace = json.dumps(
        {
            "function": "replace_text",
            "params": {
                "path": "result.txt",
                "old": "VALUE = 'invented'",
                "new": "VALUE = 'new'",
                "base_sha256": base_sha256,
            },
        }
    )
    queue = _QueueClient(
        [
            json.dumps(
                {"function": "read_file", "params": {"path": "result.txt"}}
            ),
            json.dumps(
                _audit_call(
                    "continue",
                    step_id="S1",
                    step_complete=True,
                    evidence_refs=["A00001"],
                    gaps=[],
                    reason="the exact source bytes were observed",
                )
            ),
            invalid_replace,
            invalid_replace,
            json.dumps(
                {
                    "function": "replace_text",
                    "params": {
                        "path": "result.txt",
                        "old": "VALUE = 'old'",
                        "new": "VALUE = 'new'",
                        "base_sha256": base_sha256,
                    },
                }
            ),
            json.dumps(_audit_call(
                "continue", step_id="S2", step_complete=True,
                evidence_refs=["A00002"], gaps=[], reason="the requested bytes changed",
            )),
            json.dumps({"function": "final_answer", "params": {"text": "Updated."}}),
            json.dumps(_audit_call(
                "ready_for_final", step_id="", step_complete=False,
                evidence_refs=["A00001", "A00002"], gaps=[], reason="verified update",
            )),
        ]
    )
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["read_file", "replace_text", "replace_text"]),
    )
    planner = _StrongPlanner(initial)
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
    assert len(result.state.actions) == 2
    assert result.state.protocol_rejections == 2
    assert len(planner.requests) == 1
    assert len(rolling_goal_plan(result.state).patch_ids) == 1
    assert (Path(state.goal.workspace_root) / "result.txt").read_text() == "VALUE = 'new'\n"


def test_invalid_pre_final_audit_retries_same_candidate(
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

    result = controller.run(state.run_id)

    event_types = [
        result.state.causal_records[event_id].event_type
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "completed"
    assert result.final_output == "First unaudited candidate."
    assert event_types.count("goal_final_rejected") == 0
    assert event_types.count("goal_finalizer_session_started") == 1
    assert event_types.count("run_completed") == 1
    assert "run_yielded" not in event_types
    assert result.state.protocol_rejections == 1
    starts = [event for event in result.state.causal_records.values() if event.event_type == "goal_auditor_session_started" and event.payload["auditor_role"] == "auditor_final"]
    assert len(starts) == 2
    assert starts[0].payload["audit_boundary_id"] == starts[1].payload["audit_boundary_id"]
    assert starts[0].payload["prompt_sha256"] != starts[1].payload["prompt_sha256"]
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
        audit_prompt.removeprefix("AuditorStepPromptV4: ")
    )
    assert audit_payload["active_step"]["phase"] == "mutate"
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


def test_rwkv_step_auditor_rejects_gap_outside_visible_v3_catalog(
    tmp_path: Path,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "STATEFUL-AUDITOR-V3-GAP-BOUNDARY")
    patch = _strong_patch(state)
    audits: list[dict] = []
    session = ModelSession(
        _QueueClient([]),
        settings=_settings(),
        audit_hook=audits.append,
    )
    auditor_session = ModelSession(
        _QueueClient(
            [
                json.dumps(
                    _audit_call(
                        "repair",
                        step_id="S1",
                        step_complete=False,
                        evidence_refs=[],
                        gaps=["invented_gap:not_in_prompt"],
                        reason="evidence_incomplete",
                    )
                )
            ],
            model_name="test-rwkv-7.2b-auditor",
        ),
        settings=RuntimeSettings(
            **{**_settings().__dict__, "model": "test-rwkv-7.2b-auditor"}
        ),
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

    with pytest.raises(
        ModelProtocolError,
        match="repair gaps must be selected verbatim from gap_catalog codes",
    ):
        model.audit_goal_boundary(
            state,
            controller._persist_callback,
            boundary="observation_complete",
            active_step_id="S1",
            relevant_evidence_refs=(),
        )

    event_types = [
        state.causal_records[event_id].event_type for event_id in state.causal_order
    ]
    assert event_types.count("goal_audit_recorded") == 1
    assert event_types.count("goal_audit_rejected") == 1
    assert "goal_audit_accepted" not in event_types
    audit_checkpoint = next(
        checkpoint
        for checkpoint in state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.STEP_AUDIT
    )
    audit_prompt = audit_checkpoint.transcript.split("\n\nUser: ", 1)[1].split(
        "\n\n**Tool Call:**", 1
    )[0]
    audit_payload = json.loads(audit_prompt.removeprefix("AuditorStepPromptV4: "))
    visible_codes = {item["code"] for item in audit_payload["gap_catalog"]}
    assert "invented_gap:not_in_prompt" not in visible_codes


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
        tool_selector=_selector(["write_file"]),
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
    assert all("parent" not in payload for payload in selector_payloads)
    selector_checkpoints = [
        checkpoint
        for checkpoint in result.state.model_states.values()
        if checkpoint.lane_kind is ModelLaneKind.SELECTOR
    ]
    assert len(selector_checkpoints) == 3
    assert all(
        (checkpoint.native_state_metadata or {}).get("state_policy")
        == "fresh_initial_state_per_evaluation"
        for checkpoint in selector_checkpoints
    )
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
    selector = _selector(["write_file"])
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
    assert len(selector._session.payloads) == 3
    assert all("parent" not in payload for payload in selector._session.payloads)
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
    selector = _selector(["write_file", "write_file"])
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
    assert len(selector._session.payloads) == 6
    second_selection = json.loads(
        selector._session.payloads[3]["step"].removeprefix(
            "SelectorIntentPromptV5: "
        )
    )
    assert second_selection["current_progress"]["assigned_action_count"] == 0
    assert second_selection["current_progress"]["last_action"] is None
    assert second_selection["current_subtask"]["objective"] == (
        "Create result.txt with verified content"
    )
    retry_events = [
        event
        for event in result.state.model_events.values()
        if event.event_type == "protocol_rejection"
    ]
    assert len(retry_events) == 1
    assert queue.prompts[2].count("ExecutorArgsPromptV5: ") == 1
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


@pytest.mark.parametrize("failure_kind", ["nonretryable_http", "outcome_unknown", "invalid_transport_protocol"])
def test_stateful_runtime_failure_does_not_repeat_uncertain_or_rejected_model_work(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_kind: str,
) -> None:
    from rwkv_lh.runtime.protocol import RWKVHTTPError, RWKVOutcomeUnknownError, RWKVProtocolError
    errors = {"nonretryable_http": RWKVHTTPError(400, "invalid request recovery identity"),
        "outcome_unknown": RWKVOutcomeUnknownError("Native receipt unresolved"),
        "invalid_transport_protocol": RWKVProtocolError("Native binding differs")}
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "NO-NATIVE-RESUBMISSION")
    model = LongHorizonModel(ModelSession(_QueueClient([]), settings=_settings(progressive=True)),
        tool_selector=_selector(["write_file"] * 8))
    calls = []
    def rejected(*args, **kwargs):
        calls.append(True)
        raise errors[failure_kind]
    monkeypatch.setattr(model, "next_command", rejected)
    monkeypatch.setattr(StatefulGoalLoopController, "_transport_backoff", lambda *a: None)
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)), supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=20)
    result = controller.run(state.run_id)
    assert len(calls) == 1
    assert not result.state.actions
    assert result.state.status.value != "completed"
    failures = [event for event in result.state.causal_records.values() if event.event_type == "model_transport_failure"]
    assert len(failures) == 1 and failures[0].payload["retryable"] is False


def test_goal_audit_protocol_budget_stops_repeated_pre_final_cycle(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "GOAL-AUDIT-PROTOCOL-BUDGET")
    invalid_final_audit = json.dumps(
        _audit_call(
            "continue",
            step_id="S1",
            step_complete=True,
            evidence_refs=["A00001"],
            gaps=[],
            reason="incorrectly tries to complete a step at pre-final",
        )
    )
    final_attempts = [
        ModelCommand("final_answer", {"text": "same durable candidate"}).canonical,
        invalid_final_audit, invalid_final_audit, invalid_final_audit,
    ]
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
            *final_attempts,
        ]
    )
    session = ModelSession(queue, settings=_settings(progressive=True))
    model = LongHorizonModel(session, tool_selector=_selector(["write_file"]))
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
        max_transitions=40,
    ).run(state.run_id)

    assert result.state.status.value == "blocked"
    # Three visible retries exhaust the audit budget on one still-open boundary.
    assert result.state.protocol_rejections == 3
    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert sum(event.event_type == "goal_final_rejected" for event in events) == 0
    assert sum(event.event_type == "goal_finalizer_session_started" for event in events) == 1
    assert len(result.state.actions) == 1
    assert StatefulGoalLoopController._pending_audit_boundary(result.state) is not None
    goal_rejections = [
        event
        for event in events
        if event.event_type == "protocol_rejection_recorded"
        and event.payload["protocol_scope"] == "goal_audit"
    ]
    assert len(goal_rejections) == 3
    terminal = events[-1]
    assert terminal.event_type == "run_blocked"
    assert terminal.payload["reason"] == (
        "goal_audit_protocol_rejection_budget_exhausted"
    )


def test_semantic_final_audit_repair_has_a_fixed_identical_gap_budget(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "FINAL-AUDIT-SEMANTIC-BUDGET")
    repeated_finals: list[str] = []
    for index in range(4):
        repeated_finals.extend(
            [
                json.dumps(
                    {
                        "function": "final_answer",
                        "params": {"text": f"Verified candidate {index}."},
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
            ]
        )
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
            *repeated_finals,
        ]
    )
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["write_file"]),
    )
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
        max_transitions=20,
    ).run(state.run_id)

    events = [
        result.state.causal_records[event_id]
        for event_id in result.state.causal_order
    ]
    assert result.state.status.value == "blocked"
    assert sum(event.event_type == "goal_final_rejected" for event in events) == 3
    assert len(queue.outputs) == 2
    assert events[-1].event_type == "run_blocked"
    assert events[-1].payload["reason"] == (
        "identical_final_audit_rejection_budget_exhausted"
    )


def test_mechanical_repair_appends_failed_action_to_executor_state_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "FAILED-ACTION-OBSERVATION")
    patch = GoalPlanPatch(
        patch_id="GPP-failing-check",
        base_revision=0,
        add_steps=(
            GoalPlanStep(
                step_id="S1",
                objective="Run one observable command check",
                phase="execute",
                success_evidence=("the check exits with the expected code",),
            ),
        ),
        replace_steps=(),
        discard_step_ids=(),
        reason="Exercise the mechanical failure observation boundary",
    )
    model = LongHorizonModel(
        ModelSession(
            _QueueClient(
                [
                    json.dumps(
                        {
                            "function": "check_command",
                            "params": {
                                "argv": ["false"],
                                "cwd": ".",
                                "expected_exit_code": 0,
                            },
                        }
                    )
                ]
            ),
            settings=_settings(progressive=True),
        ),
        tool_selector=_selector(["check_command"]),
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
        supervisor=_StrongPlanner(patch),
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=3,
    )

    result = controller.run(state.run_id)

    assert result.state.actions["A00001"].status is ActionStatus.FAILED
    assert "EV-ACTION-A00001" in result.state.model_events
    assert controller._first_unappended_action_observation(result.state) is None
    appended = [
        event
        for event in result.state.causal_records.values()
        if event.event_type == "action_observation_appended"
        and event.payload.get("event_id") == "EV-ACTION-A00001"
    ]
    assert len(appended) == 1
    assert appended[0].payload["model_event"]["payload"]["result"]["success"] is False


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
        tool_selector=_selector(["write_file"]),
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
    first_input = _role_prompt_payload(session.client.prompts[2], finalizer_answer.PROMPT_PREFIX)
    repaired_input = _role_prompt_payload(session.client.prompts[4], finalizer_answer.PROMPT_PREFIX)
    assert first_input != repaired_input
    assert repaired_input["feedback"]["issues"][0]["code"] == "candidate_omits_required_result"
    assert "Unsupported first candidate." in repaired_input["feedback"]["rejected_output"]


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
        tool_selector=_selector(["write_file", "read_file"]),
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


@pytest.mark.parametrize("failure", ["wrong_field", "missing_initial_obligations"])
def test_planner_raw_parse_rejection_reaches_same_boundary_repair(
    tmp_path: Path, failure: str,
) -> None:
    from rwkv_lh.supervisor_openai import OpenAIGoalSupervisorClient, SupervisorAPISettings

    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "PLANNER-RAW-REPAIR")
    model = LongHorizonModel(
        ModelSession(_QueueClient([]), settings=_settings(progressive=True)),
        tool_selector=_selector([]),
    )
    patch = GoalPlanPatch(
        patch_id="GPP-provider-fixture", base_revision=0,
        goal_obligations=(GoalObligation("O1", "Workspace is inspected", ("observe",)),),
        add_steps=(GoalPlanStep(
            step_id="S1", objective="Inspect the workspace", phase="observe",
            obligation_ids=("O1",), read_roots=(".",),
            success_evidence=("Workspace entries are observed",),
        ),), replace_steps=(), discard_step_ids=(), reason="Inspect current evidence",
    )
    valid = patch.to_dict()
    for key in ("schema_version", "patch_id", "base_revision"):
        valid.pop(key)
    for stage in valid["add_stages"]:
        for step in stage["steps"]:
            step.pop("allowed_operations")
    invalid = deepcopy(valid)
    if failure == "wrong_field":
        obligation = invalid["goal_obligations"][0]
        obligation["observable_predicate"] = obligation.pop("predicate")
    else:
        invalid["goal_obligations"] = []

    class ProviderSession:
        def __init__(self):
            self.posts = []
            self.outputs = [invalid, valid]

        def post(self, url, **kwargs):
            self.posts.append(kwargs["json"])
            value = self.outputs.pop(0)
            return SimpleNamespace(status_code=200, json=lambda: {
                "model": "strong-fixture",
                "choices": [{"finish_reason": "stop", "message": {
                    "role": "assistant", "content": json.dumps(value),
                }}],
            })

    session = ProviderSession()
    planner = OpenAIGoalSupervisorClient(SupervisorAPISettings(
        base_url="https://planner.invalid/v1", api_key="fixture-only",
        model="strong-fixture", stage_checker_model="strong-fixture",
        retry_attempts=2, plan_cache_enabled=False,
    ), session=session)
    controller = StatefulGoalLoopController(
        store, model=model, harness=model.harness, supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=4,
    )

    result = controller._issue_strong_plan_patch(
        state, plan=rolling_goal_plan(state), transitions=0,
    )

    assert result is None
    assert len(session.posts) == 2
    first = json.loads(session.posts[0]["messages"][-1]["content"])
    second = json.loads(session.posts[1]["messages"][-1]["content"])
    assert "local_validation_repair" not in first
    assert second["local_validation_repair"]["rejected_patch"] == invalid
    assert second["active_plan"] == first["active_plan"]
    assert list(second)[-1] == "local_validation_repair"
    events = [state.causal_records[key] for key in state.causal_order]
    rejected = [event for event in events if event.event_type == "strong_planner_patch_rejected"]
    assert len(rejected) == 1
    assert rejected[0].payload["rejected_patch"] == invalid
    assert not any(event.event_type == "strong_planner_call_failed" for event in events)
    committed = [event for event in events if event.event_type == "goal_plan_patch_committed"]
    assert len(committed) == 1
    assert committed[0].payload["patch"]["goal_obligations"] == valid["goal_obligations"]
    assert not state.actions


def test_goal_planner_transport_pending_is_durable_and_resolved_on_reentry(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    goal = GoalState.create(
        request="Create result.txt.",
        constraints=(),
        workspace_root=workspace,
        runtime_policy=runtime_policy_document(
            RetrievalRuntimeConfig(mode=NetworkPolicyMode.OFFLINE),
            supervisor_mode="stateful_goal",
            execution_mode="goal",
        ),
    )
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(goal, "GOAL-PLANNER-TRANSPORT-RESUME")
    model = LongHorizonModel(
        ModelSession(_QueueClient([]), settings=_settings(progressive=True)),
        tool_selector=_selector([]),
    )
    planner = _ScriptedStrongPlanner(
        (RuntimeError("temporary planner transport failure"), _strong_patch(state))
    )
    controller = StatefulGoalLoopController(
        store,
        model=model,
        harness=model.harness,
        supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=1,
    )

    first = controller.run(state.run_id)

    assert first.state.status.value == "running"
    assert len(unresolved_supervisor_pending(first.state)) == 1
    assert first.state.causal_records[first.state.causal_order[-1]].event_type == (
        "run_yielded"
    )

    # Retry the exact durable planner boundary. The benchmark lifecycle test
    # separately proves that a RUNNING+run_yielded state is eligible for this
    # re-entry; this unit stays isolated from Executor/Selector behavior.
    second_boundary = controller._issue_strong_plan_patch(
        first.state,
        plan=rolling_goal_plan(first.state),
        transitions=0,
    )

    assert len(planner.requests) == 2
    assert second_boundary is None
    assert unresolved_supervisor_pending(first.state) == ()
    event_types = [
        first.state.causal_records[event_id].event_type
        for event_id in first.state.causal_order
    ]
    assert event_types.count("supervisor_call_pending") == 1
    assert event_types.count("supervisor_call_resolved") == 1
    assert event_types.count("goal_plan_patch_committed") == 1


def test_goal_stage_checker_transport_pending_resolves_after_response(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    class RecoveringStagePlanner(_StrongPlanner):
        def review_goal_stage(self, request):
            if not self.stage_review_requests:
                self.stage_review_requests.append(request)
                raise RuntimeError("temporary stage checker transport failure")
            return super().review_goal_stage(request)

    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "GOAL-STAGE-TRANSPORT-RESUME")
    queue = _QueueClient([
        ModelCommand("write_file", {"path": "result.txt", "content": "verified"}).canonical,
        json.dumps(_audit_call("continue", step_id="S1", step_complete=True,
            evidence_refs=["A00001"], gaps=[], reason="written")),
        ModelCommand("final_answer", {"text": "Created result.txt."}).canonical,
        json.dumps(_audit_call("ready_for_final", step_id="", step_complete=False,
            evidence_refs=["A00001"], gaps=[], reason="complete")),
    ])
    model = LongHorizonModel(ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["write_file"]))
    planner = RecoveringStagePlanner(_strong_patch(state))
    monkeypatch.setattr(StatefulGoalLoopController, "_validate_contract_patch_semantics",
        staticmethod(lambda *a, **kw: None))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=planner, supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=20)
    first = controller.run(state.run_id)
    assert first.state.status.value == "interrupted"
    assert len(unresolved_supervisor_pending(first.state)) == 1
    assert len(first.state.actions) == 1
    recovered = controller.run(state.run_id)
    assert recovered.state.status.value == "completed"
    assert len(recovered.state.actions) == 1
    assert unresolved_supervisor_pending(recovered.state) == ()
    events = [recovered.state.causal_records[key] for key in recovered.state.causal_order]
    assert sum(event.event_type == "supervisor_call_pending" for event in events) == 1
    assert sum(event.event_type == "supervisor_call_resolved" for event in events) == 1
    assert [item["action_id"] for item in planner.stage_review_requests[-1].recent_action_facts] == ["A00001"]


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
    (Path(state.goal.workspace_root) / "result.txt").write_text(
        "preexisting\n",
        encoding="utf-8",
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
        tool_selector=_selector(["write_file", "write_file"]),
    )
    real_execute = model.harness.execute
    execute_count = 0

    def fail_first_execution(action, goal):
        nonlocal execute_count
        execute_count += 1
        if execute_count == 1:
            return ActionResult(
                "write_file",
                False,
                error={
                    "type": "InjectedWriteFailure",
                    "message": "injected first write failure",
                },
            )
        return real_execute(action, goal)

    monkeypatch.setattr(model.harness, "execute", fail_first_execution)
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
    assert len(eligible_labels) == 6
    assert all("final_answer" not in labels for labels in eligible_labels)
    selector_payloads = model.tool_selector._session.payloads
    assert all("parent" not in payload for payload in selector_payloads)
    second_step = json.loads(
        selector_payloads[3]["step"].removeprefix("SelectorIntentPromptV5: ")
    )
    first_step = json.loads(
        selector_payloads[0]["step"].removeprefix("SelectorIntentPromptV5: ")
    )
    assert second_step["current_subtask"] == first_step["current_subtask"]
    assert first_step["current_progress"]["assigned_action_count"] == 0
    progress = second_step["current_progress"]
    assert progress["assigned_action_count"] == 1
    assert progress["successful_action_count"] == 0
    assert progress["failed_action_count"] == 1
    last_action = progress["last_action"]
    assert last_action["operation"] == "write_file"
    assert last_action["status"] == "failed"
    assert last_action["arguments"] == {
        "content": "verified", "path": "result.txt",
        "overwrite": "true", "create_parents": "true",
    }
    assert last_action["error_type"] == "InjectedWriteFailure"
    assert last_action["error_message"] == "injected first write failure"
    assert last_action["result_metadata"] == {"outcome_type": "failed"}
    assert last_action["observed_roots"] == []
    assert last_action["mutated_roots"] == []
    assert progress["missing_read_roots"] == []
    assert progress["missing_write_roots"] == ["result.txt"]
    assert progress["workspace_targets"] == [{"path": "result.txt", "target_kind": "text_file"}]
    assert progress["completion_preconditions_satisfied"] is False
    second_executor_prompt = session.client.prompts[1]
    assert "ExecutorArgsPromptV5: " in second_executor_prompt
    assert '"error_type":"InjectedWriteFailure"' in second_executor_prompt
    assert '"error_message":"injected first write failure"' in second_executor_prompt
    assert '"target_kind":"text_file"' in second_executor_prompt
    assert '"write_file":["result.txt"]' in second_executor_prompt
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
            GoalPlanStep(phase="observe",
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


def _large_controller_plan_steps(
    state, *, two_stages: bool,
) -> tuple[GoalPlanStep, ...]:
    """Use real workspace roots and the production plan dataclasses."""
    workspace = Path(state.goal.workspace_root)
    steps = []
    for index in range(1, 20):
        root = f"source-{index}.txt"
        (workspace / root).write_text(f"Source {index} observed\n", encoding="utf-8")
        later_stage = two_stages and index > 10
        steps.append(GoalPlanStep(
            step_id=f"S{index:02d}",
            objective=f"Inspect source {index}",
            phase="observe",
            stage=2 if later_stage else 1,
            depends_on=tuple(f"S{prior:02d}" for prior in range(1, 11))
            if later_stage else (),
            obligation_ids=("O1",),
            success_evidence=(f"Source {index} has successful observation evidence",),
            read_roots=(root,),
        ))
    return tuple(steps)


def _large_controller_initial_patch(
    steps: tuple[GoalPlanStep, ...],
) -> GoalPlanPatch:
    return GoalPlanPatch(
        patch_id="GPP-large-initial",
        base_revision=0,
        add_steps=steps,
        replace_steps=(),
        discard_step_ids=(),
        reason="Inspect every requested source",
        goal_obligations=(GoalObligation(
            obligation_id="O1",
            predicate="Every requested source is inspected",
            required_phases=("observe",),
        ),),
    )


def test_large_goal_controller_persists_full_plan_and_rejects_invalid_revision(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "LARGE-PLAN-DURABLE")
    steps = _large_controller_plan_steps(state, two_stages=True)
    initial = _large_controller_initial_patch(steps)
    replacement = GoalPlanPatch(
        patch_id="GPP-large-replace", base_revision=1, add_steps=(),
        replace_steps=tuple(
            replace(step, objective=f"Inspect revised {step.step_id}")
            for step in steps[10:]
        ),
        discard_step_ids=(), reason="Revise all nine later-stage observations",
    )
    discard = GoalPlanPatch(
        patch_id="GPP-large-discard", base_revision=2, add_steps=(),
        replace_steps=(), discard_step_ids=tuple(step.step_id for step in steps[11:]),
        reason="Remove eight superseded later-stage observations",
    )
    invalid = GoalPlanPatch(
        patch_id="GPP-large-invalid", base_revision=3, add_steps=(),
        replace_steps=(replace(steps[0], depends_on=("missing",)),),
        discard_step_ids=(), reason="Invalid dependency must not reach durable state",
    )
    planner = _StrongPlanner((initial, replacement, discard, invalid))
    planner.semantic_repair_attempts = 0
    queue = _QueueClient([])
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector([]),
    )
    controller = StatefulGoalLoopController(
        store, model=model, harness=model.harness, supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=1,
    )

    for revision, patch in enumerate((initial, replacement, discard), start=1):
        assert controller._issue_strong_plan_patch(
            state, plan=rolling_goal_plan(state), transitions=0,
        ) is None
        # Reload the durable store after every Controller commit; an in-memory
        # candidate alone cannot prove that complete plans survive persistence.
        state = store.load(state.run_id)
        plan = rolling_goal_plan(state)
        expected_steps = steps if revision < 3 else steps[:11]
        assert tuple(plan.steps) == tuple(step.step_id for step in expected_steps)
        assert {step_id: step.stage for step_id, step in plan.steps.items()} == {
            step.step_id: step.stage for step in expected_steps
        }
        assert plan.step_revisions == {
            step.step_id: 2 if revision >= 2 and step.stage == 2 else 1
            for step in expected_steps
        }
        assert plan.steps["S11"].depends_on == tuple(
            step.step_id for step in steps[:10]
        )
        if revision >= 2:
            assert plan.steps["S11"].objective == "Inspect revised S11"
        assert plan.patch_ids == [
            item.patch_id for item in (initial, replacement, discard)[:revision]
        ]
        assert plan.discarded_step_ids == (
            set(discard.discard_step_ids) if revision == 3 else set()
        )
        assert not plan.batch_complete
        assert not plan.complete
        assert state.status.value != "completed"
        assert not state.final_output
        committed = [
            event for event in store.event_records(state.run_id)
            if event["type"] == "goal_plan_patch_committed"
        ]
        assert len(committed) == revision
        assert committed[-1]["data"]["plan_revision"] == revision
        assert committed[-1]["data"]["patch"] == patch.to_dict()

    before = plan.to_model_dict()
    before_revisions = dict(plan.step_revisions)
    before_discarded = set(plan.discarded_step_ids)
    rejected = controller._issue_strong_plan_patch(state, plan=plan, transitions=0)
    assert rejected is not None
    assert plan.to_model_dict() == before
    state = store.load(state.run_id)
    durable_plan = rolling_goal_plan(state)
    assert durable_plan.to_model_dict() == before
    assert durable_plan.step_revisions == before_revisions
    assert durable_plan.discarded_step_ids == before_discarded
    assert invalid.patch_id not in durable_plan.patch_ids
    events = store.event_records(state.run_id)
    assert sum(event["type"] == "goal_plan_patch_committed" for event in events) == 3
    rejection = [event for event in events if event["type"] == "strong_planner_patch_rejected"]
    assert len(rejection) == 1
    assert "unknown steps" in rejection[0]["data"]["error"]["message"]
    assert "missing" in rejection[0]["data"]["error"]["message"]
    assert rejection[0]["data"]["rejected_patch"] == invalid.to_dict()
    assert [request.plan_revision for request in planner.requests] == [0, 1, 2, 3]
    assert not any(event["type"] == "run_completed" for event in events)
    assert state.status.value != "completed"
    assert not state.final_output
    assert queue.prompts == []


def test_large_goal_controller_stage_review_keeps_all_refs_and_bounded_facts(
    tmp_path: Path,
) -> None:
    from dataclasses import replace

    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(_goal(tmp_path), "LARGE-STAGE-REVIEW-DURABLE")
    steps = _large_controller_plan_steps(state, two_stages=False)
    initial = _large_controller_initial_patch(steps)
    replacement = GoalPlanPatch(
        patch_id="GPP-large-stage-replace", base_revision=1, add_steps=(),
        replace_steps=(replace(steps[-1], objective="Inspect the revised final source"),),
        discard_step_ids=(), reason="Revise one peer before gathering evidence",
    )
    planner = _StrongPlanner((initial, replacement))
    # ModelCommand provides the production wire representation. Every model
    # response is supplied locally; the Harness still performs real file reads.
    queue = _QueueClient([
        ModelCommand("read_file", {"path": step.read_roots[0]}).canonical
        for step in steps
    ])
    model = LongHorizonModel(
        ModelSession(queue, settings=_settings(progressive=True)),
        tool_selector=_selector(["read_file"] * len(steps)),
    )
    controller = StatefulGoalLoopController(
        store, model=model, harness=model.harness, supervisor=planner,
        supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=1,
    )
    for _ in (initial, replacement):
        assert controller._issue_strong_plan_patch(
            state, plan=rolling_goal_plan(state), transitions=0,
        ) is None
        state = store.load(state.run_id)

    action_ids = []
    for index, step in enumerate(steps, start=1):
        plan = rolling_goal_plan(state)
        assert not plan.batch_complete
        active_step = plan.steps[step.step_id]
        step_revision = plan.step_revisions[step.step_id]
        mechanical_evidence = controller._step_mechanical_evidence_coverage(
            state, step.step_id, step_revision,
        )
        eligible_operations, target_contract = controller._goal_step_operation_contract(
            state, active_step, mechanical_evidence=mechanical_evidence,
        )
        selector_progress = controller._selector_current_progress(
            state, step.step_id, step_revision, mechanical_evidence,
            target_contract=target_contract,
        )
        decision = model.next_command(
            state, controller._persist_callback, eligible_operations=eligible_operations,
            selector_stage_context=goal_frontier_selector_context(
                active_step.to_dict(), current_progress=selector_progress,
            ),
            current_requirement=active_step.objective,
            executor_fact_action_ids=controller._step_executor_fact_action_ids(
                state, step.step_id, step_revision,
            ),
            executor_execution_state=controller._executor_execution_state(
                state, step.step_id, step_revision, mechanical_evidence,
                effective_phase=active_step.phase, target_contract=target_contract,
            ),
        )
        action = controller._execute_decision(state, decision)
        assert action.status is ActionStatus.SUCCEEDED
        action_ids.append(action.action_id)
        controller._persist(
            state, "goal_action_plan_step_assigned",
            {
                "action_id": action.action_id,
                "step_id": step.step_id,
                "step_revision": plan.step_revisions[step.step_id],
                "strong_planner_patch_ids": list(plan.patch_ids),
            },
            subject_id=action.action_id,
        )
        refs = (action.action_id,)
        audit = GoalAuditDecision(
            audit_id=f"AUD-large-{index}", verdict=GoalAuditVerdict.CONTINUE,
            step_id=step.step_id, evidence_refs=refs, gaps=(),
            completed_steps=(AuditedStep(step.step_id, refs),),
            reason="The assigned source has a successful Harness observation",
        )
        validate_audit_authority(
            state, plan, audit, final_candidate=False,
            active_step_id=step.step_id, allowed_evidence_refs=refs,
        )
        controller._persist(
            state, "goal_audit_accepted",
            {"audit_id": audit.audit_id, "audit": audit.to_dict(), "kernel_validated": True},
            subject_id=audit.audit_id,
        )
        state = store.load(state.run_id)
        plan = rolling_goal_plan(state)
        assert plan.batch_complete == (index == len(steps))
        assert state.status.value != "completed"
        assert not state.final_output

    assert plan.complete
    assert controller._next_unreviewed_completed_stage(state, plan) == (
        1, plan.stage_boundary_key(1),
    )
    review = controller._issue_strong_stage_review(
        state, plan=plan, stage=1, stage_boundary_key=plan.stage_boundary_key(1),
        transitions=0,
    )
    assert isinstance(review, GoalStageReview)
    assert len(planner.stage_review_requests) == 1
    request = planner.stage_review_requests[0]
    expected_ids = tuple(step.step_id for step in steps)
    assert tuple(item["step_id"] for item in request.stage_steps) == expected_ids
    assert tuple(item["step_revision"] for item in request.stage_steps) == (1,) * 18 + (2,)
    assert tuple(tuple(item["accepted_evidence_refs"]) for item in request.stage_steps) == tuple(
        (action_id,) for action_id in action_ids
    )
    assert tuple(fact["action_id"] for fact in request.recent_action_facts) == tuple(action_ids)
    assert len(request.recent_action_facts) == len(steps)
    assert review.reviewed_step_ids == expected_ids
    assert review.evidence_refs == tuple(action_ids)
    state = store.load(state.run_id)
    durable_plan = rolling_goal_plan(state)
    assert durable_plan.step_revisions == plan.step_revisions
    assert durable_plan.completed_evidence == plan.completed_evidence
    assert controller._next_unreviewed_completed_stage(state, durable_plan) is None
    events = store.event_records(state.run_id)
    committed = [event for event in events if event["type"] == "goal_stage_review_committed"]
    assert len(committed) == 1
    assert committed[0]["data"]["review"] == review.to_dict()
    # Completed steps and a Strong stage ADVANCE never replace an explicit
    # RWKV final decision or authorize Controller completion by plan size.
    assert not any(event["type"] == "run_completed" for event in events)
    assert state.status.value != "completed"
    assert not state.final_output
    assert len(queue.prompts) == len(steps)
