import json

import pytest

from rwkv_lh.tool_protocol import (
    G1iToolExchange,
    normalize_g1i_tool_call,
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
    "value,match",
    [
        ({"arguments": {}}, "non-empty name"),
        ({"name": "read_file", "arguments": []}, "must decode to an object"),
        (
            {"name": "read_file", "arguments": {}, "schema_version": "wrong"},
            "unknown fields",
        ),
    ],
)
def test_g1i_call_rejects_malformed_or_mixed_protocol_objects(value, match):
    with pytest.raises(ValueError, match=match):
        normalize_g1i_tool_call(value)
