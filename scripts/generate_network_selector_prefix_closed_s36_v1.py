#!/usr/bin/env python3
"""Derive the frozen S36 prefix-closed Selector dataset from S30."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
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
SOURCE = ROOT / "data/datasets/rwkv_lh_network_selector_true_trajectory_s30_v1/cases.jsonl"
PREREGISTRATION = ROOT / "data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/SEL_2P9_S36_PREFIX_CLOSED_HEAD_RETRAIN_PREREGISTRATION.md"
PROTOCOL = ROOT / "rwkv_lh/exact_tool_selector/compact_protocol_v3.py"
OUTPUT = ROOT / "data/datasets/rwkv_lh_network_selector_prefix_closed_s36_v1"

SOURCE_SHA256 = "5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305"
PREREGISTRATION_SHA256 = "1ec0bd7a0151ed85c1c5a668b12c4ebee628a6492755abd30b3b92f4e915e95d"
PROTOCOL_SHA256 = "2d5668e9a7c4590670bcb9af4ed93df74e97de8bc49d0980db2e0f7479f62a6b"
VERSION = "rwkv-lh.network-selector.prefix-closed-s36.v1"
ROW_SCHEMA = "rwkv-lh.network-selector-prefix-row.s36.v1"
EXPECTED_TRAJECTORIES = {"train": 2000, "dev": 500, "test": 500}
EXPECTED_PREFIXES = {"train": 3336, "dev": 765, "test": 995}
OPAQUE_ID = re.compile(r"^S36-[PT]-[0-9a-f]{24}$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def opaque_id(kind: str, *parts: object) -> str:
    digest = hashlib.sha256(
        "|".join(["S36", kind, *(str(part) for part in parts)]).encode("utf-8")
    ).hexdigest()[:24]
    return f"S36-{kind}-{digest}"


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


def make_rows() -> tuple[list[dict[str, object]], dict[str, int]]:
    derived: list[dict[str, object]] = []
    trajectory_counts: Counter[str] = Counter()
    with SOURCE.open("r", encoding="utf-8") as stream:
        for source_line in stream:
            source_line = source_line.rstrip("\n")
            source_digest = hashlib.sha256(source_line.encode("utf-8")).hexdigest()
            source = json.loads(source_line)
            split = str(source["split"])
            language = str(source["language"])
            history_inputs = list(source["history_selector_inputs"])
            inputs = [*history_inputs, source["selector_input"]]
            labels = [*source["expected_history_labels"], source["label"]]
            steps = [*source["history_steps"], source["step"]]
            if not (
                len(inputs)
                == len(labels)
                == len(steps)
                == int(source["decision_index"]) + 1
            ):
                raise RuntimeError("S36 source trajectory length changed")
            trajectory_id = opaque_id("T", source_digest)
            trajectory_counts[split] += 1
            for position, (input_dict, label, step) in enumerate(
                zip(inputs, labels, steps, strict=True)
            ):
                value = selector_input(input_dict)
                if render_compact_selector_bootstrap(value) != source["bootstrap"]:
                    raise RuntimeError("S36 source bootstrap render changed")
                if render_compact_selector_step(value) != step:
                    raise RuntimeError("S36 source step render changed")
                prior_steps = steps[:position]
                rendered = str(source["bootstrap"]) + "".join(
                    "\n" + str(item) for item in [*prior_steps, step]
                )
                prefix_id = opaque_id("P", source_digest, position)
                kind = "current" if position == len(steps) - 1 else "history"
                stage_group = (
                    "completion"
                    if label == "final_answer"
                    else ("first" if position == 0 else "continuation")
                )
                derived.append(
                    {
                        "schema_version": ROW_SCHEMA,
                        "dataset_version": VERSION,
                        "sample_id": prefix_id,
                        "trajectory_id": trajectory_id,
                        "source_row_sha256": source_digest,
                        "split": split,
                        "label": label,
                        "language": language,
                        "prefix_kind": kind,
                        "stage_group": stage_group,
                        "trajectory_position": position,
                        "trajectory_length": len(steps),
                        "has_future_tool_distractor": position < len(steps) - 1,
                        "selector_input": input_dict,
                        "selector_input_sha256": canonical_digest(input_dict),
                        "bootstrap": source["bootstrap"],
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
    return derived, dict(trajectory_counts)


def validate(
    rows: list[dict[str, object]], trajectory_counts: dict[str, int]
) -> dict[str, object]:
    if trajectory_counts != EXPECTED_TRAJECTORIES:
        raise RuntimeError(f"S36 trajectory counts changed: {trajectory_counts}")
    prefix_counts = Counter(str(row["split"]) for row in rows)
    if dict(prefix_counts) != EXPECTED_PREFIXES:
        raise RuntimeError(f"S36 prefix counts changed: {dict(prefix_counts)}")
    if len(rows) != 5096:
        raise RuntimeError("S36 total prefix count changed")
    sample_ids = [str(row["sample_id"]) for row in rows]
    trajectory_ids = {str(row["trajectory_id"]) for row in rows}
    if len(set(sample_ids)) != len(sample_ids) or len(trajectory_ids) != 3000:
        raise RuntimeError("S36 opaque ID uniqueness changed")
    if any(not OPAQUE_ID.fullmatch(value) for value in [*sample_ids, *trajectory_ids]):
        raise RuntimeError("S36 opaque ID format changed")
    lowered_labels = [label.lower() for label in NETWORK_EXACT_TOOL_LABELS]
    if any(
        label in value.lower()
        for value in [*sample_ids, *trajectory_ids]
        for label in lowered_labels
    ):
        raise RuntimeError("S36 opaque ID unexpectedly contains a label")
    trajectory_splits: dict[str, set[str]] = {
        split: {
            str(row["trajectory_id"])
            for row in rows
            if row["split"] == split
        }
        for split in EXPECTED_TRAJECTORIES
    }
    if (
        trajectory_splits["train"] & trajectory_splits["dev"]
        or trajectory_splits["train"] & trajectory_splits["test"]
        or trajectory_splits["dev"] & trajectory_splits["test"]
    ):
        raise RuntimeError("S36 trajectory split isolation changed")
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
            raise RuntimeError("S36 derived render identity changed")
    kind_counts = Counter(str(row["prefix_kind"]) for row in rows)
    if kind_counts != {"current": 3000, "history": 2096}:
        raise RuntimeError(f"S36 prefix-kind counts changed: {kind_counts}")
    return {
        "prefix_counts": dict(prefix_counts),
        "trajectory_counts": trajectory_counts,
        "kind_counts": dict(kind_counts),
        "language_counts": dict(
            Counter(str(row["language"]) for row in rows)
        ),
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
    }


def main() -> None:
    if OUTPUT.exists():
        raise RuntimeError("refusing to replace frozen S36 dataset")
    for path, expected in {
        SOURCE: SOURCE_SHA256,
        PREREGISTRATION: PREREGISTRATION_SHA256,
        PROTOCOL: PROTOCOL_SHA256,
    }.items():
        actual = sha256_file(path) if path.is_file() else "missing"
        if actual != expected:
            raise RuntimeError(
                f"S36 frozen source identity changed: {path}: {actual}"
            )

    rows, trajectory_counts = make_rows()
    validation = validate(rows, trajectory_counts)
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
        "schema_version": "rwkv-lh.dataset-manifest.s36.v1",
        "dataset_version": VERSION,
        "purpose": (
            "prefix-closed supervision for every deployed Selector position "
            "while preserving S30 trajectory state semantics"
        ),
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": SOURCE_SHA256,
            "version": "rwkv-lh.network-selector.true-trajectory-s30.v1",
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
            "deterministically expand each S30 history/current trajectory into "
            "one row per callable prefix without changing rendered input"
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
        "validation": {
            **validation,
            "exact_render_replay": True,
            "opaque_ids_without_labels": True,
            "trajectory_split_overlap": 0,
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
        "# S36 prefix-closed Selector dataset\n\n"
        "Every S30 trajectory is expanded into one supervised row for every "
        "callable Selector prefix. Source, version, purpose, generator, hashes, "
        "counts, and validation are frozen in `manifest.json`. IDs are opaque "
        "and contain no class names.\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "event": "s36_prefix_dataset_generated",
                "rows": len(rows),
                "counts": validation,
                "cases_sha256": manifest["files"]["cases.jsonl"]["sha256"],
            },
            ensure_ascii=False,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
