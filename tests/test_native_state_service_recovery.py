"""The real Native lifecycle replays results without reverting newer State facts."""
import asyncio
from dataclasses import asdict, replace
from types import SimpleNamespace

import pytest

from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal, native_request_digest, prepare_native_request
from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION
from test_native_state_service import service_module
from test_openai_compat_runtime import _cache_binding


def service_fixture(module, path, exports, counters):
    class Service(module.RWKVNativeStateService):
        def __init__(self):
            super().__init__(SimpleNamespace(model_config=SimpleNamespace(max_model_len=16384)), SimpleNamespace())
            self.ready = True
            self.model_name = "rwkv-test"
            self.tokenizer_build = "fixture-tokenizer"
            self.journal = NativeRequestJournal(path)
            self.worker_states = {}

        def _tokens(self, text, *, initial):
            return list(text.encode("utf-8"))

        async def _generate_tokens(self, **kwargs):
            kind = "sample" if kwargs["pending_token_id"] is None else "prefill"
            counters[kind] = counters.get(kind, 0) + 1
            await self._ensure_loaded(kwargs["source"])
            pending = 7 if kwargs["pending_token_id"] is None else kwargs["pending_token_id"]
            record = replace(kwargs["target"], pending_token_id=pending,
                             processed_token_count=kwargs["source"].processed_token_count + len(kwargs["prompt_token_ids"])
                             + (2 if kind == "sample" else 0))
            self.worker_states[record.state_ref] = {**asdict(record), "authoritative": False}
            return "original", [4, 5, 7], "stop"

        async def _collective(self, action, payload=None):
            ref = payload.get("state_ref")
            if action == "seed":
                self.worker_states[ref] = {**payload, "processed_token_count": 0, "authoritative": False}
            elif action == "drop":
                counters["drop"] = counters.get("drop", 0) + 1
                self.worker_states.pop(ref, None)
                return [{}]
            elif action == "export":
                exports[payload["store_key"]] = dict(self.worker_states[ref])
            elif action == "delete_export":
                exports.pop(payload["store_key"], None)
                return [{"store_key": payload["store_key"], "deleted": True}]
            elif action == "import":
                self.worker_states[ref] = {**exports[payload["store_key"]], "state_ref": ref}
            elif action == "rebind":
                counters["rebind"] = counters.get("rebind", 0) + 1
                self.worker_states[ref]["cache_binding_digest"] = payload["new_cache_binding_digest"]
            elif action != "get":
                raise AssertionError(action)
            return [dict(self.worker_states[ref])]

    return Service()


def prepared(operation, **payload):
    return prepare_native_request(operation, {
        "schema_version": NATIVE_STATE_PROTOCOL_VERSION, "model": "rwkv-test", **payload,
    })


async def create_and_generate(service):
    binding = _cache_binding()
    initial = await service.dispatch("create", prepared("create", lane_id=binding.lane_id,
                                                       delta="a", cache_binding=binding.to_dict()))
    generate = prepared("generate", parent_state_ref=initial["state_ref"],
                        parent_cache_binding_digest=binding.digest, request_id="R-generation",
                        max_tokens=4090, stop=[], sampling={})
    candidate = await service.dispatch("generate", generate)
    return initial, candidate, generate


@pytest.mark.parametrize("final_operation", ["commit", "rollback"])
def test_restart_replays_generate_without_reverting_commit_or_rollback(tmp_path, service_module, final_operation):
    exports, counters = {}, {}
    path = tmp_path / "native-requests.sqlite3"

    async def scenario():
        service = service_fixture(service_module, path, exports, counters)
        initial, generated, request = await create_and_generate(service)
        candidate_ref = generated["candidate"]["state_ref"]
        assert service._record(candidate_ref).export_record is not None
        if final_operation == "commit":
            binding = replace(_cache_binding(), parent_state_digest=initial["state_digest"], state_chain_digest="e" * 64)
            final_request = prepared("commit", candidate_state_ref=candidate_ref, cache_binding=binding.to_dict())
        else:
            final_request = prepared("rollback", candidate_state_ref=candidate_ref, parent_state_ref=initial["state_ref"])
        final = await service.dispatch(final_operation, final_request)

        restarted = service_fixture(service_module, path, exports, counters)
        queried = await restarted.request_result(request["request_id"], native_request_digest("generate", request))
        assert queried["result"] == generated
        assert await restarted.dispatch("generate", request) == generated
        assert await restarted.dispatch(final_operation, final_request) == final
        assert counters["sample"] == 1
        if final_operation == "commit":
            assert counters["rebind"] == 1
            assert restarted._record(candidate_ref).committed is True
            assert restarted.worker_states[candidate_ref]["cache_binding_digest"] == binding.digest
        else:
            assert counters["drop"] == 1
            with pytest.raises(service_module.HTTPException) as failure:
                restarted._record(candidate_ref)
            assert failure.value.status_code == 410
            assert candidate_ref not in restarted.worker_states
    asyncio.run(scenario())


def test_service_rejects_conflicting_request_without_second_sample(tmp_path, service_module):
    counters = {}
    service = service_fixture(service_module, tmp_path / "requests.sqlite3", {}, counters)

    async def scenario():
        _, _, original = await create_and_generate(service)
        with pytest.raises(service_module.HTTPException) as failure:
            await service.dispatch("generate", {**original, "max_tokens": 32})
        assert failure.value.status_code == 409
        assert counters["sample"] == 1
    asyncio.run(scenario())


def test_unknown_commit_blocks_restoring_older_candidate(tmp_path, service_module):
    service = service_fixture(service_module, tmp_path / "requests.sqlite3", {}, {})

    async def scenario():
        initial, generated, request = await create_and_generate(service)
        candidate_ref = generated["candidate"]["state_ref"]
        binding = replace(_cache_binding(), parent_state_digest=initial["state_digest"], state_chain_digest="e" * 64)
        commit = prepared("commit", candidate_state_ref=candidate_ref, cache_binding=binding.to_dict())

        async def fail_export(record):
            raise RuntimeError("interrupted after worker rebind")

        service._export = fail_export
        with pytest.raises(RuntimeError, match="after worker rebind"):
            await service.dispatch("commit", commit)
        with pytest.raises(service_module.HTTPException) as failure:
            await service.request_result(request["request_id"], native_request_digest("generate", request))
        assert failure.value.status_code == 503
        assert service.worker_states[candidate_ref]["cache_binding_digest"] == binding.digest
    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ["append", "fork", "import"])
def test_remaining_state_operations_replay_after_restart(tmp_path, service_module, operation):
    path = tmp_path / "requests.sqlite3"
    exports, counters = {}, {}

    async def scenario():
        service = service_fixture(service_module, path, exports, counters)
        binding = _cache_binding()
        initial = await service.dispatch("create", prepared("create", lane_id=binding.lane_id,
                                                           delta="a", cache_binding=binding.to_dict()))
        if operation == "import":
            request = prepared(operation, cache_binding=binding.to_dict(), export_record=initial["export_record"])
        else:
            updated = replace(binding, state_chain_digest="e" * 64, parent_state_digest=initial["state_digest"])
            request = prepared(operation, parent_state_ref=initial["state_ref"], lane_id=binding.lane_id,
                               delta="bc", cache_binding=updated.to_dict())
        original = await service.dispatch(operation, request)
        before = dict(counters)
        restarted = service_fixture(service_module, path, exports, counters)
        assert await restarted.dispatch(operation, request) == original
        assert counters == before
        assert original["state_ref"] in restarted.worker_states
    asyncio.run(scenario())


def test_http_routes_use_journal_dispatch_and_identity_query(service_module):
    routes = {}

    class App:
        def get(self, path):
            return lambda function: routes.setdefault(("GET", path), function)

        def post(self, path):
            return lambda function: routes.setdefault(("POST", path), function)

    class Service:
        async def dispatch(self, operation, payload):
            return {"operation": operation, "payload": payload}

        async def request_result(self, request_id, request_digest):
            return {"request_id": request_id, "request_digest": request_digest}

    service_module.RWKVNativeStateEndpointPlugin().attach_router(App())
    raw_request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(rwkv_native_state=Service())))

    async def scenario():
        for operation in ("create", "append", "fork", "generate", "commit", "rollback", "import"):
            response = await routes["POST", "/v1/state/" + operation]({"fixture": True}, raw_request)
            assert response["operation"] == operation
        response = await routes["GET", "/v1/state/requests/{request_id}"]("R-1", "a" * 64, raw_request)
        assert response == {"request_id": "R-1", "request_digest": "a" * 64}
    asyncio.run(scenario())
