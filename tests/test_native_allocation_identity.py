"""Identical task text must not reopen a retired bootstrap allocation."""

import asyncio

from rwkv_lh.runtime.native_request_protocol import prepare_native_request
from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.model_session import NativeRWKVModelSession
from rwkv_lh.model_io import FINAL_ANSWER_DEFINITION
from rwkv_lh.schema import ModelLaneKind
from test_model_session import FakeNativeStateClient, settings as session_settings
from test_openai_compat_runtime import _cache_binding, settings
from test_native_state_service import service_module as service_module
from test_native_state_lifecycle import disk_service, release_request
from test_native_state_service_recovery import prepared


def capturing_client(monkeypatch):
    client = OpenAICompatibleRWKVClient(settings())
    requests = []

    def request(operation, payload):
        prepared = prepare_native_request(operation, payload)
        requests.append(prepared)
        return prepared

    monkeypatch.setattr(client, "_native_request", request)
    monkeypatch.setattr(client, "_native_snapshot", lambda data, **kwargs: data)
    return client, requests


def test_independent_identical_creates_allocate_distinct_request_ids(monkeypatch):
    client, requests = capturing_client(monkeypatch)
    binding = _cache_binding()
    for _ in range(2):
        client.state_create(lane_id=binding.lane_id, text="same task", cache_binding=binding)
    assert requests[0]["request_id"] != requests[1]["request_id"]
    assert requests[0]["cache_binding"] == requests[1]["cache_binding"]


def test_explicit_allocation_retry_preserves_request_identity(monkeypatch):
    client, requests = capturing_client(monkeypatch)
    binding = _cache_binding()
    for _ in range(2):
        client.state_create(lane_id=binding.lane_id, text="same task", cache_binding=binding,
                            request_id="CREATE-CP-persistent")
    assert requests[0] == requests[1]
    assert requests[0]["request_id"] == "CREATE-CP-persistent"


def test_bootstrap_allocations_use_distinct_persistent_checkpoint_ids():
    class Client(FakeNativeStateClient):
        def state_create(self, *, lane_id, text, cache_binding, request_id=None):
            self.ids.append(request_id)
            return self._snapshot(text, cache_binding)

    client = Client([])
    client.ids = []
    session = NativeRWKVModelSession(client, settings=session_settings())
    definitions = [FINAL_ANSWER_DEFINITION]
    first = session.bootstrap(ModelLaneKind.ACTION, "same task", definitions, lane_id="LANE:ACTION")
    second = session.bootstrap(ModelLaneKind.ACTION, "same task", definitions, lane_id="LANE:ACTION")
    assert first.transcript == second.transcript
    assert client.ids == [f"CREATE-{first.checkpoint_id}", f"CREATE-{second.checkpoint_id}"]
    assert client.ids[0] != client.ids[1]


def test_prepared_checkpoint_recovery_reuses_its_allocation_id():
    class Client(FakeNativeStateClient):
        def state_create(self, *, lane_id, text, cache_binding, request_id=None):
            self.ids.append(request_id)
            return self._snapshot(text, cache_binding)

    client = Client([])
    client.ids = []
    session = NativeRWKVModelSession(client, settings=session_settings())
    checkpoint = session.prepare_bootstrap(
        ModelLaneKind.ACTION, "same task", [FINAL_ANSWER_DEFINITION], lane_id="LANE:ACTION")
    import copy
    persisted = copy.deepcopy(checkpoint.to_dict())
    session.materialize_input(checkpoint, {checkpoint.checkpoint_id: checkpoint})
    recovered_session = NativeRWKVModelSession(client, settings=session_settings())
    recovered = recovered_session.import_checkpoint(persisted)
    recovered_session.materialize_input(recovered, {recovered.checkpoint_id: recovered})
    assert client.ids == [f"CREATE-{checkpoint.checkpoint_id}"] * 2


def test_fresh_identical_allocation_generates_after_retirement_and_restart(
    monkeypatch, tmp_path, service_module,
):
    client, requests = capturing_client(monkeypatch)
    binding = _cache_binding()
    for _ in range(2):
        client.state_create(lane_id=binding.lane_id, text="same task", cache_binding=binding)

    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        original = await service.dispatch("create", requests[0])
        await service.dispatch("release", release_request(original))
        assert not list(root.glob("*.pt"))
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        # Historical receipts remain immutable; a new allocation has a new ID.
        assert await reopened.dispatch("create", requests[0]) == original
        fresh = await reopened.dispatch("create", requests[1])
        assert fresh["state_ref"] != original["state_ref"]
        assert fresh["state_digest"] == original["state_digest"]
        generated = await reopened.dispatch("generate", prepared(
            "generate", parent_state_ref=fresh["state_ref"],
            parent_cache_binding_digest=binding.digest, request_id="R-fresh-generation",
            max_tokens=32, stop=[], sampling={},
        ))
        assert generated["candidate"]["state_ref"] != fresh["state_ref"]
        assert counters["sample"] == 1

    asyncio.run(scenario())
