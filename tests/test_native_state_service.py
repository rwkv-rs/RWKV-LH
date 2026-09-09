"""Native prefill preserves the original token stream across engine requests."""

import asyncio
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest


@pytest.fixture
def service_module(monkeypatch):
    modules = {}
    for name in ("vllm", "vllm.engine", "vllm.engine.protocol", "vllm.sampling_params",
                 "fastapi", "starlette", "starlette.datastructures", "starlette.responses"):
        modules[name] = ModuleType(name)
        monkeypatch.setitem(sys.modules, name, modules[name])
    modules["vllm"].__version__ = "mechanism-engine"
    modules["vllm"].TokensPrompt = dict
    modules["vllm.engine.protocol"].EngineClient = object
    modules["vllm.sampling_params"].SamplingParams = SimpleNamespace
    modules["vllm.sampling_params"].RequestOutputKind = SimpleNamespace(FINAL_ONLY="final")
    class HTTPException(Exception):
        def __init__(self, status_code, detail):
            self.status_code, self.detail = status_code, detail
            super().__init__(detail)
    modules["fastapi"].FastAPI = object
    modules["fastapi"].Request = object
    modules["fastapi"].HTTPException = HTTPException
    modules["starlette.datastructures"].State = SimpleNamespace
    modules["starlette.responses"].JSONResponse = SimpleNamespace
    path = Path(__file__).parents[1] / "rwkv_lh/inference/native_state_service.py"
    spec = importlib.util.spec_from_file_location("mechanism_native_service", path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, spec.name, module)
    spec.loader.exec_module(module)
    return module


def make_service(module, *, fail_at=None):
    class Service(module.RWKVNativeStateService):
        def __init__(self):
            super().__init__(SimpleNamespace(model_config=SimpleNamespace(max_model_len=9)), SimpleNamespace())
            self.generated = []
            self.worker_states = {"source": ([10, 11], 12)}
            self.dropped = []

        async def _generate_tokens(self, **kwargs):
            self.generated.append(kwargs)
            assert len(kwargs["prompt_token_ids"]) + kwargs["max_tokens"] <= 9
            if len(self.generated) == fail_at:
                raise RuntimeError("mechanism engine failure")
            source, target = kwargs["source"], kwargs["target"]
            previous, pending = self.worker_states[source.state_ref]
            assert kwargs["prompt_token_ids"][0] == pending
            self.worker_states[target.state_ref] = (
                previous + kwargs["prompt_token_ids"], kwargs["pending_token_id"])
            return "", [999], "length"

        async def _collective(self, action, payload=None):
            ref = payload["state_ref"]
            if action == "drop":
                self.dropped.append(ref)
                self.worker_states.pop(ref, None)
                return [{}]
            assert action == "get"
            consumed, pending = self.worker_states[ref]
            return [{"processed_token_count": len(consumed), "pending_token_id": pending}]

        async def _clone(self, source, target):
            self.worker_states[target.state_ref] = self.worker_states[source.state_ref]

    service = Service()
    source = module._StateRecord("source", "a" * 64, "b" * 64, "zero", "0" * 64, 12, 2)
    target = module.replace(source, state_ref="target", state_digest="c" * 64,
                            cache_binding_digest="d" * 64, parent_state_ref="source")
    return service, source, target


@pytest.mark.parametrize("count", [0, 1, 8, 9, 16, 25])
def test_prefill_consumes_every_original_token_once_with_bounded_requests(service_module, count):
    service, source, target = make_service(service_module)
    tokens = list(range(100, 100 + count))
    result = asyncio.run(service._materialize_delta(source, target, tokens))
    expected = [10, 11, 12, *tokens]
    consumed, pending = service.worker_states["target"]
    assert [*consumed, pending] == expected
    assert result.state_ref == "target" and result.cache_binding_digest == target.cache_binding_digest
    assert result.parent_state_ref == "source"
    assert result.pending_token_id == expected[-1]
    assert result.processed_token_count == len(expected) - 1
    assert len(service.generated) == (count + 7) // 8
    assert service.worker_states["source"] == ([10, 11], 12)
    assert set(service.worker_states) == {"source", "target"}
    assert not service.records


def test_prefill_failure_does_not_publish_or_modify_parent(service_module):
    service, source, target = make_service(service_module, fail_at=2)
    with pytest.raises(RuntimeError, match="mechanism engine failure"):
        asyncio.run(service._materialize_delta(source, target, list(range(25))))
    assert service.worker_states == {"source": ([10, 11], 12)}
    assert not service.records


@pytest.mark.parametrize("field", ["pending_token_id", "processed_token_count"])
@pytest.mark.parametrize("corrupt_at", [1, 2, 4])
def test_prefill_rejects_inexact_worker_boundary(service_module, field, corrupt_at):
    service, source, target = make_service(service_module)
    original_collective = service._collective

    async def corrupt_boundary(action, payload=None):
        records = await original_collective(action, payload)
        if action == "get" and len(service.generated) == corrupt_at:
            records[0][field] += 1
        return records

    service._collective = corrupt_boundary
    with pytest.raises(RuntimeError, match="prefill boundary"):
        asyncio.run(service._materialize_delta(source, target, list(range(25))))
    assert service.worker_states == {"source": ([10, 11], 12)}
    assert not service.records
