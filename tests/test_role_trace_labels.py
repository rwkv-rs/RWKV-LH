"""Source/target validation over Controller test fixtures, never training data."""

from __future__ import annotations

import importlib

import pytest

from rwkv_lh.goal_state_protocols import auditor_final, auditor_step_v7
from rwkv_lh.model_io import ModelCommand
from rwkv_lh.role_trace_inputs import rebuild_role_input
from test_role_trace_inputs import controller_role_snapshots  # noqa: F401


def _validate(role, rebuilt, target, verifier_id="TEST-BOUNDARY"):
    api = importlib.import_module("rwkv_lh.role_trace_labels")
    return api.validate_role_target(role, rebuilt, target, verifier_id=verifier_id)


def _rebuilt(fixture, role):
    snapshots, _final = fixture
    expected = {
        "executor_args": "tool_schema_disclosed",
        "auditor_step": "goal_auditor_session_started",
        "auditor_final": "goal_auditor_session_started",
        "finalizer_answer": "goal_finalizer_session_started",
    }[role]
    snapshot = next(item for item in snapshots if (
        item.causal_records[item.causal_order[-1]].event_type == expected
        and (expected != "goal_auditor_session_started"
             or item.causal_records[item.causal_order[-1]].payload["auditor_role"] == role)
    ))
    boundary = snapshot.causal_records[snapshot.causal_order[-1]]
    return rebuild_role_input(role, snapshot, {
        "boundary_event_id": boundary.event_id,
        "checkpoint_id": boundary.payload["checkpoint_id"],
    })


def _audit(role):
    final = role == "auditor_final"
    return dict(
        verdict="ready_for_final" if final else "continue",
        step_id="" if final else "S1", step_complete=not final,
        evidence_refs=["A00001"], gaps=[],
        reason="The reported result is supported by the cited action.",
    )


@pytest.mark.parametrize("role", ["executor_args", "auditor_step", "auditor_final", "finalizer_answer"])
def test_current_role_target_is_preserved_byte_for_byte(controller_role_snapshots, role):
    rebuilt = _rebuilt(controller_role_snapshots, role)
    if role == "executor_args":
        target = ModelCommand("write_file", {"path": "result.txt", "content": "verified content"}).canonical
    elif role == "finalizer_answer":
        target = ModelCommand("final_answer", {"text": "Created result.txt."}).canonical
    else:
        target = ModelCommand("audit_decision", _audit(role)).canonical
    assert _validate(role, rebuilt, target) == target


def test_executor_cannot_change_selected_operation(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "executor_args")
    target = ModelCommand("read_file", {"path": "result.txt"}).canonical
    with pytest.raises(ValueError, match="selected_operation"):
        _validate("executor_args", rebuilt, target)


@pytest.mark.parametrize("params", [
    {"path": "result.txt", "content": False},
    {"path": "result.txt", "content": "verified content", "invented": True},
    {"path": "/outside/result.txt", "content": "verified content"},
])
def test_executor_uses_real_harness_argument_contract(controller_role_snapshots, params):
    rebuilt = _rebuilt(controller_role_snapshots, "executor_args")
    with pytest.raises(ValueError):
        _validate("executor_args", rebuilt, ModelCommand("write_file", params).canonical)


def test_executor_cannot_ignore_invalid_bound_fact_identity(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "executor_args")
    rebuilt["bound_fact_records"] = [{"action_id": ""}]
    target = ModelCommand("write_file", {"path": "result.txt", "content": "verified content"}).canonical
    with pytest.raises(ValueError, match="action IDs"):
        _validate("executor_args", rebuilt, target)


@pytest.mark.parametrize(("role", "field", "value"), [
    ("auditor_step", "step_id", "FUTURE-STEP"),
    ("auditor_step", "evidence_refs", ["A99999"]),
    ("auditor_step", "step_complete", False),
    ("auditor_final", "step_id", "S1"),
    ("auditor_final", "evidence_refs", ["A99999"]),
    ("auditor_final", "step_complete", True),
])
def test_audit_target_must_bind_visible_input(controller_role_snapshots, role, field, value):
    rebuilt = _rebuilt(controller_role_snapshots, role)
    decision = _audit(role)
    decision[field] = value
    with pytest.raises(ValueError):
        _validate(role, rebuilt, ModelCommand("audit_decision", decision).canonical)


@pytest.mark.parametrize("role", ["auditor_step", "auditor_final"])
def test_repair_cannot_invent_gap_outside_visible_catalog(controller_role_snapshots, role):
    rebuilt = _rebuilt(controller_role_snapshots, role)
    decision = _audit(role)
    decision.update(
        verdict="repair", step_complete=False, gaps=["invented:future-fact"],
        reason="The requested result is not established by the cited action.",
    )
    with pytest.raises(ValueError, match="gap"):
        _validate(role, rebuilt, ModelCommand("audit_decision", decision).canonical)


def test_finalizer_does_not_repair_empty_target(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "finalizer_answer")
    with pytest.raises(ValueError):
        _validate("finalizer_answer", rebuilt, ModelCommand("final_answer", {"text": ""}).canonical)


def test_missing_verifier_is_not_invented(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "finalizer_answer")
    with pytest.raises(ValueError, match="verifier"):
        _validate("finalizer_answer", rebuilt, ModelCommand("final_answer", {"text": "answer"}).canonical, verifier_id="")


def test_noncanonical_target_is_not_silently_rewritten(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "finalizer_answer")
    target = '{"function": "final_answer", "params": {"text": "answer"}}'
    with pytest.raises(ValueError, match="canonical"):
        _validate("finalizer_answer", rebuilt, target)


def test_step_audit_cannot_label_a_proved_mutation_root_missing(controller_role_snapshots):
    rebuilt = _rebuilt(controller_role_snapshots, "auditor_step")
    assert rebuilt["missing_write_roots"] == []
    decision = _audit("auditor_step")
    decision.update(verdict="repair", step_complete=False,
                    gaps=["write_root_unproved:result.txt"], reason="The current step still lacks the required evidence.")
    with pytest.raises(ValueError, match="contradict"):
        _validate("auditor_step", rebuilt, ModelCommand("audit_decision", decision).canonical)
