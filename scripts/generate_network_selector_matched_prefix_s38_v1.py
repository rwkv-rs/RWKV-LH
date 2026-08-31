#!/usr/bin/env python3
"""Generate the S38 source-separated, depth-matched prefix dataset."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from types import ModuleType
from typing import Any

from rwkv_lh.exact_tool_selector.compact_protocol_v3 import (
    COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
    compact_selector_menu_digest,
    render_compact_selector_bootstrap,
    render_compact_selector_step,
)
from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_EXACT_TOOL_LABELS,
    NetworkSelectorInput,
    NetworkSelectorProgress,
)
from rwkv_lh.exact_tool_selector.protocol import canonical_digest


ROOT = Path("/home/chase/GitHub/RWKV-LH")
SOURCE = ROOT / "data/datasets/rwkv_lh_network_exact_tool_selector_v2_4/cases.jsonl"
BASE_GENERATOR = ROOT / "scripts/generate_network_selector_true_trajectory_s30_v1.py"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S38_MATCHED_PREFIX_DATA_HEAD_PREREGISTRATION.md"
PROTOCOL = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v3.py"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_matched_prefix_s38_v1"

SOURCE_SHA256 = "78c90285defed1925691dc45325ea4380093345c39763c3bb32373e23733e9fc"
BASE_GENERATOR_SHA256 = "ab4d7c821e347fc7955945355b4b03fc1a0be8fffb4bc00caf5f261815672d21"
PREREGISTRATION_SHA256 = "d5198ab51c77372909a87afce092909568ba1dec91a15eb815b0bacfc8cad8ce"
PROTOCOL_SHA256 = "2d5668e9a7c4590670bcb9af4ed93df74e97de8bc49d0980db2e0f7479f62a6b"
VERSION = "rwkv-lh.network-selector.matched-prefix-s38.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-matched-prefix-row.s38.v1"
EXPECTED_TRAJECTORIES = {"train": 2000, "dev": 500, "test": 500}
EXPECTED_PREFIXES = {"train": 3428, "dev": 857, "test": 857}
EXPECTED_SOURCE_PER_LABEL = {"train": 240, "dev": 30, "test": 30}
OPAQUE_ID = re.compile(r"^S38-[PT]-[0-9a-f]{24}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_base() -> ModuleType:
    if sha256_file(BASE_GENERATOR) != BASE_GENERATOR_SHA256:
        raise RuntimeError("S38 frozen S30 builder identity changed")
    spec = importlib.util.spec_from_file_location(
        "rwkv_lh_s38_frozen_s30_builder", BASE_GENERATOR
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("unable to load frozen S30 trajectory builder")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def opaque_id(kind: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(["S38", kind, *(str(part) for part in parts)]).encode("utf-8")
    ).hexdigest()[:24]
    return f"S38-{kind}-{digest}"


def selector_input(value: dict[str, Any]) -> NetworkSelectorInput:
    progress = value["progress"]
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


def fixed_depth_assignment(base: ModuleType, split: str) -> list[int]:
    count = int(base.SPLIT_PER_LABEL[split]) // 2
    values = (
        [0] * 20 + [1] * 12 + [2] * 8
        if count == 40
        else [0] * 5 + [1] * 3 + [2] * 2
    )
    order = sorted(
        range(count),
        key=lambda index: base.stable_key(
            "S38-fixed-depth-order", split, index, values[index]
        ),
    )
    result = [0] * count
    for rank, sample_index in enumerate(order):
        result[sample_index] = values[rank]
    if Counter(result) != Counter(values):
        raise RuntimeError("S38 fixed depth multiset changed")
    return result


def make_trajectories(
    base: ModuleType,
    source_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, object]], dict[str, object]]:
    source_by_split_label = {
        split: {
            label: [
                row
                for row in source_rows
                if row["split"] == split and row["label"] == label
            ]
            for label in NETWORK_EXACT_TOOL_LABELS
        }
        for split in ("train", "dev", "test")
    }
    for split, by_label in source_by_split_label.items():
        expected = EXPECTED_SOURCE_PER_LABEL[split]
        if any(len(rows) != expected for rows in by_label.values()):
            raise RuntimeError(f"S38 {split} operation source balance changed")
    source_ids = {
        split: {
            str(row["sample_id"])
            for rows in source_by_split_label[split].values()
            for row in rows
        }
        for split in source_by_split_label
    }
    if (
        source_ids["train"] & source_ids["dev"]
        or source_ids["train"] & source_ids["test"]
        or source_ids["dev"] & source_ids["test"]
    ):
        raise RuntimeError("S38 operation source split overlap changed")

    assignments = {
        split: fixed_depth_assignment(base, split)
        for split in ("train", "dev", "test")
    }

    def corrected_depth_schedule(split: str, language_index: int) -> int:
        return assignments[split][language_index]

    base.depth_schedule = corrected_depth_schedule
    trajectories: list[dict[str, object]] = []
    source_usage: Counter[tuple[str, str]] = Counter()
    for split in ("train", "dev", "test"):
        per_language = int(base.SPLIT_PER_LABEL[split]) // 2
        for label in NETWORK_EXACT_TOOL_LABELS:
            for language in ("en", "zh"):
                for index in range(per_language):
                    row = base.build_row(
                        source_by_split_label[split],
                        label=label,
                        split=split,
                        language=language,
                        language_index=index,
                    )
                    if language == "en":
                        for source in row["sources"]:
                            source_id = str(source["source_id"])
                            if source_id not in source_ids[split]:
                                raise RuntimeError(
                                    "S38 English intent crossed source split"
                                )
                            source_usage[(split, source_id)] += 1
                    trajectories.append(row)
    audit = {
        "source_pool_counts": {
            split: len(source_ids[split]) for split in source_ids
        },
        "source_pool_id_sha256": {
            split: hashlib.sha256(
                "\n".join(sorted(source_ids[split])).encode("utf-8")
            ).hexdigest()
            for split in source_ids
        },
        "source_usage_distinct_ids": {
            split: len(
                {
                    source_id
                    for used_split, source_id in source_usage
                    if used_split == split
                }
            )
            for split in source_ids
        },
        "fixed_depth_assignments": assignments,
    }
    return trajectories, audit


def expand_prefixes(
    trajectories: list[dict[str, object]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for trajectory in trajectories:
        inputs = [
            *trajectory["history_selector_inputs"],
            trajectory["selector_input"],
        ]
        labels = [*trajectory["expected_history_labels"], trajectory["label"]]
        steps = [*trajectory["history_steps"], trajectory["step"]]
        if not (
            len(inputs)
            == len(labels)
            == len(steps)
            == int(trajectory["decision_index"]) + 1
        ):
            raise RuntimeError("S38 trajectory length changed")
        source_digest = canonical_digest(trajectory)
        trajectory_id = opaque_id("T", source_digest)
        for position, (input_dict, label, step) in enumerate(
            zip(inputs, labels, steps, strict=True)
        ):
            value = selector_input(input_dict)
            if (
                render_compact_selector_bootstrap(value) != trajectory["bootstrap"]
                or render_compact_selector_step(value) != step
            ):
                raise RuntimeError("S38 base trajectory render changed")
            prior_steps = steps[:position]
            rendered = str(trajectory["bootstrap"]) + "".join(
                "\n" + str(item) for item in [*prior_steps, step]
            )
            kind = "current" if position == len(steps) - 1 else "history"
            stage_group = (
                "completion"
                if label == "final_answer"
                else ("first" if position == 0 else "continuation")
            )
            rows.append(
                {
                    "schema_version": ROW_SCHEMA,
                    "dataset_version": VERSION,
                    "sample_id": opaque_id("P", source_digest, position),
                    "trajectory_id": trajectory_id,
                    "source_trajectory_sha256": source_digest,
                    "split": trajectory["split"],
                    "label": label,
                    "language": trajectory["language"],
                    "prefix_kind": kind,
                    "stage_group": stage_group,
                    "trajectory_position": position,
                    "trajectory_length": len(steps),
                    "has_future_tool_distractor": position < len(steps) - 1,
                    "selector_input": input_dict,
                    "selector_input_sha256": canonical_digest(input_dict),
                    "bootstrap": trajectory["bootstrap"],
                    "prior_steps": prior_steps,
                    "step": step,
                    "rendered_input": rendered,
                    "rendered_input_sha256": hashlib.sha256(
                        rendered.encode("utf-8")
                    ).hexdigest(),
                    "compact_input_schema_version": (
                        COMPACT_SELECTOR_INPUT_SCHEMA_VERSION
                    ),
                    "compact_menu_digest": compact_selector_menu_digest(),
                    "names_and_descriptions_only": True,
                    "contains_parameter_schemas": False,
                    "contains_full_tool_results": False,
                    "contains_executor_text": False,
                    "generated_rwkv_text": False,
                    "sampling_invoked": False,
                }
            )
    return rows


def validate(
    trajectories: list[dict[str, object]], rows: list[dict[str, object]]
) -> dict[str, object]:
    trajectory_counts = Counter(str(row["split"]) for row in trajectories)
    prefix_counts = Counter(str(row["split"]) for row in rows)
    if trajectory_counts != Counter(EXPECTED_TRAJECTORIES):
        raise RuntimeError(f"S38 trajectory counts changed: {trajectory_counts}")
    if prefix_counts != Counter(EXPECTED_PREFIXES):
        raise RuntimeError(f"S38 prefix counts changed: {prefix_counts}")
    if len(rows) != 5142:
        raise RuntimeError("S38 total prefix count changed")

    executable = set(NETWORK_EXACT_TOOL_LABELS) - {"final_answer", "ABSTAIN"}
    expected_depths = {
        "train": Counter({0: 20, 1: 12, 2: 8}),
        "dev": Counter({0: 5, 1: 3, 2: 2}),
        "test": Counter({0: 5, 1: 3, 2: 2}),
    }
    for split in expected_depths:
        for label in executable:
            for language in ("en", "zh"):
                depths = Counter(
                    int(row["decision_index"])
                    for row in trajectories
                    if row["split"] == split
                    and row["label"] == label
                    and row["language"] == language
                )
                if depths != expected_depths[split]:
                    raise RuntimeError(
                        f"S38 depth distribution changed: {split}/{label}/{language}"
                    )

    ids = [str(row["sample_id"]) for row in rows]
    trajectory_ids = {str(row["trajectory_id"]) for row in rows}
    if len(set(ids)) != len(ids) or len(trajectory_ids) != 3000:
        raise RuntimeError("S38 opaque ID uniqueness changed")
    if any(
        not OPAQUE_ID.fullmatch(value) for value in [*ids, *trajectory_ids]
    ):
        raise RuntimeError("S38 opaque ID format changed")
    for value in [*ids, *trajectory_ids]:
        if any(label.lower() in value.lower() for label in NETWORK_EXACT_TOOL_LABELS):
            raise RuntimeError("S38 opaque ID contains a label")

    split_trajectories = {
        split: {
            str(row["trajectory_id"])
            for row in rows
            if row["split"] == split
        }
        for split in EXPECTED_TRAJECTORIES
    }
    if (
        split_trajectories["train"] & split_trajectories["dev"]
        or split_trajectories["train"] & split_trajectories["test"]
        or split_trajectories["dev"] & split_trajectories["test"]
    ):
        raise RuntimeError("S38 trajectory split overlap changed")

    grouped: defaultdict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        value = selector_input(row["selector_input"])
        if (
            render_compact_selector_bootstrap(value) != row["bootstrap"]
            or render_compact_selector_step(value) != row["step"]
            or row["rendered_input"]
            != str(row["bootstrap"])
            + "".join(
                "\n" + str(item)
                for item in [*row["prior_steps"], row["step"]]
            )
        ):
            raise RuntimeError("S38 derived render changed")
        grouped[str(row["trajectory_id"])].append(row)
    for group in grouped.values():
        if [int(row["trajectory_position"]) for row in group] != list(
            range(len(group))
        ):
            raise RuntimeError("S38 prefix closure order changed")

    return {
        "trajectory_counts": dict(trajectory_counts),
        "prefix_counts": dict(prefix_counts),
        "kind_counts": dict(Counter(str(row["prefix_kind"]) for row in rows)),
        "language_counts": dict(Counter(str(row["language"]) for row in rows)),
        "position_counts": dict(
            sorted(Counter(int(row["trajectory_position"]) for row in rows).items())
        ),
        "label_counts_by_split": {
            split: dict(
                sorted(
                    Counter(
                        str(row["label"])
                        for row in rows
                        if row["split"] == split
                    ).items()
                )
            )
            for split in EXPECTED_TRAJECTORIES
        },
        "executable_depth_distribution_per_label_language": {
            split: dict(expected_depths[split]) for split in expected_depths
        },
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S38 dataset")
    for path, expected in {
        SOURCE: SOURCE_SHA256,
        BASE_GENERATOR: BASE_GENERATOR_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
        PROTOCOL: PROTOCOL_SHA256,
    }.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(f"S38 frozen identity changed: {path}: {actual}")
    source_rows = [
        json.loads(line)
        for line in SOURCE.read_text(encoding="utf-8").splitlines()
    ]
    base = load_base()
    trajectories, source_audit = make_trajectories(base, source_rows)
    rows = expand_prefixes(trajectories)
    validation = validate(trajectories, rows)

    OUTPUT.mkdir(parents=True)
    cases = OUTPUT / "cases.jsonl"
    with cases.open("w", encoding="utf-8") as stream:
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
        "schema_version": "rwkv-lh.dataset-manifest.s38.v1",
        "dataset_version": VERSION,
        "purpose": (
            "source-split-separated and depth-distribution-matched prefix "
            "supervision for the current direct Selector architecture"
        ),
        "sources": {
            "v2_4_operation_contract": {
                "path": str(SOURCE.relative_to(ROOT)),
                "sha256": SOURCE_SHA256,
                "usage": "target split uses only the same v2.4 source split",
            },
            "frozen_s30_trajectory_builder": {
                "path": str(BASE_GENERATOR.relative_to(ROOT)),
                "sha256": BASE_GENERATOR_SHA256,
                "overrides": [
                    "source pool partition",
                    "fixed depth assignment",
                    "opaque prefix expansion",
                ],
            },
        },
        "preregistration": {
            "path": str(PREREGISTRATION.relative_to(ROOT)),
            "sha256": PREREGISTRATION_SHA256,
        },
        "generator": {
            "path": str(Path(__file__).resolve().relative_to(ROOT)),
            "sha256": sha256_file(Path(__file__).resolve()),
        },
        "generation_method": (
            "build S30-shaped trajectories from split-matched v2.4 intent "
            "pools with one fixed depth permutation per split, then expand "
            "every callable prefix"
        ),
        "input_protocol": {
            "schema_version": COMPACT_SELECTOR_INPUT_SCHEMA_VERSION,
            "menu_digest": compact_selector_menu_digest(),
            "source_path": str(PROTOCOL.relative_to(ROOT)),
            "source_sha256": PROTOCOL_SHA256,
            "names_and_descriptions_only": True,
        },
        "files": {
            "cases.jsonl": {
                "rows": len(rows),
                "sha256": sha256_file(cases),
            }
        },
        "source_partition_audit": source_audit,
        "validation": {
            **validation,
            "exact_render_replay": True,
            "opaque_ids_without_labels": True,
            "trajectory_split_overlap": 0,
            "operation_source_split_overlap": 0,
            "parameter_schemas": False,
            "full_tool_results": False,
            "executor_text": False,
            "generated_rwkv_text": False,
            "sampling_invoked": False,
        },
    }
    (OUTPUT / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (OUTPUT / "README.md").write_text(
        "# S38 matched-prefix Selector dataset\n\n"
        "This dataset contains exactly 2,000/500/500 base trajectories with "
        "matched depth distributions and split-separated v2.4 English intent "
        "sources. Every callable prefix is supervised. Full provenance, "
        "generation, counts, and hashes are frozen in `manifest.json`.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "event": "s38_matched_prefix_dataset_generated",
                "trajectory_rows": len(trajectories),
                "prefix_rows": len(rows),
                "counts": validation,
                "cases_sha256": manifest["files"]["cases.jsonl"]["sha256"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
