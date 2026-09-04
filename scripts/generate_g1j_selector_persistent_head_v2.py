#!/usr/bin/env python3
"""Generate the frozen persistent-causal G1J Selector Head v2 dataset."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from rwkv_lh.exact_tool_selector.network_protocol import (
    NETWORK_ABSTAIN_LABEL,
    NETWORK_EXACT_TOOL_LABELS,
    network_selector_tool_menu,
)
from rwkv_lh.exact_tool_selector.runtime_projection import (
    SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION,
    SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION,
)
from rwkv_lh.goal_state_protocols import selector_intent
from rwkv_lh.tokenizer import RWKVTokenizer


ROOT = Path("/home/chase/GitHub/RWKV-LH")
DATASET_ID = "rwkv_lh_g1j_selector_persistent_head_v2"
DATASET_VERSION = "2"
SOURCE_SCHEMA = "rwkv-lh.g1j-selector-persistent-head-source.v2"
SAMPLE_SCHEMA = "rwkv-lh.g1j-selector-persistent-head-sample.v2"
SEQUENCE_SCHEMA = "rwkv-lh.g1j-selector-persistent-head-sequence.v2"
MANIFEST_SCHEMA = "rwkv-lh.g1j-selector-persistent-head-manifest.v2"
TRAJECTORY_MODE = "persistent-causal-sequences.v1"
DEFAULT_OUTPUT = ROOT / "data/datasets" / DATASET_ID

OPERATION_CYCLE = (
    "current_time",
    "date_diff",
    "calculator",
    "make_directory",
    "write_file",
    "append_file",
    "remove_line",
    "replace_text",
    "read_file",
    "bind_evidence",
    "file_digest",
    "copy_file",
    "move_file",
    "list_directory",
    "search_text",
    "read_json",
    "patch_json",
    "write_json",
    "check_command",
    "run_command",
    "delete_file",
    "web_search",
    "connector_lookup",
)

VARIANTS = (
    (
        "release-manifest",
        "a staged release manifest whose provenance must remain auditable; its checksum ledger, signed approval note, and packaging record form one bounded handoff",
    ),
    (
        "localized-handbook",
        "a localized operator handbook with bounded evidence requirements; terminology review, locale metadata, and the rendered guide must agree without rewriting unrelated chapters",
    ),
    (
        "telemetry-snapshot",
        "a telemetry snapshot prepared for an offline incident review; the captured counters, anomaly marker, and retention note must preserve their observation order",
    ),
    (
        "scientific-results",
        "a reproducible scientific result bundle with recorded checks; measurement provenance, derived values, and the verification note must remain independently inspectable",
    ),
    (
        "asset-catalog",
        "a versioned asset catalog undergoing a controlled migration; inventory identity, destination naming, and post-move validation must stay within the declared asset subtree",
    ),
    (
        "migration-ledger",
        "a migration ledger whose old and new locations must be reconciled; each source revision, transfer receipt, and cleanup observation belongs to the same migration entry",
    ),
    (
        "incident-report",
        "an incident report assembled from local and public observations; the timeline, external advisory, and remediation evidence must retain distinct source identities",
    ),
    (
        "package-inventory",
        "a package inventory that must preserve exact source identities; registry coordinates, local lock data, and compatibility checks must be recorded without substituting packages",
    ),
    (
        "benchmark-bundle",
        "a benchmark bundle with explicit read, mutation, and check evidence; fixture inputs, produced artifacts, and deterministic command results must remain attributable",
    ),
    (
        "weather-brief",
        "a dated weather brief combining structured records and calculations; observation time, calendar interval, and computed summary must use the named location and date window",
    ),
)

LOCAL_READ_OPERATIONS = frozenset(
    {"list_directory", "search_text", "read_file", "read_json", "file_digest", "bind_evidence"}
)
LOCAL_WRITE_OPERATIONS = frozenset(
    {
        "write_file",
        "write_json",
        "patch_json",
        "replace_text",
        "remove_line",
        "append_file",
        "make_directory",
        "copy_file",
        "move_file",
        "delete_file",
        "run_command",
    }
)


def _json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _canonical(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _split(variant: int) -> str:
    if variant < 6:
        return "train"
    if variant < 8:
        return "dev"
    return "sealed"


def _ordered_labels(values: Iterable[str]) -> list[str]:
    selected = set(values)
    return [label for label in NETWORK_EXACT_TOOL_LABELS if label in selected]


def _paths(slug: str, edge: int) -> dict[str, str]:
    directory = f"fixtures/{slug}/edge-{edge:02d}"
    return {
        "directory": directory,
        "source": f"{directory}/source.txt",
        "source_json": f"{directory}/source.json",
        "result": f"{directory}/result.txt",
        "result_json": f"{directory}/result.json",
        "copy": f"{directory}/copy.txt",
        "moved": f"{directory}/moved.txt",
    }


def _arguments(operation: str, paths: Mapping[str, str], variant: int) -> dict[str, Any]:
    table: dict[str, dict[str, Any]] = {
        "list_directory": {"path": paths["directory"], "max_entries": 50},
        "search_text": {"path": paths["directory"], "query": f"status_{variant}"},
        "read_file": {"path": paths["source"], "start_byte": 0, "max_bytes": 512},
        "read_json": {"path": paths["source_json"], "start_byte": 0, "max_bytes": 512},
        "file_digest": {"path": paths["source"]},
        "write_file": {"path": paths["result"], "content": f"verified variant {variant}\n"},
        "write_json": {"path": paths["result_json"], "value": {"variant": variant, "status": "ready"}},
        "patch_json": {"path": paths["source_json"], "updates": {"status": "ready"}},
        "replace_text": {"path": paths["source"], "old": "draft", "new": "ready"},
        "remove_line": {"path": paths["source"], "line": "obsolete=true"},
        "append_file": {"path": paths["source"], "content": f"variant={variant}\n"},
        "make_directory": {"path": paths["directory"]},
        "copy_file": {"source": paths["source"], "destination": paths["copy"]},
        "move_file": {"source": paths["source"], "destination": paths["moved"]},
        "delete_file": {"path": paths["source"]},
        "bind_evidence": {"path": paths["source"], "start_line": 1, "end_line": 1},
        "check_command": {"argv": ["python", "-m", "pytest", "-q"]},
        "run_command": {"argv": ["python", "scripts/update_fixture.py", str(variant)]},
        "web_search": {"query": f"official release status variant {variant}"},
        "connector_lookup": {"connector": "package", "query": f"rwkv-lh-{variant}"},
        "calculator": {"expression": f"{variant + 21}*2"},
        "date_diff": {"start_date": "2026-09-01", "end_date": f"2026-09-{variant + 10:02d}"},
        "current_time": {"timezone": "Asia/Shanghai"},
    }
    return table[operation]


def _result(operation: str, paths: Mapping[str, str], variant: int) -> dict[str, Any]:
    return {
        "success": True,
        "outcome_type": "observation" if operation not in LOCAL_WRITE_OPERATIONS else "mutation",
        "operation": operation,
        "fixture": f"variant-{variant:02d}",
        "path": paths["source"] if operation in LOCAL_READ_OPERATIONS else paths["result"],
    }


def _eligible(source: str, target: str, edge: int, variant: int) -> list[str]:
    candidates = {source, target}
    offsets = (3, 7, 11, 15, 19)
    for offset in offsets:
        candidates.add(OPERATION_CYCLE[(edge + variant + offset) % len(OPERATION_CYCLE)])
        if len(candidates) == 5:
            break
    return _ordered_labels(candidates)


def _goal_frontier(
    *,
    variant: int,
    edge: int,
    source: str,
    target: str,
    eligible: Sequence[str],
    position: int,
    descriptions: Mapping[str, str],
) -> str:
    slug, context = VARIANTS[variant]
    paths = _paths(slug, edge)
    operations = {source, target}
    read_roots = [paths["directory"]] if operations & LOCAL_READ_OPERATIONS else []
    write_roots = [paths["directory"]] if operations & LOCAL_WRITE_OPERATIONS else []
    action_id = f"A-{variant:02d}-{edge:02d}-01"
    latest_action = None
    latest_audit = None
    if position == 1:
        latest_action = {
            "action_id": action_id,
            "sequence": variant * 100 + edge + 1,
            "operation": source,
            "status": "succeeded",
            "arguments": _arguments(source, paths, variant),
            "result": _result(source, paths, variant),
            "error": {},
        }
        if target in LOCAL_READ_OPERATIONS or target in LOCAL_WRITE_OPERATIONS:
            latest_audit = {
                "status": "mechanically_incomplete",
                "gaps": ["the active step still lacks its second required evidence-bearing action"],
                "successful_action_ids": [action_id],
                "missing_read_roots": read_roots if target in LOCAL_READ_OPERATIONS else [],
                "missing_write_roots": write_roots if target in LOCAL_WRITE_OPERATIONS else [],
            }
        else:
            latest_audit = {
                "status": "accepted",
                "verdict": "continue",
                "evidence_refs": [action_id],
                "gaps": ["the second ordered observation or calculation is still outstanding"],
                "reason": "the first Harness result is valid but the bounded step is not complete",
            }
    current_objective = (
        f"For {context}, perform two ordered actions inside this one bounded step. "
        f"First, {descriptions[source][0].lower() + descriptions[source][1:]} "
        f"After that Harness action succeeds, {descriptions[target][0].lower() + descriptions[target][1:]} "
        "The second action consumes or verifies the first result; do not advance another plan step."
    )
    value = {
        "schema_version": SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION,
        "active_step": {
            "step_id": f"S-{variant:02d}-{edge:02d}",
            "step_revision": 1,
            "stage": edge % 4 + 1,
            "depends_on": [] if edge == 0 else [f"S-{variant:02d}-PREVIOUS"],
            "read_roots": read_roots,
            "write_roots": write_roots,
            "success_evidence": [
                f"both ordered actions for {slug} have successful Harness records"
            ],
            "constraints": ["use only the active step and its explicit dependencies"],
        },
        "progress": {
            "completed_step_ids": [f"S-{variant:02d}-PREVIOUS"] if edge else [],
            "completed_stage_count": variant % 4,
            "current_step_action_count": position,
        },
        "latest_action": latest_action,
        "latest_audit_feedback": latest_audit,
        "eligible_tools": [
            {"name": label, "description": descriptions[label]}
            for label in eligible
        ],
        "instruction": (
            "Choose exactly one eligible next operation for this active step. "
            "Use the latest Harness result and audit gaps; do not plan, fill "
            "parameters, audit, or answer the user."
        ),
        "current_objective": current_objective,
    }
    return "GoalFrontierStateV1: " + json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _final_stage(variant: int, position: int) -> str:
    slug, context = VARIANTS[variant]
    value = {
        "schema_version": SELECTOR_COMPACT_CONTRACT_STAGE_PROJECTION_VERSION,
        "action_index": variant + 2,
        "completion_ready": True,
        "latest_action": {
            "sequence": variant + 2,
            "operation": OPERATION_CYCLE[(variant * 2) % len(OPERATION_CYCLE)],
            "success": True,
            "outcome_type": "observation",
            "complete": True,
            "truncated": False,
        },
        "atom_objective": (
            f"Return the evidence-complete result for {context}; all bounded "
            f"actions in {slug} are committed and no operation remains."
        ),
    }
    if position == 1:
        value["latest_action"]["outcome_type"] = "verified_completion"
    return "CurrentDirectStageV3: " + json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _abstain_stage(
    variant: int,
    eligible: Sequence[str],
    descriptions: Mapping[str, str],
) -> str:
    slug, context = VARIANTS[variant]
    value = {
        "schema_version": SELECTOR_GOAL_FRONTIER_STAGE_PROJECTION_VERSION,
        "active_step": {
            "step_id": f"S-{variant:02d}-AMBIGUOUS",
            "step_revision": 1,
            "stage": 1,
            "depends_on": [],
            "read_roots": [],
            "write_roots": [],
            "success_evidence": ["the missing source identity has been supplied by the Planner"],
            "constraints": ["do not guess an operation or invent the missing source"],
        },
        "progress": {
            "completed_step_ids": [],
            "completed_stage_count": variant % 3,
            "current_step_action_count": 0,
        },
        "latest_action": None,
        "latest_audit_feedback": None,
        "eligible_tools": [
            {"name": label, "description": descriptions[label]}
            for label in eligible
        ],
        "instruction": (
            "Choose exactly one eligible next operation for this active step. "
            "Use the latest Harness result and audit gaps; do not plan, fill "
            "parameters, audit, or answer the user."
        ),
        "current_objective": (
            f"For {context}, the Planner has not identified whether {slug} "
            "requires a local observation, a public lookup, a calculation, or "
            "a mutation. No source, destination, expression, or evidence gap is "
            "present, so no single next operation is knowable."
        ),
    }
    return "GoalFrontierStateV1: " + json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _payload(
    *,
    stage_objective: str,
    stage_role: str,
    completed_stage_count: int,
    action_index: int,
    succeeded: Sequence[str],
    protocol_rejections: int,
    eligible: Sequence[str],
    selected: str,
) -> dict[str, Any]:
    return {
        "stage_objective": stage_objective,
        "stage_role": stage_role,
        "progress": {
            "completed_stage_count": completed_stage_count,
            "action_index": action_index,
            "succeeded_operations": list(succeeded),
            "failed_operations": [],
            "protocol_rejection_count": protocol_rejections,
        },
        "eligible_labels": list(eligible),
        "selected_operation": selected,
        "selection_authority": "planner_contract",
        "selection_verifier_id": "rwkv-lh.g1j-selector-persistent-cycle-verifier.v2",
    }


def _source(
    *,
    sequence_id: str,
    variant: int,
    position: int,
    kind: str,
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    value = {
        "schema_version": SOURCE_SCHEMA,
        "dataset_id": DATASET_ID,
        "sequence_id": sequence_id,
        "sequence_position": position,
        "sequence_length": 2,
        "split": _split(variant),
        "semantic_variant": variant,
        "source_kind": kind,
        "source_path": "scripts/generate_g1j_selector_persistent_head_v2.py",
        "payload": dict(payload),
    }
    value["source_id"] = "g1j-selector-v2-" + _digest(value)
    return value


def _records() -> list[dict[str, Any]]:
    production_operations = tuple(
        label
        for label in NETWORK_EXACT_TOOL_LABELS
        if label not in {"final_answer", NETWORK_ABSTAIN_LABEL}
    )
    if (
        len(OPERATION_CYCLE) != len(production_operations)
        or set(OPERATION_CYCLE) != set(production_operations)
    ):
        raise RuntimeError("production operation order differs from the preregistered cycle")
    descriptions = {
        str(item["name"]): str(item["description"])
        for item in network_selector_tool_menu()
    }
    records: list[dict[str, Any]] = []
    for variant in range(len(VARIANTS)):
        for edge, source_label in enumerate(OPERATION_CYCLE):
            target_label = OPERATION_CYCLE[(edge + 1) % len(OPERATION_CYCLE)]
            eligible = _eligible(source_label, target_label, edge, variant)
            sequence_id = f"SEQ-V{variant:02d}-EDGE{edge:02d}"
            for position, selected in enumerate((source_label, target_label)):
                payload = _payload(
                    stage_objective=_goal_frontier(
                        variant=variant,
                        edge=edge,
                        source=source_label,
                        target=target_label,
                        eligible=eligible,
                        position=position,
                        descriptions=descriptions,
                    ),
                    stage_role="tool_intent",
                    completed_stage_count=variant % 4,
                    action_index=0 if position == 0 else variant * 100 + edge + 1,
                    succeeded=() if position == 0 else (source_label,),
                    protocol_rejections=0,
                    eligible=eligible,
                    selected=selected,
                )
                records.append(
                    _source(
                        sequence_id=sequence_id,
                        variant=variant,
                        position=position,
                        kind="ordered_planner_contract_fixture",
                        payload=payload,
                    )
                )
        final_sequence = f"SEQ-V{variant:02d}-FINAL"
        for position in range(2):
            records.append(
                _source(
                    sequence_id=final_sequence,
                    variant=variant,
                    position=position,
                    kind="completed_contract_fixture",
                    payload=_payload(
                        stage_objective=_final_stage(variant, position),
                        stage_role="final_answer_intent",
                        completed_stage_count=variant + 1,
                        action_index=variant + 2,
                        succeeded=(OPERATION_CYCLE[(variant * 2) % len(OPERATION_CYCLE)],),
                        protocol_rejections=position,
                        eligible=("final_answer",),
                        selected="final_answer",
                    ),
                )
            )
        abstain_candidates = {
            NETWORK_ABSTAIN_LABEL,
            OPERATION_CYCLE[variant % len(OPERATION_CYCLE)],
            OPERATION_CYCLE[(variant + 5) % len(OPERATION_CYCLE)],
            OPERATION_CYCLE[(variant + 10) % len(OPERATION_CYCLE)],
            OPERATION_CYCLE[(variant + 15) % len(OPERATION_CYCLE)],
        }
        abstain_eligible = _ordered_labels(abstain_candidates)
        abstain_sequence = f"SEQ-V{variant:02d}-ABSTAIN"
        for position in range(2):
            records.append(
                _source(
                    sequence_id=abstain_sequence,
                    variant=variant,
                    position=position,
                    kind="ambiguous_contract_fixture",
                    payload=_payload(
                        stage_objective=_abstain_stage(
                            variant,
                            abstain_eligible,
                            descriptions,
                        ),
                        stage_role="tool_intent",
                        completed_stage_count=variant % 3,
                        action_index=0,
                        succeeded=(),
                        protocol_rejections=position,
                        eligible=abstain_eligible,
                        selected=NETWORK_ABSTAIN_LABEL,
                    ),
                )
            )
    return records


def _sample(source: Mapping[str, Any], tokenizer: RWKVTokenizer) -> dict[str, Any]:
    payload = source["payload"]
    selector_intent.validate_source(payload)
    prompt = selector_intent.render_prompt(payload)
    target = selector_intent.render_target(payload)
    if selector_intent.parse_target(target) != payload["selected_operation"]:
        raise RuntimeError("Selector target round trip changed")
    prompt_tokens = len(tokenizer.encode(prompt))
    if prompt_tokens > 2048:
        raise RuntimeError("Selector prompt exceeds the serving extraction limit")
    value = {
        "schema_version": SAMPLE_SCHEMA,
        "dataset_id": DATASET_ID,
        "source_id": source["source_id"],
        "sequence_id": source["sequence_id"],
        "sequence_position": source["sequence_position"],
        "sequence_length": source["sequence_length"],
        "split": source["split"],
        "label": payload["selected_operation"],
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "target_sha256": hashlib.sha256(target.encode("utf-8")).hexdigest(),
        "prompt_tokens": prompt_tokens,
        "target_tokens": len(tokenizer.encode(target)),
    }
    value["sample_id"] = "selector-v2-" + _digest(value)
    return value


def _ngrams(value: str, width: int = 5) -> Counter[bytes]:
    source = value.encode("utf-8")
    if len(source) < width:
        return Counter({source: 1})
    return Counter(source[index : index + width] for index in range(len(source) - width + 1))


def _similarity_value(source: Mapping[str, Any]) -> str:
    payload = source["payload"]
    return _canonical(
        {
            "stage_objective": payload["stage_objective"],
            "stage_role": payload["stage_role"],
            "progress": payload["progress"],
            "eligible_labels": payload["eligible_labels"],
        }
    )


def _maximum_similarity(
    left: Sequence[Mapping[str, Any]],
    right: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    left_vectors = [(_ngrams(_similarity_value(row)), row["source_id"]) for row in left]
    right_vectors = [(_ngrams(_similarity_value(row)), row["source_id"]) for row in right]
    left_norms = [math.sqrt(sum(count * count for count in vector.values())) for vector, _ in left_vectors]
    right_norms = [math.sqrt(sum(count * count for count in vector.values())) for vector, _ in right_vectors]
    maximum = -1.0
    pair = ("", "")
    for left_index, (left_vector, left_id) in enumerate(left_vectors):
        for right_index, (right_vector, right_id) in enumerate(right_vectors):
            small, large = (
                (left_vector, right_vector)
                if len(left_vector) <= len(right_vector)
                else (right_vector, left_vector)
            )
            dot = sum(count * large.get(key, 0) for key, count in small.items())
            score = dot / (left_norms[left_index] * right_norms[right_index])
            if score > maximum:
                maximum = score
                pair = (left_id, right_id)
    return {"maximum": maximum, "left_source_id": pair[0], "right_source_id": pair[1]}


def _write_jsonl(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    path.write_bytes(b"".join(_json_bytes(row) for row in rows))


def _file_record(path: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
        "lines": data.count(b"\n"),
    }


def generate(output: Path) -> None:
    output = output.resolve()
    if output.exists():
        raise FileExistsError(f"dataset output must not exist: {output}")
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    records = _records()
    tokenizer = RWKVTokenizer()
    samples = [_sample(source, tokenizer) for source in records]
    by_split = {
        split: [source for source in records if source["split"] == split]
        for split in ("train", "dev", "sealed")
    }
    sample_by_source = {sample["source_id"]: sample for sample in samples}
    label_counts = {
        split: dict(
            sorted(
                Counter(
                    source["payload"]["selected_operation"]
                    for source in selected
                ).items()
            )
        )
        for split, selected in by_split.items()
    }
    expected_counts = {
        "train": {label: 12 for label in NETWORK_EXACT_TOOL_LABELS},
        "dev": {label: 4 for label in NETWORK_EXACT_TOOL_LABELS},
        "sealed": {label: 4 for label in NETWORK_EXACT_TOOL_LABELS},
    }
    if len(records) != 500 or label_counts != expected_counts:
        raise RuntimeError("preregistered Selector row or class counts changed")
    sequence_groups: dict[str, list[dict[str, Any]]] = {}
    for source in records:
        sequence_groups.setdefault(source["sequence_id"], []).append(source)
    if len(sequence_groups) != 250 or any(
        [row["sequence_position"] for row in group] != [0, 1]
        or len({row["split"] for row in group}) != 1
        for group in sequence_groups.values()
    ):
        raise RuntimeError("Selector sequence continuity or split isolation changed")
    similarity = {
        "algorithm": "utf8-byte-5gram-cosine.v1",
        "fields": ["stage_objective", "stage_role", "progress", "eligible_labels"],
        "train_dev": _maximum_similarity(by_split["train"], by_split["dev"]),
        "train_sealed": _maximum_similarity(by_split["train"], by_split["sealed"]),
        "dev_sealed": _maximum_similarity(by_split["dev"], by_split["sealed"]),
        "threshold_exclusive": 0.95,
    }
    if any(
        similarity[name]["maximum"] >= 0.95
        for name in ("train_dev", "train_sealed", "dev_sealed")
    ):
        raise RuntimeError(f"Selector split similarity threshold failed: {similarity}")

    pending = output.with_name(output.name + f".pending.{os.getpid()}")
    pending.mkdir()
    sealed_directory = pending / "sealed"
    sealed_directory.mkdir()
    public_sources = by_split["train"] + by_split["dev"]
    public_samples = [sample_by_source[row["source_id"]] for row in public_sources]
    sealed_sources = by_split["sealed"]
    sealed_samples = [sample_by_source[row["source_id"]] for row in sealed_sources]

    def sequence_rows(selected: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
        selected_ids = {row["source_id"] for row in selected}
        return [
            {
                "schema_version": SEQUENCE_SCHEMA,
                "dataset_id": DATASET_ID,
                "sequence_id": sequence_id,
                "split": group[0]["split"],
                "source_ids": [row["source_id"] for row in group],
                "sample_ids": [sample_by_source[row["source_id"]]["sample_id"] for row in group],
                "positions": [0, 1],
                "state_reset_before_position": [True, False],
            }
            for sequence_id, group in sorted(sequence_groups.items())
            if group[0]["source_id"] in selected_ids
        ]

    _write_jsonl(pending / "source_registry.jsonl", public_sources)
    _write_jsonl(pending / "sample_index.jsonl", public_samples)
    _write_jsonl(pending / "sequence_registry.jsonl", sequence_rows(public_sources))
    _write_jsonl(sealed_directory / "source_registry.jsonl", sealed_sources)
    _write_jsonl(sealed_directory / "sample_index.jsonl", sealed_samples)
    _write_jsonl(sealed_directory / "sequence_registry.jsonl", sequence_rows(sealed_sources))
    (pending / "README.md").write_text(
        "# G1J Selector persistent Head v2 dataset\n\n"
        "Source: deterministic production-contract fixtures generated by "
        "`scripts/generate_g1j_selector_persistent_head_v2.py`.\n\n"
        "Version: 2. Purpose: train one zero-State 25-class Selector Head from "
        "step-revision-local persistent causal sequences. Generation is frozen "
        "by the experiment preregistration; sealed rows are stored separately "
        "and are not read during feature extraction or training.\n",
        encoding="utf-8",
    )
    files = {}
    for path in sorted(item for item in pending.rglob("*") if item.is_file()):
        files[str(path.relative_to(pending))] = _file_record(path)
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "dataset_id": DATASET_ID,
        "dataset_version": DATASET_VERSION,
        "purpose": "Train the sole G1J Selector Head on serving-parity persistent causal sequences.",
        "source": {
            "kind": "deterministic_production_contract_fixtures",
            "generator_path": "scripts/generate_g1j_selector_persistent_head_v2.py",
            "generator_sha256": _sha256(Path(__file__).resolve()),
            "preregistration_path": "data/experiments/RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904/PREREGISTRATION.md",
        },
        "protocol": {
            "input_schema_version": selector_intent.INPUT_SCHEMA_VERSION,
            "trajectory_mode": TRAJECTORY_MODE,
            "labels": list(NETWORK_EXACT_TOOL_LABELS),
            "operation_cycle": list(OPERATION_CYCLE),
        },
        "split": {
            "unit": "semantic_variant",
            "train_variants": list(range(6)),
            "dev_variants": [6, 7],
            "sealed_variants": [8, 9],
            "sequence_cross_split_count": 0,
        },
        "counts": {
            "rows": 500,
            "train": 300,
            "dev": 100,
            "sealed": 100,
            "sequences": 250,
            "train_sequences": 150,
            "dev_sequences": 50,
            "sealed_sequences": 50,
            "sequence_length_histogram": {"2": 250},
        },
        "label_counts": label_counts,
        "similarity": similarity,
        "token_counts": {
            "maximum_prompt_tokens": max(sample["prompt_tokens"] for sample in samples),
            "maximum_target_tokens": max(sample["target_tokens"] for sample in samples),
        },
        "files": files,
        "status": "frozen",
    }
    (pending / "manifest.json").write_bytes(_json_bytes(manifest))
    os.replace(pending, output)
    print(output)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


if __name__ == "__main__":
    generate(parse_args().output)
