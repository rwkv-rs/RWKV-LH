from __future__ import annotations

import json
import sys
from pathlib import Path

from scripts import summarize_rwkv_state_tuning_stage7_candidate as scorer


def write_json(path: Path, value: dict) -> None:
    path.write_text(json.dumps(value), encoding="utf-8")


def test_stage7_scorer_binds_runtime_attestation_to_requested_checkpoint(
    tmp_path: Path, monkeypatch
) -> None:
    dev200 = tmp_path / "dev200.json"
    own = tmp_path / "own.json"
    ecra = tmp_path / "ecra.json"
    checkpoint = tmp_path / "checkpoint.json"
    tokenizer = tmp_path / "tokenizer.json"
    attestation = tmp_path / "attestation.jsonl"
    output = tmp_path / "score.json"
    write_json(
        dev200,
        {
            "overall": {"schema_valid": 200, "operation_correct": 200},
            "by_stage": {"direct": {"arguments_exact": 107}},
        },
    )
    clusters = {
        cluster: {"operation_accuracy": 0.95}
        for cluster in scorer.OWN_CLUSTERS
    }
    write_json(
        own,
        {
            "overall": {"operation_accuracy": 0.95},
            "by_cluster": clusters,
            "contrast": {"operation_consistency_rate": 0.95},
        },
    )
    category_rows = {
        "local-only": 30,
        "public-web-required": 25,
        "deterministic-compute": 15,
        "structured-connector": 20,
        "mixed-local-online": 20,
        "privacy-policy-rejection": 10,
    }
    category_correct = {
        "local-only": 26,
        "public-web-required": 23,
        "deterministic-compute": 15,
        "structured-connector": 12,
        "mixed-local-online": 17,
        "privacy-policy-rejection": 9,
    }
    cases = []
    for category, count in category_rows.items():
        cases.extend(
            {
                "category": category,
                "checks": {"first_tool_exact": index < category_correct[category]},
            }
            for index in range(count)
        )
    write_json(
        ecra,
        {
            "cases": cases,
            "metrics": {
                "case_count": 120,
                "first_tool_exact_accuracy": sum(category_correct.values()) / 120,
                "network_decision_macro_f1": 0.974,
                "local_only_network_false_positive_rate": 0,
                "required_online_false_negative_rate": 0.0923,
                "privacy_backend_execution_count": 0,
                "privacy_policy_rejection_coverage": 1.0,
                "failed_or_unavailable_case_count": 4,
            },
        },
    )
    write_json(
        checkpoint,
        {
            "schema_version": "rwkv-lh.stage7-checkpoint-validation.v1",
            "status": "validated",
            "checkpoints": {
                "500": {
                    "checkpoint": {
                        "sha256": "candidate-sha",
                        "all_finite": True,
                        "elements": 10,
                        "nonzero_elements": 10,
                    }
                }
            },
        },
    )
    write_json(
        tokenizer,
        {
            "failure_count": 0,
            "exact_token_id_match_rate": 1.0,
            "bos_contract_match_rate": 1.0,
        },
    )
    attestation.write_text(
        json.dumps(
            {
                "event": "state_loaded",
                "state_sha256": "candidate-sha",
                "state_orientation": "rwkv_peft_parameter_v_k_direct",
            }
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "score",
            "--candidate",
            "step500",
            "--checkpoint-step",
            "500",
            "--dev200",
            str(dev200),
            "--own-dev",
            str(own),
            "--ecra",
            str(ecra),
            "--checkpoint-validation",
            str(checkpoint),
            "--tokenizer-alignment",
            str(tokenizer),
            "--vllm-attestation",
            str(attestation),
            "--engineering-regression-passed",
            "--output",
            str(output),
        ],
    )
    assert scorer.main() == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["checkpoint_step"] == 500
    assert result["selected_checkpoint_sha256"] == "candidate-sha"
    assert result["deployment_eligible"] is True
