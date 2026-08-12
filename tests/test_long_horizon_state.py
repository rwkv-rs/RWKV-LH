import sqlite3
import tempfile
import threading
from pathlib import Path

import pytest

from rwkv_lh.schema import (
    LEGACY_RUN_SCHEMA_VERSION,
    RUN_SCHEMA_VERSION,
    GoalCriterion,
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
    TaskNode,
    TaskStatus,
)
from rwkv_lh.store import ConcurrentStateError, LongHorizonStore
from rwkv_lh.task_graph import TaskGraph, TaskGraphError


def make_goal(root: Path) -> GoalState:
    return GoalState.create(
        objective="Create a verified artifact",
        original_request="Create a verified artifact without leaving the workspace",
        constraints=["Only modify the scoped workspace"],
        success_criteria=[GoalCriterion("GC1", "artifact.txt exists")],
        workspace_root=root,
    )


def make_task(task_id: str, dependencies=None, priority=50) -> TaskNode:
    return TaskNode(
        task_id=task_id,
        title=f"Task {task_id}",
        description=f"Execute {task_id}",
        dependencies=list(dependencies or []),
        priority=priority,
        action=TaskAction("write_file", {"path": f"{task_id}.txt", "content": task_id}),
    )


def test_goal_digest_detects_mutation():
    with tempfile.TemporaryDirectory() as directory:
        goal = make_goal(Path(directory))
        payload = goal.to_dict()
        payload["objective"] = "A different goal"
        with pytest.raises(ValueError, match="goal digest mismatch"):
            GoalState.from_dict(payload)


def test_store_rejects_replacing_the_immutable_goal():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-GOAL-LOCK")
        state.goal = GoalState.create(
            objective="Changed objective",
            original_request="Changed objective",
            constraints=[],
            success_criteria=[GoalCriterion("GC2", "different")],
            workspace_root=root / "workspace",
        )
        with pytest.raises(ValueError, match="immutable goal digest changed"):
            store.save(state)


def test_task_graph_orders_ready_tasks_and_enforces_dependencies():
    first = make_task("T1", priority=10)
    second = make_task("T2", ["T1"], priority=100)
    third = make_task("T3", priority=20)
    graph = TaskGraph({task.task_id: task for task in (first, second, third)})
    assert [task.task_id for task in graph.ready_tasks()] == ["T3", "T1"]
    with pytest.raises(TaskGraphError, match="unmet dependencies"):
        graph.transition("T2", TaskStatus.RUNNING)
    graph.transition("T1", TaskStatus.RUNNING)
    graph.transition("T1", TaskStatus.COMPLETED)
    assert [task.task_id for task in graph.ready_tasks()] == ["T2", "T3"]


def test_task_graph_rejects_cycles_and_completed_reexecution():
    first = make_task("T1", ["T2"])
    second = make_task("T2", ["T1"])
    with pytest.raises(TaskGraphError, match="cycle"):
        TaskGraph({"T1": first, "T2": second})

    graph = TaskGraph({"T3": make_task("T3")})
    graph.transition("T3", TaskStatus.RUNNING)
    graph.transition("T3", TaskStatus.COMPLETED)
    with pytest.raises(TaskGraphError, match="invalid task transition"):
        graph.transition("T3", TaskStatus.RUNNING)


def test_store_round_trip_and_stale_revision_rejection():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-ROUNDTRIP")
        stale = RunState.from_dict(state.to_dict())
        state.tasks["T1"] = make_task("T1")
        state = store.save(state, event_type="plan_saved")
        loaded = store.load(state.run_id)
        assert loaded.revision == 1
        assert loaded.tasks["T1"].action.action_type == "write_file"
        with pytest.raises(ConcurrentStateError):
            store.save(stale)


def test_store_recovers_from_corrupt_state_snapshot():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-RECOVER")
        state.tasks["T1"] = make_task("T1")
        state = store.save(state, event_type="plan_saved")
        with sqlite3.connect(store.database_path) as connection:
            connection.execute(
                "UPDATE runs SET state_json = ? WHERE run_id = ?",
                ("{corrupt", state.run_id),
            )
        recovered = store.load(state.run_id)
        assert recovered.revision == state.revision
        assert "T1" in recovered.tasks
        assert store.load(state.run_id).revision == state.revision


def test_old_checkpoint_recovery_keeps_revisions_monotonic():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-OLD-CHECKPOINT")
        state = store.save(state, event_type="revision_one")
        state = store.save(state, event_type="revision_two")
        with sqlite3.connect(store.database_path) as connection:
            connection.execute(
                "UPDATE runs SET state_json = ? WHERE run_id = ?",
                ("{corrupt", state.run_id),
            )
            connection.execute(
                "UPDATE checkpoints SET state_json = ? WHERE run_id = ? AND revision = ?",
                ("{corrupt", state.run_id, state.revision),
            )
        recovered = store.load(state.run_id)
        assert recovered.revision == 3
        recovered = store.save(recovered, event_type="after_recovery")
        assert recovered.revision == 4
        assert [event["revision"] for event in store.event_records(state.run_id)] == [0, 1, 2, 3, 4]


def test_controller_lease_prevents_two_writers():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-LEASE")
        attempted = threading.Event()
        errors = []

        def contender():
            attempted.set()
            try:
                with store.controller_lease(state.run_id, timeout_seconds=0.05):
                    pass
            except Exception as exc:
                errors.append(exc)

        with store.controller_lease(state.run_id):
            with sqlite3.connect(store.database_path) as connection:
                lease_count = connection.execute(
                    "SELECT COUNT(*) FROM run_leases WHERE run_id = ?",
                    (state.run_id,),
                ).fetchone()[0]
            assert lease_count == 1
            worker = threading.Thread(target=contender)
            worker.start()
            attempted.wait(timeout=1)
            worker.join(timeout=1)
        assert len(errors) == 1
        assert isinstance(errors[0], TimeoutError)


def test_store_event_revisions_are_monotonic():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-EVENTS")
        state = store.save(state, event_type="noop")
        events = store.event_records(state.run_id)
        assert [event["revision"] for event in events] == [0, 1]


def test_store_projects_tasks_and_checkpoints_transactionally():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs")
        state = store.create_run(make_goal(root / "workspace"), "LH-PROJECTION")
        state.tasks["T1"] = make_task("T1", priority=91)
        state = store.save(state, event_type="plan_saved")
        with sqlite3.connect(store.database_path) as connection:
            task_row = connection.execute(
                "SELECT status, required, active, priority FROM task_index WHERE run_id = ?",
                (state.run_id,),
            ).fetchone()
            checkpoint_count = connection.execute(
                "SELECT COUNT(*) FROM checkpoints WHERE run_id = ?",
                (state.run_id,),
            ).fetchone()[0]
        assert task_row == ("pending", 1, 1, 91)
        assert checkpoint_count == 2
        checkpoints = store.checkpoint_records(state.run_id)
        assert [item["revision"] for item in checkpoints] == [0, 1]
        assert [item["event_type"] for item in checkpoints] == [
            "run_created",
            "plan_saved",
        ]
        assert checkpoints[-1]["state"]["tasks"]["T1"]["priority"] == 91


def test_checkpoint_retention_does_not_keep_every_planning_request():
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        store = LongHorizonStore(root / "runs", checkpoint_retention=5)
        state = store.create_run(make_goal(root / "workspace"), "LH-RETENTION")
        state.status = RunStatus.PLANNING
        for index in range(12):
            state = store.save(state, event_type="model_request_returned", event={"index": index})
        with sqlite3.connect(store.database_path) as connection:
            rows = connection.execute(
                "SELECT milestone, COUNT(*) FROM checkpoints WHERE run_id = ? GROUP BY milestone",
                (state.run_id,),
            ).fetchall()
        assert dict(rows) == {0: 5, 1: 1}


def test_v1_run_migration_does_not_promote_ambiguous_goal_bindings():
    with tempfile.TemporaryDirectory() as directory:
        state = RunState("LH-V1-MIGRATION", make_goal(Path(directory)))
        state.tasks = {
            "T1": TaskNode(
                "T1",
                "Legacy task",
                "Legacy ambiguous criterion binding",
                goal_criteria=["GC1"],
                satisfies_criteria=["GC1"],
            )
        }
        payload = state.to_dict()
        payload["schema_version"] = LEGACY_RUN_SCHEMA_VERSION
        payload.pop("criterion_evidence")
        payload.pop("recovery_states")
        payload.pop("model_states")
        payload.pop("next_task_sequence")
        payload["tasks"]["T1"].pop("satisfies_criteria")

        migrated = RunState.from_dict(payload)

        assert migrated.schema_version == RUN_SCHEMA_VERSION
        assert migrated.tasks["T1"].goal_criteria == ["GC1"]
        assert migrated.tasks["T1"].satisfies_criteria == []
        assert migrated.criterion_evidence == {}
        assert migrated.next_task_sequence == 2


def test_model_task_ids_are_local_and_deterministically_rewritten():
    proposals = [
        TaskNode("T1", "Local first", "First local task"),
        TaskNode(
            "T9",
            "Local second",
            "Second local task",
            dependencies=["T1"],
        ),
    ]

    tasks, mapping, next_sequence = TaskGraph.materialize_model_tasks(
        proposals,
        existing_ids={"T1", "T9"},
        next_sequence=1,
    )

    assert mapping == {"T1": "T2", "T9": "T3"}
    assert [task.task_id for task in tasks] == ["T2", "T3"]
    assert tasks[1].dependencies == ["T2"]
    assert next_sequence == 4
    assert [task.task_id for task in proposals] == ["T1", "T9"]
