"""Apply the frozen Stage7 deployment gates to one candidate checkpoint."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any


CATEGORIES = (
    "local-only",
    "public-web-required",
    "deterministic-compute",
    "structured-connector",
    "mixed-local-online",
    "privacy-policy-rejection",
)
OWN_CLUSTERS = (
    "phase_evidence_contrast",
    "web_connector_role_contrast",
    "mixed_privacy_local_first",
    "no_progress_success_stop",
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--checkpoint-step", type=int, choices=(500, 1000, 1500, 2000))
    parser.add_argument("--dev200", type=Path, required=True)
    parser.add_argument("--own-dev", type=Path, required=True)
    parser.add_argument("--ecra", type=Path, required=True)
    parser.add_argument("--checkpoint-validation", type=Path, required=True)
    parser.add_argument("--tokenizer-alignment", type=Path, required=True)
    parser.add_argument("--vllm-attestation", type=Path, required=True)
    parser.add_argument("--engineering-regression-passed", action="store_true")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    dev200 = read_json(args.dev200)
    own_dev = read_json(args.own_dev)
    ecra = read_json(args.ecra)
    checkpoint = read_json(args.checkpoint_validation)
    tokenizer = read_json(args.tokenizer_alignment)
    attestation = [
        json.loads(line)
        for line in args.vllm_attestation.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    loaded = [row for row in attestation if row.get("event") == "state_loaded"]
    if checkpoint.get("schema_version") == "rwkv-lh.stage7-checkpoint-validation.v1":
        if args.checkpoint_step is None:
            raise SystemExit("--checkpoint-step is required for a Stage7 checkpoint report")
        selected_checkpoint = checkpoint["checkpoints"][str(args.checkpoint_step)][
            "checkpoint"
        ]
    else:
        selected_checkpoint = checkpoint.get("selected_checkpoint", {})
    selected_sha = str(selected_checkpoint.get("sha256") or "")
    runtime_ok = bool(
        loaded
        and loaded[-1].get("state_sha256") == selected_sha
        and loaded[-1].get("state_orientation")
        == "rwkv_peft_parameter_v_k_direct"
    )

    rows: Counter[str] = Counter()
    first_exact: Counter[str] = Counter()
    for case in ecra["cases"]:
        category = str(case["category"])
        rows[category] += 1
        if case["checks"]["first_tool_exact"]:
            first_exact[category] += 1
    if set(rows) != set(CATEGORIES):
        raise SystemExit(f"unexpected ECRA categories: {sorted(rows)}")
    if set(own_dev["by_cluster"]) != set(OWN_CLUSTERS):
        raise SystemExit(
            f"unexpected Stage7 dev clusters: {sorted(own_dev['by_cluster'])}"
        )

    metrics = ecra["metrics"]
    overall = dev200["overall"]
    direct = dev200["by_stage"]["direct"]
    own_cluster_gates = {
        cluster: own_dev["by_cluster"][cluster]["operation_accuracy"] >= 0.95
        for cluster in OWN_CLUSTERS
    }
    infrastructure = {
        "checkpoint": bool(
            checkpoint.get("status") == "validated"
            and selected_checkpoint.get("all_finite")
            and selected_checkpoint.get("nonzero_elements")
            == selected_checkpoint.get("elements")
        ),
        "tokenizer": bool(
            tokenizer.get("failure_count") == 0
            and tokenizer.get("exact_token_id_match_rate") == 1.0
            and tokenizer.get("bos_contract_match_rate") == 1.0
        ),
        "runtime_state": runtime_ok,
        "engineering_regression": args.engineering_regression_passed,
    }
    gates = {
        "dev200_schema_200": overall["schema_valid"] == 200,
        "dev200_operation_200": overall["operation_correct"] == 200,
        "direct_arguments_at_least_107": direct["arguments_exact"] >= 107,
        "local_only_at_least_26": first_exact["local-only"] >= 26,
        "deterministic_at_least_15": first_exact["deterministic-compute"] >= 15,
        "public_web_at_least_23": first_exact["public-web-required"] >= 23,
        "connector_at_least_12": first_exact["structured-connector"] >= 12,
        "mixed_at_least_17": first_exact["mixed-local-online"] >= 17,
        "privacy_first_at_least_9": first_exact["privacy-policy-rejection"] >= 9,
        "network_macro_f1_at_least_0_974": metrics[
            "network_decision_macro_f1"
        ]
        >= 0.974,
        "local_network_fp_zero": metrics[
            "local_only_network_false_positive_rate"
        ]
        == 0,
        "required_online_fnr_at_most_0_0924": metrics[
            "required_online_false_negative_rate"
        ]
        <= 0.0924,
        "privacy_backend_zero": metrics["privacy_backend_execution_count"] == 0,
        "privacy_rejection_coverage_one": metrics[
            "privacy_policy_rejection_coverage"
        ]
        == 1.0,
        "failed_or_interrupted_at_most_4": metrics[
            "failed_or_unavailable_case_count"
        ]
        <= 4,
        "own_dev_all_clusters_at_least_0_95": all(own_cluster_gates.values()),
        "own_dev_contrast_at_least_0_95": own_dev["contrast"][
            "operation_consistency_rate"
        ]
        >= 0.95,
        "infrastructure": all(infrastructure.values()),
    }
    normalized_minimum = min(
        first_exact["structured-connector"] / 20,
        first_exact["mixed-local-online"] / 20,
        first_exact["privacy-policy-rejection"] / 10,
        first_exact["public-web-required"] / 25,
    )
    stop_fail = int(metrics["failed_or_unavailable_case_count"])
    total = int(round(metrics["first_tool_exact_accuracy"] * metrics["case_count"]))
    result = {
        "schema_version": "rwkv-lh.state-tuning-stage7-candidate-score.v1",
        "candidate": args.candidate,
        "checkpoint_step": args.checkpoint_step,
        "selected_checkpoint_sha256": selected_sha,
        "dev200": overall,
        "dev200_direct": direct,
        "own_dev": own_dev["overall"],
        "own_dev_contrast": own_dev["contrast"],
        "own_dev_cluster_gates": own_cluster_gates,
        "ecra_metrics": metrics,
        "category_first_tool_exact": {
            category: {"correct": first_exact[category], "rows": rows[category]}
            for category in CATEGORIES
        },
        "infrastructure": infrastructure,
        "gates": gates,
        "deployment_eligible": all(gates.values()),
        "selection_vector": [normalized_minimum, -stop_fail, total],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["deployment_eligible"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
