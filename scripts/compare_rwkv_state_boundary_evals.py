"""Pairwise compare two frozen RWKV state-boundary evaluations."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def paired(rows: list[tuple[dict[str, Any], dict[str, Any]]], metric: str) -> dict[str, Any]:
    both_pass = sum(bool(left[metric]) and bool(right[metric]) for left, right in rows)
    rescued = sum(not bool(left[metric]) and bool(right[metric]) for left, right in rows)
    regressed = sum(bool(left[metric]) and not bool(right[metric]) for left, right in rows)
    both_fail = len(rows) - both_pass - rescued - regressed
    return {
        "rows": len(rows),
        "baseline_pass": both_pass + regressed,
        "candidate_pass": both_pass + rescued,
        "net_change": rescued - regressed,
        "both_pass": both_pass,
        "rescued": rescued,
        "regressed": regressed,
        "both_fail": both_fail,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
    candidate = json.loads(args.candidate.read_text(encoding="utf-8"))
    if baseline["source_sha256"] != candidate["source_sha256"]:
        raise SystemExit("evaluation source changed")
    if baseline["sampling"] != candidate["sampling"]:
        raise SystemExit("sampling contract changed")
    before = {
        f"{row['trajectory_id']}:{row.get('turn_index', 0)}:{row['stage']}": row
        for row in baseline["results"]
    }
    after = {
        f"{row['trajectory_id']}:{row.get('turn_index', 0)}:{row['stage']}": row
        for row in candidate["results"]
    }
    if set(before) != set(after):
        raise SystemExit("paired row identity changed")
    pairs = [(before[key], after[key]) for key in sorted(before)]
    for left, right in pairs:
        if left["prompt_sha256"] != right["prompt_sha256"]:
            raise SystemExit("paired prompt changed")

    by_stage: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    by_cluster: dict[str, list[tuple[dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for left, right in pairs:
        by_stage[left["stage"]].append((left, right))
        by_cluster[left["failure_cluster"]].append((left, right))
    metrics = ("schema_valid", "operation_correct", "arguments_exact")
    report = {
        "schema_version": "rwkv-lh.state-boundary-live-comparison.v1",
        "baseline_label": baseline["label"],
        "candidate_label": candidate["label"],
        "source_sha256": baseline["source_sha256"],
        "sampling": baseline["sampling"],
        "overall": {metric: paired(pairs, metric) for metric in metrics},
        "by_stage": {
            key: {metric: paired(value, metric) for metric in metrics}
            for key, value in sorted(by_stage.items())
        },
        "by_cluster": {
            key: {metric: paired(value, metric) for metric in metrics}
            for key, value in sorted(by_cluster.items())
        },
        "raw_output": {
            "same": sum(
                left["raw_output_sha256"] == right["raw_output_sha256"]
                for left, right in pairs
            ),
            "different": sum(
                left["raw_output_sha256"] != right["raw_output_sha256"]
                for left, right in pairs
            ),
        },
        "outer_function_transitions": dict(
            Counter(
                f"{left['parsed_outer_function']}->{right['parsed_outer_function']}"
                for left, right in pairs
                if left["parsed_outer_function"] != right["parsed_outer_function"]
            )
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
