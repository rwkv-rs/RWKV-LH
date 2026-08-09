"""Transactional SQLite state, checkpoints, events, and controller leases."""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol
from uuid import uuid4

from rwkv_lh.runtime.settings import PROJECT_ROOT
from rwkv_lh.schema import GoalState, RunState, RunStatus, utc_now


class ConcurrentStateError(RuntimeError):
    pass


class StateRecoveryError(RuntimeError):
    pass


class StateStore(Protocol):
    def artifact_directory(self, run_id: str) -> Path: ...

    def artifact_locator(self, path: str | Path) -> str: ...

    def create_run(self, goal: GoalState, run_id: str | None = None) -> RunState: ...

    def load(self, run_id: str) -> RunState: ...

    def save(
        self,
        state: RunState,
        *,
        expected_revision: int | None = None,
        event_type: str = "state_saved",
        event: Mapping[str, Any] | None = None,
    ) -> RunState: ...

    def controller_lease(
        self,
        run_id: str,
        *,
        timeout_seconds: float = 0.25,
        lease_seconds: float = 300.0,
    ) -> Iterator[None]: ...


class LongHorizonStore:
    _milestone_events = {
        "run_created",
        "plan_saved",
        "run_completed",
        "run_blocked",
        "run_failed",
        "run_interrupted",
        "replan_saved",
        "snapshot_recovered",
    }
    def __init__(
        self,
        root: str | Path | None = None,
        *,
        checkpoint_retention: int = 20,
    ):
        self.root = Path(root or PROJECT_ROOT / "data" / "runs").resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.database_path = self.root / "long_horizon.db"
        self.artifact_root = self.root / "artifacts"
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        self.checkpoint_retention = max(1, int(checkpoint_retention))
        self._initialize_database()

    def run_directory(self, run_id: str) -> Path:
        return self.artifact_directory(run_id)

    def artifact_directory(self, run_id: str) -> Path:
        return self.artifact_root / self._normalize_run_id(run_id)

    def artifact_locator(self, path: str | Path) -> str:
        resolved = Path(path).resolve()
        try:
            relative = resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("artifact is outside the store root") from exc
        return f"store:{relative}"

    def create_run(self, goal: GoalState, run_id: str | None = None) -> RunState:
        identifier = self._normalize_run_id(run_id or f"LH-{uuid4().hex[:16]}")
        artifact_directory = self.artifact_directory(identifier)
        artifact_directory_existed = artifact_directory.exists()
        if artifact_directory.exists() and any(artifact_directory.iterdir()):
            raise FileExistsError(f"run artifacts already exist: {identifier}")
        artifact_directory.mkdir(parents=True, exist_ok=True)
        state = RunState(run_id=identifier, goal=goal)
        try:
            return self.save(
                state,
                expected_revision=-1,
                event_type="run_created",
                event={"goal_digest": goal.digest},
            )
        except Exception:
            if not artifact_directory_existed:
                try:
                    artifact_directory.rmdir()
                except OSError:
                    pass
            raise

    def load(self, run_id: str) -> RunState:
        identifier = self._normalize_run_id(run_id)
        with self._connect() as connection:
            row = connection.execute(
                "SELECT revision, goal_digest, state_json FROM runs WHERE run_id = ?",
                (identifier,),
            ).fetchone()
            if row is None:
                raise StateRecoveryError(f"unknown run: {identifier}")
            failures: list[str] = []
            state = self._decode_state(row["state_json"], identifier, failures, "runs")
            expected_goal_digest = str(row["goal_digest"])
            if state is not None and state.goal.digest != expected_goal_digest:
                failures.append("runs: immutable goal digest mismatch")
                state = None
            if state is not None and state.revision == int(row["revision"]):
                return state
            checkpoints = connection.execute(
                """
                SELECT revision, state_json
                FROM checkpoints
                WHERE run_id = ?
                ORDER BY revision DESC
                """,
                (identifier,),
            ).fetchall()
            for checkpoint in checkpoints:
                recovered = self._decode_state(
                    checkpoint["state_json"],
                    identifier,
                    failures,
                    f"checkpoint:{checkpoint['revision']}",
                )
                if recovered is None:
                    continue
                if recovered.goal.digest != expected_goal_digest:
                    failures.append(
                        f"checkpoint:{checkpoint['revision']}: immutable goal digest mismatch"
                    )
                    continue
                return self._repair_current_snapshot(
                    connection,
                    recovered,
                    current_revision=int(row["revision"]),
                )
        detail = "; ".join(failures[:5]) or "no checkpoint rows"
        raise StateRecoveryError(f"no valid state for {identifier}: {detail}")

    def save(
        self,
        state: RunState,
        *,
        expected_revision: int | None = None,
        event_type: str = "state_saved",
        event: Mapping[str, Any] | None = None,
    ) -> RunState:
        if not state.goal.verify_digest():
            raise ValueError("goal digest mismatch")
        identifier = self._normalize_run_id(state.run_id)
        expected = state.revision if expected_revision is None else int(expected_revision)
        saved = RunState.from_dict(state.to_dict())
        event_name = str(event_type or "state_saved")
        with self._transaction() as connection:
            row = connection.execute(
                "SELECT revision, goal_digest FROM runs WHERE run_id = ?",
                (identifier,),
            ).fetchone()
            disk_revision = int(row["revision"]) if row is not None else -1
            if disk_revision != expected:
                raise ConcurrentStateError(
                    f"stale state revision: expected {expected}, found {disk_revision}"
                )
            if row is not None and str(row["goal_digest"]) != saved.goal.digest:
                raise ValueError("immutable goal digest changed")
            saved.revision = disk_revision + 1
            saved.updated_at = utc_now()
            state_json = self._serialize(saved.to_dict())
            milestone = int(event_name in self._milestone_events)
            if row is None:
                connection.execute(
                    """
                    INSERT INTO runs (
                        run_id, revision, status, goal_digest, state_json,
                        created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        identifier,
                        saved.revision,
                        saved.status.value,
                        saved.goal.digest,
                        state_json,
                        saved.created_at,
                        saved.updated_at,
                    ),
                )
            else:
                cursor = connection.execute(
                    """
                    UPDATE runs
                    SET revision = ?, status = ?, goal_digest = ?,
                        state_json = ?, updated_at = ?
                    WHERE run_id = ? AND revision = ?
                    """,
                    (
                        saved.revision,
                        saved.status.value,
                        saved.goal.digest,
                        state_json,
                        saved.updated_at,
                        identifier,
                        disk_revision,
                    ),
                )
                if cursor.rowcount != 1:
                    raise ConcurrentStateError(f"state changed while saving: {identifier}")
            connection.execute(
                """
                INSERT INTO checkpoints (
                    run_id, revision, state_json, event_type, milestone, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    identifier,
                    saved.revision,
                    state_json,
                    event_name,
                    milestone,
                    saved.updated_at,
                ),
            )
            self._replace_task_index(connection, saved)
            connection.execute(
                """
                INSERT INTO events (
                    timestamp, run_id, revision, type, data_json
                ) VALUES (?, ?, ?, ?, ?)
                """,
                (
                    saved.updated_at,
                    identifier,
                    saved.revision,
                    event_name,
                    self._serialize(dict(event or {})),
                ),
            )
            self._prune_checkpoints(connection, identifier)
        self.artifact_directory(identifier).mkdir(parents=True, exist_ok=True)
        return saved

    def event_records(self, run_id: str) -> list[dict[str, Any]]:
        identifier = self._normalize_run_id(run_id)
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT event_id, timestamp, run_id, revision, type, data_json
                FROM events
                WHERE run_id = ?
                ORDER BY event_id
                """,
                (identifier,),
            ).fetchall()
        return [
            {
                "event_id": int(row["event_id"]),
                "timestamp": row["timestamp"],
                "run_id": row["run_id"],
                "revision": int(row["revision"]),
                "type": row["type"],
                "data": json.loads(row["data_json"]),
            }
            for row in rows
        ]

    @contextmanager
    def controller_lease(
        self,
        run_id: str,
        *,
        timeout_seconds: float = 0.25,
        lease_seconds: float = 300.0,
    ) -> Iterator[None]:
        identifier = self._normalize_run_id(run_id)
        timeout = max(0.0, float(timeout_seconds))
        duration = max(1.0, float(lease_seconds))
        owner_id = uuid4().hex
        deadline = time.monotonic() + timeout
        while True:
            if self._try_acquire_lease(identifier, owner_id, duration):
                break
            if time.monotonic() >= deadline:
                raise TimeoutError(f"controller lease unavailable: {identifier}")
            time.sleep(min(0.025, max(0.0, deadline - time.monotonic())))

        stop_heartbeat = threading.Event()
        heartbeat_errors: list[Exception] = []

        def heartbeat() -> None:
            interval = max(0.25, min(duration / 3.0, 30.0))
            while not stop_heartbeat.wait(interval):
                try:
                    self._renew_lease(identifier, owner_id, duration)
                except Exception as exc:
                    heartbeat_errors.append(exc)
                    return

        worker = threading.Thread(
            target=heartbeat,
            name=f"long-horizon-lease-{identifier}",
            daemon=True,
        )
        worker.start()
        body_failed = False
        try:
            yield
        except BaseException:
            body_failed = True
            raise
        finally:
            stop_heartbeat.set()
            worker.join(timeout=1.0)
            self._release_lease(identifier, owner_id)
            if heartbeat_errors and not body_failed:
                raise ConcurrentStateError(
                    f"controller lease lost: {identifier}: {heartbeat_errors[0]}"
                )

    def _initialize_database(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    revision INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    goal_digest TEXT NOT NULL,
                    state_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS task_index (
                    run_id TEXT NOT NULL,
                    task_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    required INTEGER NOT NULL,
                    active INTEGER NOT NULL,
                    priority INTEGER NOT NULL,
                    PRIMARY KEY (run_id, task_id),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS task_index_ready
                ON task_index(run_id, status, active, required, priority DESC);

                CREATE TABLE IF NOT EXISTS checkpoints (
                    run_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    state_json TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    milestone INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY (run_id, revision),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    run_id TEXT NOT NULL,
                    revision INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    data_json TEXT NOT NULL,
                    UNIQUE (run_id, revision),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS run_leases (
                    run_id TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    process_id INTEGER NOT NULL,
                    acquired_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id) ON DELETE CASCADE
                );

                PRAGMA user_version = 1;
                """
            )

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.database_path,
            timeout=5.0,
            isolation_level=None,
        )
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA journal_mode = WAL")
        connection.execute("PRAGMA synchronous = FULL")
        connection.execute("PRAGMA busy_timeout = 5000")
        return connection

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            connection.execute("BEGIN IMMEDIATE")
            yield connection
            connection.commit()
        except BaseException:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _repair_current_snapshot(
        self,
        connection: sqlite3.Connection,
        state: RunState,
        *,
        current_revision: int,
    ) -> RunState:
        connection.execute("BEGIN IMMEDIATE")
        try:
            repaired = RunState.from_dict(state.to_dict())
            recovered_from_revision = repaired.revision
            if repaired.revision < current_revision:
                maximum_event_revision = int(
                    connection.execute(
                        "SELECT COALESCE(MAX(revision), -1) FROM events WHERE run_id = ?",
                        (repaired.run_id,),
                    ).fetchone()[0]
                )
                repaired.revision = max(current_revision, maximum_event_revision) + 1
                repaired.updated_at = utc_now()
            state_json = self._serialize(repaired.to_dict())
            cursor = connection.execute(
                """
                UPDATE runs
                SET revision = ?, status = ?, goal_digest = ?,
                    state_json = ?, updated_at = ?
                WHERE run_id = ?
                """,
                (
                    repaired.revision,
                    repaired.status.value,
                    repaired.goal.digest,
                    state_json,
                    repaired.updated_at,
                    repaired.run_id,
                ),
            )
            if cursor.rowcount != 1:
                raise StateRecoveryError(f"run disappeared during recovery: {repaired.run_id}")
            self._replace_task_index(connection, repaired)
            if repaired.revision > current_revision:
                connection.execute(
                    """
                    INSERT INTO checkpoints (
                        run_id, revision, state_json, event_type, milestone, created_at
                    ) VALUES (?, ?, ?, 'snapshot_recovered', 1, ?)
                    """,
                    (
                        repaired.run_id,
                        repaired.revision,
                        state_json,
                        repaired.updated_at,
                    ),
                )
                connection.execute(
                    """
                    INSERT INTO events (
                        timestamp, run_id, revision, type, data_json
                    ) VALUES (?, ?, ?, 'snapshot_recovered', ?)
                    """,
                    (
                        repaired.updated_at,
                        repaired.run_id,
                        repaired.revision,
                        self._serialize(
                            {
                                "checkpoint_revision": recovered_from_revision,
                                "corrupt_current_revision": current_revision,
                            }
                        ),
                    ),
                )
                self._prune_checkpoints(connection, repaired.run_id)
            connection.commit()
            return repaired
        except BaseException:
            connection.rollback()
            raise

    @staticmethod
    def _replace_task_index(connection: sqlite3.Connection, state: RunState) -> None:
        connection.execute("DELETE FROM task_index WHERE run_id = ?", (state.run_id,))
        connection.executemany(
            """
            INSERT INTO task_index (
                run_id, task_id, status, required, active, priority
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    state.run_id,
                    task.task_id,
                    task.status.value,
                    int(task.required),
                    int(task.active),
                    task.priority,
                )
                for task in state.tasks.values()
            ],
        )

    def _prune_checkpoints(self, connection: sqlite3.Connection, run_id: str) -> None:
        connection.execute(
            """
            DELETE FROM checkpoints
            WHERE run_id = ?
              AND milestone = 0
              AND revision NOT IN (
                  SELECT revision
                  FROM checkpoints
                  WHERE run_id = ? AND milestone = 0
                  ORDER BY revision DESC
                  LIMIT ?
              )
            """,
            (run_id, run_id, self.checkpoint_retention),
        )

    def _try_acquire_lease(
        self,
        run_id: str,
        owner_id: str,
        lease_seconds: float,
    ) -> bool:
        now = time.time()
        with self._transaction() as connection:
            if connection.execute(
                "SELECT 1 FROM runs WHERE run_id = ?",
                (run_id,),
            ).fetchone() is None:
                raise StateRecoveryError(f"unknown run: {run_id}")
            row = connection.execute(
                "SELECT owner_id, expires_at FROM run_leases WHERE run_id = ?",
                (run_id,),
            ).fetchone()
            if row is not None and float(row["expires_at"]) > now:
                return False
            connection.execute(
                """
                INSERT INTO run_leases (
                    run_id, owner_id, process_id, acquired_at, expires_at
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(run_id) DO UPDATE SET
                    owner_id = excluded.owner_id,
                    process_id = excluded.process_id,
                    acquired_at = excluded.acquired_at,
                    expires_at = excluded.expires_at
                """,
                (run_id, owner_id, os.getpid(), now, now + lease_seconds),
            )
            return True

    def _renew_lease(
        self,
        run_id: str,
        owner_id: str,
        lease_seconds: float,
    ) -> None:
        now = time.time()
        with self._transaction() as connection:
            cursor = connection.execute(
                """
                UPDATE run_leases
                SET expires_at = ?
                WHERE run_id = ? AND owner_id = ? AND expires_at > ?
                """,
                (now + lease_seconds, run_id, owner_id, now),
            )
            if cursor.rowcount != 1:
                raise ConcurrentStateError(f"lease ownership changed: {run_id}")

    def _release_lease(self, run_id: str, owner_id: str) -> None:
        with self._transaction() as connection:
            connection.execute(
                "DELETE FROM run_leases WHERE run_id = ? AND owner_id = ?",
                (run_id, owner_id),
            )

    @staticmethod
    def _decode_state(
        raw: str,
        run_id: str,
        failures: list[str],
        source: str,
    ) -> RunState | None:
        try:
            state = RunState.from_dict(json.loads(raw))
            if state.run_id != run_id:
                raise ValueError("run_id mismatch")
            return state
        except Exception as exc:
            failures.append(f"{source}: {type(exc).__name__}: {exc}")
            return None

    @staticmethod
    def _serialize(payload: Mapping[str, Any]) -> str:
        return json.dumps(
            dict(payload),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )

    @staticmethod
    def _normalize_run_id(run_id: str) -> str:
        normalized = str(run_id or "").strip()
        if (
            not normalized
            or normalized in {".", ".."}
            or "/" in normalized
            or "\\" in normalized
            or "\x00" in normalized
        ):
            raise ValueError("invalid run_id")
        return normalized


__all__ = [
    "ConcurrentStateError",
    "LongHorizonStore",
    "StateRecoveryError",
    "StateStore",
]
