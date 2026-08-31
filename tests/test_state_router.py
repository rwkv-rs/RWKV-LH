from __future__ import annotations

from rwkv_lh.state_router.model import (
    HiddenFeatures,
    MultiHeadMLPArtifact,
    StateRouter,
)
from rwkv_lh.state_router.protocol import (
    HEAD_LABELS,
    ContextMode,
    EvidenceState,
    ExecutionPhase,
    NetworkRecommendation,
    PolicyState,
    RouteFamily,
    RouterInput,
    canonical_digest,
    resolve_router_output,
)


def probabilities(
    *,
    mode: str = "fresh",
    phase: str = "evidence_missing",
    route: str = "local",
    network: str = "network_not_required",
) -> dict[str, dict[str, float]]:
    winners = {
        "context_mode": mode,
        "execution_phase": phase,
        "route_family": route,
        "network_recommendation": network,
    }
    result: dict[str, dict[str, float]] = {}
    for name, labels in HEAD_LABELS.items():
        loser = 0.01 / (len(labels) - 1)
        result[name] = {
            label: 0.99 if label == winners[name] else loser for label in labels
        }
    return result


def fresh_input() -> RouterInput:
    return RouterInput(
        mode=ContextMode.FRESH,
        summary=None,
        evidence_state=EvidenceState.NONE,
        policy_state=PolicyState.NETWORK_ALLOWED,
        request="Read the local pyproject.toml.",
        trace_id="RTR-TEST",
    )


def test_router_input_renders_one_protocol_for_fresh_and_continuation() -> None:
    fresh = fresh_input()
    continued = RouterInput(
        mode=ContextMode.CONTINUATION,
        summary="The summary says evidence exists, but it is not authoritative.",
        evidence_state=EvidenceState.PARTIAL,
        policy_state=PolicyState.NETWORK_ALLOWED,
        request="Continue the same request.",
        trace_id="RTR-CONT",
    )

    assert fresh.render().splitlines() == [
        "Mode: fresh",
        "Summary: <none>",
        "EvidenceState: none",
        "PolicyState: network_allowed",
        'Request: "Read the local pyproject.toml."',
    ]
    assert continued.render().splitlines()[:4] == [
        "Mode: continuation",
        'Summary: "The summary says evidence exists, but it is not authoritative."',
        "EvidenceState: evidence_partial",
        "PolicyState: network_allowed",
    ]


def test_high_confidence_router_output_is_advisory_and_selects_discrete_profile() -> None:
    output = resolve_router_output(
        fresh_input(),
        probabilities(),
        model_hash="model-sha256",
        head_hash="head-sha256",
    )

    assert output.route_family is RouteFamily.LOCAL
    assert output.execution_phase is ExecutionPhase.EVIDENCE_MISSING
    assert output.network_recommendation is NetworkRecommendation.NOT_REQUIRED
    assert output.state_profile == "S_local"
    assert output.abstain is False


def test_controller_and_network_gate_facts_override_learned_phase() -> None:
    router_input = RouterInput(
        mode=ContextMode.CONTINUATION,
        summary="The task can proceed online.",
        evidence_state=EvidenceState.MISSING,
        policy_state=PolicyState.NETWORK_DENIED,
        request="Look up the current public release.",
        trace_id="RTR-DENIED",
    )
    output = resolve_router_output(
        router_input,
        probabilities(
            mode="continuation",
            phase="policy_rejected",
            route="web",
            network="network_required",
        ),
        model_hash="model-sha256",
        head_hash="head-sha256",
    )

    assert output.execution_phase is ExecutionPhase.POLICY_REJECTED
    assert output.route_family is RouteFamily.WEB
    assert output.network_recommendation is NetworkRecommendation.REQUIRED
    assert output.state_profile == "S_completion"


def test_head_conflict_forces_abstain_and_s_base() -> None:
    output = resolve_router_output(
        fresh_input(),
        probabilities(phase="evidence_committed"),
        model_hash="model-sha256",
        head_hash="head-sha256",
    )

    assert output.abstain is True
    assert output.route_family is RouteFamily.ABSTAIN
    assert output.candidate_route_family is RouteFamily.LOCAL
    assert output.state_profile == "S_base"
    assert "execution_phase_conflicts_with_controller" in output.abstain_reasons


def test_low_margin_forces_abstain_even_when_top_probability_is_high() -> None:
    values = probabilities()
    values["route_family"] = {
        label: (0.48 if label == "local" else 0.44 if label == "web" else 0.016)
        for label in HEAD_LABELS["route_family"]
    }
    output = resolve_router_output(
        fresh_input(),
        values,
        model_hash="model-sha256",
        head_hash="head-sha256",
    )

    assert output.abstain is True
    assert "route_confidence_below_threshold" in output.abstain_reasons
    assert "route_margin_below_threshold" in output.abstain_reasons


class StaticExtractor:
    def extract(self, texts: list[str]) -> list[HiddenFeatures]:
        assert texts and texts[0].startswith("Mode: fresh")
        return [
            HiddenFeatures(
                values=(1.0, -1.0),
                model_hash="model-sha256",
                token_count=8,
            )
            for _ in texts
        ]


def artifact_value() -> dict:
    heads: dict[str, dict] = {}
    winners = {
        "context_mode": "fresh",
        "execution_phase": "evidence_missing",
        "route_family": "local",
        "network_recommendation": "network_not_required",
    }
    for name, labels in HEAD_LABELS.items():
        heads[name] = {
            "weight": [[0.0, 0.0] for _ in labels],
            "bias": [10.0 if label == winners[name] else -10.0 for label in labels],
            "labels": list(labels),
        }
    value = {
        "schema_version": "rwkv-lh.state-router-head.v1",
        "feature_dim": 2,
        "hidden_dim": 2,
        "normalizer": {"mean": [0.0, 0.0], "std": [1.0, 1.0]},
        "shared": {
            "weight": [[1.0, 0.0], [0.0, 1.0]],
            "bias": [0.0, 0.0],
        },
        "layer_norm": {
            "weight": [1.0, 1.0],
            "bias": [0.0, 0.0],
            "eps": 1e-5,
        },
        "heads": heads,
        "temperatures": {name: 1.0 for name in HEAD_LABELS},
        "thresholds": {
            "route_confidence": 0.92,
            "route_margin": 0.30,
            "ood_score": 0.50,
        },
        "model_hash": "model-sha256",
        "metadata": {},
    }
    value["head_hash"] = canonical_digest(value)
    return value


def test_dependency_light_mlp_artifact_and_router_round_trip() -> None:
    artifact = MultiHeadMLPArtifact.from_dict(artifact_value())
    output = StateRouter(StaticExtractor(), artifact).route(fresh_input())

    assert output.route_family is RouteFamily.LOCAL
    assert output.abstain is False
    assert output.head_hash == artifact.head_hash


def test_artifact_rejects_label_order_and_threshold_drift() -> None:
    wrong_labels = artifact_value()
    wrong_labels["heads"]["context_mode"]["labels"].reverse()
    wrong_labels["head_hash"] = canonical_digest(
        {key: value for key, value in wrong_labels.items() if key != "head_hash"}
    )
    try:
        MultiHeadMLPArtifact.from_dict(wrong_labels)
    except ValueError as exc:
        assert "labels" in str(exc)
    else:
        raise AssertionError("artifact label drift was accepted")

    wrong_threshold = artifact_value()
    wrong_threshold["thresholds"]["route_confidence"] = 0.91
    wrong_threshold["head_hash"] = canonical_digest(
        {key: value for key, value in wrong_threshold.items() if key != "head_hash"}
    )
    try:
        MultiHeadMLPArtifact.from_dict(wrong_threshold)
    except ValueError as exc:
        assert "frozen thresholds" in str(exc)
    else:
        raise AssertionError("artifact threshold drift was accepted")
