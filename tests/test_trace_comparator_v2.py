from __future__ import annotations

import json
from pathlib import Path

from rwkv_lh.exact_tool_selector.native_network_protocol import (
    NATIVE_SELECTOR_DECODER_ID,
    NATIVE_SELECTOR_DECODER_PROTOCOL,
)
from rwkv_lh.trace_comparator_v2 import (
    CheckpointOracle,
    analyze_case,
    compare_runs,
)


def _event(index: int, event_type: str, data: dict) -> dict:
    return {
        "event_id": index + 1,
        "revision": index,
        "type": event_type,
        "data": data,
    }


def _frontier(
    *,
    step_id: str = "S1",
    objective: str = "Inspect the local source.",
    event_index: int = 0,
) -> dict:
    return _event(
        event_index,
        "action_observation_appended",
        {
            "model_event": {
                "event_type": "goal_frontier_assignment",
                "payload": {
                    "active_step": {
                        "step_id": step_id,
                        "step_revision": 1,
                        "objective": objective,
                    }
                },
            }
        },
    )


def _selection(index: int, operation: str, eligible: list[str]) -> dict:
    return _event(
        index,
        "exact_tool_selection_staged",
        {
            "selected_operation": operation,
            "selection": {
                "raw_selection": {
                    "selected_operation": operation,
                    "eligible_labels": eligible,
                    "profile_id": "candidate",
                    "profile_sha256": "1" * 64,
                    "decoder_id": NATIVE_SELECTOR_DECODER_ID,
                    "decoder_sha256": "2" * 64,
                    "decoder_protocol": NATIVE_SELECTOR_DECODER_PROTOCOL,
                }
            },
        },
    )


def _result(*, passed: bool) -> dict:
    return {
        "task_id": "CASE-1",
        "passed": passed,
        "agent_completed": passed,
        "external_passed": passed,
        "status": "completed" if passed else "blocked",
        "action_count": 1,
        "protocol_rejection_count": 0,
    }


def test_trace_comparator_finds_selector_first_then_records_amplification() -> None:
    oracle = CheckpointOracle(
        step_id="S1",
        step_revision=1,
        occurrence=1,
        acceptable_operations=("read_file",),
        expected_executor_params=None,
        expected_step_completed=None,
    )
    events = [
        _frontier(),
        _selection(1, "write_file", ["read_file", "write_file"]),
        _event(2, "model_call_accepted", {"operation": "write_file"}),
        _event(3, "action_started", {"action_id": "A1"}),
        _event(4, "action_finished", {"action_id": "A1", "result_digest": "d1"}),
        _event(5, "goal_step_evidence_gap_recorded", {"active_step_id": "S1"}),
        _event(6, "run_blocked", {"reason": "no_progress"}),
    ]

    value = analyze_case(
        task_id="CASE-1", result=_result(passed=False), events=events, oracle=[oracle]
    )

    assert value["first_verified_anomaly"]["role"] == "selector"
    assert value["first_verified_anomaly"]["event_index"] == 1
    assert [item["event_type"] for item in value["amplification_chain"]] == [
        "action_started",
        "action_finished",
        "goal_step_evidence_gap_recorded",
        "run_blocked",
    ]
    assert value["unattributed_failure"] is False


def test_trace_comparator_attributes_controller_before_selector() -> None:
    oracle = CheckpointOracle(
        step_id="S1",
        step_revision=1,
        occurrence=1,
        acceptable_operations=("read_file",),
        expected_executor_params=None,
        expected_step_completed=None,
    )
    value = analyze_case(
        task_id="CASE-1",
        result=_result(passed=False),
        events=[_frontier(), _selection(1, "write_file", ["write_file"])],
        oracle=[oracle],
    )

    assert value["first_verified_anomaly"]["role"] == "controller"
    assert value["first_verified_anomaly"]["kind"] == (
        "required_operation_absent_from_eligibility"
    )


def test_trace_comparator_does_not_invent_role_from_external_failure() -> None:
    value = analyze_case(
        task_id="CASE-1",
        result=_result(passed=False),
        events=[_frontier(), _selection(1, "read_file", ["read_file"])],
    )

    assert value["first_verified_anomaly"] is None
    assert value["unattributed_failure"] is True


def test_trace_comparator_uses_durable_protocol_rejection_once() -> None:
    events = [
        _frontier(),
        _selection(1, "replace_text", ["replace_text"]),
        _event(
            2,
            "model_call_rejected",
            {
                "request_id": "MR-1",
                "decision_id": "D-1",
                "error": "base snapshot mismatch",
            },
        ),
        _event(
            3,
            "protocol_rejection_recorded",
            {
                "request_id": "MR-1",
                "decision_id": "D-1",
                "protocol_scope": "action",
                "selected_operation": "replace_text",
                "error": "base snapshot mismatch",
            },
        ),
    ]

    value = analyze_case(
        task_id="CASE-1", result=_result(passed=False), events=events
    )

    assert value["protocol_rejection_count"] == 1
    assert value["action_protocol_rejection_count"] == 1
    assert value["verified_anomalies"] == [value["first_verified_anomaly"]]
    assert value["first_verified_anomaly"]["event_type"] == (
        "protocol_rejection_recorded"
    )
    assert value["first_verified_anomaly"]["event_index"] == 3


def test_trace_comparator_reads_nested_audit_decision() -> None:
    oracle = CheckpointOracle(
        step_id="S1",
        step_revision=1,
        occurrence=1,
        acceptable_operations=("read_file",),
        expected_executor_params=None,
        expected_step_completed=True,
    )
    events = [
        _frontier(),
        _selection(1, "read_file", ["read_file"]),
        _event(
            2,
            "goal_audit_recorded",
            {
                "audit": {
                    "step_id": "S1",
                    "verdict": "repair",
                    "completed_steps": [],
                    "gaps": ["read_root_unproved:source.txt"],
                }
            },
        ),
    ]

    value = analyze_case(
        task_id="CASE-1", result=_result(passed=False), events=events, oracle=[oracle]
    )

    assert value["audit_decision_count"] == 1
    assert value["audit_repair_count"] == 1
    assert value["audit_reported_gap_count"] == 1
    assert value["first_verified_anomaly"]["role"] == "auditor"
    assert value["first_verified_anomaly"]["kind"] == (
        "audit_completion_differs_from_oracle"
    )


def test_trace_comparator_does_not_call_repaired_plan_draft_first_error() -> None:
    events = [
        _event(
            0,
            "strong_planner_patch_rejected",
            {"error": {"type": "ValueError", "message": "invalid draft"}},
        ),
        _event(1, "goal_plan_patch_committed", {"patch_id": "GPP-VALID"}),
        _frontier(event_index=2),
        _selection(3, "read_file", ["read_file"]),
    ]

    value = analyze_case(
        task_id="CASE-1", result=_result(passed=False), events=events
    )

    assert value["first_verified_anomaly"] is None
    assert value["recovered_planner_failure_count"] == 1
    assert value["recovered_planner_failures"][0]["recovered_before_action"] is True


def _write_run(root: Path, operation: str, passed: bool) -> None:
    case = root / "cases/CASE-1"
    case.mkdir(parents=True)
    results = {
        "schema_version": "rwkv-e2e.results.v1",
        "results": [_result(passed=passed)],
    }
    (root / "results.json").write_text(json.dumps(results) + "\n")
    events = [_frontier(), _selection(1, operation, ["read_file", "write_file"])]
    (case / "event_log.json").write_text(json.dumps(events) + "\n")


def test_compare_runs_requires_same_cases_and_uses_frozen_oracle(tmp_path: Path) -> None:
    zero = tmp_path / "zero"
    tuned = tmp_path / "tuned"
    _write_run(zero, "write_file", False)
    _write_run(tuned, "read_file", True)
    oracle = tmp_path / "oracle.json"
    oracle.write_text(
        json.dumps(
            {
                "schema_version": "rwkv-lh.trace-checkpoint-oracle.v2",
                "cases": {
                    "CASE-1": [
                        {
                            "step_id": "S1",
                            "step_revision": 1,
                            "occurrence": 1,
                            "acceptable_operations": ["read_file"],
                        }
                    ]
                },
            }
        )
        + "\n"
    )

    value = compare_runs(
        runs=[("zero", zero), ("tuned", tuned)], oracle_path=oracle
    )

    assert value["historical_root_cause_prior_used"] is False
    assert value["semantic_attribution_enabled"] is True
    paired = value["paired_cases"][0]["runs"]
    assert paired["zero"]["first_verified_anomaly_role"] == "selector"
    assert paired["tuned"]["first_verified_anomaly_role"] is None


def test_compare_runs_ignores_cross_run_planner_surface_variability(
    tmp_path: Path,
) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    _write_run(first, "read_file", True)
    _write_run(second, "read_file", True)
    first_events = [
        _event(
            0,
            "goal_plan_patch_committed",
            {"steps": [{"step_id": "OBSERVE-ONE", "phase": "observe"}]},
        ),
        _frontier(
            step_id="OBSERVE-ONE",
            objective="Read the implementation.",
            event_index=1,
        ),
        _selection(2, "read_file", ["read_file"]),
    ]
    second_events = [
        _event(
            0,
            "goal_plan_patch_committed",
            {
                "steps": [
                    {"step_id": "DISCOVER-A", "phase": "derive_evidence"},
                    {"step_id": "DISCOVER-B", "phase": "observe"},
                ]
            },
        ),
        _frontier(
            step_id="DISCOVER-B",
            objective="Inspect the relevant file after a separate discovery stage.",
            event_index=1,
        ),
        _selection(2, "read_file", ["read_file"]),
    ]
    (first / "cases/CASE-1/event_log.json").write_text(
        json.dumps(first_events) + "\n",
        encoding="utf-8",
    )
    (second / "cases/CASE-1/event_log.json").write_text(
        json.dumps(second_events) + "\n",
        encoding="utf-8",
    )

    value = compare_runs(
        runs=[("first", first), ("second", second)],
        oracle_path=None,
    )

    assert value["planner_variability"]["ignored"] is True
    assert value["planner_variability"]["ignored_fields"] == [
        "exact_plan_text",
        "step_count",
        "step_ids",
        "phase_or_stage_labels",
        "step_order",
    ]
    assert all(run["passed_count"] == 1 for run in value["runs"])
    assert all(
        run["cases"][0]["first_verified_anomaly"] is None
        for run in value["runs"]
    )
