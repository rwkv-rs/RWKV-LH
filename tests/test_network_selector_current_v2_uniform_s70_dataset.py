from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = (
    ROOT / "data/datasets/rwkv_lh_network_selector_current_v2_uniform_s70_v1"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_s70_manifest_and_registered_files_are_exact() -> None:
    manifest_path = DATASET / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert _sha256(manifest_path) == (
        "34584d0c755f40e4c8cc286d907eca8d840f5f9bc84614d1d2dcac019aac5f21"
    )
    assert manifest["schema_version"] == (
        "rwkv-lh.network-selector-current-v2-uniform-manifest.s70.v1"
    )
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert manifest["architecture"] == {
        "compact_schema_version": (
            "rwkv-lh.exact-tool-selector-input.v7-requirement-byte-tail"
        ),
        "contract_projection_version": "rwkv-lh.current-direct-selector-stage.v2",
        "legacy_v1_rows": 0,
        "literal_requirement_byte_tail": True,
        "persistent_history_replayed": True,
        "s65_training_rows": 0,
        "s69_failure_record": (
            "data/experiments/NETWORK_SELECTOR_UNIFORM_SEMANTIC_S69_V1_20260831/"
            "GENERATION_ATTEMPT_1.md"
        ),
        "s69_failure_record_sha256": (
            "da08aeadbd30bc63ee5e7e4f1d262f7f4e1b769bd26f81dcc529c97e968f8f05"
        ),
        "single_responsibility_current_v2_only": True,
    }
    assert manifest["split_integrity"] == {
        "exact_request_overlap": 0,
        "rendered_input_overlap": 0,
        "root_pool_intersection_count": 0,
        "source_family_overlap": 0,
    }
    expected = {
        "cases.jsonl": (
            "2895e10545ab4a1c98e4746b38a135167a1794c9dcfdb804ffd61358ea8d4f98"
        ),
        "rwkv_state_tuning.train.requires_target_suffix.jsonl": (
            "90b117f82e42bfdfb16eed8030d2d77dab6f5f570a523f99a0e57377a71d721f"
        ),
        "rwkv_state_tuning.dev.requires_target_suffix.jsonl": (
            "feb3b1b6c26f580e64e823eb9d3e93903cb8eca94f9133a67a42b7ca0f4cf868"
        ),
    }
    for name, digest in expected.items():
        assert _sha256(DATASET / name) == digest
        assert manifest["files"][name]["sha256"] == digest


def test_s70_balances_current_v2_rows_and_preserves_request_byte_tail() -> None:
    rows = _rows(DATASET / "cases.jsonl")
    assert len(rows) == 3000
    per_label = {"train": 80, "dev": 20, "test": 20}
    per_language = {"train": 1000, "dev": 250, "test": 250}
    counts: Counter[tuple[str, str]] = Counter()
    languages: Counter[tuple[str, str]] = Counter()
    values: dict[str, dict[str, set[str]]] = {
        key: defaultdict(set)
        for key in ("task_request", "source_family_id", "rendered_input_sha256")
    }
    for row in rows:
        split = str(row["split"])
        label = str(row["label"])
        counts[(split, label)] += 1
        languages[(split, str(row["language"]))] += 1
        for key in values:
            values[key][split].add(str(row[key]))
        assert str(row["stage_objective"]).startswith("CurrentDirectStageV2: ")
        assert row["current_requirement_is_atom_objective"] is True
        assert row["complete_requirement_byte_tail"] is True
        assert row["contains_parameter_schemas"] is False
        assert row["contains_full_tool_results"] is False
        assert row["contains_executor_text"] is False
        assert row["contains_planner_raw_json"] is False
        assert row["generated_rwkv_text"] is False
        step = json.loads(str(row["rendered_input"]).rsplit("\nSelectorStepV7: ", 1)[1])
        question = step["current_question"]
        assert list(step)[-1] == "current_question"
        assert list(question) == ["question", "current_stage", "complete_requirement"]
        assert question["complete_requirement"] == row["task_request"]
        expected_tail = json.dumps(
            row["task_request"], ensure_ascii=False, separators=(",", ":")
        ) + "}}"
        assert str(row["rendered_input"]).endswith(expected_tail)
    for split in ("train", "dev", "test"):
        assert all(
            counts[(split, label)] == per_label[split]
            for label in NETWORK_EXACT_TOOL_LABELS
        )
        assert languages[(split, "en")] == per_language[split]
        assert languages[(split, "zh")] == per_language[split]
    for left, right in (("train", "dev"), ("train", "test"), ("dev", "test")):
        for key in values:
            assert values[key][left].isdisjoint(values[key][right])


def test_s70_semantic_sources_and_locked_frames_are_uniform() -> None:
    rows = _rows(DATASET / "cases.jsonl")
    expected_sources = {
        "train": Counter(
            {"s67-current-train": 40, "s69-unused-formal-train": 40}
        ),
        "dev": Counter({"s67-current-dev": 10, "s69-unused-formal-dev": 10}),
        "test": Counter({"s70-locked-effect-postcondition": 20}),
    }
    for split in ("train", "dev", "test"):
        for label in NETWORK_EXACT_TOOL_LABELS:
            selected = [
                row for row in rows if row["split"] == split and row["label"] == label
            ]
            assert Counter(str(row["semantic_source"]) for row in selected) == (
                expected_sources[split]
            )
            if split == "test":
                for language in ("en", "zh"):
                    assert {
                        int(row["semantic_core_variant"])
                        for row in selected
                        if row["language"] == language
                    } == {0, 1}
    frames: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if row["split"] == "test":
            frames[str(row["contrastive_frame_id"])].append(row)
    assert len(frames) == 20
    for members in frames.values():
        assert {str(row["label"]) for row in members} == set(
            NETWORK_EXACT_TOOL_LABELS
        )
        assert len({str(row["contrastive_context_sha256"]) for row in members}) == 1


def test_s70_holdout_and_state_export_contracts_are_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    holdout = manifest["holdout"]
    assert holdout["similarity_algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert holdout["threshold_exclusive"] == 0.95
    assert holdout["maximum_ladder_similarity"]["score"] < 0.95
    assert holdout["maximum_s68_locked_similarity"]["score"] < 0.95
    assert holdout["exact_s68_locked_request_overlap"] == 0
    assert holdout["s68_test_rows_json_parsed_for_similarity_only"] == 500
    assert holdout["s68_test_labels_accessed"] == 0
    assert holdout["s68_test_requests_persisted"] == 0
    cases = {str(row["sample_id"]): row for row in _rows(DATASET / "cases.jsonl")}
    exported_ids: set[str] = set()
    for split, expected in (("train", 2000), ("dev", 500)):
        state_rows = _rows(
            DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl"
        )
        assert len(state_rows) == expected
        for row in state_rows:
            source = cases[str(row["source_sample_id"])]
            exported_ids.add(str(row["source_sample_id"]))
            assert row["split"] == split == source["split"]
            assert row["schema_version"] == (
                "rwkv-lh.network-selector-state-tuning-row.s70.v1"
            )
            assert row["dataset_version"] == (
                "rwkv-lh.network-selector-current-v2-uniform-s70.v1"
            )
            assert row["target"] == "\nSelectorLabelV7: " + str(source["label"])
            assert row["text"] == row["prompt"] + row["target"]
            assert row["loss_mask"] == "target_suffix"
            assert row["request_last"] is True
            assert row["generated_rwkv_text"] is False
            assert row["raw_rwkv_output_modified"] is False
    assert all(cases[sample_id]["split"] != "test" for sample_id in exported_ids)
    assert not (DATASET / "rwkv_state_tuning.test.requires_target_suffix.jsonl").exists()
