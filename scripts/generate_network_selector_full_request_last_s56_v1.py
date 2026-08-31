#!/usr/bin/env python3
"""Re-render frozen Selector sources with the V5 full-request-last protocol."""

from __future__ import annotations

import hashlib
import json
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping

from rwkv_lh.exact_tool_selector.compact_protocol_v5 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
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
EXPERIMENT = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828"
PREREGISTRATION = EXPERIMENT / "SEL_2P9_S56_FULL_REQUEST_LAST_G4_R2_PREREGISTRATION.md"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_full_request_last_s56_v1"
PREREGISTRATION_SHA256 = "8c29c7de04e108e5630beab815df0437c8ac8b2ca256d0ddd2e1970b0cddf442"
RENDERER = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v5.py"
RENDERER_SHA256 = "3d19665e4a85d5296b336acf616a087f4d1e272aa8acebfc5855d7a02edab7bf"
DATASET_VERSION = "rwkv-lh.network-selector.full-request-last-s56.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-full-request-last-prefix.s56.v1"

SOURCES = {
    "s28": {
        "path": ROOT / "data/datasets/rwkv_lh_network_selector_compact_current_harness_s28_v1/cases.jsonl",
        "sha256": "a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922",
        "counts": {"train": 6000, "dev": 750, "test": 750},
    },
    "s39": {
        "path": ROOT / "data/datasets/rwkv_lh_network_selector_full_variant_matched_prefix_s39_v1/cases.jsonl",
        "sha256": "b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab",
        "counts": {"train": 3428, "dev": 857, "test": 857},
    },
    "s52": {
        "path": ROOT / "data/datasets/rwkv_lh_network_selector_request_last_s52_v1/cases.jsonl",
        "sha256": "1cb1a1b2597a16c63b92753e402529239d4a765698964e0102640bf70dab7faf",
        "counts": {"train": 1615, "dev": 399, "test": 407},
    },
    "s53": {
        "path": ROOT / "data/datasets/rwkv_lh_network_selector_multistage_s53_v1/cases.jsonl",
        "sha256": "bd3701c925717eb1d9f75d439c7fbb8b75a4905cc0099e348fa5314b98d1efde",
        "counts": {"train": 1300, "dev": 325, "test": 325},
    },
    "s55": {
        "path": ROOT / "data/datasets/rwkv_lh_network_selector_true_workflow_s55_v1/cases.jsonl",
        "sha256": "f183b5ef6389dd4549d245f05be2e9933f9b5efb8bbecaf23ae2184a75de02fe",
        "counts": {"train": 800, "dev": 240, "test": 240},
    },
}
EXPECTED_COUNTS = {"train": 13143, "dev": 2571, "test": 2579}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_row(value: Mapping[str, Any]) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("x", encoding="utf-8") as stream:
        for row in rows:
            stream.write(canonical_row(row) + "\n")


def progress(value: Mapping[str, Any]) -> NetworkSelectorProgress:
    return NetworkSelectorProgress(
        completed_stage_count=int(value.get("completed_stage_count", 0)),
        action_index=int(value.get("action_index", 0)),
        succeeded_operations=tuple(str(item) for item in value.get("succeeded_operations") or ()),
        failed_operations=tuple(str(item) for item in value.get("failed_operations") or ()),
        protocol_rejection_count=int(value.get("protocol_rejection_count", 0)),
    )


def selector_input(value: Mapping[str, Any], *, task_request: str | None = None) -> NetworkSelectorInput:
    progress_value = value.get("progress")
    if not isinstance(progress_value, Mapping):
        raise RuntimeError("source Selector progress is missing")
    request = str(task_request if task_request is not None else value.get("task_request") or "")
    return NetworkSelectorInput.create(
        task_request=request,
        stage_objective=str(value.get("stage_objective") or ""),
        stage_role=str(value.get("stage_role") or ""),
        progress=progress(progress_value),
    )


def parse_old_step(text: str, *, task_request: str) -> NetworkSelectorInput:
    marker = ": "
    if not text.startswith("SelectorStepV") or marker not in text:
        raise RuntimeError("source Selector step prefix changed")
    value = json.loads(text.split(marker, 1)[1])
    if not isinstance(value, Mapping):
        raise RuntimeError("source Selector step is not an object")
    return selector_input(value, task_request=task_request)


def history_inputs(row: Mapping[str, Any], *, task_request: str) -> list[NetworkSelectorInput]:
    raw_inputs = row.get("history_selector_inputs")
    if isinstance(raw_inputs, list):
        return [
            selector_input(value, task_request=task_request)
            for value in raw_inputs
            if isinstance(value, Mapping)
        ]
    raw_steps = row.get("prior_steps")
    if not isinstance(raw_steps, list):
        raise RuntimeError("source Selector history is missing")
    return [parse_old_step(str(value), task_request=task_request) for value in raw_steps]


def transform(source_id: str, source: Mapping[str, Any]) -> dict[str, Any]:
    raw_input = source.get("selector_input")
    if not isinstance(raw_input, Mapping):
        raise RuntimeError("source Selector input is missing")
    current = selector_input(raw_input)
    histories = history_inputs(source, task_request=current.task_request)
    bootstrap = render_compact_selector_bootstrap(current)
    prior_steps = [render_compact_selector_step(value) for value in histories]
    current_step = render_compact_selector_step(current)
    rendered = bootstrap + "".join("\n" + value for value in [*prior_steps, current_step])
    current_payload = json.loads(current_step.removeprefix("SelectorStepV5: "))
    if list(current_payload)[-1] != "current_requirement":
        raise RuntimeError("S56 current requirement is not last")
    if current_payload["current_requirement"] != current.task_request:
        raise RuntimeError("S56 current requirement changed")
    if not rendered.endswith(
        json.dumps(current.task_request, ensure_ascii=False) + "}"
    ):
        raise RuntimeError("S56 continuation edge changed")
    source_trajectory = str(source.get("trajectory_id") or source["sample_id"])
    source_position = int(
        source.get("trajectory_position")
        if source.get("trajectory_position") is not None
        else source.get("decision_index")
        or 0
    )
    sample_id = "S56-" + hashlib.sha256(
        f"{source_id}|{source['sample_id']}".encode("utf-8")
    ).hexdigest()[:24]
    return {
        "schema_version": ROW_SCHEMA,
        "dataset_version": DATASET_VERSION,
        "sample_id": sample_id,
        "source_dataset": source_id,
        "source_sample_id": str(source["sample_id"]),
        "source_trajectory_id": source_trajectory,
        "source_trajectory_position": source_position,
        "trajectory_id": f"S56-{source_id.upper()}-{source_trajectory}",
        "trajectory_position": source_position,
        "split": str(source["split"]),
        "language": str(source.get("language") or "unknown"),
        "prefix_kind": str(source.get("prefix_kind") or "independent-prefix"),
        "label": str(source["label"]),
        "bootstrap": bootstrap,
        "prior_steps": prior_steps,
        "step": current_step,
        "rendered_input": rendered,
        "rendered_input_sha256": hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
        "compact_input_schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
        "compact_menu_digest": compact_selector_menu_digest(),
        "bootstrap_payload": compact_selector_bootstrap_payload(current),
        "step_payload": compact_selector_step_payload(current),
        "input_digest": compact_selector_input_digest(current),
        "request_last": True,
        "current_requirement_is_full_task": True,
        "contains_parameter_schemas": False,
        "contains_full_tool_results": False,
        "contains_executor_text": False,
        "generated_rwkv_text": False,
        "hidden_acceptance_used": False,
    }


def validate_trajectory_prefixes(rows: list[dict[str, Any]]) -> None:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if row["source_dataset"] == "s28":
            continue
        grouped[(str(row["source_dataset"]), str(row["trajectory_id"]))].append(row)
    for identity, group in grouped.items():
        ordered = sorted(group, key=lambda value: int(value["trajectory_position"]))
        positions = [int(value["trajectory_position"]) for value in ordered]
        if positions != list(range(len(ordered))):
            raise RuntimeError(f"S56 source trajectory is incomplete: {identity}")
        for index, row in enumerate(ordered):
            if row["prior_steps"] != [value["step"] for value in ordered[:index]]:
                raise RuntimeError(f"S56 causal prefix changed: {identity}")


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S56 dataset")
    for path, expected in {
        PREREGISTRATION: PREREGISTRATION_SHA256,
        RENDERER: RENDERER_SHA256,
        **{value["path"]: value["sha256"] for value in SOURCES.values()},
    }.items():
        if sha256_file(Path(path)) != expected:
            raise RuntimeError(f"frozen S56 input changed: {path}")

    rows: list[dict[str, Any]] = []
    source_counts: dict[str, dict[str, int]] = {}
    for source_id, config in SOURCES.items():
        source_rows = [
            json.loads(line)
            for line in Path(config["path"]).read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        counts = dict(Counter(str(row["split"]) for row in source_rows))
        if counts != config["counts"]:
            raise RuntimeError(f"S56 frozen source count changed: {source_id}")
        source_counts[source_id] = counts
        rows.extend(transform(source_id, row) for row in source_rows)

    counts = dict(Counter(str(row["split"]) for row in rows))
    if counts != EXPECTED_COUNTS:
        raise RuntimeError(f"S56 aggregate counts changed: {counts}")
    if any(row["label"] not in NETWORK_EXACT_TOOL_LABELS for row in rows):
        raise RuntimeError("S56 label set changed")
    if len({str(row["sample_id"]) for row in rows}) != len(rows):
        raise RuntimeError("S56 sample identities are not unique")
    rendered_duplicates = len(rows) - len(
        {str(row["rendered_input_sha256"]) for row in rows}
    )
    if rendered_duplicates:
        raise RuntimeError(f"S56 rendered prompts are not unique: {rendered_duplicates}")
    validate_trajectory_prefixes(rows)

    staging = Path(tempfile.mkdtemp(prefix=f".{OUTPUT.name}.", dir=OUTPUT.parent))
    cases = staging / "cases.jsonl"
    write_jsonl(cases, rows)
    manifest = {
        "schema_version": "rwkv-lh.network-selector-full-request-last-manifest.s56.v1",
        "dataset_version": DATASET_VERSION,
        "purpose": "all retained Selector sources rendered with the complete requirement at every continuation edge",
        "counts": counts,
        "source_counts": source_counts,
        "label_counts": {
            split: dict(sorted(Counter(row["label"] for row in rows if row["split"] == split).items()))
            for split in ("train", "dev", "test")
        },
        "sources": {
            source_id: {
                "path": str(Path(config["path"]).relative_to(ROOT)),
                "sha256": config["sha256"],
            }
            for source_id, config in SOURCES.items()
        },
        "protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "renderer": str(RENDERER.relative_to(ROOT)),
            "renderer_sha256": RENDERER_SHA256,
            "complete_current_requirement_last": True,
            "repeated_at_every_causal_step": True,
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "validation": {
            "rendered_prompt_duplicates": 0,
            "labels_changed": False,
            "split_membership_changed": False,
            "parameter_schemas_present": False,
            "tool_result_bodies_present": False,
            "executor_text_present": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
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
        "# S56 full-request-last Selector prefixes\n",
        encoding="utf-8",
    )
    staging.rename(OUTPUT)
    print(
        json.dumps(
            {
                "event": "s56_full_request_last_dataset_finalized",
                "counts": counts,
                "cases_sha256": sha256_file(OUTPUT / "cases.jsonl"),
                "manifest_sha256": sha256_file(OUTPUT / "manifest.json"),
            },
            sort_keys=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
