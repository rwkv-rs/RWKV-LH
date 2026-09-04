import json
import hashlib
import os
import shutil
import tempfile
from pathlib import Path

import pytest

from rwkv_lh.benchmark_verifier import check_spec, run_isolated_verifier
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
)
from rwkv_lh.controller import ControllerResult
from rwkv_lh.schema import (
    CausalEvent,
    CausalEventDraft,
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
)
from rwkv_lh.store import LongHorizonStore
from scripts.run_rwkv_e2e_benchmark import (
    FaultInjectingHarness,
    FORBIDDEN_VISIBLE_KEYS,
    UnsupportedIndependentSelectorOperation,
    VISIBLE_TASK_KEYS,
    _check,
    _continue_stateful_goal_within_budget,
    _resume_current_supervisor_pending,
    _write_report,
    case_runner_exception_result,
    current_architecture_retrieval_actions,
    difficulty_group,
    load_suite,
    load_supervisor_failure_case_ids,
    materialize_workspace,
    run_case,
    stateful_goal_protocol_metadata,
    supervisor_failure_summary,
    write_supervisor_retry_manifest,
)


def _append_causal_event(state: RunState, event_type: str, payload: dict) -> None:
    sequence = len(state.causal_order) + 1
    event = CausalEvent.create(
        event_id=f"CE-{sequence:06d}",
        run_id=state.run_id,
        sequence=sequence,
        parent_id=(state.causal_order[-1] if state.causal_order else None),
        draft=CausalEventDraft.create(
            event_type,
            payload,
            subject_id=state.run_id,
        ),
    )
    state.causal_records[event.event_id] = event
    state.causal_order.append(event.event_id)


def test_benchmark_pending_resume_uses_only_current_unresolved_boundary(
    tmp_path: Path,
) -> None:
    state = RunState(
        run_id="RUN-PENDING",
        goal=GoalState.create(
            request="Complete the task.",
            constraints=(),
            workspace_root=tmp_path,
        ),
        status=RunStatus.INTERRUPTED,
    )
    _append_causal_event(
        state,
        "supervisor_call_pending",
        {
            "pending_id": "SUP-PENDING-contract_plan-0001",
            "phase": "contract_plan",
        },
    )
    calls = 0

    def resume() -> ControllerResult:
        nonlocal calls
        calls += 1
        _append_causal_event(
            state,
            "supervisor_call_resolved",
            {
                "pending_id": "SUP-PENDING-contract_plan-0001",
                "phase": "contract_plan",
            },
        )
        return ControllerResult(state, "", 0)

    recovered, attempts = _resume_current_supervisor_pending(
        ControllerResult(state, "", 0),
        max_attempts=3,
        resume=resume,
    )
    assert recovered.state is state
    assert attempts == 1
    assert calls == 1

    unchanged, attempts = _resume_current_supervisor_pending(
        recovered,
        max_attempts=3,
        resume=resume,
    )
    assert unchanged is recovered
    assert attempts == 0
    assert calls == 1


def test_goal_benchmark_continues_checkpoint_until_audited_completion(
    tmp_path: Path,
) -> None:
    state = RunState(
        run_id="RUN-GOAL-CONTINUE",
        goal=GoalState.create(
            request="Complete the task.",
            constraints=(),
            workspace_root=tmp_path,
        ),
        status=RunStatus.RUNNING,
    )
    _append_causal_event(
        state,
        "run_yielded",
        {
            "reason": "strong_planner_semantic_invalid",
            "resumable": True,
            "termination_permitted": False,
            "continuation": "controller_resume",
        },
    )
    remaining_budgets: list[int] = []

    def resume(remaining: int) -> ControllerResult:
        remaining_budgets.append(remaining)
        state.status = RunStatus.COMPLETED
        _append_causal_event(
            state,
            "run_completed",
            {
                "decision_id": "D-final",
                "audit_id": "AUD-final",
                "rwkv_audit_accepted": True,
            },
        )
        return ControllerResult(state, "audited final", 3)

    result, continuations, consumed = _continue_stateful_goal_within_budget(
        ControllerResult(state, "", 2),
        max_total_transitions=10,
        resume=resume,
    )

    assert result.state.status is RunStatus.COMPLETED
    assert result.final_output == "audited final"
    assert continuations == 1
    assert consumed == 5
    assert remaining_budgets == [8]


def test_goal_benchmark_bounds_zero_transition_checkpoints_and_defers_unavailable(
    tmp_path: Path,
) -> None:
    state = RunState(
        run_id="RUN-GOAL-BOUNDED",
        goal=GoalState.create(
            request="Complete the task.",
            constraints=(),
            workspace_root=tmp_path,
        ),
        status=RunStatus.RUNNING,
    )
    _append_causal_event(
        state,
        "run_yielded",
        {
            "reason": "controller_slice_exhausted",
            "termination_permitted": False,
        },
    )
    calls = 0

    def zero_transition_resume(remaining: int) -> ControllerResult:
        nonlocal calls
        del remaining
        calls += 1
        _append_causal_event(
            state,
            "run_yielded",
            {
                "reason": "controller_slice_exhausted",
                "termination_permitted": False,
            },
        )
        return ControllerResult(state, "", 0)

    result, continuations, consumed = _continue_stateful_goal_within_budget(
        ControllerResult(state, "", 0),
        max_total_transitions=3,
        resume=zero_transition_resume,
    )

    assert result.state.status is RunStatus.RUNNING
    assert continuations == calls == 2
    assert consumed == 3

    _append_causal_event(
        state,
        "run_yielded",
        {
            "reason": "strong_planner_unavailable",
            "termination_permitted": False,
        },
    )
    unavailable, continuations, consumed = (
        _continue_stateful_goal_within_budget(
            ControllerResult(state, "", 0),
            max_total_transitions=3,
            resume=lambda remaining: (_ for _ in ()).throw(
                AssertionError(f"unexpected resume with {remaining}")
            ),
        )
    )
    assert unavailable.state.status is RunStatus.RUNNING
    assert continuations == 0
    assert consumed == 1


def test_case_runner_exception_is_recorded_without_aborting_or_synthesizing(
    tmp_path: Path,
):
    task = {"task_id": "E2E-LH09", "level": "long_horizon"}
    try:
        raise ValueError("unsupported operation contract: mock_api")
    except ValueError as exc:
        result = case_runner_exception_result(task, tmp_path, exc)

    audit = json.loads((tmp_path / result["audit"]).read_text(encoding="utf-8"))
    assert result["task_id"] == "E2E-LH09"
    assert result["status"] == "runner_error"
    assert result["passed"] is False
    assert result["action_count"] == 0
    assert audit["exception_type"] == "ValueError"
    assert audit["model_output_rewritten"] is False
    assert audit["model_output_deleted"] is False
    assert audit["synthetic_action_added"] is False


def test_fixed_selector_mock_api_boundary_is_recorded_as_explicit_unsupported(
    tmp_path: Path,
):
    task = {"task_id": "E2E-LH09", "level": "long_horizon"}
    try:
        raise UnsupportedIndependentSelectorOperation("mock_api")
    except UnsupportedIndependentSelectorOperation as exc:
        result = case_runner_exception_result(task, tmp_path, exc)

    audit = json.loads((tmp_path / result["audit"]).read_text(encoding="utf-8"))
    assert result["status"] == "unsupported_operation_contract"
    assert result["unsupported_operation"] == "mock_api"
    assert result["expected_capability_boundary"] is True
    assert result["model_requests"] == 0
    assert result["action_count"] == 0
    assert audit["unsupported_operation"] == "mock_api"
    assert audit["expected_capability_boundary"] is True
    assert audit["model_output_rewritten"] is False
    assert audit["model_output_deleted"] is False
    assert audit["synthetic_action_added"] is False


def test_independent_selector_stops_before_model_for_mock_api_fixture(
    tmp_path: Path,
):
    task = {"task_id": "E2E-LH09", "level": "long_horizon"}
    acceptance = {"runner_control": {"enable_mock_api": True}}

    with pytest.raises(UnsupportedIndependentSelectorOperation) as captured:
        run_case(
            task,
            acceptance,
            tmp_path,
            max_transitions=10,
            independent_selector=True,
        )

    assert captured.value.operation == "mock_api"
    assert not (tmp_path / "cases/E2E-LH09").exists()


def test_current_architecture_runner_menu_matches_23_class_selector(tmp_path):
    harness = FaultInjectingHarness(
        actions=current_architecture_retrieval_actions(tmp_path / "snapshots")
    )
    executable = {item["name"] for item in harness.g1i_tool_definitions()}
    expected = set(NETWORK_EXACT_TOOL_LABELS)

    assert executable == expected
    assert len(executable) == 23


def test_stateful_report_names_strong_planner_and_rwkv_audit_without_reviewer(
    tmp_path: Path,
) -> None:
    _write_report(
        tmp_path,
        [
            {
                "task_id": "STATEFUL-1",
                "difficulty_group": "hard",
                "level": "tier4_medium_project",
                "agent_completed": False,
                "external_passed": False,
                "passed": False,
                "model_requests": 1,
                "supervisor_request_count": 1,
                "action_count": 0,
                "protocol_rejection_count": 0,
                "supervisor_enabled": True,
                "stateful_goal": True,
            }
        ],
    )

    report = (tmp_path / "REPORT.md").read_text(encoding="utf-8")
    assert "Strong Model is the required Planner" in report
    assert "isolated RWKV Auditor" in report
    assert "no Strong Reviewer is called" in report
    assert "plan/review feedback" not in report


def test_stateful_run_protocol_records_required_strong_planner_without_reviewer() -> None:
    metadata = stateful_goal_protocol_metadata(
        enabled=True, strong_planner_available=True
    )

    assert metadata == {
        "enabled": True,
        "persistent_executor_state_count": 0,
        "executor_state_scope": "one_selected_action",
        "selector_tool_decisions_per_action": 1,
        "selector_model_evaluations_per_action": 3,
        "selector_state_count_per_step": 0,
        "selector_state_policy": "three_fresh_initial_state_evaluations",
        "selector_input_scope": "current_subtask_only",
        "selector_menu_order_ids": ["canonical", "rotate_8", "rotate_17"],
        "selector_vote_rule": "three_menu_order_vote_v1",
        "auditor_state_isolated": True,
        "rwkv_audit_required": True,
        "audit_wkv_merge": False,
        "strong_model_dependency": True,
        "strong_planner_required": True,
        "strong_planner_protocol": "rwkv-lh.goal-plan-patch.v3",
        "strong_reviewer_enabled": False,
    }


def test_rwkv_e2e_catalog_has_30_balanced_model_visible_tasks():
    tasks, acceptance = load_suite()
    assert len(tasks) == 30
    assert len(acceptance) == 30
    assert {task["level"] for task in tasks} == {"basic", "medium", "hard"}
    assert {
        level: sum(task["level"] == level for task in tasks)
        for level in ("basic", "medium", "hard")
    } == {"basic": 10, "medium": 10, "hard": 10}
    for task in tasks:
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)


def test_rwkv_e2e_workspace_never_contains_hidden_acceptance():
    tasks, _ = load_suite()
    task = next(item for item in tasks if item["task_id"] == "E2E-B02")
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        materialize_workspace(task, workspace)
        assert (workspace / "input.txt").read_text(encoding="utf-8") == "project=Orion\ncount=7\n"
        assert not (workspace / "acceptance.json").exists()
        assert not any("acceptance" in path.name for path in workspace.rglob("*"))


def test_external_acceptance_is_independent_of_agent_completion_state():
    tasks, acceptance = load_suite()
    task = next(item for item in tasks if item["task_id"] == "E2E-B02")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        materialize_workspace(task, workspace)
        (workspace / "report.json").write_text(
            json.dumps({"project": "Orion", "doubled_count": 14}) + "\n",
            encoding="utf-8",
        )
        store = LongHorizonStore(root / "state")
        results = [
            _check(item, workspace, store, "NOT-A-RUN", {})
            for item in acceptance["E2E-B02"]["checks"]
        ]
        assert all(item.passed for item in results)


def test_long_horizon_catalog_has_12_hidden_acceptance_cases():
    tasks, acceptance = load_suite("lh12")
    assert len(tasks) == 12
    assert len(acceptance) == 12
    assert {task["task_id"] for task in tasks} == {
        f"E2E-LH{index:02d}" for index in range(1, 13)
    }
    assert all(task["level"] == "long_horizon" for task in tasks)
    for task in tasks:
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)


def test_extension_catalog_completes_fixed_90_case_difficulty_groups():
    extension, acceptance = load_suite("extension48")
    assert len(extension) == 48
    assert len(acceptance) == 48
    assert len({task["task_id"] for task in extension}) == 48
    assert {
        level: sum(task["level"] == level for task in extension)
        for level in ("basic", "medium", "hard")
    } == {"basic": 20, "medium": 20, "hard": 8}

    all_tasks = []
    all_acceptance = {}
    for suite in ("core30", "lh12", "extension48"):
        tasks, hidden = load_suite(suite)
        all_tasks.extend(tasks)
        assert not (set(all_acceptance) & set(hidden))
        all_acceptance.update(hidden)

    assert len(all_tasks) == len(all_acceptance) == 90
    assert len({task["task_id"] for task in all_tasks}) == 90
    assert {
        group: sum(difficulty_group(task["level"]) == group for task in all_tasks)
        for group in ("basic", "medium", "hard")
    } == {"basic": 30, "medium": 30, "hard": 30}
    for task in all_tasks:
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)


def test_agent_v1_project_suite_keeps_acceptance_hidden_and_verifier_frozen():
    tasks, acceptance = load_suite("agentv1")
    assert len(tasks) == len(acceptance) == 1
    task = tasks[0]
    assert task["task_id"] == "AGENT-V1-WEB01"
    assert task["level"] == "project"
    assert set(task) <= VISIBLE_TASK_KEYS
    assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        materialize_workspace(task, workspace)
        assert (workspace / "verify_app.py").is_file()
        assert not (workspace / "acceptance.json").exists()
        frozen = next(
            item
            for item in acceptance["AGENT-V1-WEB01"]["checks"]
            if item["kind"] == "file_content" and item["path"] == "verify_app.py"
        )
        assert (workspace / "verify_app.py").read_text(encoding="utf-8") == frozen["content"]


def test_agent_capability_ladder_v1_is_frozen_balanced_and_model_clean(
    tmp_path: Path,
):
    tasks, acceptance = load_suite("agentladderv1")
    expected_levels = {
        "tier1_closed_loop": 2,
        "tier2_small_workflow": 2,
        "tier3_cross_file": 2,
        "tier4_medium_project": 2,
        "tier5_networked_project": 2,
    }

    assert len(tasks) == len(acceptance) == 10
    assert {
        level: sum(task["level"] == level for task in tasks)
        for level in expected_levels
    } == expected_levels
    assert {
        difficulty_group(level) for level in expected_levels
    } == {"basic", "medium", "hard"}
    for index, task in enumerate(tasks):
        assert set(task) <= VISIBLE_TASK_KEYS
        assert not (set(task) & FORBIDDEN_VISIBLE_KEYS)
        assert "runner_control" not in task
        workspace = tmp_path / f"case-{index:02d}"
        materialize_workspace(task, workspace)
        assert not (workspace / "acceptance.json").exists()
        for path in workspace.rglob("*.py"):
            compile(path.read_text(encoding="utf-8"), str(path), "exec")
        frozen = next(
            item
            for item in acceptance[task["task_id"]]["checks"]
            if item["kind"] == "file_content"
            and item["path"] == "verify_project.py"
        )
        assert (workspace / "verify_project.py").read_text(encoding="utf-8") == frozen["content"]


def test_agent_capability_ladder_binds_retrieval_policy_once_per_task():
    tasks, acceptance = load_suite("agentladderv1")
    levels = {task["task_id"]: task["level"] for task in tasks}

    for task_id, case in acceptance.items():
        control = case["runner_control"]
        expected = (
            "auto_public"
            if levels[task_id] == "tier5_networked_project"
            else "offline"
        )
        assert control == {
            "network_policy": expected,
            "network_explicit_approval": False,
            "network_public_workspace_paths": [],
        }
        grounding = [
            check
            for check in case["checks"]
            if check["kind"] == "network_evidence_grounding"
        ]
        assert bool(grounding) == (expected == "auto_public")


def _network_evidence_event(url: str) -> list[dict[str, object]]:
    record = {
        "schema_version": "rwkv-lh.evidence-record.v1",
        "evidence_record_id": "E-test-record",
        "source_object": {
            "schema_version": "rwkv-lh.source-object.v1",
            "source_object_id": "public_web_page:test",
            "source_object_type": "public_web_page",
            "source_record_id": "a" * 64,
        },
        "snapshot_digest": "b" * 64,
        "exact_spans": [
            {
                "schema_version": "rwkv-lh.evidence-span.v1",
                "span_id": "SPAN-test",
                "text": "official packaging guidance",
                "locator": {"snapshot_digest": "b" * 64},
            }
        ],
        "structured_fields": {},
        "url": url,
        "title": "Official guide",
        "published": "",
        "retrieved_at": "2026-08-30T00:00:00+00:00",
    }
    envelope = {
        "schema_version": "rwkv-lh.external-evidence.v1",
        "route_id": "ROUTE-test",
        "tool": "web_search",
        "records": [record],
    }
    return [
        {
            "type": "atom_outcome_committed",
            "data": {
                "outcome": {
                    "actions": [
                        {
                            "action_id": "A00001",
                            "operation": "web_search",
                            "arguments": {"query": "official packaging guide"},
                            "status": "succeeded",
                            "result": {
                                "success": True,
                                "output": json.dumps(envelope),
                                "evidence": [record],
                                "metadata": {"external_evidence": envelope},
                            },
                        }
                    ]
                }
            },
        }
    ]


def test_network_evidence_grounding_requires_committed_url_in_artifact(
    tmp_path: Path,
):
    url = "https://packaging.python.org/en/latest/guides/writing-pyproject-toml/"
    (tmp_path / "SOURCES.md").write_text(f"Source: {url}\n", encoding="utf-8")
    spec = {
        "kind": "network_evidence_grounding",
        "operations": ["web_search"],
        "paths": ["SOURCES.md"],
        "required_hosts": ["packaging.python.org"],
        "min_successful_actions": 1,
        "min_records": 1,
        "min_cited_urls": 1,
    }

    result = check_spec(spec, tmp_path, _network_evidence_event(url), {})

    assert result.passed
    assert result.observation["successful_action_count"] == 1
    assert result.observation["valid_record_count"] == 1
    assert result.observation["cited_urls"] == [url]


def test_network_evidence_grounding_rejects_fabricated_artifact_url(
    tmp_path: Path,
):
    committed = "https://packaging.python.org/en/latest/guides/writing-pyproject-toml/"
    (tmp_path / "SOURCES.md").write_text(
        "Source: https://packaging.python.org/fabricated\n", encoding="utf-8"
    )

    result = check_spec(
        {
            "kind": "network_evidence_grounding",
            "operations": ["web_search"],
            "paths": ["SOURCES.md"],
            "required_hosts": ["packaging.python.org"],
            "min_successful_actions": 1,
            "min_records": 1,
            "min_cited_urls": 1,
        },
        tmp_path,
        _network_evidence_event(committed),
        {},
    )

    assert not result.passed
    assert result.observation["valid_record_count"] == 1
    assert result.observation["cited_url_count"] == 0


def test_supervisor_failure_summary_preserves_retry_semantics_and_resolution():
    unresolved = supervisor_failure_summary(
        [
            {
                "type": "supervisor_request_failed",
                "phase": "contract_plan",
                "run_id": "E2E-M01",
                "request_digest": "digest-1",
                "http_status": 403,
                "error": "SupervisorTransportError: supervisor HTTP 403",
            }
        ]
    )
    assert unresolved == {
        "failed": True,
        "category": "authorization",
        "retryable": False,
        "http_status": 403,
        "phase": "contract_plan",
        "error": "SupervisorTransportError: supervisor HTTP 403",
        "unresolved_request_count": 1,
    }

    resolved = supervisor_failure_summary(
        [
            {
                "type": "supervisor_request_failed",
                "phase": "contract_plan",
                "run_id": "E2E-M01",
                "request_digest": "digest-1",
                "http_status": 503,
            },
            {
                "type": "supervisor_request_returned",
                "phase": "contract_plan",
                "run_id": "E2E-M01",
                "request_digest": "digest-1",
            },
        ]
    )
    assert resolved["failed"] is False


def test_supervisor_failure_summary_includes_local_semantic_failures_and_resolution():
    failed_event = {
        "type": "supervisor_call_failed",
        "data": {
            "phase": "contract_plan",
            "resumable": True,
            "error": {
                "type": "ValueError",
                "message": "mutation requires a dependent verify node",
            },
        },
    }

    unresolved = supervisor_failure_summary([], [failed_event])

    assert unresolved == {
        "failed": True,
        "category": "semantic_validation",
        "retryable": True,
        "http_status": 0,
        "phase": "contract_plan",
        "error": "ValueError: mutation requires a dependent verify node",
        "unresolved_request_count": 1,
    }
    resolved = supervisor_failure_summary(
        [],
        [failed_event, {"type": "contract_graph_patch_committed", "data": {}}],
    )
    assert resolved["failed"] is False


def test_supervisor_retry_manifest_round_trips_failed_and_not_started_cases(tmp_path):
    output = tmp_path / "run"
    output.mkdir()
    selected = [{"task_id": "E2E-B01"}, {"task_id": "E2E-B02"}]
    results = [
        {
            "task_id": "E2E-B01",
            "supervisor_failure": {
                "failed": True,
                "category": "authorization",
                "retryable": False,
                "http_status": 403,
                "phase": "contract_plan",
                "error": "denied",
            },
        }
    ]

    write_supervisor_retry_manifest(output, selected=selected, results=results)

    assert load_supervisor_failure_case_ids(output) == ("E2E-B01", "E2E-B02")
    manifest = json.loads((output / "retry_manifest.json").read_text())
    assert manifest["non_retryable_case_count"] == 1
    assert manifest["cases"][1]["category"] == "not_started"


def test_load_supervisor_failures_from_legacy_results_and_case_audit(tmp_path):
    output = tmp_path / "legacy"
    case_root = output / "cases" / "E2E-B01"
    case_root.mkdir(parents=True)
    (case_root / "audit.json").write_text(
        json.dumps(
            {
                "supervisor_trace": [
                    {
                        "type": "supervisor_request_failed",
                        "phase": "contract_review",
                        "run_id": "E2E-B01",
                        "request_digest": "digest",
                        "http_status": 500,
                        "error": "SupervisorTransportError: supervisor HTTP 500",
                    }
                ]
            }
        )
    )
    (output / "results.json").write_text(
        json.dumps(
            {
                "schema_version": "rwkv-e2e.results.v1",
                "results": [
                    {
                        "task_id": "E2E-B01",
                        "audit": "cases/E2E-B01/audit.json",
                    }
                ],
            }
        )
    )

    assert load_supervisor_failure_case_ids(output) == ("E2E-B01",)


def test_extension_seeded_python_files_compile():
    tasks, _ = load_suite("extension48")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for task in tasks:
            workspace = root / task["task_id"]
            materialize_workspace(task, workspace)
            for path in workspace.rglob("*.py"):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_frozen_codex_reference_covers_the_same_90_cases_and_digest():
    root = Path(__file__).resolve().parents[1]
    dataset = root / "data" / "datasets" / "rwkv_e2e_90_v1"
    manifest = json.loads((dataset / "manifest.json").read_text(encoding="utf-8"))
    reference_path = dataset / "codex_reference_answers.json"
    references = json.loads(reference_path.read_text(encoding="utf-8"))
    digest = hashlib.sha256(reference_path.read_bytes()).hexdigest()

    all_tasks = []
    for suite in ("core30", "lh12", "extension48"):
        tasks, _ = load_suite(suite)
        all_tasks.extend(tasks)

    assert manifest["case_count"] == 90
    assert manifest["difficulty_groups"] == {
        "basic": 30,
        "medium": 30,
        "hard": 30,
    }
    assert digest == manifest["reference_answer_policy"]["sha256"]
    assert digest == "947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b"
    assert {item["task_id"] for item in references["cases"]} == {
        task["task_id"] for task in all_tasks
    }
    assert {
        group: sum(item["group"] == group for item in references["cases"])
        for group in ("basic", "medium", "hard")
    } == {"basic": 30, "medium": 30, "hard": 30}


def test_long_horizon_generators_materialize_dynamic_pressure_fixtures():
    tasks, _ = load_suite("lh12")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        manifest_task = next(item for item in tasks if item["task_id"] == "E2E-LH03")
        manifest_workspace = root / "manifest"
        materialize_workspace(manifest_task, manifest_workspace)
        assert len(list((manifest_workspace / "catalog").rglob("manifest.json"))) == 3
        assert (manifest_workspace / "catalog/root_manifest.json").is_file()

        shard_task = next(item for item in tasks if item["task_id"] == "E2E-LH05")
        shard_workspace = root / "shards"
        materialize_workspace(shard_task, shard_workspace)
        assert len(list((shard_workspace / "shards").glob("*.json"))) == 18
        assert len(list((shard_workspace / "fallback").glob("*.json"))) == 4

        memory_task = next(item for item in tasks if item["task_id"] == "E2E-LH11")
        memory_workspace = root / "memory"
        materialize_workspace(memory_task, memory_workspace)
        assert len(list((memory_workspace / "artifacts").glob("*.txt"))) == 40


def test_all_seeded_python_files_compile():
    tasks, _ = load_suite("lh12")
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        for task in tasks:
            workspace = root / task["task_id"]
            materialize_workspace(task, workspace)
            for path in workspace.rglob("*.py"):
                compile(path.read_text(encoding="utf-8"), str(path), "exec")


def test_dynamic_discovery_manifest_exposes_only_root_entrypoint():
    tasks, _ = load_suite("lh12")
    task = next(item for item in tasks if item["task_id"] == "E2E-LH03")
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        materialize_workspace(task, workspace)
        goal = type("Goal", (), {"workspace_root": str(workspace)})()
        harness = FaultInjectingHarness(
            manifest_entrypoints=("catalog/root_manifest.json",)
        )
        manifest = harness.workspace_manifest(goal)
        assert manifest["discovery_policy"] == "entrypoints_only"
        assert [entry["path"] for entry in manifest["entries"]] == [
            "catalog/root_manifest.json"
        ]


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_benchmark_agent_command_sandbox_does_not_share_network():
    with tempfile.TemporaryDirectory() as directory:
        workspace = Path(directory) / "workspace"
        workspace.mkdir()
        goal = type("Goal", (), {"workspace_root": str(workspace)})()
        harness = FaultInjectingHarness()
        command, _ = harness._bubblewrap_command(
            goal,
            workspace,
            ["python", "probe.py"],
        )
        assert "--unshare-all" in command
        assert "--share-net" not in command


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_benchmark_harness_passes_uv_python_environment_to_sandbox(tmp_path):
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    goal = GoalState.create(
        request="run the project Python test tool",
        constraints=[],
        workspace_root=workspace,
    )
    harness = FaultInjectingHarness()

    result = harness.execute(
        TaskAction(
            "check_command",
            {"argv": ["python", "-m", "pytest", "--version"]},
        ),
        goal,
    )

    assert result.success is True
    assert result.output.startswith("pytest ")
    assert result.metadata["sandbox_backend"] == "bubblewrap"


def test_cascading_command_stage_checker_requires_ordered_failures_then_success():
    events = []
    for index, (exit_code, output) in enumerate(
        [(1, "layer A"), (1, "layer B"), (1, "layer C"), (0, "ok")],
        start=1,
    ):
        attempt_id = f"A{index}"
        events.extend(
            [
                {
                    "type": "attempt_started",
                    "data": {
                        "attempt_id": attempt_id,
                        "arguments": {"argv": ["python", "verify.py"]},
                    },
                },
                {
                    "type": "action_returned",
                    "data": {
                        "attempt_id": attempt_id,
                        "exit_code": exit_code,
                        "output": output,
                    },
                },
            ]
        )
    result = check_spec(
        {
            "kind": "command_exit_stages",
            "argv": ["python", "verify.py"],
            "stages": ["layer A", "layer B", "layer C"],
        },
        Path("."),
        events,
        {},
    )
    assert result.passed


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_isolated_verifier_hides_catalog_logs_tests_and_parent_memory():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        (workspace / "probe.py").write_text(
            """import os
from pathlib import Path

assert not Path('/tests').exists()
assert not Path('/logs/verifier').exists()
assert not Path('/opt/rwkv-lh-src').exists()
try:
    os.open(f'/proc/{os.getppid()}/mem', os.O_RDONLY)
except OSError:
    pass
else:
    raise AssertionError('verifier parent memory is readable')
try:
    Path('leak.txt').write_text('leaked')
except OSError:
    pass
else:
    raise AssertionError('verifier workspace is writable')
""",
            encoding="utf-8",
        )
        result = run_isolated_verifier(
            {"checks": [{"kind": "command_exit", "argv": ["python", "probe.py"]}]},
            workspace,
            [],
            {},
            private_root=root / "private",
        )
        assert result.passed
        assert result.metadata["acceptance_transport"] == "stdin"
        assert result.metadata["workspace_mount"] == "read_only_snapshot"
        assert result.metadata["network"] == "unshared"
        assert not (workspace / "leak.txt").exists()


@pytest.mark.skipif(
    os.name != "posix" or shutil.which("bwrap") is None,
    reason="bubblewrap verifier requires Linux and bwrap",
)
def test_isolated_verifier_rejects_workspace_symlinks_fail_closed():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        workspace = root / "workspace"
        workspace.mkdir()
        outside = root / "hidden_acceptance.json"
        outside.write_text('{"secret": true}', encoding="utf-8")
        (workspace / "escape.json").symlink_to(outside)
        with pytest.raises(ValueError, match="rejects non-regular file"):
            run_isolated_verifier(
                {"checks": [{"kind": "path_absent", "path": "nothing"}]},
                workspace,
                [],
                {},
                private_root=root / "private",
            )
