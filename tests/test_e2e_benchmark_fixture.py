from __future__ import annotations

from rwkv_lh.schema import TaskAction
from scripts.run_rwkv_e2e_benchmark import FaultInjectingHarness


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
