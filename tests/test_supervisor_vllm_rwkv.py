"""Native RWKV Supervisor transport retains Goal contracts and zero State."""

from __future__ import annotations

import hashlib
import json
import os
from copy import deepcopy
from dataclasses import replace

import pytest

from rwkv_lh.goal_loop_protocol import (
    GoalObligation,
    GoalPlanPatch,
    GoalPlanRequest,
    GoalPlanStep,
    GoalStageReview,
    GoalStageReviewRequest,
    GoalStageReviewVerdict,
    RollingGoalPlan,
)
from rwkv_lh.runtime.protocol import TextCompletionRequest
from rwkv_lh.runtime.sampling import sampling_parameters
from rwkv_lh.supervisor_openai import (
    OpenAICompatibleSupervisorClient,
    SupervisorAPISettings,
    SupervisorProtocolError,
    _render_user_payload,
)


def _settings(**overrides) -> SupervisorAPISettings:
    return replace(SupervisorAPISettings(
        base_url="http://supervisor.invalid/v1",
        api_key="fixture-secret-never-audited",
        model="fixture-planner-13b",
        stage_checker_model="fixture-checker-13b",
        retry_attempts=1,
        semantic_repair_attempts=0,
        plan_cache_enabled=False,
    ), **overrides)


def _native_settings(**overrides) -> SupervisorAPISettings:
    return _settings(backend_profile="vllm-rwkv-native", **overrides)


def _plan_materials(count: int = 1):
    steps = tuple(GoalPlanStep(
        step_id=f"S{index}", objective=f"Inspect source {index}",
        phase="observe", stage=1, obligation_ids=("O1",),
        success_evidence=(f"Source {index} was observed",),
        read_roots=(f"source-{index}.txt",),
    ) for index in range(1, count + 1))
    patch = GoalPlanPatch(
        patch_id="GPP-fixture", base_revision=0, add_steps=steps,
        replace_steps=(), discard_step_ids=(), reason="Inspect requested sources",
        goal_obligations=(GoalObligation(
            obligation_id="O1", predicate="All requested sources are inspected",
            required_phases=("observe",),
        ),),
    )
    request = GoalPlanRequest(
        run_id="RUN-native-supervisor", immutable_request="Inspect the requested sources.",
        goal_digest="fixture-goal-digest", plan_revision=0,
        active_plan=RollingGoalPlan(goal_digest="fixture-goal-digest").to_model_dict(),
        latest_audit=None, workspace_manifest={},
    )
    # Derive the model-owned fields from the sole production serializer.
    value = patch.to_dict()
    for key in ("schema_version", "patch_id", "base_revision"):
        value.pop(key)
    for stage in value["add_stages"]:
        for step in stage["steps"]:
            step.pop("allowed_operations")
    return request, patch, value


def _review_materials():
    _, patch, _ = _plan_materials(19)
    projected = []
    for index, step in enumerate(patch.add_steps, start=1):
        item = step.to_dict()
        item.pop("stage")
        item["step_revision"] = 2 if index == 19 else 1
        item["accepted_evidence_refs"] = [f"A{index:05d}"]
        projected.append(item)
    request = GoalStageReviewRequest(
        run_id="RUN-native-stage", immutable_request="Inspect the requested sources.",
        goal_digest="fixture-goal-digest", stage=1,
        stage_steps=tuple(projected), workspace_manifest={},
    )
    review = GoalStageReview(
        review_id="GSR-fixture", stage=1, verdict=GoalStageReviewVerdict.ADVANCE,
        reviewed_step_ids=tuple(step.step_id for step in patch.add_steps),
        evidence_refs=tuple(f"A{index:05d}" for index in range(1, 20)),
        gaps=(), reason="The supplied stage evidence is coherent",
    )
    value = review.to_dict()
    for key in tuple(value):
        if key not in {"verdict", "gaps", "reason"}:
            value.pop(key)
    return request, review, value


class _Response:
    status_code = 200

    def __init__(self, payload):
        self.payload = payload

    def json(self):
        return deepcopy(self.payload)


class _Session:
    trust_env = False

    def __init__(self, payload):
        self.payload = payload
        self.posts = []

    def post(self, url, **kwargs):
        self.posts.append({"url": url, **kwargs})
        return _Response(self.payload)


def _response(value, *, text=None, finish_reason="stop"):
    return {
        "model": "fixture-planner-13b",
        "choices": [{
            "index": 0,
            "text": text if text is not None else ">fixture reasoning</think>\n" + json.dumps(value),
            "finish_reason": finish_reason,
            "token_ids": [10, 11, 12],
        }],
        "prompt_token_ids": [0, 1, 2],
        "usage": {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
    }


def _assert_native_payload(body, *, model, prompt, max_tokens):
    expected = TextCompletionRequest(
        prompt=prompt, max_tokens=max_tokens, temperature=0.1,
        top_p=1.0, top_k=0, presence_penalty=0.0, frequency_penalty=0.0,
        penalty_decay=0.996, stop=("✿",), stop_token_ids=(0,),
        add_special_tokens=True, return_token_ids=True,
    ).payload(model, sampler_mode="native")
    expected["vllm_xargs"] = {
        "rwkv_state_profile": "zero", "rwkv_state_profile_sha256": "0" * 64,
    }
    assert body == expected


def test_supervisor_defaults_expand_planner_only_and_public_config_is_safe():
    settings = _settings()
    assert settings.backend_profile == "openai-compatible"
    assert settings.max_plan_tokens == 8192
    assert settings.read_timeout_seconds == 240.0
    assert (settings.max_review_tokens, settings.max_directive_tokens,
            settings.max_contract_plan_tokens, settings.max_contract_review_tokens) == (
        1400, 1200, 4000, 2400,
    )
    public = settings.public_dict()
    assert public["backend_profile"] == settings.backend_profile
    assert public["max_plan_tokens"] == 8192
    assert public["read_timeout_seconds"] == 240.0
    assert public["api_key_configured"] is True
    assert "api_key" not in public
    assert settings.api_key not in json.dumps(public)


@pytest.mark.parametrize("mode", ["defaults", "canonical", "matching_aliases", "conflicting_aliases"])
def test_supervisor_native_env_loading_and_alias_conflicts(tmp_path, monkeypatch, mode):
    for key in tuple(os.environ):
        if key.startswith(("RWKV_LH_PLANNER_", "RWKV_LH_STAGE_CHECKER_", "SUPERVISOR_")):
            monkeypatch.delenv(key)
    lines = [
        "RWKV_LH_PLANNER_BASE_URL=http://supervisor.invalid/v1",
        "RWKV_LH_PLANNER_API_KEY=fixture-env-secret",
        "RWKV_LH_PLANNER_MODEL=fixture-local-13b",
        "RWKV_LH_PLANNER_BACKEND_PROFILE=vllm-rwkv-native",
        "RWKV_LH_EXECUTOR_STATE_PROFILE_ID=must-not-load",
    ]
    if mode != "defaults":
        lines.extend(("RWKV_LH_PLANNER_MAX_PLAN_TOKENS=9000", "RWKV_LH_PLANNER_READ_TIMEOUT=300"))
    if mode in {"matching_aliases", "conflicting_aliases"}:
        lines.append("SUPERVISOR_MAX_PLAN_TOKENS=" + ("9000" if mode == "matching_aliases" else "1800"))
        lines.append("SUPERVISOR_READ_TIMEOUT=300")
    monkeypatch.delenv("RWKV_LH_EXECUTOR_STATE_PROFILE_ID", raising=False)
    path = tmp_path / "supervisor-fixture.env"
    path.write_text("\n".join(lines), encoding="utf-8")
    if mode == "conflicting_aliases":
        with pytest.raises(ValueError, match="conflicting role settings"):
            SupervisorAPISettings.from_env(path)
        return
    loaded = SupervisorAPISettings.from_env(path)
    assert loaded.backend_profile == "vllm-rwkv-native"
    assert loaded.max_plan_tokens == (8192 if mode == "defaults" else 9000)
    assert loaded.read_timeout_seconds == (240 if mode == "defaults" else 300)
    assert loaded.stage_checker_model == loaded.model
    assert "RWKV_LH_EXECUTOR_STATE_PROFILE_ID" not in os.environ
    assert "fixture-env-secret" not in json.dumps(loaded.public_dict())


def test_supervisor_unknown_backend_profile_is_rejected():
    with pytest.raises(ValueError, match="backend_profile|BACKEND_PROFILE"):
        _settings(backend_profile="guess-from-model-name").validate()


@pytest.mark.parametrize("phase", ["goal_plan", "goal_stage_review"])
def test_native_wire_has_exact_prompt_sampling_and_zero_identity(phase, monkeypatch):
    for role in ("EXECUTOR", "AUDITOR_STEP", "FINALIZER", "AUDITOR_FINAL"):
        monkeypatch.setenv(f"RWKV_LH_{role}_STATE_PROFILE_ID", "foreign-candidate")
        monkeypatch.setenv(f"RWKV_LH_{role}_STATE_PROFILE_SHA256", "f" * 64)
    request, _, _ = _plan_materials()
    payload_text = _render_user_payload(request.to_dict())
    system_prompt = "Fixture system instruction, including Unicode 中文."
    client = OpenAICompatibleSupervisorClient(_native_settings(), session=_Session({}))
    with sampling_parameters(1.8, seed=123, request_id="foreign-executor",
                             top_p=0.4, top_k=9, presence_penalty=1,
                             frequency_penalty=1, penalty_decay=0.1):
        endpoint, body, _ = client._wire_request(
            phase=phase, selected_model="fixture-selected-model",
            system_prompt=system_prompt, payload_text=payload_text, max_tokens=8192,
            schema_revision="fixture", schema=client._goal_plan_patch_schema(),
        )
    assert endpoint == "http://supervisor.invalid/v1/completions"
    _assert_native_payload(
        body, model="fixture-selected-model", max_tokens=8192,
        prompt=f"System✿{system_prompt}✿\nUser✿{payload_text}✿\nBot✿<think",
    )


def test_native_backend_does_not_change_non_goal_wire():
    client = OpenAICompatibleSupervisorClient(_native_settings(), session=_Session({}))
    request, _, _ = _plan_materials()
    endpoint, body, transport = client._wire_request(
        phase="plan", selected_model="fixture-legacy-supervisor",
        system_prompt="Fixture", payload_text=_render_user_payload(request.to_dict()),
        max_tokens=8192, schema_revision="fixture", schema=client._goal_plan_patch_schema(),
    )
    assert endpoint.endswith("/chat/completions")
    assert transport == "chat_completions"
    assert "messages" in body
    assert "prompt" not in body
    assert "vllm_xargs" not in body


@pytest.mark.parametrize("phase", ["goal_plan", "goal_stage_review"])
def test_native_goal_roles_preserve_canonical_contract_and_audit_raw_output(phase):
    request, expected, value = _plan_materials(19) if phase == "goal_plan" else _review_materials()
    payload = _response(value)
    session = _Session(payload)
    audit = []
    settings = _native_settings()
    client = OpenAICompatibleSupervisorClient(settings, session=session, audit_hook=audit.append)
    result = client.plan_goal_patch(request) if phase == "goal_plan" else client.review_goal_stage(request)
    if phase == "goal_plan":
        assert result.add_steps == expected.add_steps
        assert result.goal_obligations == expected.goal_obligations
        assert result.base_revision == request.plan_revision
    else:
        assert result.verdict == expected.verdict
        assert result.reviewed_step_ids == expected.reviewed_step_ids
        assert result.evidence_refs == expected.evidence_refs
    assert len(session.posts) == 1
    posted = session.posts[0]
    assert posted["url"].endswith("/completions")
    assert posted["timeout"] == (10.0, 240.0)
    body = posted["json"]
    expected_model = settings.model if phase == "goal_plan" else settings.stage_checker_model
    expected_budget = 8192 if phase == "goal_plan" else 2400
    tail = "✿\nUser✿" + _render_user_payload(request.to_dict()) + "✿\nBot✿<think"
    assert body["prompt"].startswith("System✿")
    assert body["prompt"].endswith(tail)
    _assert_native_payload(body, model=expected_model, prompt=body["prompt"], max_tokens=expected_budget)
    started = next(item for item in audit if item["type"] == "supervisor_request_started")
    returned = next(item for item in audit if item["type"] == "supervisor_request_returned")
    raw = payload["choices"][0]["text"]
    assert started["prompt_sha256"] == hashlib.sha256(body["prompt"].encode()).hexdigest()
    assert started["prefill_sha256"] == hashlib.sha256(b"<think").hexdigest()
    assert returned["raw_output"] == raw
    assert returned["raw_output_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert returned["output_sha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert returned["raw_token_ids"] == payload["choices"][0]["token_ids"]
    assert returned["prompt_token_ids"] == payload["prompt_token_ids"]
    assert settings.api_key not in json.dumps(audit)


@pytest.mark.parametrize("finish_reason", ["length", "content_filter", "", None, "unexpected"])
def test_native_rejects_non_stop_even_with_complete_json(finish_reason):
    request, _, value = _plan_materials()
    session = _Session(_response(value, finish_reason=finish_reason))
    client = OpenAICompatibleSupervisorClient(_native_settings(), session=session)
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)
    assert len(session.posts) == 1


@pytest.mark.parametrize("fault", [
    "bare_json", "full_think_prefix", "unclosed_think", "leading_space", "leading_prose",
    "trailing_prose", "second_json", "truncated_json", "non_object", "missing_choices",
    "empty_choices", "multiple_choices", "missing_text", "wrong_text_type", "empty_text",
])
def test_native_rejects_malformed_completion_boundary(fault):
    request, _, value = _plan_materials()
    payload = _response(value)
    choice = payload["choices"][0]
    valid_json = json.dumps(value)
    texts = {
        "bare_json": valid_json,
        "full_think_prefix": "<think>reasoning</think>" + valid_json,
        "unclosed_think": ">reasoning" + valid_json,
        "leading_space": " " + choice["text"],
        "leading_prose": "prose" + choice["text"],
        "trailing_prose": choice["text"] + " trailing prose",
        "second_json": choice["text"] + valid_json,
        "truncated_json": ">reasoning</think>" + valid_json[:-1],
        "non_object": ">reasoning</think>[]",
        "wrong_text_type": [choice["text"]],
        "empty_text": "",
    }
    if fault in texts:
        choice["text"] = texts[fault]
    elif fault == "missing_choices":
        payload.pop("choices")
    elif fault == "empty_choices":
        payload["choices"] = []
    elif fault == "multiple_choices":
        payload["choices"].append(deepcopy(choice))
    elif fault == "missing_text":
        choice.pop("text")
    client = OpenAICompatibleSupervisorClient(_native_settings(), session=_Session(payload))
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)


@pytest.mark.parametrize("location", ["prompt", "output"])
@pytest.mark.parametrize("bad_tokens", [[True], [-1], ["12"], "12"])
def test_native_rejects_malformed_returned_token_ids(location, bad_tokens):
    request, _, value = _plan_materials()
    payload = _response(value)
    if location == "prompt":
        payload["prompt_token_ids"] = bad_tokens
    else:
        payload["choices"][0]["token_ids"] = bad_tokens
    client = OpenAICompatibleSupervisorClient(_native_settings(), session=_Session(payload))
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)


@pytest.mark.parametrize("missing", [False, True])
def test_native_missing_token_ids_remain_unavailable_without_rejecting_json(missing):
    request, expected, value = _plan_materials()
    payload = _response(value)
    if missing:
        payload.pop("prompt_token_ids")
        payload["choices"][0].pop("token_ids")
    else:
        payload["prompt_token_ids"] = None
        payload["choices"][0]["token_ids"] = None
    audit = []
    client = OpenAICompatibleSupervisorClient(
        _native_settings(), session=_Session(payload), audit_hook=audit.append,
    )
    assert client.plan_goal_patch(request).add_steps == expected.add_steps
    returned = next(item for item in audit if item["type"] == "supervisor_request_returned")
    assert returned.get("raw_token_ids") in (None, [])
    assert returned.get("prompt_token_ids") in (None, [])
    assert returned.get("raw_token_ids_available") is not True
    assert returned.get("prompt_token_ids_available") is not True


def test_native_transport_does_not_repair_invalid_goal_phase():
    request, _, value = _plan_materials()
    value["add_stages"][0]["steps"][0]["phase"] = "public-source observe"
    client = OpenAICompatibleSupervisorClient(
        _native_settings(), session=_Session(_response(value)),
    )
    with pytest.raises(ValueError, match="phase"):
        client.plan_goal_patch(request)


@pytest.mark.parametrize("difference", ["transport", "endpoint", "plan_budget", "review_budget"])
def test_native_cache_identity_changes_with_actual_transport_configuration(tmp_path, difference):
    settings = _native_settings(plan_cache_enabled=True, plan_cache_dir=str(tmp_path))
    changed = {
        "transport": replace(settings, backend_profile="openai-compatible"),
        "endpoint": replace(settings, base_url="http://other.invalid/v1"),
        "plan_budget": replace(settings, max_plan_tokens=4096),
        "review_budget": replace(settings, max_contract_review_tokens=4096),
    }[difference]
    phase = "goal_stage_review" if difference == "review_budget" else "goal_plan"
    request, _, _ = _review_materials() if phase == "goal_stage_review" else _plan_materials()
    paths = []
    for selected in (settings, changed):
        client = OpenAICompatibleSupervisorClient(selected, session=_Session({}))
        paths.append(client._validated_response_cache_path(
            phase=phase, cache_schema="fixture-cache", request_payload=request.to_dict(),
            system_prompt="Same system instruction",
            schema=client._goal_stage_review_schema() if phase == "goal_stage_review" else client._goal_plan_patch_schema(),
        ))
    assert paths[0] != paths[1]


@pytest.mark.parametrize("bad_count", ["invalid", {"bad": "value"}, float("inf")])
def test_native_bad_usage_stays_transport_protocol_error_with_raw_evidence(bad_count):
    request, _, value = _plan_materials()
    payload = _response(value)
    payload["usage"]["prompt_tokens"] = bad_count
    events = []
    session = _Session(payload)
    client = OpenAICompatibleSupervisorClient(
        _native_settings(), session=session, audit_hook=events.append,
    )
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)
    raw = next(event for event in events if event["type"] == "supervisor_raw_response_returned")
    assert raw["attempt"] == 1
    assert raw["raw_response"] == payload
    assert len(session.posts) == 1


def test_native_rejected_token_ids_remain_in_raw_response_evidence():
    request, _, value = _plan_materials()
    payload = _response(value)
    payload["choices"][0]["token_ids"] = [True]
    events = []
    client = OpenAICompatibleSupervisorClient(
        _native_settings(), session=_Session(payload), audit_hook=events.append,
    )
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)
    raw = next(event for event in events if event["type"] == "supervisor_raw_response_returned")
    assert raw["attempt"] == 1
    assert raw["raw_response"] == payload


@pytest.mark.parametrize("usage", [["bad"], 42, []])
def test_native_non_object_usage_is_a_protocol_error(usage):
    request, _, value = _plan_materials()
    payload = _response(value)
    payload["usage"] = usage
    events = []
    client = OpenAICompatibleSupervisorClient(
        _native_settings(), session=_Session(payload), audit_hook=events.append,
    )
    with pytest.raises(SupervisorProtocolError):
        client.plan_goal_patch(request)
    raw = next(event for event in events if event["type"] == "supervisor_raw_response_returned")
    assert raw["raw_response"] == payload
