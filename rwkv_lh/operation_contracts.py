"""Authoritative structural contracts shared by Harness and Selector feedback."""

from __future__ import annotations


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
    "TEXT_PATH_OPERATIONS",
    "infer_goal_step_phase",
]
