import json

import pytest

from rwkv_lh.tool_protocol import (
    G1iToolExchange,
    REGISTERED_TOOL_ENVELOPE_FAMILIES,
    TASK_COMMIT_SCHEMA_VERSION,
    TASK_BATCH_SCHEMA_VERSION,
    convert_g1i_tool_call_format_with_trace,
    convert_protocol_schema_format_with_trace,
    convert_task_batch_format_with_trace,
    normalize_g1i_tool_call,
    normalize_g1i_tool_call_with_trace,
    normalize_task_batch_envelope_with_trace,
    protocol_payload_digest,
    render_g1i_tool_dialog,
    validate_canonical_g1i_tool_call,
    validate_canonical_task_batch,
)


TOOLS = [
    {
        "name": "read_file",
        "description": "Read one file.",
        "parameters": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
            "additionalProperties": False,
        },
    }
]


def test_g1i_initial_dialog_uses_online_role_and_fence_format():
    prompt = render_g1i_tool_dialog(TOOLS, "Read input.txt")
    assert prompt == (
        "System: Tools: "
        + json.dumps(TOOLS, ensure_ascii=False, separators=(",", ":"))
        + "\nReturn only a JSON function call.\n\n"
        "User: Read input.txt\n\n"
        "Assistant: ```json\n"
    )


def test_g1i_followup_uses_user_function_output_as_a_new_turn():
    prompt = render_g1i_tool_dialog(
        TOOLS,
        "Read input.txt",
        exchanges=[
            G1iToolExchange(
                call={"name": "read_file", "arguments": {"path": "input.txt"}},
                function_output={"success": True, "output": "alpha"},
            )
        ],
    )
    assert (
        '{"name":"read_file","arguments":{"path":"input.txt"}}\n\n'
        'User: Function output: {"success":true,"output":"alpha"}\n\n'
        "Assistant: ```json\n"
    ) in prompt
    assert "```\nUser: Function output" not in prompt


def test_g1i_call_normalizes_openai_style_string_arguments():
    call = normalize_g1i_tool_call(
        {"name": "read_file", "arguments": '{"path":"input.txt"}'}
    )
    assert call.to_dict() == {
        "name": "read_file",
        "arguments": {"path": "input.txt"},
    }


def test_normalizer_exposes_only_five_closed_wire_format_families():
    assert REGISTERED_TOOL_ENVELOPE_FAMILIES == (
        "canonical_call",
        "flat_name_alias",
        "flat_args_alias",
        "single_nested_call",
        "single_tool_calls",
    )


@pytest.mark.parametrize(
    "payload,expected_transformations",
    [
        (
            {
                "function_call": {
                    "name": "read_file",
                    "arguments": {"path": "input.txt"},
                }
            },
            ("function_call_envelope_to_canonical",),
        ),
        (
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "arguments": '{"path":"input.txt"}',
                },
            },
            ("typed_function_envelope_to_canonical", "json_string_to_object"),
        ),
        (
            {"function": "read_file", "arguments": {"path": "input.txt"}},
            ("function_name_alias_to_canonical",),
        ),
        (
            {"tool": "read_file", "arguments": {"path": "input.txt"}},
            ("tool_name_alias_to_canonical",),
        ),
    ],
)
def test_g1i_call_transparently_normalizes_known_single_function_envelopes(
    payload, expected_transformations
):
    call, transformations = normalize_g1i_tool_call_with_trace(payload)
    assert call.to_dict() == {
        "name": "read_file",
        "arguments": {"path": "input.txt"},
    }
    assert transformations == expected_transformations


@pytest.mark.parametrize(
    "payload,expected_transformations",
    [
        (
            {
                "type": "function",
                "name": "read_file",
                "arguments": {"path": "input.txt"},
            },
            ("flat_typed_function_envelope_to_canonical",),
        ),
        (
            {
                "action_type": "read_file",
                "arguments": {"path": "input.txt"},
            },
            ("action_type_alias_to_canonical",),
        ),
        (
            {
                "action": {
                    "type": "read_file",
                    "arguments": {"path": "input.txt"},
                }
            },
            ("action_envelope_to_canonical",),
        ),
        (
            {
                "action": {
                    "type": "read_file",
                    "path": "input.txt",
                }
            },
            ("flat_action_envelope_to_canonical",),
        ),
        (
            {
                "action_type": "read_file",
                "path": "input.txt",
            },
            ("flat_action_type_envelope_to_canonical",),
        ),
        (
            {
                "tool_calls": [
                    {
                        "id": "call-1",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": '{"path":"input.txt"}',
                        },
                    }
                ]
            },
            ("single_tool_calls_envelope_to_canonical", "json_string_to_object"),
        ),
        (
            {
                "tool_calls": [
                    {
                        "name": "read_file",
                        "arguments": {"path": "input.txt"},
                    }
                ]
            },
            ("single_direct_tool_calls_envelope_to_canonical",),
        ),
    ],
)
def test_round23_registered_action_envelopes_are_transparent_and_name_bound(
    payload, expected_transformations
):
    call, transformations = normalize_g1i_tool_call_with_trace(
        payload,
        expected_name="read_file",
    )
    assert call.to_dict() == {
        "name": "read_file",
        "arguments": {"path": "input.txt"},
    }
    assert transformations == expected_transformations


def test_round36_tool_args_alias_changes_only_wire_keys():
    args = {
        "path": "result.txt",
        "start_char": 0,
        "max_chars": 16000,
        "nested": {"preserved": [1, "two", False]},
    }
    raw = {"tool": "read_file", "args": args}

    converted, transformations = convert_g1i_tool_call_format_with_trace(raw)

    assert raw == {"tool": "read_file", "args": args}
    assert converted == {"name": "read_file", "arguments": args}
    assert converted["arguments"] is args
    assert transformations == ("tool_args_alias_to_canonical",)


@pytest.mark.parametrize(
    "payload,match",
    [
        ({"tool": "read_file", "args": []}, "must be an object"),
        ({"tool": "read_file", "args": None}, "must be an object"),
        ({"tool": "", "args": {}}, "non-empty name"),
        (
            {"tool": "read_file", "args": {}, "arguments": {}},
            "unknown fields",
        ),
        (
            {"tool": "read_file", "args": {}, "reasoning": "extra"},
            "unknown fields",
        ),
    ],
)
def test_round36_tool_args_alias_does_not_coerce_or_drop_fields(payload, match):
    with pytest.raises(ValueError, match=match):
        normalize_g1i_tool_call_with_trace(payload)


@pytest.mark.parametrize(
    "payload,match",
    [
        (
            {"action": {"type": "read_file"}},
            "exactly type and arguments",
        ),
        ({"tool_calls": []}, "exactly one call"),
        (
            {
                "tool_calls": [
                    {
                        "type": "function",
                        "function": {"name": "read_file", "arguments": {}},
                    },
                    {
                        "type": "function",
                        "function": {"name": "read_file", "arguments": {}},
                    },
                ]
            },
            "exactly one call",
        ),
        (
            {"action_type": "write_file", "arguments": {"path": "input.txt"}},
            "does not match",
        ),
        (
            {
                "name": "read_file",
                "arguments": {},
                "action_type": "read_file",
            },
            "unknown fields",
        ),
    ],
)
def test_round23_registered_action_envelopes_fail_closed_on_ambiguity(
    payload, match
):
    with pytest.raises(ValueError, match=match):
        normalize_g1i_tool_call_with_trace(payload, expected_name="read_file")


@pytest.mark.parametrize(
    "payload",
    [
        {"action_type": "read_file", "arguments": {"path": "input.txt"}},
        {
            "action": {
                "type": "read_file",
                "arguments": {"path": "input.txt"},
            }
        },
        {
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "input.txt"},
                    },
                }
            ]
        },
    ],
)
def test_registered_action_envelopes_select_their_own_explicit_tool(payload):
    call, transformations = normalize_g1i_tool_call_with_trace(payload)
    assert call.to_dict() == {
        "name": "read_file",
        "arguments": {"path": "input.txt"},
    }
    assert transformations


@pytest.mark.parametrize(
    "payload",
    [
        {"name": 123, "arguments": {"path": "input.txt"}},
        {"tool": 123, "arguments": {"path": "input.txt"}},
        {"action": {"type": 123, "arguments": {"path": "input.txt"}}},
        {"name": " read_file ", "arguments": {"path": "input.txt"}},
    ],
)
def test_format_boundary_never_coerces_or_trims_a_tool_name(payload):
    with pytest.raises(ValueError, match="non-empty name"):
        normalize_g1i_tool_call_with_trace(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "read_file", "arguments": {"path": "input.txt", "mode": 7}},
        {"tool": "read_file", "arguments": {"path": "input.txt", "mode": 7}},
        {
            "action": {
                "type": "read_file",
                "arguments": {"path": "input.txt", "mode": 7},
            }
        },
        {"action": {"type": "read_file", "path": "input.txt", "mode": 7}},
        {"action_type": "read_file", "path": "input.txt", "mode": 7},
        {
            "tool_calls": [
                {
                    "type": "function",
                    "function": {
                        "name": "read_file",
                        "arguments": {"path": "input.txt", "mode": 7},
                    },
                }
            ]
        },
    ],
)
def test_every_wire_family_preserves_the_complete_argument_object(payload):
    call, _ = normalize_g1i_tool_call_with_trace(payload)
    assert call.arguments == {"path": "input.txt", "mode": 7}


def test_task_batch_graph_wrapper_normalizes_to_one_canonical_envelope():
    tasks = [
        {
            "local_id": "step_1",
            "title": "Inspect",
            "description": "Read input",
            "dependencies": [],
            "postcondition": "The input is observed",
        },
        {
            "local_id": "step_2",
            "title": "Summarize",
            "description": "Summarize the observed input",
            "dependencies": ["step_1"],
            "postcondition": "The input summary is observed",
        },
    ]
    raw = {
        "schema_version": TASK_BATCH_SCHEMA_VERSION,
        "task_graph": {
            "tasks": tasks,
            "edges": [{"source": "step_1", "target": "step_2"}],
        },
    }
    normalized, transformations = normalize_task_batch_envelope_with_trace(raw)

    assert normalized["schema_version"] == TASK_BATCH_SCHEMA_VERSION
    assert normalized["tasks"] == tasks
    assert normalized["tasks"] is tasks
    assert set(normalized) == {"schema_version", "tasks"}
    assert transformations == (
        "task_graph_tasks_to_canonical_tasks",
        "redundant_mirrored_edges_removed",
    )
    assert protocol_payload_digest(raw) != protocol_payload_digest(normalized)


@pytest.mark.parametrize(
    "payload,match",
    [
        (
            {"tasks": [{}], "task_graph": {"tasks": [{}]}},
            "conflicting task arrays",
        ),
        (
            {"task_graph": {"tasks": [{}], "nodes": [{}]}},
            "multiple task arrays",
        ),
        (
            {
                "schema_version": TASK_BATCH_SCHEMA_VERSION,
                "task_graph": {"nodes": [{"local_id": "T1"}]},
            },
            "explicit dependencies",
        ),
        (
            {
                "schema_version": "long-horizon.goal.v1",
                "task_graph": {"tasks": [{}]},
            },
            "unsupported task batch schema",
        ),
        (
            {
                "schema_version": TASK_BATCH_SCHEMA_VERSION,
                "task_graph": {
                    "tasks": [
                        {
                            "local_id": "T2",
                            "dependencies": ["T1"],
                        }
                    ],
                    "edges": [{"source": "T9", "target": "T2"}],
                },
            },
            "exactly mirror Task dependencies",
        ),
        (
            {
                "schema_version": TASK_BATCH_SCHEMA_VERSION,
                "task_graph": {
                    "tasks": [
                        {
                            "local_id": "T2",
                            "dependencies": ["T1"],
                        }
                    ],
                    "edges": [
                        {
                            "source": "T1",
                            "target": "T2",
                            "description": "then summarize",
                        }
                    ],
                },
            },
            "only source and target",
        ),
    ],
)
def test_round23_plan_graph_envelope_fails_closed_on_conflict(payload, match):
    with pytest.raises(ValueError, match=match):
        normalize_task_batch_envelope_with_trace(payload)


@pytest.mark.parametrize(
    "value,match",
    [
        ({"arguments": {}}, "non-empty name"),
        ({"name": "read_file", "arguments": []}, "must be an object"),
        (
            {"name": "read_file", "arguments": {}, "schema_version": "wrong"},
            "unknown fields",
        ),
        (
            {
                "type": "function",
                "function": {"name": "read_file", "arguments": {}},
                "extra": True,
            },
            "unknown fields",
        ),
    ],
)
def test_g1i_call_rejects_malformed_or_mixed_protocol_objects(value, match):
    with pytest.raises(ValueError, match=match):
        normalize_g1i_tool_call(value)


def test_format_converter_does_not_assume_canonical_call_is_semantically_valid():
    raw = {"function": "", "arguments": {"path": "input.txt"}}

    converted, transformations = convert_g1i_tool_call_format_with_trace(raw)

    assert converted == {"name": "", "arguments": {"path": "input.txt"}}
    assert transformations == ("function_name_alias_to_canonical",)
    with pytest.raises(ValueError, match="non-empty name"):
        validate_canonical_g1i_tool_call(converted)


def test_task_format_converter_preserves_wrong_schema_for_canonical_validator():
    tasks = [{"local_id": "T1", "dependencies": []}]
    converted, transformations = convert_task_batch_format_with_trace(
        {
            "schema_version": "wrong",
            "task_graph": {"tasks": tasks},
        }
    )

    assert converted == {"schema_version": "wrong", "tasks": tasks}
    assert converted["tasks"] is tasks
    assert transformations == ("task_graph_tasks_to_canonical_tasks",)
    with pytest.raises(ValueError, match="unsupported task batch schema"):
        validate_canonical_task_batch(converted)


@pytest.mark.parametrize(
    "alias,canonical",
    [
        ("rwkv-lh.task-commit.v1", TASK_COMMIT_SCHEMA_VERSION),
        ("rwkv-lh.task-batch.v1", TASK_BATCH_SCHEMA_VERSION),
        ("rwkv-lh.task_batch.v1", TASK_BATCH_SCHEMA_VERSION),
    ],
)
def test_round34_schema_converter_changes_only_registered_spelling(
    alias, canonical
):
    nested = {"items": [{"path": "result.txt", "value": 7}]}
    raw = {
        "schema_version": alias,
        "decision": "pass",
        "reason": "observed",
        "extra": nested,
    }

    converted, transformations = convert_protocol_schema_format_with_trace(
        raw,
        canonical_schema=canonical,
    )

    assert raw["schema_version"] == alias
    assert converted == {**raw, "schema_version": canonical}
    assert converted["extra"] is nested
    assert transformations == (f"schema_alias:{alias}->{canonical}",)


@pytest.mark.parametrize("schema", ["1", "1.0.0", "task_batch.v1", None])
def test_round34_schema_converter_leaves_unregistered_or_missing_schema_unchanged(
    schema,
):
    raw = {"tasks": []}
    if schema is not None:
        raw["schema_version"] = schema

    converted, transformations = convert_protocol_schema_format_with_trace(
        raw,
        canonical_schema=TASK_BATCH_SCHEMA_VERSION,
    )

    assert converted == raw
    assert transformations == ()


def test_round46_exact_missing_task_commit_schema_is_format_only():
    raw = {
        "reason": "The observed file still contains protocol=v1.",
        "decision": "replan",
    }

    converted, transformations = convert_protocol_schema_format_with_trace(
        raw,
        canonical_schema=TASK_COMMIT_SCHEMA_VERSION,
    )

    assert raw == {
        "reason": "The observed file still contains protocol=v1.",
        "decision": "replan",
    }
    assert converted == {
        "schema_version": TASK_COMMIT_SCHEMA_VERSION,
        **raw,
    }
    assert converted["reason"] is raw["reason"]
    assert converted["decision"] is raw["decision"]
    assert transformations == (
        f"missing_schema_tag->{TASK_COMMIT_SCHEMA_VERSION}",
    )


@pytest.mark.parametrize(
    "raw",
    [
        {"decision": "replan"},
        {"reason": "insufficient"},
        {"reason": "insufficient", "decision": "replan", "extra": True},
    ],
)
def test_round46_unregistered_missing_schema_shapes_remain_fail_closed(raw):
    converted, transformations = convert_protocol_schema_format_with_trace(
        raw,
        canonical_schema=TASK_COMMIT_SCHEMA_VERSION,
    )

    assert converted == raw
    assert transformations == ()


def test_round46_missing_schema_shape_is_not_registered_for_task_batch():
    raw = {"reason": "not a task batch", "decision": "replan"}

    converted, transformations = convert_protocol_schema_format_with_trace(
        raw,
        canonical_schema=TASK_BATCH_SCHEMA_VERSION,
    )

    assert converted == raw
    assert transformations == ()


def test_round34_task_batch_alias_reaches_only_the_canonical_validator():
    tasks = [{"local_id": "T1", "dependencies": []}]
    converted, transformations = convert_task_batch_format_with_trace(
        {
            "schema_version": "rwkv-lh.task-batch.v1",
            "tasks": tasks,
            "extra": "must remain invalid",
        }
    )

    assert converted == {
        "schema_version": TASK_BATCH_SCHEMA_VERSION,
        "tasks": tasks,
        "extra": "must remain invalid",
    }
    assert transformations == (
        "schema_alias:rwkv-lh.task-batch.v1->long-horizon.task-batch.v1",
    )
    with pytest.raises(ValueError, match="requires exactly schema_version and tasks"):
        validate_canonical_task_batch(converted)
