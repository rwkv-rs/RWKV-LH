"""Minimal G1i wire boundary for direct operation-specific calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from rwkv_lh.schema import ModelEvent


class ModelIOError(ValueError):
    """A generated response is not exactly one explicit function call."""


MODEL_COMMAND_NORMALIZER_VERSION = "direct-call-envelope.v1"

JSON_CALL_STOP_SUFFIXES: tuple[str, ...] = (
    "\n```",
    "\n\nSystem:",
    "\n\nUser:",
    "\n\nAssistant:",
)


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _object_schema(
    properties: Mapping[str, Any],
    required: Sequence[str],
) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": dict(properties),
        "required": list(required),
        "additionalProperties": False,
    }


FINAL_ANSWER_DEFINITION: dict[str, Any] = {
    "name": "final_answer",
    "description": (
        "End the run and return a non-empty user-facing answer. Use this only when you "
        "decide no further tool call is needed. State failures or partial work honestly."
    ),
    "parameters": _object_schema(
        {"text": {"type": "string", "minLength": 1}},
        ("text",),
    ),
}


@dataclass(frozen=True)
class ModelCommand:
    name: str
    arguments: dict[str, Any]

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ModelIOError("function name must be non-empty")

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": dict(self.arguments)}

    def to_wire_dict(self) -> dict[str, Any]:
        return {"function": self.name, "params": dict(self.arguments)}

    @property
    def canonical(self) -> str:
        return canonical_json(self.to_wire_dict())

    @property
    def digest(self) -> str:
        return canonical_digest(self.to_dict())


@dataclass(frozen=True)
class ModelCommandNormalization:
    input_payload: dict[str, Any]
    normalized_payload: dict[str, Any]
    transformations: tuple[str, ...] = ()
    normalizer_version: str = MODEL_COMMAND_NORMALIZER_VERSION

    @property
    def changed(self) -> bool:
        return bool(self.transformations)

    def to_dict(self) -> dict[str, Any]:
        return {
            "normalizer_version": self.normalizer_version,
            "transformations": list(self.transformations),
            "input_payload": dict(self.input_payload),
            "normalized_payload": dict(self.normalized_payload),
            "input_payload_digest": canonical_digest(self.input_payload),
            "normalized_payload_digest": canonical_digest(self.normalized_payload),
            "controller_semantic_fields_generated": False,
        }


def render_bootstrap(
    definitions: Sequence[Mapping[str, Any]],
    assignment: str,
) -> str:
    request = str(assignment or "").strip()
    if not request:
        raise ModelIOError("assignment must be non-empty")
    if not definitions:
        raise ModelIOError("at least one operation definition is required")
    return (
        f"System: Tools: {canonical_json([dict(item) for item in definitions])}\n"
        "Choose exactly one displayed tool. Return only one JSON function call using "
        '"function" for its name and "params" for its complete parameters. Do not '
        "describe the call outside JSON.\n\n"
        f"User: {request}\n\n"
        "Assistant: ```json\n"
    )


def render_event_append(
    event: ModelEvent,
    visible_definitions: Sequence[Mapping[str, Any]] = (),
) -> str:
    scope = ""
    if visible_definitions:
        scope = (
            "\n\nSystem: Tools: "
            + canonical_json([dict(item) for item in visible_definitions])
            + "\nChoose exactly one displayed tool and return one JSON function call."
        )
    return (
        scope
        + "\n\nUser: Function output: "
        + canonical_json(event.to_model_dict())
        + "\n\nAssistant: ```json\n"
    )


def _extract_json(raw_output: str) -> tuple[str, list[str]]:
    raw = str(raw_output or "")
    if not raw:
        raise ModelIOError("model output is empty")
    transformations: list[str] = []
    text = raw
    stripped = text.strip()
    if stripped != text:
        transformations.append("surface:surrounding_whitespace_removed")
        text = stripped
    if text.startswith("```"):
        if not text.endswith("```"):
            raise ModelIOError("Markdown code fence is not closed")
        first_newline = text.find("\n")
        if first_newline < 0:
            raise ModelIOError("Markdown code fence has no JSON body")
        opener = text[:first_newline].strip().casefold()
        if opener not in {"```", "```json"}:
            raise ModelIOError("only a plain or json Markdown fence is accepted")
        text = text[first_newline + 1 : -3].strip()
        transformations.append("surface:markdown_code_fence_removed")
    return text, transformations


def parse_model_command_with_trace(
    raw_output: str,
) -> tuple[ModelCommand, ModelCommandNormalization]:
    """Normalize only common call-envelope spellings and Markdown fencing."""

    text, transformations = _extract_json(raw_output)
    try:
        value = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ModelIOError(f"model output is not one JSON object: {exc}") from exc
    if not isinstance(value, Mapping):
        raise ModelIOError("function call must be one JSON object")
    input_payload = dict(value)

    name_keys = [key for key in ("function", "name", "tool") if key in value]
    argument_keys = [
        key
        for key in ("params", "parameters", "arguments", "args", "function_args")
        if key in value
    ]
    if not name_keys and not argument_keys and len(value) == 1:
        name, arguments = next(iter(value.items()))
        if not isinstance(name, str) or not name.strip():
            raise ModelIOError("single-key call requires a non-empty operation name")
        if not isinstance(arguments, Mapping):
            raise ModelIOError("single-key call requires an argument object")
        transformations.append("call_envelope:single_key_object->function+params")
    else:
        if len(name_keys) != 1 or len(argument_keys) != 1:
            raise ModelIOError(
                "function call requires exactly one function/name/tool and one "
                "params/parameters/arguments/args/function_args key"
            )
        if set(value) != {name_keys[0], argument_keys[0]}:
            raise ModelIOError("function call contains fields outside its call envelope")
        name = value[name_keys[0]]
        arguments = value[argument_keys[0]]
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ModelIOError("function name must be a trimmed non-empty string")
        if not isinstance(arguments, Mapping):
            raise ModelIOError("function parameters must be an object")
        if (name_keys[0], argument_keys[0]) != ("function", "params"):
            transformations.append(
                f"call_envelope:{name_keys[0]}+{argument_keys[0]}->function+params"
            )

    normalized = {"function": name, "params": dict(arguments)}
    return ModelCommand(str(name), dict(arguments)), ModelCommandNormalization(
        input_payload=input_payload,
        normalized_payload=normalized,
        transformations=tuple(transformations),
    )


def parse_model_command(raw_output: str) -> ModelCommand:
    command, _ = parse_model_command_with_trace(raw_output)
    return command


def validate_final_answer(command: ModelCommand) -> None:
    if command.name != "final_answer":
        raise ModelIOError("terminal response must use final_answer")
    if set(command.arguments) != {"text"}:
        raise ModelIOError("final_answer requires exactly text")
    text = command.arguments.get("text")
    if not isinstance(text, str) or not text.strip():
        raise ModelIOError("final_answer text must be non-empty")


__all__ = [
    "FINAL_ANSWER_DEFINITION",
    "JSON_CALL_STOP_SUFFIXES",
    "MODEL_COMMAND_NORMALIZER_VERSION",
    "ModelCommand",
    "ModelCommandNormalization",
    "ModelIOError",
    "canonical_digest",
    "canonical_json",
    "parse_model_command",
    "parse_model_command_with_trace",
    "render_bootstrap",
    "render_event_append",
    "validate_final_answer",
]
