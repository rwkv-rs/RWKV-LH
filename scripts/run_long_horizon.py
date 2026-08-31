"""Create, resume, and inspect persistent Long-Horizon Agent runs."""

from __future__ import annotations

import argparse
import json
import os
import socket
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from rwkv_lh.model import LongHorizonModel
from rwkv_lh.proactive import ProactiveJob, ProactiveOutcome, ProactiveStore, ProactiveWorker
from rwkv_lh.product_runtime import build_product_controller
from rwkv_lh.retrieval import (
    NetworkPolicyMode,
    RetrievalRuntimeConfig,
    runtime_policy_document,
)
from rwkv_lh.schema import RunStatus
from rwkv_lh.store import LongHorizonStore, StateRecoveryError
from rwkv_lh.trace_projection import (
    project_run_activity,
    unresolved_supervisor_pending,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local RWKV Long-Horizon Agent")
    parser.add_argument(
        "--state-directory",
        default="data/runs",
        help="SQLite and artifact directory",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    start = subparsers.add_parser("start", help="Create and execute a new run")
    request = start.add_mutually_exclusive_group(required=True)
    request.add_argument("--request", help="Long-horizon user request")
    request.add_argument("--request-file", help="UTF-8 file containing the request")
    start.add_argument("--workspace", required=True, help="Scoped task workspace")
    start.add_argument("--constraint", action="append", default=[])
    start.add_argument("--run-id", default=None)
    start.add_argument(
        "--supervisor",
        choices=("none", "contract_graph"),
        default="none",
        help="Use the configured strong model for contract planning/review",
    )
    start.add_argument(
        "--network-policy",
        choices=[item.value for item in NetworkPolicyMode],
        default=NetworkPolicyMode.OFFLINE.value,
        help="Immutable run-level network policy; auto_public lets RWKV choose public retrieval tools",
    )
    start.add_argument(
        "--approve-workspace-egress",
        action="store_true",
        help="Approve egress only from paths declared with --public-workspace-path",
    )
    start.add_argument(
        "--public-workspace-path",
        action="append",
        default=[],
        help="Workspace-relative file or directory explicitly declared public (repeatable)",
    )
    start.add_argument(
        "--state-router-shadow",
        action="store_true",
        help="Record advisory State Router predictions without affecting execution",
    )

    resume = subparsers.add_parser("resume", help="Resume an existing run")
    resume.add_argument("run_id")

    status = subparsers.add_parser("status", help="Print structured run state")
    status.add_argument("run_id")

    enqueue = subparsers.add_parser(
        "enqueue", help="Persist a one-shot or interval-triggered proactive run"
    )
    queued_request = enqueue.add_mutually_exclusive_group(required=True)
    queued_request.add_argument("--request")
    queued_request.add_argument("--request-file")
    enqueue.add_argument("--workspace", required=True)
    enqueue.add_argument("--constraint", action="append", default=[])
    enqueue.add_argument(
        "--network-policy",
        choices=[item.value for item in NetworkPolicyMode],
        default=NetworkPolicyMode.OFFLINE.value,
    )
    enqueue.add_argument("--approve-workspace-egress", action="store_true")
    enqueue.add_argument("--public-workspace-path", action="append", default=[])
    enqueue.add_argument("--state-router-shadow", action="store_true")
    enqueue.add_argument(
        "--supervisor", choices=("none", "contract_graph"), default="contract_graph"
    )
    enqueue.add_argument("--due-at", default="", help="ISO-8601 time; default now")
    enqueue.add_argument("--interval-seconds", type=int, default=0)
    enqueue.add_argument("--max-attempts", type=int, default=5)
    enqueue.add_argument("--max-transitions", type=int, default=200)
    enqueue.add_argument("--require-approval", default="")

    serve = subparsers.add_parser("serve", help="Run the persistent proactive worker")
    serve.add_argument("--once", action="store_true")
    serve.add_argument("--poll-seconds", type=float, default=2.0)
    serve.add_argument("--worker-id", default=f"{socket.gethostname()}-{os.getpid()}")

    subparsers.add_parser("jobs", help="List proactive jobs")
    approve = subparsers.add_parser("approve", help="Decide a pending approval")
    approve.add_argument("approval_id")
    approve.add_argument("--reject", action="store_true")
    approve.add_argument("--by", default="local-user")
    approve.add_argument("--reason", default="")
    notifications = subparsers.add_parser("notifications", help="Read local lifecycle notifications")
    notifications.add_argument("--after", type=int, default=0)
    return parser


def _request_text(arguments: argparse.Namespace) -> str:
    if arguments.request is not None:
        return str(arguments.request).strip()
    return Path(arguments.request_file).read_text(encoding="utf-8").strip()


def _summary(state, final_output: str = "") -> dict[str, Any]:
    activity = project_run_activity(state)
    return {
        "run_id": state.run_id,
        "revision": state.revision,
        "status": state.status.value,
        "request": state.goal.request,
        "runtime_policy": state.goal.runtime_policy,
        "actions": {
            item["activity_id"]: {
                key: value for key, value in item.items() if key != "activity_id"
            }
            for item in activity["actions"]
        },
        "direct_action_count": len(activity["direct_actions"]),
        "atom_action_count": len(activity["atom_actions"]),
        "artifact_count": len(state.artifacts),
        "model_requests": activity["rwkv_model_requests"],
        "direct_model_requests": activity["direct_model_requests"],
        "atom_model_requests": activity["atom_model_requests"],
        "final_output": final_output,
    }


def _retrieval_config(arguments: argparse.Namespace) -> RetrievalRuntimeConfig:
    return RetrievalRuntimeConfig(
        mode=NetworkPolicyMode(arguments.network_policy),
        explicit_approval=bool(arguments.approve_workspace_egress),
        public_workspace_paths=tuple(arguments.public_workspace_path or []),
    )


def _scheduled_payload(arguments: argparse.Namespace) -> dict[str, Any]:
    workspace = Path(arguments.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    return {
        "schema_version": "rwkv-lh.proactive-run-request.v1",
        "request": _request_text(arguments),
        "workspace": str(workspace),
        "constraints": list(arguments.constraint or []),
        "runtime_policy": runtime_policy_document(
            _retrieval_config(arguments),
            supervisor_mode=arguments.supervisor,
            state_router_mode=(
                "shadow" if bool(arguments.state_router_shadow) else "disabled"
            ),
        ),
        "max_transitions": max(1, min(int(arguments.max_transitions), 500)),
    }


def _job_dict(job: ProactiveJob) -> dict[str, Any]:
    return {
        "job_id": job.job_id,
        "run_id": job.run_id,
        "trigger_id": job.trigger_id,
        "concurrency_key": job.concurrency_key,
        "status": job.status.value,
        "due_at": job.due_at,
        "attempts": job.attempts,
        "lease_generation": job.lease_generation,
        "max_attempts": job.max_attempts,
        "approval_id": job.approval_id,
        "lease_owner": job.lease_owner,
        "lease_until": job.lease_until,
        "last_error": job.last_error,
        "payload": dict(job.payload),
    }


def _last_terminal_reason(state) -> str:
    for event_id in reversed(state.causal_order):
        event = state.causal_records[event_id]
        if event.event_type in {"run_interrupted", "run_failed"}:
            return str(event.payload.get("reason") or "")
    return ""


def _proactive_handler(
    job: ProactiveJob,
    *,
    store: LongHorizonStore,
    state_root: Path,
) -> ProactiveOutcome:
    payload = dict(job.payload)
    run_id = job.run_id or f"PROACTIVE-{job.job_id}"
    try:
        state = store.load(run_id)
    except StateRecoveryError as exc:
        if not str(exc).startswith("unknown run:"):
            raise
        goal = LongHorizonModel.create_literal_goal(
            str(payload.get("request") or ""),
            str(payload.get("workspace") or ""),
            constraints=[str(item) for item in payload.get("constraints") or []],
            runtime_policy=dict(payload.get("runtime_policy") or {}),
        )
        state = store.create_run(goal, run_id)
    controller = build_product_controller(
        store,
        state,
        state_root=state_root,
        max_transitions=max(1, min(int(payload.get("max_transitions", 200)), 500)),
    )
    result = controller.run(run_id)
    if result.state.status == RunStatus.COMPLETED:
        return ProactiveOutcome(True, run_id=run_id)
    reason = _last_terminal_reason(result.state)
    pending_supervisor = bool(unresolved_supervisor_pending(result.state))
    retryable = pending_supervisor or reason == "model_transport_unavailable"
    return ProactiveOutcome(
        False,
        run_id=run_id,
        retryable=retryable,
        error=reason or result.state.status.value,
    )


def main() -> int:
    arguments = _parser().parse_args()
    state_root = Path(arguments.state_directory).expanduser().resolve()
    store = LongHorizonStore(state_root)
    if arguments.command == "status":
        state = store.load(arguments.run_id)
        print(json.dumps(_summary(state, state.final_output), ensure_ascii=False, indent=2))
        return 0

    proactive = (
        ProactiveStore(state_root / "proactive")
        if arguments.command
        in {"jobs", "notifications", "approve", "enqueue", "serve"}
        else None
    )

    if arguments.command == "jobs":
        assert proactive is not None
        print(
            json.dumps(
                [_job_dict(item) for item in proactive.jobs()],
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if arguments.command == "notifications":
        assert proactive is not None
        print(
            json.dumps(
                proactive.notifications(after=arguments.after),
                ensure_ascii=False,
                indent=2,
            )
        )
        return 0

    if arguments.command == "approve":
        assert proactive is not None
        job = proactive.decide_approval(
            arguments.approval_id,
            approved=not arguments.reject,
            decided_by=arguments.by,
            reason=arguments.reason,
        )
        print(json.dumps(_job_dict(job), ensure_ascii=False, indent=2))
        return 0

    if arguments.command == "enqueue":
        assert proactive is not None
        payload = _scheduled_payload(arguments)
        due = (
            datetime.fromisoformat(arguments.due_at.replace("Z", "+00:00"))
            if arguments.due_at
            else datetime.now(timezone.utc)
        )
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        if arguments.interval_seconds:
            trigger_id = proactive.schedule_interval(
                payload,
                interval_seconds=arguments.interval_seconds,
                first_fire_at=due,
                max_attempts=arguments.max_attempts,
                approval_kind=arguments.require_approval,
                concurrency_key=f"workspace:{payload['workspace']}",
            )
            print(json.dumps({"trigger_id": trigger_id}, ensure_ascii=False, indent=2))
        else:
            job = proactive.enqueue(
                payload,
                due_at=due,
                max_attempts=arguments.max_attempts,
                approval_kind=arguments.require_approval,
                concurrency_key=f"workspace:{payload['workspace']}",
            )
            print(json.dumps(_job_dict(job), ensure_ascii=False, indent=2))
        return 0

    if arguments.command == "serve":
        assert proactive is not None
        worker = ProactiveWorker(
            proactive,
            lambda job: _proactive_handler(job, store=store, state_root=state_root),
            worker_id=arguments.worker_id,
        )
        while True:
            processed = worker.run_once()
            if arguments.once:
                break
            if processed is None:
                time.sleep(max(0.1, min(float(arguments.poll_seconds), 60.0)))
        return 0

    if arguments.command == "resume":
        state = store.load(arguments.run_id)
        controller = build_product_controller(store, state, state_root=state_root)
        result = controller.resume(arguments.run_id)
        print(json.dumps(_summary(result.state, result.final_output), ensure_ascii=False, indent=2))
        return 0 if result.state.status.value == "completed" else 2

    workspace = Path(arguments.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    config = _retrieval_config(arguments)
    goal = LongHorizonModel.create_literal_goal(
        _request_text(arguments),
        str(workspace),
        constraints=list(arguments.constraint or []),
        runtime_policy=runtime_policy_document(
            config,
            supervisor_mode=arguments.supervisor,
            state_router_mode=(
                "shadow" if bool(arguments.state_router_shadow) else "disabled"
            ),
        ),
    )
    state = store.create_run(goal, arguments.run_id)
    controller = build_product_controller(store, state, state_root=state_root)
    result = controller.run(state.run_id)
    print(json.dumps(_summary(result.state, result.final_output), ensure_ascii=False, indent=2))
    return 0 if result.state.status.value == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
