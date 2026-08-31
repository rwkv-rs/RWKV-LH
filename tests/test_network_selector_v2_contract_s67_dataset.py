from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    compact_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.compact_protocol_v7 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    SELECTOR_CURRENT_QUESTION,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_v2_contract_s67_v1"
CASES = DATASET / "cases.jsonl"
MANIFEST = DATASET / "manifest.json"
TRAIN_STATE = DATASET / "rwkv_state_tuning.train.requires_target_suffix.jsonl"
DEV_STATE = DATASET / "rwkv_state_tuning.dev.requires_target_suffix.jsonl"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_s67_frozen_manifest_and_current_runtime_rows() -> None:
    assert sha256_file(CASES) == "0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859"
    assert sha256_file(MANIFEST) == "0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46"
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert manifest["holdout"]["maximum_similarity"]["score"] < 0.95
    assert manifest["split_integrity"] == {
        "exact_request_overlap": 0,
        "lexicon_pool_intersection_count": 0,
        "rendered_input_overlap": 0,
        "source_family_overlap": 0,
    }
    assert manifest["role_purity"] == {
        "executor_text_count": 0,
        "full_tool_result_count": 0,
        "generated_rwkv_text_count": 0,
        "hidden_acceptance_count": 0,
        "parameter_schema_count": 0,
        "planner_raw_json_count": 0,
        "raw_rwkv_output_modified": False,
        "sampling_invoked": False,
    }

    expected_labels = {item["name"] for item in compact_selector_tool_menu()}
    rows = read_jsonl(CASES)
    counts: Counter[tuple[str, str]] = Counter()
    languages: Counter[tuple[str, str]] = Counter()
    inputs_by_split: dict[str, set[str]] = defaultdict(set)
    families_by_split: dict[str, set[str]] = defaultdict(set)
    requests_by_split: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        split = str(row["split"])
        label = str(row["label"])
        rendered_input = str(row["rendered_input"])
        task_request = str(row["task_request"])
        assert row["projection_version"] == "rwkv-lh.current-direct-selector-stage.v2"
        assert str(row["stage_objective"]).startswith("CurrentDirectStageV2: ")
        assert row["compact_input_schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
        assert row["complete_requirement_byte_tail"] is True
        assert row["current_requirement_is_atom_objective"] is True
        assert row["generated_rwkv_text"] is False
        assert row["hidden_acceptance_used"] is False
        assert row["contains_executor_text"] is False
        assert row["contains_full_tool_results"] is False
        assert row["contains_parameter_schemas"] is False
        assert row["contains_planner_raw_json"] is False
        assert hashlib.sha256(rendered_input.encode()).hexdigest() == row["rendered_input_sha256"]

        step = json.loads(rendered_input.rsplit("\nSelectorStepV7: ", maxsplit=1)[1])
        question = step["current_question"]
        assert list(step)[-1] == "current_question"
        assert list(question) == ["question", "current_stage", "complete_requirement"]
        assert question["question"] == SELECTOR_CURRENT_QUESTION
        assert question["current_stage"] == row["stage_objective"]
        assert question["complete_requirement"] == task_request
        assert rendered_input.endswith(json.dumps(task_request, ensure_ascii=False) + "}}")

        counts[(split, label)] += 1
        languages[(split, str(row["language"]))] += 1
        inputs_by_split[split].add(str(row["rendered_input_sha256"]))
        families_by_split[split].add(str(row["source_family_id"]))
        requests_by_split[split].add(task_request)

    assert len(rows) == 3000
    assert {label for _, label in counts} == expected_labels
    for label in expected_labels:
        assert counts[("train", label)] == 80
        assert counts[("dev", label)] == 20
        assert counts[("test", label)] == 20
    assert languages == {
        ("train", "en"): 1000,
        ("train", "zh"): 1000,
        ("dev", "en"): 250,
        ("dev", "zh"): 250,
        ("test", "en"): 250,
        ("test", "zh"): 250,
    }
    for left, right in (("train", "dev"), ("train", "test"), ("dev", "test")):
        assert inputs_by_split[left].isdisjoint(inputs_by_split[right])
        assert families_by_split[left].isdisjoint(families_by_split[right])
        assert requests_by_split[left].isdisjoint(requests_by_split[right])


def test_s67_state_exports_cover_only_train_and_dev_with_additive_targets() -> None:
    assert sha256_file(TRAIN_STATE) == "f47864e3e58e437bd5b91e8b52158e3b01accf28292fb99c3f7e0e0a03b85cd0"
    assert sha256_file(DEV_STATE) == "06bec25d03277bd135f59d8d7af745b55bce234900768afebaaf26f121987d13"
    case_rows = {str(row["sample_id"]): row for row in read_jsonl(CASES)}
    state_rows = read_jsonl(TRAIN_STATE) + read_jsonl(DEV_STATE)
    assert len(state_rows) == 2500
    assert {str(row["split"]) for row in state_rows} == {"train", "dev"}
    assert not any(str(row["split"]) == "test" for row in state_rows)

    for row in state_rows:
        source = case_rows[str(row["source_sample_id"])]
        target = "\nSelectorLabelV7: " + str(row["label"])
        assert row["split"] == source["split"]
        assert row["label"] == source["label"]
        assert row["prompt"] == source["rendered_input"]
        assert row["target"] == target
        assert row["text"] == str(row["prompt"]) + target
        assert row["loss_mask"] == "target_suffix"
        assert row["jsonl_bos_token_id"] == 0
        assert row["request_last"] is True
        assert row["persistent_history_replayed"] is True
        assert row["generated_rwkv_text"] is False
        assert row["raw_rwkv_output_modified"] is False
        assert int(row["text_tokens_including_bos"]) <= 2496
