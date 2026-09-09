"""Input reconstruction fixtures; these are not production training records."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_SELECTOR_MENU_ORDER_IDS
from rwkv_lh.goal_loop_protocol import GoalPlanPatch, GoalPlanStep
from rwkv_lh.goal_state_protocols import selector_intent_v5
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.role_trace_inputs import RoleInputReconstructionError, rebuild_role_input
from rwkv_lh.schema import CausalEventDraft, GoalState
from rwkv_lh.stateful_goal_loop import StatefulGoalLoopController
from rwkv_lh.store import LongHorizonStore


def _selector_boundary(tmp_path: Path):
    from rwkv_lh.goal_state_protocols import executor_args_v5

    workspace = tmp_path / "workspace"
    workspace.mkdir()
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(GoalState.create(
        request="Read the JSON document", constraints=(), workspace_root=workspace,
    ), "TRACE-INPUT-FIXTURE")
    patch = GoalPlanPatch(
        patch_id="P1", base_revision=0,
        add_steps=(GoalPlanStep(
            step_id="S1", objective="Read the JSON document", phase="observe",
            read_roots=("data.json",), success_evidence=("JSON observed",),
            allowed_operations=("read_json",),
        ),), replace_steps=(), discard_step_ids=(), reason="Fixture plan",
    )
    state = store.save(state, causal_event=CausalEventDraft.create(
        "goal_plan_patch_committed", {"patch": patch.to_dict()}, subject_id="P1",
    ))
    mechanical = StatefulGoalLoopController._step_mechanical_evidence_coverage(state, "S1", 1)
    contract = executor_args_v5.build_target_contract(
        phase="observe", roots=("data.json",),
        target_descriptors=({"path": "data.json", "type": "file", "target_kind": "json_file", "exists": True},),
        compatible_targets_by_operation={"read_json": ["data.json"]},
    )
    execution = StatefulGoalLoopController._executor_execution_state(
        state, "S1", 1, mechanical, effective_phase="observe", target_contract=contract,
    )
    payload = dict(
        active_step_id="S1", active_step_revision=1, effective_phase="observe",
        eligible_operations=["read_json"], target_contract=contract,
        mechanical_evidence_sha256=canonical_digest(mechanical),
        executor_execution_state=execution,
    )
    state = store.save(state, causal_event=CausalEventDraft.create(
        "goal_role_input_boundary", payload, subject_id="S1",
    ))
    return store, state


def test_selector_rebuilds_three_production_menus_from_durable_boundary(tmp_path: Path):
    store, state = _selector_boundary(tmp_path)
    restored = store.load(state.run_id)
    assert restored.causal_order == state.causal_order
    prompts = []
    for menu_id in NETWORK_SELECTOR_MENU_ORDER_IDS:
        result = rebuild_role_input("selector_intent", restored, {
            "boundary_event_id": restored.causal_order[-1], "menu_order_id": menu_id,
        })
        assert result["protocol_version"] == selector_intent_v5.INPUT_SCHEMA_VERSION
        assert result["protocol_prompt"] == selector_intent_v5.render_prompt(result["prompt_source"])
        assert result["prompt_source"]["current_progress"]["missing_read_roots"] == ["data.json"]
        assert result["coverage"]["json_root"] is True
        prompts.append(result["bootstrap_prompt"])
    assert len(set(prompts)) == 3


def test_rejects_final_state_at_an_earlier_boundary(tmp_path: Path):
    store, state = _selector_boundary(tmp_path)
    boundary = state.causal_order[-1]
    state = store.save(state, causal_event=CausalEventDraft.create(
        "goal_step_evidence_gap_recorded", {"reason": "later fixture event"}, subject_id="S1",
    ))
    with pytest.raises(RoleInputReconstructionError, match="snapshot"):
        rebuild_role_input("selector_intent", state, {"boundary_event_id": boundary})


def test_rejects_persisted_execution_state_that_disagrees_with_actions(tmp_path: Path):
    _store, state = _selector_boundary(tmp_path)
    altered = deepcopy(state)
    altered.causal_records[altered.causal_order[-1]].payload["executor_execution_state"]["assigned_action_count"] = 2
    with pytest.raises(RoleInputReconstructionError, match="execution state|digest"):
        rebuild_role_input("selector_intent", altered, {"boundary_event_id": altered.causal_order[-1]})


def test_rejects_prompt_as_a_substitute_for_missing_harness_boundary(tmp_path: Path):
    _store, state = _selector_boundary(tmp_path)
    removed = state.causal_order.pop()
    del state.causal_records[removed]
    with pytest.raises(RoleInputReconstructionError, match="durable|boundary"):
        rebuild_role_input("selector_intent", state, {
            "boundary_event_id": state.causal_order[-1], "prompt_source": {"forged": True},
        })


@pytest.fixture
def controller_role_snapshots(tmp_path: Path, monkeypatch, request):
    # Reuse the existing Controller mock transport fixtures. Harness I/O is real;
    # Planner, Selector and audits are explicitly mock decisions, not labels.
    import json
    from test_stateful_goal_loop import (
        _QueueClient, _StrongPlanner, _audit_call, _goal, _selector, _settings,
        _strong_patch,
    )
    from rwkv_lh.model import LongHorizonModel
    from rwkv_lh.model_session import ModelSession
    from rwkv_lh.schema import RunState
    from rwkv_lh.supervisor import SupervisorPolicy

    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=1000)
    state = store.create_run(_goal(tmp_path), "ROLE-INPUT-CONTROLLER-FIXTURE")
    snapshots = []
    original_save = store.save

    def capture(*args, **kwargs):
        saved = original_save(*args, **kwargs)
        snapshots.append(RunState.from_dict(saved.to_dict()))
        return saved

    monkeypatch.setattr(store, "save", capture)
    outputs = [
        json.dumps({"function": "write_file", "params": {"path": "result.txt", "content": "verified content"}}),
        json.dumps(_audit_call("continue", step_id="S1", step_complete=True, evidence_refs=["A00001"], gaps=[], reason="Fixture write observed")),
        json.dumps({"function": "final_answer", "params": {"text": "Created result.txt."}}),
        json.dumps(_audit_call("ready_for_final", step_id="", step_complete=False, evidence_refs=["A00001"], gaps=[], reason="Fixture final evidence present")),
    ]
    exercise_feedback = getattr(request, "param", None) == "feedback"
    if exercise_feedback:
        from rwkv_lh.goal_state_protocols import auditor_step_v4
        gap = next(item["code"] for item in auditor_step_v4.build_gap_catalog(
            _strong_patch(state).add_steps[0].to_dict(), ()
        ) if item["code"].startswith("phase_evidence_unproved:"))
        outputs = [
            outputs[0], "{}",
            json.dumps(_audit_call("repair", step_id="S1", step_complete=False, evidence_refs=["A00001"], gaps=[gap], reason="Fixture semantic gap")),
            json.dumps({"function": "write_file", "params": {"path": "result.txt", "content": "verified revised content"}}),
            json.dumps(_audit_call("continue", step_id="S1", step_complete=True, evidence_refs=["A00002"], gaps=[], reason="Fixture revision observed")),
            outputs[2], "{}",
            json.dumps(_audit_call("repair", step_id="", step_complete=False, evidence_refs=["A00002"], gaps=["candidate_omits_required_result"], reason="Fixture answer gap")),
            "{}",
            json.dumps({"function": "final_answer", "params": {"text": "Created and revised result.txt."}}),
            json.dumps(_audit_call("ready_for_final", step_id="", step_complete=False, evidence_refs=["A00002"], gaps=[], reason="Fixture final evidence present")),
        ]
    queue = _QueueClient(outputs)
    model = LongHorizonModel(ModelSession(queue, settings=_settings(progressive=True)), tool_selector=_selector(["write_file"] * (2 if exercise_feedback else 1)))
    monkeypatch.setattr(StatefulGoalLoopController, "_validate_contract_patch_semantics", staticmethod(lambda *args, **kwargs: None))
    transition_budget = 30 if exercise_feedback else getattr(request, "param", 20)
    controller = StatefulGoalLoopController(
        store, model=model, harness=model.harness, supervisor=_StrongPlanner(_strong_patch(state)),
        supervisor_policy=SupervisorPolicy(mode="static"), max_transitions=transition_budget,
    )
    final = controller.run(state.run_id).state
    assert final.status.value == ("completed" if transition_budget >= 20 else "interrupted")
    return snapshots, final


@pytest.mark.parametrize("controller_role_snapshots", ["feedback"], indirect=True)
def test_all_five_roles_rebuild_feedback_from_their_exact_durable_boundary(controller_role_snapshots):
    snapshots, final = controller_role_snapshots
    observed = set()
    for snapshot in snapshots:
        event = snapshot.causal_records[snapshot.causal_order[-1]]
        role = {
            "goal_role_input_boundary": "selector_intent",
            "tool_schema_disclosed": "executor_args",
            "goal_finalizer_session_started": "finalizer_answer",
            "goal_auditor_session_started": event.payload.get("auditor_role"),
        }.get(event.event_type)
        if not role:
            continue
        rebuilt = rebuild_role_input(role, snapshot, {
            "boundary_event_id": event.event_id, "checkpoint_id": event.payload.get("checkpoint_id"),
        })
        if role != "selector_intent":
            assert rebuilt["expected_checkpoint_transcript"] == snapshot.model_states[event.payload["checkpoint_id"]].transcript
        source = rebuilt["prompt_source"]
        feedback = (source["current_progress"]["feedback"] if role == "selector_intent"
                    else source["execution_state"]["feedback"] if role == "executor_args"
                    else source["feedback"])
        if feedback is not None:
            assert role in feedback["recipient_roles"]
            assert feedback["source_id"] and feedback["boundary_id"]
            observed.add((role, feedback["kind"]))
        if role == "finalizer_answer" and source["retry_feedback"] is not None:
            assert feedback is not None
            assert feedback["issues"][0]["code"] == "candidate_omits_required_result"
            observed.add((role, source["retry_feedback"]["kind"]))
    assert observed == {
        ("selector_intent", "semantic"), ("executor_args", "semantic"),
        ("auditor_step", "protocol"), ("auditor_final", "protocol"),
        ("finalizer_answer", "protocol"), ("finalizer_answer", "semantic"),
    }
    assert len(final.actions) == 2


@pytest.mark.parametrize("role,event_type", [
    ("executor_args", "tool_schema_disclosed"),
    ("auditor_step", "goal_auditor_session_started"),
    ("finalizer_answer", "goal_finalizer_session_started"),
    ("auditor_final", "goal_auditor_session_started"),
])
@pytest.mark.parametrize("stored", [False, True])
def test_every_role_matches_actual_controller_checkpoint(controller_role_snapshots, tmp_path, role, event_type, stored):
    import sqlite3
    from rwkv_lh.schema import RunState

    snapshots, _final = controller_role_snapshots
    snapshot = next(snapshot for snapshot in snapshots if (
        snapshot.causal_records[snapshot.causal_order[-1]].event_type == event_type
        and (event_type != "goal_auditor_session_started" or snapshot.causal_records[snapshot.causal_order[-1]].payload["auditor_role"] == role)
    ))
    if stored:
        with sqlite3.connect(tmp_path / "state" / "long_horizon.db") as database:
            raw = database.execute("SELECT state_json FROM checkpoints WHERE run_id = ? AND revision = ?", (snapshot.run_id, snapshot.revision)).fetchone()[0]
        snapshot = RunState.from_dict(LongHorizonStore._deserialize(raw))
    event = snapshot.causal_records[snapshot.causal_order[-1]]
    result = rebuild_role_input(role, snapshot, {
        "boundary_event_id": event.event_id, "checkpoint_id": event.payload["checkpoint_id"],
    })
    assert result["expected_checkpoint_transcript"] == snapshot.model_states[event.payload["checkpoint_id"]].transcript
    if role != "executor_args":
        assert result["evidence_refs"]


def test_selector_snapshot_matches_production_votes(controller_role_snapshots):
    from rwkv_lh.schema import ModelLaneKind

    snapshots, final = controller_role_snapshots
    snapshot = next(snapshot for snapshot in snapshots if snapshot.causal_records[snapshot.causal_order[-1]].event_type == "goal_role_input_boundary")
    checkpoints = [checkpoint for checkpoint in final.model_states.values() if checkpoint.lane_kind is ModelLaneKind.SELECTOR]
    assert len(checkpoints) == 3
    for checkpoint in checkpoints:
        result = rebuild_role_input("selector_intent", snapshot, {
            "boundary_event_id": snapshot.causal_order[-1],
            "menu_order_id": checkpoint.native_state_metadata["menu_order_id"],
        })
        assert result["expected_checkpoint_transcript"] == checkpoint.transcript


def test_rejects_durable_harness_scope_outside_active_plan(tmp_path: Path):
    from rwkv_lh.goal_state_protocols import executor_args_v5

    store, state = _selector_boundary(tmp_path)
    payload = deepcopy(state.causal_records[state.causal_order[-1]].payload)
    contract = executor_args_v5.build_target_contract(
        phase="observe", roots=("outside.json",),
        target_descriptors=({"path": "outside.json", "type": "file", "target_kind": "json_file", "exists": True},),
        compatible_targets_by_operation={"read_json": ["outside.json"]},
    )
    mechanical = StatefulGoalLoopController._step_mechanical_evidence_coverage(state, "S1", 1)
    payload["target_contract"] = contract
    payload["executor_execution_state"] = StatefulGoalLoopController._executor_execution_state(
        state, "S1", 1, mechanical, effective_phase="observe", target_contract=contract,
    )
    state = store.save(state, causal_event=CausalEventDraft.create("goal_role_input_boundary", payload, subject_id="S1"))
    with pytest.raises(RoleInputReconstructionError, match="target roots"):
        rebuild_role_input("selector_intent", state, {"boundary_event_id": state.causal_order[-1]})


def test_failure_context_is_rebuilt_from_real_harness_outcome(tmp_path: Path):
    import json
    from test_stateful_goal_loop import _QueueClient, _settings
    from rwkv_lh.controller import LongHorizonController
    from rwkv_lh.model import LongHorizonModel
    from rwkv_lh.model_session import ModelSession

    store, state = _selector_boundary(tmp_path)
    model = LongHorizonModel(ModelSession(_QueueClient([json.dumps({"function": "read_json", "params": {"path": "data.json"}})]), settings=_settings()))
    controller = LongHorizonController(store, model=model, harness=model.harness)
    decision = model.next_command(state, controller._persist_callback, eligible_operations=("read_json",))
    action = controller._execute_decision(state, decision)
    controller._persist(state, "goal_action_plan_step_assigned", dict(action_id=action.action_id, step_id="S1", step_revision=1), subject_id=action.action_id)
    assert not action.result["success"]
    prior = next(state.causal_records[eid] for eid in reversed(state.causal_order) if state.causal_records[eid].event_type == "goal_role_input_boundary")
    payload = deepcopy(prior.payload)
    mechanical = StatefulGoalLoopController._step_mechanical_evidence_coverage(state, "S1", 1)
    payload["mechanical_evidence_sha256"] = canonical_digest(mechanical)
    payload["executor_execution_state"] = StatefulGoalLoopController._executor_execution_state(
        state, "S1", 1, mechanical, effective_phase="observe", target_contract=payload["target_contract"],
    )
    state = store.save(state, causal_event=CausalEventDraft.create("goal_role_input_boundary", payload, subject_id="S1"))
    result = rebuild_role_input("selector_intent", state, {"boundary_event_id": state.causal_order[-1]})
    assert result["coverage"]["failed_last_action"] is True
    assert result["coverage"]["nonempty_error_type"] is True
    assert result["prompt_source"]["current_progress"]["assigned_action_count"] == 1
    assert result["missing_read_roots"] == ["data.json"]


def test_audit_coverage_excludes_unreferenced_actions(controller_role_snapshots):
    from rwkv_lh.model import LongHorizonModel
    from rwkv_lh.role_trace_inputs import _audit_coverage

    _snapshots, state = controller_role_snapshots
    visible = LongHorizonModel._audit_evidence_records(state, ("A00001",))
    covered = _audit_coverage(state, visible)
    assert covered["mutate"] is True
    assert covered["missing_target"] is True
    # The same durable run still contains the successful write and its missing
    # target assignment. Neither is visible when its evidence ref is withheld.
    invisible = _audit_coverage(state, ())
    assert not any(invisible.values())


def test_audit_coverage_ignores_later_unseen_assignment(controller_role_snapshots):
    from rwkv_lh.goal_state_protocols import executor_args_v5
    from rwkv_lh.model import LongHorizonModel
    from rwkv_lh.role_trace_inputs import _audit_coverage

    _snapshots, state = controller_role_snapshots
    visible = LongHorizonModel._audit_evidence_records(state, ("A00001",))
    expected = _audit_coverage(state, visible)
    original = next(state.causal_records[eid] for eid in state.causal_order if state.causal_records[eid].event_type == "goal_role_input_boundary")
    payload = deepcopy(original.payload)
    payload["target_contract"] = executor_args_v5.build_target_contract(
        phase="mutate", roots=("result.txt",),
        target_descriptors=({"path": "result.txt", "type": "directory", "target_kind": "directory", "exists": True},),
        compatible_targets_by_operation={"write_file": ["result.txt"]},
    )
    # Appended fixture fact is causally after the only referenced action. It
    # must not replace that action's actual pre-execution target observation.
    changed = deepcopy(state)
    LongHorizonStore._append_causal_event(changed, CausalEventDraft.create("goal_role_input_boundary", payload, subject_id="S1"))
    assert _audit_coverage(changed, visible) == expected
