from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS
from rwkv_lh.goal_state_protocols import selector_intent


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATASET = (
    PROJECT_ROOT / "data/datasets/rwkv_lh_g1j_selector_persistent_head_v2"
)


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_selector_v2_dataset_is_balanced_and_split_by_sequence() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["dataset_id"] == "rwkv_lh_g1j_selector_persistent_head_v2"
    assert manifest["protocol"]["trajectory_mode"] == "persistent-causal-sequences.v1"
    assert manifest["protocol"]["labels"] == list(NETWORK_EXACT_TOOL_LABELS)
    assert manifest["counts"] == {
        "rows": 500,
        "train": 300,
        "dev": 100,
        "sealed": 100,
        "sequences": 250,
        "train_sequences": 150,
        "dev_sequences": 50,
        "sealed_sequences": 50,
        "sequence_length_histogram": {"2": 250},
    }
    assert manifest["similarity"]["algorithm"] == "utf8-byte-5gram-cosine.v1"
    for comparison in ("train_dev", "train_sealed", "dev_sealed"):
        assert manifest["similarity"][comparison]["maximum"] < 0.95
    for split, support in (("train", 12), ("dev", 4), ("sealed", 4)):
        assert manifest["label_counts"][split] == {
            label: support for label in sorted(NETWORK_EXACT_TOOL_LABELS)
        }

    public_sequences = _rows(DATASET / "sequence_registry.jsonl")
    sealed_sequences = _rows(DATASET / "sealed/sequence_registry.jsonl")
    assert len(public_sequences) == 200
    assert len(sealed_sequences) == 50
    sequence_ids = [row["sequence_id"] for row in public_sequences + sealed_sequences]
    assert len(sequence_ids) == len(set(sequence_ids)) == 250
    for sequence in public_sequences + sealed_sequences:
        assert sequence["positions"] == [0, 1]
        assert sequence["state_reset_before_position"] == [True, False]
        assert len(sequence["source_ids"]) == len(sequence["sample_ids"]) == 2


def test_selector_v2_dataset_files_and_prompts_are_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    for name, record in manifest["files"].items():
        path = DATASET / name
        assert path.is_file()
        assert _sha256(path) == record["sha256"]
        assert len(path.read_bytes()) == record["bytes"]

    sources = _rows(DATASET / "source_registry.jsonl") + _rows(
        DATASET / "sealed/source_registry.jsonl"
    )
    samples = _rows(DATASET / "sample_index.jsonl") + _rows(
        DATASET / "sealed/sample_index.jsonl"
    )
    sample_by_source = {row["source_id"]: row for row in samples}
    assert len(sources) == len(sample_by_source) == 500
    assert Counter(row["split"] for row in sources) == {
        "train": 300,
        "dev": 100,
        "sealed": 100,
    }
    for source in sources:
        payload = source["payload"]
        selector_intent.validate_source(payload)
        prompt = selector_intent.render_prompt(payload)
        target = selector_intent.render_target(payload)
        sample = sample_by_source[source["source_id"]]
        assert hashlib.sha256(prompt.encode()).hexdigest() == sample["prompt_sha256"]
        assert hashlib.sha256(target.encode()).hexdigest() == sample["target_sha256"]
        assert selector_intent.parse_target(target) == payload["selected_operation"]


def test_selector_v2_second_rows_are_true_same_scope_transitions() -> None:
    sources = _rows(DATASET / "source_registry.jsonl") + _rows(
        DATASET / "sealed/source_registry.jsonl"
    )
    by_sequence: dict[str, list[dict[str, object]]] = {}
    for source in sources:
        by_sequence.setdefault(str(source["sequence_id"]), []).append(source)
    assert len(by_sequence) == 250

    for sequence_id, sequence in by_sequence.items():
        sequence.sort(key=lambda row: int(row["sequence_position"]))
        first, second = sequence
        assert [first["sequence_position"], second["sequence_position"]] == [0, 1]
        assert first["split"] == second["split"]
        first_payload = first["payload"]
        second_payload = second["payload"]
        assert first_payload["eligible_labels"] == second_payload["eligible_labels"]
        if sequence_id.endswith("-FINAL"):
            assert first_payload["eligible_labels"] == ["final_answer"]
            assert second_payload["selected_operation"] == "final_answer"
            assert first_payload["stage_objective"].startswith("CurrentDirectStageV3: ")
            continue
        first_frontier = json.loads(
            first_payload["stage_objective"].removeprefix("GoalFrontierStateV1: ")
        )
        second_frontier = json.loads(
            second_payload["stage_objective"].removeprefix("GoalFrontierStateV1: ")
        )
        assert first_frontier["active_step"] == second_frontier["active_step"]
        assert first_frontier["current_objective"] == second_frontier["current_objective"]
        if sequence_id.endswith("-ABSTAIN"):
            assert second_payload["selected_operation"] == "ABSTAIN"
            assert second_payload["progress"]["protocol_rejection_count"] == 1
            assert second_frontier["latest_action"] is None
            continue
        assert first_frontier["latest_action"] is None
        assert second_frontier["latest_action"]["operation"] == first_payload[
            "selected_operation"
        ]
        assert second_frontier["latest_action"]["status"] == "succeeded"
        assert second_frontier["progress"]["current_step_action_count"] == 1
        assert second_payload["progress"]["succeeded_operations"] == [
            first_payload["selected_operation"]
        ]
        assert second_payload["selected_operation"] != first_payload[
            "selected_operation"
        ]
