"""State retirement preserves receipts while bounding real disk snapshots."""
import asyncio
from dataclasses import replace
from pathlib import Path

import pytest

from rwkv_lh.runtime.native_request_recovery import native_request_digest
from rwkv_lh.runtime.native_state import NATIVE_STATE_LIFECYCLE_VERSION
from test_native_state_service import service_module as service_module
from test_native_state_service_recovery import create_and_generate, prepared, service_fixture
from test_openai_compat_runtime import _cache_binding


def disk_service(module, tmp_path, *, exports=None, counters=None):
    exports = {} if exports is None else exports
    counters = {} if counters is None else counters
    service = service_fixture(module, tmp_path / "requests.sqlite3", exports, counters)
    root = tmp_path / "blobs"
    root.mkdir(exist_ok=True)
    collective = service._collective

    async def action(operation, payload=None):
        if operation == "clone":
            source = service.worker_states[payload["source_ref"]]
            service.worker_states[payload["target_ref"]] = {
                **source, "state_ref": payload["target_ref"], "state_digest": payload["target_digest"],
                "cache_binding_digest": payload["target_cache_binding_digest"],
            }
            return [dict(service.worker_states[payload["target_ref"]])]
        if operation == "delete_export":
            key = payload["store_key"]
            (root / (key + ".pt")).unlink(missing_ok=True)
            exports.pop(key, None)
            counters["delete"] = counters.get("delete", 0) + 1
            return [{"store_key": key, "deleted": True, "worker_rank": 0}]
        result = await collective(operation, payload)
        if operation == "export":
            (root / (payload["store_key"] + ".pt")).write_bytes(b"new-mechanism-state")
        return result

    service._collective = action
    return service, exports, counters, root


def test_rollback_reclaims_candidate_disk_but_keeps_original_receipt(tmp_path, service_module):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        initial, generated, request = await create_and_generate(service)
        candidate = generated["candidate"]
        assert len(list(root.glob("*.pt"))) == 2
        rollback = prepared("rollback", candidate_state_ref=candidate["state_ref"],
                            parent_state_ref=initial["state_ref"])
        original = await service.dispatch("rollback", rollback)
        assert len(list(root.glob("*.pt"))) == 1
        assert not (root / (candidate["state_digest"] + ".pt")).exists()
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        assert (await reopened.request_result(request["request_id"],
                native_request_digest("generate", request)))["result"] == generated
        assert await reopened.dispatch("generate", request) == generated
        assert await reopened.dispatch("rollback", rollback) == original
        assert counters["sample"] == 1
        assert len(list(root.glob("*.pt"))) == 1
    asyncio.run(scenario())


def release_request(*snapshots, request_id=None, aliases=False):
    kwargs = {} if request_id is None else {"request_id": request_id}
    return prepared("release", lifecycle_protocol=NATIVE_STATE_LIFECYCLE_VERSION,
                    **({"release_import_aliases": True} if aliases else {}),
                    states=[{key: item[key] for key in ("state_ref", "state_digest", "cache_binding_digest")}
                            for item in snapshots], **kwargs)


async def initial_state(service):
    binding = _cache_binding()
    request = prepared("create", lane_id=binding.lane_id, delta="mechanism", cache_binding=binding.to_dict())
    return await service.dispatch("create", request), request


def test_release_keeps_original_ids_and_allows_verified_new_batch_replay(tmp_path, service_module):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        initial, create = await initial_state(service)
        release = release_request(initial)
        expected = {"released_state_refs": [initial["state_ref"]]}
        assert await service.dispatch("release", release) == expected
        assert not list(root.glob("*.pt"))
        restarted, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        assert await restarted.dispatch("release", release) == expected
        assert await restarted.dispatch("release", release_request(initial, request_id="R-new-batch")) == expected
        assert await restarted.dispatch("create", create) == initial
        assert (await restarted.request_result(create["request_id"],
                native_request_digest("create", create)))["result"] == initial
        assert not restarted.worker_states and not list(root.glob("*.pt"))
        bad = {**initial, "cache_binding_digest": "f" * 64}
        with pytest.raises(service_module.HTTPException) as failure:
            await restarted.dispatch("release", release_request(bad))
        assert failure.value.status_code == 409
        with pytest.raises(service_module.HTTPException) as failure:
            await restarted.dispatch("import", prepared("import", export_record=initial["export_record"],
                                      cache_binding=_cache_binding().to_dict()))
        assert failure.value.status_code == 410
        assert not list(root.glob("*.pt"))
    asyncio.run(scenario())


def test_release_protects_shared_blob_alias_and_its_cold_restore(tmp_path, service_module):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        first, _ = await initial_state(service)
        imported_request = prepared("import", export_record=first["export_record"],
                                    cache_binding=_cache_binding().to_dict())
        alias = await service.dispatch("import", imported_request)
        assert first["state_ref"] != alias["state_ref"]
        assert len(list(root.glob("*.pt"))) == 1
        await service.dispatch("release", release_request(first))
        assert len(list(root.glob("*.pt"))) == 1
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        assert await reopened.dispatch("import", imported_request) == alias
        assert alias["state_ref"] in reopened.worker_states
        await reopened.dispatch("release", release_request(alias))
        assert not list(root.glob("*.pt"))
        assert counters["delete"] == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("fault", ["digest", "unknown", "duplicate", "candidate", "protocol"])
def test_release_batch_rejects_before_any_retirement(tmp_path, service_module, fault):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        first, _ = await initial_state(service)
        second_binding = replace(_cache_binding(), state_chain_digest="e" * 64,
                                 parent_state_digest=first["state_digest"])
        second = await service.dispatch("append", prepared("append", parent_state_ref=first["state_ref"],
                              lane_id=second_binding.lane_id, delta="next", cache_binding=second_binding.to_dict()))
        request = release_request(first, second)
        if fault == "digest":
            request["states"][1]["state_digest"] = "f" * 64
        elif fault == "unknown":
            request["states"][1]["state_ref"] = "WKV-" + "f" * 32
        elif fault == "duplicate":
            request["states"][1] = dict(request["states"][0])
        elif fault == "protocol":
            request["lifecycle_protocol"] = "unsupported"
        else:
            generated = await service.dispatch("generate", prepared("generate", parent_state_ref=second["state_ref"],
                            parent_cache_binding_digest=second_binding.digest, request_id="R-live-candidate",
                            max_tokens=4090, stop=[], sampling={}))
            request["states"].append({**request["states"][1],
                                     "state_ref": generated["candidate"]["state_ref"],
                                     "state_digest": generated["candidate"]["state_digest"]})
        before = sorted(root.glob("*.pt"))
        with pytest.raises(service_module.HTTPException):
            await service.dispatch("release", request)
        assert sorted(root.glob("*.pt")) == before
        assert service._record(first["state_ref"]).committed
        assert service._record(second["state_ref"]).committed
    asyncio.run(scenario())


def test_parent_waits_for_live_candidate_terminal_operation(tmp_path, service_module):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        initial, generated, _ = await create_and_generate(service)
        with pytest.raises(service_module.HTTPException) as failure:
            await service.dispatch("release", release_request(initial))
        assert failure.value.status_code == 409
        assert len(list(root.glob("*.pt"))) == 2
        await service.dispatch("rollback", prepared("rollback", parent_state_ref=initial["state_ref"],
                                      candidate_state_ref=generated["candidate"]["state_ref"]))
        await service.dispatch("release", release_request(initial, request_id="R-after-settlement"))
        assert not list(root.glob("*.pt"))
    asyncio.run(scenario())


def test_candidate_export_cannot_bypass_commit_by_creating_import_alias(tmp_path, service_module):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        _, generated, _ = await create_and_generate(service)
        candidate = service._record(generated["candidate"]["state_ref"])
        with pytest.raises(service_module.HTTPException) as failure:
            await service.dispatch("import", prepared("import", export_record=candidate.export_record,
                cache_binding=_cache_binding().to_dict()))
        assert failure.value.status_code == 409
        assert not service._record(candidate.state_ref).committed
        assert len(list(root.glob("*.pt"))) == 2
    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ["append", "fork", "generate", "import"])
def test_unknown_input_pins_survive_restart_and_prevent_release(tmp_path, service_module, operation):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        initial, _ = await initial_state(service)
        if operation == "import":
            request = prepared("import", export_record=initial["export_record"], cache_binding=_cache_binding().to_dict())
        else:
            request = prepared(operation, parent_state_ref=initial["state_ref"], request_id="R-uncertain-"+operation)
        async def unknown():
            raise RuntimeError("mechanism interruption after durable claim")
        with pytest.raises(RuntimeError, match="mechanism interruption"):
            await service.journal.execute(operation, request, unknown, execution_lock=service.request_lock)
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        with pytest.raises(service_module.HTTPException) as failure:
            await reopened.dispatch("release", release_request(initial))
        assert failure.value.status_code == 503
        assert len(list(root.glob("*.pt"))) == 1
        assert reopened.journal.lookup(request["request_id"]).status == "unknown"
    asyncio.run(scenario())


def test_inflight_claim_protects_parent_before_execution_lock(tmp_path, service_module):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        initial, _ = await initial_state(service)
        request = prepared("append", parent_state_ref=initial["state_ref"], request_id="R-queued")
        await service.request_lock.acquire()
        queued = asyncio.create_task(service.journal.execute("append", request,
                    lambda: asyncio.sleep(0, result={"fixture": True}), execution_lock=service.request_lock))
        await asyncio.sleep(0)
        assert service.journal.lookup(request["request_id"]).status == "pending"
        with pytest.raises(service_module.HTTPException) as failure:
            await service.release(release_request(initial))
        assert failure.value.status_code == 503
        assert len(list(root.glob("*.pt"))) == 1
        service.request_lock.release()
        await queued
        await service.dispatch("release", release_request(initial))
        assert not list(root.glob("*.pt"))
    asyncio.run(scenario())


@pytest.mark.parametrize("point", ["before_unlink", "after_unlink", "before_queue_ack"])
def test_durable_gc_recovers_at_each_deletion_boundary(tmp_path, service_module, point):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        initial, create = await initial_state(service)
        original = service._collective
        async def crash(action, payload=None):
            if action == "delete_export":
                if point == "after_unlink":
                    await original(action, payload)
                raise OSError("mechanism power loss")
            return await original(action, payload)
        if point == "before_queue_ack":
            def fail_ack(_key):
                raise OSError("mechanism acknowledgement loss")
            service.journal.mark_blob_deleted = fail_ack
        else:
            service._collective = crash
        release = release_request(initial)
        expected = await service.dispatch("release", release)
        assert service.journal.lookup(release["request_id"]).status == "completed"
        assert service.journal.gc_pending_count() == 1
        assert service.gc_last_error == "OSError"
        assert len(list(root.glob("*.pt"))) == (1 if point == "before_unlink" else 0)
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        assert await reopened.dispatch("release", release) == expected
        assert await reopened.dispatch("create", create) == initial
        assert not list(root.glob("*.pt"))
        assert reopened.journal.gc_pending_count() == 0
        assert not reopened.gc_last_error
    asyncio.run(scenario())


def test_retirement_transaction_failure_never_deletes_or_drops_state(tmp_path, service_module, monkeypatch):
    async def scenario():
        service, _, counters, root = disk_service(service_module, tmp_path)
        initial, _ = await initial_state(service)
        original = type(service.journal)._update_state_metadata
        def interrupt(connection, request_id, metadata):
            original(connection, request_id, metadata)
            raise RuntimeError("mechanism interrupted transaction")
        monkeypatch.setattr(type(service.journal), "_update_state_metadata", staticmethod(interrupt))
        request = release_request(initial)
        with pytest.raises(RuntimeError, match="interrupted transaction"):
            await service.dispatch("release", request)
        assert service.journal.lookup(request["request_id"]).status == "unknown"
        assert len(list(root.glob("*.pt"))) == 1
        assert initial["state_ref"] in service.worker_states
        assert not counters.get("delete")
        assert not service.journal.gc_pending_count()
        assert service.journal.lookup_state_metadata(initial["state_ref"]).get("released") is not True
    asyncio.run(scenario())


def test_long_append_generate_rollback_chain_bounds_disk_and_keeps_receipts(tmp_path, service_module):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        current, first_request = await initial_state(service)
        first = dict(current)
        for index in range(80):
            binding = replace(_cache_binding(), state_chain_digest=f"{index + 1:064x}",
                              parent_state_digest=current["state_digest"])
            child = await service.dispatch("append", prepared("append", parent_state_ref=current["state_ref"],
                        lane_id=binding.lane_id, delta=f"new event {index}", cache_binding=binding.to_dict()))
            await service.dispatch("release", release_request(current))
            generated = await service.dispatch("generate", prepared("generate", parent_state_ref=child["state_ref"],
                        parent_cache_binding_digest=binding.digest, request_id=f"R-generation-{index}",
                        max_tokens=4090, stop=[], sampling={}))
            await service.dispatch("rollback", prepared("rollback", parent_state_ref=child["state_ref"],
                        candidate_state_ref=generated["candidate"]["state_ref"]))
            current = child
            assert len(list(root.glob("*.pt"))) == 1
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        assert await reopened.dispatch("create", first_request) == first
        await reopened._ensure_loaded(reopened._record(current["state_ref"]))
        assert current["state_ref"] in reopened.worker_states
        assert counters["sample"] == 80
        assert len(list(root.glob("*.pt"))) == 1
    asyncio.run(scenario())


def test_release_route_and_capabilities_use_current_lifecycle_constant(tmp_path, service_module):
    service, _, _, _ = disk_service(service_module, tmp_path)
    capability = service.capabilities()["recurrent_state"]
    assert capability["release"] is True
    assert capability["state_lifecycle_protocol"] == NATIVE_STATE_LIFECYCLE_VERSION
    routes = {}
    class App:
        def get(self, path):
            return lambda function: routes.setdefault(("GET", path), function)
        def post(self, path):
            return lambda function: routes.setdefault(("POST", path), function)
    service_module.RWKVNativeStateEndpointPlugin().attach_router(App())
    assert ("POST", "/v1/state/release") in routes


def test_original_release_reclaims_import_chain_but_preserves_independent_fork(tmp_path, service_module):
    async def scenario():
        service, exports, counters, root = disk_service(service_module, tmp_path)
        original, _ = await initial_state(service)
        aliases = []
        exported = original["export_record"]
        for index in range(3):
            alias = await service.dispatch("import", prepared("import", request_id=f"R-import-{index}",
                export_record=exported, cache_binding=_cache_binding().to_dict()))
            aliases.append(alias)
            exported = alias["export_record"]
        fork_binding = replace(_cache_binding(), lane_id="independent-fork",
                               state_chain_digest="e" * 64, parent_state_digest=original["state_digest"])
        fork = await service.dispatch("fork", prepared("fork", parent_state_ref=original["state_ref"],
            lane_id=fork_binding.lane_id, delta="", cache_binding=fork_binding.to_dict()))
        assert len(list(root.glob("*.pt"))) == 2
        reopened, _, _, _ = disk_service(service_module, tmp_path, exports=exports, counters=counters)
        # The client no longer knows any alias IDs after its process loss.
        released = await reopened.dispatch("release", release_request(original, aliases=True))
        assert released == {"released_state_refs": [original["state_ref"]],
                            "released_alias_state_refs": sorted(value["state_ref"] for value in aliases)}
        assert len(list(root.glob("*.pt"))) == 1
        await reopened._ensure_loaded(reopened._record(fork["state_ref"]))
        assert fork["state_ref"] in reopened.worker_states
        again = await reopened.dispatch("release", release_request(original, aliases=True, request_id="R-another-batch"))
        assert again == released
        assert len(list(root.glob("*.pt"))) == 1
    asyncio.run(scenario())


def test_releasing_one_alias_does_not_release_original_or_sibling(tmp_path, service_module):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        original, _ = await initial_state(service)
        alias = await service.dispatch("import", prepared("import", export_record=original["export_record"],
            cache_binding=_cache_binding().to_dict()))
        result = await service.dispatch("release", release_request(alias, aliases=True))
        assert result["released_alias_state_refs"] == []
        assert service._record(original["state_ref"]).committed
        assert len(list(root.glob("*.pt"))) == 1
    asyncio.run(scenario())


@pytest.mark.parametrize("pending", [False, True])
def test_alias_expansion_checks_candidate_and_unknown_input_dependencies(tmp_path, service_module, pending):
    async def scenario():
        service, _, _, root = disk_service(service_module, tmp_path)
        original, _ = await initial_state(service)
        alias = await service.dispatch("import", prepared("import", export_record=original["export_record"],
            cache_binding=_cache_binding().to_dict()))
        request = prepared("generate", parent_state_ref=alias["state_ref"],
            parent_cache_binding_digest=alias["cache_binding_digest"], request_id="R-alias-generation",
            max_tokens=4090, stop=[], sampling={})
        if pending:
            async def uncertain():
                raise RuntimeError("mechanism unknown")
            with pytest.raises(RuntimeError):
                await service.journal.execute("generate", request, uncertain)
        else:
            await service.dispatch("generate", request)
        with pytest.raises(service_module.HTTPException) as failure:
            await service.dispatch("release", release_request(original, aliases=True))
        assert failure.value.status_code == (503 if pending else 409)
        assert service._record(original["state_ref"]).committed
        assert service._record(alias["state_ref"]).committed
        assert len(list(root.glob("*.pt"))) == (1 if pending else 2)
    asyncio.run(scenario())


@pytest.mark.parametrize("failure", ["none", "after_unlink"])
def test_worker_deletion_is_durable_retryable_and_rank_local(tmp_path, monkeypatch, failure):
    from test_native_persistent_store import worker_module
    worker, _ = worker_module(tmp_path, 0)
    key = "a" * 64
    target = worker._native_store_path(key, 0)
    target.write_bytes(b"fresh mechanism export")
    other_rank = worker._native_store_path(key, 1)
    other_rank.write_bytes(b"another rank")
    synced = []
    sync = worker._sync_native_directory
    def interrupted(path):
        synced.append(path)
        if failure == "after_unlink" and len(synced) == 1:
            raise OSError("mechanism fsync interruption")
        sync(path)
    monkeypatch.setattr(worker, "_sync_native_directory", interrupted)
    if failure == "after_unlink":
        with pytest.raises(OSError):
            worker.delete_native_state_export(store_key=key, worker_rank=0)
        assert not target.exists()
    expected = {"store_key": key, "worker_rank": 0, "deleted": True}
    assert worker.delete_native_state_export(store_key=key, worker_rank=0) == expected
    assert worker.delete_native_state_export(store_key=key, worker_rank=0) == expected
    assert other_rank.read_bytes() == b"another rank"
    assert len(synced) == (3 if failure == "after_unlink" else 2)
    assert all(path == target.parent for path in synced)


@pytest.mark.parametrize("kind", ["symlink", "directory", "path_escape", "rank_bool"])
def test_worker_deletion_rejects_non_blob_paths(tmp_path, kind):
    from test_native_persistent_store import worker_module
    worker, _ = worker_module(tmp_path, 0)
    key = "a" * 64
    target = worker._native_store_path(key, 0)
    protected = tmp_path / "outside.bin"
    protected.write_bytes(b"must remain")
    if kind == "symlink":
        target.symlink_to(protected)
    elif kind == "directory":
        target.mkdir()
    with pytest.raises(ValueError):
        worker.delete_native_state_export(store_key="../outside.bin" if kind == "path_escape" else key,
                                         worker_rank=True if kind == "rank_bool" else 0)
    assert protected.read_bytes() == b"must remain"


def test_populated_pre_lifecycle_journal_is_not_silently_upgraded(tmp_path):
    import sqlite3
    from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal
    path = tmp_path / "old-mechanism.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE native_requests (request_id TEXT)")
        connection.execute("INSERT INTO native_requests VALUES ('old-mechanism-request')")
    with pytest.raises(RuntimeError, match="fresh journal"):
        NativeRequestJournal(path)
