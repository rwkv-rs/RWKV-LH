"""Extract auditable role samples from frozen production checkpoints.

This module is a dataset consumer, not a sixth role protocol. It never runs a
model, invents scenarios, reads benchmark answer keys, or creates formal dataset
versions. Missing observations are exclusions; contradictory evidence rejects
the batch. The CLI publishes immutable candidate/audit artifacts only.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
from typing import Any, Mapping, Sequence

from rwkv_lh.goal_state_protocols import (
    auditor_final, auditor_step_v3, executor_args_v4, finalizer_answer, selector_intent_v4,
)
from rwkv_lh.goal_loop_protocol import action_mutates_root, action_observes_root
from rwkv_lh.model_io import JSON_CALL_STOP_SUFFIXES, parse_model_command_with_trace
from rwkv_lh.schema import ActionStatus, CausalEvent, ModelCheckpoint, RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.token_budget import VOCAB_PATH, tokenizer


SOURCE_REGISTRATION_SCHEMA = "rwkv-lh.role-trace-source-registration.v1"
EXTRACTION_SCHEMA = "rwkv-lh.role-trace-extraction.v1"
ROOT = Path(__file__).resolve().parents[2]
ZERO_SHA = "0" * 64
ROLE_MODULES = {
    "selector_intent": selector_intent_v4,
    "executor_args": executor_args_v4,
    "auditor_step": auditor_step_v3,
    "finalizer_answer": finalizer_answer,
    "auditor_final": auditor_final,
}
REQUIRED_ARTIFACTS = frozenset({"sqlite", "model_trace", "event_log", "state_timeline", "causal_ledger", "run_protocol", "source_tree_manifest"})
CASE_ARTIFACT_PATHS = {
    "sqlite": "state/long_horizon.db", "model_trace": "model_trace.json",
    "event_log": "event_log.json", "state_timeline": "state_timeline.json.gz",
    "causal_ledger": "causal_ledger.json",
}
SOURCE_CODE_PATHS = tuple(sorted({
    *(str(path.relative_to(ROOT)) for path in (ROOT / "rwkv_lh").rglob("*.py")
      if not path.name.startswith("role_trace_")),
    str(VOCAB_PATH.relative_to(ROOT)),
}))


class DatasetIntegrityError(ValueError):
    """Frozen evidence disagrees: no samples from this batch may be published."""


class SampleExcluded(ValueError):
    """A boundary lacks sufficient evidence for a legitimate training label."""

    def __init__(self, message: str, *, review_candidate: Mapping | None = None):
        super().__init__(message)
        self.review_candidate = dict(review_candidate) if review_candidate is not None else None


def _digest(value: bytes | str) -> str:
    return hashlib.sha256(value.encode("utf-8") if isinstance(value, str) else value).hexdigest()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _is_sha(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_frozen_scope(record: Mapping, protocol: Any, source_manifest: Any) -> None:
    from rwkv_lh.stateful_goal_loop import STATEFUL_GOAL_LOOP_ARCHITECTURE

    if not isinstance(protocol, Mapping) or protocol.get("schema_version") != "rwkv-lh.round-run-protocol.v1":
        raise DatasetIntegrityError("source requires the frozen production run protocol")
    if protocol.get("architecture") != STATEFUL_GOAL_LOOP_ARCHITECTURE or protocol.get("round") != record["source_run_id"]:
        raise DatasetIntegrityError("frozen run architecture/round differs from source registration")
    cases = protocol.get("selected_case_ids")
    if not isinstance(cases, list) or len(cases) != len(set(cases)) or protocol.get("selected_case_count") != len(cases) or record["run_id"] not in cases:
        raise DatasetIntegrityError("source case is outside the frozen development selection")
    resources = protocol.get("source_resources")
    if not isinstance(resources, list) or not any(isinstance(item, Mapping) and item.get("role") == "visible_tasks" and item.get("suite") == record["suite"] and _is_sha(item.get("sha256")) for item in resources):
        raise DatasetIntegrityError("source suite lacks a frozen visible development scope")
    # Only metadata are read; the registered resources (especially answer keys)
    # are never opened by the extractor.
    if not isinstance(source_manifest, list) or protocol.get("code", {}).get("source_tree_manifest_sha256") != _digest(_canonical(source_manifest)):
        raise DatasetIntegrityError("frozen source manifest SHA mismatch")
    paths = [item.get("path") for item in source_manifest if isinstance(item, Mapping)]
    if len(paths) != len(source_manifest) or len(paths) != len(set(paths)):
        raise DatasetIntegrityError("frozen source manifest contains duplicate/malformed paths")
    hashes = {item["path"]: item.get("sha256") for item in source_manifest}
    for path in SOURCE_CODE_PATHS:
        if hashes.get(path) != _digest((ROOT / path).read_bytes()):
            raise DatasetIntegrityError(f"source production builder/State implementation differs: {path}")


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise DatasetIntegrityError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _json(data: bytes | str) -> Any:
    try:
        return json.loads(data, object_pairs_hook=_pairs,
                          parse_constant=lambda item: (_ for _ in ()).throw(ValueError(item)))
    except (UnicodeError, ValueError) as exc:
        raise DatasetIntegrityError(f"invalid JSON: {exc}") from exc


def _source_path(path: Path) -> Path:
    # Check both spelling and resolved target before opening even a manifest.
    for candidate in (path.absolute(), path.resolve()):
        parts = [part.casefold() for part in candidate.parts]
        if any("holdout" in part or part in {"acceptance", "acceptance_tests", "sealed"}
               for part in parts):
            raise DatasetIntegrityError("protected source is not a development trace")
        if any(part.startswith("confirmation") for part in parts):
            raise DatasetIntegrityError("protected confirmation samples are not source traces")
    return path.resolve()


def validate_output_path(path: Path) -> Path:
    output = _source_path(Path(path))
    if "datasets" in output.parts or not any(output.is_relative_to(ROOT / "data" / directory)
               for directory in ("experiments", "test_runs")):
        raise DatasetIntegrityError("audit output must be under data/experiments or data/test_runs")
    if output.exists():
        raise DatasetIntegrityError("audit output already exists; overwrite is forbidden")
    return output


def read_artifact(record: Mapping[str, Any], base_dir: Path) -> bytes:
    if not isinstance(record, Mapping) or set(record) != {"path", "sha256"}:
        raise DatasetIntegrityError("artifact requires exact path and SHA fields")
    digest = record["sha256"]
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise DatasetIntegrityError("artifact SHA must be lowercase SHA-256")
    path = _source_path(Path(base_dir) / str(record["path"]))
    value = path.read_bytes()
    if _digest(value) != digest:
        raise DatasetIntegrityError(f"artifact SHA mismatch: {path}")
    return value


def read_registration(path: Path) -> dict[str, Any]:
    path = _source_path(Path(path))
    value = _json(path.read_bytes())
    if not isinstance(value, dict) or value.get("schema_version") != SOURCE_REGISTRATION_SCHEMA:
        raise DatasetIntegrityError("unsupported source registration schema")
    if (set(value) - {"schema_version", "source_runs", "coverage_scope"}
            or not isinstance(value.get("source_runs"), list)):
        raise DatasetIntegrityError("source registration fields are invalid")
    identities = set()
    for run in value["source_runs"]:
        if not isinstance(run, dict):
            raise DatasetIntegrityError("source run must be an object")
        key = (run.get("source_run_id"), run.get("run_id"))
        if key in identities:
            raise DatasetIntegrityError("duplicate source run or conflicting project family")
        identities.add(key)
    return value


@dataclass(frozen=True)
class SourceRun:
    registration: Mapping[str, Any]
    final_state: RunState
    snapshots: Mapping[str, RunState]
    model_trace: Sequence[Mapping[str, Any]]
    reviews: Sequence[Mapping[str, Any]]
    collection_contract: Mapping[str, Any] | None = None


def _json_changes(before: Any, after: Any, path: str = "$") -> list[dict[str, Any]]:
    """Recompute the runner's structural delta without using it as authority."""
    if isinstance(before, dict) and isinstance(after, dict):
        changes = []
        for key in sorted(set(before) | set(after)):
            child = f"{path}.{key}"
            if key not in before:
                changes.append({"op": "add", "path": child, "after": after[key]})
            elif key not in after:
                changes.append({"op": "remove", "path": child})
            else:
                changes.extend(_json_changes(before[key], after[key], child))
        return changes
    if isinstance(before, list) and isinstance(after, list):
        shared = min(len(before), len(after))
        changes = [change for i in range(shared)
                   for change in _json_changes(before[i], after[i], f"{path}[{i}]")]
        changes.extend({"op": "remove", "path": f"{path}[{i}]"} for i in range(shared, len(before)))
        changes.extend({"op": "add", "path": f"{path}[{i}]", "after": after[i]}
                       for i in range(shared, len(after)))
        return changes
    return [] if before == after else [{"op": "replace", "path": path, "after": after}]


def load_source_run(record: Mapping[str, Any], *, base_dir: Path,
                    coverage_scope_sha256: str | None = None) -> SourceRun:
    if record.get("source_kind") != "production_trace":
        raise DatasetIntegrityError("only production_trace may supply role data")
    if record.get("collection_mode") not in {"all_zero", "role_stage"}:
        raise DatasetIntegrityError("source collection must be all_zero or frozen role_stage")
    artifacts = record.get("artifacts")
    if not isinstance(artifacts, dict) or not REQUIRED_ARTIFACTS <= set(artifacts):
        raise DatasetIntegrityError("complete SQLite, trace, event, timeline and ledger artifacts are required")
    if set(artifacts) - REQUIRED_ARTIFACTS - {"human_reviews"}:
        raise DatasetIntegrityError("unknown source artifact")
    for key in ("run_id", "source_run_id", "project_family", "suite"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            raise DatasetIntegrityError(f"source {key} must be nonempty")
    if any(word in record["suite"].casefold() for word in ("holdout", "acceptance", "confirmation", "fixture")):
        raise DatasetIntegrityError("protected or fixture suite cannot supply training traces")
    if set(record.get("protocol_sha256", {})) != set(ROLE_MODULES):
        raise DatasetIntegrityError("source must freeze the five current protocol hashes")
    for role, module in ROLE_MODULES.items():
        if record["protocol_sha256"][role] != _digest(Path(module.__file__).read_bytes()):
            raise DatasetIntegrityError(f"source protocol SHA mismatch: {role}")
    raw = {name: read_artifact(item, base_dir) for name, item in artifacts.items()}
    protocol = _json(raw["run_protocol"])
    _validate_frozen_scope(record, protocol, _json(raw["source_tree_manifest"]))
    if coverage_scope_sha256 is not None and protocol.get("role_data_scope_sha256") != coverage_scope_sha256:
        raise DatasetIntegrityError("coverage scope was not pinned in the frozen source run protocol")
    contract = protocol.get("role_data_collection")
    if (contract is None) != (record["collection_mode"] == "all_zero"):
        raise DatasetIntegrityError("source collection mode differs from frozen role-stage contract")
    if contract is not None:
        from rwkv_lh.role_trace_stages import validate_collection_contract
        try:
            contract = validate_collection_contract(contract)
        except ValueError as exc:
            raise DatasetIntegrityError(str(exc)) from exc
    path = _source_path(Path(base_dir) / artifacts["sqlite"]["path"])
    if any(Path(str(path) + suffix).exists() and Path(str(path) + suffix).stat().st_size
           for suffix in ("-wal", "-journal")):
        raise DatasetIntegrityError("SQLite is not a frozen standalone snapshot (active WAL/journal)")
    with sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        if connection.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise DatasetIntegrityError("SQLite integrity check failed")
        run_rows = connection.execute("SELECT state_json FROM runs WHERE run_id=?", (record["run_id"],)).fetchall()
        if len(run_rows) != 1:
            raise DatasetIntegrityError("source run is absent or ambiguous in SQLite")
        final_state = RunState.from_dict(LongHorizonStore._deserialize(run_rows[0]["state_json"]))
        rows = connection.execute("SELECT * FROM checkpoints WHERE run_id=? ORDER BY revision", (record["run_id"],)).fetchall()
        event_rows = connection.execute("SELECT * FROM events WHERE run_id=? ORDER BY revision", (record["run_id"],)).fetchall()
    if _digest(path.read_bytes()) != _digest(raw["sqlite"]):
        raise DatasetIntegrityError("SQLite changed during extraction")
    if not rows or not final_state.causal_order:
        raise DatasetIntegrityError("source lacks durable checkpoints/causal facts")
    try:
        timeline = _json(gzip.decompress(raw["state_timeline"]))
    except (OSError, EOFError) as exc:
        raise DatasetIntegrityError("invalid compressed state timeline") from exc
    events = _json(raw["event_log"])
    trace = _json(raw["model_trace"])
    ledger = _json(raw["causal_ledger"])
    if not isinstance(trace, list) or any(not isinstance(item, dict) for item in trace):
        raise DatasetIntegrityError("model trace must be an event array")
    if not isinstance(events, list) or len(events) != len(event_rows):
        raise DatasetIntegrityError("event log differs from SQLite")
    for exported, sql in zip(events, event_rows):
        causal = LongHorizonStore._deserialize(sql["data_json"])
        if exported.get("revision") != sql["revision"] or exported.get("type") != sql["type"] or exported.get("causal_event") != causal or exported.get("data") != causal.get("payload"):
            raise DatasetIntegrityError("event log/SQLite causal event mismatch")
    if not isinstance(timeline, list) or len(timeline) != len(rows):
        raise DatasetIntegrityError("state timeline/checkpoint count mismatch")
    snapshots = {}
    causal_at_revision = {
        row["revision"]: CausalEvent.from_dict(LongHorizonStore._deserialize(row["data_json"]))
        for row in event_rows
    }
    previous = None
    previous_revision = -1
    for row, exported in zip(rows, timeline):
        snapshot = RunState.from_dict(LongHorizonStore._deserialize(row["state_json"]))
        state_dict = snapshot.to_dict()
        if snapshot.run_id != final_state.run_id or row["revision"] != snapshot.revision or row["revision"] <= previous_revision:
            raise DatasetIntegrityError("snapshot run/revision identity mismatch")
        expected_event = causal_at_revision.get(snapshot.revision)
        if (expected_event is None or not snapshot.causal_order
            or snapshot.causal_order[-1] != expected_event.event_id
            or len(snapshot.causal_order) != expected_event.sequence):
            raise DatasetIntegrityError("snapshot contains future or missing causal facts at its SQLite revision")
        if snapshot.causal_order != final_state.causal_order[:len(snapshot.causal_order)]:
            raise DatasetIntegrityError("snapshot is not a causal prefix of final state")
        if any(snapshot.causal_records[key].to_dict() != final_state.causal_records[key].to_dict() for key in snapshot.causal_order):
            raise DatasetIntegrityError("immutable causal event changed between snapshots")
        expected_changes = [] if previous is None else _json_changes(previous, state_dict)
        if exported.get("revision") != snapshot.revision or exported.get("state_sha256") != _digest(_canonical(state_dict)) or exported.get("changes_from_previous") != expected_changes or exported.get("change_digest") != _digest(_canonical({"changes": expected_changes})):
            raise DatasetIntegrityError("state timeline cannot be exactly recomputed from SQLite")
        if previous is None and (exported.get("snapshot_kind") != "initial_exact" or exported.get("state") != state_dict):
            raise DatasetIntegrityError("initial state timeline snapshot mismatch")
        if snapshot.causal_order:
            snapshots[snapshot.causal_order[-1]] = snapshot
        previous, previous_revision = state_dict, snapshot.revision
    if previous != final_state.to_dict():
        raise DatasetIntegrityError("final SQLite state is not the final retained checkpoint")
    if not isinstance(ledger, dict) or ledger.get("causal_events") != [final_state.causal_records[key].to_dict() for key in final_state.causal_order]:
        raise DatasetIntegrityError("causal ledger differs from authoritative SQLite")
    if ledger.get("policy", {}).get("hidden_acceptance_included") is not False:
        raise DatasetIntegrityError("causal ledger lacks development-only boundary attestation")
    reviews = _json(raw["human_reviews"]) if "human_reviews" in raw else []
    if not isinstance(reviews, list) or any(not isinstance(review, Mapping) for review in reviews):
        raise DatasetIntegrityError("human reviews must be an array")
    from rwkv_lh.role_trace_stages import validate_collection_states
    try:
        validate_collection_states(final_state, trace, contract)
    except ValueError as exc:
        raise DatasetIntegrityError(str(exc)) from exc
    return SourceRun(dict(record), final_state, snapshots, trace, reviews, contract)


def register_case(case_dir: Path, *, run_id: str, source_run_id: str, project_family: str, suite: str) -> dict:
    case_dir = _source_path(Path(case_dir))
    record = {
        "run_id": run_id, "source_run_id": source_run_id, "project_family": project_family,
        "suite": suite, "source_kind": "production_trace", "collection_mode": "all_zero",
        "protocol_sha256": {role: _digest(Path(module.__file__).read_bytes()) for role, module in ROLE_MODULES.items()},
        "artifacts": {},
    }
    for key, relative in CASE_ARTIFACT_PATHS.items():
        path = _source_path(case_dir / relative)
        record["artifacts"][key] = {"path": str(path), "sha256": _digest(path.read_bytes())}
    for key, name in (("run_protocol", "RUN_PROTOCOL.json"), ("source_tree_manifest", "source_tree_manifest.json")):
        path = _source_path(case_dir.parent.parent / name)
        record["artifacts"][key] = {"path": str(path), "sha256": _digest(path.read_bytes())}
    protocol = _json(read_artifact(record["artifacts"]["run_protocol"], case_dir))
    record["collection_mode"] = "role_stage" if protocol.get("role_data_collection") is not None else "all_zero"
    load_source_run(record, base_dir=case_dir)
    return {"schema_version": SOURCE_REGISTRATION_SCHEMA, "source_runs": [record]}


def validate_raw_generation(raw: Mapping[str, Any]) -> tuple[str, list[int]]:
    if raw.get("finish_reason") != "stop":
        raise SampleExcluded("finish_reason is not natural stop")
    ids = raw.get("raw_token_ids")
    if not isinstance(ids, list) or not ids:
        raise SampleExcluded("raw generated token IDs are missing")
    if any(type(item) is not int or item < 0 for item in ids):
        raise DatasetIntegrityError("invalid raw token ID")
    text = raw.get("raw_output")
    if not isinstance(text, str) or raw.get("raw_output_sha256") != _digest(text):
        raise DatasetIntegrityError("raw generation text/SHA mismatch")
    try:
        stream = tokenizer().decode_bytes(ids).decode("utf-8")
    except (KeyError, ValueError, UnicodeError) as exc:
        raise DatasetIntegrityError("raw token stream cannot be decoded") from exc
    if stream != text and not any(stream == text + suffix for suffix in JSON_CALL_STOP_SUFFIXES):
        raise DatasetIntegrityError("raw token stream differs from output and attested stop suffix")
    if raw.get("state_profile_id") != "zero" or raw.get("state_profile_sha256") != ZERO_SHA:
        raise DatasetIntegrityError("generation is not explicitly bound to zero State")
    if raw.get("postprocessed") is not False:
        raise DatasetIntegrityError("raw generation cannot be postprocessed")
    return stream, ids


def _events(source: SourceRun) -> list[CausalEvent]:
    return [source.final_state.causal_records[key] for key in source.final_state.causal_order]


def _parse_original_command(raw: Mapping[str, Any]):
    from types import SimpleNamespace
    from rwkv_lh.model_session import _restore_attested_stop_suffix

    # Keep the full token stream as the target. Parse exactly the production
    # transport-visible text, restoring only the already attested Markdown fence.
    parsed_text, _ = _restore_attested_stop_suffix(SimpleNamespace(
        raw_output=raw["raw_output"], raw_token_ids=tuple(raw["raw_token_ids"]),
        finish_reason=raw["finish_reason"],
    ))
    return parse_model_command_with_trace(parsed_text)[0]


def _successful_progress(action, rebuilt: Mapping[str, Any]) -> bool:
    return (
        action.status is ActionStatus.SUCCEEDED and bool((action.result or {}).get("success"))
        and (any(action_observes_root(action, root) for root in rebuilt.get("missing_read_roots", []))
             or any(action_mutates_root(action, root) for root in rebuilt.get("missing_write_roots", [])))
    )


def _action_authority(source: SourceRun, rebuilt: Mapping, request_id: str, selection_id: str = "") -> list[str]:
    decisions = source.final_state.decisions
    matching = []
    for action in source.final_state.actions.values():
        decision = decisions.get(action.decision_id)
        if ((request_id and action.request_id == request_id)
            or (selection_id and decision is not None and decision.tool_selection_id == selection_id)):
            if _successful_progress(action, rebuilt):
                matching.append(action.action_id)
    return matching


def _validate_protocol_identity(payload: Mapping, role: str) -> None:
    module = ROLE_MODULES[role]
    if payload.get("protocol_schema_version") != module.INPUT_SCHEMA_VERSION or payload.get("protocol_sha256") != _digest(Path(module.__file__).read_bytes()):
        raise DatasetIntegrityError(f"runtime attestation protocol mismatch: {role}")


def _review_authority(source: SourceRun, row: Mapping[str, Any]) -> list[str]:
    matching = [review for review in source.reviews
                if review.get("request_id") == row["request_id"] and review.get("role") == row["role"]]
    if not matching:
        return []
    purpose = matching[0].get("purpose")
    semantic = purpose in {"semantic_label", "trace_correction"}
    if row["role"] in {"auditor_step", "auditor_final", "finalizer_answer"} and not semantic:
        raise DatasetIntegrityError("Auditor/Finalizer review must bind semantic label evidence")
    if semantic and row["role"] not in {"selector_intent", "auditor_step", "auditor_final", "finalizer_answer"}:
        raise DatasetIntegrityError("reviewed semantic corrections cannot bypass Executor execution evidence")
    reviewers = set()
    for review in matching:
        if (review.get("input_sha256") != _digest(row["input_text"])
            or review.get("target_sha256") != _digest(row["target_text"])
            or review.get("decision") != "accept" or review.get("purpose") != purpose
            or purpose not in {"failure_recovery_positive", "semantic_label", "trace_correction"}):
            raise DatasetIntegrityError("human review does not bind exact input/target recovery evidence")
        if semantic:
            for key in ("source_run_id", "run_id", "boundary_event_id", "original_output_record_sha256"):
                if review.get(key) != row.get(key) or not row.get(key):
                    raise DatasetIntegrityError(f"human review does not bind exact {key}")
            refs = review.get("evidence_refs")
            if (not isinstance(refs, list) or any(not isinstance(ref, str) for ref in refs)
                    or len(refs) != len(set(refs))
                    or not set(refs) <= set(row["available_evidence_refs"])
                    or not isinstance(review.get("rationale"), str) or not review["rationale"].strip()):
                raise DatasetIntegrityError("human review requires visible evidence and a rationale")
            if purpose == "trace_correction" and (
                review.get("target_text") != row["target_text"]
                or row["target_text"] == row["original_target_text"]
            ):
                raise DatasetIntegrityError("reviewed correction must bind distinct explicit target bytes")
        identity = review.get("reviewer_id")
        if not isinstance(identity, str) or not identity.strip():
            raise DatasetIntegrityError("human reviewer identity is missing")
        reviewers.add(identity)
    if len(reviewers) != 2 or len({reviewer.strip() for reviewer in reviewers}) != 2 or len(matching) != 2:
        raise DatasetIntegrityError("human_double_review requires exactly two distinct reviewers")
    if not semantic and not row["coverage"].get("failed_last_action"):
        raise DatasetIntegrityError("human reviews only label failure recovery positives")
    return sorted(reviewers)


def _review_target(source: SourceRun, role: str, request_id: str, original: str) -> str:
    corrections = [review for review in source.reviews if review.get("role") == role
                   and review.get("request_id") == request_id and review.get("purpose") == "trace_correction"]
    if not corrections:
        return original
    targets = [review.get("target_text") for review in corrections]
    if any(not isinstance(target, str) or not target for target in targets) or len(set(targets)) != 1:
        raise DatasetIntegrityError("human corrections disagree or lack explicit target bytes")
    return targets[0]


def _has_review(source: SourceRun, role: str, request_id: str) -> bool:
    return any(review.get("request_id") == request_id and review.get("role") == role for review in source.reviews)


def _audit_acceptance(events: Sequence[CausalEvent], recorded: CausalEvent,
                      boundary: CausalEvent, canonical_target: str) -> CausalEvent | None:
    from rwkv_lh.goal_loop_protocol import GoalAuditDecision

    payload = recorded.payload
    audit, _ = GoalAuditDecision.parse_with_bindings(canonical_target, audit_id=payload["audit_id"])
    boundary_id = boundary.payload.get("audit_boundary_id")
    opened = [item for item in events if item.event_type == "goal_audit_boundary_opened"
              and item.subject_id == boundary_id and item.sequence < boundary.sequence]
    if len(opened) != 1 or not boundary_id or payload.get("audit_boundary_id") != boundary_id:
        raise DatasetIntegrityError("Auditor output boundary identity mismatch")
    if payload.get("audit") != audit.to_dict() or payload.get("audit_digest") != audit.digest:
        raise DatasetIntegrityError("recorded Auditor decision differs from raw target")
    accepted = [item for item in events if item.event_type == "goal_audit_accepted"
                and item.payload.get("request_id") == payload.get("request_id")]
    if not accepted:
        return None
    if len(accepted) != 1:
        raise DatasetIntegrityError("duplicate Auditor kernel acceptance")
    item = accepted[0]
    if (item.sequence <= recorded.sequence or item.payload.get("kernel_validated") is not True
        or item.payload.get("audit_boundary_id") != boundary_id
        or item.payload.get("boundary") != opened[0].payload.get("boundary")
        or item.payload.get("audit_id") != audit.audit_id
        or item.payload.get("audit_digest") != audit.digest
        or item.payload.get("audit") != audit.to_dict()):
        raise DatasetIntegrityError("Auditor kernel acceptance differs from this boundary and raw decision")
    return item


def _validate_decision_record(source: SourceRun, event: CausalEvent, checkpoint: ModelCheckpoint,
                              command: Any, generation: Mapping[str, Any]) -> None:
    raw = event.payload["raw_generation"]
    decision = source.final_state.decisions.get(str(event.payload.get("decision_id") or ""))
    if decision is None:
        raise SampleExcluded("missing durable command decision")
    if event.payload.get("decision") != decision.to_dict():
        raise DatasetIntegrityError("durable command decision differs from causal event")
    output_id = (generation["candidate_checkpoint_id"] if generation["outcome"] == "committed"
                 else checkpoint.checkpoint_id)
    output = source.final_state.model_states.get(output_id)
    if output is None:
        raise SampleExcluded("missing durable command output checkpoint")
    expected = {
        "request_id": raw["request_id"], "lane_id": checkpoint.lane_id,
        "input_checkpoint_id": checkpoint.checkpoint_id,
        # DecisionRecord stores the transcript digest even for native transport;
        # the physical State digest is checked separately in generation evidence.
        "input_digest": checkpoint.transcript_digest,
        "visible_event_ids": tuple(checkpoint.event_ids), "raw_output": raw["raw_output"],
        "command_digest": command.digest, "sampling": raw["sampling"],
        "model": checkpoint.model, "transport": checkpoint.transport,
        "accepted": True, "output_checkpoint_id": output_id, "output_digest": output.transcript_digest,
    }
    if any(getattr(decision, key) != value for key, value in expected.items()):
        raise DatasetIntegrityError("command decision is not bound to its original generation")
    if (event.payload.get("request_id") != raw["request_id"]
        or event.payload.get("operation") != command.name
        or event.payload.get("wire_command_digest") != command.digest):
        raise DatasetIntegrityError("accepted command event differs from raw command identity")


def _final_acceptance(source: SourceRun, events: Sequence[CausalEvent], recorded: CausalEvent,
                      request_id: str, text: str) -> CausalEvent | None:
    decision_id = recorded.payload.get("decision_id")
    if source.final_state.status.value != "completed" or source.final_state.final_decision_id != decision_id:
        return None
    if source.final_state.final_output != text:
        raise DatasetIntegrityError("completed Finalizer text differs from raw candidate")
    opened = [item for item in events if item.event_type == "goal_audit_boundary_opened"
              and item.payload.get("final_candidate") is True
              and item.payload.get("decision_id") == decision_id
              and item.sequence > recorded.sequence]
    if not opened:
        return None
    if len(opened) != 1:
        raise DatasetIntegrityError("Finalizer has duplicate final candidate audit boundaries")
    gate = opened[0]
    accepted = [item for item in events if item.event_type == "goal_audit_accepted"
                and item.payload.get("audit_boundary_id") == gate.subject_id]
    completed = [item for item in events if item.event_type == "run_completed"
                 and item.payload.get("decision_id") == decision_id]
    if not accepted or not completed:
        return None
    if len(accepted) != 1 or len(completed) != 1:
        raise DatasetIntegrityError("Finalizer completion/audit is not unique")
    audit, completion = accepted[0], completed[0]
    if (not recorded.sequence < gate.sequence < audit.sequence < completion.sequence
        or audit.payload.get("kernel_validated") is not True
        or audit.payload.get("audit", {}).get("verdict") != "ready_for_final"
        or completion.payload.get("audit_id") != audit.payload.get("audit_id")
        or completion.payload.get("audit_boundary_id") != gate.subject_id
        or completion.payload.get("request_id") != request_id
        or completion.payload.get("final_output") != text
        or completion.payload.get("final_output_sha256") != _digest(text)
        or completion.payload.get("rwkv_audit_accepted") is not True
        or completion.payload.get("controller_rewritten") is not False):
        raise DatasetIntegrityError("Finalizer completion is not bound to this candidate and final audit")
    audit_records = [item for item in events if item.event_type == "goal_audit_recorded"
                     and item.payload.get("request_id") == audit.payload.get("request_id")]
    audit_starts = [item for item in events if item.event_type == "goal_auditor_session_started"
                    and item.payload.get("audit_boundary_id") == gate.subject_id
                    and gate.sequence < item.sequence < audit.sequence]
    if len(audit_records) != 1:
        raise SampleExcluded("Finalizer lacks the raw final Auditor decision")
    audit_record = audit_records[0]
    bound_starts = [item for item in audit_starts if item.payload.get("checkpoint_id") == audit_record.payload.get("audit_checkpoint_id")]
    if len(bound_starts) != 1:
        raise SampleExcluded("Finalizer lacks the final Auditor input boundary")
    if audit_record.payload.get("parsed") is not True or audit_record.payload.get("auditor_role") != "auditor_final":
        raise DatasetIntegrityError("Finalizer completion refers to an unparsed or nonfinal audit")
    audit_raw = audit_record.payload.get("raw_generation", {})
    validate_raw_generation(audit_raw)
    audit_command = _parse_original_command(audit_raw)
    if _audit_acceptance(events, audit_record, bound_starts[0], audit_command.canonical) != audit:
        raise DatasetIntegrityError("Finalizer completion borrowed a different Auditor acceptance")
    return audit


def _sample(source: SourceRun, *, role: str, request_id: str, boundary: CausalEvent,
            checkpoint: ModelCheckpoint, rebuilt: Mapping, context: Mapping, target: str,
            target_ids: Sequence[int], authority: str, action_refs: Sequence[str], raw: Mapping,
            original_target: str | None = None) -> dict:
    original = target if original_target is None else original_target
    corrected = target != original
    row = {
        "schema_version": EXTRACTION_SCHEMA, "role": role, "request_id": request_id,
        "run_id": source.final_state.run_id, "source_run_id": source.registration["source_run_id"],
        "project_family": source.registration["project_family"],
        "input_protocol": ROLE_MODULES[role].INPUT_SCHEMA_VERSION,
        "protocol_sha256": source.registration["protocol_sha256"][role],
        "input_text": context["prompt_text"], "target_text": target,
        "protocol_prompt": rebuilt["protocol_prompt"], "protocol_source": rebuilt["prompt_source"],
        "coverage": dict(rebuilt["coverage"]), "boundary_event_id": boundary.event_id,
        "boundary_revision": source.snapshots[boundary.event_id].revision,
        "boundary_refs": list(rebuilt["boundary_refs"]),
        "input_checkpoint_id": checkpoint.checkpoint_id,
        "context": dict(context), "raw_output_token_ids": list(target_ids),
        "original_target_text": original, "original_output_record_sha256": _digest(_canonical(raw)),
        "target_origin": "human_trace_correction" if corrected else "raw_model_output",
        "target_token_ids": tokenizer().encode(target) if corrected else list(target_ids),
        "target_token_ids_source": "local_tokenizer_for_reviewed_target" if corrected else "raw_generation",
        "target_tokenizer_sha256": _digest(VOCAB_PATH.read_bytes()),
        "available_evidence_refs": list(rebuilt.get("evidence_refs", [])),
        "raw_output": dict(raw), "label_authority": authority,
        "label_evidence_action_ids": list(action_refs), "recomputed": True,
    }
    row["sample_id"] = "RT-" + _digest(_canonical({key: row[key] for key in ("source_run_id", "run_id", "request_id", "role", "boundary_event_id")}))
    reviewers = _review_authority(source, row)
    if reviewers:
        row["label_authority"] = "human_double_review"
        row["human_reviewers"] = reviewers
    elif authority == "human_double_review":
        raise SampleExcluded("missing two pinned human recovery reviews")
    return row


def extract_source(source: SourceRun, *, roles: Sequence[str] = tuple(ROLE_MODULES)) -> tuple[list[dict], list[dict]]:
    from rwkv_lh.role_trace_context import reconstruct_context, TraceContextError, bind_server_input_tokens
    from rwkv_lh.role_trace_inputs import rebuild_role_input
    from rwkv_lh.role_trace_generation import (
        GenerationEvidenceError, GenerationEvidenceMissing,
        validate_generation_evidence, validate_selector_generation,
    )

    if not set(roles) <= set(ROLE_MODULES) or not roles:
        raise DatasetIntegrityError("unknown or empty role selection")
    if source.collection_contract is not None and set(roles) != {source.collection_contract["target_role"]}:
        raise DatasetIntegrityError("role-stage extraction must select exactly the frozen target role")
    events = _events(source)
    samples, exclusions = [], []
    starts = {}
    returns = {}
    for event in source.model_trace:
        request_id = event.get("request_id")
        if not request_id:
            continue
        target = starts if event.get("type") == "model_session_generation_started" else returns if event.get("type") == "model_session_generation_returned" else None
        if target is not None:
            if request_id in target:
                raise DatasetIntegrityError("duplicate model request boundary")
            target[request_id] = event
    latest = {}
    consumed_requests = set()
    for event in events:
        payload = event.payload
        if event.event_type in {"goal_role_input_boundary", "tool_schema_disclosed", "goal_auditor_session_started", "goal_finalizer_session_started"}:
            latest[event.event_type] = event
        if event.event_type == "exact_tool_selection_staged" and "selector_intent" in roles:
            from rwkv_lh.exact_tool_selector.network_protocol import NETWORK_SELECTOR_MENU_ORDER_IDS, NetworkSelectorInput
            from rwkv_lh.exact_tool_selector.input_protocol import network_selector_input_protocol
            from rwkv_lh.exact_tool_selector.native_network_protocol import NativeNetworkToolSelection
            from rwkv_lh.model import LongHorizonModel
            selection = payload.get("selection", {})
            raw_ensemble = selection.get("raw_selection", {})
            lanes = raw_ensemble.get("lane_selections", {})
            if not lanes:
                exclusions.append({"event_id": event.event_id, "role": "selector_intent", "reason": "missing_three_menu_lane_records"})
                continue
            if set(lanes) != set(NETWORK_SELECTOR_MENU_ORDER_IDS):
                raise DatasetIntegrityError("Selector requires exactly the three registered menus")
            if len({row.get("trace_id") for row in lanes.values()}) != len(lanes) or len({row.get("selector_checkpoint_id") for row in lanes.values()}) != len(lanes):
                raise DatasetIntegrityError("Selector menus must have independent request/checkpoint identities")
            parsed_lanes = [NativeNetworkToolSelection.from_dict(lanes[menu]) for menu in NETWORK_SELECTOR_MENU_ORDER_IDS]
            ensemble_operation, ensemble_record = LongHorizonModel._selector_ensemble_choice(parsed_lanes, eligible_labels=parsed_lanes[0].eligible_labels)
            if raw_ensemble.get("selected_operation") != ensemble_operation or raw_ensemble.get("menu_order_ensemble") != ensemble_record:
                raise DatasetIntegrityError("Selector ensemble is inconsistent with raw lane votes")
            for menu, raw in lanes.items():
                request_id = str(raw.get("trace_id") or "")
                try:
                    boundary = latest.get("goal_role_input_boundary")
                    if boundary is None or boundary.event_id not in source.snapshots:
                        raise SampleExcluded("missing durable Selector input boundary")
                    checkpoint = source.final_state.model_states.get(str(raw.get("selector_checkpoint_id") or ""))
                    if checkpoint is None:
                        raise SampleExcluded("missing Selector checkpoint")
                    rebuilt = rebuild_role_input("selector_intent", source.snapshots[boundary.event_id], {"boundary_event_id": boundary.event_id, "menu_order_id": menu})
                    expected = rebuilt.get("expected_checkpoint_transcript") or rebuilt.get("full_input_text")
                    if expected is None or checkpoint.transcript != expected or checkpoint.transcript_digest != _digest(expected):
                        raise DatasetIntegrityError("Selector builder/checkpoint byte mismatch")
                    _validate_protocol_identity(raw_ensemble, "selector_intent")
                    if raw.get("profile_id") != "zero" or raw.get("profile_sha256") != ZERO_SHA:
                        raise DatasetIntegrityError("Selector is not explicitly zero State")
                    if checkpoint.state_profile_id != "zero" or checkpoint.state_profile_sha256 != ZERO_SHA or raw.get("model") != checkpoint.model or raw.get("model_sha256") != (checkpoint.native_state_metadata or {}).get("model_sha256"):
                        raise DatasetIntegrityError("Selector raw identity differs from checkpoint")
                    protocol = network_selector_input_protocol(selector_intent_v4.INPUT_SCHEMA_VERSION)
                    network = NetworkSelectorInput.create(
                        current_subtask=rebuilt["network_input"]["current_subtask"],
                        current_progress=rebuilt["network_input"]["current_progress"],
                        eligible_labels=rebuilt["network_input"]["eligible_labels"],
                        menu_order_id=menu,
                    )
                    if raw.get("input_digest") != protocol.input_digest(network) or raw.get("menu_digest") != protocol.menu_digest(network) or raw.get("eligible_labels") != list(network.eligible_labels):
                        raise DatasetIntegrityError("Selector input/menu/eligible labels differ from rebuilt boundary")
                    try:
                        validate_selector_generation(raw, checkpoint, network)
                    except GenerationEvidenceMissing as exc:
                        raise SampleExcluded(str(exc)) from exc
                    except GenerationEvidenceError as exc:
                        raise DatasetIntegrityError(str(exc)) from exc
                    module = ROLE_MODULES["selector_intent"]
                    operation = raw.get("selected_operation")
                    action_refs = _action_authority(source, rebuilt, "", str(selection.get("selection_id") or ""))
                    action_refs = [key for key in action_refs if source.final_state.actions[key].action_type == operation]
                    if action_refs:
                        authority = "executed_fixture"
                    elif rebuilt["eligible_operations"] == [operation]:
                        authority = "planner_contract"
                    elif _has_review(source, "selector_intent", request_id):
                        authority = "human_double_review"
                    else:
                        authority = "pending_human_review"
                    label_source = dict(rebuilt["prompt_source"])
                    label_source.update(selected_operation=operation,
                                        selection_authority=authority if authority != "pending_human_review" else "human_double_review",
                                        selection_verifier_id=boundary.event_id)
                    target = module.render_target(label_source)
                    ids = raw.get("decoder_trace", {}).get("token_ids")
                    if not isinstance(ids, list) or not ids:
                        raise SampleExcluded("missing Selector raw suffix token IDs")
                    try:
                        decoded = tokenizer().decode_bytes(ids).decode("utf-8")
                    except (KeyError, ValueError, UnicodeError) as exc:
                        raise DatasetIntegrityError("Selector suffix token stream cannot be decoded") from exc
                    if any(type(token) is not int or token < 0 for token in ids) or decoded != target:
                        raise DatasetIntegrityError("Selector suffix token trace differs from target")
                    context = {"prompt_text": expected, "prompt_sha256": _digest(expected), "transport": checkpoint.transport,
                               "initial_state": {"profile_id": "zero", "profile_sha256": ZERO_SHA, "model": checkpoint.model, "model_sha256": raw["model_sha256"]},
                               "token_ids": None, "token_ids_complete": False,
                               "local_tokenizer_sha256": _digest(VOCAB_PATH.read_bytes()),
                               "reconstructed_token_ids": tokenizer().encode(expected), "reconstructed_token_ids_include_bos": False,
                               "chain_evidence": [checkpoint.checkpoint_id], "menu_order_id": menu}
                    try:
                        # Selector is one fresh full-prompt forward even though
                        # its checkpoint transport is native_rwkv.
                        context = bind_server_input_tokens(context, {
                            **raw["decoder_trace"],
                            "prompt_token_ids_scope": "full_context" if raw["decoder_trace"].get("prompt_token_ids_scope") == "full_prompt" else "unspecified",
                        })
                    except TraceContextError as exc:
                        raise DatasetIntegrityError(str(exc)) from exc
                    reviewed_target = _review_target(source, "selector_intent", request_id, target)
                    if reviewed_target != target:
                        try:
                            reviewed_operation = module.parse_target(reviewed_target)
                            label_source.update(selected_operation=reviewed_operation, selection_authority="human_double_review")
                            if module.render_target(label_source) != reviewed_target:
                                raise ValueError("noncanonical Selector correction")
                        except ValueError as exc:
                            raise DatasetIntegrityError(f"Selector correction violates the original eligible contract: {exc}") from exc
                    row = _sample(source, role="selector_intent", request_id=request_id, boundary=boundary, checkpoint=checkpoint,
                                  rebuilt=rebuilt, context=context, target=reviewed_target, original_target=target,
                                  target_ids=ids, authority=authority, action_refs=action_refs, raw=raw)
                    if row["label_authority"] == "pending_human_review":
                        raise SampleExcluded("no unique contract or executed advancing label for Selector lane", review_candidate=row)
                    samples.append(row)
                except SampleExcluded as exc:
                    excluded = {"event_id": event.event_id, "request_id": request_id, "role": "selector_intent", "reason": str(exc)}
                    if exc.review_candidate is not None:
                        excluded["review_candidate"] = exc.review_candidate
                    exclusions.append(excluded)
            continue
        if event.event_type not in {"model_call_accepted", "model_call_rejected", "goal_audit_recorded"} or not isinstance(payload.get("raw_generation"), dict):
            continue
        role = (str(payload.get("auditor_role") or "auditor_step") if event.event_type == "goal_audit_recorded"
                else "finalizer_answer" if payload.get("model_role") == "finalizer_answer" else "executor_args")
        raw = payload["raw_generation"]
        request_id = str(raw.get("request_id") or "")
        consumed_requests.add(request_id)
        if role not in roles:
            continue
        try:
            has_review = _has_review(source, role, request_id)
            if event.event_type == "model_call_rejected":
                raise SampleExcluded("rejected generation is context only, not a positive label")
            start, returned = starts.get(request_id), returns.get(request_id)
            if start is None or returned is None:
                raise SampleExcluded("missing raw request/response boundary")
            if returned.get("raw_generation") != raw:
                raise DatasetIntegrityError("durable output differs from original model trace")
            boundary_kind = "tool_schema_disclosed" if role == "executor_args" else "goal_finalizer_session_started" if role == "finalizer_answer" else "goal_auditor_session_started"
            boundary = latest.get(boundary_kind)
            if boundary is None or boundary.event_id not in source.snapshots:
                raise SampleExcluded("missing exact retained role input snapshot")
            checkpoint_id = str(start.get("input_checkpoint_id") or "")
            if boundary.payload.get("checkpoint_id") != checkpoint_id:
                raise DatasetIntegrityError("generation input is not bound to its durable role boundary")
            checkpoint = source.snapshots[boundary.event_id].model_states.get(checkpoint_id)
            if checkpoint is None:
                raise SampleExcluded("missing input checkpoint")
            _validate_protocol_identity(boundary.payload, role)
            if checkpoint.state_profile_id != "zero" or checkpoint.state_profile_sha256 != ZERO_SHA:
                raise DatasetIntegrityError("input checkpoint is not zero State")
            rebuilt = rebuild_role_input(role, source.snapshots[boundary.event_id], {"boundary_event_id": boundary.event_id, "checkpoint_id": checkpoint_id})
            expected = rebuilt.get("expected_checkpoint_transcript")
            if expected is None or checkpoint.transcript != expected:
                raise DatasetIntegrityError("role builder/checkpoint byte mismatch")
            try:
                context = reconstruct_context(checkpoint_id, source.snapshots[boundary.event_id].model_states, source.model_trace)
            except TraceContextError as exc:
                if any(marker in str(exc).lower() for marker in ("mismatch", "digest", "identity", "cycle")):
                    raise DatasetIntegrityError(str(exc)) from exc
                raise SampleExcluded(str(exc)) from exc
            target, target_ids = validate_raw_generation(raw)
            try:
                generation = validate_generation_evidence(request_id, checkpoint, raw, source.model_trace, source.final_state.model_states)
            except GenerationEvidenceMissing as exc:
                raise SampleExcluded(str(exc)) from exc
            except GenerationEvidenceError as exc:
                raise DatasetIntegrityError(str(exc)) from exc
            context["generation_evidence"] = generation
            try:
                context = bind_server_input_tokens(context, raw)
            except TraceContextError as exc:
                raise DatasetIntegrityError(str(exc)) from exc
            if raw.get("response_model") != checkpoint.model:
                raise DatasetIntegrityError("raw response model differs from input checkpoint")
            if role in {"auditor_step", "auditor_final", "finalizer_answer"}:
                # Kernel acceptance proves protocol consistency, not semantic
                # truth. Failed runs and rejected audits can supply the exact
                # review input; no successful later phase is required.
                if role == "finalizer_answer":
                    original_command = _parse_original_command(raw)
                    _validate_decision_record(source, event, checkpoint, original_command, generation)
                    if source.final_state.status.value == "completed":
                        _final_acceptance(source, events, event, request_id, original_command.arguments["text"])
                else:
                    original_command = _parse_original_command(raw) if payload.get("parsed") is True else None
                    if original_command is not None:
                        _audit_acceptance(events, event, boundary, original_command.canonical)
                selected_target = _review_target(source, role, request_id, target)
                row = _sample(source, role=role, request_id=request_id, boundary=boundary,
                              checkpoint=checkpoint, rebuilt=rebuilt, context=context,
                              target=selected_target, original_target=target, target_ids=target_ids,
                              authority="pending_human_review", action_refs=rebuilt["evidence_refs"], raw=raw)
                if row["label_authority"] != "human_double_review":
                    raise SampleExcluded("Auditor/Finalizer semantic target requires independent double review",
                                         review_candidate=row)
                if selected_target == target:
                    if original_command is None:
                        raise DatasetIntegrityError("unparsed audit requires an explicit reviewed correction")
                    canonical_target = original_command.canonical
                else:
                    canonical_target = selected_target
                from rwkv_lh.role_trace_labels import validate_role_target
                try:
                    validate_role_target(role, rebuilt, canonical_target, verifier_id=boundary.event_id)
                except ValueError as exc:
                    raise DatasetIntegrityError(f"reviewed role target/source mismatch: {exc}") from exc
                samples.append(row)
                continue
            command = _parse_original_command(raw)
            if generation["outcome"] != "committed":
                raise DatasetIntegrityError("accepted Executor command lacks its committed generation State")
            _validate_decision_record(source, event, checkpoint, command, generation)
            from rwkv_lh.role_trace_labels import validate_role_target
            try:
                validate_role_target(role, rebuilt, command.canonical, verifier_id=boundary.event_id)
            except ValueError as exc:
                raise DatasetIntegrityError(f"role target/source mismatch: {exc}") from exc
            authority = "executed_fixture"
            actual_actions = [action for action in source.final_state.actions.values() if action.request_id == request_id]
            if not actual_actions:
                raise SampleExcluded("missing actual Executor execution; review cannot replace Harness evidence")
            if any(action.status is not ActionStatus.SUCCEEDED or not (action.result or {}).get("success") for action in actual_actions):
                raise SampleExcluded("failed action output remains negative context even with human review")
            if any(action.action_type != command.name or action.wire_arguments != command.arguments
                   for action in actual_actions):
                raise DatasetIntegrityError("executed action differs from raw Executor command")
            action_refs = _action_authority(source, rebuilt, request_id)
            if not action_refs and not has_review:
                raise SampleExcluded("Executor did not execute successfully and advance a missing root")
            if has_review:
                authority = "human_double_review"
                action_refs = [action.action_id for action in actual_actions]
            samples.append(_sample(source, role=role, request_id=request_id, boundary=boundary, checkpoint=checkpoint, rebuilt=rebuilt,
                                   context=context, target=target, target_ids=target_ids, authority=authority, action_refs=action_refs, raw=raw))
        except SampleExcluded as exc:
            excluded = {"event_id": event.event_id, "request_id": request_id, "role": role, "reason": str(exc)}
            if exc.review_candidate is not None:
                excluded["review_candidate"] = exc.review_candidate
            exclusions.append(excluded)
    for request_id, start in starts.items():
        if request_id not in consumed_requests:
            exclusions.append({"request_id": request_id, "role": start.get("model_role", "unknown"), "reason": "request_has_no_durable_role_output"})
    return samples, exclusions


def extract_registration(registration_path: Path, output_dir: Path, *, roles: Sequence[str] = tuple(ROLE_MODULES),
                         prior_regression: Mapping | None = None, expected_regression_fingerprint: str | None = None) -> dict:
    from rwkv_lh.role_trace_artifacts import build_artifacts, write_artifacts, validate_coverage_requirements

    output = validate_output_path(output_dir)
    registration_path = _source_path(Path(registration_path))
    registration = read_registration(registration_path)
    requirements, scope_sha = None, None
    if "coverage_scope" in registration:
        scope = _json(read_artifact(registration["coverage_scope"], registration_path.parent))
        if (not isinstance(scope, Mapping) or set(scope) != {"schema_version", "objective", "requirements"}
                or scope.get("schema_version") != "rwkv-lh.role-trace-coverage-scope.v1"
                or not isinstance(scope.get("objective"), str) or not scope["objective"].strip()):
            raise DatasetIntegrityError("invalid preregistered role coverage scope")
        try:
            requirements = validate_coverage_requirements(scope["requirements"], list(roles))
        except ValueError as exc:
            raise DatasetIntegrityError(str(exc)) from exc
        scope_sha = registration["coverage_scope"]["sha256"]
    samples, exclusions, source_rows = [], [], []
    for record in registration["source_runs"]:
        source = load_source_run(record, base_dir=registration_path.parent, coverage_scope_sha256=scope_sha)
        rows, rejected = extract_source(source, roles=roles)
        if prior_regression is not None:
            from rwkv_lh.role_trace_artifacts import split_project_family
            kept = []
            for row in rows:
                if split_project_family(row["project_family"]) == "train":
                    kept.append(row)
                else:
                    rejected.append({"request_id": row["request_id"], "role": row["role"], "reason": "new_source_family_belongs_to_immutable_regression_split"})
            rows = kept
        samples.extend(rows)
        exclusions.extend({"run_id": source.final_state.run_id, **row} for row in rejected)
        source_rows.append({**dict(record), "role_data_collection": source.collection_contract})
    provenance = {
        "source_runs": source_rows, "source_registration_sha256": _digest(registration_path.read_bytes()),
        "extractor_sha256": _digest(Path(__file__).read_bytes()),
        "protocol_sha256": {role: _digest(Path(module.__file__).read_bytes()) for role, module in ROLE_MODULES.items()},
        "helper_sha256": {name: _digest((ROOT / "rwkv_lh" / name).read_bytes()) for name in ("role_trace_context.py", "role_trace_inputs.py", "role_trace_artifacts.py", "role_trace_labels.py", "role_trace_generation.py", "role_trace_stages.py")},
        "recomputed_rows": len(samples), "exclusions": exclusions,
        "requested_roles": list(roles),
        "coverage_scope_sha256": scope_sha,
        "server_input_token_ids_complete": all(row["context"].get("token_ids_complete") for row in samples) if samples else False,
        "output_kind": "candidate_audit_only", "training_started": False,
        "formal_dataset_version_created": False,
    }
    bundle = build_artifacts(samples, provenance=provenance, prior_regression=prior_regression,
                             expected_regression_fingerprint=expected_regression_fingerprint,
                             coverage_requirements=requirements)
    return write_artifacts(output, bundle)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    register = subparsers.add_parser("register", help="Hash and verify one frozen production case")
    register.add_argument("--case-dir", type=Path, required=True)
    for name in ("run-id", "source-run-id", "project-family", "suite"):
        register.add_argument("--" + name, required=True)
    register.add_argument("--output", type=Path, required=True)
    extract = subparsers.add_parser("extract", help="Write an immutable role candidate audit")
    extract.add_argument("--registration", type=Path, required=True)
    extract.add_argument("--output", type=Path, required=True)
    extract.add_argument("--role", action="append", choices=tuple(ROLE_MODULES))
    extract.add_argument("--prior-regression", type=Path, help="Explicitly provided frozen regression artifact (never inferred)")
    extract.add_argument("--regression-sha256", help="Pinned SHA-256 from the prior freeze registration")
    extract.add_argument("--expected-regression-fingerprint", help="Pinned regression identity, independent of the supplied file")
    args = parser.parse_args(argv)
    try:
        if args.command == "register":
            output = validate_output_path(args.output)
            value = register_case(args.case_dir, run_id=args.run_id, source_run_id=args.source_run_id,
                                  project_family=args.project_family, suite=args.suite)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as handle:
                handle.write(_canonical(value) + "\n")
            print(_canonical({"registration": str(output), "source_count": 1}))
            return 0
        prior = None
        if any((args.prior_regression, args.regression_sha256, args.expected_regression_fingerprint)):
            if not all((args.prior_regression, args.regression_sha256, args.expected_regression_fingerprint)):
                raise DatasetIntegrityError("regression reuse requires a file and both independent pins")
            prior = _json(read_artifact({"path": str(args.prior_regression.resolve()), "sha256": args.regression_sha256}, ROOT))
        manifest = extract_registration(args.registration, args.output, roles=args.role or tuple(ROLE_MODULES),
                                        prior_regression=prior, expected_regression_fingerprint=args.expected_regression_fingerprint)
        print(_canonical(manifest))
        return 0 if manifest.get("status") == "valid" else 2
    except (ValueError, OSError, sqlite3.Error) as exc:
        print(_canonical({"status": "rejected", "error": str(exc)}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
