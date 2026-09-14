"""Isolated worker process used by the local RWKV-LH web UI."""

from __future__ import annotations

import argparse
import json
import os
import traceback
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.model_session import create_model_session
from rwkv_lh.read_only_agent import ReadOnlyJob, run_read_only_job
from rwkv_lh.coding_agent import CodingJob, run_coding_job
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


def direct_settings():
    from dataclasses import replace
    from rwkv_lh.runtime.settings import get_runtime_settings
    return replace(get_runtime_settings(), return_token_ids=True,
                   state_transport="native_required", state_profile_id="zero",
                   state_profile_sha256="0" * 64, tool_disclosure_mode="full")


def run(run_root: Path, *, resume: bool, max_transitions: int) -> int:
    if resume:
        raise ValueError("direct frontend resume is not yet supported; preserve this run and create a new task")
    request = read_json(run_root / "request.json")
    if not isinstance(request, dict) or request.get("runtime") != "direct_rwkv":
        raise ValueError("historical runtime is read-only; create a new direct RWKV task")
    scope = request["tool_scope"]
    goal = request["request"]
    if request.get("constraints"):
        goal += "\n\n用户补充要求：\n" + "\n".join(request["constraints"])
    update_metadata(run_root, active=True, phase="controller_running", pid=os.getpid(),
                    worker_started_at=utc_now(), error="")
    settings = direct_settings()
    # No credentials enter persisted configuration. The shared executor records
    # actual input, output, observations and native State relations.
    atomic_write_json(run_root / "runtime.json", {
        key: value for key, value in vars(settings).items()
        if key not in {"api_key", "cf_access_client_id", "cf_access_client_secret", "proxy_url"}
    })
    if scope == "coding":
        result = run_coding_job(CodingJob(
            request["run_id"], goal, str(run_root / "workspace"), str(run_root / "delivery"),
            max_transitions, request["max_seconds"]), settings=settings, session_factory=create_model_session)
    else:
        result = run_read_only_job(ReadOnlyJob(
            request["run_id"], goal, str(run_root / "workspace"), str(run_root / "execution"),
            max_transitions, request["max_seconds"], tool_scope=scope),
            settings=settings, session_factory=create_model_session)
    atomic_write_json(run_root / "result.json", {**result, "final_output": result["final"]})
    submitted = result["termination"] == "submitted"
    execution = run_root / ("delivery/execution" if scope == "coding" else "execution")
    update_metadata(run_root, active=False, phase="finished" if submitted else "blocked",
                    pid=None, status="submitted" if submitted else "interrupted",
                    state_created=(execution / "state_snapshot.json").exists(),
                    termination_reason=result["termination_reason"],
                    worker_finished_at=utc_now(), result_path="result.json", error="")
    return 0 if submitted else 1


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
