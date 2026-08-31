from __future__ import annotations

import json
from pathlib import Path

import pytest

from rwkv_lh.state_router.local_backend import LocalVLLMRWKVSettings
from rwkv_lh.state_router.metrics import (
    FIRST_ROUND_GATES,
    FORMAL_GATES,
    acceptance_gates,
    classification_metrics,
    evaluate_probabilities,
    expected_calibration_error,
)
from rwkv_lh.state_router.protocol import HEAD_LABELS


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/datasets/rwkv_lh_state_router_2k_v1/test.jsonl"


def rows() -> list[dict]:
    return [json.loads(line) for line in DATA.read_text(encoding="utf-8").splitlines()]


def perfect_predictions(records: list[dict]) -> list[dict[str, dict[str, float]]]:
    predictions = []
    for row in records:
        prediction: dict[str, dict[str, float]] = {}
        for name, labels in HEAD_LABELS.items():
            loser = 0.004 / (len(labels) - 1)
            prediction[name] = {
                label: 0.996 if label == row["labels"][name] else loser
                for label in labels
            }
        predictions.append(prediction)
    return predictions


def test_classification_and_ece_metrics_are_dependency_free() -> None:
    metrics = classification_metrics(
        ["a", "a", "b", "b"], ["a", "b", "b", "b"], ["a", "b"]
    )
    assert metrics["accuracy"] == 0.75
    assert metrics["per_class"]["a"]["recall"] == 0.5
    assert expected_calibration_error(
        ["a", "b"], [{"a": 0.9, "b": 0.1}, {"a": 0.2, "b": 0.8}]
    ) == pytest.approx(0.15)


def test_frozen_router_metrics_cover_accuracy_safety_confidence_and_mirrors() -> None:
    records = rows()
    report = evaluate_probabilities(records, perfect_predictions(records))

    assert report["route_accuracy"] == 1.0
    assert report["route_macro_f1"] == 1.0
    assert report["phase_macro_f1"] == 1.0
    assert report["network_required_recall"] == 1.0
    assert report["connector_recall"] == 1.0
    assert report["bare_summary_consistency"] == 1.0
    assert report["safety"] == {
        "network_required_fnr": 0.0,
        "unnecessary_network_rate": 0.0,
        "premature_final_when_evidence_missing": 0.0,
        "continue_after_policy_rejected": 0.0,
        "connector_downgraded_to_web": 0.0,
    }
    assert report["confidence"]["high_confidence_route_accuracy"] == 1.0
    assert report["confidence"]["ood_abstain_recall"] == 1.0
    assert report["confidence"]["wrong_without_abstain_rate"] == 0.0
    assert acceptance_gates(report, FIRST_ROUND_GATES)["passed"] is True
    assert acceptance_gates(report, FORMAL_GATES)["passed"] is True


def test_local_backend_settings_require_a_full_engine_revision() -> None:
    with pytest.raises(ValueError, match="full Git commit"):
        LocalVLLMRWKVSettings(engine_revision="main")


def test_derived_runtime_requires_one_complete_attestation() -> None:
    base = "a" * 40
    derived = "b" * 40
    with pytest.raises(ValueError, match="explicit derivation manifest"):
        LocalVLLMRWKVSettings(
            engine_revision=derived,
            model_artifact_engine_revision=base,
        )
    with pytest.raises(ValueError, match="manifest and manifest SHA-256"):
        LocalVLLMRWKVSettings(
            engine_revision=derived,
            model_artifact_engine_revision=base,
            runtime_derivation_manifest=Path("derivation.json"),
        )
    settings = LocalVLLMRWKVSettings(
        engine_revision=derived,
        model_artifact_engine_revision=base,
        runtime_derivation_manifest=Path("derivation.json"),
        runtime_derivation_manifest_sha256="c" * 64,
    )
    assert settings.engine_revision == derived
    assert settings.model_artifact_engine_revision == base


def test_metrics_reject_non_probability_scores() -> None:
    records = rows()[:1]
    prediction = perfect_predictions(records)
    prediction[0]["route_family"]["local"] += 0.2
    with pytest.raises(ValueError, match="sum to 1"):
        evaluate_probabilities(records, prediction)
