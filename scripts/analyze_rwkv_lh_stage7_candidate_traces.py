"""Post-hoc trace attribution for frozen Stage7 candidate evaluations."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_candidate(value: str) -> tuple[str, Path]:
    label, separator, path = value.partition("=")
    if not separator or not label or not path:
        raise argparse.ArgumentTypeError("candidate must use LABEL=PATH")
    return label, Path(path).resolve()


def boundary_failures(report: Mapping[str, Any]) -> dict[str, Any]:
    operation = [row for row in report["results"] if not row["operation_correct"]]
    argument = [
        row
        for row in report["results"]
        if row["operation_correct"] and not row["arguments_exact"]
    ]

    def compact(row: Mapping[str, Any]) -> dict[str, Any]:
        return {
            "trajectory_id": row["trajectory_id"],
            "turn_index": row.get("turn_index", 0),
            "failure_cluster": row["failure_cluster"],
            "stage": row["stage"],
            "expected_operation": row["expected_operation"],
            "parsed_outer_function": row["parsed_outer_function"],
            "parsed_operation": row["parsed_operation"],
            "raw_output": row["raw_output"],
            "error": row["error"],
        }

    return {
        "operation_failure_count": len(operation),
        "argument_only_failure_count": len(argument),
        "operation_transition_counts": dict(
            Counter(
                f"{row['expected_operation']}->{row['parsed_operation'] or '<invalid>'}"
                for row in operation
            )
        ),
        "operation_failures_by_cluster": dict(
            Counter(row["failure_cluster"] for row in operation)
        ),
        "argument_failures_by_cluster": dict(
            Counter(row["failure_cluster"] for row in argument)
        ),
        "operation_failures": [compact(row) for row in operation],
        "argument_only_failures": [compact(row) for row in argument],
    }


def ecra_failures(report: Mapping[str, Any]) -> dict[str, Any]:
    failures = [case for case in report["cases"] if not case["checks"]["first_tool_exact"]]
    result = []
    for case in failures:
        actual = case["actual"]
        result.append(
            {
                "case_id": case["case_id"],
                "category": case["category"],
                "language": case["language"],
                "expected_first_tool": case["expected"]["first_tool"],
                "actual_first_tool": actual["first_tool"],
                "expected_sequence": case["expected"]["tool_sequence"],
                "actual_operations": actual["operations"],
                "run_status": actual["run_status"],
                "failure": actual["failure"],
                "protocol_rejections": actual["protocol_rejections"],
                "policy_rejection_count": actual["policy_rejection_count"],
                "backend_execution_count": actual["backend_execution_count"],
                "network_called": actual["network_called"],
            }
        )
    return {
        "first_tool_failure_count": len(failures),
        "failures_by_category": dict(Counter(case["category"] for case in failures)),
        "first_tool_transition_counts": dict(
            Counter(
                f"{case['expected']['first_tool']}->{case['actual']['first_tool'] or '<none>'}"
                for case in failures
            )
        ),
        "failed_or_unavailable_case_count": report["metrics"][
            "failed_or_unavailable_case_count"
        ],
        "failures": result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-ecra", type=Path, required=True)
    parser.add_argument("--candidate", action="append", type=parse_candidate, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    labels = [label for label, _path in args.candidate]
    if len(labels) != len(set(labels)):
        raise SystemExit("candidate labels must be unique")
    baseline = read_json(args.baseline_ecra.resolve())
    baseline_by_id = {case["case_id"]: case for case in baseline["cases"]}
    candidates: dict[str, dict[str, Any]] = {}
    case_matrix: dict[str, dict[str, bool]] = defaultdict(dict)
    for label, root in args.candidate:
        own = read_json(root / "own_dev400_greedy.json")
        round1 = read_json(root / "round1_dev200_greedy.json")
        ecra = read_json(root / "ecra_route120_B/results.json")
        score = read_json(root / "candidate_score.json")
        comparison = Counter()
        for case in ecra["cases"]:
            case_id = case["case_id"]
            current = bool(case["checks"]["first_tool_exact"])
            previous = bool(baseline_by_id[case_id]["checks"]["first_tool_exact"])
            comparison[
                (
                    "both_correct"
                    if previous and current
                    else "regressed"
                    if previous and not current
                    else "fixed"
                    if not previous and current
                    else "both_incorrect"
                )
            ] += 1
            case_matrix[case_id][label] = current
        candidates[label] = {
            "checkpoint_step": score["checkpoint_step"],
            "checkpoint_sha256": score["selected_checkpoint_sha256"],
            "deployment_eligible": score["deployment_eligible"],
            "failed_gates": [name for name, passed in score["gates"].items() if not passed],
            "own_dev": boundary_failures(own),
            "round1_dev": boundary_failures(round1),
            "ecra": ecra_failures(ecra),
            "stage4_ecra_comparison": dict(comparison),
        }
    recurring = {
        case_id: statuses
        for case_id, statuses in sorted(case_matrix.items())
        if sum(not status for status in statuses.values()) > 1
    }
    result = {
        "schema_version": "rwkv-lh.stage7-posthoc-trace-attribution.v1",
        "method": "Frozen score first; post-hoc attribution from raw boundary outputs and ECRA Controller traces.",
        "baseline_ecra": str(args.baseline_ecra.resolve()),
        "candidate_order": labels,
        "candidates": candidates,
        "recurring_ecra_failures": recurring,
        "recurring_ecra_failure_count": len(recurring),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "candidate_order": labels,
                "eligible": {
                    label: value["deployment_eligible"]
                    for label, value in candidates.items()
                },
                "recurring_ecra_failure_count": len(recurring),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
