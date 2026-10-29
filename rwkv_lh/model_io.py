"""Minimal G1i wire boundary for direct operation-specific calls."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from rwkv_lh.schema import ModelEvent


class ModelIOError(ValueError):
    """A generated response is not exactly one explicit function call."""


MODEL_COMMAND_NORMALIZER_VERSION = "direct-call-envelope.v4"

ASSISTANT_JSON_CONTINUATION_ANCHOR = "\n\nAssistant: ```json\n"
TOOL_CALL_JSON_CONTINUATION_ANCHOR = "\n\n**Tool Call:**\n\n```json\n"

JSON_CALL_STOP_SUFFIXES: tuple[str, ...] = (
    "\n```",
    # G1J may leave the JSON tool-call mode through its native dialogue token
    # before emitting the next role.  Stop at the transport boundary itself;
    # waiting for a later plain-text role marker turns an otherwise exact JSON
    # object into an invalid multi-turn response.
    "✿text1✿",
    "\n`✿text1✿",
    "\nSystem:",
    "\nUser:",
    "\nAssistant:",
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
    *,
    native_tool_call_json: bool = False,
) -> str:
    request = str(assignment or "").strip()
    if not request:
        raise ModelIOError("assignment must be non-empty")
    if not definitions:
        raise ModelIOError("at least one operation definition is required")
    generation_anchor = (
        TOOL_CALL_JSON_CONTINUATION_ANCHOR
        if native_tool_call_json
        else "\n\nAssistant: ```json\n"
    )
    return (
        f"System: Tools: {canonical_json([dict(item) for item in definitions])}\n"
        "Choose exactly one displayed tool. Return only one JSON function call using "
        '"function" for its name and "params" for its complete parameters. Do not '
        "describe the call outside JSON.\n\n"
        f"User: {request}"
        + generation_anchor
    )




def render_tool_disclosure(definition: Mapping[str, Any]) -> str:
    """Render one selected operation contract outside the system message."""

    selected = dict(definition)
    name = str(selected.get("name") or "").strip()
    parameters = selected.get("parameters")
    if not name or not isinstance(parameters, Mapping):
        raise ModelIOError("selected operation requires a name and parameter schema")
    return (
        "\n\nUser: Controller-selected operation contract: "
        + canonical_json(
            {
                "selected_operation": name,
                "selected_tool_contract": selected,
            }
        )
        + "\nReturn only one direct JSON function call for this selected operation, "
        'using "function" for its name and "params" for the complete parameter '
        "object. Do not select another operation and do not describe the call.\n\n"
        "Assistant: ```json\n"
    )








def _close_generation_anchor(previous_transcript: str, *, completed: bool = False) -> str:
    """End a runtime-owned, empty JSON opener before appending another turn.

    Rollback restores the input checkpoint, including its generation opener.
    This adds only protocol framing; rejected output and answers are untouched.
    A committed response never ends with an unused canonical opener.
    """
    anchors = (ASSISTANT_JSON_CONTINUATION_ANCHOR, TOOL_CALL_JSON_CONTINUATION_ANCHOR)
    return "\n```\n" if previous_transcript and (completed or previous_transcript.endswith(anchors)) else ""


def render_event_append(
    event: ModelEvent,
    visible_definitions: Sequence[Mapping[str, Any]] = (),
    *,
    include_generation_anchor: bool = True,
    previous_transcript: str = "",
    close_generation_anchor: bool = False,
) -> str:
    event_prefix = "\n\nUser: Function output: "
    scope = ""
    if visible_definitions:
        scope = (
            "\n\nSystem: Tools: "
            + canonical_json([dict(item) for item in visible_definitions])
            + "\nChoose exactly one displayed tool and return one JSON function call."
        )
    rendered = (
        _close_generation_anchor(previous_transcript, completed=close_generation_anchor)
        + scope
        + event_prefix
        + canonical_json(event.to_model_dict())
    )
    if include_generation_anchor:
        rendered += ASSISTANT_JSON_CONTINUATION_ANCHOR
    return rendered


def render_rollover_event_summary(
    events: Sequence[ModelEvent],
    *,
    include_generation_anchor: bool = True,
    previous_transcript: str = "",
) -> str:
    """Render the exact event bodies that remain visible after a rollover."""

    selected = tuple(events)
    if not selected:
        return ""
    event_ids = [event.event_id for event in selected]
    if len(set(event_ids)) != len(event_ids):
        raise ModelIOError("rollover event summary contains duplicate event ids")
    rendered = (
        _close_generation_anchor(previous_transcript)
        + "\n\nUser: Deterministic recent controller event summary: "
        + canonical_json([event.to_model_dict() for event in selected])
        + "\nThese controller-produced event bodies remain visible after context "
        "rollover. Use their exact errors and observations when choosing the next "
        "call."
    )
    if include_generation_anchor:
        rendered += ASSISTANT_JSON_CONTINUATION_ANCHOR
    return rendered


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
        if not text:
            raise ModelIOError("Markdown code fence has no JSON body")
        transformations.append("surface:markdown_code_fence_removed")
    # A second top-level object is never part of the one-call wire contract.
    # Keep the first object byte-for-byte and drop only a trailing object; a
    # stop string on "\n{" would instead truncate a leading blank line or a
    # pretty-printed nested object.
    if text.startswith("{"):
        try:
            _value, end = json.JSONDecoder().raw_decode(text)
        except json.JSONDecodeError:
            pass
        else:
            remainder = text[end:].strip()
            if remainder.startswith("{"):
                text = text[:end].rstrip()
                transformations.append("surface:trailing_second_object_removed")
    return text, transformations


def _repair_structural_escaped_quotes(text: str) -> str | None:
    """Repair model-emitted ``\"`` delimiters outside JSON strings.

    Some RWKV generations emit an object-shaped argument value but escape its
    member-string delimiters as though that object were itself a JSON string,
    for example ``{"arguments": {\"path\": \"a.txt\"}}``.  This is not valid
    JSON.  Keep the recovery deliberately narrow: only reinterpret a backslash
    quote encountered outside a normal JSON string, and only close that repaired
    string where a JSON key or value may end.  The caller still requires the
    repaired text to decode as one object and pass the ordinary call contract.
    """

    output: list[str] = []
    string_mode = ""
    normal_escape = False
    repaired_delimiters = 0
    index = 0
    length = len(text)
    while index < length:
        character = text[index]
        following = text[index + 1] if index + 1 < length else ""
        if not string_mode:
            if character == '"':
                output.append(character)
                string_mode = "normal"
                normal_escape = False
                index += 1
                continue
            if character == "\\" and following == '"':
                output.append('"')
                string_mode = "repaired"
                repaired_delimiters += 1
                index += 2
                continue
            output.append(character)
            index += 1
            continue

        if string_mode == "normal":
            output.append(character)
            if normal_escape:
                normal_escape = False
            elif character == "\\":
                normal_escape = True
            elif character == '"':
                string_mode = ""
            index += 1
            continue

        if character == "\\" and following == '"':
            lookahead = index + 2
            while lookahead < length and text[lookahead].isspace():
                lookahead += 1
            next_significant = text[lookahead] if lookahead < length else ""
            if not next_significant or next_significant in ":,}]":
                output.append('"')
                string_mode = ""
                repaired_delimiters += 1
            else:
                output.extend((character, following))
            index += 2
            continue
        output.append(character)
        index += 1

    if string_mode == "repaired" or repaired_delimiters < 2:
        return None
    repaired = "".join(output)
    return repaired if repaired != text else None


def load_model_json(source: str):
    """Reject ambiguous objects, including nested/string-encoded arguments."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ModelIOError(f'duplicate JSON key: {key!r}')
            result[key] = value
        return result
    return json.loads(source, object_pairs_hook=unique_object)


def parse_model_command_with_trace(
    raw_output: str,
) -> tuple[ModelCommand, ModelCommandNormalization]:
    """Normalize only common call-envelope spellings and Markdown fencing."""

    text, transformations = _extract_json(raw_output)
    try:
        value = load_model_json(text)
    except json.JSONDecodeError as original_exc:
        repaired = _repair_structural_escaped_quotes(text)
        if repaired is None:
            raise ModelIOError(
                f"model output is not one JSON object: {original_exc}"
            ) from original_exc
        try:
            value = load_model_json(repaired)
        except json.JSONDecodeError:
            raise ModelIOError(
                f"model output is not one JSON object: {original_exc}"
            ) from original_exc
        transformations.append("surface:structural_escaped_quotes_repaired")
    if not isinstance(value, Mapping):
        raise ModelIOError("function call must be one JSON object")
    input_payload = dict(value)

    if set(value) == {"function_call"}:
        call = value["function_call"]
        if not isinstance(call, Mapping) or set(call) != {"name", "arguments"}:
            raise ModelIOError(
                "function_call envelope requires exactly name and arguments"
            )
        name = call["name"]
        arguments = call["arguments"]
        if isinstance(arguments, str):
            try:
                arguments = load_model_json(arguments)
            except json.JSONDecodeError as exc:
                raise ModelIOError(
                    f"function_call arguments are not one JSON object: {exc}"
                ) from exc
            transformations.append(
                "call_envelope:function_call.arguments_json_decoded"
            )
        if not isinstance(name, str) or not name.strip() or name != name.strip():
            raise ModelIOError("function name must be a trimmed non-empty string")
        if not isinstance(arguments, Mapping):
            raise ModelIOError("function parameters must be an object")
        transformations.append(
            "call_envelope:function_call.name+arguments->function+params"
        )
    else:
        name_keys = [key for key in ("function", "name", "tool") if key in value]
        argument_keys = [
            key
            for key in (
                "params",
                "parameters",
                "arguments",
                "args",
                "function_args",
            )
            if key in value
        ]
        if not name_keys and not argument_keys and len(value) == 1:
            name, arguments = next(iter(value.items()))
            if not isinstance(name, str) or not name.strip():
                raise ModelIOError(
                    "single-key call requires a non-empty operation name"
                )
            if not isinstance(arguments, Mapping):
                raise ModelIOError("single-key call requires an argument object")
            transformations.append(
                "call_envelope:single_key_object->function+params"
            )
        else:
            if len(name_keys) != 1 or len(argument_keys) != 1:
                raise ModelIOError(
                    "function call requires exactly one function/name/tool and one "
                    "params/parameters/arguments/args/function_args key"
                )
            if set(value) != {name_keys[0], argument_keys[0]}:
                raise ModelIOError(
                    "function call contains fields outside its call envelope"
                )
            name = value[name_keys[0]]
            arguments = value[argument_keys[0]]
            if not isinstance(name, str) or not name.strip() or name != name.strip():
                raise ModelIOError("function name must be a trimmed non-empty string")
            if argument_keys[0] in {"arguments", "function_args"} and isinstance(
                arguments, str
            ):
                try:
                    arguments = load_model_json(arguments)
                except json.JSONDecodeError as exc:
                    raise ModelIOError(
                        f"{argument_keys[0]} are not one JSON object: {exc}"
                    ) from exc
                transformations.append(
                    f"call_envelope:{name_keys[0]}.{argument_keys[0]}_json_decoded"
                )
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
    "ASSISTANT_JSON_CONTINUATION_ANCHOR",
    "JSON_CALL_STOP_SUFFIXES",
    "MODEL_COMMAND_NORMALIZER_VERSION",
    "TOOL_CALL_JSON_CONTINUATION_ANCHOR",
    "ModelCommand",
    "ModelCommandNormalization",
    "ModelIOError",
    "canonical_digest",
    "canonical_json",
    "parse_model_command",
    "parse_model_command_with_trace",
    "render_bootstrap",
    "render_event_append",
    "render_rollover_event_summary",
    "render_tool_disclosure",
    "validate_final_answer",
]
