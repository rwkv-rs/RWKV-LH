"""Production/data-shared G1J Executor-Args renderer and parser."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from rwkv_lh.goal_state_protocols import (
    _exact_fields,
    _nonempty,
    _objects,
    _render,
    _strict_command,
    _strings,
)
from rwkv_lh.model_io import ModelCommand, TOOL_CALL_JSON_CONTINUATION_ANCHOR


INPUT_SCHEMA_VERSION = "rwkv-lh.g1j-per-stage-state-tuning.executor-args.v1"
OUTPUT_SCHEMA_VERSION = INPUT_SCHEMA_VERSION

_PROMPT_FIELDS = (
    "current_requirement",
    "selected_operation",
    "selected_tool_contract",
    "committed_fact_refs",
    "executor_history",
)
_SOURCE_FIELDS = (*_PROMPT_FIELDS, "command", "fixture_id", "execution_verifier_id")


def _validate_prompt_source(source: Any) -> Mapping[str, Any]:
    selected = _exact_fields(source, _PROMPT_FIELDS, "executor prompt source")
    _nonempty(selected["current_requirement"], "current_requirement")
    operation = _nonempty(selected["selected_operation"], "selected_operation")
    if operation in {"final_answer", "ABSTAIN"}:
        raise ValueError("Executor-Args cannot receive a terminal or abstain operation")
    contract = selected["selected_tool_contract"]
    if not isinstance(contract, Mapping) or not contract:
        raise ValueError("selected_tool_contract must be a non-empty object")
    if str(contract.get("name") or "") != operation:
        raise ValueError("selected_tool_contract must match selected_operation")
    _strings(
        selected["committed_fact_refs"],
        "committed_fact_refs",
        sorted_unique=True,
    )
    _objects(selected["executor_history"], "executor_history")
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
        "selected_operation": prompt["selected_operation"],
        "selected_tool_contract": dict(prompt["selected_tool_contract"]),
        "committed_fact_refs": list(prompt["committed_fact_refs"]),
        "executor_history": [dict(item) for item in prompt["executor_history"]],
        "current_question": (
            "Return one canonical direct call for the selected operation with every "
            "required parameter explicit; do not select another operation or answer the user."
        ),
    }
    return _render("ExecutorArgsPromptV1: ", payload)


def render_target(source: Any) -> str:
    validate_source(source)
    command = source["command"]
    return ModelCommand(str(command["function"]), dict(command["params"])).canonical


def render_generation_prompt(source: Any) -> str:
    """Render the saved role payload at G1J's native first-call boundary."""

    return render_prompt(source) + TOOL_CALL_JSON_CONTINUATION_ANCHOR


def parse_target(target: str) -> ModelCommand:
    from rwkv_lh.model_io import parse_model_command

    parsed = parse_model_command(target)
    command = _strict_command(target, parsed.name)
    if command.name in {"final_answer", "ABSTAIN"}:
        raise ValueError("Executor-Args target cannot be terminal or abstain")
    return command


__all__ = [
    "INPUT_SCHEMA_VERSION",
    "OUTPUT_SCHEMA_VERSION",
    "parse_target",
    "render_generation_prompt",
    "render_prompt",
    "render_target",
    "validate_source",
]
