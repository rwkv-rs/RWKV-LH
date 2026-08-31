from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_current_harness_identifiable_s26_v1"
CASES_SHA256 = "4a01c16a2e320e7754529544ea0299e5abdd6015b0b079c78c1f7d9ab24e4465"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows() -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]


def test_s26_manifest_and_balanced_contract_are_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {"rows": 3000, "sha256": CASES_SHA256}
    assert manifest["architecture"] == "current-direct-LongHorizonModel-dual-state"
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert manifest["language_counts"] == {
        "train": {"en": 1000, "zh": 1000},
        "dev": {"en": 250, "zh": 250},
        "test": {"en": 250, "zh": 250},
    }
    assert manifest["phase_counts"] == {
        "train": {"first": 1000, "continuation_1": 800, "continuation_2": 200},
        "dev": {"first": 250, "continuation_1": 200, "continuation_2": 50},
        "test": {"first": 250, "continuation_1": 200, "continuation_2": 50},
    }
    assert manifest["validation"]["surface_variant_partition"] == {
        "train": [0, 1, 2, 3], "dev": [4], "test": [5]
    }
    assert manifest["validation"]["holdout_similarity"]["maximum"]["score"] < 0.75
    assert manifest["generated_rwkv_text_count"] == 0
    assert manifest["contains_full_tool_results"] is False
    assert manifest["contains_tool_schemas"] is False
    assert manifest["contains_executor_text"] is False


def test_s26_all_rows_match_the_persistent_current_harness_protocol() -> None:
    values = rows()
    assert len(values) == 3000
    assert len({row["sample_id"] for row in values}) == 3000
    assert len({row["semantic_family_id"] for row in values}) == 3000
    assert len({row["trajectory_rendered_input"] for row in values}) == 3000
    for split, per_label in (("train", 80), ("dev", 20), ("test", 20)):
        selected = [row for row in values if row["split"] == split]
        assert Counter(row["label"] for row in selected) == Counter(
            {label: per_label for label in NETWORK_EXACT_TOOL_LABELS}
        )
        assert all(
            Counter(
                row["language"]
                for row in selected
                if row["label"] == label
            ) == {"en": per_label // 2, "zh": per_label // 2}
            for label in NETWORK_EXACT_TOOL_LABELS
        )

    families = {
        split: {row["semantic_family_id"] for row in values if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert not families["train"] & families["dev"]
    assert not families["train"] & families["test"]
    assert not families["dev"] & families["test"]

    for row in values:
        depth = int(row["decision_index"])
        history_steps = list(row["history_steps"])
        history_labels = list(row["expected_history_labels"])
        assert depth in {0, 1, 2}
        assert len(history_steps) == len(history_labels) == depth
        assert row["request_identifiable"] is True
        assert row["persistent_history_replay_required"] is bool(depth)
        assert row["generated_rwkv_text"] is False
        assert row["contains_full_tool_results"] is False
        assert row["contains_tool_schemas"] is False
        assert row["contains_executor_text"] is False

        current = dict(row["selector_input"])
        selector = NetworkSelectorInput(
            task_request=current["task_request"],
            stage_objective=current["stage_objective"],
            stage_role=current["stage_role"],
            progress=NetworkSelectorProgress(**{
                **current["progress"],
                "succeeded_operations": tuple(current["progress"]["succeeded_operations"]),
                "failed_operations": tuple(current["progress"]["failed_operations"]),
            }),
            menu=tuple(current["tools"]),
            schema_version=current["schema_version"],
        )
        assert selector.render_bootstrap() == row["bootstrap"]
        assert selector.render_step() == row["step"]
        expected_trajectory = row["bootstrap"] + "".join(
            "\n" + step for step in [*history_steps, row["step"]]
        )
        assert expected_trajectory == row["trajectory_rendered_input"]
        assert hashlib.sha256(expected_trajectory.encode("utf-8")).hexdigest() == row["trajectory_rendered_input_sha256"]
        assert current["stage_objective"].startswith("CurrentDirectStageV1: ")
        assert current["stage_role"] == "work"
        assert set(current["tools"][0]) == {"name", "description"}
        assert all(set(item) == {"name", "description"} for item in current["tools"])
        progress = current["progress"]
        assert progress["action_index"] == depth
        assert progress["completed_stage_count"] == depth
        assert progress["failed_operations"] == []
        assert progress["succeeded_operations"] == ([] if depth == 0 else [history_labels[-1]])

        for index, step_text in enumerate(history_steps):
            payload = json.loads(step_text.removeprefix("SelectorStepV2: "))
            assert payload["stage_objective"].startswith("CurrentDirectStageV1: ")
            assert payload["progress"]["action_index"] == index
            assert payload["progress"]["completed_stage_count"] == index
            assert payload["progress"]["failed_operations"] == []
            assert payload["progress"]["succeeded_operations"] == (
                [] if index == 0 else [history_labels[index - 1]]
            )


def test_s26_test_surface_families_are_not_present_in_training() -> None:
    values = rows()
    by_split = {
        split: {int(row["surface_variant"]) for row in values if row["split"] == split}
        for split in ("train", "dev", "test")
    }
    assert by_split == {"train": {0, 1, 2, 3}, "dev": {4}, "test": {5}}
    assert all(
        row["source"]["kind"] in {
            "v2_4_explicit_intent_promoted_to_literal_request",
            "deterministic_bilingual_tool_contract_fixture",
        }
        for row in values
    )
