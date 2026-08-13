"""G1i function-call framing and normalized tool-call contracts."""

from __future__ import annotations

import json
import hashlib
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


G1I_TOOL_PROTOCOL_VERSION = "g1i-tool-dialog.v1"
TRANSPARENT_PROTOCOL_NORMALIZER_VERSION = "transparent-protocol-boundary.v4"
TASK_BATCH_SCHEMA_VERSION = "long-horizon.task-batch.v1"
TASK_COMMIT_SCHEMA_VERSION = "long-horizon.task-commit.v1"

# Only exact spellings observed in the frozen Round33 traces are registered.
# This table changes representation, never object shape or semantic fields.
REGISTERED_PROTOCOL_SCHEMA_ALIASES = {
    TASK_BATCH_SCHEMA_VERSION: frozenset(
        {"rwkv-lh.task-batch.v1", "rwkv-lh.task_batch.v1"}
    ),
    TASK_COMMIT_SCHEMA_VERSION: frozenset({"rwkv-lh.task-commit.v1"}),
}

# An exact Task-commit object with both semantic fields but no protocol tag is
# a registered RWKV wire form. The converter adds only fixed format metadata;
# any other missing-schema shape remains fail-closed.
REGISTERED_MISSING_SCHEMA_FIELDS = {
    TASK_COMMIT_SCHEMA_VERSION: frozenset({"reason", "decision"}),
}

# Five wire-format families cover the forms observed in frozen RWKV runs.  This
# is deliberately a closed list: adding another spelling requires a new audited
# protocol version, rather than another permissive coercion in business logic.
REGISTERED_TOOL_ENVELOPE_FAMILIES = (
    "canonical_call",
    "flat_name_alias",
    "flat_args_alias",
    "single_nested_call",
    "single_tool_calls",
)

_FLAT_NAME_ALIASES = {
    frozenset({"name", "arguments"}): ("name", None),
    frozenset({"function", "arguments"}): (
        "function",
        "function_name_alias_to_canonical",
    ),
    frozenset({"tool", "arguments"}): ("tool", "tool_name_alias_to_canonical"),
    frozenset({"action_type", "arguments"}): (
        "action_type",
        "action_type_alias_to_canonical",
    ),
}


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


def convert_protocol_schema_format_with_trace(
    value: Mapping[str, Any],
    *,
    canonical_schema: str,
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Convert one registered schema spelling without validating its object.

    Every semantic key and value is retained. Unknown schema versions and
    unregistered missing-schema shapes are returned unchanged so the one
    downstream canonical validator can reject them.
    """

    if not isinstance(value, Mapping):
        raise ValueError("protocol payload must be a JSON object")
    converted = dict(value)
    schema = converted.get("schema_version")
    missing_fields = REGISTERED_MISSING_SCHEMA_FIELDS.get(canonical_schema)
    if schema is None and missing_fields is not None and set(converted) == missing_fields:
        return (
            {"schema_version": canonical_schema, **converted},
            (f"missing_schema_tag->{canonical_schema}",),
        )
    aliases = REGISTERED_PROTOCOL_SCHEMA_ALIASES.get(canonical_schema, frozenset())
    if not isinstance(schema, str) or schema not in aliases:
        return converted, ()
    converted["schema_version"] = canonical_schema
    return converted, (f"schema_alias:{schema}->{canonical_schema}",)


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


def _unwrap_registered_tool_envelope(
    raw: dict[str, Any],
) -> tuple[dict[str, Any], list[str]]:
    """Remove one registered wire envelope without interpreting its payload."""

    fields = frozenset(raw)
    alias = _FLAT_NAME_ALIASES.get(fields)
    if alias is not None:
        name_field, transformation = alias
        canonical = {"name": raw[name_field], "arguments": raw["arguments"]}
        return canonical, [transformation] if transformation else []

    if fields == frozenset({"tool", "args"}):
        return (
            {"name": raw["tool"], "arguments": raw["args"]},
            ["tool_args_alias_to_canonical"],
        )

    if fields == frozenset({"type", "name", "arguments"}):
        if raw.get("type") != "function":
            raise ValueError("flat typed call type must be function")
        return (
            {"name": raw["name"], "arguments": raw["arguments"]},
            ["flat_typed_function_envelope_to_canonical"],
        )

    if fields == frozenset({"function_call"}):
        nested = raw["function_call"]
        if not isinstance(nested, Mapping):
            raise ValueError("function_call must be an object")
        return dict(nested), ["function_call_envelope_to_canonical"]

    if fields == frozenset({"type", "function"}):
        if raw.get("type") != "function":
            raise ValueError("typed function call type must be function")
        nested = raw["function"]
        if not isinstance(nested, Mapping):
            raise ValueError("typed function call must contain a function object")
        return dict(nested), ["typed_function_envelope_to_canonical"]

    if fields == frozenset({"action"}):
        nested = raw["action"]
        if not isinstance(nested, Mapping):
            raise ValueError("action envelope must contain an object")
        action = dict(nested)
        if set(action) == {"type", "arguments"}:
            return (
                {"name": action["type"], "arguments": action["arguments"]},
                ["action_envelope_to_canonical"],
            )
        if "type" in action and "arguments" not in action and len(action) > 1:
            return (
                {
                    "name": action["type"],
                    "arguments": {
                        key: item for key, item in action.items() if key != "type"
                    },
                },
                ["flat_action_envelope_to_canonical"],
            )
        else:
            unknown = sorted(set(action) - {"type", "arguments"})
            missing = sorted({"type", "arguments"} - set(action))
            raise ValueError(
                "action envelope must contain exactly type and arguments; "
                f"unknown={unknown}, missing={missing}"
            )

    if "action_type" in raw and "arguments" not in raw and len(raw) > 1:
        return (
            {
                "name": raw["action_type"],
                "arguments": {
                    key: item for key, item in raw.items() if key != "action_type"
                },
            },
            ["flat_action_type_envelope_to_canonical"],
        )

    if fields != frozenset({"tool_calls"}):
        return raw, []

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
            raise ValueError("tool_calls function item has unknown or mixed fields")
        if item.get("type") != "function":
            raise ValueError("tool_calls item type must be function")
        function = item.get("function")
        if not isinstance(function, Mapping):
            raise ValueError("tool_calls function must be an object")
        return dict(function), ["single_tool_calls_envelope_to_canonical"]
    if {"name", "arguments"}.issubset(item):
        if set(item) - {"name", "arguments", "id"}:
            raise ValueError("direct tool_calls item has unknown or mixed fields")
        return (
            {"name": item["name"], "arguments": item["arguments"]},
            ["single_direct_tool_calls_envelope_to_canonical"],
        )
    raise ValueError(
        "tool_calls item must contain one registered function-call shape"
    )


def normalize_g1i_tool_call_with_trace(
    value: Mapping[str, Any],
    *,
    expected_name: str | None = None,
) -> tuple[G1iToolCall, tuple[str, ...]]:
    """Compose format conversion with the one canonical call validator.

    Conversion only changes a registered wire representation. Name selection,
    canonical schema checks, and argument type checks remain downstream
    protocol validation and are not responsibilities of the format layer.
    """

    canonical, transformations = convert_g1i_tool_call_format_with_trace(value)
    call = validate_canonical_g1i_tool_call(
        canonical,
        expected_name=expected_name,
    )
    return call, transformations


def convert_g1i_tool_call_format_with_trace(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Convert registered RWKV call formats without judging their content."""

    if not isinstance(value, Mapping):
        raise ValueError("G1i tool call must be a JSON object")
    canonical, transformations = _unwrap_registered_tool_envelope(dict(value))
    arguments: Any = canonical.get("arguments")
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError as exc:
            raise ValueError("G1i tool-call arguments contain invalid JSON") from exc
        canonical = {**canonical, "arguments": arguments}
        transformations.append("json_string_to_object")
    return canonical, tuple(transformations)


def validate_canonical_g1i_tool_call(
    value: Mapping[str, Any],
    *,
    expected_name: str | None = None,
) -> G1iToolCall:
    """Validate the only call shape accepted by internal project code."""

    canonical = dict(value)
    unknown = sorted(set(canonical) - {"name", "arguments"})
    if unknown:
        raise ValueError(f"G1i tool call has unknown fields: {unknown}")
    raw_name = canonical.get("name")
    if not isinstance(raw_name, str) or not raw_name or raw_name != raw_name.strip():
        raise ValueError("G1i tool call requires a non-empty name")
    name = raw_name
    if expected_name and name != expected_name:
        raise ValueError(
            "G1i tool call name does not match the uniquely selected action: "
            f"expected {expected_name!r}, got {name!r}"
        )
    arguments: Any = canonical.get("arguments")
    if not isinstance(arguments, Mapping):
        raise ValueError("G1i tool-call arguments must be an object")
    return G1iToolCall(name=name, arguments=dict(arguments))


def normalize_task_batch_envelope_with_trace(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Compose Task-batch format conversion with canonical validation."""

    canonical, transformations = convert_task_batch_format_with_trace(value)
    validate_canonical_task_batch(canonical)
    return canonical, transformations


def convert_task_batch_format_with_trace(
    value: Mapping[str, Any],
) -> tuple[dict[str, Any], tuple[str, ...]]:
    """Convert a registered Task-batch wrapper without changing any Task.

    Task objects and their order are retained verbatim. A missing protocol
    version is always fail-closed; bare task fragments remain invalid and no
    semantic task field is inferred.
    """

    if not isinstance(value, Mapping):
        raise ValueError("task batch payload must be a JSON object")
    raw, schema_transformations = convert_protocol_schema_format_with_trace(
        value,
        canonical_schema=TASK_BATCH_SCHEMA_VERSION,
    )
    graph = raw.get("task_graph")
    graph_tasks = graph.get("tasks") if isinstance(graph, Mapping) else None
    graph_nodes = graph.get("nodes") if isinstance(graph, Mapping) else None
    top_tasks_present = "tasks" in raw
    graph_tasks_present = isinstance(graph, Mapping) and "tasks" in graph
    graph_nodes_present = isinstance(graph, Mapping) and "nodes" in graph

    if top_tasks_present and (graph_tasks_present or graph_nodes_present):
        raise ValueError("task batch payload contains conflicting task arrays")
    if graph_tasks_present and graph_nodes_present:
        raise ValueError("task_graph contains multiple task arrays")
    if top_tasks_present:
        return raw, schema_transformations
    if not isinstance(graph, Mapping):
        return raw, schema_transformations

    if set(raw) != {"schema_version", "task_graph"}:
        raise ValueError(
            "registered task batch wrapper requires exactly schema_version "
            "and task_graph"
        )
    unknown_graph_fields = set(graph) - {"tasks", "nodes", "edges"}
    if unknown_graph_fields:
        raise ValueError(
            f"task_graph contains unknown fields: {sorted(unknown_graph_fields)}"
        )

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
        return raw, schema_transformations

    schema = raw.get("schema_version")
    transformations = [
        *schema_transformations,
        f"{source.replace('.', '_')}_to_canonical_tasks",
    ]
    edges = graph.get("edges")
    if edges not in (None, []):
        if not isinstance(edges, list) or not all(
            isinstance(item, Mapping) for item in edges
        ):
            raise ValueError("task_graph.edges must be an array of objects")
        declared: set[tuple[str, str]] = set()
        for edge in edges:
            if set(edge) != {"source", "target"}:
                raise ValueError(
                    "task_graph.edges may contain only source and target"
                )
            source = edge.get("source")
            target = edge.get("target")
            if not isinstance(source, str) or not source or not isinstance(
                target, str
            ) or not target:
                raise ValueError("task_graph edge requires source and target")
            declared.add((source, target))
        mirrored = {
            (dependency, item.get("local_id"))
            for item in tasks
            if isinstance(item, Mapping)
            for dependency in item.get("dependencies") or []
            if isinstance(dependency, str)
        }
        if declared != mirrored:
            raise ValueError(
                "task_graph.edges must exactly mirror Task dependencies"
            )
        transformations.append("redundant_mirrored_edges_removed")
    normalized = {"schema_version": schema, "tasks": tasks}
    return normalized, tuple(transformations)


def validate_canonical_task_batch(value: Mapping[str, Any]) -> None:
    """Validate the only Task-batch envelope accepted by project logic."""

    if set(value) != {"schema_version", "tasks"}:
        raise ValueError(
            "canonical task batch requires exactly schema_version and tasks"
        )
    schema = value.get("schema_version")
    if schema != TASK_BATCH_SCHEMA_VERSION:
        raise ValueError(f"unsupported task batch schema: {schema}")
    if not isinstance(value.get("tasks"), list):
        raise ValueError("canonical task batch tasks must be an array")


__all__ = [
    "G1I_TOOL_PROTOCOL_VERSION",
    "REGISTERED_TOOL_ENVELOPE_FAMILIES",
    "REGISTERED_PROTOCOL_SCHEMA_ALIASES",
    "TASK_BATCH_SCHEMA_VERSION",
    "TASK_COMMIT_SCHEMA_VERSION",
    "TRANSPARENT_PROTOCOL_NORMALIZER_VERSION",
    "G1iToolCall",
    "G1iToolExchange",
    "convert_g1i_tool_call_format_with_trace",
    "convert_protocol_schema_format_with_trace",
    "convert_task_batch_format_with_trace",
    "normalize_g1i_tool_call",
    "normalize_g1i_tool_call_with_trace",
    "normalize_task_batch_envelope_with_trace",
    "protocol_payload_digest",
    "render_g1i_tool_dialog",
    "validate_canonical_g1i_tool_call",
    "validate_canonical_task_batch",
]
