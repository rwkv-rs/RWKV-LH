"""Create, resume, and inspect persistent Long-Horizon Agent runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from rwkv_lh.controller import LongHorizonController
from rwkv_lh.harness import ActionHarness
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.store import LongHorizonStore


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
    start.add_argument("--seed", type=int, default=None, help="Optional reproducible goal-parse seed")
    start.add_argument("--run-id", default=None)

    resume = subparsers.add_parser("resume", help="Resume an existing run")
    resume.add_argument("run_id")

    status = subparsers.add_parser("status", help="Print structured run state")
    status.add_argument("run_id")
    return parser


def _request_text(arguments: argparse.Namespace) -> str:
    if arguments.request is not None:
        return str(arguments.request).strip()
    return Path(arguments.request_file).read_text(encoding="utf-8").strip()


def _summary(state, final_output: str = "") -> dict[str, Any]:
    return {
        "run_id": state.run_id,
        "revision": state.revision,
        "status": state.status.value,
        "goal": state.goal.objective,
        "tasks": {
            task_id: {
                "title": task.title,
                "status": task.status.value,
                "active": task.active,
                "attempts": len(task.attempt_ids),
                "output_refs": task.output_refs,
            }
            for task_id, task in state.tasks.items()
        },
        "artifact_count": len(state.artifacts),
        "model_requests": len(state.temp_decisions),
        "final_output": final_output,
    }


def main() -> int:
    arguments = _parser().parse_args()
    store = LongHorizonStore(Path(arguments.state_directory))
    if arguments.command == "status":
        state = store.load(arguments.run_id)
        final = state.memory_index.get("M-FINAL")
        print(json.dumps(_summary(state, final.content if final else ""), ensure_ascii=False, indent=2))
        return 0

    harness = ActionHarness()
    model = LongHorizonModel(harness=harness)
    controller = LongHorizonController(store, model=model, harness=harness)
    if arguments.command == "resume":
        result = controller.resume(arguments.run_id)
        print(json.dumps(_summary(result.state, result.final_output), ensure_ascii=False, indent=2))
        return 0 if result.state.status.value == "completed" else 2

    workspace = Path(arguments.workspace).expanduser().resolve()
    workspace.mkdir(parents=True, exist_ok=True)
    goal, goal_decision = model.parse_goal(
        _request_text(arguments),
        str(workspace),
        constraints=list(arguments.constraint or []),
        seed=arguments.seed,
    )
    state = store.create_run(goal, arguments.run_id)
    state.temp_decisions.append(goal_decision)
    state = store.save(
        state,
        event_type="goal_parsed",
        event={
            "request_id": goal_decision.request_id,
            "temperature": goal_decision.temperature,
            "seed": arguments.seed,
            "outcome": goal_decision.outcome,
        },
    )
    result = controller.run(state.run_id)
    print(json.dumps(_summary(result.state, result.final_output), ensure_ascii=False, indent=2))
    return 0 if result.state.status.value == "completed" else 2


if __name__ == "__main__":
    raise SystemExit(main())
