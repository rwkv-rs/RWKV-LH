import json

import pytest

from rwkv_lh.tool_protocol import (
    G1iToolExchange,
    normalize_g1i_tool_call,
    normalize_g1i_tool_call_with_trace,
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
