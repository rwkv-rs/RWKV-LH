"""G1i function-call framing and normalized tool-call contracts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


G1I_TOOL_PROTOCOL_VERSION = "g1i-tool-dialog.v1"


@dataclass(frozen=True)
class G1iToolExchange:
    """One completed tool call and its observed function output."""

    call: Mapping[str, Any]
    function_output: Any


@dataclass(frozen=True)
class G1iToolCall:
    """A validated G1i function call with normalized object arguments."""

    name: str
    arguments: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "arguments": dict(self.arguments)}


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def render_g1i_tool_dialog(
    tools: Sequence[Mapping[str, Any]],
    task: str,
    *,
    exchanges: Sequence[G1iToolExchange] = (),
) -> str:
    """Render the exact G1i tool dialog used by the completion endpoint.

    The assistant fence is deliberately left open. With recurrent state support,
    callers can feed only the newly appended function-output segment. Until then,
    this renderer also provides a deterministic full-prefix replay fallback.
    """

    normalized_task = str(task or "").strip()
    if not normalized_task:
        raise ValueError("G1i tool dialog requires a non-empty task")
    normalized_tools = [dict(item) for item in tools]
    if not normalized_tools:
        raise ValueError("G1i tool dialog requires at least one tool")
    parts = [
        f"System: Tools: {_canonical_json(normalized_tools)}\n",
        "Return only a JSON function call.\n\n",
        f"User: {normalized_task}\n\n",
        "Assistant: ```json\n",
    ]
    for exchange in exchanges:
        call = normalize_g1i_tool_call(exchange.call)
        parts.extend(
            [
                _canonical_json(call.to_dict()),
                "\n\nUser: Function output: ",
                _canonical_json(exchange.function_output),
                "\n\nAssistant: ```json\n",
            ]
        )
    return "".join(parts)


def normalize_g1i_tool_call(value: Mapping[str, Any]) -> G1iToolCall:
    """Validate one call and decode vLLM/OpenAI-style string arguments."""

    if not isinstance(value, Mapping):
        raise ValueError("G1i tool call must be a JSON object")
    unknown = sorted(set(value) - {"name", "arguments"})
    if unknown:
        raise ValueError(f"G1i tool call has unknown fields: {unknown}")
    name = str(value.get("name") or "").strip()
    if not name:
        raise ValueError("G1i tool call requires a non-empty name")
    arguments: Any = value.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("G1i tool-call arguments contain invalid JSON") from exc
    if not isinstance(arguments, Mapping):
        raise ValueError("G1i tool-call arguments must decode to an object")
    return G1iToolCall(name=name, arguments=dict(arguments))


__all__ = [
    "G1I_TOOL_PROTOCOL_VERSION",
    "G1iToolCall",
    "G1iToolExchange",
    "normalize_g1i_tool_call",
    "render_g1i_tool_dialog",
]
