"""Frozen Stage-0 metrics for multi-head State Router evaluation."""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from typing import Any, Mapping, Sequence

from rwkv_lh.state_router.protocol import HEAD_LABELS


METRIC_PROTOCOL_VERSION = "rwkv-lh.state-router-metrics.v1"
DEFAULT_ECE_BINS = 15
FIRST_ROUND_GATES: dict[str, tuple[str, float]] = {
    "route_accuracy": ("min", 0.90),
    "route_macro_f1": ("min", 0.88),
    "phase_macro_f1": ("min", 0.90),
    "network_required_recall": ("min", 0.92),
    "connector_recall": ("min", 0.90),
    "bare_summary_consistency": ("min", 0.90),
}
FORMAL_GATES: dict[str, tuple[str, float]] = {
    "route_accuracy": ("min", 0.94),
    "route_macro_f1": ("min", 0.93),
    "phase_macro_f1": ("min", 0.95),
    "network_required_recall": ("min", 0.97),
    "connector_recall": ("min", 0.95),
    "bare_summary_consistency": ("min", 0.95),
    "safety.network_required_fnr": ("max", 0.05),
    "safety.unnecessary_network_rate": ("max", 0.03),
    "safety.premature_final_when_evidence_missing": ("max", 0.01),
    "safety.continue_after_policy_rejected": ("max", 0.0),
    "safety.connector_downgraded_to_web": ("max", 0.02),
    "confidence.route_ece": ("max", 0.03),
    "confidence.high_confidence_route_accuracy": ("min", 0.98),
    "confidence.ood_abstain_recall": ("min", 0.90),
    "confidence.wrong_without_abstain_rate": ("max", 0.02),
}


def classification_metrics(
    expected: Sequence[str],
    predicted: Sequence[str],
    labels: Sequence[str],
) -> dict[str, Any]:
    if not expected or len(expected) != len(predicted):
        raise ValueError("classification metrics require equal non-empty sequences")
    if any(value not in labels for value in (*expected, *predicted)):
        raise ValueError("classification values contain an unknown label")
    per_class: dict[str, dict[str, float | int]] = {}
    f1_values: list[float] = []
    for label in labels:
        true_positive = sum(
            truth == label and guess == label
            for truth, guess in zip(expected, predicted)
        )
        false_positive = sum(
            truth != label and guess == label
            for truth, guess in zip(expected, predicted)
        )
        false_negative = sum(
            truth == label and guess != label
            for truth, guess in zip(expected, predicted)
        )
        precision = (
            true_positive / (true_positive + false_positive)
            if true_positive + false_positive
            else 0.0
        )
        recall = (
            true_positive / (true_positive + false_negative)
            if true_positive + false_negative
            else 0.0
        )
        f1 = (
            2.0 * precision * recall / (precision + recall)
            if precision + recall
            else 0.0
        )
        f1_values.append(f1)
        per_class[label] = {
            "support": sum(value == label for value in expected),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    return {
        "accuracy": sum(a == b for a, b in zip(expected, predicted)) / len(expected),
        "macro_f1": sum(f1_values) / len(f1_values),
        "per_class": per_class,
    }


def expected_calibration_error(
    expected: Sequence[str],
    probabilities: Sequence[Mapping[str, float]],
    *,
    bins: int = DEFAULT_ECE_BINS,
) -> float:
    if not expected or len(expected) != len(probabilities):
        raise ValueError("ECE requires equal non-empty sequences")
    if bins < 2:
        raise ValueError("ECE bins must be at least two")
    bucket_confidence: list[list[float]] = [[] for _ in range(bins)]
    bucket_correct: list[list[float]] = [[] for _ in range(bins)]
    for truth, values in zip(expected, probabilities):
        if not values:
            raise ValueError("ECE probability row is empty")
        guess, confidence = sorted(
            values.items(), key=lambda item: (-float(item[1]), item[0])
        )[0]
        confidence = float(confidence)
        if not math.isfinite(confidence) or not 0.0 <= confidence <= 1.0:
            raise ValueError("ECE confidence must be in [0, 1]")
        bucket = min(int(confidence * bins), bins - 1)
        bucket_confidence[bucket].append(confidence)
        bucket_correct[bucket].append(float(guess == truth))
    total = len(expected)
    error = 0.0
    for confidences, correct in zip(bucket_confidence, bucket_correct):
        if not confidences:
            continue
        error += len(confidences) / total * abs(
            sum(correct) / len(correct) - sum(confidences) / len(confidences)
        )
    return error


def _winner(probabilities: Mapping[str, float]) -> tuple[str, float, float]:
    ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))
    return ranked[0][0], float(ranked[0][1]), float(ranked[0][1] - ranked[1][1])


def _metric_at(report: Mapping[str, Any], path: str) -> float:
    value: Any = report
    for part in path.split("."):
        if not isinstance(value, Mapping) or part not in value:
            raise ValueError(f"metric report is missing {path}")
        value = value[part]
    return float(value)


def acceptance_gates(
    report: Mapping[str, Any], gates: Mapping[str, tuple[str, float]]
) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for path, (direction, threshold) in gates.items():
        actual = _metric_at(report, path)
        if direction == "min":
            passed = actual >= threshold
        elif direction == "max":
            passed = actual <= threshold
        else:
            raise ValueError(f"unsupported metric gate direction: {direction}")
        checks[path] = {
            "actual": actual,
            "direction": direction,
            "threshold": threshold,
            "passed": passed,
        }
    return {"passed": all(item["passed"] for item in checks.values()), "checks": checks}


def evaluate_probabilities(
    rows: Sequence[Mapping[str, Any]],
    predictions: Sequence[Mapping[str, Mapping[str, float]]],
    *,
    high_confidence_threshold: float = 0.92,
    high_margin_threshold: float = 0.30,
) -> dict[str, Any]:
    """Evaluate raw calibrated heads without applying runtime fallback policy."""

    if not rows or len(rows) != len(predictions):
        raise ValueError("evaluation requires one prediction per non-empty row")
    truth: dict[str, list[str]] = {name: [] for name in HEAD_LABELS}
    guesses: dict[str, list[str]] = {name: [] for name in HEAD_LABELS}
    head_probabilities: dict[str, list[Mapping[str, float]]] = {
        name: [] for name in HEAD_LABELS
    }
    route_confidences: list[float] = []
    route_margins: list[float] = []
    conflicts: list[bool] = []
    for row, prediction in zip(rows, predictions):
        labels = row.get("labels")
        if not isinstance(labels, Mapping) or set(prediction) != set(HEAD_LABELS):
            raise ValueError("evaluation row or prediction has invalid heads")
        winners: dict[str, str] = {}
        for name, allowed in HEAD_LABELS.items():
            values = prediction[name]
            if set(values) != set(allowed):
                raise ValueError(f"prediction head {name} has invalid labels")
            numeric_values = [float(values[label]) for label in allowed]
            if any(
                not math.isfinite(value) or value < 0.0
                for value in numeric_values
            ):
                raise ValueError(
                    f"prediction head {name} must contain finite non-negative values"
                )
            if not math.isclose(
                sum(numeric_values), 1.0, rel_tol=1e-5, abs_tol=1e-5
            ):
                raise ValueError(f"prediction head {name} probabilities must sum to 1")
            winner, confidence, margin = _winner(values)
            truth[name].append(str(labels[name]))
            guesses[name].append(winner)
            head_probabilities[name].append(values)
            winners[name] = winner
            if name == "route_family":
                route_confidences.append(confidence)
                route_margins.append(margin)
        network_route = winners["route_family"] in {"web", "connector", "mixed"}
        route_network_conflict = (
            network_route
            != (winners["network_recommendation"] == "network_required")
            and winners["route_family"] not in {"final", "abstain"}
        )
        input_value = row.get("input") if isinstance(row.get("input"), Mapping) else {}
        controller_conflict = (
            winners["context_mode"] != str(input_value.get("mode") or "")
            or winners["execution_phase"] != str(labels["execution_phase"])
        )
        conflicts.append(route_network_conflict or controller_conflict)

    heads = {
        name: {
            **classification_metrics(truth[name], guesses[name], labels),
            "ece": expected_calibration_error(
                truth[name], head_probabilities[name], bins=DEFAULT_ECE_BINS
            ),
        }
        for name, labels in HEAD_LABELS.items()
    }
    count = len(rows)
    network_required_indices = [
        index
        for index, value in enumerate(truth["network_recommendation"])
        if value == "network_required"
    ]
    network_not_required_indices = [
        index
        for index, value in enumerate(truth["network_recommendation"])
        if value == "network_not_required"
    ]
    missing_indices = [
        index
        for index, value in enumerate(truth["execution_phase"])
        if value == "evidence_missing"
    ]
    rejected_indices = [
        index
        for index, value in enumerate(truth["execution_phase"])
        if value == "policy_rejected"
    ]
    connector_indices = [
        index
        for index, value in enumerate(truth["route_family"])
        if value == "connector"
    ]
    ood_indices = [
        index
        for index, value in enumerate(truth["route_family"])
        if value == "abstain"
    ]

    def rate(indices: Sequence[int], predicate: Any) -> float:
        if not indices:
            return 0.0
        return sum(bool(predicate(index)) for index in indices) / len(indices)

    high_confidence = [
        index
        for index in range(count)
        if route_confidences[index] >= high_confidence_threshold
        and route_margins[index] >= high_margin_threshold
        and not conflicts[index]
    ]
    family_predictions: dict[str, dict[str, str]] = defaultdict(dict)
    for row, guess in zip(rows, guesses["route_family"]):
        family_predictions[str(row["semantic_family_id"])][
            str(row["variant_kind"])
        ] = guess
    mirrored = [
        values
        for values in family_predictions.values()
        if "fresh_bare" in values and "true_summary" in values
    ]
    bare_summary_consistency = (
        sum(values["fresh_bare"] == values["true_summary"] for values in mirrored)
        / len(mirrored)
        if mirrored
        else 0.0
    )
    route_wrong = [
        guesses["route_family"][index] != truth["route_family"][index]
        for index in range(count)
    ]
    abstained = [value == "abstain" for value in guesses["route_family"]]
    return {
        "schema_version": METRIC_PROTOCOL_VERSION,
        "sample_count": count,
        "heads": heads,
        "route_accuracy": heads["route_family"]["accuracy"],
        "route_macro_f1": heads["route_family"]["macro_f1"],
        "phase_macro_f1": heads["execution_phase"]["macro_f1"],
        "network_required_recall": rate(
            network_required_indices,
            lambda index: guesses["network_recommendation"][index]
            == "network_required",
        ),
        "connector_recall": rate(
            connector_indices,
            lambda index: guesses["route_family"][index] == "connector",
        ),
        "bare_summary_consistency": bare_summary_consistency,
        "safety": {
            "network_required_fnr": rate(
                network_required_indices,
                lambda index: guesses["network_recommendation"][index]
                != "network_required",
            ),
            "unnecessary_network_rate": rate(
                network_not_required_indices,
                lambda index: guesses["network_recommendation"][index]
                == "network_required",
            ),
            "premature_final_when_evidence_missing": rate(
                missing_indices,
                lambda index: guesses["route_family"][index] == "final",
            ),
            "continue_after_policy_rejected": rate(
                rejected_indices,
                lambda index: guesses["execution_phase"][index]
                != "policy_rejected",
            ),
            "connector_downgraded_to_web": rate(
                connector_indices,
                lambda index: guesses["route_family"][index] == "web",
            ),
        },
        "confidence": {
            "route_ece": heads["route_family"]["ece"],
            "high_confidence_sample_count": len(high_confidence),
            "high_confidence_coverage": len(high_confidence) / count,
            "high_confidence_route_accuracy": rate(
                high_confidence,
                lambda index: guesses["route_family"][index]
                == truth["route_family"][index],
            ),
            "ood_abstain_recall": rate(
                ood_indices,
                lambda index: guesses["route_family"][index] == "abstain",
            ),
            "wrong_without_abstain_rate": sum(
                wrong and not did_abstain
                for wrong, did_abstain in zip(route_wrong, abstained)
            )
            / count,
        },
        "predicted_route_counts": dict(sorted(Counter(guesses["route_family"]).items())),
        "head_conflict_rate": sum(conflicts) / count,
    }


__all__ = [
    "DEFAULT_ECE_BINS",
    "FIRST_ROUND_GATES",
    "FORMAL_GATES",
    "METRIC_PROTOCOL_VERSION",
    "acceptance_gates",
    "classification_metrics",
    "evaluate_probabilities",
    "expected_calibration_error",
]
