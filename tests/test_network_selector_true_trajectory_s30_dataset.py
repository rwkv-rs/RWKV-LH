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
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1"
CASES_SHA256 = "5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305"


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return manifest, rows


def test_s30_manifest_freezes_sources_generator_and_balanced_splits() -> None:
    manifest, rows = load()
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {
        "rows": 3000,
        "sha256": CASES_SHA256,
    }
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest["generator"]["sha256"]
    assert sha256_file(ROOT / manifest["preregistration"]["path"]) == manifest["preregistration"]["sha256"]
    assert manifest["counts"] == {"train": 2000, "dev": 500, "test": 500}
    assert len(rows) == 3000
    for split, support in (("train", 80), ("dev", 20), ("test", 20)):
        selected = [row for row in rows if row["split"] == split]
        assert Counter(row["label"] for row in selected) == Counter(
            {label: support for label in NETWORK_EXACT_TOOL_LABELS}
        )
        for label in NETWORK_EXACT_TOOL_LABELS:
            assert Counter(
                row["language"] for row in selected if row["label"] == label
            ) == {"en": support // 2, "zh": support // 2}


def test_s30_replays_exact_production_shaped_compact_trajectories() -> None:
    manifest, rows = load()
    assert manifest["input_protocol"] == {
        "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "menu_digest": compact_selector_menu_digest(),
        "source_path": "rwkv_lh/exact_tool_selector/compact_protocol_v3.py",
        "source_sha256": "976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508",
        "names_and_descriptions_only": True,
    }
    for row in rows:
        current = row["selector_input"]
        histories = row["history_selector_inputs"]
        assert row["selector_input_sha256"] == canonical_digest(current)
        assert row["bootstrap"] == render_compact_selector_bootstrap(current)
        assert row["step"] == render_compact_selector_step(current)
        assert row["history_steps"] == [
            render_compact_selector_step(value) for value in histories
        ]
        assert len(histories) == row["decision_index"] == len(row["expected_history_labels"])
        expected_delta = row["expected_history_labels"][-1:]
        assert current["progress"]["succeeded_operations"] == expected_delta
        assert current["progress"]["failed_operations"] == []
        assert row["trajectory_rendered_input"] == row["bootstrap"] + "".join(
            "\n" + item for item in [*row["history_steps"], row["step"]]
        )
        assert row["compact_menu_digest"] == compact_selector_menu_digest()
        assert not row["generated_rwkv_text"]
        assert not row["contains_parameter_schemas"]
        assert not row["contains_full_tool_results"]
        assert not row["contains_executor_text"]


def test_s30_contains_future_tool_negatives_and_unhinted_completion() -> None:
    manifest, rows = load()
    first_executable = [
        row
        for row in rows
        if row["stage_group"] == "first"
        and row["label"] not in {"final_answer", "ABSTAIN"}
    ]
    ratio = sum(bool(row["has_future_tool_distractor"]) for row in first_executable) / len(first_executable)
    assert ratio == manifest["first_noncontrol_future_tool_ratio"]
    assert ratio >= 0.5
    completions = [row for row in rows if row["label"] == "final_answer"]
    assert len(completions) == 120
    for row in completions:
        assert row["stage_group"] == "completion"
        assert row["completion_inferred"] is True
        assert row["decision_index"] in {1, 2}
        assert row["future_labels"] == []
        request = row["selector_input"]["task_request"].lower()
        assert all(
            marker not in request
            for marker in (
                "final_answer",
                "no tool",
                "no operation",
                "不再调用",
                "无需工具",
            )
        )


def test_s30_split_families_are_disjoint_and_ecra_is_similarity_only() -> None:
    manifest, rows = load()
    for field in (
        "semantic_family_id",
        "lexical_family_id",
        "entity_family_id",
        "trajectory_family_id",
    ):
        values = {
            split: {row[field] for row in rows if row["split"] == split}
            for split in ("train", "dev", "test")
        }
        assert not values["train"] & values["dev"]
        assert not values["train"] & values["test"]
        assert not values["dev"] & values["test"]
    ecra = manifest["sources"]["ecra120_similarity_audit_only"]
    assert ecra["labels_or_text_used_for_generation"] is False
    similarity = manifest["validation"]["holdout_similarity"]
    assert similarity["algorithm"] == "utf8-byte-5gram-cosine.v1"
    assert similarity["maximum"]["score"] < similarity["threshold_exclusive"] == 0.75
