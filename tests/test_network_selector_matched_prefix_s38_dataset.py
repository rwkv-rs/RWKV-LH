from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


ROOT = Path(__file__).resolve().parents[1]
DATASET = ROOT / "data/datasets/rwkv_lh_network_selector_matched_prefix_s38_v1"
CASES_SHA256 = "a0f22a9e6889cf36450efb43de1611ac2a7156c742607ad099447c80dbbecdf7"
OPAQUE_ID = re.compile(r"^S38-[PT]-[0-9a-f]{24}$")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load() -> tuple[dict[str, object], list[dict[str, object]]]:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    rows = [
        json.loads(line)
        for line in (DATASET / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    return manifest, rows


def selector_input(value: dict[str, object]) -> NetworkSelectorInput:
    progress = value["progress"]
    assert isinstance(progress, dict)
    return NetworkSelectorInput.create(
        task_request=str(value["task_request"]),
        stage_objective=str(value["stage_objective"]),
        stage_role=str(value["stage_role"]),
        progress=NetworkSelectorProgress(
            completed_stage_count=int(progress["completed_stage_count"]),
            action_index=int(progress["action_index"]),
            succeeded_operations=tuple(progress["succeeded_operations"]),
            failed_operations=tuple(progress["failed_operations"]),
            protocol_rejection_count=int(progress["protocol_rejection_count"]),
        ),
    )


def test_s38_manifest_freezes_sources_generator_and_matched_counts() -> None:
    manifest, rows = load()
    assert sha256_file(DATASET / "cases.jsonl") == CASES_SHA256
    assert manifest["files"]["cases.jsonl"] == {
        "rows": 5142,
        "sha256": CASES_SHA256,
    }
    for source in manifest["sources"].values():
        assert sha256_file(ROOT / source["path"]) == source["sha256"]
    assert sha256_file(ROOT / manifest["generator"]["path"]) == manifest["generator"]["sha256"]
    assert sha256_file(ROOT / manifest["preregistration"]["path"]) == manifest["preregistration"]["sha256"]
    assert manifest["validation"]["trajectory_counts"] == {
        "train": 2000,
        "dev": 500,
        "test": 500,
    }
    assert manifest["validation"]["prefix_counts"] == {
        "train": 3428,
        "dev": 857,
        "test": 857,
    }
    assert manifest["validation"]["operation_source_split_overlap"] == 0
    assert manifest["validation"]["trajectory_split_overlap"] == 0
    assert len(rows) == 5142


def test_s38_has_exact_prefix_closure_and_v3_rendering() -> None:
    manifest, rows = load()
    assert manifest["input_protocol"]["menu_digest"] == compact_selector_menu_digest()
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        assert OPAQUE_ID.fullmatch(str(row["sample_id"]))
        assert OPAQUE_ID.fullmatch(str(row["trajectory_id"]))
        assert all(
            label.lower() not in str(row["sample_id"]).lower()
            and label.lower() not in str(row["trajectory_id"]).lower()
            for label in NETWORK_EXACT_TOOL_LABELS
        )
        value = selector_input(row["selector_input"])
        assert render_compact_selector_bootstrap(value) == row["bootstrap"]
        assert render_compact_selector_step(value) == row["step"]
        assert row["rendered_input"] == row["bootstrap"] + "".join(
            "\n" + item for item in [*row["prior_steps"], row["step"]]
        )
        assert not row["contains_parameter_schemas"]
        assert not row["contains_full_tool_results"]
        assert not row["contains_executor_text"]
        assert not row["generated_rwkv_text"]
        assert not row["sampling_invoked"]
        grouped[str(row["trajectory_id"])].append(row)
    assert len(grouped) == 3000
    for group in grouped.values():
        assert [row["trajectory_position"] for row in group] == list(range(len(group)))
        assert group[-1]["prefix_kind"] == "current"
        assert sum(row["prefix_kind"] == "current" for row in group) == 1


def test_s38_depth_multisets_match_dev_and_test_exactly() -> None:
    _manifest, rows = load()
    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["trajectory_id"])].append(row)
    current_rows = [group[-1] for group in grouped.values()]
    executable = set(NETWORK_EXACT_TOOL_LABELS) - {"final_answer", "ABSTAIN"}
    expected = {
        "train": Counter({0: 20, 1: 12, 2: 8}),
        "dev": Counter({0: 5, 1: 3, 2: 2}),
        "test": Counter({0: 5, 1: 3, 2: 2}),
    }
    for split in expected:
        for label in executable:
            for language in ("en", "zh"):
                assert Counter(
                    int(row["trajectory_length"]) - 1
                    for row in current_rows
                    if row["split"] == split
                    and row["label"] == label
                    and row["language"] == language
                ) == expected[split]
    for split in ("train", "dev", "test"):
        assert set(row["label"] for row in rows if row["split"] == split) == set(
            NETWORK_EXACT_TOOL_LABELS
        )
