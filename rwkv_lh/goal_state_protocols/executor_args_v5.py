"""Observation-conditioned production/data protocol for the G1J Executor.

V5 owns the typed progress contract and makes the factual authority of
the preceding Harness observations explicit.  A navigation summary may help the
model find material, but it is never authority for a path, source literal, cursor,
or read-modify-write base revision.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields, _nonempty, _objects, _render, _strict_command, _strings,
)
from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.model_io import ModelCommand, TOOL_CALL_JSON_CONTINUATION_ANCHOR
from rwkv_lh.observation_funnel import OBSERVATION_PROJECTION_VERSION


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.executor-args.v5"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION
PROMPT_PREFIX = "ExecutorArgsPromptV5: "
OBSERVATION_BINDING_SCHEMA_VERSION = "rwkv-lh.executor-observation-binding.v1"
TARGET_CONTRACT_SCHEMA_VERSION = "rwkv-lh.goal-step-target-contract.v2"
EXACT_SOURCE_RULE = (
    "mutation_literals_must_be_copied_from_exact_spans_or_literal_structured_fields"
)
STALE_SNAPSHOT_POLICY = "read_modify_write_requires_matching_base_sha256"

_PROMPT_FIELDS = (
    "current_requirement",
    "execution_state",
    "observation_binding",
    "selected_operation",
    "selected_tool_contract",
    "committed_fact_refs",
    "executor_history",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "command", "fixture_id", "execution_verifier_id")
_OBSERVATION_BINDING_FIELDS = (
    "schema_version",
    "projection_version",
    "fact_action_ids",
    "exact_source_rule",
    "summary_fact_authority",
    "stale_snapshot_policy",
)


_EXECUTION_STATE_FIELDS = (
    "active_step_id",
    "active_step_revision",
    "declared_phase",
    "effective_phase",
    "assigned_action_count",
    "successful_action_count",
    "failed_action_count",
    "remaining_read_roots",
    "remaining_write_roots",
    "last_action",
    "feedback",
    "target_contract",
)
_LAST_ACTION_FIELDS = (
    "action_id",
    "operation",
    "status",
    "arguments",
    "result_progress",
)
_RESULT_PROGRESS_FIELDS = (
    "success",
    "outcome_type",
    "complete",
    "truncated",
    "next_start_byte",
    "next_cursor",
    "error_type",
    "error_message",
)
_TARGET_CONTRACT_FIELDS = (
    "schema_version",
    "phase",
    "roots",
    "target_descriptors",
    "compatible_targets_by_operation",
    "discovery_complete",
)
_PHASES = {"observe", "mutate", "execute", "derive_evidence"}
_TARGET_KINDS = {
    "directory",
    "json_file",
    "text_file",
    "binary_file",
    "large_file",
    "missing",
    "other",
}


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _validate_target_contract(value: Any) -> Mapping[str, Any]:
    contract = _exact_fields(value, _TARGET_CONTRACT_FIELDS, "target_contract")
    if contract["schema_version"] != TARGET_CONTRACT_SCHEMA_VERSION:
        raise ValueError("target_contract schema is invalid")
    if contract["phase"] not in _PHASES:
        raise ValueError("target_contract phase is invalid")
    _strings(contract["roots"], "target_contract.roots")
    descriptors = contract["target_descriptors"]
    if not isinstance(descriptors, list):
        raise ValueError("target_contract.target_descriptors must be an array")
    descriptor_paths: set[str] = set()
    for descriptor in descriptors:
        if not isinstance(descriptor, Mapping):
            raise ValueError("target descriptor must be an object")
        fields = set(descriptor)
        required = {"path", "type", "target_kind", "exists"}
        if not required <= fields <= required | {"size_bytes"}:
            raise ValueError("target descriptor fields mismatch")
        path = _nonempty(descriptor["path"], "target descriptor path")
        if path in descriptor_paths:
            raise ValueError("target descriptor paths must be unique")
        descriptor_paths.add(path)
        if descriptor["target_kind"] not in _TARGET_KINDS:
            raise ValueError("target descriptor kind is invalid")
        if not isinstance(descriptor["exists"], bool):
            raise ValueError("target descriptor exists must be boolean")
        if "size_bytes" in descriptor:
            _nonnegative_int(descriptor["size_bytes"], "target descriptor size_bytes")
    if not isinstance(contract["discovery_complete"], bool):
        raise ValueError("target discovery completeness must be explicit")
    compatible = contract["compatible_targets_by_operation"]
    if not isinstance(compatible, Mapping):
        raise ValueError("compatible_targets_by_operation must be an object")
    for operation, paths in compatible.items():
        _nonempty(operation, "compatible target operation")
        _strings(paths, f"compatible targets for {operation}")
        if not set(paths) <= descriptor_paths:
            raise ValueError("compatible target path lacks a typed descriptor")
    return contract


def build_target_contract(
    *,
    phase: str,
    roots: Sequence[str],
    target_descriptors: Sequence[Mapping[str, Any]],
    compatible_targets_by_operation: Mapping[str, Sequence[str]],
    discovery_complete: bool = True,
) -> dict[str, Any]:
    """Project Harness descriptors into the exact Executor target contract."""
    contract = {
        "schema_version": TARGET_CONTRACT_SCHEMA_VERSION,
        "phase": phase,
        "roots": list(roots),
        "target_descriptors": [
            {key: item[key] for key in ("path", "type", "target_kind", "exists", "size_bytes")
             if key in item}
            for item in target_descriptors
        ],
        "compatible_targets_by_operation": {
            operation: list(paths) for operation, paths in compatible_targets_by_operation.items()
        },
    }
    contract["discovery_complete"] = discovery_complete
    _validate_target_contract(contract)
    return contract


def _validate_execution_state(value: Any) -> Mapping[str, Any]:
    state = _exact_fields(value, _EXECUTION_STATE_FIELDS, "execution_state")
    _nonempty(state["active_step_id"], "execution_state.active_step_id")
    revision = _nonnegative_int(
        state["active_step_revision"], "execution_state.active_step_revision"
    )
    if revision < 1:
        raise ValueError("execution_state.active_step_revision must be positive")
    for name in ("declared_phase", "effective_phase"):
        if state[name] not in _PHASES:
            raise ValueError(f"execution_state.{name} is invalid")
    assigned = _nonnegative_int(
        state["assigned_action_count"], "execution_state.assigned_action_count"
    )
    successful = _nonnegative_int(
        state["successful_action_count"], "execution_state.successful_action_count"
    )
    failed = _nonnegative_int(
        state["failed_action_count"], "execution_state.failed_action_count"
    )
    if successful + failed != assigned:
        raise ValueError("execution_state action counters are inconsistent")
    _strings(state["remaining_read_roots"], "execution_state.remaining_read_roots")
    _strings(state["remaining_write_roots"], "execution_state.remaining_write_roots")
    validate_feedback(state["feedback"], recipient="executor_args")
    _validate_target_contract(state["target_contract"])

    last_action = state["last_action"]
    if assigned == 0:
        if last_action is not None:
            raise ValueError("execution_state without actions cannot carry last_action")
        return state
    if last_action is None:
        raise ValueError("execution_state with actions requires last_action")
    last = _exact_fields(last_action, _LAST_ACTION_FIELDS, "last_action")
    _nonempty(last["action_id"], "last_action.action_id")
    _nonempty(last["operation"], "last_action.operation")
    _nonempty(last["status"], "last_action.status")
    if not isinstance(last["arguments"], Mapping):
        raise ValueError("last_action.arguments must be an object")
    progress = _exact_fields(
        last["result_progress"], _RESULT_PROGRESS_FIELDS, "last_action.result_progress"
    )
    if not isinstance(progress["success"], bool):
        raise ValueError("last_action.result_progress.success must be boolean")
    _nonempty(progress["outcome_type"], "last_action.result_progress.outcome_type")
    for name in ("complete", "truncated"):
        if progress[name] is not None and not isinstance(progress[name], bool):
            raise ValueError(f"last_action.result_progress.{name} is invalid")
    if progress["next_start_byte"] is not None:
        _nonnegative_int(
            progress["next_start_byte"],
            "last_action.result_progress.next_start_byte",
        )
    if not isinstance(progress["next_cursor"], str):
        raise ValueError("last_action.result_progress.next_cursor must be a string")
    if not isinstance(progress["error_type"], str):
        raise ValueError("last_action.result_progress.error_type must be a string")
    if not isinstance(progress["error_message"], str) or len(
        progress["error_message"]
    ) > 1200:
        raise ValueError("last_action.result_progress.error_message is invalid")
    return state


def build_execution_state(
    *,
    active_step_id: str,
    active_step_revision: int,
    declared_phase: str,
    effective_phase: str,
    assigned_actions: Sequence[Any],
    mechanical_evidence: Mapping[str, Any],
    target_contract: Mapping[str, Any],
    feedback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project step-bound durable Harness actions through the one current constructor.

    Callers select the active step revision's actions in causal sequence order.
    Production, trace extraction and evaluation share this exact projection;
    action counts and continuation fields are derived from Harness records.
    """
    if any(str(action.status.value) == "running" for action in assigned_actions):
        raise ValueError("Executor progress cannot include a running action")
    successful = [
        action for action in assigned_actions
        if str(action.status.value) == "succeeded"
        and bool((action.result or {}).get("success"))
    ]
    last_action = None
    if assigned_actions:
        latest = assigned_actions[-1]
        result = dict(latest.result or {})
        metadata = result.get("metadata")
        metadata = metadata if isinstance(metadata, Mapping) else {}
        error = getattr(latest, "error", None)
        if not isinstance(error, Mapping):
            error = result.get("error")
        error = error if isinstance(error, Mapping) else {}
        next_start_byte = metadata.get("next_start_byte")
        if (
            isinstance(next_start_byte, bool)
            or not isinstance(next_start_byte, int)
            or next_start_byte < 0
        ):
            next_start_byte = None
        next_cursor = metadata.get("next_cursor")
        complete = metadata.get("complete")
        truncated = metadata.get("truncated")
        last_action = {
            "action_id": latest.action_id,
            "operation": latest.action_type,
            "status": str(latest.status.value),
            "arguments": dict(latest.arguments),
            "result_progress": {
                "success": bool(result.get("success")),
                "outcome_type": str(
                    result.get("outcome_type")
                    or getattr(latest, "outcome_type", None) or "pending"
                ),
                "complete": complete if isinstance(complete, bool) else None,
                "truncated": truncated if isinstance(truncated, bool) else None,
                "next_start_byte": next_start_byte,
                "next_cursor": next_cursor if isinstance(next_cursor, str) else "",
                "error_type": str(error.get("type") or ""),
                "error_message": str(error.get("message") or "")[:1200],
            },
        }
    state = {
        "active_step_id": active_step_id,
        "active_step_revision": active_step_revision,
        "declared_phase": declared_phase,
        "effective_phase": effective_phase,
        "assigned_action_count": len(assigned_actions),
        "successful_action_count": len(successful),
        "failed_action_count": len(assigned_actions) - len(successful),
        "remaining_read_roots": list(mechanical_evidence.get("missing_read_roots") or ()),
        "remaining_write_roots": list(mechanical_evidence.get("missing_write_roots") or ()),
        "last_action": last_action,
        "feedback": dict(feedback) if feedback is not None else None,
        "target_contract": dict(target_contract),
    }
    _validate_execution_state(state)
    return state


def build_prompt_source(
    *,
    current_requirement: str,
    execution_state: Mapping[str, Any],
    selected_operation: str,
    selected_tool_contract: Mapping[str, Any],
    committed_fact_refs: Sequence[str],
    executor_history: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Build and validate the same ordered input for runtime, data and evaluation."""
    facts = sorted(set(committed_fact_refs))
    source = {
        "current_requirement": current_requirement,
        "execution_state": dict(execution_state),
        "observation_binding": observation_binding(facts),
        "selected_operation": selected_operation,
        "selected_tool_contract": dict(selected_tool_contract),
        "committed_fact_refs": facts,
        "executor_history": [dict(item) for item in executor_history],
    }
    _validate_prompt_source(source)
    return source


def build_source(
    *,
    current_requirement: str,
    execution_state: Mapping[str, Any],
    selected_operation: str,
    selected_tool_contract: Mapping[str, Any],
    committed_fact_refs: Sequence[str],
    executor_history: Sequence[Mapping[str, Any]],
    command: Mapping[str, Any],
    fixture_id: str,
    execution_verifier_id: str,
) -> dict[str, Any]:
    """Attach a trace-backed target to the shared prompt input."""
    source = build_prompt_source(
        current_requirement=current_requirement, execution_state=execution_state,
        selected_operation=selected_operation, selected_tool_contract=selected_tool_contract,
        committed_fact_refs=committed_fact_refs, executor_history=executor_history,
    )
    source.update(command=dict(command), fixture_id=fixture_id,
                  execution_verifier_id=execution_verifier_id)
    validate_source(source)
    return source




def observation_binding(fact_action_ids: Sequence[str]) -> dict[str, Any]:
    """Build the one frozen factual-authority contract used by data and runtime."""

    selected = tuple(sorted(dict.fromkeys(str(item) for item in fact_action_ids)))
    return {
        "schema_version": OBSERVATION_BINDING_SCHEMA_VERSION,
        "projection_version": OBSERVATION_PROJECTION_VERSION,
        "fact_action_ids": list(selected),
        "exact_source_rule": EXACT_SOURCE_RULE,
        "summary_fact_authority": False,
        "stale_snapshot_policy": STALE_SNAPSHOT_POLICY,
    }


def _validate_observation_binding(
    value: Any,
    *,
    committed_fact_refs: Sequence[str],
) -> Mapping[str, Any]:
    selected = _exact_fields(
        value,
        _OBSERVATION_BINDING_FIELDS,
        "observation_binding",
    )
    if selected["schema_version"] != OBSERVATION_BINDING_SCHEMA_VERSION:
        raise ValueError("observation_binding schema is invalid")
    if selected["projection_version"] != OBSERVATION_PROJECTION_VERSION:
        raise ValueError("observation projection version is invalid")
    fact_action_ids = _strings(
        selected["fact_action_ids"],
        "observation_binding.fact_action_ids",
        sorted_unique=True,
    )
    if fact_action_ids != tuple(committed_fact_refs):
        raise ValueError(
            "observation_binding facts must exactly match committed_fact_refs"
        )
    if selected["exact_source_rule"] != EXACT_SOURCE_RULE:
        raise ValueError("observation_binding exact source rule is invalid")
    if selected["summary_fact_authority"] is not False:
        raise ValueError("navigation summaries cannot have factual authority")
    if selected["stale_snapshot_policy"] != STALE_SNAPSHOT_POLICY:
        raise ValueError("observation_binding stale snapshot policy is invalid")
    return selected


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "executor prompt source")
    _nonempty(selected["current_requirement"], "current_requirement")
    _validate_execution_state(selected["execution_state"])
    operation = _nonempty(selected["selected_operation"], "selected_operation")
    if operation in {"final_answer", "ABSTAIN"}:
        raise ValueError("Executor-Args cannot receive a terminal or abstain operation")
    contract = selected["selected_tool_contract"]
    if not isinstance(contract, Mapping) or not contract:
        raise ValueError("selected_tool_contract must be a non-empty object")
    if str(contract.get("name") or "") != operation:
        raise ValueError("selected_tool_contract must match selected_operation")
    _strings(selected["committed_fact_refs"], "committed_fact_refs", sorted_unique=True)
    _objects(selected["executor_history"], "executor_history")
    _validate_observation_binding(
        selected["observation_binding"],
        committed_fact_refs=tuple(selected["committed_fact_refs"]),
    )
    return selected


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "executor source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    command = _exact_fields(selected["command"], ("function", "params"), "command")
    if command["function"] != selected["selected_operation"]:
        raise ValueError("command function must preserve selected_operation")
    if not isinstance(command["params"], Mapping):
        raise ValueError("command.params must be an object")
    _nonempty(selected["fixture_id"], "fixture_id")
    _nonempty(selected["execution_verifier_id"], "execution_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "executor render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "executor_args",
        "current_requirement": prompt["current_requirement"],
        "execution_state": dict(prompt["execution_state"]),
        "observation_binding": dict(prompt["observation_binding"]),
        "selected_operation": prompt["selected_operation"],
        "selected_tool_contract": dict(prompt["selected_tool_contract"]),
        "committed_fact_refs": list(prompt["committed_fact_refs"]),
        "executor_history": [dict(item) for item in prompt["executor_history"]],
        "current_question": (
            "Return one canonical direct call for the selected operation. Derive each "
            "factual parameter from the bound Harness observations. Copy code, text, "
            "paths, cursors, identifiers, and structured values exactly; a navigation "
            "summary is not factual evidence. For patch_json, replace_text, or "
            "remove_line, include the exact current file base_sha256. Do not select "
            "another operation or answer the user."
        ),
    }
    return _render(PROMPT_PREFIX, payload)


def render_target(source: Any) -> str:
    validate_source(source)
    command = source["command"]
    return ModelCommand(str(command["function"]), dict(command["params"])).canonical


def render_generation_prompt(source: Any) -> str:
    return render_prompt(source) + TOOL_CALL_JSON_CONTINUATION_ANCHOR


def parse_target(target: str) -> ModelCommand:
    from rwkv_lh.model_io import parse_model_command

    parsed = parse_model_command(target)
    command = _strict_command(target, parsed.name)
    if command.name in {"final_answer", "ABSTAIN"}:
        raise ValueError("Executor-Args target cannot be terminal or abstain")
    return command


__all__ = [
    "EXACT_SOURCE_RULE",
    "INPUT_SCHEMA_VERSION",
    "OBSERVATION_BINDING_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "PROMPT_PREFIX",
    "STALE_SNAPSHOT_POLICY",
    "TARGET_CONTRACT_SCHEMA_VERSION",
    "build_execution_state",
    "build_prompt_source",
    "build_source",
    "build_target_contract",
    "observation_binding",
    "parse_target",
    "render_generation_prompt",
    "render_prompt",
    "render_target",
    "validate_source",
]
