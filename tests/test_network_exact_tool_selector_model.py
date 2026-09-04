from __future__ import annotations

from pathlib import Path

import pytest

from rwkv_lh.exact_tool_selector.head import (
    NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL,
    NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
    NetworkSelectorMLPArtifact,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NETWORK_SELECTOR_MENU_ORDER_IDS,
    NetworkExactToolSelection,
    NetworkSelectorInput,
)
from rwkv_lh.model import LongHorizonModel
from rwkv_lh.model_io import canonical_digest
from rwkv_lh.tokenizer import RWKVTokenizer


def _artifact_value() -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": NETWORK_SELECTOR_HEAD_SCHEMA_VERSION,
        "feature_dim": 2,
        "hidden_dim": 2,
        "labels": list(NETWORK_EXACT_TOOL_LABELS),
        "feature_protocol": "rwkv-lh.vllm-rwkv-final-hidden-last.v1",
        "feature_mean": [0.0, 0.0],
        "feature_std": [1.0, 1.0],
        "shared_weight": [[1.0, 0.0], [0.0, 1.0]],
        "shared_bias": [0.0, 0.0],
        "layer_norm_weight": [1.0, 1.0],
        "layer_norm_bias": [0.0, 0.0],
        "head_weight": [
            [float(index), -float(index)]
            for index in range(len(NETWORK_EXACT_TOOL_LABELS))
        ],
        "head_bias": [0.0] * len(NETWORK_EXACT_TOOL_LABELS),
        "temperature": 0.8,
        "model_hash": "1" * 64,
        "metadata": {"fixture": True},
    }
    value["head_hash"] = canonical_digest(value)
    return value


def test_network_selector_mlp_preserves_all_raw_logits_and_argmax() -> None:
    artifact = NetworkSelectorMLPArtifact.from_dict(_artifact_value())

    logits = artifact.raw_logits([2.0, -1.0])

    assert len(logits) == len(NETWORK_EXACT_TOOL_LABELS)
    assert artifact.select([2.0, -1.0]) == NETWORK_EXACT_TOOL_LABELS[-1]
    assert sum(artifact.probabilities([2.0, -1.0])) == pytest.approx(1.0)


def test_network_selector_mlp_rejects_artifact_mutation() -> None:
    value = _artifact_value()
    value["temperature"] = 1.2

    with pytest.raises(ValueError, match="digest mismatch"):
        NetworkSelectorMLPArtifact.from_dict(value)


def test_network_selector_mlp_registers_same_forward_fusion_protocol() -> None:
    value = _artifact_value()
    value["feature_protocol"] = NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL
    value["head_hash"] = canonical_digest(
        {key: item for key, item in value.items() if key != "head_hash"}
    )

    artifact = NetworkSelectorMLPArtifact.from_dict(value)

    assert artifact.feature_protocol == NETWORK_SELECTOR_FUSION_FEATURE_PROTOCOL


def test_selector_menu_order_ablation_has_three_fixed_permutations() -> None:
    inputs = [
        NetworkSelectorInput.create(
            current_subtask={
                "objective": "Inspect one file.",
                "phase": "observe",
                "read_roots": ["fixture.txt"],
                "write_roots": [],
                "success_evidence": ["file contents observed"],
                "constraints": [],
            },
            eligible_labels=("search_text", "read_file", "write_file"),
            menu_order_id=menu_order_id,
        )
        for menu_order_id in NETWORK_SELECTOR_MENU_ORDER_IDS
    ]

    assert len({item.menu_digest for item in inputs}) == 3
    assert all(
        {tool["name"] for tool in item.menu} == set(NETWORK_EXACT_TOOL_LABELS)
        for item in inputs
    )
    assert [item.menu_order_id for item in inputs] == list(
        NETWORK_SELECTOR_MENU_ORDER_IDS
    )


def test_selector_menu_votes_are_independent_and_below_context_limit() -> None:
    subtask = {
        "objective": "Read src/pricing.py and verify the price calculation rule.",
        "phase": "observe",
        "read_roots": ["src/pricing.py"],
        "write_roots": [],
        "success_evidence": ["the exact rule is observed from src/pricing.py"],
        "constraints": ["do not modify files"],
    }
    inputs = [
        NetworkSelectorInput.create(
            current_subtask=subtask,
            menu_order_id=menu_order_id,
        )
        for menu_order_id in NETWORK_SELECTOR_MENU_ORDER_IDS
    ]
    tokenizer = RWKVTokenizer(
        Path(__file__).resolve().parents[1]
        / "rwkv_lh/data/rwkv_vocab_v20230424.txt"
    )

    assert [len(tokenizer.encode(item.render())) for item in inputs] == [725, 725, 727]
    assert all(item.current_subtask == subtask for item in inputs)
    assert all("progress" not in item.render() for item in inputs)
    assert all("latest_action" not in item.render() for item in inputs)


def _selection(
    selection_id: str,
    scores: dict[str, float],
    *,
    eligible_labels: tuple[str, ...],
) -> NetworkExactToolSelection:
    logits = [0.0] * len(NETWORK_EXACT_TOOL_LABELS)
    for label, score in scores.items():
        logits[NETWORK_EXACT_TOOL_LABELS.index(label)] = score
    selected = max(
        eligible_labels,
        key=lambda label: (
            logits[NETWORK_EXACT_TOOL_LABELS.index(label)],
            -NETWORK_EXACT_TOOL_LABELS.index(label),
        ),
    )
    return NetworkExactToolSelection(
        selection_id=selection_id,
        trace_id=f"TRACE-{selection_id}",
        selected_operation=selected,
        logits=tuple(logits),
        temperature=0.25,
        input_digest="1" * 64,
        menu_digest="2" * 64,
        selector_checkpoint_id=f"CP-{selection_id}",
        input_token_count=10,
        model="selector",
        model_sha256="4" * 64,
        head_sha256="5" * 64,
        profile_id="zero",
        profile_sha256="6" * 64,
        eligible_labels=eligible_labels,
    )


def test_selector_menu_order_vote_uses_majority_then_registered_tie_break() -> None:
    eligible = ("search_text", "read_file", "write_file")
    majority = [
        _selection("A", {"read_file": 5.0}, eligible_labels=eligible),
        _selection("B", {"read_file": 4.0}, eligible_labels=eligible),
        _selection("C", {"write_file": 6.0}, eligible_labels=eligible),
    ]
    selected, record = LongHorizonModel._selector_ensemble_choice(
        majority,
        eligible_labels=eligible,
    )
    assert selected == "read_file"
    assert record["aggregation_rule"] == "two_of_three_majority"

    three_way = [
        _selection(
            "D",
            {"read_file": 5.0, "write_file": 4.0},
            eligible_labels=eligible,
        ),
        _selection(
            "E",
            {"write_file": 5.0, "read_file": 4.0},
            eligible_labels=eligible,
        ),
        _selection(
            "F",
            {"search_text": 5.0, "read_file": 4.0},
            eligible_labels=eligible,
        ),
    ]
    selected, record = LongHorizonModel._selector_ensemble_choice(
        three_way,
        eligible_labels=eligible,
    )
    assert selected == "read_file"
    assert record["aggregation_rule"] == (
        "three_way_tie_median_rank_then_normalized_logit"
    )
    assert record["state_policy"] == "three_fresh_initial_state_evaluations"
