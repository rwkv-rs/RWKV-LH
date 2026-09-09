"""Bind raw JSON-role targets to the one rebuilt production input contract.

These are structural/evidence checks, not label authority. The caller must still
prove an executed advancement, a unique eligible planner contract, or two bound
human reviews for a semantic or failure-recovery target. A review cannot bypass any check
here. Selector suffixes have their separate three-menu decoder validation.
"""

from __future__ import annotations

from collections.abc import Mapping
from copy import deepcopy
from typing import Any

from rwkv_lh.executor_provenance import validate_executor_argument_provenance
from rwkv_lh.goal_state_protocols import (
    auditor_final, auditor_step_v4, executor_args_v5, finalizer_answer,
)
from rwkv_lh.harness import ActionHarness, HarnessError, TaskAction
from rwkv_lh.goal_loop_protocol import action_mutates_root, action_observes_root
from rwkv_lh.schema import ActionRecord, ActionStatus


_MODULES = {
    "executor_args": executor_args_v5,
    "auditor_step": auditor_step_v4,
    "auditor_final": auditor_final,
    "finalizer_answer": finalizer_answer,
}


class RoleTraceLabelError(ValueError):
    """A raw target does not satisfy its reconstructed production input."""


def _validate_step_gap_facts(source: Mapping[str, Any], decision: Mapping[str, Any]) -> None:
    # The catalog enumerates possible gaps, not true gaps. Reject contradictions
    # provable from the exact evidence shown to this Auditor; semantic criteria
    # still require independent label review. Truncated observations prove no
    # complete read root, even if the scheduling prerequisite was satisfied.
    actions = []
    for record in source["evidence_records"]:
        raw = record.get("action")
        if isinstance(raw, Mapping):
            action = ActionRecord.from_dict({**raw, "action_type": raw.get("operation")})
            if action.status is ActionStatus.SUCCEEDED and (action.result or {}).get("success") is True:
                actions.append(action)
    for gap in decision["gaps"]:
        prefix, _, root = gap.partition(":")
        if prefix not in {"read_root_unproved", "write_root_unproved"}:
            continue
        for action in actions:
            metadata = (action.result or {}).get("metadata") or {}
            if prefix == "read_root_unproved":
                proved = (metadata.get("truncated") is not True and metadata.get("complete") is not False
                          and action_observes_root(action, root))
            else:
                proved = action_mutates_root(action, root)
            if proved:
                raise RoleTraceLabelError(f"gap contradicts visible successful evidence: {gap}")


def validate_role_target(
    role: str, rebuilt: Mapping[str, Any], canonical_target: str, *, verifier_id: str,
) -> str:
    """Validate without supplying, repairing, or rewriting any target field.

    Executor arguments pass the same semantics-free interface normalization and
    exact-source provenance checks as production; the returned training target
    always retains its original wire arguments. The verifier id binds the source
    contract to an existing durable boundary; it does not grant label authority.
    """
    if role not in _MODULES:
        raise RoleTraceLabelError(f"unsupported JSON role: {role}")
    if not isinstance(verifier_id, str) or not verifier_id.strip():
        raise RoleTraceLabelError("an existing nonempty verifier_id is required")
    module = _MODULES[role]
    if rebuilt.get("protocol_version") != module.INPUT_SCHEMA_VERSION:
        raise RoleTraceLabelError("target requires the current rebuilt input protocol")
    prompt_source = rebuilt.get("prompt_source")
    if not isinstance(prompt_source, Mapping):
        raise RoleTraceLabelError("target requires a rebuilt prompt source")
    try:
        parsed = module.parse_target(canonical_target)
        if parsed.canonical != canonical_target:
            raise RoleTraceLabelError("target must already be canonical; rewriting is forbidden")
        source = deepcopy(dict(prompt_source))
        if role == "executor_args":
            source.update(
                command={"function": parsed.name, "params": dict(parsed.arguments)},
                fixture_id=verifier_id, execution_verifier_id=verifier_id,
            )
        elif role == "auditor_step":
            source.update(decision=dict(parsed.arguments), completion_verifier_id=verifier_id)
        elif role == "auditor_final":
            source.update(decision=dict(parsed.arguments), final_verifier_id=verifier_id)
        else:
            source.update(final_text=parsed.arguments["text"], fact_verifier_id=verifier_id)
        module.validate_source(source)
        if role == "auditor_step":
            _validate_step_gap_facts(source, parsed.arguments)
        if module.render_target(source) != canonical_target:
            raise RoleTraceLabelError("target differs from the source-bound canonical target")
        if role == "executor_args":
            if "bound_fact_records" not in rebuilt:
                raise RoleTraceLabelError("Executor target lacks reconstructed bound fact records")
            normalized, _trace = ActionHarness().normalize_action_with_trace(
                TaskAction(parsed.name, dict(parsed.arguments)),
            )
            validate_executor_argument_provenance(
                normalized.action_type, normalized.arguments,
                current_requirement=source["current_requirement"],
                fact_records=rebuilt["bound_fact_records"],
                execution_state=source["execution_state"],
            )
    except (ValueError, TypeError, KeyError, HarnessError) as exc:
        if isinstance(exc, RoleTraceLabelError):
            raise
        raise RoleTraceLabelError(str(exc)) from exc
    return canonical_target


__all__ = ["RoleTraceLabelError", "validate_role_target"]
