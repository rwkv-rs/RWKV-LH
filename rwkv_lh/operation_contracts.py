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
# Content classifications are hints. Eligibility uses filesystem structure;
# parsing, encoding and mutation-specific conditions remain Harness outcomes.
_FILE_TARGET_KINDS = frozenset({"json_file", "text_file", "binary_file", "large_file"})
_CREATABLE_FILE_KINDS = frozenset({"missing", *_FILE_TARGET_KINDS})
_OPERATION_TARGET_KINDS: dict[str, dict[str, frozenset[str]]] = {
    "list_directory": {"path": frozenset({"directory"})},
    "search_text": {"path": frozenset({"directory", *_FILE_TARGET_KINDS})},
    **{operation: {"path": _FILE_TARGET_KINDS} for operation in (
        "read_file", "read_json", "file_digest", "patch_json", "replace_text",
        "remove_line", "bind_evidence",
    )},
    **{operation: {"path": _CREATABLE_FILE_KINDS} for operation in (
        "write_file", "write_json", "append_file",
    )},
    "make_directory": {"path": frozenset({"missing", "directory"})},
    **{operation: {"source": _FILE_TARGET_KINDS, "destination": _CREATABLE_FILE_KINDS}
       for operation in ("copy_file", "move_file")},
    "delete_file": {"path": frozenset({"missing", "directory", *_FILE_TARGET_KINDS})},
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
    "operation_accepts_target_kind",
    "project_goal_step_operations",
]
