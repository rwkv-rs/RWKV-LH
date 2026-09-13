"""Audit frozen UltraData ranges and compile a bounded external Code task pilot.

No downloads, model calls or training. The compiled tasks are inputs for the
existing benchmark runner; their private checks use its isolated verifier.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

from rwkv_lh.benchmark_verifier import run_isolated_verifier
from rwkv_lh.goal_state_protocols import auditor_final, auditor_step_v7, executor_args_v7, finalizer_answer, selector_intent_v7
from rwkv_lh.role_trace_artifacts import byte_5gram_cosine
from rwkv_lh.ultradata import audit_trajectory, compile_code_task, read_frozen_range


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(fetch_manifest: Path, *, root: Path, output: Path, code_count: int = 3) -> dict:
    if code_count < 1:
        raise ValueError("positive code count required")
    if output.exists():
        raise ValueError("output already exists; preserve prior audit results")
    source = json.loads(fetch_manifest.read_text(encoding="utf-8"))
    output.mkdir(parents=True)
    audits, selected, ranges, pairs = [], [], [], []
    tasks, cases, ids = [], {}, set()
    for item in sorted(source["sources"], key=lambda x: (x["group"], x["path"])):
        if "error" in item:
            ranges.append({**item, "disposition": "acquisition_failed"})
            continue
        if len(item["revision"]) != 40 or any(c not in "0123456789abcdef" for c in item["revision"]):
            raise ValueError("immutable source revision required")
        records, metadata = read_frozen_range(root / item["local_path"], item["sha256"])
        ranges.append({"group": item["group"], "path": item["path"], **metadata})
        for record in records:
            provenance = {"group": item["group"], "repository": item["repository"], "revision": item["revision"],
                          "path": item["path"], "range_sha256": item["sha256"],
                          **{key: record[key] for key in ("line_number", "byte_offset", "bytes", "row_sha256")}}
            if "error" in record:
                audits.append({**provenance, "disposition": "invalid_json", "error": record["error"]})
                continue
            row = record["row"]
            if item["group"] in {"sft_tool", "sft_code"}:
                audit = audit_trajectory(row)
                audits.append({**provenance, **audit, "disposition": "external_trajectory_review_only"})
                continue
            if item["group"] != "rl_code":
                raise ValueError("unknown source group")
            try:
                task, case = compile_code_task(row)
            except ValueError as error:
                audits.append({**provenance, "uuid": row.get("uuid"), "disposition": "invalid_code_task", "error": str(error)})
                continue
            uid = row["uuid"]
            audit = {**provenance, "uuid": uid, "disposition": "outside_fixed_pilot_count",
                     "test_cases": len(row["ground_truth"]["inputs"]), "role_training_eligible": False,
                     "query_sha256": hashlib.sha256(row["query"].encode()).hexdigest()}
            if uid in ids:
                audit["disposition"] = "duplicate_source_id_requires_review"
            elif len(tasks) < code_count:
                scores = [dict(left=prior["uuid"], right=uid, cosine=byte_5gram_cosine(prior["query"], row["query"]))
                          for prior in selected]
                pairs.extend(scores)
                if any(pair["cosine"] >= 0.95 for pair in scores):
                    audit["disposition"] = "near_duplicate_of_selected_task"
                else:
                    audit["disposition"] = "selected_pending_execution_validation"
                    tasks.append(task)
                    cases[task["task_id"]] = case
                    selected.append({**provenance, "uuid": uid, "query": row["query"],
                                     "test_cases": audit["test_cases"], "query_sha256": audit["query_sha256"]})
            ids.add(uid)
            audits.append(audit)
    write_json(output / "public/tasks.json", {"tasks": tasks})
    write_json(output / "private/acceptance.json", {"cases": cases})
    with (output / "AUDIT.jsonl").open("w", encoding="utf-8") as handle:
        for audit in audits:
            handle.write(json.dumps(audit, ensure_ascii=False) + "\n")
    from rwkv_lh import ultradata
    summary = {
        "source_run": source["source_run"], "kind": "external_task_preparation_not_role_dataset",
        "fetch_manifest_sha256": digest(fetch_manifest), "requested_code_count": code_count,
        "selected_code_count": len(tasks), "selection_count_satisfied": len(tasks) == code_count,
        "selection": "source path then line; first structurally valid unique std-I/O tasks; no performance-based replacement",
        "selected": [{key: value for key, value in row.items() if key != "query"} for row in selected],
        "dispositions": dict(Counter(row["disposition"] for row in audits)), "ranges": ranges,
        "complete_rows_audited": len(audits),
        "group_counts": dict(Counter(row["group"] for row in audits)),
        "split_algorithm": "pilot preparation only; no train/dev/confirmation split; no holdout access",
        "similarity": {"algorithm": "UTF-8 byte 5-gram count-vector cosine", "threshold": 0.95,
                       "scope": "candidate Code queries against previously selected pilot queries only", "pairs": pairs},
        "sft_coverage": {group: {
            "terminal_kinds": dict(Counter(x.get("terminal_kind", "invalid") for x in audits if x["group"] == group)),
            "tool_calls": sum(x.get("tool_calls", 0) for x in audits if x["group"] == group),
            "masked_assistant_turns": sum(x.get("masked_assistant_turns", 0) for x in audits if x["group"] == group),
            "rows_with_structural_review_flags": sum(bool(x.get("review_reasons")) for x in audits if x["group"] == group),
            "environment_reproduced": 0, "role_training_samples": 0,
        } for group in ("sft_tool", "sft_code")},
        "generator": {"path": str(Path(__file__).relative_to(root)), "sha256": digest(Path(__file__))},
        "adapter": {"path": str(Path(ultradata.__file__).relative_to(root)), "sha256": digest(Path(ultradata.__file__))},
        "role_protocol_modules": [{"module": module.__name__, "sha256": digest(Path(module.__file__))}
            for module in (selector_intent_v7, executor_args_v7, auditor_step_v7, finalizer_answer, auditor_final)],
        "compiled_files": [{"path": str(path.relative_to(output)), "sha256": digest(path)}
                           for path in (output / "public/tasks.json", output / "private/acceptance.json", output / "AUDIT.jsonl")],
        "agent_metrics": None, "role_training_samples": 0, "optimizer_steps": 0,
    }
    write_json(output / "MANIFEST.json", summary)
    return summary


def verify(bundle: Path, task_id: str, workspace: Path, output: Path) -> dict:
    manifest = json.loads((bundle / "MANIFEST.json").read_text())
    for item in manifest["compiled_files"]:
        if digest(bundle / item["path"]) != item["sha256"]:
            raise ValueError("compiled pilot file SHA-256 mismatch")
    cases = json.loads((bundle / "private/acceptance.json").read_text())["cases"]
    result = run_isolated_verifier(cases[task_id], workspace, [], {}, private_root=output / "private_runtime")
    record = {"task_id": task_id, "kind": "candidate_verification_not_agent_evaluation", "passed": result.passed,
              "checks": [item.to_dict() for item in result.checks], "metadata": result.metadata,
              "bundle_manifest_sha256": digest(bundle / "MANIFEST.json"),
              "candidate_files": [{"path": str(path.relative_to(workspace)), "sha256": digest(path)}
                                  for path in sorted(workspace.rglob("*")) if path.is_file()]}
    write_json(output / "RESULT.json", record)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("prepare")
    build.add_argument("--fetch-manifest", type=Path, required=True)
    build.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    build.add_argument("--output", type=Path, required=True)
    build.add_argument("--code-count", type=int, default=3)
    check = commands.add_parser("verify")
    check.add_argument("--bundle", type=Path, required=True)
    check.add_argument("--task-id", required=True)
    check.add_argument("--workspace", type=Path, required=True)
    check.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "prepare":
        result = prepare(args.fetch_manifest.resolve(), root=args.root.resolve(), output=args.output.resolve(), code_count=args.code_count)
        print(json.dumps({key: result[key] for key in ("complete_rows_audited", "group_counts", "selected_code_count", "selection_count_satisfied")}))
        return 0 if result["selection_count_satisfied"] else 1
    result = verify(args.bundle.resolve(), args.task_id, args.workspace.resolve(), args.output.resolve())
    print(json.dumps({"task_id": args.task_id, "passed": result["passed"]}))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
