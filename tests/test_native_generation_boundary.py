"""Stop-output identity owns the published State, independently of worker timing."""
import asyncio
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from test_native_state_service import service_module
from test_native_state_service_recovery import prepared, service_fixture
from test_openai_compat_runtime import _cache_binding
from rwkv_lh.runtime.native_request_recovery import native_request_digest


@pytest.mark.parametrize("overshoot", [-1, 0, 1, 2, 5])
@pytest.mark.parametrize("restart", [False, True])
def test_published_generation_uses_returned_boundary_through_retry_and_restart(
    tmp_path, service_module, overshoot, restart,
):
    async def scenario():
        path = tmp_path / "requests.sqlite3"
        exports, counters = {}, {}
        service = service_fixture(service_module, path, exports, counters, sample_overshoot=overshoot)
        binding = _cache_binding()
        initial = await service.dispatch("create", prepared("create", delta="ab", cache_binding=binding.to_dict()))
        current = initial
        expected = list(b"ab")
        for attempt in range(2):
            request = prepared("generate", parent_state_ref=current["state_ref"],
                parent_cache_binding_digest=binding.digest, request_id=f"generation-{attempt}",
                max_tokens=16, stop=["```"], sampling={}, return_token_ids=True)
            response = await service.dispatch("generate", request)
            candidate = response["candidate"]
            assert candidate["content"] == "original"
            assert candidate["finish_reason"] == "stop"
            assert candidate["metadata"]["prompt_token_ids"] == expected
            assert candidate["metadata"]["token_ids"] == [4, 5, 7]
            expected.extend([4, 5, 7])
            state = service._record(candidate["state_ref"])
            assert state.input_token_ids == expected
            assert state.processed_token_count + 1 == len(expected)
            assert service.worker_states[state.state_ref]["consumed_token_ids"] == expected[:-1]
            assert state.pending_token_id == expected[-1]
            # Only the logical root/committed States and the published candidate remain.
            assert set(service.worker_states) == set(service.records)
            if attempt == 1:
                await service.dispatch("rollback", prepared("rollback", candidate_state_ref=state.state_ref,
                    parent_state_ref=current["state_ref"]))
                assert state.state_ref not in service.worker_states
                break
            binding = replace(binding, parent_state_digest=current["state_digest"], state_chain_digest="d" * 64)
            committed = await service.dispatch("commit", prepared("commit", candidate_state_ref=state.state_ref,
                cache_binding=binding.to_dict()))
            if restart:
                service = service_fixture(service_module, path, exports, counters, sample_overshoot=overshoot)
            assert await service.dispatch("generate", request) == response
            assert counters["sample"] == 1
            binding = replace(binding, parent_state_digest=committed["state_digest"], delta_digest="e" * 64)
            current = await service.dispatch("append", prepared("append", parent_state_ref=committed["state_ref"],
                delta="rejected arguments; retry", cache_binding=binding.to_dict()))
            expected.extend(b"rejected arguments; retry")
        assert counters["sample"] == 2
    asyncio.run(scenario())


@pytest.mark.parametrize("finish_reason", [None, "", 42])
def test_native_does_not_invent_a_stop_reason(finish_reason, service_module):
    async def scenario():
        service = service_module.RWKVNativeStateService(None, SimpleNamespace())
        source = service_module._StateRecord("source", "a" * 64, "b" * 64, "zero", "0" * 64, 1, 1)
        target = replace(source, state_ref="target")
        async def generate(*args):
            yield SimpleNamespace(outputs=[SimpleNamespace(token_ids=[7], text="output", finish_reason=finish_reason)])
        async def ensure_loaded(record):
            pass
        async def collective(action, payload):
            return [{**asdict(replace(target, pending_token_id=7, processed_token_count=2)), "authoritative": False}]
        service.engine_client = SimpleNamespace(generate=generate)
        service._ensure_loaded = ensure_loaded
        service._collective = collective
        with pytest.raises(RuntimeError, match="finish reason"):
            await service._generate_tokens(source=source, target=target, prompt_token_ids=[1], request_id="missing-stop",
                max_tokens=3, stop=[], sampling={}, pending_token_id=None)
    asyncio.run(scenario())


def test_failed_candidate_materialization_is_not_published_or_sampled_again(tmp_path, service_module):
    async def scenario():
        exports, counters = {}, {}
        service = service_fixture(service_module, tmp_path / "requests.sqlite3", exports, counters, sample_overshoot=2)
        binding = _cache_binding()
        initial = await service.dispatch("create", prepared("create", delta="a", cache_binding=binding.to_dict()))
        async def failed_materialization(source, target, tokens):
            raise RuntimeError("injected candidate materialization failure")
        service._materialize_delta = failed_materialization
        request = prepared("generate", parent_state_ref=initial["state_ref"],
            parent_cache_binding_digest=binding.digest, request_id="generation-failed-materialization",
            max_tokens=16, stop=["```"], sampling={})
        with pytest.raises(RuntimeError, match="candidate materialization failure"):
            await service.dispatch("generate", request)
        assert set(service.records) == set(service.worker_states) == {initial["state_ref"]}
        assert len(exports) == 1
        receipt = await service.request_result(request["request_id"], native_request_digest("generate", request))
        assert receipt["status"] == "unknown"
        with pytest.raises(service_module.HTTPException):
            await service.dispatch("generate", request)
        assert counters["sample"] == 1
    asyncio.run(scenario())
