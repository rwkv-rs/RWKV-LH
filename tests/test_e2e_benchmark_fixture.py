from __future__ import annotations

from rwkv_lh.schema import TaskAction
from scripts.run_rwkv_e2e_benchmark import (
    FaultInjectingHarness,
    _accepted_final_model_response,
)


def test_mock_api_extension_uses_the_authoritative_action_definition_schema() -> None:
    harness = FaultInjectingHarness(enable_mock_api=True)
    definition = harness.definition("mock_api")
    tool = {
        item["name"]: item
        for item in harness.g1i_tool_definitions(["mock_api"])
    }["mock_api"]

    assert tool["parameters"] == definition.parameters_schema()
    assert tool["parameters"]["properties"]["operation"]["enum"] == [
        "create",
        "query",
        "update",
        "finalize",
    ]
    normalized = harness.normalize_action(
        TaskAction(
            "mock_api",
            {"operation": "query", "request_id": "stable-1"},
        )
    )
    assert normalized.arguments == {
        "operation": "query",
        "request_id": "stable-1",
        "payload": {},
    }

    specs = harness.deterministic_verification_specs(normalized)
    assert specs is not None
    assert [(item.kind, item.required) for item in specs] == [
        ("action_succeeded", True)
    ]


def test_final_audit_links_the_accepted_request_not_trace_completion_order() -> None:
    selected = {
        "type": "model_session_generation_returned",
        "lane_id": "LANE:ACTION",
        "request_id": "MR-SELECTED",
        "raw_output": '{"function":"final_answer","params":{"text":"selected"}}',
    }
    later_unselected = {
        "type": "model_session_generation_returned",
        "lane_id": "LANE:ACTION",
        "request_id": "MR-UNSELECTED",
        "raw_output": '{"function":"final_answer","params":{"text":"other"}}',
    }
    event_log = [
        {
            "type": "model_call_accepted",
            "data": {
                "operation": "final_answer",
                "request_id": "MR-SELECTED",
            },
        }
    ]

    assert _accepted_final_model_response(
        [selected, later_unselected],
        event_log,
    ) == selected
