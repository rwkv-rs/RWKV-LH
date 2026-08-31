from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_semantic_boundary_s68_v1"
FOCUS = {"append_file", "write_file", "replace_text", "copy_file", "move_file"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_s68_manifest_and_registered_files_are_exact() -> None:
    manifest_path = DATASET / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert _sha256(manifest_path) == "4a6e201e3d1dc6dff63f72660a08455ae619c1186b45c95c7f9d86ffc985ea0c"
    assert manifest["schema_version"] == "rwkv-lh.network-selector-semantic-boundary-manifest.s68.v1"
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert manifest["semantic_boundary"]["focus_labels"] == [
        "append_file",
        "write_file",
        "replace_text",
        "copy_file",
        "move_file",
    ]
    assert manifest["split_integrity"] == {
        "lexicon_pool_intersection_count": 0,
        "semantic_variant_intersection_count": 0,
        "exact_request_overlap": 0,
        "source_family_overlap": 0,
        "rendered_input_overlap": 0,
    }
    expected = {
        "cases.jsonl": "8b0f1a17f25863f448858d082c7b6cf7dec5cb76414f635f5f2ab8416566d218",
        "rwkv_state_tuning.train.requires_target_suffix.jsonl": "6b63300e379229540d23e968791db46ca1aaa83e203ff0e50dd0aaafe7cf852b",
        "rwkv_state_tuning.dev.requires_target_suffix.jsonl": "54b1c9bb987c8ca0b9ae1eed904937e619ab63c3d5763eab7cfdf83cf70da5dc",
    }
    for name, digest in expected.items():
        assert _sha256(DATASET / name) == digest
        assert manifest["files"][name]["sha256"] == digest


def test_s68_balances_all_labels_and_keeps_request_at_byte_tail() -> None:
    rows = _rows(DATASET / "cases.jsonl")
    assert len(rows) == 3000
    expected_per_label = {"train": 80, "dev": 20, "test": 20}
    expected_per_language = {"train": 1000, "dev": 250, "test": 250}
    counts: Counter[tuple[str, str]] = Counter()
    languages: Counter[tuple[str, str]] = Counter()
    requests: dict[str, set[str]] = defaultdict(set)
    rendered: dict[str, set[str]] = defaultdict(set)
    families: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        split = str(row["split"])
        label = str(row["label"])
        counts[(split, label)] += 1
        languages[(split, str(row["language"]))] += 1
        requests[split].add(str(row["task_request"]))
        rendered[split].add(str(row["rendered_input_sha256"]))
        families[split].add(str(row["source_family_id"]))
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
    for split, per_label in expected_per_label.items():
        assert {label for candidate_split, label in counts if candidate_split == split} == set(
            NETWORK_EXACT_TOOL_LABELS
        )
        assert all(counts[(split, label)] == per_label for label in NETWORK_EXACT_TOOL_LABELS)
        assert languages[(split, "en")] == expected_per_language[split]
        assert languages[(split, "zh")] == expected_per_language[split]
    for left, right in (("train", "dev"), ("train", "test"), ("dev", "test")):
        assert requests[left].isdisjoint(requests[right])
        assert rendered[left].isdisjoint(rendered[right])
        assert families[left].isdisjoint(families[right])


def test_s68_focus_variants_are_split_disjoint_and_frames_are_paired() -> None:
    rows = _rows(DATASET / "cases.jsonl")
    expected_variants = {
        "train": {0, 1, 2, 3, 4},
        "dev": {5, 6},
        "test": {7, 8},
    }
    variants: dict[tuple[str, str, str], set[int]] = defaultdict(set)
    frames: dict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        if not row["semantic_boundary_focus"]:
            continue
        split = str(row["split"])
        label = str(row["label"])
        variants[(split, label, str(row["language"]))].add(
            int(row["semantic_core_variant"])
        )
        frames[(split, str(row["contrastive_frame_id"]))].append(row)
    for split in ("train", "dev", "test"):
        for label in FOCUS:
            for language in ("en", "zh"):
                assert variants[(split, label, language)] == expected_variants[split]
    assert len(frames) == 80 + 20 + 20
    for members in frames.values():
        assert {str(row["label"]) for row in members} == FOCUS
        assert len({str(row["contrastive_context_sha256"]) for row in members}) == 1


def test_s68_state_exports_exclude_locked_test_and_preserve_suffix_contract() -> None:
    cases = {str(row["sample_id"]): row for row in _rows(DATASET / "cases.jsonl")}
    for split, expected in (("train", 2000), ("dev", 500)):
        rows = _rows(DATASET / f"rwkv_state_tuning.{split}.requires_target_suffix.jsonl")
        assert len(rows) == expected
        for row in rows:
            source = cases[str(row["source_sample_id"])]
            assert row["split"] == split == source["split"]
            assert row["schema_version"] == "rwkv-lh.network-selector-state-tuning-row.s68.v1"
            assert row["dataset_version"] == "rwkv-lh.network-selector-semantic-boundary-s68.v1"
            assert row["target"] == "\nSelectorLabelV7: " + source["label"]
            assert row["text"] == row["prompt"] + row["target"]
            assert row["loss_mask"] == "target_suffix"
            assert row["request_last"] is True
            assert row["generated_rwkv_text"] is False
            assert row["raw_rwkv_output_modified"] is False
    assert not (DATASET / "rwkv_state_tuning.test.requires_target_suffix.jsonl").exists()
