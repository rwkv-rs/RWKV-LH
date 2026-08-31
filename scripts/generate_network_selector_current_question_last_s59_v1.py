#!/usr/bin/env python3
"""Re-render identifiable S58 rows with V6 current-question-last inputs."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.exact_tool_selector.compact_protocol_v6 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    SELECTOR_CURRENT_QUESTION,
    compact_selector_bootstrap_payload,
    compact_selector_input_digest,
    compact_selector_menu_digest,
    compact_selector_step_payload,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_identifiable_s58_v1/cases.jsonl"
SOURCE_MANIFEST = SOURCE.with_name("manifest.json")
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S59_CURRENT_QUESTION_LAST_PREREGISTRATION.md"
RENDERER = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v6.py"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_current_question_last_s59_v1"

SOURCE_SHA256 = "d49f938eb67858f3f17cf7e47672f5ec1b1d01918bd6e0b48e3dd1212399ebf0"
SOURCE_MANIFEST_SHA256 = "681d6cf2e5cf1a017933912bb0b92ee8aa77bda445d3ec0a78880a6f4be4fa4f"
PREREGISTRATION_SHA256 = "b0cfc8bc2bae612103c2b2233a05b9b0c907e5cbefc2adcc53460a13a08ce00b"
RENDERER_SHA256 = "a54ee775e3cea4c4614911ca042a804a7c2f896ccba7fc9d2ed40255cc45f4c4"
EXPECTED_COUNTS = {"train": 13143, "dev": 2571, "test": 2579}
DATASET_VERSION = "rwkv-lh.network-selector.current-question-last-s59.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-current-question-last-prefix.s59.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_row(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def parse_v5_step(text: str) -> NetworkSelectorInput:
    prefix = "SelectorStepV5: "
    if not text.startswith(prefix):
        raise RuntimeError("S59 source step is not frozen V5")
    payload = json.loads(text.removeprefix(prefix))
    if list(payload)[-1] != "current_requirement":
        raise RuntimeError("S59 source current requirement is not last")
    progress = payload.get("progress")
    if not isinstance(progress, Mapping):
        raise RuntimeError("S59 source progress is missing")
    return NetworkSelectorInput.create(
        task_request=str(payload.get("current_requirement") or ""),
        stage_objective=str(payload.get("stage_objective") or ""),
        stage_role=str(payload.get("stage_role") or ""),
        progress=NetworkSelectorProgress(
            completed_stage_count=int(progress.get("completed_stage_count", 0)),
            action_index=int(progress.get("action_index", 0)),
            succeeded_operations=tuple(
                str(item) for item in progress.get("succeeded_operations") or ()
            ),
            failed_operations=tuple(
                str(item) for item in progress.get("failed_operations") or ()
            ),
            protocol_rejection_count=int(progress.get("protocol_rejection_count", 0)),
        ),
    )


def transform(source: Mapping[str, Any]) -> dict[str, Any]:
    current = parse_v5_step(str(source["step"]))
    histories = [parse_v5_step(str(item)) for item in source["prior_steps"]]
    if any(value.task_request != current.task_request for value in histories):
        raise RuntimeError("S59 source trajectory changed immutable request")
    bootstrap = render_compact_selector_bootstrap(current)
    prior_steps = [render_compact_selector_step(value) for value in histories]
    step = render_compact_selector_step(current)
    rendered = bootstrap + "".join("\n" + item for item in [*prior_steps, step])
    step_payload = json.loads(step.removeprefix("SelectorStepV6: "))
    question = step_payload.get("current_question")
    if not (
        list(step_payload)[-1] == "current_question"
        and isinstance(question, dict)
        and list(question)[-1] == "question"
        and question.get("complete_requirement") == current.task_request
        and question.get("current_stage") == current.stage_objective
        and question.get("question") == SELECTOR_CURRENT_QUESTION
    ):
        raise RuntimeError("S59 current question is not complete and final")
    if not rendered.endswith(json.dumps(SELECTOR_CURRENT_QUESTION) + "}}"):
        raise RuntimeError("S59 continuation edge changed")
    source_id = str(source["sample_id"])
    sample_id = "S59-" + hashlib.sha256(source_id.encode("utf-8")).hexdigest()[:24]
    source_trajectory = str(source["trajectory_id"])
    return {
        **{
            key: source[key]
            for key in (
                "source_dataset",
                "language",
                "prefix_kind",
                "label",
                "source_label",
                "source_family",
                "label_corrected",
                "label_policy",
                "label_correction_reason",
            )
        },
        "schema_version": ROW_SCHEMA,
        "dataset_version": DATASET_VERSION,
        "sample_id": sample_id,
        "source_sample_id": source_id,
        "source_s58_source_sample_id": str(source["source_sample_id"]),
        "source_trajectory_id": source_trajectory,
        "source_trajectory_position": int(source["trajectory_position"]),
        "trajectory_id": "S59-" + source_trajectory,
        "trajectory_position": int(source["trajectory_position"]),
        "split": str(source["split"]),
        "bootstrap": bootstrap,
        "prior_steps": prior_steps,
        "step": step,
        "rendered_input": rendered,
        "rendered_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "bootstrap_payload": compact_selector_bootstrap_payload(current),
        "step_payload": compact_selector_step_payload(current),
        "input_digest": compact_selector_input_digest(current),
        "complete_current_question_last": True,
        "current_requirement_is_full_task": True,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "generated_rwkv_text": False,
        "hidden_acceptance_used": False,
    }


def validate_trajectories(rows: list[dict[str, Any]]) -> None:
    groups: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["source_dataset"] == "s28":
            continue
        groups[(str(row["source_dataset"]), str(row["trajectory_id"]))].append(row)
    for identity, group in groups.items():
        ordered = sorted(group, key=lambda value: int(value["trajectory_position"]))
        if [int(value["trajectory_position"]) for value in ordered] != list(
            range(len(ordered))
        ):
            raise RuntimeError(f"S59 trajectory is incomplete: {identity}")
        for index, row in enumerate(ordered):
            if row["prior_steps"] != [value["step"] for value in ordered[:index]]:
                raise RuntimeError(f"S59 causal prefix changed: {identity}")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S59 dataset")
    for path, expected in {
        SOURCE: SOURCE_SHA256,
        SOURCE_MANIFEST: SOURCE_MANIFEST_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
        RENDERER: RENDERER_SHA256,
    }.items():
        if not path.is_file() or sha256_file(path) != expected:
            raise RuntimeError(f"S59 frozen input changed: {path}")
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
        if line
    ]
    rows = [transform(row) for row in source_rows]
    counts = dict(Counter(str(row["split"]) for row in rows))
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"S59 split counts changed: {counts}")
    if any(row["label"] not in NETWORK_EXACT_TOOL_LABELS for row in rows):
        raise RuntimeError("S59 label set changed")
    if any(row["label"] != source["label"] for row, source in zip(rows, source_rows, strict=True)):
        raise RuntimeError("S59 changed a label")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("S59 sample ids are not unique")
    if len({str(row["rendered_input_sha256"]) for row in rows}) != len(rows):
        raise RuntimeError("S59 rendered prompts are not unique")
    validate_trajectories(rows)

    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    with cases.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_row(row) + "\n")
    manifest = {
        "schema_version": "rwkv-lh.network-selector-current-question-last-manifest.s59.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "complete task, current stage, and explicit decision question adjacent to the continuation edge",
        "counts": counts,
        "source_counts": {
            source: {
                split: sum(
                    row["source_dataset"] == source and row["split"] == split
                    for row in rows
                )
                for split in ("train", "dev", "test")
            }
            for source in ("s28", "s39", "s52", "s53", "s55")
        },
        "label_counts": {
            split: dict(
                sorted(Counter(row["label"] for row in rows if row["split"] == split).items())
            )
            for split in ("train", "dev", "test")
        },
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "manifest_sha256": SOURCE_MANIFEST_SHA256,
            "labels_changed": False,
            "split_membership_changed": False,
        },
        "protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "renderer": str(RENDERER.relative_to(ROOT)),
            "renderer_sha256": RENDERER_SHA256,
            "complete_task_near_tail": True,
            "current_stage_near_tail": True,
            "explicit_current_question_final": True,
            "repeated_at_every_causal_step": True,
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "validation": {
            "rendered_prompt_duplicates": 0,
            "parameter_schemas_present": False,
            "tool_result_bodies_present": False,
            "executor_text_present": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
            "raw_rwkv_output_modified": False,
        },
        "files": {
            "cases.jsonl": {
                "rows": len(rows),
                "bytes": cases.stat().st_size,
                "sha256": sha256_file(cases),
            }
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
    }
    (staging / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S59 current-question-last Selector prefixes\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s59_dataset_complete",
                "counts": counts,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
