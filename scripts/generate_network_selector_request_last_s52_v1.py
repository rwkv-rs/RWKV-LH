#!/usr/bin/env python3
"""Derive the paired S52 request-last dataset from frozen S51 rows."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter
from pathlib import Path

from rwkv_lh.exact_tool_selector.compact_protocol_v4 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


ROOT = Path("/home/chase/GitHub/RWKV-LH")
EXPERIMENT = (
    ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
)
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_natural_harness_s51_v1"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_request_last_s52_v1"
PREREGISTRATION = (
    EXPERIMENT / "SEL_2P9_S52_REQUEST_LAST_PAIRED_ABLATION_PREREGISTRATION.md"
)

SOURCE_CASES_SHA256 = "da7d280db64728b1b77f2db24cd0ae86b2735f3e130d0e6597897bffcaec242f"
SOURCE_MANIFEST_SHA256 = "7b9ac06887d942ed10e98d8825648160ce970a7257fdf1d05acaa07df4f2aacb"
PREREGISTRATION_SHA256 = "6523bb20b9934ef1f8e7ec04bc9df78b1ea871f4ed334ee00cf22d70f783d4a6"
EXPECTED_PREFIXES = {"train": 1615, "dev": 399, "test": 407}
EXPECTED_TRAJECTORIES = {"train": 423, "dev": 105, "test": 106}
EXPECTED_ROWS = 2421
EXPECTED_TRAJECTORY_ROWS = 634
VERSION = "rwkv-lh.network-selector.request-last-s52.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-request-last-prefix.s52.v1"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selector_input(value: dict[str, object]) -> NetworkSelectorInput:
    progress = dict(value["progress"])
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


def paired_id(value: object) -> str:
    text = str(value)
    if not text.startswith("S51-"):
        raise RuntimeError(f"unexpected S51 identity: {text}")
    return "S52-" + text.removeprefix("S51-")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S52 dataset")
    for path, expected in {
        SOURCE / "cases.jsonl": SOURCE_CASES_SHA256,
        SOURCE / "manifest.json": SOURCE_MANIFEST_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
    }.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S52 frozen source changed: {path}: {actual}")

    source_rows = [
        json.loads(line)
        for line in (SOURCE / "cases.jsonl").read_text(encoding="utf-8").splitlines()
    ]
    if len(source_rows) != EXPECTED_ROWS:
        raise RuntimeError("S52 source row count changed")

    rows: list[dict[str, object]] = []
    trajectory_count = 0
    prior_steps: list[str] = []
    previous_trajectory = ""
    bootstrap = ""
    for source in source_rows:
        trajectory_id = str(source["trajectory_id"])
        if trajectory_id != previous_trajectory:
            trajectory_count += 1
            previous_trajectory = trajectory_id
            prior_steps = []
            bootstrap = render_compact_selector_bootstrap(
                selector_input(dict(source["selector_input"]))
            )
        current = selector_input(dict(source["selector_input"]))
        current_bootstrap = render_compact_selector_bootstrap(current)
        if current_bootstrap != bootstrap:
            raise RuntimeError("S52 task bootstrap changed within a trajectory")
        step = render_compact_selector_step(current)
        step_payload = json.loads(step.removeprefix("SelectorStepV4: "))
        if list(step_payload)[-1] != "stage_objective":
            raise RuntimeError("S52 current question is not at the continuation tail")
        rendered = bootstrap + "".join(
            "\n" + item for item in [*prior_steps, step]
        )
        row = {
            **source,
            "schema_version": ROW_SCHEMA,
            "dataset_version": VERSION,
            "sample_id": paired_id(source["sample_id"]),
            "trajectory_id": paired_id(source["trajectory_id"]),
            "bootstrap": bootstrap,
            "step": step,
            "prior_steps": list(prior_steps),
            "rendered_input": rendered,
            "rendered_input_sha256": hashlib.sha256(
                rendered.encode("utf-8")
            ).hexdigest(),
            "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "compact_menu_digest": compact_selector_menu_digest(),
            "paired_source_sample_id": str(source["sample_id"]),
            "paired_source_rendered_input_sha256": str(
                source["rendered_input_sha256"]
            ),
            "request_last": True,
        }
        if row["selector_input"] != source["selector_input"]:
            raise RuntimeError("S52 changed the semantic Selector input")
        if row["selector_input_sha256"] != canonical_digest(source["selector_input"]):
            raise RuntimeError("S52 semantic Selector input digest changed")
        rows.append(row)
        prior_steps.append(step)

    if trajectory_count != EXPECTED_TRAJECTORY_ROWS:
        raise RuntimeError("S52 trajectory count changed")
    if Counter(str(row["split"]) for row in rows) != EXPECTED_PREFIXES:
        raise RuntimeError("S52 prefix split counts changed")
    trajectory_splits: Counter[str] = Counter()
    seen: set[str] = set()
    for row in rows:
        trajectory_id = str(row["trajectory_id"])
        if trajectory_id not in seen:
            seen.add(trajectory_id)
            trajectory_splits[str(row["split"])] += 1
    if trajectory_splits != EXPECTED_TRAJECTORIES:
        raise RuntimeError("S52 trajectory split counts changed")
    if len({str(row["sample_id"]) for row in rows}) != EXPECTED_ROWS:
        raise RuntimeError("S52 sample IDs are not unique")
    if len({str(row["rendered_input_sha256"]) for row in rows}) != EXPECTED_ROWS:
        raise RuntimeError("S52 rendered prefixes are not unique")

    paired_fields = (
        "selector_input",
        "selector_input_sha256",
        "label",
        "split",
        "language",
        "prefix_kind",
        "trajectory_position",
        "trajectory_length",
        "stage_group",
        "source_kind",
        "source_id",
        "generated_rwkv_text",
        "contains_parameter_schemas",
        "contains_full_tool_results",
        "contains_executor_text",
        "hidden_acceptance_used",
    )
    for source, row in zip(source_rows, rows, strict=True):
        if any(source[field] != row[field] for field in paired_fields):
            raise RuntimeError("S52 paired semantic field changed")

    staging = Path(tempfile.mkdtemp(prefix=".rwkv_lh_s52.", dir=OUTPUT.parent))
    cases_path = staging / "cases.jsonl"
    with cases_path.open("w", encoding="utf-8") as stream:
        for row in rows:
            stream.write(
                json.dumps(
                    row,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
                + "\n"
            )
    manifest = {
        "schema_version": "rwkv-lh.network-selector-request-last-dataset-manifest.s52.v1",
        "dataset_version": VERSION,
        "purpose": "paired request-last input-layout ablation for the independent 2.9B Selector",
        "rows": len(rows),
        "trajectories": trajectory_count,
        "split_prefix_counts": dict(sorted(Counter(str(row["split"]) for row in rows).items())),
        "split_trajectory_counts": dict(sorted(trajectory_splits.items())),
        "label_counts": {
            split: dict(
                sorted(
                    Counter(
                        str(row["label"])
                        for row in rows
                        if row["split"] == split
                    ).items()
                )
            )
            for split in ("train", "dev", "test")
        },
        "source": {
            "cases_path": str((SOURCE / "cases.jsonl").relative_to(ROOT)),
            "cases_sha256": SOURCE_CASES_SHA256,
            "manifest_path": str((SOURCE / "manifest.json").relative_to(ROOT)),
            "manifest_sha256": SOURCE_MANIFEST_SHA256,
        },
        "generation": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_file(Path(__file__).resolve()),
            "preregistration": str(PREREGISTRATION.relative_to(ROOT)),
            "preregistration_sha256": PREREGISTRATION_SHA256,
        },
        "contracts": {
            "paired_row_order": True,
            "paired_semantic_fields_byte_equal": True,
            "only_render_version_and_derived_identity_changed": True,
            "bootstrap_task_request_last": True,
            "step_stage_objective_last": True,
            "parameter_schemas_present": False,
            "tool_results_present": False,
            "executor_text_present": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        },
    }
    manifest_path = staging / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "README.md").write_text(
        "# S52 request-last paired Selector dataset\n\n"
        "This dataset changes only the frozen S51 rendering geometry and derived identities. "
        "Sources, counts, generation and hashes are recorded in `manifest.json`.\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s52_dataset_finalized",
                "rows": len(rows),
                "trajectories": trajectory_count,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
