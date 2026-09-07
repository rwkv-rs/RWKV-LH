"""Deterministic current-run trace comparison without semantic guesswork.

The comparator identifies role errors only from mechanical invariants or a
pre-frozen local checkpoint oracle. An external task failure without such a
link remains unattributed; it is never back-filled as a Selector error.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


TRACE_COMPARISON_SCHEMA = "rwkv-lh.trace-comparison.v2"
TRACE_ORACLE_SCHEMA = "rwkv-lh.trace-checkpoint-oracle.v2"


def sha256_path(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _event_data(event: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(event.get("data") or event.get("payload"))


def _event_position(event: Mapping[str, Any], fallback: int) -> tuple[int, int]:
    event_id = event.get("event_id")
    revision = event.get("revision")
    return (
        int(event_id) if isinstance(event_id, int) else fallback,
        int(revision) if isinstance(revision, int) else fallback,
    )


def _rejection_identities(data: Mapping[str, Any]) -> frozenset[str]:
    """Return stable identities shared by transient and durable rejection events."""

    return frozenset(
        str(value)
        for value in (data.get("request_id"), data.get("decision_id"))
        if str(value or "")
    )


def _planner_failure_recovered_before_action(
    events: Sequence[Mapping[str, Any]], event_index: int
) -> bool:
    """A rejected draft is not an Agent anomaly when its repair commits first.

    Strong Planner validation can reject a draft and immediately request one
    semantic repair.  The rejected draft never becomes executable state.  It
    is therefore diagnostic, rather than the first causal error, when a valid
    plan is committed before any action session or terminal boundary.
    """

    action_or_terminal_boundaries = {
        "action_session_started",
        "exact_tool_selection_staged",
        "model_call_accepted",
        "action_started",
        "run_blocked",
        "run_completed",
        "run_failed",
        "run_yielded",
    }
    for later in events[event_index + 1 :]:
        event_type = str(later.get("type") or "")
        if event_type == "goal_plan_patch_committed":
            return True
        if event_type in action_or_terminal_boundaries:
            return False
    return False


@dataclass(frozen=True)
class CheckpointOracle:
    step_id: str
    step_revision: int | None
    occurrence: int
    acceptable_operations: tuple[str, ...]
    expected_executor_params: Mapping[str, Any] | None
    expected_step_completed: bool | None

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "CheckpointOracle":
        operations = tuple(str(item) for item in value.get("acceptable_operations") or ())
        if not operations or len(set(operations)) != len(operations):
            raise ValueError("oracle acceptable_operations must be non-empty and unique")
        revision = value.get("step_revision")
        expected_params = value.get("expected_executor_params")
        if expected_params is not None and not isinstance(expected_params, Mapping):
            raise ValueError("expected_executor_params must be an object")
        expected_completed = value.get("expected_step_completed")
        if expected_completed is not None and not isinstance(expected_completed, bool):
            raise ValueError("expected_step_completed must be boolean")
        result = cls(
            step_id=str(value.get("step_id") or ""),
            step_revision=(int(revision) if revision is not None else None),
            occurrence=int(value.get("occurrence", 1)),
            acceptable_operations=operations,
            expected_executor_params=(dict(expected_params) if expected_params is not None else None),
            expected_step_completed=expected_completed,
        )
        if not result.step_id or result.occurrence < 1:
            raise ValueError("oracle checkpoint identity is invalid")
        return result


def load_oracle(path: Path | None) -> tuple[dict[str, tuple[CheckpointOracle, ...]], str]:
    if path is None:
        return {}, ""
    path = path.resolve()
    value = _read_json(path)
    if value.get("schema_version") != TRACE_ORACLE_SCHEMA:
        raise ValueError("unsupported trace checkpoint oracle")
    cases = value.get("cases")
    if not isinstance(cases, Mapping):
        raise ValueError("trace oracle cases must be an object")
    result: dict[str, tuple[CheckpointOracle, ...]] = {}
    for task_id, raw in cases.items():
        if not isinstance(raw, list):
            raise ValueError(f"trace oracle case must be an array: {task_id}")
        checkpoints = tuple(CheckpointOracle.from_dict(_mapping(item)) for item in raw)
        identities = [
            (item.step_id, item.step_revision, item.occurrence) for item in checkpoints
        ]
        if len(identities) != len(set(identities)):
            raise ValueError(f"duplicate trace oracle checkpoint: {task_id}")
        result[str(task_id)] = checkpoints
    return result, sha256_path(path)


def _selection_payload(data: Mapping[str, Any]) -> Mapping[str, Any]:
    selection = _mapping(data.get("selection"))
    raw = _mapping(selection.get("raw_selection"))
    if raw:
        return raw
    attestation = _mapping(data.get("selector_attestation"))
    return _mapping(attestation.get("raw_selection")) or selection or data


def _frontier_payload(event: Mapping[str, Any]) -> Mapping[str, Any] | None:
    if str(event.get("type") or "") != "action_observation_appended":
        return None
    model_event = _mapping(_event_data(event).get("model_event"))
    if str(model_event.get("event_type") or "") != "goal_frontier_assignment":
        return None
    return _mapping(_mapping(model_event.get("payload")).get("active_step"))


def _find_oracle(
    checkpoints: Sequence[CheckpointOracle],
    *,
    step_id: str,
    step_revision: int | None,
    occurrence: int,
) -> CheckpointOracle | None:
    for checkpoint in checkpoints:
        if (
            checkpoint.step_id == step_id
            and checkpoint.occurrence == occurrence
            and (
                checkpoint.step_revision is None
                or checkpoint.step_revision == step_revision
            )
        ):
            return checkpoint
    return None


def _anomaly(
    *,
    role: str,
    kind: str,
    event: Mapping[str, Any],
    event_index: int,
    evidence: Mapping[str, Any],
) -> dict[str, Any]:
    event_id, revision = _event_position(event, event_index + 1)
    return {
        "role": role,
        "kind": kind,
        "confidence": "exact",
        "event_index": event_index,
        "event_id": event_id,
        "revision": revision,
        "event_type": str(event.get("type") or ""),
        "evidence": dict(evidence),
    }


def analyze_case(
    *,
    task_id: str,
    result: Mapping[str, Any],
    events: Sequence[Mapping[str, Any]],
    oracle: Sequence[CheckpointOracle] = (),
) -> dict[str, Any]:
    frontier: Mapping[str, Any] = {}
    frontier_occurrences: Counter[tuple[str, int | None]] = Counter()
    selection_count = 0
    selection_records: list[dict[str, Any]] = []
    anomalies: list[dict[str, Any]] = []
    active_selection: dict[str, Any] | None = None
    started_actions: dict[str, tuple[int, Mapping[str, Any]]] = {}
    finished_actions: set[str] = set()
    repeated_selections: Counter[tuple[str, str]] = Counter()
    repeated_results: Counter[str] = Counter()
    audit_gap_count = 0
    audit_decision_count = 0
    audit_repair_count = 0
    audit_reported_gap_count = 0
    protocol_rejection_count = 0
    action_protocol_rejection_count = 0
    audit_protocol_rejection_count = 0
    recovered_planner_failures: list[dict[str, Any]] = []
    durable_rejection_identities = {
        identity
        for event in events
        if str(event.get("type") or "") == "protocol_rejection_recorded"
        for identity in _rejection_identities(_event_data(event))
    }

    for index, event in enumerate(events):
        event_type = str(event.get("type") or "")
        data = _event_data(event)
        new_frontier = _frontier_payload(event)
        if new_frontier is not None:
            frontier = new_frontier
            continue
        if event_type in {"strong_planner_patch_rejected", "strong_planner_call_failed"}:
            if _planner_failure_recovered_before_action(events, index):
                event_id, revision = _event_position(event, index + 1)
                recovered_planner_failures.append(
                    {
                        "event_index": index,
                        "event_id": event_id,
                        "revision": revision,
                        "event_type": event_type,
                        "recovered_before_action": True,
                    }
                )
                continue
            anomalies.append(
                _anomaly(
                    role="planner",
                    kind=event_type,
                    event=event,
                    event_index=index,
                    evidence={"error": data.get("error"), "reason": data.get("reason")},
                )
            )
            continue
        if event_type == "protocol_rejection_recorded":
            protocol_rejection_count += 1
            protocol_scope = str(data.get("protocol_scope") or "")
            if protocol_scope == "goal_audit":
                role = "auditor"
                kind = "auditor_protocol_rejected"
                audit_protocol_rejection_count += 1
            else:
                role = "executor"
                kind = "executor_protocol_rejected"
                action_protocol_rejection_count += 1
            anomalies.append(
                _anomaly(
                    role=role,
                    kind=kind,
                    event=event,
                    event_index=index,
                    evidence={
                        "protocol_scope": protocol_scope,
                        "request_id": data.get("request_id"),
                        "decision_id": data.get("decision_id"),
                        "selected_operation": data.get("selected_operation"),
                        "reason": data.get("reason"),
                        "error": data.get("error"),
                    },
                )
            )
            continue
        if event_type in {"model_protocol_rejected", "model_call_rejected"}:
            # A model_call_rejected event is the transient half of the durable
            # protocol_rejection_recorded event when request/decision IDs match.
            # Count and attribute the durable event exactly once.
            if _rejection_identities(data) & durable_rejection_identities:
                continue
            protocol_rejection_count += 1
            anomalies.append(
                _anomaly(
                    role="executor",
                    kind="executor_protocol_rejected_without_durable_record",
                    event=event,
                    event_index=index,
                    evidence={"reason": data.get("reason"), "error": data.get("error")},
                )
            )
            continue
        if event_type == "exact_tool_selection_rejected":
            protocol_rejection_count += 1
            anomalies.append(
                _anomaly(
                    role="selector",
                    kind="selector_selection_rejected",
                    event=event,
                    event_index=index,
                    evidence={"reason": data.get("reason"), "error": data.get("error")},
                )
            )
            continue
        if event_type == "exact_tool_selection_staged":
            selection_count += 1
            step_id = str(frontier.get("step_id") or "")
            raw_revision = frontier.get("step_revision")
            step_revision = int(raw_revision) if raw_revision is not None else None
            identity = (step_id, step_revision)
            frontier_occurrences[identity] += 1
            occurrence = frontier_occurrences[identity]
            selection = _selection_payload(data)
            selected = str(
                selection.get("selected_operation")
                or data.get("selected_operation")
                or ""
            )
            eligible = tuple(str(item) for item in selection.get("eligible_labels") or ())
            matched = _find_oracle(
                oracle,
                step_id=step_id,
                step_revision=step_revision,
                occurrence=occurrence,
            )
            record = {
                "selection_index": selection_count,
                "event_index": index,
                "step_id": step_id,
                "step_revision": step_revision,
                "occurrence": occurrence,
                "objective": str(frontier.get("objective") or ""),
                "selected_operation": selected,
                "eligible_labels": list(eligible),
                "selector_profile_id": str(
                    selection.get("profile_id")
                    or _mapping(data.get("selection")).get("selector_profile_id")
                    or ""
                ),
                "selector_profile_sha256": str(
                    selection.get("profile_sha256")
                    or _mapping(data.get("selection")).get("selector_profile_sha256")
                    or ""
                ),
                "selector_decoder_id": str(
                    selection.get("decoder_id")
                    or _mapping(data.get("selection")).get("selector_decoder_id")
                    or ""
                ),
                "selector_decoder_sha256": str(
                    selection.get("decoder_sha256")
                    or _mapping(data.get("selection")).get(
                        "selector_decoder_sha256"
                    )
                    or ""
                ),
                "selector_decoder_protocol": str(
                    selection.get("decoder_protocol")
                    or _mapping(data.get("selection")).get(
                        "selector_decoder_protocol"
                    )
                    or ""
                ),
                "oracle_matched": matched is not None,
                "acceptable_operations": (
                    list(matched.acceptable_operations) if matched is not None else []
                ),
            }
            selection_records.append(record)
            active_selection = {"record": record, "oracle": matched}
            repeated_selections[(step_id, selected)] += 1
            if matched is not None:
                allowed = set(matched.acceptable_operations)
                if not (allowed & set(eligible)):
                    anomalies.append(
                        _anomaly(
                            role="controller",
                            kind="required_operation_absent_from_eligibility",
                            event=event,
                            event_index=index,
                            evidence={
                                "step_id": step_id,
                                "acceptable_operations": sorted(allowed),
                                "eligible_labels": list(eligible),
                            },
                        )
                    )
                elif selected not in allowed:
                    anomalies.append(
                        _anomaly(
                            role="selector",
                            kind="selected_operation_outside_oracle_set",
                            event=event,
                            event_index=index,
                            evidence={
                                "step_id": step_id,
                                "selected_operation": selected,
                                "acceptable_operations": sorted(allowed),
                            },
                        )
                    )
            continue
        if event_type == "model_call_accepted":
            operation = str(data.get("operation") or "")
            if active_selection is not None:
                selected = active_selection["record"]["selected_operation"]
                if operation != selected:
                    anomalies.append(
                        _anomaly(
                            role="executor",
                            kind="executor_changed_selected_operation",
                            event=event,
                            event_index=index,
                            evidence={"selected_operation": selected, "executor_operation": operation},
                        )
                    )
                checkpoint = active_selection["oracle"]
                if checkpoint is not None and checkpoint.expected_executor_params is not None:
                    normalized = _mapping(
                        _mapping(data.get("argument_normalization")).get("normalized_action")
                    )
                    actual_params = _mapping(normalized.get("arguments"))
                    if dict(actual_params) != dict(checkpoint.expected_executor_params):
                        anomalies.append(
                            _anomaly(
                                role="executor",
                                kind="executor_params_differ_from_oracle",
                                event=event,
                                event_index=index,
                                evidence={
                                    "expected_params": dict(checkpoint.expected_executor_params),
                                    "actual_params": dict(actual_params),
                                },
                            )
                        )
            continue
        if event_type == "action_started":
            action_id = str(data.get("action_id") or "")
            if action_id:
                started_actions[action_id] = (index, event)
            continue
        if event_type == "action_finished":
            action_id = str(data.get("action_id") or "")
            finished_actions.add(action_id)
            digest = str(data.get("result_digest") or "")
            if digest:
                repeated_results[digest] += 1
            continue
        if event_type == "goal_step_evidence_gap_recorded":
            audit_gap_count += 1
            continue
        if event_type == "goal_audit_recorded":
            audit_decision_count += 1
            audit = _mapping(data.get("audit"))
            verdict = str(audit.get("verdict") or "")
            gaps = tuple(str(item) for item in audit.get("gaps") or ())
            audit_reported_gap_count += len(gaps)
            if verdict == "repair":
                audit_repair_count += 1
            if active_selection is None:
                continue
            checkpoint = active_selection["oracle"]
            audited_step_id = str(audit.get("step_id") or "")
            selected_step_id = str(active_selection["record"].get("step_id") or "")
            if (
                checkpoint is not None
                and checkpoint.expected_step_completed is not None
                and audited_step_id == selected_step_id
            ):
                completed_steps = {
                    str(_mapping(item).get("step_id") or "")
                    for item in audit.get("completed_steps") or ()
                }
                actual = audited_step_id in completed_steps
                if actual != checkpoint.expected_step_completed:
                    anomalies.append(
                        _anomaly(
                            role="auditor",
                            kind="audit_completion_differs_from_oracle",
                            event=event,
                            event_index=index,
                            evidence={
                                "expected_step_completed": checkpoint.expected_step_completed,
                                "actual_step_completed": actual,
                                "verdict": verdict,
                                "gaps": list(gaps),
                            },
                        )
                    )
            continue

    for action_id, (index, event) in started_actions.items():
        if action_id not in finished_actions:
            anomalies.append(
                _anomaly(
                    role="harness",
                    kind="started_action_has_no_terminal_event",
                    event=event,
                    event_index=index,
                    evidence={"action_id": action_id},
                )
            )
    anomalies.sort(key=lambda item: (item["event_index"], item["role"], item["kind"]))
    first = anomalies[0] if anomalies else None
    first_index = int(first["event_index"]) if first is not None else -1
    amplification: list[dict[str, Any]] = []
    if first is not None:
        for index, event in enumerate(events):
            if index <= first_index:
                continue
            event_type = str(event.get("type") or "")
            data = _event_data(event)
            if event_type in {
                "action_started",
                "action_finished",
                "goal_step_evidence_gap_recorded",
                "goal_audit_boundary_resolved",
                "run_blocked",
                "run_yielded",
            }:
                event_id, revision = _event_position(event, index + 1)
                amplification.append(
                    {
                        "event_index": index,
                        "event_id": event_id,
                        "revision": revision,
                        "event_type": event_type,
                        "action_id": str(data.get("action_id") or ""),
                        "reason": str(data.get("reason") or ""),
                        "step_completed": data.get("step_completed"),
                    }
                )
    repeated_selection_count = sum(
        count - 1 for count in repeated_selections.values() if count > 1
    )
    repeated_result_count = sum(
        count - 1 for count in repeated_results.values() if count > 1
    )
    unattributed_failure = bool(
        not result.get("passed") and first is None
    )
    return {
        "task_id": task_id,
        "passed": bool(result.get("passed")),
        "agent_completed": bool(result.get("agent_completed")),
        "external_passed": bool(result.get("external_passed")),
        "status": str(result.get("status") or ""),
        "event_count": len(events),
        "action_count": int(result.get("action_count") or 0),
        "selection_count": selection_count,
        "oracle_checkpoint_count": len(oracle),
        "oracle_matched_selection_count": sum(
            bool(item["oracle_matched"]) for item in selection_records
        ),
        "protocol_rejection_count": max(
            protocol_rejection_count,
            int(result.get("protocol_rejection_count") or 0),
        ),
        "action_protocol_rejection_count": action_protocol_rejection_count,
        "audit_protocol_rejection_count": audit_protocol_rejection_count,
        "audit_decision_count": audit_decision_count,
        "audit_repair_count": audit_repair_count,
        "audit_reported_gap_count": audit_reported_gap_count,
        "audit_evidence_gap_count": audit_gap_count,
        "recovered_planner_failure_count": len(recovered_planner_failures),
        "recovered_planner_failures": recovered_planner_failures,
        "repeated_step_operation_count": repeated_selection_count,
        "repeated_result_digest_count": repeated_result_count,
        "selections": selection_records,
        "verified_anomalies": anomalies,
        "first_verified_anomaly": first,
        "amplification_chain": amplification,
        "unattributed_failure": unattributed_failure,
        "attribution_policy": (
            "mechanical_or_frozen_oracle_only; external failure alone is unattributed"
        ),
    }


def analyze_run(
    *,
    name: str,
    run_directory: Path,
    oracle: Mapping[str, Sequence[CheckpointOracle]],
) -> dict[str, Any]:
    run_directory = run_directory.resolve()
    results_path = run_directory / "results.json"
    payload = _read_json(results_path)
    if payload.get("schema_version") != "rwkv-e2e.results.v1":
        raise ValueError(f"unsupported results schema: {results_path}")
    cases = []
    for result in payload.get("results") or []:
        task_id = str(result["task_id"])
        event_path = run_directory / "cases" / task_id / "event_log.json"
        events = _read_json(event_path)
        if not isinstance(events, list) or any(not isinstance(item, Mapping) for item in events):
            raise ValueError(f"invalid event log: {event_path}")
        cases.append(
            analyze_case(
                task_id=task_id,
                result=result,
                events=events,
                oracle=oracle.get(task_id, ()),
            )
        )
    roles = Counter(
        str(case["first_verified_anomaly"]["role"])
        for case in cases
        if case["first_verified_anomaly"] is not None
    )
    return {
        "name": name,
        "run_directory": str(run_directory),
        "results_sha256": sha256_path(results_path),
        "case_count": len(cases),
        "passed_count": sum(case["passed"] for case in cases),
        "agent_completed_count": sum(case["agent_completed"] for case in cases),
        "external_passed_count": sum(case["external_passed"] for case in cases),
        "action_count": sum(case["action_count"] for case in cases),
        "protocol_rejection_count": sum(case["protocol_rejection_count"] for case in cases),
        "repeated_step_operation_count": sum(
            case["repeated_step_operation_count"] for case in cases
        ),
        "audit_evidence_gap_count": sum(case["audit_evidence_gap_count"] for case in cases),
        "unattributed_failure_count": sum(case["unattributed_failure"] for case in cases),
        "first_verified_anomaly_roles": dict(sorted(roles.items())),
        "cases": cases,
    }


def compare_runs(
    *,
    runs: Sequence[tuple[str, Path]],
    oracle_path: Path | None,
) -> dict[str, Any]:
    if len(runs) < 2 or len({name for name, _ in runs}) != len(runs):
        raise ValueError("trace comparison requires at least two uniquely named runs")
    oracle, oracle_sha256 = load_oracle(oracle_path)
    analyzed = [
        analyze_run(name=name, run_directory=path, oracle=oracle)
        for name, path in runs
    ]
    task_sets = [{case["task_id"] for case in run["cases"]} for run in analyzed]
    if any(task_set != task_sets[0] for task_set in task_sets[1:]):
        raise ValueError("paired trace runs contain different task ids")
    by_run = {
        run["name"]: {case["task_id"]: case for case in run["cases"]}
        for run in analyzed
    }
    paired_cases = []
    for task_id in sorted(task_sets[0]):
        values = {name: by_run[name][task_id] for name, _ in runs}
        paired_cases.append(
            {
                "task_id": task_id,
                "runs": {
                    name: {
                        "passed": value["passed"],
                        "status": value["status"],
                        "action_count": value["action_count"],
                        "protocol_rejection_count": value["protocol_rejection_count"],
                        "repeated_step_operation_count": value[
                            "repeated_step_operation_count"
                        ],
                        "first_verified_anomaly_role": (
                            value["first_verified_anomaly"]["role"]
                            if value["first_verified_anomaly"] is not None
                            else None
                        ),
                        "unattributed_failure": value["unattributed_failure"],
                    }
                    for name, value in values.items()
                },
            }
        )
    return {
        "schema_version": TRACE_COMPARISON_SCHEMA,
        "oracle_path": str(oracle_path.resolve()) if oracle_path is not None else "",
        "oracle_sha256": oracle_sha256,
        "semantic_attribution_enabled": bool(oracle_path),
        "historical_root_cause_prior_used": False,
        "planner_variability": {
            "ignored": True,
            "ignored_fields": [
                "exact_plan_text",
                "step_count",
                "step_ids",
                "phase_or_stage_labels",
                "step_order",
            ],
            "comparison_basis": [
                "goal_obligation_coverage",
                "harness_valid_actions",
                "task_completion",
                "external_verifier_acceptance",
            ],
        },
        "run_count": len(analyzed),
        "paired_task_count": len(paired_cases),
        "runs": analyzed,
        "paired_cases": paired_cases,
    }


__all__ = [
    "TRACE_COMPARISON_SCHEMA",
    "TRACE_ORACLE_SCHEMA",
    "CheckpointOracle",
    "analyze_case",
    "analyze_run",
    "compare_runs",
    "load_oracle",
]
