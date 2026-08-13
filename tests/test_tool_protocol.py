import json

import pytest

from rwkv_lh.tool_protocol import (
    G1iToolExchange,
    normalize_g1i_tool_call,
    normalize_g1i_tool_call_with_trace,
    normalize_plan_envelope_with_trace,
    protocol_payload_digest,
    render_g1i_tool_dialog,
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


@pytest.mark.parametrize(
    "payload,expected_transformations",
    [
        (
            {"function_call": {"name": "read_file", "arguments": {"path": "input.txt"}}},
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


@pytest.mark.parametrize(
    "payload,match",
    [
        (
            {"action": {"type": "read_file", "path": "input.txt"}},
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


def test_round23_new_action_envelopes_require_a_uniquely_selected_action():
    with pytest.raises(ValueError, match="uniquely selected action"):
        normalize_g1i_tool_call_with_trace(
            {"action_type": "read_file", "arguments": {"path": "input.txt"}}
        )


def test_round23_plan_graph_envelope_closes_registered_schema_without_task_mutation():
    tasks = [
        {
            "local_id": "step_1",
            "title": "Inspect",
            "description": "Read input",
            "dependencies": [],
            "required": True,
            "priority": 50,
            "advances_criteria": ["GC1"],
            "satisfies_criteria": [],
            "retry_policy": {"max_attempts": 3},
        }
    ]
    raw = {"task_graph": {"tasks": tasks}}
    normalized, transformations = normalize_plan_envelope_with_trace(raw)

    assert normalized["schema_version"] == "long-horizon.plan.v2"
    assert normalized["tasks"] == tasks
    assert normalized["tasks"] is tasks
    assert transformations == (
        "task_graph_tasks_to_canonical_tasks",
        "registered_plan_envelope_implies_v2",
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
            {"task_graph": {"nodes": [{"local_id": "T1"}]}},
            "explicit dependencies",
        ),
        (
            {
                "schema_version": "long-horizon.goal.v1",
                "task_graph": {"tasks": [{}]},
            },
            "unsupported registered plan envelope schema",
        ),
    ],
)
def test_round23_plan_graph_envelope_fails_closed_on_conflict(payload, match):
    with pytest.raises(ValueError, match=match):
        normalize_plan_envelope_with_trace(payload)


@pytest.mark.parametrize(
    "value,match",
    [
        ({"arguments": {}}, "non-empty name"),
        ({"name": "read_file", "arguments": []}, "must decode to an object"),
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
