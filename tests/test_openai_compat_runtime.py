import json

import pytest
import requests

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.protocol import RWKVOutcomeUnknownError, RWKVProtocolError
from rwkv_lh.runtime.sampling import (
    get_request_seed,
    get_request_temperature,
    sampling_parameters,
)
from rwkv_lh.runtime.settings import RuntimeSettings


class FakeResponse:
    def __init__(self, payload, status_code=200, headers=None):
        self.content = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.status_code = status_code
        self.headers = headers or {}
        self.text = self.content.decode("utf-8")


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.trust_env = True

    def request(self, method, endpoint, **kwargs):
        self.calls.append((method, endpoint, kwargs))
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item

    def close(self):
        return None


def settings(**overrides):
    values = {
        "base_url": "http://127.0.0.1:29613/v1",
        "api_key": "test-key",
        "model": "rwkv-test",
        "connect_timeout_seconds": 1.0,
        "read_timeout_seconds": 2.0,
        "retry_attempts": 2,
        "retry_backoff_seconds": 0.0,
        "default_temperature": 0.1,
        "trust_environment_proxies": False,
        "verify_tls": True,
    }
    values.update(overrides)
    return RuntimeSettings(**values)


def test_request_level_rapid_sampling_profile_reaches_wire(monkeypatch):
    fake = FakeSession(
        [
            FakeResponse(
                {
                    "id": "cmpl-1",
                    "model": "rwkv-test",
                    "choices": [{"text": "完成", "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 2},
                }
            )
        ]
    )
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())

    with sampling_parameters(0.36, request_id="MR-test-wire"):
        response = client.text_completion(
            "规划",
            max_tokens=20,
            min_tokens=3,
            stop=["### User"],
            stop_token_ids=[123],
        )

    payload = fake.calls[0][2]["json"]
    assert payload == {
        "model": "rwkv-test",
        "prompt": "规划",
        "max_tokens": 20,
        "temperature": 0.36,
        "top_p": 1.0,
        "top_k": 0,
        "presence_penalty": 0.0,
        "frequency_penalty": 0.0,
        "penalty_decay": 0.996,
        "min_tokens": 3,
        "add_special_tokens": True,
        "stream": False,
        "stop": ["### User"],
        "stop_token_ids": [123],
        "request_id": "MR-test-wire",
    }
    assert response.content == "完成"
    assert response.usage == {
        "prompt_tokens": 3,
        "completion_tokens": 2,
        "total_tokens": 5,
    }
    assert get_request_seed() is None
    assert get_request_temperature() == 0.1


def test_seed_is_rejected_before_a_request_is_sent(monkeypatch):
    fake = FakeSession([])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(ValueError, match="seed is unsupported"):
        client.text_completion("no seed", seed=77)
    assert fake.calls == []


def test_runtime_context_budget_reserves_output_bos_and_margin():
    runtime = settings(
        max_model_len=100,
        context_safety_margin=10,
        bos_token_count=1,
    )
    assert runtime.max_prompt_tokens(20) == 69


def test_rapid_sampler_rejects_greedy_temperature_locally():
    with pytest.raises(ValueError, match="between 1e-5 and 2"):
        with sampling_parameters(0.0):
            pass


def test_connect_timeout_is_retried(monkeypatch):
    fake = FakeSession(
        [
            requests.ConnectTimeout("first connect timeout"),
            FakeResponse({"choices": [{"text": "ok", "finish_reason": "stop"}]}),
        ]
    )
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    assert client.text_completion("retry").content == "ok"
    assert len(fake.calls) == 2


def test_generation_read_timeout_is_unknown_and_not_retried(monkeypatch):
    fake = FakeSession(
        [
            requests.ReadTimeout("response lost"),
            FakeResponse({"choices": [{"text": "must not be requested"}]}),
        ]
    )
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(RWKVOutcomeUnknownError):
        client.text_completion("unknown outcome")
    assert len(fake.calls) == 1


def test_malformed_completion_is_protocol_error(monkeypatch):
    fake = FakeSession([FakeResponse({"choices": []})])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(RWKVProtocolError):
        client.text_completion("invalid")
