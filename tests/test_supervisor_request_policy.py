"""Provider options and output exhaustion remain visible across the JSON boundary."""
from dataclasses import replace
import json
import os

import pytest

from rwkv_lh.supervisor_openai import (
    OpenAICompatibleSupervisorClient, SupervisorAPISettings, SupervisorProtocolError,
)
from test_supervisor_openai import FakeResponse, FakeSession, response, settings


def request(client, phase="goal_plan"):
    return client._request_json(
        phase=phase, run_id="request-policy-fixture", request_digest="fixture",
        system_prompt="Return one JSON object.", request_payload={"fixture": "opaque"},
        schema={}, max_tokens=32768,
    )


def test_role_options_reach_future_provider_unchanged_and_bind_cache(tmp_path):
    configured = replace(settings(), model="future-provider-planner", stage_checker_model="future-provider-checker",
        planner_request_options={"reasoning_effort": "low", "thinking": {"type": "enabled"}},
        stage_checker_request_options={"reasoning_effort": "high"},
        plan_cache_enabled=True, plan_cache_dir=str(tmp_path))
    fake = FakeSession([response({"fixture": True}), response({"fixture": True})])
    audit = []
    client = OpenAICompatibleSupervisorClient(configured, session=fake, audit_hook=audit.append)
    request(client)
    request(client, "goal_stage_review")
    planner, checker = [post["json"] for post in fake.posts]
    assert planner["model"] == "future-provider-planner"
    assert planner["reasoning_effort"] == "low" and planner["max_tokens"] == 32768
    assert checker["model"] == "future-provider-checker" and checker["reasoning_effort"] == "high"
    assert "thinking" not in checker
    planner["thinking"]["type"] = "disabled"
    assert configured.public_dict()["planner_request_options"]["thinking"]["type"] == "enabled"
    started = [event for event in audit if event["type"] == "supervisor_request_started"]
    assert started[0]["request_options"]["reasoning_effort"] == "low"
    assert started[0]["wire_body_sha256"] != started[1]["wire_body_sha256"]
    changed = OpenAICompatibleSupervisorClient(replace(configured, planner_request_options={"reasoning_effort": "high"}))
    cache_args = dict(phase="goal_plan", cache_schema="fixture", request_payload={"fixture": "opaque"},
        system_prompt="Return one JSON object.", schema={})
    assert client._validated_response_cache_path(**cache_args) != changed._validated_response_cache_path(**cache_args)


def test_request_options_load_separately_from_role_environment(tmp_path, monkeypatch):
    for name in tuple(os.environ):
        if name.startswith(("RWKV_LH_PLANNER_", "RWKV_LH_STAGE_CHECKER_", "SUPERVISOR_")):
            monkeypatch.delenv(name)
    monkeypatch.setenv("RWKV_LH_PLANNER_REQUEST_OPTIONS", '{"reasoning_effort":"low"}')
    monkeypatch.setenv("RWKV_LH_STAGE_CHECKER_REQUEST_OPTIONS", '{"thinking":{"type":"disabled"}}')
    monkeypatch.setenv("RWKV_LH_PLANNER_BASE_URL", "https://provider.invalid")
    monkeypatch.setenv("RWKV_LH_PLANNER_API_KEY", "test-only")
    monkeypatch.setenv("RWKV_LH_PLANNER_MODEL", "future-model")
    configured = SupervisorAPISettings.from_env(tmp_path / "absent.env")
    assert configured.planner_request_options == {"reasoning_effort": "low"}
    assert configured.stage_checker_request_options == {"thinking": {"type": "disabled"}}


@pytest.mark.parametrize("options", [[], {"max_tokens": 999999}, {"model": "replacement"},
    {"messages": []}, {"response_format": {}}, {"stream": False}, {"api_key": "secret"},
    {"temperature": float("nan")}, {1: "invalid-key"}])
def test_request_options_cannot_override_contract_or_carry_non_json(options):
    with pytest.raises(ValueError, match="request options"):
        configured = replace(settings(), planner_request_options=options)
        configured.validate()


@pytest.mark.parametrize("content", ["", '{"unfinished":', '{"complete_but_truncated":true}'])
@pytest.mark.parametrize("phase", ["goal_plan", "goal_stage_review"])
def test_output_exhaustion_is_recorded_before_content_parsing_with_bounded_retry(content, phase):
    # finish_reason=length is a resource outcome: it is recorded before any
    # content parsing and retried within retry_attempts on the same budget
    # (unlike protocol defects, which never retry).
    usage = {"completion_tokens": 32768, "completion_tokens_details": {"reasoning_tokens": 32768}}
    envelope = {"model": "future-provider", "choices": [{"message": {"role": "assistant", "content": content},
        "finish_reason": "length"}], "usage": usage}
    fake = FakeSession([FakeResponse(envelope), FakeResponse(envelope)])
    audit = []
    client = OpenAICompatibleSupervisorClient(replace(settings(), retry_attempts=2, retry_backoff_seconds=0.0),
                                              session=fake, audit_hook=audit.append)
    with pytest.raises(SupervisorProtocolError, match="finish_reason") as captured:
        request(client, phase)
    assert type(captured.value).__name__ == "SupervisorGenerationInterrupted"
    assert len(fake.posts) == 2
    received = next(event for event in audit if event["type"] == "supervisor_response_envelope_received")
    failed = next(event for event in audit if event["type"] == "supervisor_request_failed")
    assert audit.index(received) < audit.index(failed)
    assert received["raw_response"] == envelope and received["usage"] == usage
    assert failed["error_category"] == "generation_limit"
    assert failed["finish_reason"] == "length" and failed["usage"] == usage
    assert failed["max_tokens"] == 32768 and not failed["retryable"]
    assert not any(event["type"] == "supervisor_request_returned" for event in audit)
    assert "test-secret-never-audited" not in json.dumps(audit)


def test_empty_natural_stop_is_still_a_protocol_error_with_envelope_evidence():
    fake = FakeSession([FakeResponse({"choices": [{"message": {"content": ""}, "finish_reason": "stop"}], "usage": {}})])
    audit = []
    client = OpenAICompatibleSupervisorClient(settings(), session=fake, audit_hook=audit.append)
    with pytest.raises(SupervisorProtocolError, match="empty JSON"):
        request(client)
    assert next(event for event in audit if event["type"] == "supervisor_request_failed")["error_category"] == "protocol"
    assert any(event["type"] == "supervisor_response_envelope_received" for event in audit)
