"""Shared strict primitives for the five G1J per-stage StateTune protocols."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from typing import Any

from rwkv_lh.model_io import ModelCommand, parse_model_command


ZERO_STATE_SHA256 = "0" * 64
ROLE_STATE_IDS = {
    "selector_intent": "selector-intent-2p9-v1",
    "executor_args": "executor-args-v1",
    "auditor_step": "auditor-step-v1",
    "finalizer_answer": "finalizer-answer-v1",
    "auditor_final": "auditor-final-v1",
}


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be an object")
    return value


def _exact_fields(
    value: Any,
    fields: Sequence[str],
    name: str,
) -> Mapping[str, Any]:
    selected = _mapping(value, name)
    if tuple(selected) != tuple(fields) or set(selected) != set(fields):
        raise ValueError(f"{name} fields/order must be exactly {tuple(fields)!r}")
    return selected


def _exact_field_set(
    value: Any,
    fields: Sequence[str],
    name: str,
) -> Mapping[str, Any]:
    selected = _mapping(value, name)
    if set(selected) != set(fields):
        raise ValueError(f"{name} fields must be exactly {tuple(fields)!r}")
    return selected


def _nonempty(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _strings(
    value: Any,
    name: str,
    *,
    nonempty: bool = False,
    sorted_unique: bool = False,
) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be an array")
    selected = tuple(_nonempty(item, f"{name} item") for item in value)
    if nonempty and not selected:
        raise ValueError(f"{name} must not be empty")
    if len(set(selected)) != len(selected):
        raise ValueError(f"{name} must contain unique values")
    if sorted_unique and selected != tuple(sorted(selected)):
        raise ValueError(f"{name} must be sorted")
    return selected


def _objects(value: Any, name: str, *, nonempty: bool = False) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ValueError(f"{name} must be an array")
    selected = tuple(_mapping(item, f"{name} item") for item in value)
    if nonempty and not selected:
        raise ValueError(f"{name} must not be empty")
    return selected


def _nonnegative_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _render(prefix: str, payload: Mapping[str, Any]) -> str:
    return prefix + json.dumps(
        dict(payload),
        ensure_ascii=False,
        sort_keys=False,
        separators=(",", ":"),
    )


def _strict_command(target: str, operation: str) -> ModelCommand:
    if not isinstance(target, str) or not target:
        raise ValueError("target must be a non-empty string")
    command = parse_model_command(target)
    if command.name != operation:
        raise ValueError(f"target must call {operation!r}")
    if target != command.canonical:
        raise ValueError("target must be canonical direct-call JSON")
    return command


_AUDIT_FIELDS = (
    "verdict",
    "step_id",
    "step_complete",
    "evidence_refs",
    "gaps",
    "reason",
)


def _audit_decision(
    value: Any,
    *,
    allowed_verdicts: Sequence[str],
) -> Mapping[str, Any]:
    decision = _exact_field_set(value, _AUDIT_FIELDS, "decision")
    verdict = _nonempty(decision["verdict"], "decision.verdict")
    if verdict not in set(allowed_verdicts):
        raise ValueError(f"decision.verdict must be one of {tuple(allowed_verdicts)!r}")
    if not isinstance(decision["step_id"], str):
        raise ValueError("decision.step_id must be a string")
    if not isinstance(decision["step_complete"], bool):
        raise ValueError("decision.step_complete must be boolean")
    _strings(decision["evidence_refs"], "decision.evidence_refs")
    _strings(decision["gaps"], "decision.gaps")
    _nonempty(decision["reason"], "decision.reason")
    return decision


def _audit_target(target: str, *, allowed_verdicts: Sequence[str]) -> ModelCommand:
    command = _strict_command(target, "audit_decision")
    _audit_decision(command.arguments, allowed_verdicts=allowed_verdicts)
    return command


__all__ = ["ROLE_STATE_IDS", "ZERO_STATE_SHA256"]
