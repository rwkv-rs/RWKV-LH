"""Dropped Native responses query durable results without repeating mutations."""
from __future__ import annotations

import asyncio
import json
import multiprocessing
import os
import sqlite3
from urllib.parse import parse_qs, unquote, urlparse

import pytest
import requests

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.protocol import (
    RWKVOutcomeUnknownError, RWKVRequestNotRecorded, RuntimeCapabilities,
)
from test_openai_compat_runtime import FakeResponse, FakeSession, _cache_binding, settings


NOT_RECORDED = FakeResponse({"detail": "request ID is not recorded"}, status_code=404)


def test_proven_unrecorded_request_is_resubmitted_not_left_unknown(monkeypatch):
    # The journal claims a row before any execution, so a twice-confirmed 404
    # receipt proves the POST never reached the application (e.g. a dead
    # pooled keep-alive connection). The content-addressed request is then
    # safely resubmitted instead of being reported as an unknown outcome.
    events = []
    fake = FakeSession([
        requests.ConnectionError("dead pooled connection"),
        NOT_RECORDED,
        NOT_RECORDED,
        FakeResponse({"rolled_back": True, "parent_state_ref": "parent"}),
    ])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings(), audit_hook=events.append)
    client.state_rollback(candidate_state_ref="candidate", parent_state_ref="parent")
    assert [method for method, _, _ in fake.calls] == ["POST", "GET", "GET", "POST"]
    # Both submissions carry the same content-addressed request id, so the
    # server journal deduplicates a late-arriving original.
    assert fake.calls[0][2]["json"]["request_id"] == fake.calls[3][2]["json"]["request_id"]
    kinds = [event["type"] for event in events]
    assert kinds == [
        "native_request_prepared",
        "native_request_transport_error",
        "native_request_resubmitted",
    ]
    # The first cause is audited before any receipt query can overwrite it.
    assert events[1]["error_type"] == "RWKVOutcomeUnknownError"
    assert "dead pooled connection" in events[1]["error_message"]


def test_unrecorded_resubmission_is_bounded_and_keeps_the_original_cause(monkeypatch):
    fake = FakeSession([
        requests.ConnectionError("first failure"),
        NOT_RECORDED,
        NOT_RECORDED,
        requests.ConnectionError("second failure"),
        NOT_RECORDED,
        NOT_RECORDED,
    ])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(RWKVRequestNotRecorded) as excinfo:
        client.state_rollback(candidate_state_ref="candidate", parent_state_ref="parent")
    assert [method for method, _, _ in fake.calls] == [
        "POST", "GET", "GET", "POST", "GET", "GET",
    ]
    assert "never executed" in str(excinfo.value)
    assert "second failure" in str(excinfo.value)


def test_single_unconfirmed_not_recorded_receipt_does_not_resubmit(monkeypatch):
    # One 404 can race the original POST bytes; only a second confirmation
    # after backoff proves the request was never recorded.
    fake = FakeSession([
        requests.ReadTimeout("response lost"),
        NOT_RECORDED,
        FakeResponse({"detail": "proxy hiccup"}, status_code=503),
        NOT_RECORDED,
        FakeResponse({"rolled_back": True, "parent_state_ref": "parent"}),
    ])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings(retry_attempts=1))
    client.state_rollback(candidate_state_ref="candidate", parent_state_ref="parent")
    # One 404, an unavailable receipt endpoint, then the confirming 404:
    # resubmission happens only after the second 404 confirmation.
    assert [method for method, _, _ in fake.calls] == [
        "POST", "GET", "GET", "GET", "POST",
    ]


def test_unknown_receipt_still_never_repeats_post(monkeypatch):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestRecord, native_request_digest, prepare_native_request,
    )
    from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION
    payload = prepare_native_request("rollback", {
        "schema_version": NATIVE_STATE_PROTOCOL_VERSION, "model": "rwkv-test",
        "candidate_state_ref": "candidate", "parent_state_ref": "parent",
    })
    unknown = NativeRequestRecord(
        payload["request_id"], "rollback",
        native_request_digest("rollback", payload), "unknown",
    ).to_response()
    fake = FakeSession([
        requests.ReadTimeout("response lost"),
        FakeResponse(unknown),
    ])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(RWKVOutcomeUnknownError) as excinfo:
        client.state_rollback(candidate_state_ref="candidate", parent_state_ref="parent")
    assert [method for method, _, _ in fake.calls] == ["POST", "GET"]
    # The receipt outcome does not erase the original transport failure.
    assert "original error" in str(excinfo.value)
    assert "response lost" in str(excinfo.value)


def test_native_capabilities_require_explicit_safe_chunk_and_recovery_support():
    capabilities = RuntimeCapabilities.from_mapping({"recurrent_state": {
        "chunked_prefill": True,
        "request_recovery": True, "request_recovery_protocol": "fixture-protocol",
    }}, source="fixture")
    assert capabilities.recurrent_state_chunked_prefill is True
    assert capabilities.recurrent_state_request_recovery is True
    assert capabilities.recurrent_state_request_recovery_protocol == "fixture-protocol"
    missing = RuntimeCapabilities.from_mapping({}, source="fixture")
    assert missing.recurrent_state_chunked_prefill is False
    assert missing.recurrent_state_request_recovery is False


def test_journal_claims_the_request_row_before_any_execution_starts(tmp_path):
    # Contract anchor for client-side 404 semantics: because this row exists
    # before invoke() runs, a receipt query that returns 404 proves the request
    # never executed and may be safely resubmitted. Breaking this ordering
    # silently breaks RWKVRequestNotRecorded recovery.
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestJournal, NativeRequestResult, prepare_native_request,
    )
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    payload = prepare_native_request("generate", {"model": "fixture", "request_id": "R-claim"})
    observed = []

    async def invoke():
        record = journal.lookup(payload["request_id"])
        observed.append(None if record is None else record.status)
        return NativeRequestResult({"content": "fixture"})

    asyncio.run(journal.execute("generate", payload, invoke))
    assert observed == ["pending"]


@pytest.mark.parametrize("operation", ["generate", "commit", "rollback"])
def test_journal_replays_durable_result_without_reexecuting(tmp_path, operation):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestJournal, NativeRequestResult, prepare_native_request,
    )
    path = tmp_path / "requests.sqlite3"
    payload = prepare_native_request(operation, {"model": "fixture", "request_id": "R-1"})
    calls = []

    async def invoke():
        calls.append(operation)
        return NativeRequestResult({"operation": operation, "token_ids": [31, 7]},
                                   recovery_metadata={"state_ref": "fixture-state"})

    async def scenario():
        first = await NativeRequestJournal(path).execute(operation, payload, invoke)
        reopened = NativeRequestJournal(path)
        replayed = await reopened.execute(operation, payload, invoke)
        assert replayed.to_response() == first.to_response()
        assert replayed.recovery_metadata == {"state_ref": "fixture-state"}
        assert reopened.lookup(payload["request_id"]).status == "completed"
        assert calls == [operation]
    asyncio.run(scenario())


@pytest.mark.parametrize("operation", ["generate", "commit", "rollback", "create", "append", "fork", "import"])
@pytest.mark.parametrize("loss", ["read_timeout", "connection", "chunked", "http_503", "invalid_json"])
def test_client_recovers_original_durable_result_after_response_loss(tmp_path, monkeypatch, operation, loss):
    from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal
    from rwkv_lh.runtime.native_state import NATIVE_STATE_PROTOCOL_VERSION
    binding = _cache_binding()
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    result = ({"candidate": {
        "state_ref": "candidate", "state_digest": "a" * 64, "content": "original answer",
        "finish_reason": "stop", "metadata": {"token_ids": [31, 7]},
        "parent_state_digest": "b" * 64, "parent_cache_binding_digest": binding.digest,
    }} if operation == "generate" else {"rolled_back": True, "parent_state_ref": "parent"}
        if operation == "rollback" else {
            "state_ref": "snapshot", "state_digest": "a" * 64,
            "export_record": {"locator": "fixture"}, "state_format_version": "fixture-v1",
            "server_build": "fixture", "tokenizer_build": "fixture",
            "cache_binding_digest": binding.digest, "protocol_version": NATIVE_STATE_PROTOCOL_VERSION,
        })

    class JournalSession:
        def __init__(self):
            self.calls = []
            self.executions = 0

        def request(self, method, endpoint, **kwargs):
            self.calls.append((method, endpoint, kwargs))
            parsed = urlparse(endpoint)
            if method == "GET":
                request_id = unquote(parsed.path.rsplit("/", 1)[1])
                digest = parse_qs(parsed.query)["request_digest"][0]
                return FakeResponse(journal.lookup(request_id, digest).to_response())

            async def invoke():
                self.executions += 1
                return result

            record = asyncio.run(journal.execute(operation, kwargs["json"], invoke))
            if len(self.calls) == 1:
                if loss == "http_503":
                    return FakeResponse({"detail": "proxy response unavailable"}, status_code=503)
                if loss == "invalid_json":
                    response = FakeResponse({})
                    response.content = b"broken"
                    return response
                error = {"read_timeout": requests.ReadTimeout, "connection": requests.ConnectionError,
                         "chunked": requests.exceptions.ChunkedEncodingError}[loss]
                raise error("response lost after durable completion")
            return FakeResponse(record.body)

        def close(self):
            pass

    fake = JournalSession()
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())

    def invoke_client():
        if operation == "generate":
            return client.state_generate(parent_state_ref="parent", request_id="R-1", max_tokens=4090,
                stop=(), sampling={}, parent_cache_binding_digest=binding.digest)
        if operation == "commit":
            return client.state_commit(candidate_state_ref="candidate", cache_binding=binding)
        if operation == "rollback":
            return client.state_rollback(candidate_state_ref="candidate", parent_state_ref="parent")
        if operation == "import":
            return client.state_import(export_record={"locator": "fixture"}, cache_binding=binding)
        kwargs = {"lane_id": binding.lane_id, "text": "fixture", "cache_binding": binding}
        if operation != "create":
            kwargs["parent_state_ref"] = "parent"
        return getattr(client, "state_" + operation)(**kwargs)

    first = invoke_client()
    assert [method for method, _, _ in fake.calls] == ["POST", "GET"]
    assert invoke_client() == first
    assert fake.executions == 1
    assert fake.calls[0][2]["json"]["request_id"] == fake.calls[2][2]["json"]["request_id"]
    assert b"test-key" not in journal.path.read_bytes()


@pytest.mark.parametrize("field,value", [
    ("request_id", "another-request"), ("request_digest", "b" * 64),
    ("operation", "commit"), ("result_sha256", "c" * 64),
    ("schema_version", "unknown"), ("status", "invented"),
])
def test_client_rejects_mismatched_recovery_receipt(monkeypatch, field, value):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestRecord, native_request_digest, prepare_native_request,
    )
    payload = prepare_native_request("generate", {"request_id": "R-1"})
    response = NativeRequestRecord("R-1", "generate", native_request_digest("generate", payload),
                                  "completed", {"content": "original"}, 200).to_response()
    response[field] = value
    fake = FakeSession([FakeResponse(response)])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(RWKVOutcomeUnknownError):
        client.recover_native_request("generate", payload)
    assert all(method == "GET" for method, _, _ in fake.calls)


def test_inflight_generation_queries_until_original_result_is_ready(monkeypatch):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestRecord, native_request_digest, prepare_native_request,
    )
    payload = prepare_native_request("generate", {"request_id": "R-1"})
    digest = native_request_digest("generate", payload)
    pending = NativeRequestRecord("R-1", "generate", digest, "pending").to_response()
    completed = NativeRequestRecord("R-1", "generate", digest, "completed", {"raw": "original"}, 200).to_response()
    fake = FakeSession([FakeResponse(pending), FakeResponse(pending), FakeResponse(completed)])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings(retry_attempts=1))
    assert client.recover_native_request("generate", payload) == {"raw": "original"}
    assert [method for method, _, _ in fake.calls] == ["GET", "GET", "GET"]


def test_journal_rejects_same_id_with_changed_payload(tmp_path):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestConflict, NativeRequestJournal, prepare_native_request,
    )
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    original = prepare_native_request("generate", {"request_id": "R-1", "max_tokens": 4090})
    changed = prepare_native_request("generate", {"request_id": "R-1", "max_tokens": 10})
    calls = []

    async def invoke():
        calls.append(1)
        return {"content": "original"}

    async def scenario():
        await journal.execute("generate", original, invoke)
        with pytest.raises(NativeRequestConflict):
            await journal.execute("generate", changed, invoke)
        with pytest.raises(NativeRequestConflict):
            await journal.execute("commit", original, invoke)
        assert len(calls) == 1
    asyncio.run(scenario())


def test_disconnected_waiter_does_not_cancel_or_duplicate_generation(tmp_path):
    from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal, prepare_native_request
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    payload = prepare_native_request("generate", {"request_id": "R-1"})

    async def scenario():
        started, release = asyncio.Event(), asyncio.Event()
        calls = []

        async def invoke():
            calls.append(1)
            started.set()
            await release.wait()
            return {"token_ids": [19, 2]}

        disconnected = asyncio.create_task(journal.execute("generate", payload, invoke))
        await started.wait()
        disconnected.cancel()
        with pytest.raises(asyncio.CancelledError):
            await disconnected
        assert journal.lookup(payload["request_id"]).status == "pending"
        duplicate = asyncio.create_task(journal.execute("generate", payload, invoke))
        release.set()
        result = await duplicate
        assert result.body == {"token_ids": [19, 2]}
        assert len(calls) == 1
    asyncio.run(scenario())


def test_interrupted_operation_is_unknown_after_restart_and_never_reexecuted(tmp_path):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestJournal, NativeRequestOutcomeUnknown, prepare_native_request,
    )
    path = tmp_path / "requests.sqlite3"
    journal = NativeRequestJournal(path)
    payload = prepare_native_request("commit", {"request_id": "R-1"})
    calls = []

    async def invoke():
        calls.append(1)
        raise RuntimeError("credential-like-detail-must-not-be-logged")

    async def scenario():
        with pytest.raises(RuntimeError):
            await journal.execute("commit", payload, invoke)
        reopened = NativeRequestJournal(path)
        assert reopened.lookup("R-1").status == "unknown"
        with pytest.raises(NativeRequestOutcomeUnknown):
            await reopened.execute("commit", payload, invoke)
        assert len(calls) == 1
        assert b"credential-like-detail" not in path.read_bytes()
    asyncio.run(scenario())


def _exit_during_claimed_request(path):
    from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal, prepare_native_request

    async def interrupted():
        os._exit(73)

    payload = prepare_native_request("generate", {"request_id": "R-process-exit"})
    asyncio.run(NativeRequestJournal(path).execute("generate", payload, interrupted))


def test_process_exit_leaves_unknown_claim_without_authorizing_second_sample(tmp_path):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestJournal, NativeRequestOutcomeUnknown, prepare_native_request,
    )
    path = tmp_path / "requests.sqlite3"
    process = multiprocessing.get_context("spawn").Process(target=_exit_during_claimed_request, args=(path,))
    process.start()
    try:
        process.join(timeout=10)
        assert process.exitcode == 73
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)
    journal = NativeRequestJournal(path)
    assert journal.lookup("R-process-exit").status == "unknown"
    payload = prepare_native_request("generate", {"request_id": "R-process-exit"})

    async def must_not_sample():
        pytest.fail("a process crash must not authorize another sample")

    with pytest.raises(NativeRequestOutcomeUnknown):
        asyncio.run(journal.execute("generate", payload, must_not_sample))


@pytest.mark.parametrize("column,value", [
    ("result_json", json.dumps({"raw": "changed"})),
    ("recovery_json", json.dumps({"state_ref": "changed"})),
    ("status_code", 201),
])
def test_journal_rejects_changed_result_or_state_recovery_metadata(tmp_path, column, value):
    from rwkv_lh.runtime.native_request_recovery import NativeRequestJournal, prepare_native_request
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    payload = prepare_native_request("generate", {"request_id": "R-1"})

    async def invoke():
        return {"raw": "original"}

    asyncio.run(journal.execute("generate", payload, invoke))
    with sqlite3.connect(journal.path) as connection:
        connection.execute(f"UPDATE native_requests SET {column}=? WHERE request_id=?", (value, "R-1"))
    with pytest.raises(RuntimeError, match="integrity mismatch"):
        journal.lookup("R-1")


@pytest.mark.parametrize("wait", [-1, float("nan"), float("inf"), True])
def test_invalid_recovery_wait_is_rejected_before_request(monkeypatch, wait):
    fake = FakeSession([])
    monkeypatch.setattr(OpenAICompatibleRWKVClient, "_new_session", lambda self: fake)
    client = OpenAICompatibleRWKVClient(settings())
    with pytest.raises(ValueError):
        client.recover_native_request("generate", {"request_id": "R-1"}, max_wait_seconds=wait)
    assert fake.calls == []


def test_old_request_replay_cannot_resurrect_dropped_state(tmp_path):
    from rwkv_lh.runtime.native_request_recovery import (
        NativeRequestJournal, NativeRequestResult, prepare_native_request,
    )
    journal = NativeRequestJournal(tmp_path / "requests.sqlite3")
    generate = prepare_native_request("generate", {"request_id": "R-generate"})
    rollback = prepare_native_request("rollback", {"request_id": "R-rollback"})

    async def sample():
        return NativeRequestResult({"candidate": "state"}, recovery_metadata={
            "states": [{"state_ref": "state", "committed": False}], "dropped_state_refs": [],
        })

    async def drop():
        return NativeRequestResult({"rolled_back": True}, recovery_metadata={
            "states": [], "dropped_state_refs": ["state"],
        })

    async def scenario():
        await journal.execute("generate", generate, sample)
        await journal.execute("rollback", rollback, drop)
        await journal.execute("generate", generate, sample)
        assert journal.lookup_state_metadata("state") == {"state_ref": "state", "committed": False, "dropped": True}
    asyncio.run(scenario())
