from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_compact_current_harness_s28_v1"
CASES_SHA256 = "a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def rows() -> list[dict[str, object]]:
    return [json.loads(line) for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()]


def test_s28_manifest_freezes_all_25_classes_and_new_blind_split() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {"rows": 7500, "sha256": CASES_SHA256}
    assert manifest["counts"] == {"train": 6000, "dev": 750, "test": 750}
    assert manifest["class_count"] == 25
    assert manifest["executable_tool_count"] == 23
    assert manifest["control_label_count"] == 2
    assert manifest["language_counts"] == {
        "train": {"en": 4000, "zh": 2000},
        "dev": {"en": 375, "zh": 375},
        "test": {"en": 375, "zh": 375},
    }
    assert manifest["phase_counts"] == {
        "train": {"first": 3000, "continuation_1": 2400, "continuation_2": 600},
        "dev": {"first": 350, "continuation_1": 300, "continuation_2": 100},
        "test": {"first": 350, "continuation_1": 300, "continuation_2": 100},
    }
    assert manifest["input_protocol"]["schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
    assert manifest["input_protocol"]["menu_digest"] == compact_selector_menu_digest()
    assert manifest["input_protocol"]["menu_first_task_last"] is True
    assert manifest["input_protocol"]["names_and_descriptions_only"] is True
    assert manifest["validation"]["holdout_similarity"]["maximum"]["score"] < 0.75
    assert manifest["generated_rwkv_text_count"] == 0
    assert manifest["contains_parameter_schemas"] is False
    assert manifest["contains_full_tool_results"] is False
    assert manifest["contains_executor_text"] is False


def test_s28_rows_are_balanced_and_all_family_axes_are_disjoint() -> None:
    values = rows()
    assert len(values) == 7500
    assert len({row["sample_id"] for row in values}) == 7500
    assert len({row["trajectory_rendered_input"] for row in values}) == 7500
    for split, per_label in (("train", 240), ("dev", 30), ("test", 30)):
        selected = [row for row in values if row["split"] == split]
        assert Counter(row["label"] for row in selected) == Counter({label: per_label for label in NETWORK_EXACT_TOOL_LABELS})
        expected_language = {"en": 160, "zh": 80} if split == "train" else {"en": 15, "zh": 15}
        expected_phase = (
            {"first": 120, "continuation_1": 96, "continuation_2": 24}
            if split == "train"
            else {"first": 14, "continuation_1": 12, "continuation_2": 4}
        )
        for label in NETWORK_EXACT_TOOL_LABELS:
            class_rows = [row for row in selected if row["label"] == label]
            assert Counter(row["language"] for row in class_rows) == expected_language
            assert Counter(row["phase"] for row in class_rows) == expected_phase

    for field in ("semantic_family_id", "lexical_family_id", "entity_family_id"):
        by_split = {split: {row[field] for row in values if row["split"] == split} for split in ("train", "dev", "test")}
        assert not by_split["train"] & by_split["dev"]
        assert not by_split["train"] & by_split["test"]
        assert not by_split["dev"] & by_split["test"]
    for label in NETWORK_EXACT_TOOL_LABELS:
        variants = {
            int(row["source"]["variant"])
            for row in values
            if row["split"] == "train" and row["language"] == "en" and row["label"] == label
        }
        assert variants == set(range(6))


def test_s28_every_row_replays_the_exact_compact_current_harness_protocol() -> None:
    for row in rows():
        current = dict(row["selector_input"])
        depth = int(row["decision_index"])
        history_steps = list(row["history_steps"])
        history_inputs = list(row["history_selector_inputs"])
        assert len(history_steps) == len(history_inputs) == len(row["expected_history_labels"]) == depth
        assert row["request_identifiable"] is True
        assert row["persistent_history_replay_required"] is bool(depth)
        assert row["compact_input_schema_version"] == COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
        assert row["compact_menu_digest"] == compact_selector_menu_digest()
        assert row["bootstrap"] == render_compact_selector_bootstrap(current)
        assert row["step"] == render_compact_selector_step(current)
        assert history_steps == [render_compact_selector_step(item) for item in history_inputs]
        expected = row["bootstrap"] + "".join("\n" + item for item in [*history_steps, row["step"]])
        assert row["trajectory_rendered_input"] == expected
        assert row["trajectory_rendered_input_sha256"] == hashlib.sha256(expected.encode("utf-8")).hexdigest()
        assert current["stage_objective"].startswith("CurrentDirectStageV1: ")
        assert current["stage_role"] == "work"
        assert current["progress"]["action_index"] == depth
        assert current["progress"]["completed_stage_count"] == depth
        assert row["generated_rwkv_text"] is False
        assert row["contains_parameter_schemas"] is False
        assert row["contains_full_tool_results"] is False
        assert row["contains_executor_text"] is False
