import hashlib
import json
from pathlib import Path

import pytest

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionResult, ObservedArtifact
from rwkv_lh.memory import WorkingMemoryBuilder
from rwkv_lh.model import CrossValidationDecision
from rwkv_lh.schema import (
    Attempt,
    AttemptStatus,
    GoalCriterion,
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
    ValidationSpec,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import LongHorizonStore


def make_goal(workspace: Path) -> GoalState:
    workspace.mkdir(parents=True, exist_ok=True)
    return GoalState.create(
        objective="Execute and verify a workspace mutation",
        original_request="Write the requested value and preserve its observation",
        constraints=["Stay inside the workspace"],
        success_criteria=[GoalCriterion("GC1", "The requested mutation is verified")],
        workspace_root=workspace,
    )


def make_recording_state(
    tmp_path: Path,
    action: TaskAction,
) -> tuple[LongHorizonController, RunState]:
    goal = make_goal(tmp_path / "workspace")
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(goal, "ROUND22-SNAPSHOT")
    task = TaskNode(
        "T1",
        "Produce artifact",
        "Execute one mutation",
        status=TaskStatus.RUNNING,
        action=action,
        attempt_ids=["T1-A1"],
    )
    attempt = Attempt(
        "T1-A1",
        "T1",
        AttemptStatus.RUNNING,
        action_fingerprint(action),
        "round22-snapshot",
        utc_now(),
    )
    state.tasks = {"T1": task}
    state.attempts = {"T1-A1": attempt}
    state.active_task_id = "T1"
    state.status = RunStatus.RUNNING
    return LongHorizonController(store), state


@pytest.mark.parametrize(
    ("action_type", "arguments", "initial_files", "target"),
    [
        (
            "write_file",
            {
                "path": "answer.txt",
                "content": "Orion\n14\n",
                "overwrite": True,
                "create_parents": True,
            },
            {},
            "answer.txt",
        ),
        (
            "write_json",
            {"path": "answer.json", "value": {"count": 14, "name": "Orion"}},
            {},
            "answer.json",
        ),
        (
            "append_file",
            {"path": "answer.log", "content": "14\n"},
            {"answer.log": b"Orion\n"},
            "answer.log",
        ),
        (
            "copy_file",
            {"source": "source.txt", "destination": "copied.txt"},
            {"source.txt": b"Orion\n14\n"},
            "copied.txt",
        ),
    ],
)
def test_mutation_snapshot_reads_exact_post_action_workspace_bytes(
    tmp_path,
    action_type,
    arguments,
    initial_files,
    target,
):
    action = TaskAction(action_type, arguments)
    controller, state = make_recording_state(tmp_path, action)
    workspace = Path(state.goal.workspace_root)
    for relative, content in initial_files.items():
        path = workspace / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    result = controller.harness.execute(action, state.goal)
    original_output = result.output
    audits = controller._record_artifacts_and_memory(
        state,
        "T1",
        "T1-A1",
        result,
    )

    assert result.success is True
    assert result.output == original_output
    assert state.memory_index["M-T1-A1"].kind == "action_result"
    assert state.memory_index["M-T1-A1"].content == original_output
    snapshot_id = "M-T1-A1-POST-R1"
    snapshot = state.memory_index[snapshot_id]
    payload = json.loads(snapshot.content)
    actual = (workspace / target).read_bytes()
    assert snapshot.kind == "post_action_workspace_snapshot"
    assert payload == {
        "action_type": action_type,
        "content": actual.decode("utf-8"),
        "content_included": True,
        "media_type": result.artifacts[0].media_type,
        "omission_reason": "",
        "path": target,
        "schema_version": "rwkv-lh.post-action-workspace-snapshot.v1",
        "sha256": hashlib.sha256(actual).hexdigest(),
        "size_bytes": len(actual),
    }
    assert state.tasks["T1"].output_refs == [
        "M-T1-A1",
        snapshot_id,
        "T1-A1-R1",
    ]
    assert audits == [
        {
            "action_type": action_type,
            "artifact_id": "T1-A1-R1",
            "attempt_id": "T1-A1",
            "content_included": True,
            "memory_id": snapshot_id,
            "media_type": result.artifacts[0].media_type,
            "omission_reason": "",
            "path": target,
            "reference_or_acceptance_used": False,
            "rwkv_output_modified": False,
            "schema_version": "rwkv-lh.post-action-workspace-snapshot.v1",
            "sha256": hashlib.sha256(actual).hexdigest(),
            "size_bytes": len(actual),
            "source": "post_action_workspace_read",
            "task_id": "T1",
        }
    ]


def test_snapshot_is_visible_only_to_declared_dependency(tmp_path):
    action = TaskAction(
        "write_json",
        {"path": "answer.json", "value": {"name": "Orion", "count": 14}},
    )
    controller, state = make_recording_state(tmp_path, action)
    result = controller.harness.execute(action, state.goal)
    controller._record_artifacts_and_memory(state, "T1", "T1-A1", result)
    snapshot_id = "M-T1-A1-POST-R1"
    dependent = TaskNode(
        "T2",
        "Use exact producer state",
        "Continue from the declared producer",
        dependencies=["T1"],
    )
    unrelated = TaskNode(
        "T3",
        "Unrelated task",
        "Must not receive undeclared producer state",
        inputs=[{"memory_id": snapshot_id}],
    )

    dependent_context = WorkingMemoryBuilder().build(state, dependent)
    unrelated_context = WorkingMemoryBuilder().build(state, unrelated)

    assert "M-T1-A1" in dependent_context.selected_memory_ids
    assert snapshot_id in dependent_context.selected_memory_ids
    assert state.memory_index[snapshot_id].content in dependent_context.to_prompt()
    assert snapshot_id not in unrelated_context.selected_memory_ids
    assert state.memory_index[snapshot_id].content not in unrelated_context.to_prompt()


@pytest.mark.parametrize(
    ("case_name", "expected_reason"),
    [
        ("hash_mismatch", "artifact_hash_mismatch"),
        ("size_mismatch", "artifact_size_mismatch"),
        ("symlink", "artifact_path_uses_symlink"),
        ("parent_traversal", "artifact_path_parent_traversal"),
        ("absolute", "artifact_path_not_workspace_relative"),
    ],
)
def test_untrusted_artifact_observation_fails_closed(
    tmp_path,
    case_name,
    expected_reason,
):
    action = TaskAction(
        "write_file",
        {
            "path": "target.txt",
            "content": "observed",
            "overwrite": True,
            "create_parents": True,
        },
    )
    controller, state = make_recording_state(tmp_path, action)
    workspace = Path(state.goal.workspace_root)
    target = workspace / "target.txt"
    target.write_text("observed", encoding="utf-8")
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    observed_path = "target.txt"
    observed_hash = digest
    observed_size = target.stat().st_size
    if case_name == "hash_mismatch":
        observed_hash = "0" * 64
    elif case_name == "size_mismatch":
        observed_size += 1
    elif case_name == "symlink":
        alias = workspace / "alias.txt"
        alias.symlink_to(target)
        observed_path = "alias.txt"
    elif case_name == "parent_traversal":
        observed_path = "../outside.txt"
    elif case_name == "absolute":
        observed_path = str(target)
    result = ActionResult(
        "write_file",
        True,
        output="file written",
        artifacts=[
            ObservedArtifact(
                observed_path,
                observed_hash,
                "text/plain",
                observed_size,
            )
        ],
    )

    audits = controller._record_artifacts_and_memory(
        state,
        "T1",
        "T1-A1",
        result,
    )

    assert "M-T1-A1-POST-R1" not in state.memory_index
    assert audits[0]["memory_id"] == ""
    assert audits[0]["content_included"] is False
    assert audits[0]["omission_reason"] == expected_reason
    assert state.memory_index["M-T1-A1"].content == "file written"


def test_large_and_non_utf8_snapshots_retain_metadata_without_content(tmp_path):
    large_action = TaskAction(
        "write_file",
        {
            "path": "large.txt",
            "content": "x" * 20_001,
            "overwrite": True,
            "create_parents": True,
        },
    )
    large_controller, large_state = make_recording_state(tmp_path / "large", large_action)
    large_result = large_controller.harness.execute(large_action, large_state.goal)
    large_audits = large_controller._record_artifacts_and_memory(
        large_state,
        "T1",
        "T1-A1",
        large_result,
    )
    large_payload = json.loads(
        large_state.memory_index["M-T1-A1-POST-R1"].content
    )
    assert "content" not in large_payload
    assert large_payload["content_included"] is False
    assert large_payload["omission_reason"] == "content_exceeds_20000_bytes"
    assert large_audits[0]["omission_reason"] == "content_exceeds_20000_bytes"

    binary_action = TaskAction(
        "copy_file",
        {"source": "source.bin", "destination": "copied.bin"},
    )
    binary_controller, binary_state = make_recording_state(
        tmp_path / "binary",
        binary_action,
    )
    binary_workspace = Path(binary_state.goal.workspace_root)
    (binary_workspace / "source.bin").write_bytes(b"\xff\xfe\xfd")
    binary_result = binary_controller.harness.execute(binary_action, binary_state.goal)
    binary_audits = binary_controller._record_artifacts_and_memory(
        binary_state,
        "T1",
        "T1-A1",
        binary_result,
    )
    binary_payload = json.loads(
        binary_state.memory_index["M-T1-A1-POST-R1"].content
    )
    assert "content" not in binary_payload
    assert binary_payload["content_included"] is False
    assert binary_payload["omission_reason"] == "content_not_utf8"
    assert binary_audits[0]["omission_reason"] == "content_not_utf8"


def test_failed_and_read_only_actions_do_not_create_snapshot_memory(tmp_path):
    failed_action = TaskAction(
        "write_file",
        {
            "path": "target.txt",
            "content": "unused",
            "overwrite": True,
            "create_parents": True,
        },
    )
    failed_controller, failed_state = make_recording_state(
        tmp_path / "failed",
        failed_action,
    )
    failed_result = ActionResult(
        "write_file",
        False,
        error={"type": "FixtureFailure", "message": "not executed"},
    )
    failed_audits = failed_controller._record_artifacts_and_memory(
        failed_state,
        "T1",
        "T1-A1",
        failed_result,
    )
    assert failed_audits == []
    assert not any(
        entry.kind == "post_action_workspace_snapshot"
        for entry in failed_state.memory_index.values()
    )

    read_action = TaskAction("read_file", {"path": "target.txt"})
    read_controller, read_state = make_recording_state(tmp_path / "read", read_action)
    read_workspace = Path(read_state.goal.workspace_root)
    (read_workspace / "target.txt").write_text("read only", encoding="utf-8")
    read_result = read_controller.harness.execute(read_action, read_state.goal)
    read_audits = read_controller._record_artifacts_and_memory(
        read_state,
        "T1",
        "T1-A1",
        read_result,
    )
    assert read_audits == []
    assert not any(
        entry.kind == "post_action_workspace_snapshot"
        for entry in read_state.memory_index.values()
    )


class SnapshotCompletionModel:
    def cross_validate(
        self,
        state,
        task,
        context,
        persist,
        *,
        action_result=None,
        validation_results=None,
    ):
        return CrossValidationDecision(
            True,
            "fixture semantic pass",
            [
                {
                    "criterion_id": criterion_id,
                    "subject_task_id": task.task_id,
                    "producer_task_id": task.task_id,
                    "comparison": "exact_equals",
                    "actual": {
                        "read_op": "action_output_text",
                        "arguments": {},
                        "transforms": [],
                    },
                    "expected": {
                        "read_op": "goal_literal",
                        "arguments": {
                            "goal_quote": "Write",
                            "value": str((action_result or {}).get("output") or ""),
                        },
                        "transforms": [],
                    },
                }
                for criterion_id in task.satisfies_criteria
            ],
        )

    def final_answer(self, state, context, persist):
        return "fixture verified completion"

    def commit_criterion_evidence(
        self,
        state,
        context,
        persist,
        *,
        criterion_ids,
        source_catalog,
    ):
        del state, context, persist
        actual_sources = source_catalog["causal_actual_sources"]
        assert actual_sources
        return {
            "decision": "pass",
            "bindings": [
                {
                    "criterion_id": criterion_id,
                    "actual_ref": actual_sources[0]["ref"],
                    "expected_ref": "GOAL",
                    "reason": "fixture provenance pass",
                }
                for criterion_id in criterion_ids
            ],
        }


def test_snapshot_audit_event_and_state_survive_store_reload(tmp_path):
    workspace = tmp_path / "workspace"
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(make_goal(workspace), "ROUND22-PERSISTED-SNAPSHOT")
    action = TaskAction(
        "write_file",
        {
            "path": "answer.txt",
            "content": "Orion\n14\n",
            "overwrite": True,
            "create_parents": True,
        },
    )
    task = TaskNode(
        "T1",
        "Write answer",
        "Write the exact answer",
        satisfies_criteria=["GC1"],
        action=action,
        completion_criteria=[
            ValidationSpec(
                "file_content",
                {"path": "answer.txt", "expected_content": "Orion\n14\n"},
            )
        ],
    )
    state.tasks = {"T1": task}
    state.status = RunStatus.RUNNING
    state = store.save(state, event_type="plan_saved")

    result = LongHorizonController(
        store,
        model=SnapshotCompletionModel(),
    ).run(state.run_id)
    loaded = store.load(state.run_id)
    events = store.event_records(state.run_id)
    event_types = [event["type"] for event in events]

    assert result.state.status == RunStatus.COMPLETED
    assert "M-T1-A1-POST-R1" in loaded.memory_index
    assert loaded.memory_index["M-T1-A1"].content == "file written"
    assert event_types.index("action_returned") < event_types.index(
        "post_action_workspace_snapshot_recorded"
    )
    audit = next(
        event["data"]
        for event in events
        if event["type"] == "post_action_workspace_snapshot_recorded"
    )
    assert audit["memory_id"] == "M-T1-A1-POST-R1"
    assert audit["artifact_id"] == "T1-A1-R1"
    assert audit["content_included"] is True
    assert audit["reference_or_acceptance_used"] is False
    assert audit["rwkv_output_modified"] is False
    assert "content" not in audit
    revision = loaded.artifact_revisions["answer.txt"][0]
    assert revision.artifact_id == "T1-A1-R1"
    assert revision.outcome_type == "success"
    assert revision.task_commit_status == "committed"


def test_declared_negative_outcome_is_an_observation_not_a_controller_answer(
    tmp_path,
):
    goal = make_goal(tmp_path / "workspace")
    state = RunState("ROUND25-TYPED-OUTCOME", goal)
    task = TaskNode(
        "T1",
        "Observe optional config",
        "Read config if it exists and preserve absence as an observation",
        operation_kind="observe",
        subject_key="workspace/config",
        phase_key="discover",
        effect_targets=["config.json"],
        expected_outcomes=["success", "not_found"],
        postcondition="The config presence or absence is observed",
        action=TaskAction("read_json", {"path": "config.json"}),
        completion_criteria=[
            ValidationSpec("action_succeeded", {}),
            ValidationSpec("file_exists", {"path": "config.json"}),
        ],
        attempt_ids=["T1-A1"],
    )
    state.tasks = {"T1": task}
    result = ActionResult(
        "read_json",
        False,
        error={"type": "FileNotFoundError", "message": "config.json"},
    )

    validation, effect_observed, task_committed = LongHorizonController(
        LongHorizonStore(tmp_path / "state")
    )._validate_task_result(state, task, result)

    assert result.outcome_type == "not_found"
    assert effect_observed is True
    assert task_committed is True
    typed = next(item for item in validation if item.kind == "declared_outcome_observed")
    assert typed.evidence == {
        "outcome_type": "not_found",
        "expected_outcomes": ["success", "not_found"],
        "tool_success": False,
    }
