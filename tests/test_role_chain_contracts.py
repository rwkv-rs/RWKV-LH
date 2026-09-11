"""Engineering regression cases, never role training examples."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from rwkv_lh.goal_loop_protocol import GoalPlanStep
from rwkv_lh.model import LongHorizonModel, ModelProtocolError
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.model_session import ModelSession
from rwkv_lh.schema import GoalState
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.supervisor import SupervisorPolicy
from test_stateful_goal_loop import _QueueClient, _StrongPlanner, _selector, _settings
from test_role_trace_inputs import controller_role_snapshots


def setup_scope(tmp_path, roots=("output",)):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(GoalState.create(request="Produce an output", constraints=(),
        workspace_root=workspace), "ROLE-CHAIN-CONTRACT")
    model = LongHorizonModel(ModelSession(_QueueClient([]), settings=_settings(progressive=True)),
        tool_selector=_selector([]))
    controller = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(), supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=1)
    step = GoalPlanStep(step_id="S1", objective="Produce the output", phase="mutate",
        write_roots=roots, success_evidence=("output produced",))
    return controller, state, step


def test_empty_workspace_excludes_tools_that_require_existing_sources(tmp_path):
    controller, state, step = setup_scope(tmp_path)
    operations, _ = controller._goal_step_operation_contract(state, step)
    assert "write_file" in operations
    assert {"copy_file", "move_file"}.isdisjoint(operations)


def test_copy_source_can_be_outside_write_scope_but_move_source_cannot(tmp_path):
    controller, state, step = setup_scope(tmp_path)
    (Path(state.goal.workspace_root) / "source").write_text("keep this")
    operations, contract = controller._goal_step_operation_contract(state, step)
    assert "copy_file" in operations
    for operation in ("copy_file", "move_file"):
        decision = SimpleNamespace(command=ModelCommand(operation, {"source": "source", "destination": "output"}),
            decision=SimpleNamespace(decision_id="D1", request_id="MR1", tool_selection_id="SEL1"))
        if operation == "move_file":
            with pytest.raises(ModelProtocolError, match="source.*outside"):
                controller._validate_decision_target_contract(state, decision, contract)
        else:
            controller._validate_decision_target_contract(state, decision, contract)
    assert "move_file" not in operations
    assert (Path(state.goal.workspace_root) / "source").read_text() == "keep this"


def test_incomplete_source_discovery_keeps_unknown_eligibility(tmp_path):
    controller, state, step = setup_scope(tmp_path, roots=(".",))
    (Path(state.goal.workspace_root) / ".git").mkdir()
    operations, contract = controller._goal_step_operation_contract(state, step)
    assert contract["discovery_complete"] is False
    assert {"copy_file", "move_file"} <= set(operations)


def test_large_discovery_does_not_flood_role_handoffs(tmp_path):
    import json
    from rwkv_lh.goal_state_protocols import executor_args_v7, selector_intent_v7
    from rwkv_lh.token_budget import get_token_count
    controller, state, step = setup_scope(tmp_path, roots=(".",))
    for index in range(300):
        (Path(state.goal.workspace_root) / f"item-{index:04d}").write_text("input fact")
    _, contract = controller._goal_step_operation_contract(state, step)
    execution = executor_args_v7.build_execution_state(active_step_id="S1", active_step_revision=1,
        declared_phase="mutate", effective_phase="mutate", assigned_actions=[], mechanical_evidence={}, target_contract=contract)
    source = executor_args_v7.build_prompt_source(immutable_goal=state.goal.request, current_requirement=step.objective,
        execution_state=execution, selected_operation="write_file", selected_tool_contract=controller.model._definitions_by_name["write_file"],
        committed_fact_refs=[], executor_history=[])
    progress = selector_intent_v7.build_current_progress(assigned_actions=[], read_roots=[], write_roots=step.write_roots,
        mechanical_evidence={}, target_descriptors=contract["target_descriptors"], action_observes_root=lambda *_: False,
        action_mutates_root=lambda *_: False, discovery_complete=contract["discovery_complete"],
        operation_targets=contract["argument_targets_by_operation"])
    assert get_token_count(executor_args_v7.render_generation_prompt(source)) < 8192
    assert get_token_count(json.dumps(progress)) < 8192
    assert set(source["execution_state"]["target_contract"]["argument_targets_by_operation"]) == {"write_file"}
    assert source["execution_state"]["target_contract"]["discovery_complete"] is False
    assert len(contract["target_descriptors"]) == 256


@pytest.mark.parametrize("role", ["executor_args", "auditor_step"])
def test_current_role_input_preserves_original_requirement(controller_role_snapshots, role):
    from rwkv_lh.role_trace_inputs import rebuild_role_input
    snapshots, final = controller_role_snapshots
    for state in snapshots:
        event = state.causal_records[state.causal_order[-1]]
        if (role == "executor_args" and event.event_type == "tool_schema_disclosed"
            or role == "auditor_step" and event.event_type == "goal_auditor_session_started"
            and event.payload["auditor_role"] == role):
            rebuilt = rebuild_role_input(role, state, {"boundary_event_id": event.event_id,
                "checkpoint_id": event.payload["checkpoint_id"]})
            assert rebuilt["prompt_source"].get("immutable_goal") == final.goal.request
            assert rebuilt["expected_checkpoint_transcript"] == state.model_states[event.payload["checkpoint_id"]].transcript
            return
    pytest.fail("role boundary was not reached")


def test_executor_can_author_new_content_while_copying_observed_literals_exactly():
    from test_goal_state_protocols import _executor_source
    from rwkv_lh.goal_state_protocols import executor_args_v7
    source = _executor_source()
    prompt = executor_args_v7.render_prompt(source)
    assert "Create new content from immutable_goal" in prompt
    assert "Copy code, text" not in prompt
    assert "base_sha256" in prompt


def test_selector_handoff_is_durable_before_native_executor_allocation(tmp_path, monkeypatch):
    from test_model_session import FakeNativeStateClient, settings
    from test_stateful_goal_loop import _strong_patch
    from rwkv_lh.model_session import NativeRWKVModelSession
    from rwkv_lh.runtime.protocol import RWKVHTTPError
    from dataclasses import replace
    client = FakeNativeStateClient([])
    native = NativeRWKVModelSession(client, settings=replace(settings(state_transport="native_rwkv",
        state_profile_id="zero", state_profile_sha256="0" * 64, model_sha256="a" * 64), tool_disclosure_mode="progressive"))
    selector = _selector(["write_file"])
    model = LongHorizonModel(native, tool_selector=selector,
        step_auditor_session=ModelSession(_QueueClient([]), settings=replace(_settings(progressive=True), state_profile_id="zero", state_profile_sha256="0" * 64)),
        finalizer_session=ModelSession(_QueueClient([]), settings=replace(_settings(progressive=True), state_profile_id="zero", state_profile_sha256="0" * 64)),
        final_auditor_session=ModelSession(_QueueClient([]), settings=replace(_settings(progressive=True), state_profile_id="zero", state_profile_sha256="0" * 64)))
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(GoalState.create(request="Create result.txt with verified content",
        constraints=(), workspace_root=workspace), "NATIVE-HANDOFF-ORDER")
    monkeypatch.setattr(StatefulGoalLoopController, "_validate_contract_patch_semantics", staticmethod(lambda *a, **kw: None))

    def unavailable(**kwargs):
        raise RWKVHTTPError(503, "allocation unavailable", retryable=False)

    monkeypatch.setattr(client, "state_create", unavailable)
    result = StatefulGoalLoopController(store, model=model, harness=model.harness,
        supervisor=_StrongPlanner(_strong_patch(state)), supervisor_policy=SupervisorPolicy(mode="static"),
        max_transitions=10).run(state.run_id)
    assert len(selector._session.payloads) == 3
    assert result.state.pending_selection_id
    assert len(result.state.tool_selections) == 1
    assert not result.state.actions


@pytest.mark.parametrize("role", ["auditor_step", "finalizer_answer", "auditor_final"])
def test_independent_role_does_not_materialize_executor_cache(controller_role_snapshots, monkeypatch, role):
    import json
    from test_stateful_goal_loop import _audit_call
    snapshots, _ = controller_role_snapshots
    target_type = "goal_finalizer_session_started" if role == "finalizer_answer" else "goal_auditor_session_started"
    state = next(state for state in snapshots if state.causal_records[state.causal_order[-1]].event_type == target_type
        and (role == "finalizer_answer" or state.causal_records[state.causal_order[-1]].payload["auditor_role"] == role))
    output = ModelCommand("final_answer", {"text": "Created result.txt."}).canonical if role == "finalizer_answer" else json.dumps(_audit_call(
        "continue" if role == "auditor_step" else "ready_for_final",
        step_id="S1" if role == "auditor_step" else "", step_complete=role == "auditor_step",
        evidence_refs=["A00001"], gaps=[], reason="Evidence complete"))
    model = LongHorizonModel(ModelSession(_QueueClient([output]), settings=_settings(progressive=True)), tool_selector=_selector([]))
    def forbidden(*args, **kwargs):
        pytest.fail("independent role accessed Executor cache")
    monkeypatch.setattr(model, "_checkpoint", forbidden)
    monkeypatch.setattr(model, "_append_event", forbidden)
    persist = lambda *args, **kwargs: None
    if role == "finalizer_answer":
        model.finalize_goal_answer(state, persist)
    else:
        model.audit_goal_boundary(state, persist, boundary="mutation_transaction_complete" if role == "auditor_step" else "pre_final",
            active_step_id="S1" if role == "auditor_step" else "", final_candidate=role == "auditor_final",
            final_candidate_command=ModelCommand("final_answer", {"text": "Created result.txt."}) if role == "auditor_final" else None,
            relevant_evidence_refs=["A00001"])
