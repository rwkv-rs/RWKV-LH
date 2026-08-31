"""Isolated worker process used by the local RWKV-LH web UI."""

from __future__ import annotations

import argparse
import json
import os
import time
import traceback
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.model import LongHorizonModel
from rwkv_lh.product_runtime import build_product_controller
from rwkv_lh.retrieval import (
    RetrievalRuntimeConfig,
    retrieval_policy_from_goal,
    runtime_policy_document,
)
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.run_lifecycle import goal_self_termination_only
from rwkv_lh.web_ui import atomic_write_json, read_json, update_metadata, utc_now


def append_jsonl(path: Path, event: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(dict(event), ensure_ascii=False, separators=(",", ":")) + "\n"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())


def result_payload(state: Any, final_output: str, transitions: int) -> dict[str, Any]:
    persisted_final = state.final_output
    return {
        "schema_version": "rwkv-lh.manual-web-result.v1",
        "generated_at": utc_now(),
        "run_id": state.run_id,
        "status": state.status.value,
        "revision": state.revision,
        "transitions": transitions,
        "action_count": len(state.actions),
        "causal_record_count": len(state.causal_order),
        "artifact_count": len(state.artifacts),
        "model_request_count": len(state.temp_decisions),
        "final_output": final_output,
        "persisted_final_output": persisted_final,
        "final_output_matches_persisted_rwkv": final_output == persisted_final,
        "output_policy": (
            "The UI and worker return the Controller's exact final output. They do not generate, "
            "select, repair, or rewrite an answer."
        ),
    }


def run(run_root: Path, *, resume: bool, max_transitions: int) -> int:
    request = read_json(run_root / "request.json")
    if not isinstance(request, dict):
        raise ValueError("request.json is missing or invalid")
    run_id = str(request["run_id"])
    workspace = (run_root / "workspace").resolve()
    store = LongHorizonStore(run_root / "state", checkpoint_retention=100_000)
    trace_path = run_root / "model_trace.jsonl"
    if resume:
        state = store.load(run_id)
        config = retrieval_policy_from_goal(state.goal)
    else:
        config = RetrievalRuntimeConfig.from_dict(request.get("retrieval_policy"))
    update_metadata(
        run_root,
        active=True,
        phase="resuming" if resume else "creating_literal_request",
        pid=os.getpid(),
        worker_started_at=utc_now(),
        error="",
    )
    if not resume:
        goal = LongHorizonModel.create_literal_goal(
            str(request["request"]),
            str(workspace),
            constraints=[str(item) for item in request.get("constraints") or []],
            runtime_policy=runtime_policy_document(
                config,
                supervisor_mode=str(request.get("supervisor_mode") or "none"),
                state_router_mode=(
                    "shadow" if bool(request.get("state_router_shadow", False)) else "disabled"
                ),
                execution_mode=str(request.get("execution_mode") or "bounded"),
            ),
        )
        state = store.create_run(goal, run_id)
        update_metadata(
            run_root,
            state_created=True,
            phase="controller_running",
            request=state.goal.request,
            goal_digest=state.goal.digest,
        )

    def append_model_trace(event: Mapping[str, Any]) -> None:
        append_jsonl(trace_path, {**dict(event), "source": "rwkv"})

    def append_supervisor_trace(event: Mapping[str, Any]) -> None:
        append_jsonl(trace_path, {**dict(event), "source": "strong_supervisor"})

    controller = build_product_controller(
        store,
        state,
        state_root=run_root,
        max_transitions=max_transitions,
        model_audit_hook=append_model_trace,
        supervisor_audit_hook=append_supervisor_trace,
    )
    result = controller.resume(run_id) if resume else controller.run(run_id)
    continuation_count = 0
    while goal_self_termination_only(result.state.goal) and result.state.status.value == "running":
        continuation_count += 1
        payload = result_payload(result.state, result.final_output, result.transitions)
        payload["continuation_count"] = continuation_count
        atomic_write_json(run_root / "result.json", payload)
        latest = result.state.causal_records[result.state.causal_order[-1]]
        reason = str(latest.payload.get("reason") or "goal_continuation")
        update_metadata(
            run_root,
            active=True,
            phase="goal_continuing",
            status=result.state.status.value,
            revision=result.state.revision,
            continuation_count=continuation_count,
            continuation_reason=reason,
            error="",
        )
        if reason.endswith("_unavailable") or reason.endswith("_failure"):
            time.sleep(min(60.0, float(2 ** min(continuation_count - 1, 6))))
        result = controller.resume(run_id)
    payload = result_payload(result.state, result.final_output, result.transitions)
    payload["continuation_count"] = continuation_count
    atomic_write_json(run_root / "result.json", payload)
    update_metadata(
        run_root,
        active=False,
        phase="finished",
        pid=None,
        status=result.state.status.value,
        revision=result.state.revision,
        worker_finished_at=utc_now(),
        result_path="result.json",
        error="",
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--max-transitions", required=True, type=int)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = args.run_root.expanduser().resolve()
    try:
        return run(run_root, resume=args.resume, max_transitions=args.max_transitions)
    except BaseException as exc:
        update_metadata(
            run_root,
            active=False,
            phase="failed",
            pid=None,
            worker_finished_at=utc_now(),
            error=f"{type(exc).__name__}: {exc}"[:2000],
        )
        traceback.print_exc()
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
