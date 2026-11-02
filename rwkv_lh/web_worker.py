"""Isolated worker process used by the local RWKV-LH web UI."""

from __future__ import annotations

import argparse
import os
import shutil
import traceback
from pathlib import Path

from rwkv_lh.model_session import create_model_session
from rwkv_lh.agent_jobs import CodingJob
from rwkv_lh.project_agent import run_project_job as run_coding_job, resume_project, continue_project
from rwkv_lh.project_ledger import ProjectLedger
from rwkv_lh.project_runtime import ARCHITECTURE
from rwkv_lh.web_ui import atomic_write_json, read_json, update_metadata, utc_now, followup_payload, can_continue


def direct_settings():
    from rwkv_lh.runtime.settings import direct_agent_settings, get_runtime_settings
    return direct_agent_settings(get_runtime_settings())



def run(run_root: Path, *, resume: bool, max_transitions: int, followup=None) -> int:
    request = read_json(run_root / "request.json")
    if not isinstance(request, dict) or request.get("runtime") != ARCHITECTURE:
        raise ValueError("historical runtime is read-only; create a new task")
    scope = request["tool_scope"]
    if scope != 'coding':
        raise ValueError('historical tool_scope is read-only; create a new Project task')
    goal = request["request"]
    if request.get("constraints"):
        goal += "\n\n用户补充要求：\n" + "\n".join(request["constraints"])
    update_metadata(run_root, active=True, phase="controller_running", pid=os.getpid(),
                    worker_started_at=utc_now(), error="")
    settings = direct_settings()
    # No credentials enter persisted configuration. The agent session records
    # actual input, output, observations and native State relations.
    atomic_write_json(run_root / "runtime.json", {
        key: value for key, value in vars(settings).items()
        if key not in {"api_key", "cf_access_client_id", "cf_access_client_secret", "proxy_url"}
    })
    if followup is not None:
        if resume:
            raise ValueError('choose resume or follow-up')
        expected = followup.get('expected_request_count')
        payload = followup_payload({k: v for k, v in followup.items() if k != 'expected_request_count'})
        db = ProjectLedger(run_root / 'delivery/execution')
        with db.lease():
            state = db.scan_verified_events()['state']
            if not can_continue(state) or (expected is not None and expected != len(state['requests'])):
                raise ValueError('follow-up requires its original ended, confirmed session boundary')
            archive = run_root / 'deliveries' / f"turn-{len(state['requests']):03d}"
            archive.mkdir(parents=True, exist_ok=True)
            for source in (run_root / 'result.json', run_root / 'delivery/DELIVERY.json'):
                if source.is_file():
                    target = archive / source.name
                    if target.exists() and target.read_bytes() != source.read_bytes():
                        raise ValueError('previous delivery archive changed')
                    if not target.exists():
                        shutil.copyfile(source, target)
        result = continue_project(run_root / 'delivery', settings=settings,
                                  expected_request_count=expected, **payload)
    elif resume:
        result = resume_project(run_root / 'delivery', settings=settings)
    else:
        result = run_coding_job(CodingJob(
            request["run_id"], goal, str(run_root / "workspace"), str(run_root / "delivery"),
            max_transitions, request["max_seconds"], writable_paths=tuple(request.get('writable_paths', ['.'])),
            protected_paths=tuple(request.get('protected_paths', []))), settings=settings, session_factory=create_model_session)
    atomic_write_json(run_root / "result.json", {**result, "final_output": result["final"]})
    submitted = result["termination"] == 'agent_finished'
    execution = run_root / "delivery/execution"
    update_metadata(run_root, active=False, phase="finished" if submitted else "blocked",
                    pid=None, status=result.get("status", "finished" if submitted else "interrupted"),
                    state_created=(execution / "state_snapshot.json").exists() or (execution / 'project.sqlite3').exists(),
                    termination_reason=result["termination_reason"],
                    worker_finished_at=utc_now(), result_path="result.json", error="")
    return 0 if submitted else 1


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", required=True, type=Path)
    parser.add_argument("--max-transitions", required=True, type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument('--followup-file', type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_root = args.run_root.expanduser().resolve()
    try:
        return run(run_root, resume=args.resume, max_transitions=args.max_transitions,
                   followup=read_json(args.followup_file) if args.followup_file else None)
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
