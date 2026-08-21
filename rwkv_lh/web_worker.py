"""Isolated worker process used by the local RWKV-LH web UI."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_session import ModelSession
from rwkv_lh.store import LongHorizonStore
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
    session = ModelSession(audit_hook=lambda event: append_jsonl(trace_path, event))
    harness = ActionHarness()
    model = LongHorizonModel(session, harness=harness)
    controller = LongHorizonController(
        store,
        model=model,
        harness=harness,
        max_transitions=max_transitions,
    )
    update_metadata(
        run_root,
        active=True,
        phase="resuming" if resume else "creating_literal_request",
        pid=os.getpid(),
        worker_started_at=utc_now(),
        error="",
    )
    if resume:
        result = controller.resume(run_id)
    else:
        goal = model.create_literal_goal(
            str(request["request"]),
            str(workspace),
            constraints=[str(item) for item in request.get("constraints") or []],
        )
        state = store.create_run(goal, run_id)
        update_metadata(
            run_root,
            state_created=True,
            phase="controller_running",
            request=state.goal.request,
            goal_digest=state.goal.digest,
        )
        result = controller.run(run_id)
    payload = result_payload(result.state, result.final_output, result.transitions)
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
