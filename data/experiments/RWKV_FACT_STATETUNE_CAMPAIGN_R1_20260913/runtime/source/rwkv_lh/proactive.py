"""Persistent proactive control plane: triggers, jobs, leases and approvals."""

from __future__ import annotations

import fcntl
import hashlib
import json
import sqlite3
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping
from uuid import uuid4


PROACTIVE_SCHEMA_VERSION = "rwkv-lh.proactive.v2"
_PROACTIVE_MIGRATABLE_SCHEMA_VERSIONS = frozenset(
    {"rwkv-lh.proactive.v1", PROACTIVE_SCHEMA_VERSION}
)


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    selected = value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)
    return selected.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _parse(value: str) -> datetime:
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def _json(value: Mapping[str, Any]) -> str:
    return json.dumps(dict(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class JobStatus(str, Enum):
    QUEUED = "queued"
    WAITING_APPROVAL = "waiting_approval"
    RUNNING = "running"
    WAITING_RETRY = "waiting_retry"
    COMPLETED = "completed"
    FAILED = "failed"
    DEAD_LETTER = "dead_letter"
    CANCELLED = "cancelled"


class LeaseFenceError(RuntimeError):
    """The worker no longer owns the exact lease generation it claimed."""


@dataclass(frozen=True)
class ProactiveJob:
    job_id: str
    payload: Mapping[str, Any]
    status: JobStatus
    due_at: str
    attempts: int
    max_attempts: int
    run_id: str = ""
    trigger_id: str = ""
    concurrency_key: str = ""
    approval_id: str = ""
    lease_owner: str = ""
    lease_until: str = ""
    last_error: str = ""

    @property
    def lease_generation(self) -> int:
        """Monotonic fencing token incremented on every claim or takeover."""
        return self.attempts


@dataclass(frozen=True)
class ProactiveOutcome:
    completed: bool
    run_id: str = ""
    retryable: bool = False
    error: str = ""


JobHandler = Callable[[ProactiveJob], ProactiveOutcome]


class ProactiveStore:
    """SQLite-backed scheduler state independent from model semantics."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "proactive.sqlite3"
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=30, isolation_level=None)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=30000")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            meta_exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' "
                "AND name='proactive_meta'"
            ).fetchone()
            if meta_exists is not None:
                prior = connection.execute(
                    "SELECT value FROM proactive_meta WHERE key='schema_version'"
                ).fetchone()
                if (
                    prior is not None
                    and str(prior["value"])
                    not in _PROACTIVE_MIGRATABLE_SCHEMA_VERSIONS
                ):
                    raise RuntimeError("unsupported proactive database schema")
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS proactive_meta (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proactive_triggers (
                    trigger_id TEXT PRIMARY KEY,
                    kind TEXT NOT NULL CHECK(kind IN ('interval')),
                    payload_json TEXT NOT NULL,
                    interval_seconds INTEGER NOT NULL CHECK(interval_seconds >= 1),
                    next_fire_at TEXT NOT NULL,
                    max_attempts INTEGER NOT NULL CHECK(max_attempts >= 1),
                    approval_kind TEXT NOT NULL DEFAULT '',
                    concurrency_key TEXT NOT NULL DEFAULT '',
                    enabled INTEGER NOT NULL DEFAULT 1,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS proactive_jobs (
                    job_id TEXT PRIMARY KEY,
                    idempotency_key TEXT NOT NULL UNIQUE,
                    trigger_id TEXT NOT NULL DEFAULT '',
                    payload_json TEXT NOT NULL,
                    run_id TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL,
                    due_at TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    max_attempts INTEGER NOT NULL,
                    approval_id TEXT NOT NULL DEFAULT '',
                    concurrency_key TEXT NOT NULL DEFAULT '',
                    lease_owner TEXT NOT NULL DEFAULT '',
                    lease_until TEXT NOT NULL DEFAULT '',
                    last_error TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS proactive_jobs_due
                    ON proactive_jobs(status, due_at);
                CREATE TABLE IF NOT EXISTS proactive_approvals (
                    approval_id TEXT PRIMARY KEY,
                    job_id TEXT NOT NULL UNIQUE,
                    kind TEXT NOT NULL,
                    status TEXT NOT NULL CHECK(status IN ('pending','approved','rejected')),
                    requested_at TEXT NOT NULL,
                    decided_at TEXT NOT NULL DEFAULT '',
                    decided_by TEXT NOT NULL DEFAULT '',
                    reason TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY(job_id) REFERENCES proactive_jobs(job_id)
                );
                CREATE TABLE IF NOT EXISTS proactive_notifications (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL DEFAULT '',
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT value FROM proactive_meta WHERE key='schema_version'"
            ).fetchone()
            trigger_columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(proactive_triggers)"
                ).fetchall()
            }
            if "concurrency_key" not in trigger_columns:
                connection.execute(
                    "ALTER TABLE proactive_triggers ADD COLUMN "
                    "concurrency_key TEXT NOT NULL DEFAULT ''"
                )
            job_columns = {
                str(row["name"])
                for row in connection.execute(
                    "PRAGMA table_info(proactive_jobs)"
                ).fetchall()
            }
            if "concurrency_key" not in job_columns:
                connection.execute(
                    "ALTER TABLE proactive_jobs ADD COLUMN "
                    "concurrency_key TEXT NOT NULL DEFAULT ''"
                )
            connection.execute(
                "CREATE INDEX IF NOT EXISTS proactive_jobs_concurrency "
                "ON proactive_jobs(concurrency_key, status, due_at)"
            )
            if existing is None:
                connection.execute(
                    "INSERT INTO proactive_meta(key,value) VALUES('schema_version',?)",
                    (PROACTIVE_SCHEMA_VERSION,),
                )
            elif str(existing["value"]) != PROACTIVE_SCHEMA_VERSION:
                connection.execute(
                    "UPDATE proactive_meta SET value=? WHERE key='schema_version'",
                    (PROACTIVE_SCHEMA_VERSION,),
                )
            connection.commit()

    @staticmethod
    def _job(row: sqlite3.Row) -> ProactiveJob:
        return ProactiveJob(
            job_id=str(row["job_id"]),
            payload=json.loads(str(row["payload_json"])),
            status=JobStatus(str(row["status"])),
            due_at=str(row["due_at"]),
            attempts=int(row["attempts"]),
            max_attempts=int(row["max_attempts"]),
            run_id=str(row["run_id"]),
            trigger_id=str(row["trigger_id"]),
            concurrency_key=str(row["concurrency_key"]),
            approval_id=str(row["approval_id"]),
            lease_owner=str(row["lease_owner"]),
            lease_until=str(row["lease_until"]),
            last_error=str(row["last_error"]),
        )

    @staticmethod
    def _notify(
        connection: sqlite3.Connection,
        event_type: str,
        payload: Mapping[str, Any],
        *,
        job_id: str = "",
        at: str,
    ) -> None:
        connection.execute(
            "INSERT INTO proactive_notifications(job_id,event_type,payload_json,created_at) "
            "VALUES(?,?,?,?)",
            (job_id, event_type, _json(payload), at),
        )

    def enqueue(
        self,
        payload: Mapping[str, Any],
        *,
        due_at: datetime | None = None,
        max_attempts: int = 5,
        idempotency_key: str | None = None,
        trigger_id: str = "",
        approval_kind: str = "",
        concurrency_key: str = "",
    ) -> ProactiveJob:
        scheduled = _iso(due_at or _now())
        observed = _iso(_now())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            job = self._enqueue_in_transaction(
                connection,
                payload,
                scheduled=scheduled,
                observed=observed,
                max_attempts=max_attempts,
                idempotency_key=idempotency_key,
                trigger_id=trigger_id,
                approval_kind=approval_kind,
                concurrency_key=concurrency_key,
            )
            connection.commit()
        return job

    def _enqueue_in_transaction(
        self,
        connection: sqlite3.Connection,
        payload: Mapping[str, Any],
        *,
        scheduled: str,
        observed: str,
        max_attempts: int,
        idempotency_key: str | None,
        trigger_id: str,
        approval_kind: str,
        concurrency_key: str,
    ) -> ProactiveJob:
        """Materialize one occurrence inside the caller's write transaction."""
        job_id = f"JOB-{uuid4().hex[:16]}"
        key = str(idempotency_key or job_id).strip()
        attempts = max(1, int(max_attempts))
        approval = str(approval_kind or "").strip()
        concurrency = str(concurrency_key or "").strip()[:1000]
        approval_id = f"APPROVAL-{uuid4().hex[:16]}" if approval else ""
        status = JobStatus.WAITING_APPROVAL if approval else JobStatus.QUEUED
        existing = connection.execute(
            "SELECT * FROM proactive_jobs WHERE idempotency_key=?", (key,)
        ).fetchone()
        if existing is not None:
            return self._job(existing)
        connection.execute(
            "INSERT INTO proactive_jobs("
            "job_id,idempotency_key,trigger_id,payload_json,status,due_at,max_attempts,"
            "approval_id,concurrency_key,created_at,updated_at) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?)",
            (
                job_id,
                key,
                str(trigger_id),
                _json(payload),
                status.value,
                scheduled,
                attempts,
                approval_id,
                concurrency,
                observed,
                observed,
            ),
        )
        if approval:
            connection.execute(
                "INSERT INTO proactive_approvals(approval_id,job_id,kind,status,requested_at) "
                "VALUES(?,?,?,?,?)",
                (approval_id, job_id, approval, "pending", observed),
            )
            self._notify(
                connection,
                "approval_requested",
                {"approval_id": approval_id, "kind": approval},
                job_id=job_id,
                at=observed,
            )
        self._notify(
            connection,
            "job_enqueued",
            {"due_at": scheduled, "status": status.value},
            job_id=job_id,
            at=observed,
        )
        row = connection.execute(
            "SELECT * FROM proactive_jobs WHERE job_id=?", (job_id,)
        ).fetchone()
        assert row is not None
        return self._job(row)

    def schedule_interval(
        self,
        payload: Mapping[str, Any],
        *,
        interval_seconds: int,
        first_fire_at: datetime | None = None,
        max_attempts: int = 5,
        approval_kind: str = "",
        concurrency_key: str = "",
        trigger_id: str | None = None,
    ) -> str:
        seconds = max(1, int(interval_seconds))
        selected_id = str(trigger_id or f"TRIGGER-{uuid4().hex[:16]}")
        observed = _iso(_now())
        with self._connect() as connection:
            connection.execute(
                "INSERT INTO proactive_triggers("
                "trigger_id,kind,payload_json,interval_seconds,next_fire_at,max_attempts,"
                "approval_kind,concurrency_key,created_at,updated_at) "
                "VALUES(?,?,?,?,?,?,?,?,?,?)",
                (
                    selected_id,
                    "interval",
                    _json(payload),
                    seconds,
                    _iso(first_fire_at or _now()),
                    max(1, int(max_attempts)),
                    str(approval_kind or ""),
                    str(concurrency_key or "").strip()[:1000],
                    observed,
                    observed,
                ),
            )
        return selected_id

    def fire_due_triggers(self, *, now: datetime | None = None) -> tuple[ProactiveJob, ...]:
        observed_time = now or _now()
        observed = _iso(observed_time)
        created: list[ProactiveJob] = []
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            rows = connection.execute(
                "SELECT * FROM proactive_triggers WHERE enabled=1 AND next_fire_at<=? "
                "ORDER BY next_fire_at,trigger_id",
                (observed,),
            ).fetchall()
            for row in rows:
                scheduled = _parse(str(row["next_fire_at"]))
                interval = timedelta(seconds=int(row["interval_seconds"]))
                next_fire = scheduled + interval
                while next_fire <= observed_time:
                    next_fire += interval
                active = connection.execute(
                    "SELECT * FROM proactive_jobs WHERE trigger_id=? "
                    "AND status IN ('waiting_approval','queued','running','waiting_retry') "
                    "ORDER BY created_at,job_id LIMIT 1",
                    (str(row["trigger_id"]),),
                ).fetchone()
                if active is None:
                    job = self._enqueue_in_transaction(
                        connection,
                        json.loads(str(row["payload_json"])),
                        scheduled=_iso(scheduled),
                        observed=observed,
                        max_attempts=int(row["max_attempts"]),
                        idempotency_key=f"{row['trigger_id']}:{_iso(scheduled)}",
                        trigger_id=str(row["trigger_id"]),
                        approval_kind=str(row["approval_kind"]),
                        concurrency_key=str(row["concurrency_key"]),
                    )
                    created.append(job)
                else:
                    self._notify(
                        connection,
                        "trigger_occurrence_coalesced",
                        {
                            "trigger_id": str(row["trigger_id"]),
                            "scheduled_at": _iso(scheduled),
                            "next_fire_at": _iso(next_fire),
                            "active_job_id": str(active["job_id"]),
                            "active_status": str(active["status"]),
                        },
                        job_id=str(active["job_id"]),
                        at=observed,
                    )
                connection.execute(
                    "UPDATE proactive_triggers SET next_fire_at=?,updated_at=? "
                    "WHERE trigger_id=?",
                    (
                        _iso(next_fire),
                        observed,
                        str(row["trigger_id"]),
                    ),
                )
            connection.commit()
        return tuple(created)

    def claim(
        self,
        worker_id: str,
        *,
        lease_seconds: int = 300,
        now: datetime | None = None,
    ) -> ProactiveJob | None:
        observed_time = now or _now()
        observed = _iso(observed_time)
        lease_until = _iso(observed_time + timedelta(seconds=max(10, lease_seconds)))
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT candidate.* FROM proactive_jobs AS candidate WHERE "
                "(((candidate.status IN ('queued','waiting_retry') "
                "AND candidate.due_at<=?) OR "
                "(candidate.status='running' AND candidate.lease_until!='' "
                "AND candidate.lease_until<=?))) "
                "AND (candidate.concurrency_key='' OR NOT EXISTS ("
                "SELECT 1 FROM proactive_jobs AS active "
                "WHERE active.job_id!=candidate.job_id "
                "AND active.concurrency_key=candidate.concurrency_key "
                "AND active.status='running' AND active.lease_until>?)) "
                "ORDER BY candidate.due_at,candidate.created_at LIMIT 1",
                (observed, observed, observed),
            ).fetchone()
            if row is None:
                connection.commit()
                return None
            job_id = str(row["job_id"])
            connection.execute(
                "UPDATE proactive_jobs SET status='running',attempts=attempts+1,"
                "lease_owner=?,lease_until=?,updated_at=? WHERE job_id=?",
                (str(worker_id), lease_until, observed, job_id),
            )
            self._notify(
                connection,
                "job_claimed",
                {
                    "worker_id": str(worker_id),
                    "lease_until": lease_until,
                    "lease_generation": int(row["attempts"]) + 1,
                },
                job_id=job_id,
                at=observed,
            )
            updated = connection.execute(
                "SELECT * FROM proactive_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            connection.commit()
        assert updated is not None
        return self._job(updated)

    def bind_run(
        self,
        job_id: str,
        run_id: str,
        *,
        worker_id: str,
        lease_generation: int,
    ) -> None:
        observed = _iso(_now())
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE proactive_jobs SET run_id=?,updated_at=? WHERE job_id=? "
                "AND status='running' AND lease_owner=? AND attempts=? "
                "AND lease_until>?",
                (
                    str(run_id),
                    observed,
                    str(job_id),
                    str(worker_id),
                    int(lease_generation),
                    observed,
                ),
            )
        if cursor.rowcount != 1:
            raise LeaseFenceError("job run binding lost its lease fence")

    def renew_lease(
        self,
        job_id: str,
        worker_id: str,
        *,
        lease_generation: int,
        lease_seconds: int = 300,
    ) -> bool:
        observed_time = _now()
        with self._connect() as connection:
            cursor = connection.execute(
                "UPDATE proactive_jobs SET lease_until=?,updated_at=? WHERE job_id=? "
                "AND status='running' AND lease_owner=? AND attempts=? "
                "AND lease_until>?",
                (
                    _iso(observed_time + timedelta(seconds=max(10, lease_seconds))),
                    _iso(observed_time),
                    str(job_id),
                    str(worker_id),
                    int(lease_generation),
                    _iso(observed_time),
                ),
            )
        return cursor.rowcount == 1

    def complete(
        self,
        job_id: str,
        *,
        worker_id: str,
        lease_generation: int,
        run_id: str = "",
    ) -> None:
        observed = _iso(_now())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE proactive_jobs SET status='completed',run_id=CASE WHEN ?='' THEN "
                "run_id ELSE ? END,lease_owner='',lease_until='',last_error='',updated_at=? "
                "WHERE job_id=? AND status='running' AND lease_owner=? AND attempts=? "
                "AND lease_until>?",
                (
                    run_id,
                    run_id,
                    observed,
                    job_id,
                    str(worker_id),
                    int(lease_generation),
                    observed,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise LeaseFenceError("job completion lost its lease fence")
            self._notify(
                connection,
                "job_completed",
                {"run_id": run_id},
                job_id=job_id,
                at=observed,
            )
            connection.commit()

    def retry(
        self,
        job_id: str,
        error: str,
        *,
        worker_id: str,
        lease_generation: int,
        delay_seconds: int,
    ) -> JobStatus:
        observed_time = _now()
        observed = _iso(observed_time)
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT attempts,max_attempts,status,lease_owner,lease_until "
                "FROM proactive_jobs WHERE job_id=?",
                (job_id,),
            ).fetchone()
            if row is None:
                raise KeyError(job_id)
            if (
                str(row["status"]) != JobStatus.RUNNING.value
                or str(row["lease_owner"]) != str(worker_id)
                or int(row["attempts"]) != int(lease_generation)
                or not str(row["lease_until"])
                or _parse(str(row["lease_until"])) <= observed_time
            ):
                connection.rollback()
                raise LeaseFenceError("job retry lost its lease fence")
            exhausted = int(row["attempts"]) >= int(row["max_attempts"])
            status = JobStatus.DEAD_LETTER if exhausted else JobStatus.WAITING_RETRY
            due = _iso(observed_time + timedelta(seconds=max(0, int(delay_seconds))))
            connection.execute(
                "UPDATE proactive_jobs SET status=?,due_at=?,lease_owner='',lease_until='',"
                "last_error=?,updated_at=? WHERE job_id=?",
                (status.value, due, str(error)[:2000], observed, job_id),
            )
            self._notify(
                connection,
                "job_dead_lettered" if exhausted else "job_retry_scheduled",
                {"error": str(error)[:2000], "due_at": due},
                job_id=job_id,
                at=observed,
            )
            connection.commit()
        return status

    def fail(
        self,
        job_id: str,
        error: str,
        *,
        worker_id: str,
        lease_generation: int,
    ) -> None:
        observed = _iso(_now())
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            cursor = connection.execute(
                "UPDATE proactive_jobs SET status='failed',lease_owner='',lease_until='',"
                "last_error=?,updated_at=? WHERE job_id=? AND status='running' "
                "AND lease_owner=? AND attempts=? AND lease_until>?",
                (
                    str(error)[:2000],
                    observed,
                    job_id,
                    str(worker_id),
                    int(lease_generation),
                    observed,
                ),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                raise LeaseFenceError("job failure lost its lease fence")
            self._notify(
                connection,
                "job_failed",
                {"error": str(error)[:2000]},
                job_id=job_id,
                at=observed,
            )
            connection.commit()

    def decide_approval(
        self,
        approval_id: str,
        *,
        approved: bool,
        decided_by: str,
        reason: str = "",
    ) -> ProactiveJob:
        observed = _iso(_now())
        decision = "approved" if approved else "rejected"
        job_status = JobStatus.QUEUED if approved else JobStatus.CANCELLED
        with self._connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT job_id,status FROM proactive_approvals WHERE approval_id=?",
                (approval_id,),
            ).fetchone()
            if row is None:
                raise KeyError(approval_id)
            if str(row["status"]) != "pending":
                raise ValueError("approval was already decided")
            job_id = str(row["job_id"])
            connection.execute(
                "UPDATE proactive_approvals SET status=?,decided_at=?,decided_by=?,reason=? "
                "WHERE approval_id=?",
                (decision, observed, str(decided_by), str(reason)[:1000], approval_id),
            )
            connection.execute(
                "UPDATE proactive_jobs SET status=?,updated_at=? "
                "WHERE job_id=? AND status='waiting_approval'",
                (job_status.value, observed, job_id),
            )
            self._notify(
                connection,
                f"approval_{decision}",
                {"approval_id": approval_id, "decided_by": str(decided_by)},
                job_id=job_id,
                at=observed,
            )
            job_row = connection.execute(
                "SELECT * FROM proactive_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            connection.commit()
        assert job_row is not None
        return self._job(job_row)

    def jobs(self, *, limit: int = 200) -> tuple[ProactiveJob, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM proactive_jobs ORDER BY created_at DESC LIMIT ?",
                (max(1, min(int(limit), 1000)),),
            ).fetchall()
        return tuple(self._job(row) for row in rows)

    def notifications(self, *, after: int = 0, limit: int = 200) -> tuple[dict[str, Any], ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM proactive_notifications WHERE sequence>? "
                "ORDER BY sequence LIMIT ?",
                (max(0, int(after)), max(1, min(int(limit), 1000))),
            ).fetchall()
        return tuple(
            {
                "sequence": int(row["sequence"]),
                "job_id": str(row["job_id"]),
                "event_type": str(row["event_type"]),
                "payload": json.loads(str(row["payload_json"])),
                "created_at": str(row["created_at"]),
            }
            for row in rows
        )

    @contextmanager
    def concurrency_lease(self, concurrency_key: str) -> Iterator[None]:
        """Serialize one local handler scope independently of SQLite lease expiry."""

        selected = str(concurrency_key or "").strip()
        if not selected:
            yield
            return
        lock_root = self.root / "concurrency_locks"
        lock_root.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(selected.encode("utf-8")).hexdigest()
        path = lock_root / f"{digest}.lock"
        with path.open("a+b") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class ProactiveWorker:
    def __init__(
        self,
        store: ProactiveStore,
        handler: JobHandler,
        *,
        worker_id: str,
        retry_base_seconds: int = 30,
        lease_seconds: int = 300,
    ) -> None:
        self.store = store
        self.handler = handler
        self.worker_id = str(worker_id)
        self.retry_base_seconds = max(1, int(retry_base_seconds))
        self.lease_seconds = max(10, int(lease_seconds))

    def run_once(self, *, now: datetime | None = None) -> ProactiveJob | None:
        self.store.fire_due_triggers(now=now)
        job = self.store.claim(
            self.worker_id,
            lease_seconds=self.lease_seconds,
            now=now,
        )
        if job is None:
            return None
        stop_heartbeat = threading.Event()
        lease_lost = threading.Event()

        def heartbeat() -> None:
            while not stop_heartbeat.wait(max(2.0, self.lease_seconds / 3)):
                if not self.store.renew_lease(
                    job.job_id,
                    self.worker_id,
                    lease_generation=job.lease_generation,
                    lease_seconds=self.lease_seconds,
                ):
                    lease_lost.set()
                    return

        heartbeat_thread = threading.Thread(
            target=heartbeat,
            name=f"rwkv-lh-lease-{job.job_id}",
            daemon=True,
        )
        heartbeat_thread.start()
        try:
            with self.store.concurrency_lease(job.concurrency_key):
                outcome = self.handler(job)
            if not isinstance(outcome, ProactiveOutcome):
                raise TypeError("proactive handler returned an invalid outcome")
        except Exception as exc:
            stop_heartbeat.set()
            heartbeat_thread.join(timeout=1)
            try:
                self.store.retry(
                    job.job_id,
                    f"{type(exc).__name__}: {exc}",
                    worker_id=self.worker_id,
                    lease_generation=job.lease_generation,
                    delay_seconds=(
                        self.retry_base_seconds * (2 ** max(0, job.attempts - 1))
                    ),
                )
            except LeaseFenceError:
                pass
            return job
        stop_heartbeat.set()
        heartbeat_thread.join(timeout=1)
        if lease_lost.is_set():
            return job
        if outcome.run_id:
            try:
                self.store.bind_run(
                    job.job_id,
                    outcome.run_id,
                    worker_id=self.worker_id,
                    lease_generation=job.lease_generation,
                )
            except LeaseFenceError:
                return job
        try:
            if outcome.completed:
                self.store.complete(
                    job.job_id,
                    worker_id=self.worker_id,
                    lease_generation=job.lease_generation,
                    run_id=outcome.run_id,
                )
            elif outcome.retryable:
                self.store.retry(
                    job.job_id,
                    outcome.error or "run requested retry",
                    worker_id=self.worker_id,
                    lease_generation=job.lease_generation,
                    delay_seconds=(
                        self.retry_base_seconds * (2 ** max(0, job.attempts - 1))
                    ),
                )
            else:
                self.store.fail(
                    job.job_id,
                    outcome.error or "run failed",
                    worker_id=self.worker_id,
                    lease_generation=job.lease_generation,
                )
        except LeaseFenceError:
            pass
        return job


__all__ = [
    "JobStatus",
    "LeaseFenceError",
    "PROACTIVE_SCHEMA_VERSION",
    "ProactiveJob",
    "ProactiveOutcome",
    "ProactiveStore",
    "ProactiveWorker",
]
