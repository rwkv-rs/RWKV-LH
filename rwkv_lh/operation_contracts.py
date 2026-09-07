"""Authoritative structural contracts shared by Harness and Selector feedback."""

from __future__ import annotations

from collections.abc import Sequence


PATH_MUTATION_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "write_file": ("path",),
    "write_json": ("path",),
    "patch_json": ("path",),
    "replace_text": ("path",),
    "remove_line": ("path",),
    "append_file": ("path",),
    "delete_file": ("path",),
    "make_directory": ("path",),
    "copy_file": ("destination",),
    "move_file": ("source", "destination"),
}
PATH_MUTATION_OPERATIONS = frozenset(PATH_MUTATION_ARGUMENTS)
JSON_PATH_OPERATIONS = frozenset({"read_json", "write_json", "patch_json"})
TEXT_PATH_OPERATIONS = frozenset(
    {"read_file", "write_file", "replace_text", "remove_line", "append_file"}
)

WORKSPACE_TARGET_KINDS = frozenset(
    {
        "directory",
        "json_file",
        "json_candidate_file",
        "text_file",
        "binary_file",
        "large_file",
        "missing",
        "other",
    }
)
OPERATION_TARGET_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "list_directory": ("path",),
    "search_text": ("path",),
    "read_file": ("path",),
    "read_json": ("path",),
    "file_digest": ("path",),
    "write_file": ("path",),
    "write_json": ("path",),
    "patch_json": ("path",),
    "replace_text": ("path",),
    "remove_line": ("path",),
    "append_file": ("path",),
    "make_directory": ("path",),
    "copy_file": ("source", "destination"),
    "move_file": ("source", "destination"),
    "delete_file": ("path",),
    "bind_evidence": ("path",),
}
_FILE_TARGET_KINDS = frozenset(
    {"json_file", "json_candidate_file", "text_file", "binary_file", "large_file"}
)
_OPERATION_TARGET_KINDS: dict[str, dict[str, frozenset[str]]] = {
    "list_directory": {"path": frozenset({"directory"})},
    "search_text": {
        "path": frozenset({"directory", "json_file", "text_file", "large_file"})
    },
    # Both readers are safe observations. A valid JSON file may need its exact raw
    # bytes (hashes, formatting, or text replacement), while a filename-declared
    # JSON candidate may need a failed parse to establish that fallback is required.
    # Keep mutation compatibility strict, but do not make either observation path
    # unreachable.
    "read_file": {
        "path": frozenset(
            {"json_file", "json_candidate_file", "text_file", "large_file"}
        )
    },
    "read_json": {"path": frozenset({"json_file", "json_candidate_file"})},
    "file_digest": {"path": _FILE_TARGET_KINDS},
    "write_file": {
        "path": frozenset(
            {"missing", "json_file", "json_candidate_file", "text_file", "large_file"}
        )
    },
    "write_json": {
        "path": frozenset({"missing", "json_file", "json_candidate_file"})
    },
    "patch_json": {"path": frozenset({"json_file"})},
    "replace_text": {
        "path": frozenset(
            {"json_file", "json_candidate_file", "text_file", "large_file"}
        )
    },
    "remove_line": {"path": frozenset({"text_file", "large_file"})},
    "append_file": {"path": frozenset({"missing", "text_file", "large_file"})},
    "make_directory": {"path": frozenset({"missing", "directory"})},
    "copy_file": {
        "source": _FILE_TARGET_KINDS,
        "destination": frozenset({"missing", *_FILE_TARGET_KINDS}),
    },
    "move_file": {
        "source": _FILE_TARGET_KINDS,
        "destination": frozenset({"missing", *_FILE_TARGET_KINDS}),
    },
    "delete_file": {
        "path": frozenset({"missing", "directory", *_FILE_TARGET_KINDS})
    },
    "bind_evidence": {
        "path": frozenset({"json_file", "text_file", "large_file"})
    },
}


def operation_accepts_target_kind(
    operation: str,
    target_kind: str,
    *,
    argument_name: str = "path",
) -> bool:
    """Return the frozen Harness-level operation/target compatibility fact."""

    selected_operation = str(operation or "").strip()
    selected_kind = str(target_kind or "").strip()
    if selected_kind not in WORKSPACE_TARGET_KINDS:
        raise ValueError(f"unsupported workspace target kind: {selected_kind!r}")
    argument_contract = _OPERATION_TARGET_KINDS.get(selected_operation)
    if argument_contract is None:
        return True
    allowed = argument_contract.get(str(argument_name or "").strip())
    return allowed is not None and selected_kind in allowed


def compatible_target_paths(
    operation: str,
    descriptors: Sequence[dict[str, object]],
    *,
    argument_name: str = "path",
) -> tuple[str, ...]:
    """Project typed Harness descriptors to compatible path candidates."""

    return tuple(
        dict.fromkeys(
            str(item.get("path") or "")
            for item in descriptors
            if str(item.get("path") or "")
            and operation_accepts_target_kind(
                operation,
                str(item.get("target_kind") or ""),
                argument_name=argument_name,
            )
        )
    )

# Planner steps declare only one coarse responsibility.  The Controller uses
# these fixed families to compile a smaller Selector menu without choosing the
# concrete operation on the model's behalf.
GOAL_STEP_PHASES = (
    "observe",
    "mutate",
    "execute",
    "derive_evidence",
)
LOCAL_OBSERVE_OPERATIONS = frozenset(
    {"list_directory", "search_text", "read_file", "read_json", "file_digest"}
)
EXTERNAL_OBSERVE_OPERATIONS = frozenset({"web_search", "connector_lookup"})
GOAL_STEP_PHASE_OPERATIONS: dict[str, frozenset[str]] = {
    "observe": LOCAL_OBSERVE_OPERATIONS | EXTERNAL_OBSERVE_OPERATIONS,
    "mutate": PATH_MUTATION_OPERATIONS,
    "execute": frozenset({"check_command", "run_command"}),
    "derive_evidence": frozenset(
        {"bind_evidence", "calculator", "date_diff", "current_time"}
    ),
}


def project_goal_step_operations(
    *,
    authorized_operations: Sequence[str],
    phase: str,
    read_roots: Sequence[str] = (),
    write_roots: Sequence[str] = (),
) -> tuple[str, ...]:
    """Apply the production Goal-step phase boundary without choosing a tool.

    The Controller and StateTune data builder must share this function.  It
    narrows the policy-authorized Harness registry to one responsibility
    family while preserving the caller's authoritative class order.
    """

    selected_phase = str(phase or "").strip()
    if selected_phase not in GOAL_STEP_PHASE_OPERATIONS:
        raise ValueError(f"unsupported Goal step phase: {selected_phase!r}")
    family = GOAL_STEP_PHASE_OPERATIONS[selected_phase]
    if selected_phase == "observe":
        family = LOCAL_OBSERVE_OPERATIONS if read_roots else EXTERNAL_OBSERVE_OPERATIONS
    elif selected_phase == "execute":
        family = frozenset({"run_command" if write_roots else "check_command"})
    return tuple(
        operation
        for operation in dict.fromkeys(str(item) for item in authorized_operations)
        if operation in family
    )


def infer_goal_step_phase(
    *,
    write_roots: tuple[str, ...],
    allowed_operations: tuple[str, ...],
) -> str:
    """Infer only for durable pre-v3 plans and legacy contract projection."""

    allowed = set(allowed_operations)
    for phase in ("execute", "derive_evidence", "mutate", "observe"):
        if allowed & GOAL_STEP_PHASE_OPERATIONS[phase]:
            return phase
    return "mutate" if write_roots else "observe"


__all__ = [
    "GOAL_STEP_PHASES",
    "GOAL_STEP_PHASE_OPERATIONS",
    "EXTERNAL_OBSERVE_OPERATIONS",
    "JSON_PATH_OPERATIONS",
    "LOCAL_OBSERVE_OPERATIONS",
    "PATH_MUTATION_ARGUMENTS",
    "PATH_MUTATION_OPERATIONS",
    "OPERATION_TARGET_ARGUMENTS",
    "TEXT_PATH_OPERATIONS",
    "WORKSPACE_TARGET_KINDS",
    "compatible_target_paths",
    "infer_goal_step_phase",
    "operation_accepts_target_kind",
    "project_goal_step_operations",
]
