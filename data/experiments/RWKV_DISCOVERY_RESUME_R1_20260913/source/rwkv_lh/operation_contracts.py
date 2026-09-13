"""Authoritative structural contracts shared by Harness and Selector feedback."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass


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
# Content classifications are hints. Eligibility uses filesystem structure;
# parsing, encoding and mutation-specific conditions remain Harness outcomes.
_FILE_TARGET_KINDS = frozenset({"json_file", "text_file", "binary_file", "large_file"})
_CREATABLE_FILE_KINDS = frozenset({"missing", *_FILE_TARGET_KINDS})
_PATH_KINDS = {
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


@dataclass(frozen=True)
class PathArgumentContract:
    accepted_kinds: frozenset[str]
    access: str


# One declaration owns structural preconditions AND filesystem effects.
# All downstream projections, including Harness mutation accounting, derive here.
PATH_ARGUMENT_CONTRACTS = {
    operation: {
        name: PathArgumentContract(kinds,
            "read_write" if operation == "move_file" and name == "source"
            else "read" if operation in {"list_directory", "search_text", "read_file",
                "read_json", "file_digest", "bind_evidence"} or name == "source"
            else "write")
        for name, kinds in arguments.items()
    } for operation, arguments in _PATH_KINDS.items()
}
OPERATION_TARGET_ARGUMENTS = {op: tuple(args) for op, args in PATH_ARGUMENT_CONTRACTS.items()}
PATH_MUTATION_ARGUMENTS = {
    op: tuple(name for name, contract in args.items() if contract.access != "read")
    for op, args in PATH_ARGUMENT_CONTRACTS.items()
    if any(contract.access != "read" for contract in args.values())
}
PATH_MUTATION_OPERATIONS = frozenset(PATH_MUTATION_ARGUMENTS)
DISTINCT_PATH_ARGUMENTS = {operation: ("source", "destination") for operation in ("copy_file", "move_file")}


def path_within_roots(path: str, roots: Sequence[str]) -> bool:
    parts = tuple(p for p in str(path).replace("\\", "/").split("/") if p not in {"", "."})
    if ".." in parts or str(path).startswith("/"):
        return False
    for root in roots:
        parent = tuple(p for p in str(root).replace("\\", "/").split("/") if p not in {"", "."})
        if ".." not in parent and (not parent or parts[:len(parent)] == parent):
            return True
    return False


def project_argument_targets(*, operations: Sequence[str], roots: Sequence[str],
                             scope_roots: Sequence[str], descriptors: Sequence[Mapping],
                             discovery_complete: bool) -> dict:
    """Express each parameter independently; unknown discovery never proves absence."""
    result = {}
    for operation in operations:
        arguments = {}
        for name, spec in PATH_ARGUMENT_CONTRACTS.get(operation, {}).items():
            scope = (tuple(scope_roots) if spec.access == "read_write" else (".",)
                     if name == "source" else tuple(roots) or (".",))
            visible = [item for item in descriptors if path_within_roots(item["path"], scope)]
            candidates = list(compatible_target_paths(operation, visible, argument_name=name))
            directories = [item["path"] for item in visible if item["target_kind"] == "directory"]
            creatable = directories if "missing" in spec.accepted_kinds else []
            # Unexpanded/omitted directories may contain a usable path. A known
            # missing file, in contrast, is fully observed even if another scope is not.
            complete = discovery_complete or (not directories and bool(visible))
            arguments[name] = {"access": spec.access, "scope_roots": list(scope),
                "compatible_paths": candidates, "creatable_roots": creatable,
                "discovery_complete": complete,
                "availability": "available" if candidates or creatable else "unavailable" if complete else "unknown"}
        result[operation] = arguments
    return result


def eligible_target_operations(argument_targets: Mapping) -> tuple[str, ...]:
    selected = []
    for operation, arguments in argument_targets.items():
        if any(item["availability"] == "unavailable" for item in arguments.values()):
            continue
        pair = DISTINCT_PATH_ARGUMENTS.get(operation)
        if pair:
            left, right = (arguments[name] for name in pair)
            if (not left["creatable_roots"] and not right["creatable_roots"]
                and left["discovery_complete"] and right["discovery_complete"]
                and len(set(left["compatible_paths"]) | set(right["compatible_paths"])) < 2):
                continue
        selected.append(operation)
    return tuple(selected)


def summarize_operation_targets(argument_targets: Mapping) -> dict:
    """Selector needs preconditions and effects, not every possible argument."""
    return {op: {name: {"access": item["access"], "scope_roots": list(item["scope_roots"]),
        "availability": item["availability"], "compatible_path_count": len(item["compatible_paths"]),
        "creatable_root_count": len(item["creatable_roots"]), "discovery_complete": item["discovery_complete"]}
        for name, item in args.items()} for op, args in argument_targets.items()}


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
    argument_contract = PATH_ARGUMENT_CONTRACTS.get(selected_operation)
    if argument_contract is None:
        return True
    allowed = argument_contract.get(str(argument_name or "").strip())
    return allowed is not None and selected_kind in allowed.accepted_kinds


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
