"""Durable Native request results; an uncertain operation is never executed again.

The journal stores request digests, original results and service-owned recovery
metadata. It never stores request headers, request bodies or exception text.
The service must export every referenced State before returning its result.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import sqlite3
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Awaitable, Callable, Mapping
from uuid import uuid4

from rwkv_lh.runtime.native_request_protocol import (
    NATIVE_REQUEST_RECOVERY_VERSION, NATIVE_REQUEST_OPERATIONS,
    native_result_digest, native_request_digest, prepare_native_request,
)


class NativeRequestConflict(ValueError):
    """A request ID is already bound to a different operation or payload."""


class NativeRequestInProgress(RuntimeError):
    """A durable claim exists but this process has no waiter for it."""


class NativeRequestOutcomeUnknown(RuntimeError):
    """An operation may have executed; executing it again is prohibited."""


class NativeStateRetired(ValueError):
    """An explicitly retired handle cannot authorize a new operation."""


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)



@dataclass(frozen=True)
class NativeRequestResult:
    body: Mapping[str, Any]
    status_code: int = 200
    recovery_metadata: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class NativeRequestRecord:
    request_id: str
    operation: str
    request_digest: str
    status: str
    body: Mapping[str, Any] | None = None
    status_code: int | None = None
    recovery_metadata: Mapping[str, Any] = field(default_factory=dict)

    def to_response(self) -> dict[str, Any]:
        response = {
            "schema_version": NATIVE_REQUEST_RECOVERY_VERSION,
            "request_id": self.request_id,
            "operation": self.operation,
            "request_digest": self.request_digest,
            "status": self.status,
        }
        if self.status == "completed":
            assert self.body is not None
            response.update(http_status=self.status_code, result=dict(self.body),
                            result_sha256=native_result_digest(self.body))
        return response


class NativeRequestJournal:
    """SQLite claims survive process loss; shielded work survives HTTP loss.

    A completed result is replayable after restart. A pending row owned by a
    different journal instance is unknown, because no durable result proves
    whether its side effects completed. Neither state authorizes a second call.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        os.fchmod(fd, 0o600)
        os.close(fd)
        self.owner_id = uuid4().hex
        self._tasks: dict[str, asyncio.Task[NativeRequestRecord]] = {}
        with self._connect() as connection:
            connection.execute("PRAGMA journal_mode=WAL")
            tables = {row[0] for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            if ("native_requests" in tables and "native_request_inputs" not in tables
                    and connection.execute("SELECT 1 FROM native_requests LIMIT 1").fetchone()):
                raise RuntimeError("Native lifecycle requires a fresh journal; historical input pins are unavailable")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_requests (
                request_id TEXT PRIMARY KEY, operation TEXT NOT NULL,
                request_digest TEXT NOT NULL, status TEXT NOT NULL,
                owner_id TEXT NOT NULL, result_json TEXT, result_sha256 TEXT,
                status_code INTEGER, recovery_json TEXT, created REAL NOT NULL,
                updated REAL NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_request_states (
                state_ref TEXT PRIMARY KEY, metadata_json TEXT NOT NULL,
                metadata_sha256 TEXT NOT NULL, updated_request_id TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_request_mutations (
                request_id TEXT PRIMARY KEY, state_ref TEXT NOT NULL)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_request_inputs (
                request_id TEXT NOT NULL, kind TEXT NOT NULL, resource TEXT NOT NULL,
                PRIMARY KEY(request_id,kind,resource))""")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_state_retirements (
                state_ref TEXT PRIMARY KEY, store_key TEXT, cache_dropped INTEGER NOT NULL DEFAULT 0)""")
            connection.execute("""CREATE TABLE IF NOT EXISTS native_state_gc (
                store_key TEXT PRIMARY KEY)""")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute("PRAGMA synchronous=FULL")
            with connection:
                yield connection
        finally:
            connection.close()

    def _record(self, row: sqlite3.Row) -> NativeRequestRecord:
        status = row["status"]
        if status == "pending" and row["owner_id"] != self.owner_id:
            status = "unknown"
        body = json.loads(row["result_json"]) if row["result_json"] is not None else None
        metadata = json.loads(row["recovery_json"] or "{}")
        if status == "completed" and (not isinstance(body, dict)
                or not isinstance(metadata, dict)
                or native_result_digest({"body": body, "status_code": row["status_code"],
                                         "recovery_metadata": metadata}) != row["result_sha256"]):
            raise RuntimeError("Native request result integrity mismatch")
        return NativeRequestRecord(
            row["request_id"], row["operation"], row["request_digest"], status,
            body, row["status_code"], metadata,
        )

    def lookup(self, request_id: str, request_digest: str | None = None) -> NativeRequestRecord | None:
        with self._connect() as connection:
            row = connection.execute("SELECT * FROM native_requests WHERE request_id=?", (request_id,)).fetchone()
        if row is None:
            return None
        if request_digest is not None and row["request_digest"] != request_digest:
            raise NativeRequestConflict("Native request ID has a different payload")
        return self._record(row)

    def lookup_state_metadata(self, state_ref: str, *, allow_request_id: str = "") -> dict[str, Any] | None:
        with self._connect() as connection:
            uncertain = connection.execute("""SELECT r.request_id FROM native_request_mutations m
                JOIN native_requests r ON r.request_id=m.request_id WHERE m.state_ref=?
                AND r.status IN ('pending', 'unknown') AND r.request_id != ? LIMIT 1""",
                (state_ref, allow_request_id)).fetchone()
            if uncertain is not None:
                raise NativeRequestOutcomeUnknown("Native State has an unresolved mutation")
            row = connection.execute("SELECT * FROM native_request_states WHERE state_ref=?", (state_ref,)).fetchone()
        if row is None:
            return None
        metadata = json.loads(row["metadata_json"])
        if (not isinstance(metadata, dict) or metadata.get("state_ref") != state_ref
                or native_result_digest(metadata) != row["metadata_sha256"]):
            raise RuntimeError("Native State recovery metadata integrity mismatch")
        return metadata

    @staticmethod
    def _state_rows(connection) -> list[dict[str, Any]]:
        result = []
        for row in connection.execute("SELECT * FROM native_request_states"):
            metadata = json.loads(row["metadata_json"])
            if (not isinstance(metadata, dict) or metadata.get("state_ref") != row["state_ref"]
                    or native_result_digest(metadata) != row["metadata_sha256"]):
                raise RuntimeError("Native State recovery metadata integrity mismatch")
            result.append(metadata)
        return result

    @staticmethod
    def _retired(metadata: Mapping[str, Any]) -> bool:
        return metadata.get("dropped") is True or metadata.get("released") is True

    @staticmethod
    def _store_key(metadata: Mapping[str, Any]) -> str | None:
        exported = metadata.get("export_record")
        key = exported.get("store_key") if isinstance(exported, dict) else None
        if key is not None and (not isinstance(key, str) or not re.fullmatch(r"[0-9a-f]{64}", key)):
            raise RuntimeError("Native State export has an invalid store key")
        return key

    def validate_release(self, refs: set[str], *, allow_request_id: str) -> None:
        """Called under the service execution lock before any batch mutation."""
        with self._connect() as connection:
            states = self._state_rows(connection)
            by_ref = {value["state_ref"]: value for value in states}
            for value in states:
                if (not self._retired(value) and value.get("committed") is False
                        and value.get("parent_state_ref") in refs):
                    raise NativeRequestConflict("a live candidate still requires the parent State")
            keys = {self._store_key(by_ref[ref]) for ref in refs if ref in by_ref}
            keys.discard(None)
            for row in connection.execute("""SELECT i.kind,i.resource FROM native_request_inputs i
                    JOIN native_requests r ON r.request_id=i.request_id
                    WHERE r.status IN ('pending','unknown') AND r.request_id != ?""", (allow_request_id,)):
                if (row["kind"] == "state" and row["resource"] in refs
                        or row["kind"] == "blob" and row["resource"] in keys):
                    raise NativeRequestOutcomeUnknown("a pending or unknown request still requires this State")

    def import_aliases_for(self, originals: set[str]) -> list[dict[str, Any]]:
        with self._connect() as connection:
            states = self._state_rows(connection)
        by_ref = {value["state_ref"]: value for value in states}
        aliases = []
        for value in states:
            origin = value.get("import_origin_state_ref")
            if origin not in originals or value["state_ref"] in originals:
                continue
            original = by_ref[origin]
            if (all(value.get(key) == original.get(key) for key in ("state_digest", "cache_binding_digest"))
                    and self._store_key(value) == self._store_key(original)):
                aliases.append(value)
        return aliases

    def pending_retirements(self) -> list[str]:
        with self._connect() as connection:
            return [row[0] for row in connection.execute(
                "SELECT state_ref FROM native_state_retirements WHERE cache_dropped=0 ORDER BY state_ref")]

    def mark_cache_dropped(self, state_ref: str) -> None:
        with self._connect() as connection:
            connection.execute("UPDATE native_state_retirements SET cache_dropped=1 WHERE state_ref=?", (state_ref,))

    def reclaimable_store_keys(self) -> list[str]:
        """Only current owners/pins retain tensors, never historical receipts."""
        with self._connect() as connection:
            states = self._state_rows(connection)
            by_ref = {value["state_ref"]: value for value in states}
            protected = {self._store_key(value) for value in states if not self._retired(value)}
            for row in connection.execute("""SELECT i.kind,i.resource FROM native_request_inputs i
                    JOIN native_requests r ON r.request_id=i.request_id WHERE r.status IN ('pending','unknown')"""):
                if row["kind"] == "blob":
                    protected.add(row["resource"])
                elif row["resource"] in by_ref:
                    protected.add(self._store_key(by_ref[row["resource"]]))
            return [row[0] for row in connection.execute("SELECT store_key FROM native_state_gc ORDER BY store_key")
                    if row[0] not in protected]

    def mark_blob_deleted(self, store_key: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM native_state_gc WHERE store_key=?", (store_key,))

    def gc_pending_count(self) -> int:
        with self._connect() as connection:
            return connection.execute("SELECT COUNT(*) FROM native_state_gc").fetchone()[0]

    @classmethod
    def _update_state_metadata(cls, connection, request_id, metadata):
        states = metadata.get("states", [])
        dropped = metadata.get("dropped_state_refs", [])
        released = metadata.get("released_state_refs", [])
        if (not isinstance(states, list) or not isinstance(dropped, list) or not isinstance(released, list)
                or any(not isinstance(value, dict) or not isinstance(value.get("state_ref"), str)
                       or not value["state_ref"] for value in states)
                or any(not isinstance(ref, str) or not ref for ref in dropped + released)):
            raise ValueError("invalid Native State recovery metadata")
        refs = [value["state_ref"] for value in states] + dropped + released
        if len(refs) != len(set(refs)):
            raise ValueError("duplicate Native State recovery metadata")
        values = states + [{"state_ref": ref, "dropped": True} for ref in dropped] + [
            {"state_ref": ref, "released": True} for ref in released]
        for value in values:
            ref = value["state_ref"]
            previous = connection.execute("SELECT * FROM native_request_states WHERE state_ref=?", (ref,)).fetchone()
            if previous is not None:
                old = json.loads(previous["metadata_json"])
                if native_result_digest(old) != previous["metadata_sha256"]:
                    raise RuntimeError("Native State recovery metadata integrity mismatch")
                if cls._retired(old) and not cls._retired(value):
                    raise ValueError("a retired Native State cannot be resurrected")
                if old.get("committed") is True and value.get("committed") is False:
                    raise ValueError("a committed Native State cannot become a candidate")
                if cls._retired(value):
                    value = {**old, **value}
                    key = cls._store_key(old)
                    connection.execute("""INSERT INTO native_state_retirements (state_ref,store_key)
                        VALUES (?,?) ON CONFLICT(state_ref) DO NOTHING""", (ref, key))
                    if key and not cls._retired(old):
                        connection.execute("INSERT OR IGNORE INTO native_state_gc (store_key) VALUES (?)", (key,))
            connection.execute("""INSERT INTO native_request_states
                (state_ref, metadata_json, metadata_sha256, updated_request_id) VALUES (?, ?, ?, ?)
                ON CONFLICT(state_ref) DO UPDATE SET metadata_json=excluded.metadata_json,
                metadata_sha256=excluded.metadata_sha256, updated_request_id=excluded.updated_request_id""",
                (ref, _json(value), native_result_digest(value), request_id))

    @staticmethod
    def _input_resources(operation: str, payload: Mapping[str, Any]) -> set[tuple[str, str]]:
        resources = set()
        for field in ("parent_state_ref", "candidate_state_ref"):
            value = payload.get(field)
            if isinstance(value, str) and value:
                resources.add(("state", value))
        if operation == "release" and isinstance(payload.get("states"), list):
            for value in payload["states"]:
                if isinstance(value, dict) and isinstance(value.get("state_ref"), str) and value["state_ref"]:
                    resources.add(("state", value["state_ref"]))
        exported = payload.get("export_record") if operation == "import" else None
        if isinstance(exported, dict):
            for kind, field in (("state", "state_ref"), ("blob", "store_key")):
                value = exported.get(field)
                if isinstance(value, str) and value:
                    resources.add((kind, value))
        return resources

    def _claim(self, operation: str, payload: Mapping[str, Any]) -> tuple[NativeRequestRecord, bool]:
        if dict(payload) != prepare_native_request(operation, payload):
            raise ValueError("Native request requires recovery protocol and request ID")
        request_id = payload["request_id"]
        digest = native_request_digest(operation, payload)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute("SELECT * FROM native_requests WHERE request_id=?", (request_id,)).fetchone()
            if row is not None:
                if row["request_digest"] != digest or row["operation"] != operation:
                    raise NativeRequestConflict("Native request ID has a different payload")
                return self._record(row), False
            now = time.time()
            resources = self._input_resources(operation, payload)
            for kind, resource in resources:
                if kind == "state":
                    row = connection.execute("SELECT metadata_json FROM native_request_states WHERE state_ref=?", (resource,)).fetchone()
                    if row is not None and self._retired(json.loads(row[0])) and operation != "release":
                        raise NativeStateRetired("State handle was explicitly retired")
            mutation_ref = payload.get("candidate_state_ref") if operation in {"commit", "rollback"} else None
            if isinstance(mutation_ref, str) and mutation_ref:
                uncertain = connection.execute("""SELECT r.request_id FROM native_request_mutations m
                    JOIN native_requests r ON r.request_id=m.request_id WHERE m.state_ref=?
                    AND r.status IN ('pending', 'unknown') LIMIT 1""", (mutation_ref,)).fetchone()
                if uncertain is not None:
                    raise NativeRequestOutcomeUnknown("Native State already has an unresolved mutation")
            connection.execute("""INSERT INTO native_requests
                (request_id, operation, request_digest, status, owner_id, created, updated)
                VALUES (?, ?, ?, 'pending', ?, ?, ?)""", (request_id, operation, digest, self.owner_id, now, now))
            connection.executemany("INSERT INTO native_request_inputs (request_id,kind,resource) VALUES (?,?,?)",
                                   [(request_id, kind, resource) for kind, resource in sorted(resources)])
            if isinstance(mutation_ref, str) and mutation_ref:
                connection.execute("INSERT INTO native_request_mutations (request_id,state_ref) VALUES (?,?)",
                                   (request_id, mutation_ref))
        return NativeRequestRecord(request_id, operation, digest, "pending"), True

    async def _run(self, claimed: NativeRequestRecord, invoke: Callable[[], Awaitable[NativeRequestResult | Mapping[str, Any]]], execution_lock=None) -> NativeRequestRecord:
        if execution_lock is not None:
            async with execution_lock:
                return await self._run(claimed, invoke)
        try:
            result = await invoke()
            if isinstance(result, Mapping):
                result = NativeRequestResult(result)
            if not isinstance(result, NativeRequestResult) or not isinstance(result.body, Mapping):
                raise TypeError("Native request callback returned an invalid result")
            if isinstance(result.status_code, bool) or not isinstance(result.status_code, int) or not 200 <= result.status_code <= 599:
                raise ValueError("Native request result has an invalid HTTP status")
            body_json, metadata_json = _json(dict(result.body)), _json(dict(result.recovery_metadata))
            result_digest = native_result_digest({"body": dict(result.body), "status_code": result.status_code,
                                                  "recovery_metadata": dict(result.recovery_metadata)})
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")
                self._update_state_metadata(connection, claimed.request_id, result.recovery_metadata)
                changed = connection.execute("""UPDATE native_requests SET status='completed', result_json=?,
                    result_sha256=?, status_code=?, recovery_json=?, updated=?
                    WHERE request_id=? AND owner_id=? AND status='pending'""",
                    (body_json, result_digest, result.status_code, metadata_json,
                     time.time(), claimed.request_id, self.owner_id))
                if changed.rowcount != 1:
                    raise RuntimeError("Native request completion lost its durable claim")
            record = self.lookup(claimed.request_id, claimed.request_digest)
            assert record is not None
            return record
        except BaseException:
            with self._connect() as connection:
                connection.execute("""UPDATE native_requests SET status='unknown', updated=?
                    WHERE request_id=? AND owner_id=? AND status='pending'""",
                    (time.time(), claimed.request_id, self.owner_id))
            raise

    async def execute(self, operation: str, payload: Mapping[str, Any],
                      invoke: Callable[[], Awaitable[NativeRequestResult | Mapping[str, Any]]], *,
                      execution_lock: asyncio.Lock | None = None) -> NativeRequestRecord:
        claimed, created = self._claim(operation, payload)
        if claimed.status == "completed":
            return claimed
        if claimed.status == "unknown":
            raise NativeRequestOutcomeUnknown("Native request outcome is unknown; reexecution is prohibited")
        task = self._tasks.get(claimed.request_id)
        if created:
            task = asyncio.create_task(self._run(claimed, invoke, execution_lock))
            self._tasks[claimed.request_id] = task

            def done(completed: asyncio.Task[NativeRequestRecord]) -> None:
                self._tasks.pop(claimed.request_id, None)
                if not completed.cancelled():
                    completed.exception()  # Retrieve detached failures without logging their text.
            task.add_done_callback(done)
        if task is None:
            raise NativeRequestInProgress("Native request is pending in another execution context")
        return await asyncio.shield(task)
