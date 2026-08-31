from __future__ import annotations

import hashlib
import json
from pathlib import Path

from rwkv_lh.exact_tool_selector.protocol import EXACT_TOOL_LABELS, selector_menu_digest
from scripts.build_exact_tool_selector_dataset_v1 import (
    DATASET_SCHEMA,
    DEDUP_THRESHOLD,
    ROOT,
    _deduplicate,
)

DATASET = ROOT / "data" / "datasets" / "rwkv_lh_exact_tool_selector_v1"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _synthetic_row(row_id: str, label: str) -> dict[str, object]:
    return {
        "row_id": row_id,
        "label": label,
        "selector_input": {
            "task_request": "Inspect the exact same task.",
            "stage_objective": "Use the next operation and then finish.",
            "stage_role": "work",
            "progress": {
                "completed_stage_count": 0,
                "action_index": 0,
                "succeeded_operations": [],
                "failed_operations": [],
                "protocol_rejection_count": 0,
            },
        },
    }


def test_dedup_is_class_conditional_and_retains_boundary_contrasts() -> None:
    rows = [
        _synthetic_row("A", "read_file"),
        _synthetic_row("B", "read_file"),
        _synthetic_row("C", "final_answer"),
    ]

    kept, duplicates, cross_label = _deduplicate(rows)

    assert [row["row_id"] for row in kept] == ["A", "C"]
    assert duplicates == [
        {
            "dropped_row_id": "B",
            "kept_row_id": "A",
            "dropped_label": "read_file",
            "kept_label": "read_file",
            "class_conditional": True,
            "similarity": 1.0,
            "algorithm": "utf8-byte-5gram-cosine.v1",
            "threshold": DEDUP_THRESHOLD,
        }
    ]
    assert len(cross_label) == 1
    assert cross_label[0]["row_id"] == "C"
    assert cross_label[0]["neighbor_row_id"] == "A"
    assert cross_label[0]["retained_as_causal_boundary_contrast"] is True


def test_candidate_dataset_is_auditable_and_fails_closed() -> None:
    manifest = json.loads((DATASET / "manifest.json").read_text(encoding="utf-8"))
    coverage = json.loads((DATASET / "coverage.json").read_text(encoding="utf-8"))
    sources = json.loads((DATASET / "sources.json").read_text(encoding="utf-8"))

    assert manifest["schema_version"] == DATASET_SCHEMA
    assert manifest["status"] == "candidate_unfrozen"
    assert manifest["training_authorized"] is False
    assert manifest["tool_menu_digest"] == selector_menu_digest()
    assert coverage["eligible_to_freeze"] is False
    assert coverage["formal_files_emitted"] is False
    assert not any(
        (DATASET / f"{split}.jsonl").exists() for split in ("train", "dev", "test")
    )
    assert set(coverage["all_counts"]) == set(EXACT_TOOL_LABELS)
    assert coverage["cross_label_near_neighbors_retained"] > 0
    assert {item["adapter"] for item in sources["source_roots"]} == {
        "atom_graph",
        "direct_action",
    }
    assert any(item["adapter"] == "direct_action" for item in sources["source_runs"])
    assert coverage["all_counts"]["run_command"] > 0

    for name, identity in manifest["files"].items():
        path = DATASET / name
        assert path.stat().st_size == identity["bytes"]
        assert _sha256(path) == identity["sha256"]


def test_candidate_rows_retain_raw_rwkv_bytes_and_family_split() -> None:
    family_splits: dict[str, str] = {}
    rows = [
        json.loads(line)
        for line in (DATASET / "candidates.unfrozen.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]

    assert rows
    trajectory_steps: dict[str, list[int]] = {}
    for row in rows:
        assert row["label"] in EXACT_TOOL_LABELS
        source = row["source"]
        raw_output = source["raw_output"]
        assert source["raw_output_modified"] is False
        assert (
            hashlib.sha256(raw_output.encode("utf-8")).hexdigest()
            == source["raw_output_sha256"]
        )
        rendered = row["selector_input_rendered"]
        assert rendered == (
            row["selector_bootstrap_rendered"] + "\n" + row["selector_step_rendered"]
        )
        assert '"parameters"' not in rendered
        assert '"arguments"' not in rendered
        assert '"result"' not in rendered
        family_id = row["family_id"]
        split = row["split"]
        assert family_splits.setdefault(family_id, split) == split
        trajectory_steps.setdefault(row["trajectory_id"], []).append(
            row["trajectory_step_index"]
        )
    assert all(steps == sorted(steps) for steps in trajectory_steps.values())


def test_direct_rows_are_single_raw_calls_without_semantic_synthesis() -> None:
    rows = [
        json.loads(line)
        for line in (DATASET / "candidates.unfrozen.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    direct_rows = [
        row
        for row in rows
        if row["source"]["label_evidence"]["kind"]
        in {
            "successful_direct_harness_action_in_accepted_run",
            "byte_exact_accepted_direct_final_boundary",
        }
    ]

    assert direct_rows
    for row in direct_rows:
        evidence = row["source"]["label_evidence"]
        assert evidence["single_rwkv_direct_action"] is True
        assert evidence["order_ensemble_used"] is False
        assert evidence["raw_generation_trace_joined"] is True
        if evidence["kind"] == "successful_direct_harness_action_in_accepted_run":
            assert evidence["controller_semantic_fields_generated"] is False
