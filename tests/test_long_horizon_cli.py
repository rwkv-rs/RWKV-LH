from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace

from rwkv_lh.proactive import JobStatus, ProactiveJob
from rwkv_lh.schema import (
    CausalEvent,
    CausalEventDraft,
    GoalState,
    RunState,
    RunStatus,
)
from scripts import run_long_horizon
from scripts.run_long_horizon import _parser, _proactive_handler, _scheduled_payload


def test_start_and_enqueue_accept_explicit_state_router_shadow(tmp_path) -> None:
    parser = _parser()
    start = parser.parse_args(
        [
            "--state-directory",
            str(tmp_path / "state"),
            "start",
            "--request",
            "test",
            "--workspace",
            str(tmp_path / "start-workspace"),
            "--state-router-shadow",
        ]
    )
    assert start.state_router_shadow is True

    enqueue = parser.parse_args(
        [
            "enqueue",
            "--request",
            "test",
            "--workspace",
            str(tmp_path / "enqueue-workspace"),
            "--state-router-shadow",
        ]
    )
    policy = _scheduled_payload(enqueue)["runtime_policy"]
    assert policy["state_router"] == {
        "schema_version": "rwkv-lh.state-router-runtime-policy.v1",
        "mode": "shadow",
    }


def test_resolved_historical_supervisor_pending_does_not_retry_later_stop(
    tmp_path,
    monkeypatch,
) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    state = RunState(
        run_id="RUN-RESOLVED-PENDING",
        goal=GoalState.create(
            request="Complete the task.",
            constraints=(),
            workspace_root=workspace,
        ),
        status=RunStatus.INTERRUPTED,
    )

    def append(event_type, payload):
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

    append(
        "supervisor_call_pending",
        {"pending_id": "SUP-PENDING-contract_review-0001", "phase": "contract_review"},
    )
    append(
        "supervisor_call_resolved",
        {"pending_id": "SUP-PENDING-contract_review-0001", "phase": "contract_review"},
    )
    append("run_interrupted", {"reason": "contract_graph_evidence_stagnant"})

    class Store:
        def load(self, run_id):
            assert run_id == state.run_id
            return state

    class Controller:
        def run(self, run_id):
            assert run_id == state.run_id
            return SimpleNamespace(state=state)

    monkeypatch.setattr(
        run_long_horizon,
        "build_product_controller",
        lambda *args, **kwargs: Controller(),
    )
    job = ProactiveJob(
        job_id="JOB-1",
        payload={"request": state.goal.request, "workspace": str(workspace)},
        status=JobStatus.RUNNING,
        due_at=datetime.now(timezone.utc).isoformat(),
        attempts=1,
        max_attempts=3,
        run_id=state.run_id,
    )

    outcome = _proactive_handler(
        job,
        store=Store(),
        state_root=tmp_path / "state",
    )

    assert outcome.completed is False
    assert outcome.retryable is False
    assert outcome.error == "contract_graph_evidence_stagnant"
