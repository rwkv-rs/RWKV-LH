from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from rwkv_lh.schema import (
    ActionRecord,
    ActionStatus,
    ArtifactRecord,
    CausalEvent,
    CausalEventDraft,
    GoalState,
    RunState,
    RunStatus,
    TaskAction,
    action_fingerprint,
    utc_now,
)
from rwkv_lh.store import ConcurrentStateError, LongHorizonStore


def literal(tmp_path: Path) -> GoalState:
    workspace = tmp_path / "workspace"
    workspace.mkdir(exist_ok=True)
    return GoalState.create(
        request="Read input.txt and write output.txt.",
        constraints=["workspace only", "workspace only"],
        workspace_root=workspace,
    )


def action_record() -> ActionRecord:
    action = TaskAction("write_file", {"path": "out.txt", "content": "ok"})
    return ActionRecord(
        action_id="A00001",
        sequence=1,
        status=ActionStatus.SUCCEEDED,
        action_type=action.action_type,
        arguments=action.arguments,
        wire_arguments=action.arguments,
        action_fingerprint=action_fingerprint(action),
        idempotency_key="idem-1",
        decision_id="D-1",
        request_id="MR-1",
        started_at=utc_now(),
        ended_at=utc_now(),
        result={"action_type": "write_file", "success": True, "output": "file written"},
        outcome_type="success",
    )


def save_action_started(store: LongHorizonStore, state: RunState) -> RunState:
    action = action_record()
    action.status = ActionStatus.RUNNING
    action.ended_at = None
    action.result = None
    action.outcome_type = "pending"
    return store.save(
        state,
        causal_event=CausalEventDraft.create(
            "action_started",
            {"action_id": action.action_id, "action": action.to_dict()},
            subject_id=action.action_id,
            cause_id=state.causal_order[-1],
        ),
    )


def save_action_finished(store: LongHorizonStore, state: RunState) -> RunState:
    action = ActionRecord.from_dict(state.actions["A00001"].to_dict())
    action.status = ActionStatus.SUCCEEDED
    action.ended_at = utc_now()
    action.result = {
        "action_type": "write_file", "success": True, "output": "file written"
    }
    action.outcome_type = "success"
    return store.save(
        state,
        causal_event=CausalEventDraft.create(
            "action_finished",
            {
                "action_id": action.action_id,
                "action": action.to_dict(),
                "artifacts": [],
                "artifact_revisions": [],
            },
            subject_id=action.action_id,
            cause_id=state.causal_order[-1],
        ),
    )


def test_literal_request_is_immutable_and_deduplicates_constraints(tmp_path: Path) -> None:
    goal = literal(tmp_path)
    assert goal.request == "Read input.txt and write output.txt."
    assert goal.constraints == ("workspace only",)
    assert goal.verify_digest()
    assert GoalState.from_dict(goal.to_dict()) == goal


def test_literal_request_digest_rejects_mutation(tmp_path: Path) -> None:
    payload = literal(tmp_path).to_dict()
    payload["request"] = "changed"
    with pytest.raises(ValueError, match="digest"):
        GoalState.from_dict(payload)


def test_run_state_round_trip_rebuilds_action_projection_from_events(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = save_action_started(store, store.create_run(literal(tmp_path), "R1"))
    state = save_action_finished(store, state)
    payload = state.to_dict()
    assert "actions" in payload
    assert "tasks" not in payload
    assert "attempts" not in payload
    restored = RunState.from_dict(json.loads(json.dumps(payload)))
    assert restored.actions["A00001"].action_type == "write_file"
    assert restored.actions["A00001"].status == ActionStatus.SUCCEEDED
    assert restored.actions["A00001"].result == {
        "action_type": "write_file", "success": True, "output": "file written"
    }


def test_old_v16_state_is_not_silently_loaded(tmp_path: Path) -> None:
    payload = RunState(run_id="R1", goal=literal(tmp_path)).to_dict()
    payload["schema_version"] = "long-horizon.run.v16"
    with pytest.raises(ValueError, match="unsupported run schema"):
        RunState.from_dict(payload)


def test_action_fingerprint_is_key_order_stable() -> None:
    left = TaskAction("write_json", {"path": "a.json", "value": {"a": 1, "b": 2}})
    right = TaskAction("write_json", {"value": {"b": 2, "a": 1}, "path": "a.json"})
    assert action_fingerprint(left) == action_fingerprint(right)


def test_causal_event_round_trip_and_digest() -> None:
    draft = CausalEventDraft.create(
        "action_started",
        {"action_id": "A00001"},
        subject_id="A00001",
    )
    record = CausalEvent.create(
        event_id="CE-000001",
        run_id="RUN",
        sequence=1,
        parent_id=None,
        draft=draft,
        created_at="2026-08-15T00:00:00.000+00:00",
    )
    assert CausalEvent.from_dict(record.to_dict()) == record
    damaged = record.to_dict()
    damaged["payload"]["action_id"] = "A99999"
    with pytest.raises(ValueError, match="digest"):
        CausalEvent.from_dict(damaged)


def test_unregistered_event_type_is_rejected() -> None:
    with pytest.raises(ValueError, match="unregistered"):
        CausalEventDraft.create("invented_event", {}, subject_id="RUN")


def test_store_writes_one_common_envelope_for_every_revision(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(literal(tmp_path), "RUN-1")
    assert state.causal_order == ["CE-000001"]
    state = store.save(
        state,
        causal_event=CausalEventDraft.create(
            "run_started",
            {"status": "running"},
            subject_id=state.run_id,
            cause_id=state.causal_order[-1],
        ),
    )
    assert state.causal_order == ["CE-000001", "CE-000002"]
    records = [state.causal_records[item] for item in state.causal_order]
    assert records[1].parent_id == records[0].event_id
    assert records[1].event_type == "run_started"
    assert records[1].payload_schema == "rwkv-lh.run-started.v1"


def test_store_action_index_contains_only_action_projection(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(literal(tmp_path), "RUN-2")
    state = save_action_started(store, state)
    state = save_action_finished(store, state)
    with sqlite3.connect(store.database_path) as connection:
        row = connection.execute(
            "SELECT action_id, status, sequence, operation FROM action_index"
        ).fetchone()
        tables = {
            item[0]
            for item in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")
        }
    assert row == ("A00001", "succeeded", 1, "write_file")
    assert "task_index" not in tables


def test_store_rejects_stale_revision(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    first = store.create_run(literal(tmp_path), "RUN-3")
    stale = RunState.from_dict(first.to_dict())
    first = store.save(
        first,
        causal_event=CausalEventDraft.create(
            "state_saved", {}, subject_id=first.run_id, cause_id=first.causal_order[-1]
        ),
    )
    with pytest.raises(ConcurrentStateError):
        store.save(
            stale,
            causal_event=CausalEventDraft.create(
                "state_saved", {}, subject_id=stale.run_id, cause_id=stale.causal_order[-1]
            ),
        )
    assert store.load("RUN-3").revision == first.revision


def test_store_event_and_checkpoint_sequences_align(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state", checkpoint_retention=50)
    state = store.create_run(literal(tmp_path), "RUN-4")
    for index in range(3):
        state = store.save(
            state,
            causal_event=CausalEventDraft.create(
                "state_saved",
                {"index": index},
                subject_id=state.run_id,
                cause_id=state.causal_order[-1],
            ),
        )
    events = store.event_records("RUN-4")
    checkpoints = store.checkpoint_records("RUN-4")
    assert [item["revision"] for item in events] == [0, 1, 2, 3]
    assert [item["revision"] for item in checkpoints] == [0, 1, 2, 3]


def test_artifact_record_is_rebuilt_from_finished_action_event(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = save_action_started(store, store.create_run(literal(tmp_path), "R"))
    artifact = ArtifactRecord(
        artifact_id="ART-1",
        action_id="A00001",
        path="out.txt",
        sha256="a" * 64,
        media_type="text/plain",
        size_bytes=2,
    )
    action = ActionRecord.from_dict(state.actions["A00001"].to_dict())
    action.status = ActionStatus.SUCCEEDED
    action.ended_at = utc_now()
    action.result = {
        "action_type": "write_file", "success": True, "output": "file written"
    }
    action.outcome_type = "success"
    action.artifact_refs = [artifact.artifact_id]
    state = store.save(
        state,
        causal_event=CausalEventDraft.create(
            "action_finished",
            {
                "action_id": action.action_id,
                "action": action.to_dict(),
                "artifacts": [artifact.__dict__],
                "artifact_revisions": [],
            },
            subject_id=action.action_id,
            cause_id=state.causal_order[-1],
        ),
    )
    restored = RunState.from_dict(state.to_dict(include_projections=False))
    assert restored.artifacts["ART-1"].action_id == "A00001"
    assert restored.artifacts["ART-1"].size_bytes == 2


def test_projection_fields_cannot_override_event_authority(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = save_action_started(store, store.create_run(literal(tmp_path), "RUN-X"))
    state = save_action_finished(store, state)
    payload = state.to_dict()
    payload["actions"]["A00001"]["status"] = "running"
    restored = RunState.from_dict(payload)
    assert restored.actions["A00001"].status == ActionStatus.SUCCEEDED


def test_projection_digest_tampering_is_rejected(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = store.create_run(literal(tmp_path), "RUN-DIGEST")
    payload = state.to_dict(include_projections=False)
    payload["projection_digest"] = "0" * 64
    with pytest.raises(ValueError, match="projection digest"):
        RunState.from_dict(payload)


def test_causal_order_tampering_is_rejected(tmp_path: Path) -> None:
    store = LongHorizonStore(tmp_path / "state")
    state = save_action_started(store, store.create_run(literal(tmp_path), "RUN-ORDER"))
    payload = state.to_dict(include_projections=False)
    payload["causal_order"] = list(reversed(payload["causal_order"]))
    with pytest.raises(ValueError, match="sequence or parent"):
        RunState.from_dict(payload)
