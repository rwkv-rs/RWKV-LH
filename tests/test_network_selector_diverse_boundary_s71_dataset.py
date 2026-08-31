from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_EXACT_TOOL_LABELS


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_diverse_boundary_s71_v1"
SPLIT_PATTERN = re.compile(r'"split":"(train|dev|test)"')


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _visible_rows_without_opening_locked() -> tuple[list[dict[str, object]], int]:
    rows: list[dict[str, object]] = []
    skipped_test = 0
    with (DATASET / "cases.jsonl").open("r", encoding="utf-8") as stream:
        for line in stream:
            match = SPLIT_PATTERN.search(line)
            assert match is not None
            if match.group(1) == "test":
                skipped_test += 1
                continue
            rows.append(json.loads(line))
    return rows, skipped_test


def test_s71_manifest_and_registered_files_are_exact() -> None:
    manifest_path = DATASET / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert _sha256(manifest_path) == (
        "b01c739babbc6cfd3eb8a92b7dd6250504110df2e42f270ebdba7a7091bd82ca"
    )
    assert manifest["schema_version"] == (
        "rwkv-lh.network-selector-diverse-boundary-manifest.s71.v1"
    )
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert manifest["train_diversity"] == {
        "core_sources": [
            "s67-canonical-core-0",
            "s67-held-out-core-1",
            "s69-formal-core-0",
            "s69-formal-core-1",
        ],
        "rows_per_core_per_label_language": 10,
        "semantic_cores_per_label_language": 4,
        "total_rows": 2000,
    }
    assert manifest["visible_dev_reclassification"]["blind_or_locked"] is False
    assert manifest["visible_dev_reclassification"]["optimizer_use"] is False
    assert manifest["visible_dev_reclassification"][
        "s70_quarantined_test_rows_reclassified_and_json_parsed"
    ] == 500
    assert manifest["locked_test"] == {
        "opened_by_model_runner": False,
        "shared_contrastive_frames": 20,
        "source": "new S71 sealed relation/effect inventory",
        "test_rows_json_parsed_after_dataset_commit": 0,
        "variants_per_label_language": 2,
    }
    expected = {
        "cases.jsonl": "aaaaccfbd1bb5e7afe7bbcc64e0ea2b1283f1808413e93f497d90d1ed749088c",
        "rwkv_state_tuning.train.requires_target_suffix.jsonl": (
            "36c3faa290ab284734bb6c1bc7034431f683da3c147fd52fc63eb60c3241993f"
        ),
        "rwkv_state_tuning.dev.requires_target_suffix.jsonl": (
            "cdb72d7959cd6a569730cd0359a37b6119b03b64e056ed4f47589f9435bc4317"
        ),
    }
    for name, digest in expected.items():
        assert _sha256(DATASET / name) == digest
        assert manifest["files"][name]["sha256"] == digest


def test_s71_visible_splits_are_balanced_and_keep_requirement_at_byte_tail() -> None:
    rows, skipped_test = _visible_rows_without_opening_locked()
    assert len(rows) == 2500
    assert skipped_test == 500
    counts: Counter[tuple[str, str]] = Counter()
    languages: Counter[tuple[str, str]] = Counter()
    variants: dict[tuple[str, str, str], Counter[int]] = defaultdict(Counter)
    for row in rows:
        split = str(row["split"])
        label = str(row["label"])
        language = str(row["language"])
        counts[(split, label)] += 1
        languages[(split, language)] += 1
        variants[(split, label, language)][int(row["semantic_core_variant"])] += 1
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
    for label in NETWORK_EXACT_TOOL_LABELS:
        assert counts[("train", label)] == 80
        assert counts[("dev", label)] == 20
        for language in ("en", "zh"):
            assert variants[("train", label, language)] == Counter(
                {0: 10, 1: 10, 2: 10, 3: 10}
            )
            assert variants[("dev", label, language)] == Counter({0: 5, 1: 5})
    assert languages == Counter(
        {("train", "en"): 1000, ("train", "zh"): 1000, ("dev", "en"): 250, ("dev", "zh"): 250}
    )


def test_s71_holdout_and_train_dev_state_exports_are_frozen() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    holdout = manifest["holdout"]
    assert holdout["similarity_algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert holdout["threshold_exclusive"] == 0.95
    assert holdout["maximum_ladder_similarity"]["score"] < 0.95
    assert holdout["maximum_generated_s70_similarity"]["score"] < 0.95
    assert holdout["exact_generated_s70_request_overlap"] == 0
    cases = {
        str(row["sample_id"]): row
        for row in _visible_rows_without_opening_locked()[0]
    }
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
                "rwkv-lh.network-selector-state-tuning-row.s71.v1"
            )
            assert row["dataset_version"] == (
                "rwkv-lh.network-selector-diverse-boundary-s71.v1"
            )
            assert row["target"] == "\nSelectorLabelV7: " + str(source["label"])
            assert row["text"] == row["prompt"] + row["target"]
            assert row["loss_mask"] == "target_suffix"
            assert row["request_last"] is True
            assert row["generated_rwkv_text"] is False
            assert row["raw_rwkv_output_modified"] is False
    assert len(exported_ids) == 2500
    assert not (DATASET / "rwkv_state_tuning.test.requires_target_suffix.jsonl").exists()
