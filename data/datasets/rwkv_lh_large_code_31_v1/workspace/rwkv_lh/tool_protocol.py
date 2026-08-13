"""G1i function-call framing and normalized tool-call contracts."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


G1I_TOOL_PROTOCOL_VERSION = "g1i-tool-dialog.v1"
TRANSPARENT_PROTOCOL_NORMALIZER_VERSION = "transparent-protocol-boundary.v1"
_SUPPORTED_PLAN_SCHEMAS = frozenset(
    {"long-horizon.plan.v1", "long-horizon.plan.v2"}
)


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


def protocol_payload_digest(value: Any) -> str:
    """Return a stable digest for an audited protocol payload."""

    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


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

    call, _ = normalize_g1i_tool_call_with_trace(value)
    return call


def normalize_g1i_tool_call_with_trace(
    value: Mapping[str, Any],
    *,
    expected_name: str | None = None,
) -> tuple[G1iToolCall, tuple[str, ...]]:
    """Normalize known wire envelopes while reporting every format change.

    The accepted variants all carry exactly one function name and one argument
    object. Unknown or mixed fields remain fail-closed; this function never
    invents a name, argument, or semantic value.
    """

    if not isinstance(value, Mapping):
        raise ValueError("G1i tool call must be a JSON object")
    raw = dict(value)
    transformations: list[str] = []
    normalized_expected_name = str(expected_name or "").strip()

    def require_selected_action() -> None:
        if not normalized_expected_name:
            raise ValueError(
                "registered action envelope requires one uniquely selected action"
            )

    if set(raw) == {"function_call"} and isinstance(raw["function_call"], Mapping):
        canonical = dict(raw["function_call"])
        transformations.append("function_call_envelope_to_canonical")
    elif (
        set(raw) == {"type", "function"}
        and raw.get("type") == "function"
        and isinstance(raw.get("function"), Mapping)
    ):
        canonical = dict(raw["function"])
        transformations.append("typed_function_envelope_to_canonical")
    elif (
        set(raw) == {"function", "arguments"}
        and isinstance(raw.get("function"), str)
    ):
        canonical = {"name": raw["function"], "arguments": raw["arguments"]}
        transformations.append("function_name_alias_to_canonical")
    elif set(raw) == {"type", "name", "arguments"} and raw.get("type") == "function":
        require_selected_action()
        canonical = {"name": raw["name"], "arguments": raw["arguments"]}
        transformations.append("flat_typed_function_envelope_to_canonical")
    elif set(raw) == {"action_type", "arguments"}:
        require_selected_action()
        canonical = {
            "name": raw["action_type"],
            "arguments": raw["arguments"],
        }
        transformations.append("action_type_alias_to_canonical")
    elif set(raw) == {"action"} and isinstance(raw.get("action"), Mapping):
        require_selected_action()
        action = dict(raw["action"])
        if set(action) != {"type", "arguments"}:
            unknown = sorted(set(action) - {"type", "arguments"})
            missing = sorted({"type", "arguments"} - set(action))
            raise ValueError(
                "action envelope must contain exactly type and arguments; "
                f"unknown={unknown}, missing={missing}"
            )
        canonical = {"name": action["type"], "arguments": action["arguments"]}
        transformations.append("action_envelope_to_canonical")
    elif set(raw) == {"tool_calls"}:
        require_selected_action()
        tool_calls = raw["tool_calls"]
        if not isinstance(tool_calls, list) or len(tool_calls) != 1:
            raise ValueError("tool_calls envelope must contain exactly one call")
        item = tool_calls[0]
        if not isinstance(item, Mapping):
            raise ValueError("tool_calls item must be an object")
        item = dict(item)
        if "id" in item and not isinstance(item["id"], str):
            raise ValueError("tool_calls item id must be a string")
        if {"type", "function"}.issubset(item):
            if set(item) - {"type", "function", "id"}:
                raise ValueError(
                    "tool_calls function item has unknown or mixed fields"
                )
            if item.get("type") != "function":
                raise ValueError("tool_calls item type must be function")
            function = item.get("function")
            if not isinstance(function, Mapping):
                raise ValueError("tool_calls function must be an object")
            canonical = dict(function)
            transformations.append("single_tool_calls_envelope_to_canonical")
        elif {"name", "arguments"}.issubset(item):
            if set(item) - {"name", "arguments", "id"}:
                raise ValueError(
                    "direct tool_calls item has unknown or mixed fields"
                )
            canonical = {
                "name": item["name"],
                "arguments": item["arguments"],
            }
            transformations.append(
                "single_direct_tool_calls_envelope_to_canonical"
            )
        else:
            raise ValueError(
                "tool_calls item must contain one registered function-call shape"
            )
    else:
        canonical = raw
    unknown = sorted(set(canonical) - {"name", "arguments"})
    if unknown:
        raise ValueError(f"G1i tool call has unknown fields: {unknown}")
    name = str(canonical.get("name") or "").strip()
    if not name:
        raise ValueError("G1i tool call requires a non-empty name")
    if normalized_expected_name and name != normalized_expected_name:
        raise ValueError(
            "G1i tool call name does not match the uniquely selected action: "
            f"expected {normalized_expected_name!r}, got {name!r}"
        )
    arguments: Any = canonical.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("G1i tool-call arguments contain invalid JSON") from exc
        transformations.append("json_string_to_object")
    if not isinstance(arguments, Mapping):
        raise ValueError("G1i tool-call arguments must decode to an object")
    return G1iToolCall(name=name, arguments=dict(arguments)), tuple(transformations)


def normalize_plan_envelope_with_trace(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Normalize only pre-registered, unambiguous plan wire envelopes.

    Task objects and their order are retained verbatim. A missing protocol
    version is closed only for the explicitly registered task_graph envelope;
    bare task fragments remain invalid and no semantic task field is inferred.
    """

    if not isinstance(value, Mapping):
        raise ValueError("plan payload must be a JSON object")
    raw = dict(value)
    graph = raw.get("task_graph")
    graph_tasks = graph.get("tasks") if isinstance(graph, Mapping) else None
    graph_nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    top_tasks_present = "tasks" in raw
    graph_tasks_present = isinstance(graph, Mapping) and "tasks" in graph
    graph_nodes_present = isinstance(graph, Mapping) and "nodes" in graph

    if top_tasks_present and (graph_tasks_present or graph_nodes_present):
        raise ValueError("plan payload contains conflicting task arrays")
    if graph_tasks_present and graph_nodes_present:
        raise ValueError("task_graph contains multiple task arrays")
    if top_tasks_present:
        return raw, ()
    if not isinstance(graph, Mapping):
        return raw, ()

    source = ""
    tasks: Any = None
    if graph_tasks_present:
        if not isinstance(graph_tasks, list) or not graph_tasks:
            raise ValueError("task_graph.tasks must be a non-empty array")
        source = "task_graph.tasks"
        tasks = graph_tasks
    elif graph_nodes_present:
        if not isinstance(graph_nodes, list) or not graph_nodes:
            raise ValueError("task_graph.nodes must be a non-empty array")
        if not all(
            isinstance(item, Mapping) and "dependencies" in item
            for item in graph_nodes
        ):
            raise ValueError(
                "task_graph.nodes requires explicit dependencies on every node"
            )
        source = "task_graph.nodes"
        tasks = graph_nodes
    else:
        return raw, ()

    schema = str(raw.get("schema_version") or "").strip()
    transformations = [f"{source.replace('.', '_')}_to_canonical_tasks"]
    normalized = dict(raw)
    normalized["tasks"] = tasks
    if schema:
        if schema not in _SUPPORTED_PLAN_SCHEMAS:
            raise ValueError(f"unsupported registered plan envelope schema: {schema}")
    else:
        normalized["schema_version"] = "long-horizon.plan.v2"
        transformations.append("registered_plan_envelope_implies_v2")
    return normalized, tuple(transformations)


__all__ = [
    "G1I_TOOL_PROTOCOL_VERSION",
    "TRANSPARENT_PROTOCOL_NORMALIZER_VERSION",
    "G1iToolCall",
    "G1iToolExchange",
    "normalize_g1i_tool_call",
    "normalize_g1i_tool_call_with_trace",
    "normalize_plan_envelope_with_trace",
    "protocol_payload_digest",
    "render_g1i_tool_dialog",
]
