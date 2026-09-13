"""Failure-aware native G1J Selector renderer and exact suffix contract.

V7 carries step-bound audit feedback as well as the bounded facts the root-cause audit found
missing from the Selector's next input: the previous action's arguments, its
Harness error type/message, its result metadata, and the typed workspace
targets the Controller already resolved for the active step.  Production,
StateTune data generation, and acceptance evaluation must all build
``current_progress`` through :func:`build_current_progress` so the three
surfaces share one distribution byte for byte.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields,
    _mapping,
    _nonempty,
    _nonnegative_int,
    _render,
    _strings,
)
from rwkv_lh.goal_state_protocols.feedback import validate_feedback
from rwkv_lh.goal_state_protocols.execution_failures import build_rejections, validate_rejections
from rwkv_lh.operation_contracts import GOAL_STEP_PHASES, WORKSPACE_TARGET_KINDS, summarize_operation_targets
from rwkv_lh.observation_funnel import project_action_result


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v7"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION
PROMPT_PREFIX = "SelectorIntentPromptV7: "
TARGET_PREFIX = "\nSelectorIntentV7: "
MENU_PREFIX = "SelectorIntentMenuV7: "
ROLE_PREFIX = "SelectorIntentRoleV7: "
ROLE_MARKER = "\n" + ROLE_PREFIX
MENU_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.selector-intent-menu.v7"
ENDPOINT = "/selector-intent-v7/select"

SUBTASK_FIELDS = (
    "objective",
    "phase",
    "read_roots",
    "write_roots",
    "success_evidence",
    "constraints",
)
PROGRESS_FIELDS = (
    "assigned_action_count",
    "successful_action_count",
    "failed_action_count",
    "last_action",
    "missing_read_roots",
    "missing_write_roots",
    "workspace_targets",
    "mechanical_preconditions_satisfied",
    "completion_authority",
    "evidence_records",
    "feedback",
    "target_discovery_complete",
    "recent_rejections",
    "operation_targets",
)
LAST_ACTION_FIELDS = (
    "operation",
    "status",
    "arguments",
    "error_type",
    "error_message",
    "result_metadata",
    "observed_roots",
    "mutated_roots",
    "observation",
)
WORKSPACE_TARGET_FIELDS = ("path", "target_kind")
_PROMPT_FIELDS = ("current_subtask", "current_progress", "eligible_labels")
_SOURCE_FIELDS = (
    *_PROMPT_FIELDS,
    "selected_operation",
    "selection_authority",
    "selection_verifier_id",
)
_AUTHORITIES = frozenset({"planner_contract", "executed_fixture", "human_double_review"})
_PHASES = frozenset(GOAL_STEP_PHASES)
_ACTION_STATUSES = frozenset({"succeeded", "failed", "interrupted"})

# Bounds are part of the frozen contract: they cap prompt growth and keep the
# projection identical between the Controller and the data builder.
MAX_ARGUMENT_KEYS = 8
MAX_ARGUMENT_CHARS = 160
MAX_ERROR_MESSAGE_CHARS = 240
MAX_WORKSPACE_TARGETS = 32
RESULT_METADATA_KEYS = (
    "outcome_type",
    "exit_code",
    "target_kind",
    "entry_count",
    "match_count",
    "byte_count",
    "size_bytes",
    "truncated",
    "changed_path_count",
)


def _bounded_text(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else str(value)
    text = text.replace("\r\n", "\n")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _scalar_text(value: Any, limit: int) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (int, float, str)):
        return _bounded_text(value, limit)
    # Structured argument values keep only their type and size; the Selector
    # chooses an operation and must not see full payloads.
    if isinstance(value, Mapping):
        return f"<object:{len(value)} keys>"
    if isinstance(value, Sequence):
        return f"<array:{len(value)} items>"
    return _bounded_text(repr(value), limit)


def project_arguments(arguments: Mapping[str, Any] | None) -> dict[str, str]:
    """Bound the previous action's arguments to short scalar strings."""

    if not arguments:
        return {}
    projected: dict[str, str] = {}
    for key in list(arguments)[:MAX_ARGUMENT_KEYS]:
        projected[str(key)] = _scalar_text(arguments[key], MAX_ARGUMENT_CHARS)
    return projected


def project_result_metadata(
    metadata: Mapping[str, Any] | None,
    *,
    outcome_type: str | None = None,
    exit_code: int | None = None,
) -> dict[str, Any]:
    """Keep only whitelisted scalar result facts."""

    source: dict[str, Any] = {}
    if outcome_type:
        source["outcome_type"] = str(outcome_type)
    if exit_code is not None:
        source["exit_code"] = int(exit_code)
    if metadata:
        for key in RESULT_METADATA_KEYS:
            if key in source or key not in metadata:
                continue
            value = metadata[key]
            if isinstance(value, bool) or value is None:
                source[key] = value
            elif isinstance(value, (int, float)):
                source[key] = value
            elif isinstance(value, str):
                source[key] = _bounded_text(value, MAX_ARGUMENT_CHARS)
    return {key: source[key] for key in RESULT_METADATA_KEYS if key in source}


def project_last_action(
    *,
    operation: str,
    status: str,
    succeeded: bool,
    arguments: Mapping[str, Any] | None,
    error: Mapping[str, Any] | None,
    result_metadata: Mapping[str, Any] | None,
    observed_roots: Sequence[str],
    mutated_roots: Sequence[str],
    outcome_type: str | None = None,
    exit_code: int | None = None,
    result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Project one durable Harness action into the exact current ``last_action``."""

    error_type: str | None = None
    error_message: str | None = None
    if not succeeded:
        error_type = str((error or {}).get("type") or outcome_type or "failed")
        message = (error or {}).get("message")
        if message is None:
            message = (error or {}).get("detail")
        error_message = _bounded_text(message, MAX_ERROR_MESSAGE_CHARS) if message else ""
    return {
        "operation": str(operation),
        "status": str(status),
        "arguments": project_arguments(arguments),
        "error_type": error_type,
        "error_message": error_message,
        "result_metadata": project_result_metadata(
            result_metadata,
            outcome_type=outcome_type,
            exit_code=exit_code,
        ),
        "observed_roots": [str(item) for item in observed_roots],
        "mutated_roots": [str(item) for item in mutated_roots],
        "observation": project_action_result(
            dict(result or {}), operation=operation, arguments=arguments or {},
            focus_text="", max_exact_chars=2400, structured_budget=3600,
        ),
    }


def project_workspace_targets(
    descriptors: Sequence[Mapping[str, Any]],
) -> list[dict[str, str]]:
    """Project typed Harness descriptors to bounded ``{path, target_kind}`` rows."""

    rows: dict[str, str] = {}
    for item in descriptors:
        path = str(item.get("path") or "")
        kind = str(item.get("target_kind") or "")
        if not path or path in rows:
            continue
        if kind not in WORKSPACE_TARGET_KINDS:
            raise ValueError(f"unsupported workspace target kind: {kind!r}")
        rows[path] = kind
        if len(rows) >= MAX_WORKSPACE_TARGETS:
            break
    return [{"path": path, "target_kind": kind} for path, kind in rows.items()]


def build_current_progress(
    *,
    assigned_actions: Sequence[Any],
    read_roots: Sequence[str],
    write_roots: Sequence[str],
    mechanical_evidence: Mapping[str, Any],
    target_descriptors: Sequence[Mapping[str, Any]],
    action_observes_root: Any,
    action_mutates_root: Any,
    feedback: Mapping[str, Any] | None = None,
    recent_rejections: Sequence[Mapping[str, Any]] = (),
    operation_targets: Mapping[str, Any] | None = None,
    discovery_complete: bool = True,
    evidence_records: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    """Build the one production ``current_progress`` from durable Harness actions.

    This is the only permitted constructor for Selector progress.  The
    Controller calls it before every Selector request; StateTune data builders
    and acceptance evaluators must call it on the same durable action records
    instead of hand-writing progress dictionaries.  ``assigned_actions`` are the
    actions bound to the active step revision in sequence order; each exposes
    ``action_type``, ``status`` (with ``.value``), ``arguments`` and ``result``.
    """

    successful = [
        action
        for action in assigned_actions
        if str(action.status.value) == "succeeded"
        and bool((action.result or {}).get("success"))
    ]
    last_action: dict[str, Any] | None = None
    if assigned_actions:
        latest = assigned_actions[-1]
        result = latest.result if isinstance(latest.result, Mapping) else {}
        latest_succeeded = (
            str(latest.status.value) == "succeeded" and bool(result.get("success"))
        )
        error = result.get("error")
        exit_code = result.get("exit_code")
        last_action = project_last_action(
            result=result,
            operation=latest.action_type,
            status=str(latest.status.value),
            succeeded=latest_succeeded,
            arguments=(
                latest.arguments if isinstance(latest.arguments, Mapping) else {}
            ),
            error=error if isinstance(error, Mapping) else None,
            result_metadata=(
                result.get("metadata")
                if isinstance(result.get("metadata"), Mapping)
                else None
            ),
            observed_roots=[
                root
                for root in read_roots
                if latest_succeeded and action_observes_root(latest, root)
            ],
            mutated_roots=[
                root
                for root in write_roots
                if latest_succeeded and action_mutates_root(latest, root)
            ],
            outcome_type=(
                str(result.get("outcome_type")) if result.get("outcome_type") else None
            ),
            exit_code=(
                int(exit_code)
                if isinstance(exit_code, int) and not isinstance(exit_code, bool)
                else None
            ),
        )
    progress = {
        "assigned_action_count": len(assigned_actions),
        "successful_action_count": len(successful),
        "failed_action_count": len(assigned_actions) - len(successful),
        "last_action": last_action,
        "missing_read_roots": list(mechanical_evidence.get("missing_read_roots") or ()),
        "missing_write_roots": list(
            mechanical_evidence.get("missing_write_roots") or ()
        ),
        "workspace_targets": project_workspace_targets(tuple(target_descriptors)),
        "mechanical_preconditions_satisfied": bool(
            mechanical_evidence.get("completion_preconditions_satisfied")
        ),
        "completion_authority": False,
        "evidence_records": [dict(record) for record in evidence_records],
    }
    progress["feedback"] = dict(feedback) if feedback is not None else None
    progress["target_discovery_complete"] = discovery_complete and (
        len(progress["workspace_targets"]) == len({item["path"] for item in target_descriptors})
    )
    progress["recent_rejections"] = build_rejections(recent_rejections)
    progress["operation_targets"] = summarize_operation_targets(operation_targets or {})
    validate_progress(progress, read_roots=read_roots, write_roots=write_roots)
    return progress


def validate_last_action(
    last_action: Any,
    *,
    read_roots: Sequence[str],
    write_roots: Sequence[str],
) -> Mapping[str, Any]:
    action = _exact_fields(last_action, LAST_ACTION_FIELDS, "last_action")
    _mapping(action["observation"], "last_action.observation")
    _nonempty(action["operation"], "last_action.operation")
    if action["status"] not in _ACTION_STATUSES:
        raise ValueError("last_action.status is invalid")
    arguments = _mapping(action["arguments"], "last_action.arguments")
    if len(arguments) > MAX_ARGUMENT_KEYS:
        raise ValueError("last_action.arguments exceeds the key bound")
    for key, value in arguments.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("last_action.arguments must map strings to strings")
        if len(value) > MAX_ARGUMENT_CHARS:
            raise ValueError("last_action.arguments value exceeds the bound")
    error_type = action["error_type"]
    error_message = action["error_message"]
    if error_type is None:
        if error_message is not None:
            raise ValueError("last_action.error_message requires error_type")
    else:
        _nonempty(error_type, "last_action.error_type")
        if not isinstance(error_message, str):
            raise ValueError("last_action.error_message must be a string")
        if len(error_message) > MAX_ERROR_MESSAGE_CHARS:
            raise ValueError("last_action.error_message exceeds the bound")
    if action["status"] == "succeeded" and error_type is not None:
        raise ValueError("succeeded last_action cannot carry an error")
    if action["status"] != "succeeded" and error_type is None:
        raise ValueError("non-succeeded last_action requires error_type")
    metadata = _mapping(action["result_metadata"], "last_action.result_metadata")
    if tuple(metadata) != tuple(
        key for key in RESULT_METADATA_KEYS if key in metadata
    ):
        raise ValueError("last_action.result_metadata keys/order are invalid")
    for key, value in metadata.items():
        if not (
            value is None
            or isinstance(value, (bool, int, float))
            or (isinstance(value, str) and len(value) <= MAX_ARGUMENT_CHARS)
        ):
            raise ValueError(f"last_action.result_metadata.{key} is invalid")
    _strings(action["observed_roots"], "last_action.observed_roots")
    _strings(action["mutated_roots"], "last_action.mutated_roots")
    if not set(action["observed_roots"]).issubset(read_roots):
        raise ValueError("last_action observed roots exceed current_subtask")
    if not set(action["mutated_roots"]).issubset(write_roots):
        raise ValueError("last_action mutated roots exceed current_subtask")
    if action["status"] != "succeeded" and (
        action["observed_roots"] or action["mutated_roots"]
    ):
        raise ValueError("non-succeeded last_action cannot cover roots")
    return action


def validate_workspace_targets(value: Any) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError("current_progress.workspace_targets must be an array")
    if len(value) > MAX_WORKSPACE_TARGETS:
        raise ValueError("current_progress.workspace_targets exceeds the bound")
    seen: set[str] = set()
    rows = []
    for item in value:
        row = _exact_fields(item, WORKSPACE_TARGET_FIELDS, "workspace_target")
        path = _nonempty(row["path"], "workspace_target.path")
        if path in seen:
            raise ValueError("current_progress.workspace_targets repeats a path")
        seen.add(path)
        if row["target_kind"] not in WORKSPACE_TARGET_KINDS:
            raise ValueError("workspace_target.target_kind is invalid")
        rows.append(row)
    return tuple(rows)


def validate_progress(
    progress: Any,
    *,
    read_roots: Sequence[str],
    write_roots: Sequence[str],
) -> Mapping[str, Any]:
    selected = _exact_fields(progress, PROGRESS_FIELDS, "current_progress")
    validate_feedback(selected["feedback"], recipient="selector_intent")
    validate_rejections(selected["recent_rejections"])
    if not isinstance(selected["operation_targets"], Mapping):
        raise ValueError("operation_targets must be an object")
    if not isinstance(selected["target_discovery_complete"], bool):
        raise ValueError("target discovery completeness must be explicit")
    for name in (
        "assigned_action_count",
        "successful_action_count",
        "failed_action_count",
    ):
        _nonnegative_int(selected[name], f"current_progress.{name}")
    if selected["successful_action_count"] + selected["failed_action_count"] != (
        selected["assigned_action_count"]
    ):
        raise ValueError("current_progress action counters are inconsistent")
    _strings(selected["missing_read_roots"], "current_progress.missing_read_roots")
    _strings(
        selected["missing_write_roots"], "current_progress.missing_write_roots"
    )
    if not set(selected["missing_read_roots"]).issubset(read_roots):
        raise ValueError("current_progress missing read roots exceed current_subtask")
    if not set(selected["missing_write_roots"]).issubset(write_roots):
        raise ValueError("current_progress missing write roots exceed current_subtask")
    validate_workspace_targets(selected["workspace_targets"])
    if selected["completion_authority"] is not False:
        raise ValueError("mechanical progress cannot grant completion authority")
    if not isinstance(selected["evidence_records"], list) or any(
        not isinstance(record, Mapping) for record in selected["evidence_records"]
    ):
        raise ValueError("current_progress.evidence_records must contain fact records")
    if not isinstance(selected["mechanical_preconditions_satisfied"], bool):
        raise ValueError(
            "current_progress.mechanical_preconditions_satisfied must be boolean"
        )
    expected_complete = not (
        selected["missing_read_roots"] or selected["missing_write_roots"]
    ) and selected["successful_action_count"] > 0
    if selected["mechanical_preconditions_satisfied"] is not expected_complete:
        raise ValueError("current_progress completion flag is inconsistent")
    last_action = selected["last_action"]
    if last_action is None:
        if selected["assigned_action_count"] != 0:
            raise ValueError("current_progress with actions requires last_action")
    else:
        validate_last_action(
            last_action,
            read_roots=read_roots,
            write_roots=write_roots,
        )
    return selected


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "selector prompt source")
    subtask = _exact_fields(
        selected["current_subtask"], SUBTASK_FIELDS, "current_subtask"
    )
    _nonempty(subtask["objective"], "current_subtask.objective")
    if subtask["phase"] not in _PHASES:
        raise ValueError("current_subtask.phase is invalid")
    for name in ("read_roots", "write_roots", "constraints"):
        _strings(subtask[name], f"current_subtask.{name}")
    _strings(
        subtask["success_evidence"],
        "current_subtask.success_evidence",
        nonempty=True,
    )
    validate_progress(
        selected["current_progress"],
        read_roots=subtask["read_roots"],
        write_roots=subtask["write_roots"],
    )
    _strings(selected["eligible_labels"], "eligible_labels", nonempty=True)
    return selected


def build_prompt_source(
    *,
    current_subtask: Mapping[str, Any],
    current_progress: Mapping[str, Any],
    eligible_labels: Sequence[str],
) -> dict[str, Any]:
    """Bind a current subtask to progress built from its durable actions."""

    source = {
        "current_subtask": dict(current_subtask),
        "current_progress": dict(current_progress),
        "eligible_labels": list(eligible_labels),
    }
    _validate_prompt_source(source)
    return source


def validate_source(source: Any) -> None:
    selected = _exact_fields(source, _SOURCE_FIELDS, "selector source")
    _validate_prompt_source({name: selected[name] for name in _PROMPT_FIELDS})
    operation = _nonempty(selected["selected_operation"], "selected_operation")
    if operation not in tuple(selected["eligible_labels"]):
        raise ValueError("selected_operation must be eligible")
    authority = _nonempty(selected["selection_authority"], "selection_authority")
    if authority not in _AUTHORITIES:
        raise ValueError("selection_authority is invalid")
    _nonempty(selected["selection_verifier_id"], "selection_verifier_id")


def render_prompt(source: Any) -> str:
    selected = _exact_fields(source, tuple(source), "selector render source")
    if tuple(selected) == _SOURCE_FIELDS:
        validate_source(selected)
        prompt = {name: selected[name] for name in _PROMPT_FIELDS}
    else:
        prompt = dict(_validate_prompt_source(selected))
    payload = {
        "schema_version": INPUT_SCHEMA_VERSION,
        "role": "selector_intent",
        "eligible_labels": list(prompt["eligible_labels"]),
        "current_subtask": dict(prompt["current_subtask"]),
        "current_progress": dict(prompt["current_progress"]),
        "current_question": (
            "Use the visible observation content, dependency evidence and feedback diagnosis. "
            "Mechanical preconditions only describe executed scope; they never prove semantic completion. "
            "A successful search or directory listing is not a full-file read. "
            "Choose exactly one eligible operation that advances this current "
            "subtask from the recorded mechanical progress, the previous action's "
            "exact Harness outcome, and the typed workspace targets; do not fill "
            "parameters, audit, plan, or answer the user."
        ),
    }
    return _render(PROMPT_PREFIX, payload)


def render_target(source: Any) -> str:
    validate_source(source)
    return TARGET_PREFIX + str(source["selected_operation"])


def parse_target(target: str) -> str:
    prefix = TARGET_PREFIX
    if not isinstance(target, str) or not target.startswith(prefix):
        raise ValueError("selector target prefix is invalid")
    operation = target[len(prefix) :]
    if not operation or operation.strip() != operation or "\n" in operation:
        raise ValueError("selector target must contain one exact operation label")
    return operation


__all__ = [
    "ENDPOINT",
    "INPUT_SCHEMA_VERSION",
    "LAST_ACTION_FIELDS",
    "MAX_ARGUMENT_CHARS",
    "MAX_ARGUMENT_KEYS",
    "MAX_ERROR_MESSAGE_CHARS",
    "MAX_WORKSPACE_TARGETS",
    "OUTPUT_SCHEMA_VERSION",
    "MENU_PREFIX",
    "MENU_SCHEMA_VERSION",
    "PROMPT_PREFIX",
    "PROGRESS_FIELDS",
    "RESULT_METADATA_KEYS",
    "ROLE_MARKER",
    "ROLE_PREFIX",
    "TARGET_PREFIX",
    "WORKSPACE_TARGET_FIELDS",
    "build_current_progress",
    "build_prompt_source",
    "parse_target",
    "project_arguments",
    "project_last_action",
    "project_result_metadata",
    "project_workspace_targets",
    "render_prompt",
    "render_target",
    "validate_last_action",
    "validate_progress",
    "validate_source",
    "validate_workspace_targets",
]
