#!/usr/bin/env python3
"""Build the auditable candidate pool for the 2.9B exact-tool Selector.

This builder never asks a model for labels.  It accepts only RWKV calls that can
be linked to successful Harness actions in a fully externally-accepted run, plus
byte-exact accepted final boundaries.  Formal train/dev/test files are emitted
only when every frozen class has at least 30 test examples.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from rwkv_lh.exact_tool_selector.protocol import (
    EXACT_TOOL_LABELS,
    SelectorInput,
    SelectorProgress,
    canonical_digest,
    selector_menu_digest,
    selector_tool_menu,
    validate_label,
)
from rwkv_lh.model_io import ModelIOError, parse_model_command

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENTS = ROOT / "data" / "experiments"
DEFAULT_OUTPUT = ROOT / "data" / "datasets" / "rwkv_lh_exact_tool_selector_v1"
DATASET_SCHEMA = "rwkv-lh.exact-tool-selector-dataset.v1"
ROW_SCHEMA = "rwkv-lh.exact-tool-selector-row.v1"
SOURCE_SCHEMA = "rwkv-lh.exact-tool-selector-sources.v1"
DEDUP_ALGORITHM = "utf8-byte-5gram-cosine.v1"
DEDUP_THRESHOLD = 0.95
MIN_TEST_PER_CLASS = 30
README_TEXT = """# RWKV-LH Exact-Tool Selector v1\n\nThis directory is a candidate pool, not a frozen training dataset.\n\n- Labels come only from successful RWKV-authority Harness actions in fully\n  accepted runs or byte-exact accepted final boundaries. Atom-graph and\n  pre-ensemble direct-action records use separate fail-closed source adapters.\n- Direct-action rows require an exact raw-generation/request/decision/action\n  join and are rejected if order ensemble or controller semantic synthesis was\n  used.\n- Raw RWKV output is retained with its UTF-8 SHA-256 and is never rewritten.\n- The 20-class input contains tool names/descriptions, never parameter schemas.\n- `coverage.json` is authoritative. Training is forbidden while\n  `eligible_to_freeze=false`; in that state no train/dev/test files are emitted.\n- Duplicate filtering is class-conditional. Cross-label near neighbors are\n  retained because they represent causal state boundaries.\n\nBuild the candidate inventory:\n\n```text\npython /home/chase/GitHub/RWKV-LH/scripts/build_exact_tool_selector_dataset_v1.py\n```\n\n`--freeze` fails closed until every class has at least 30 test rows.\n"""

# Newest compatible protocol first so cross-round duplicates retain the latest
# causal record.  INVALID/interrupted source roots are deliberately absent.
# Atom-graph sources expose an explicit RWKV-authority outcome contract.  The
# older direct-action sources expose the same facts as model_call_accepted ->
# action_finished causal pairs.  Keep the adapters separate: accepting an old
# direct-action row through the atom adapter would silently weaken provenance.
ATOM_SOURCE_ROOTS = (
    EXPERIMENTS / "Round165_minimal_contract_loop_full90_20260824",
    EXPERIMENTS / "Round164_minimal_contract_loop_canary_20260824",
    EXPERIMENTS / "Round162_typed_contract_full90_20260823",
    EXPERIMENTS / "Round161_typed_contract_defect_canary_20260823",
    EXPERIMENTS / "Round160_terra_fp_trap_M04_M08_20260823",
    EXPERIMENTS / "Round160_sol_fp_trap_M04_M08_20260823",
    EXPERIMENTS / "Round158_contract_graph_full90_20260823",
    EXPERIMENTS / "Round157_frozen_contract_mechanical_veto_20260823",
    EXPERIMENTS / "Round155_mandatory_contract_parent_exclusive_canary_20260823",
    EXPERIMENTS / "Round154_contract_graph_result_only_canary_20260823",
    EXPERIMENTS / "Round153_split_reasoning_literal_review_B04_20260823",
)

# These are the newest fully completed single-RWKV direct-action runs before
# the order-ensemble experiments.  The adapter below rejects an ensemble field
# even if a future source is accidentally added here.
DIRECT_ACTION_SOURCE_ROOTS = (
    EXPERIMENTS / "Round129_v19p2_full90",
    EXPERIMENTS / "Round128_v19p3_full90",
    EXPERIMENTS / "Round127_v19p2_full90",
    EXPERIMENTS / "Round122_v18p3_full90",
    EXPERIMENTS / "Round121_v18p2_full90",
    EXPERIMENTS / "Round120_v18p1_full90",
    EXPERIMENTS / "Round119_v18p0_full90",
)

SOURCE_ADAPTER_ROOTS = (
    *((path, "atom_graph") for path in ATOM_SOURCE_ROOTS),
    *((path, "direct_action") for path in DIRECT_ACTION_SOURCE_ROOTS),
)
SOURCE_ROOTS = tuple(path for path, _adapter in SOURCE_ADAPTER_ROOTS)


@dataclass(frozen=True)
class ParsedGeneration:
    trace_index: int
    raw_output: str
    raw_output_sha256: str
    operation: str
    arguments: Mapping[str, Any]
    request_id: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise TypeError(f"{path} must contain a JSON object")
    return dict(value)


def _load_array(path: Path) -> list[Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, list):
        raise TypeError(f"{path} must contain a JSON array")
    return value


def _strict_case_reasons(audit: Mapping[str, Any]) -> tuple[str, ...]:
    reasons: list[str] = []
    if audit.get("schema_version") != "rwkv-e2e.case-audit.v1":
        reasons.append("unsupported_audit_schema")
    for key in (
        "passed",
        "agent_completed",
        "external_passed",
        "final_output_nonempty",
    ):
        if audit.get(key) is not True:
            reasons.append(f"case_{key}_not_true")
    boundary = audit.get("output_non_intervention")
    if not isinstance(boundary, Mapping):
        reasons.append("missing_output_non_intervention")
    elif boundary.get("byte_exact_match") is not True:
        reasons.append("delivered_final_not_byte_exact")
    return tuple(reasons)


def _causal_records(audit: Mapping[str, Any]) -> list[dict[str, Any]]:
    run_state = audit.get("run_state")
    records = (
        run_state.get("causal_records") if isinstance(run_state, Mapping) else None
    )
    if not isinstance(records, Mapping):
        return []
    selected = [dict(item) for item in records.values() if isinstance(item, Mapping)]
    return sorted(selected, key=lambda item: int(item.get("sequence") or 0))


def _atom_definitions(
    records: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    definitions: dict[str, dict[str, Any]] = {}
    for record in records:
        if record.get("event_type") != "contract_graph_patch_committed":
            continue
        payload = record.get("payload")
        patch = payload.get("patch") if isinstance(payload, Mapping) else None
        nodes = patch.get("new_nodes") if isinstance(patch, Mapping) else None
        if not isinstance(nodes, list):
            continue
        for node in nodes:
            atom = node.get("atom") if isinstance(node, Mapping) else None
            if not isinstance(atom, Mapping):
                continue
            atom_id = str(atom.get("atom_id") or "")
            if not atom_id:
                continue
            normalized = dict(atom)
            existing = definitions.get(atom_id)
            if existing is not None and canonical_digest(existing) != canonical_digest(
                normalized
            ):
                raise ValueError(f"atom definition changed within one run: {atom_id}")
            definitions[atom_id] = normalized
    return definitions


def _outcome_records(records: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        dict(record)
        for record in records
        if record.get("event_type") == "atom_outcome_committed"
    ]


def _parsed_generations(trace: Sequence[Any]) -> dict[str, list[ParsedGeneration]]:
    selected: dict[str, list[ParsedGeneration]] = {}
    for index, raw_record in enumerate(trace):
        if not isinstance(raw_record, Mapping):
            continue
        if raw_record.get("type") != "model_session_generation_returned":
            continue
        atom_id = str(raw_record.get("atom_id") or "")
        raw_output = raw_record.get("raw_output")
        if not atom_id or not isinstance(raw_output, str):
            continue
        try:
            command = parse_model_command(raw_output)
        except ModelIOError:
            continue
        selected.setdefault(atom_id, []).append(
            ParsedGeneration(
                trace_index=index,
                raw_output=raw_output,
                raw_output_sha256=_sha256_bytes(raw_output.encode("utf-8")),
                operation=command.name,
                arguments=dict(command.arguments),
                request_id=str(raw_record.get("request_id") or ""),
            )
        )
    return selected


def _parsed_generations_by_request(
    trace: Sequence[Any],
) -> dict[str, list[ParsedGeneration]]:
    """Index byte-exact direct-lane generations without inventing atom IDs."""

    selected: dict[str, list[ParsedGeneration]] = {}
    for index, raw_record in enumerate(trace):
        if not isinstance(raw_record, Mapping):
            continue
        if raw_record.get("type") != "model_session_generation_returned":
            continue
        request_id = str(raw_record.get("request_id") or "")
        raw_output = raw_record.get("raw_output")
        if not request_id or not isinstance(raw_output, str):
            continue
        try:
            command = parse_model_command(raw_output)
        except ModelIOError:
            continue
        selected.setdefault(request_id, []).append(
            ParsedGeneration(
                trace_index=index,
                raw_output=raw_output,
                raw_output_sha256=_sha256_bytes(raw_output.encode("utf-8")),
                operation=command.name,
                arguments=dict(command.arguments),
                request_id=request_id,
            )
        )
    return selected


def _split_for_family(family_id: str) -> str:
    bucket = int(hashlib.sha256(family_id.encode("utf-8")).hexdigest()[:8], 16) % 10
    if bucket == 0:
        return "dev"
    if bucket == 1:
        return "test"
    return "train"


def _byte_ngrams(text: str, n: int = 5) -> Counter[bytes]:
    raw = text.encode("utf-8")
    if len(raw) < n:
        return Counter({raw: 1})
    return Counter(raw[index : index + n] for index in range(len(raw) - n + 1))


def _cosine(left: Counter[bytes], right: Counter[bytes]) -> float:
    common = left.keys() & right.keys()
    numerator = sum(left[item] * right[item] for item in common)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)


def _deduplicate(
    rows: Sequence[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    kept: list[dict[str, Any]] = []
    vectors: list[Counter[bytes]] = []
    duplicates: list[dict[str, Any]] = []
    cross_label_neighbors: list[dict[str, Any]] = []
    for row in rows:
        selector_input = row["selector_input"]
        semantic_projection = {
            key: selector_input[key]
            for key in (
                "task_request",
                "stage_objective",
                "stage_role",
                "progress",
            )
        }
        dedup_text = json.dumps(
            semantic_projection,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        vector = _byte_ngrams(dedup_text)
        match_index = -1
        match_score = 0.0
        cross_label_match_index = -1
        cross_label_match_score = 0.0
        for index, existing in enumerate(vectors):
            score = _cosine(vector, existing)
            if row["label"] == kept[index]["label"] and score >= DEDUP_THRESHOLD:
                match_index = index
                match_score = score
                break
            if (
                row["label"] != kept[index]["label"]
                and score >= DEDUP_THRESHOLD
                and score > cross_label_match_score
            ):
                cross_label_match_index = index
                cross_label_match_score = score
        if match_index >= 0:
            duplicates.append(
                {
                    "dropped_row_id": row["row_id"],
                    "kept_row_id": kept[match_index]["row_id"],
                    "dropped_label": row["label"],
                    "kept_label": kept[match_index]["label"],
                    "class_conditional": True,
                    "similarity": round(match_score, 12),
                    "algorithm": DEDUP_ALGORITHM,
                    "threshold": DEDUP_THRESHOLD,
                }
            )
            continue
        if cross_label_match_index >= 0:
            cross_label_neighbors.append(
                {
                    "row_id": row["row_id"],
                    "row_label": row["label"],
                    "neighbor_row_id": kept[cross_label_match_index]["row_id"],
                    "neighbor_label": kept[cross_label_match_index]["label"],
                    "similarity": round(cross_label_match_score, 12),
                    "algorithm": DEDUP_ALGORITHM,
                    "threshold": DEDUP_THRESHOLD,
                    "retained_as_causal_boundary_contrast": True,
                }
            )
        kept.append(row)
        vectors.append(vector)
    return kept, duplicates, cross_label_neighbors


def _find_generation(
    generations: Sequence[ParsedGeneration],
    operation: str,
    *,
    after_trace_index: int,
) -> ParsedGeneration | None:
    return next(
        (
            item
            for item in generations
            if item.trace_index > after_trace_index and item.operation == operation
        ),
        None,
    )


def _row(
    *,
    audit: Mapping[str, Any],
    source_root: Path,
    audit_path: Path,
    outcome_record: Mapping[str, Any],
    atom: Mapping[str, Any],
    generation: ParsedGeneration,
    label: str,
    progress: SelectorProgress,
    evidence: Mapping[str, Any],
    trajectory_step_index: int,
) -> dict[str, Any]:
    task_id = str(audit.get("task_id") or "")
    selector_input = SelectorInput.create(
        task_request=str(audit.get("user_request") or ""),
        stage_objective=str(atom.get("objective") or ""),
        stage_role=str(atom.get("role") or "work"),
        progress=progress,
    )
    relative_audit = audit_path.relative_to(ROOT).as_posix()
    identity = {
        "source_audit": relative_audit,
        "source_event_id": str(outcome_record.get("event_id") or ""),
        "source_trace_index": generation.trace_index,
        "label": validate_label(label),
    }
    trajectory_id = f"TRAJ-{canonical_digest({'source_audit': relative_audit})[:24]}"
    return {
        "schema_version": ROW_SCHEMA,
        "row_id": f"SEL-{canonical_digest(identity)[:24]}",
        "family_id": task_id,
        "trajectory_id": trajectory_id,
        "trajectory_step_index": trajectory_step_index,
        "split": _split_for_family(task_id),
        "label": label,
        "selector_input": selector_input.to_dict(),
        "selector_input_rendered": selector_input.render(),
        "selector_bootstrap_rendered": selector_input.render_bootstrap(),
        "selector_step_rendered": selector_input.render_step(),
        "selector_input_sha256": _sha256_bytes(selector_input.render().encode("utf-8")),
        "source": {
            "run": source_root.name,
            "audit": relative_audit,
            "outcome_event_id": str(outcome_record.get("event_id") or ""),
            "atom_id": str(atom.get("atom_id") or ""),
            "trace_index": generation.trace_index,
            "request_id": generation.request_id,
            "raw_output": generation.raw_output,
            "raw_output_sha256": generation.raw_output_sha256,
            "raw_output_modified": False,
            "label_evidence": dict(evidence),
        },
    }


def _case_rows(
    source_root: Path,
    audit_path: Path,
    audit: Mapping[str, Any],
    trace: Sequence[Any],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    exclusions: Counter[str] = Counter()
    records = _causal_records(audit)
    definitions = _atom_definitions(records)
    outcomes = _outcome_records(records)
    generations_by_atom = _parsed_generations(trace)
    result: list[dict[str, Any]] = []
    prior_succeeded: list[str] = []
    prior_failed: list[str] = []
    prior_rejections = 0
    completed_stage_count = 0
    action_index = 0

    for record in outcomes:
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            exclusions["outcome_missing_payload"] += 1
            continue
        outcome = payload.get("outcome")
        atom_id = str(payload.get("atom_id") or "")
        atom = definitions.get(atom_id)
        if not isinstance(outcome, Mapping) or atom is None:
            exclusions["outcome_missing_atom_definition"] += 1
            continue
        if (
            outcome.get("status") != "completed"
            or payload.get("rwkv_action_authority") is not True
            or payload.get("supervisor_action_executed") is not False
            or payload.get("controller_rewritten") is not False
        ):
            exclusions["outcome_not_strict_rwkv_authority"] += 1
            continue
        generations = generations_by_atom.get(atom_id, [])
        trace_cursor = -1
        actions = outcome.get("actions")
        if not isinstance(actions, list):
            exclusions["outcome_actions_not_array"] += 1
            continue
        for action in actions:
            if not isinstance(action, Mapping):
                exclusions["action_not_object"] += 1
                continue
            operation = str(action.get("operation") or "")
            generation = _find_generation(
                generations,
                operation,
                after_trace_index=trace_cursor,
            )
            if generation is None:
                exclusions["action_raw_generation_not_linked"] += 1
                continue
            trace_cursor = generation.trace_index
            status = str(action.get("status") or "")
            result_value = action.get("result")
            succeeded = (
                status == "succeeded"
                and isinstance(result_value, Mapping)
                and result_value.get("success") is True
            )
            if succeeded and operation in EXACT_TOOL_LABELS:
                progress = SelectorProgress(
                    completed_stage_count=completed_stage_count,
                    action_index=action_index,
                    succeeded_operations=tuple(prior_succeeded[-12:]),
                    failed_operations=tuple(prior_failed[-12:]),
                    protocol_rejection_count=prior_rejections,
                )
                result.append(
                    _row(
                        audit=audit,
                        source_root=source_root,
                        audit_path=audit_path,
                        outcome_record=record,
                        atom=atom,
                        generation=generation,
                        label=operation,
                        progress=progress,
                        evidence={
                            "kind": "successful_harness_action_in_accepted_run",
                            "action_id": str(action.get("action_id") or ""),
                            "action_status": status,
                            "result_success": True,
                            "case_external_passed": True,
                            "rwkv_action_authority": True,
                            "supervisor_action_executed": False,
                            "controller_rewritten": False,
                        },
                        trajectory_step_index=len(result),
                    )
                )
                prior_succeeded.append(operation)
            else:
                prior_failed.append(operation)
            action_index += 1

        final_generation = _find_generation(
            generations,
            "final_answer",
            after_trace_index=trace_cursor,
        )
        candidate_output = outcome.get("candidate_output")
        candidate_sha = str(outcome.get("candidate_output_sha256") or "")
        if (
            final_generation is not None
            and isinstance(candidate_output, str)
            and final_generation.arguments.get("text") == candidate_output
            and _sha256_bytes(candidate_output.encode("utf-8")) == candidate_sha
        ):
            progress = SelectorProgress(
                completed_stage_count=completed_stage_count,
                action_index=action_index,
                succeeded_operations=tuple(prior_succeeded[-12:]),
                failed_operations=tuple(prior_failed[-12:]),
                protocol_rejection_count=prior_rejections,
            )
            result.append(
                _row(
                    audit=audit,
                    source_root=source_root,
                    audit_path=audit_path,
                    outcome_record=record,
                    atom=atom,
                    generation=final_generation,
                    label="final_answer",
                    progress=progress,
                    evidence={
                        "kind": "byte_exact_accepted_atom_final_boundary",
                        "candidate_output_sha256": candidate_sha,
                        "case_external_passed": True,
                        "rwkv_action_authority": True,
                        "supervisor_action_executed": False,
                        "controller_rewritten": False,
                    },
                    trajectory_step_index=len(result),
                )
            )
        else:
            exclusions["final_raw_generation_not_byte_exact"] += 1
        prior_rejections += int(outcome.get("protocol_rejections") or 0)
        completed_stage_count += 1
    return result, exclusions


def _direct_case_rows(
    source_root: Path,
    audit_path: Path,
    audit: Mapping[str, Any],
    trace: Sequence[Any],
) -> tuple[list[dict[str, Any]], Counter[str]]:
    """Extract strict pre-ensemble direct-action causal pairs.

    This is intentionally not a compatibility fallback.  Every emitted action
    must join one accepted raw generation, one non-semantic argument
    normalization record, and one successful Harness result by both decision
    and request identity.  Final rows additionally require the audit's
    byte-exact delivery boundary.
    """

    exclusions: Counter[str] = Counter()
    records = _causal_records(audit)
    start_records = [
        record for record in records if record.get("event_type") == "run_started"
    ]
    if len(start_records) != 1:
        exclusions["direct_run_start_not_unique"] += 1
        return [], exclusions
    start_payload = start_records[0].get("payload")
    if not isinstance(start_payload, Mapping) or (
        start_payload.get("architecture") != "single-rwkv-direct-action.v1"
        or start_payload.get("online_task_graph") is not False
        or start_payload.get("reviewer") is not False
    ):
        exclusions["direct_run_architecture_not_strict"] += 1
        return [], exclusions
    terminal_records = [
        record for record in records if record.get("event_type") == "run_completed"
    ]
    terminal_payload = (
        terminal_records[0].get("payload") if len(terminal_records) == 1 else None
    )
    if not isinstance(terminal_payload, Mapping) or (
        terminal_payload.get("controller_rewritten") is not False
        or terminal_payload.get("output_source") != "rwkv_explicit_final_answer_text"
    ):
        exclusions["direct_run_terminal_not_raw_rwkv"] += 1
        return [], exclusions

    generations = _parsed_generations_by_request(trace)
    accepted_calls: dict[str, tuple[Mapping[str, Any], ParsedGeneration]] = {}
    for record in records:
        if record.get("event_type") != "model_call_accepted":
            continue
        payload = record.get("payload")
        if not isinstance(payload, Mapping):
            exclusions["direct_call_missing_payload"] += 1
            continue
        # Historical order-ensemble data selected among multiple RWKV outputs.
        # It remains preserved in its source audit but is not a raw single-call
        # label source for this dataset.
        if "order_ensemble" in payload:
            exclusions["direct_call_used_order_ensemble"] += 1
            continue
        decision = payload.get("decision")
        if not isinstance(decision, Mapping) or decision.get("accepted") is not True:
            exclusions["direct_call_not_accepted"] += 1
            continue
        decision_id = str(payload.get("decision_id") or "")
        request_id = str(payload.get("request_id") or "")
        raw_output = decision.get("raw_output")
        operation = str(payload.get("operation") or "")
        if (
            not decision_id
            or not request_id
            or not isinstance(raw_output, str)
            or str(decision.get("request_id") or "") != request_id
            or str(decision.get("decision_id") or "") != decision_id
        ):
            exclusions["direct_call_identity_incomplete"] += 1
            continue
        matches = [
            generation
            for generation in generations.get(request_id, [])
            if generation.raw_output == raw_output and generation.operation == operation
        ]
        if len(matches) != 1:
            exclusions["direct_call_raw_generation_not_unique"] += 1
            continue
        if decision_id in accepted_calls:
            exclusions["direct_call_duplicate_decision_id"] += 1
            continue
        accepted_calls[decision_id] = (payload, matches[0])

    result: list[dict[str, Any]] = []
    prior_succeeded: list[str] = []
    prior_failed: list[str] = []
    protocol_rejections = 0
    action_index = 0
    direct_atom = {
        "atom_id": "LANE:ACTION",
        "objective": str(audit.get("user_request") or ""),
        "role": "work",
    }
    if not direct_atom["objective"]:
        exclusions["direct_case_missing_user_request"] += 1
        return [], exclusions

    for record in records:
        event_type = str(record.get("event_type") or "")
        if event_type in {"model_call_rejected", "model_protocol_rejected"}:
            protocol_rejections += 1
            continue
        if event_type == "action_finished":
            payload = record.get("payload")
            action = payload.get("action") if isinstance(payload, Mapping) else None
            if not isinstance(action, Mapping):
                exclusions["direct_action_missing_payload"] += 1
                continue
            operation = str(action.get("action_type") or "")
            call_pair = accepted_calls.get(str(action.get("decision_id") or ""))
            action_result = action.get("result")
            succeeded = (
                action.get("status") == "succeeded"
                and isinstance(action_result, Mapping)
                and action_result.get("success") is True
            )
            if call_pair is None:
                exclusions["direct_action_missing_accepted_call"] += 1
            else:
                call, generation = call_pair
                normalization = call.get("argument_normalization")
                raw_action = (
                    normalization.get("raw_action")
                    if isinstance(normalization, Mapping)
                    else None
                )
                normalized_action = (
                    normalization.get("normalized_action")
                    if isinstance(normalization, Mapping)
                    else None
                )
                identity_matches = (
                    str(action.get("request_id") or "")
                    == str(call.get("request_id") or "")
                    and operation == str(call.get("operation") or "")
                    and isinstance(raw_action, Mapping)
                    and raw_action.get("action_type") == operation
                    and isinstance(normalized_action, Mapping)
                    and normalized_action.get("action_type") == operation
                    and normalization.get("controller_semantic_fields_generated")
                    is False
                )
                if not identity_matches:
                    exclusions["direct_action_identity_or_normalization_mismatch"] += 1
                elif succeeded and operation in EXACT_TOOL_LABELS:
                    progress = SelectorProgress(
                        completed_stage_count=0,
                        action_index=action_index,
                        succeeded_operations=tuple(prior_succeeded[-12:]),
                        failed_operations=tuple(prior_failed[-12:]),
                        protocol_rejection_count=protocol_rejections,
                    )
                    result.append(
                        _row(
                            audit=audit,
                            source_root=source_root,
                            audit_path=audit_path,
                            outcome_record=record,
                            atom=direct_atom,
                            generation=generation,
                            label=operation,
                            progress=progress,
                            evidence={
                                "kind": (
                                    "successful_direct_harness_action_in_accepted_run"
                                ),
                                "action_id": str(action.get("action_id") or ""),
                                "action_status": "succeeded",
                                "result_success": True,
                                "case_external_passed": True,
                                "single_rwkv_direct_action": True,
                                "order_ensemble_used": False,
                                "controller_semantic_fields_generated": False,
                                "raw_generation_trace_joined": True,
                            },
                            trajectory_step_index=len(result),
                        )
                    )
                    prior_succeeded.append(operation)
                else:
                    prior_failed.append(operation)
            action_index += 1
            continue

        if event_type != "model_call_accepted":
            continue
        payload = record.get("payload")
        if (
            not isinstance(payload, Mapping)
            or payload.get("operation") != "final_answer"
        ):
            continue
        call_pair = accepted_calls.get(str(payload.get("decision_id") or ""))
        boundary = audit.get("output_non_intervention")
        if call_pair is None or not isinstance(boundary, Mapping):
            exclusions["direct_final_missing_accepted_call_or_boundary"] += 1
            continue
        _call, generation = call_pair
        delivered = boundary.get("delivered_final_output")
        decoded = boundary.get("decoded_final_answer_text")
        if (
            boundary.get("byte_exact_match") is not True
            or boundary.get("raw_rwkv_final_output") != generation.raw_output
            or not isinstance(delivered, str)
            or decoded != delivered
            or generation.arguments.get("text") != delivered
            or terminal_payload.get("final_output") != delivered
            or terminal_payload.get("final_output_sha256")
            != _sha256_bytes(delivered.encode("utf-8"))
        ):
            exclusions["direct_final_not_byte_exact"] += 1
            continue
        progress = SelectorProgress(
            completed_stage_count=0,
            action_index=action_index,
            succeeded_operations=tuple(prior_succeeded[-12:]),
            failed_operations=tuple(prior_failed[-12:]),
            protocol_rejection_count=protocol_rejections,
        )
        result.append(
            _row(
                audit=audit,
                source_root=source_root,
                audit_path=audit_path,
                outcome_record=record,
                atom=direct_atom,
                generation=generation,
                label="final_answer",
                progress=progress,
                evidence={
                    "kind": "byte_exact_accepted_direct_final_boundary",
                    "case_external_passed": True,
                    "single_rwkv_direct_action": True,
                    "order_ensemble_used": False,
                    "controller_rewritten": False,
                    "raw_generation_trace_joined": True,
                },
                trajectory_step_index=len(result),
            )
        )
    return result, exclusions


def _jsonl_bytes(rows: Iterable[Mapping[str, Any]]) -> bytes:
    return (
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for row in rows
        )
    ).encode("utf-8")


def _write_bytes(path: Path, value: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(value)


def _counts(
    rows: Sequence[Mapping[str, Any]], *, split: str | None = None
) -> dict[str, int]:
    selected = [row for row in rows if split is None or row.get("split") == split]
    counts = Counter(str(row.get("label") or "") for row in selected)
    return {label: counts[label] for label in EXACT_TOOL_LABELS}


def build(output_dir: Path, *, freeze: bool) -> tuple[dict[str, Any], bool]:
    source_cases: list[dict[str, Any]] = []
    source_runs: list[dict[str, Any]] = []
    exclusions: Counter[str] = Counter()
    rows: list[dict[str, Any]] = []
    for source_root, source_adapter in SOURCE_ADAPTER_ROOTS:
        results_path = source_root / "results.json"
        if not source_root.is_dir() or not results_path.is_file():
            exclusions["source_root_missing_results"] += 1
            continue
        source_runs.append(
            {
                "run": source_root.name,
                "adapter": source_adapter,
                "results": results_path.relative_to(ROOT).as_posix(),
                "results_sha256": _file_sha256(results_path),
            }
        )
        result_index = {
            str(item.get("task_id") or ""): item
            for item in _load_object(results_path).get("results", [])
            if isinstance(item, Mapping)
        }
        for task_id, result in sorted(result_index.items()):
            relative_audit = result.get("audit")
            if not isinstance(relative_audit, str) or not relative_audit:
                exclusions["result_missing_audit_path"] += 1
                continue
            audit_path = source_root / relative_audit
            if not audit_path.is_file():
                exclusions["audit_file_missing"] += 1
                continue
            audit = _load_object(audit_path)
            reasons = _strict_case_reasons(audit)
            if reasons:
                exclusions.update(reasons)
                continue
            trace_path = audit_path.with_name("model_trace.json")
            if not trace_path.is_file():
                exclusions["model_trace_missing"] += 1
                continue
            trace = _load_array(trace_path)
            if source_adapter == "atom_graph":
                case_rows, case_exclusions = _case_rows(
                    source_root,
                    audit_path,
                    audit,
                    trace,
                )
            elif source_adapter == "direct_action":
                case_rows, case_exclusions = _direct_case_rows(
                    source_root,
                    audit_path,
                    audit,
                    trace,
                )
            else:  # pragma: no cover - frozen in SOURCE_ADAPTER_ROOTS
                raise AssertionError(f"unknown source adapter: {source_adapter}")
            exclusions.update(case_exclusions)
            if not case_rows:
                exclusions["strict_case_produced_no_rows"] += 1
                continue
            rows.extend(case_rows)
            source_cases.append(
                {
                    "run": source_root.name,
                    "adapter": source_adapter,
                    "task_id": task_id,
                    "audit": audit_path.relative_to(ROOT).as_posix(),
                    "audit_sha256": _file_sha256(audit_path),
                    "model_trace": trace_path.relative_to(ROOT).as_posix(),
                    "model_trace_sha256": _file_sha256(trace_path),
                    "row_count_before_dedup": len(case_rows),
                }
            )

    deduplicated, duplicates, cross_label_neighbors = _deduplicate(rows)
    train_counts = _counts(deduplicated, split="train")
    dev_counts = _counts(deduplicated, split="dev")
    test_counts = _counts(deduplicated, split="test")
    coverage_gaps = {
        label: {
            "train": train_counts[label],
            "dev": dev_counts[label],
            "test": test_counts[label],
            "required_test": MIN_TEST_PER_CLASS,
            "missing_test": max(0, MIN_TEST_PER_CLASS - test_counts[label]),
        }
        for label in EXACT_TOOL_LABELS
        if test_counts[label] < MIN_TEST_PER_CLASS
    }
    eligible = not coverage_gaps

    source_manifest = {
        "schema_version": SOURCE_SCHEMA,
        "source": (
            "RWKV-LH causal audits from explicitly registered atom-graph and "
            "pre-ensemble direct-action formal/canary roots"
        ),
        "version": "2026-08-28-compatible-roots-v2",
        "purpose": "exact next-tool labels for the independent 2.9B Selector",
        "generation": "scripts/build_exact_tool_selector_dataset_v1.py",
        "generator": {
            "path": "scripts/build_exact_tool_selector_dataset_v1.py",
            "sha256": _file_sha256(Path(__file__).resolve()),
        },
        "label_policy": (
            "successful RWKV-authority Harness action in an externally accepted run; "
            "or byte-exact accepted atom final boundary; never model self-label"
        ),
        "source_roots": [
            {
                "path": path.relative_to(ROOT).as_posix(),
                "adapter": adapter,
            }
            for path, adapter in SOURCE_ADAPTER_ROOTS
        ],
        "source_runs": source_runs,
        "cases": source_cases,
    }
    coverage = {
        "schema_version": DATASET_SCHEMA,
        "status": "eligible_to_freeze" if eligible else "candidate_unfrozen",
        "eligible_to_freeze": eligible,
        "formal_files_emitted": bool(freeze and eligible),
        "rows_before_dedup": len(rows),
        "rows_after_dedup": len(deduplicated),
        "duplicate_rows": len(duplicates),
        "cross_label_near_neighbors_retained": len(cross_label_neighbors),
        "unique_family_count": len({str(row["family_id"]) for row in deduplicated}),
        "class_order": list(EXACT_TOOL_LABELS),
        "all_counts": _counts(deduplicated),
        "train_counts": train_counts,
        "dev_counts": dev_counts,
        "test_counts": test_counts,
        "coverage_gaps": coverage_gaps,
        "minimum_test_per_class": MIN_TEST_PER_CLASS,
        "split_policy": "sha256(family_id) modulo 10: 0=dev, 1=test, 2..9=train",
        "dedup": {
            "algorithm": DEDUP_ALGORITHM,
            "threshold": DEDUP_THRESHOLD,
            "scope": (
                "global over canonical task_request+stage_objective+stage_role+progress "
                "within each label before split emission; cross-label near neighbors "
                "are retained as causal boundary contrasts; the byte-identical frozen "
                "menu is excluded; source priority newest-compatible first"
            ),
        },
        "exclusions": dict(exclusions.most_common()),
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    trajectory_path = output_dir / "trajectories.unfiltered.jsonl"
    candidate_path = output_dir / "candidates.unfrozen.jsonl"
    duplicates_path = output_dir / "duplicates.jsonl"
    cross_label_path = output_dir / "cross_label_near_neighbors.jsonl"
    sources_path = output_dir / "sources.json"
    coverage_path = output_dir / "coverage.json"
    readme_path = output_dir / "README.md"
    _write_bytes(trajectory_path, _jsonl_bytes(rows))
    _write_bytes(candidate_path, _jsonl_bytes(deduplicated))
    _write_bytes(duplicates_path, _jsonl_bytes(duplicates))
    _write_bytes(cross_label_path, _jsonl_bytes(cross_label_neighbors))
    _write_bytes(readme_path, README_TEXT.encode("utf-8"))
    _write_bytes(
        sources_path,
        (
            json.dumps(source_manifest, ensure_ascii=False, indent=2, sort_keys=True)
            + "\n"
        ).encode("utf-8"),
    )
    _write_bytes(
        coverage_path,
        (
            json.dumps(coverage, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
    )

    formal_paths: list[Path] = []
    if freeze and eligible:
        for split in ("train", "dev", "test"):
            path = output_dir / f"{split}.jsonl"
            _write_bytes(
                path,
                _jsonl_bytes(row for row in deduplicated if row["split"] == split),
            )
            formal_paths.append(path)

    artifact_paths = [
        trajectory_path,
        candidate_path,
        duplicates_path,
        cross_label_path,
        sources_path,
        coverage_path,
        readme_path,
        *formal_paths,
    ]
    manifest = {
        "schema_version": DATASET_SCHEMA,
        "dataset": "rwkv_lh_exact_tool_selector_v1",
        "status": coverage["status"],
        "training_authorized": bool(freeze and eligible),
        "source": source_manifest["source"],
        "version": source_manifest["version"],
        "purpose": source_manifest["purpose"],
        "generation": source_manifest["generation"],
        "tool_menu": [dict(item) for item in selector_tool_menu()],
        "tool_menu_digest": selector_menu_digest(),
        "files": {
            path.name: {
                "bytes": path.stat().st_size,
                "sha256": _file_sha256(path),
            }
            for path in artifact_paths
        },
    }
    manifest_path = output_dir / "manifest.json"
    _write_bytes(
        manifest_path,
        (
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        ).encode("utf-8"),
    )
    return manifest, eligible


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--freeze",
        action="store_true",
        help="emit train/dev/test only when every class has at least 30 test rows",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    manifest, eligible = build(output_dir, freeze=bool(args.freeze))
    print(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True))
    if args.freeze and not eligible:
        raise SystemExit(
            "refusing to freeze: coverage.json lists classes below the fixed test minimum"
        )


if __name__ == "__main__":
    main()
