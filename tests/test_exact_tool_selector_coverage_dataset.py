from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.protocol import (
    ABSTAIN_LABEL,
    EXACT_TOOL_LABELS,
    selector_menu_digest,
)
from rwkv_lh.harness import ActionHarness
from rwkv_lh.schema import TaskAction

ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_exact_tool_coverage_v1"
CASES = DATASET / "cases.jsonl"
PREFLIGHT = DATASET / "preflight.jsonl"
MANIFEST = DATASET / "manifest.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _split_for_family(family_id: str) -> str:
    bucket = int(hashlib.sha256(family_id.encode()).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "dev"
    if bucket == 1:
        return "test"
    return "train"


def _rows() -> list[dict[str, object]]:
    return [json.loads(line) for line in CASES.read_text(encoding="utf-8").splitlines()]


def test_coverage_plan_manifest_hashes_and_fixed_counts() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = _rows()

    assert manifest["artifact_kind"] == "frozen_collection_plan_not_training_data"
    assert manifest["tool_menu_digest"] == selector_menu_digest()
    assert manifest["class_order"] == list(EXACT_TOOL_LABELS)
    assert manifest["files"]["cases.jsonl"]["sha256"] == _sha256(CASES)
    assert manifest["files"]["preflight.jsonl"]["sha256"] == _sha256(PREFLIGHT)
    assert manifest["files"]["README.md"]["sha256"] == _sha256(DATASET / "README.md")
    assert manifest["generator"]["sha256"] == _sha256(
        ROOT / manifest["generator"]["path"]
    )
    assert manifest["protocol"]["sha256"] == _sha256(
        ROOT / manifest["protocol"]["path"]
    )

    assert len(rows) == 6000
    assert manifest["counts"]["total"] == 6000
    assert manifest["counts"]["semantic_families"] == 6000
    assert manifest["counts"]["by_split"] == {
        "train": 4800,
        "dev": 600,
        "test": 600,
    }
    expected_label_split = {"train": 240, "dev": 30, "test": 30}
    assert manifest["counts"]["by_label"] == {label: 300 for label in EXACT_TOOL_LABELS}
    assert manifest["counts"]["by_label_and_split"] == {
        label: expected_label_split for label in EXACT_TOOL_LABELS
    }
    assert manifest["counts"]["preflight_total"] == 40
    assert manifest["counts"]["preflight_by_label"] == {
        label: 2 for label in EXACT_TOOL_LABELS
    }

    similarity = manifest["validation"]["similarity_audit"]
    assert similarity["algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert similarity["threshold"] == 0.95
    assert similarity["input"] == similarity["kept"] == 6000
    assert similarity["dropped"] == 0
    assert similarity["maximum_compared_similarity"] < 0.95
    assert all(item["dropped"] == 0 for item in similarity["by_label"].values())


def test_coverage_plan_is_schema_valid_isolated_and_contains_no_model_output() -> None:
    rows = _rows()
    harness = ActionHarness()
    case_ids: set[str] = set()
    family_ids: set[str] = set()
    projection_digests: set[str] = set()
    counts: Counter[tuple[str, str]] = Counter()
    abstain_rules: Counter[str] = Counter()
    validated_actions = 0

    for row in rows:
        label = str(row["label"])
        split = str(row["split"])
        family_id = str(row["semantic_family_id"])
        projection = row["selector_projection"]
        projection_digest = str(row["selector_projection_sha256"])

        assert row["schema_version"] == "rwkv-lh.exact-tool-coverage-case.v1"
        assert row["case_id"] not in case_ids
        assert family_id not in family_ids
        assert projection_digest not in projection_digests
        case_ids.add(str(row["case_id"]))
        family_ids.add(family_id)
        projection_digests.add(projection_digest)
        counts[(label, split)] += 1

        assert label in EXACT_TOOL_LABELS
        assert split == _split_for_family(family_id)
        assert set(projection) == {
            "task_request",
            "stage_objective",
            "stage_role",
            "progress",
        }
        rendered = _canonical(projection)
        assert hashlib.sha256(rendered.encode()).hexdigest() == projection_digest
        assert all(
            key not in rendered for key in ('"arguments"', '"parameters"', '"result"')
        )
        assert row["collection_status"] == "not_run"
        assert row["raw_rwkv_output_present"] is False

        workspace = row["workspace"]
        fixture_paths = [*workspace["directories"]]
        for item in workspace["files"]:
            raw = item["content_utf8"].encode()
            assert item["bytes"] == len(raw)
            assert item["sha256"] == hashlib.sha256(raw).hexdigest()
            fixture_paths.append(item["path"])
        for value in fixture_paths:
            path = Path(value)
            assert not path.is_absolute()
            assert ".." not in path.parts

        execution = row["executor_contract"]
        if label == ABSTAIN_LABEL:
            assert execution is None
            assert row["verifier"]["raw_output_applicable"] is False
            abstain_rules[str(row["verifier"]["rule_id"])] += 1
            continue
        if label == "final_answer":
            assert execution == {"operation": "final_answer"}
            continue

        assert execution["operation"] == label
        action = TaskAction(label, execution["expected_arguments"])
        normalized = harness.normalize_action(action)
        assert normalized.action_type == label
        validated_actions += 1
        for name in ("path", "source", "destination", "cwd"):
            if name in normalized.arguments:
                path = Path(normalized.arguments[name])
                assert not path.is_absolute()
                assert ".." not in path.parts

    assert len(case_ids) == len(family_ids) == len(projection_digests) == 6000
    assert counts == Counter(
        {
            (label, split): expected
            for label in EXACT_TOOL_LABELS
            for split, expected in (("train", 240), ("dev", 30), ("test", 30))
        }
    )
    assert validated_actions == 5400
    assert abstain_rules == Counter(
        {
            "unsupported_capability": 60,
            "ambiguous_target": 60,
            "unsafe_unscoped_mutation": 60,
            "missing_observable_reference": 60,
            "irreconcilable_effects": 60,
        }
    )


def test_preflight_families_are_separate_from_formal_collection() -> None:
    formal = _rows()
    preflight = [
        json.loads(line) for line in PREFLIGHT.read_text(encoding="utf-8").splitlines()
    ]
    assert len(preflight) == 40
    assert {str(row["semantic_family_id"]) for row in formal}.isdisjoint(
        str(row["semantic_family_id"]) for row in preflight
    )
    assert Counter(str(row["label"]) for row in preflight) == Counter(
        {label: 2 for label in EXACT_TOOL_LABELS}
    )
    assert all(row["split"] == "preflight" for row in preflight)
    assert all(row["collection_status"] == "not_run" for row in preflight)
    assert all(row["raw_rwkv_output_present"] is False for row in preflight)
