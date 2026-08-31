"""Pairwise compare frozen baseline and tuned Round1 2K live evaluations."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("--baseline", type=Path, required=True)
parser.add_argument("--tuned", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
baseline = json.loads(args.baseline.read_text(encoding="utf-8"))
tuned = json.loads(args.tuned.read_text(encoding="utf-8"))
if baseline["dev_sha256"] != tuned["dev_sha256"]:
    raise SystemExit("dev split changed")
if baseline["sampling"] != tuned["sampling"]:
    raise SystemExit("sampling contract changed")
before = {row["trajectory_id"] + ":" + row["stage"]: row for row in baseline["results"]}
after = {row["trajectory_id"] + ":" + row["stage"]: row for row in tuned["results"]}
if set(before) != set(after) or len(before) != 200:
    raise SystemExit("paired evaluation rows changed")


def paired(rows: list[tuple[dict, dict]], metric: str) -> dict:
    both_pass = sum(bool(left[metric]) and bool(right[metric]) for left, right in rows)
    rescued = sum(not bool(left[metric]) and bool(right[metric]) for left, right in rows)
    regressed = sum(bool(left[metric]) and not bool(right[metric]) for left, right in rows)
    both_fail = len(rows) - both_pass - rescued - regressed
    before_rate = (both_pass + regressed) / len(rows)
    after_rate = (both_pass + rescued) / len(rows)
    return {
        "rows": len(rows),
        "baseline_rate": before_rate,
        "tuned_rate": after_rate,
        "absolute_delta": after_rate - before_rate,
        "both_pass": both_pass,
        "rescued": rescued,
        "regressed": regressed,
        "both_fail": both_fail,
    }


pairs = [(before[key], after[key]) for key in sorted(before)]
by_cluster: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
by_signature: dict[str, list[tuple[dict, dict]]] = defaultdict(list)
for left, right in pairs:
    if left["failure_cluster"] != right["failure_cluster"]:
        raise SystemExit("cluster changed")
    by_cluster[left["failure_cluster"]].append((left, right))
    by_signature[left["failure_signature_id"]].append((left, right))

metrics = ("schema_valid", "operation_correct", "arguments_exact")
report = {
    "schema_version": "rwkv-lh.action-state-tuning-live-comparison.v1",
    "baseline_label": baseline["label"],
    "tuned_label": tuned["label"],
    "dev_sha256": baseline["dev_sha256"],
    "sampling": baseline["sampling"],
    "overall": {metric: paired(pairs, metric) for metric in metrics},
    "by_cluster": {
        key: {metric: paired(value, metric) for metric in metrics}
        for key, value in sorted(by_cluster.items())
    },
    "by_signature": {
        key: {metric: paired(value, metric) for metric in metrics}
        for key, value in sorted(by_signature.items())
    },
}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
