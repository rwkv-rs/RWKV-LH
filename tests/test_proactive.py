from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import multiprocessing
import sqlite3
import threading

import pytest

from rwkv_lh.proactive import (
    JobStatus,
    LeaseFenceError,
    ProactiveOutcome,
    ProactiveStore,
    ProactiveWorker,
)


T0 = datetime(2030, 1, 1, tzinfo=timezone.utc)


def test_enqueue_is_idempotent_and_approval_blocks_claim(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    first = store.enqueue(
        {"request": "publish release"},
        due_at=T0,
        idempotency_key="release-42",
        approval_kind="publish_external",
    )
    duplicate = store.enqueue(
        {"request": "must not replace"},
        due_at=T0,
        idempotency_key="release-42",
    )

    assert duplicate.job_id == first.job_id
    assert duplicate.payload == first.payload
    assert first.status == JobStatus.WAITING_APPROVAL
    assert store.claim("worker", now=T0) is None

    approved = store.decide_approval(
        first.approval_id,
        approved=True,
        decided_by="local-user",
    )
    claimed = store.claim("worker", now=T0)
    assert approved.status == JobStatus.QUEUED
    assert claimed is not None
    assert claimed.job_id == first.job_id
    assert claimed.status == JobStatus.RUNNING


def test_expired_lease_is_reclaimed_after_process_loss(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    job = store.enqueue({"request": "resume"}, due_at=T0)
    first = store.claim("worker-1", lease_seconds=10, now=T0)
    assert first is not None
    assert store.claim("worker-2", now=T0 + timedelta(seconds=9)) is None

    recovered = store.claim("worker-2", now=T0 + timedelta(seconds=11))

    assert recovered is not None
    assert recovered.job_id == job.job_id
    assert recovered.lease_owner == "worker-2"
    assert recovered.attempts == 2


def test_only_lease_owner_can_renew_running_job(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    store.enqueue(
        {"request": "long task"},
        due_at=datetime.now(timezone.utc) - timedelta(seconds=1),
    )
    claimed = store.claim("worker-1")
    assert claimed is not None
    assert store.renew_lease(
        claimed.job_id,
        "worker-2",
        lease_generation=claimed.lease_generation,
    ) is False
    assert store.renew_lease(
        claimed.job_id,
        "worker-1",
        lease_generation=claimed.lease_generation,
    ) is True


def test_worker_retries_with_bound_then_dead_letters(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    store.enqueue({"request": "retry"}, due_at=T0, max_attempts=2)

    def unavailable(_job):
        return ProactiveOutcome(False, retryable=True, error="provider unavailable")

    worker = ProactiveWorker(store, unavailable, worker_id="worker", retry_base_seconds=1)
    assert worker.run_once(now=T0) is not None
    assert store.jobs()[0].status == JobStatus.WAITING_RETRY
    assert worker.run_once(now=datetime.now(timezone.utc) + timedelta(seconds=10)) is not None
    assert store.jobs()[0].status == JobStatus.DEAD_LETTER
    assert [item["event_type"] for item in store.notifications()][-1] == "job_dead_lettered"


def test_interval_trigger_materializes_one_idempotent_occurrence(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    trigger_id = store.schedule_interval(
        {"request": "periodic audit"},
        interval_seconds=60,
        first_fire_at=T0,
        trigger_id="TRIGGER-AUDIT",
    )

    first = store.fire_due_triggers(now=T0)
    repeated = store.fire_due_triggers(now=T0)
    claimed = store.claim("worker", now=T0)
    assert claimed is not None
    store.complete(
        claimed.job_id,
        worker_id="worker",
        lease_generation=claimed.lease_generation,
    )
    second = store.fire_due_triggers(now=T0 + timedelta(seconds=60))

    assert trigger_id == "TRIGGER-AUDIT"
    assert len(first) == 1
    assert repeated == ()
    assert len(second) == 1
    assert first[0].job_id != second[0].job_id


def test_concurrent_schedulers_materialize_due_occurrence_once(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    store.schedule_interval(
        {"request": "periodic audit"},
        interval_seconds=60,
        first_fire_at=T0,
        trigger_id="TRIGGER-CONCURRENT",
    )

    with ThreadPoolExecutor(max_workers=2) as executor:
        counts = tuple(
            executor.map(lambda _index: len(store.fire_due_triggers(now=T0)), range(2))
        )

    assert sorted(counts) == [0, 1]
    assert len(store.jobs()) == 1


def test_interval_coalesces_while_prior_occurrence_is_non_terminal(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    store.schedule_interval(
        {"request": "periodic audit"},
        interval_seconds=60,
        first_fire_at=T0,
        trigger_id="TRIGGER-COALESCE",
        concurrency_key="workspace:/audit",
    )

    first = store.fire_due_triggers(now=T0)
    coalesced = store.fire_due_triggers(now=T0 + timedelta(seconds=60))

    assert len(first) == 1
    assert first[0].concurrency_key == "workspace:/audit"
    assert coalesced == ()
    assert len(store.jobs()) == 1
    event = store.notifications()[-1]
    assert event["event_type"] == "trigger_occurrence_coalesced"
    assert event["job_id"] == first[0].job_id
    assert event["payload"] == {
        "active_job_id": first[0].job_id,
        "active_status": "queued",
        "next_fire_at": _iso_for_test(T0 + timedelta(seconds=120)),
        "scheduled_at": _iso_for_test(T0 + timedelta(seconds=60)),
        "trigger_id": "TRIGGER-COALESCE",
    }


def _iso_for_test(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds")


def _hold_process_concurrency_lease(root, entered) -> None:
    store = ProactiveStore(root)
    with store.concurrency_lease("workspace:/shared"):
        entered.set()
        threading.Event().wait(30)


def test_same_concurrency_key_never_has_two_running_leases(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    first = store.enqueue(
        {"request": "first"},
        due_at=T0,
        concurrency_key="workspace:/shared",
    )
    second = store.enqueue(
        {"request": "second"},
        due_at=T0,
        concurrency_key="workspace:/shared",
    )

    claimed = store.claim("worker-1", lease_seconds=30, now=T0)
    blocked = store.claim("worker-2", lease_seconds=30, now=T0)

    assert claimed is not None
    assert claimed.job_id in {first.job_id, second.job_id}
    assert blocked is None
    store.complete(
        claimed.job_id,
        worker_id="worker-1",
        lease_generation=claimed.lease_generation,
    )
    remaining = store.claim("worker-2", lease_seconds=30, now=T0)
    assert remaining is not None
    assert remaining.job_id != claimed.job_id


def test_different_concurrency_keys_can_be_claimed_independently(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    store.enqueue(
        {"request": "left"},
        due_at=T0,
        concurrency_key="workspace:/left",
    )
    store.enqueue(
        {"request": "right"},
        due_at=T0,
        concurrency_key="workspace:/right",
    )

    first = store.claim("worker-1", lease_seconds=30, now=T0)
    second = store.claim("worker-2", lease_seconds=30, now=T0)

    assert first is not None and second is not None
    assert first.job_id != second.job_id
    assert first.concurrency_key != second.concurrency_key


def test_concurrency_lease_excludes_stale_live_handler(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    first_entered = threading.Event()
    release_first = threading.Event()
    second_entered = threading.Event()

    def first_handler_scope() -> None:
        with store.concurrency_lease("workspace:/shared"):
            first_entered.set()
            assert release_first.wait(timeout=5)

    def takeover_handler_scope() -> None:
        assert first_entered.wait(timeout=5)
        with store.concurrency_lease("workspace:/shared"):
            second_entered.set()

    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(first_handler_scope)
        assert first_entered.wait(timeout=5)
        second = executor.submit(takeover_handler_scope)
        assert second_entered.wait(timeout=0.2) is False
        release_first.set()
        first.result(timeout=5)
        second.result(timeout=5)

    assert second_entered.is_set()


def test_concurrency_lease_is_cross_process_and_released_on_death(tmp_path) -> None:
    root = tmp_path / "control"
    store = ProactiveStore(root)
    context = multiprocessing.get_context("fork")
    first_entered = context.Event()
    process = context.Process(
        target=_hold_process_concurrency_lease,
        args=(root, first_entered),
    )
    second_entered = threading.Event()

    def takeover_handler_scope() -> None:
        with store.concurrency_lease("workspace:/shared"):
            second_entered.set()

    process.start()
    try:
        assert first_entered.wait(timeout=5)
        with ThreadPoolExecutor(max_workers=1) as executor:
            takeover = executor.submit(takeover_handler_scope)
            assert second_entered.wait(timeout=0.2) is False
            process.terminate()
            process.join(timeout=5)
            assert process.is_alive() is False
            takeover.result(timeout=5)
    finally:
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

    assert process.exitcode is not None
    assert second_entered.is_set()


def test_proactive_v1_database_migrates_concurrency_columns(tmp_path) -> None:
    root = tmp_path / "control"
    root.mkdir()
    path = root / "proactive.sqlite3"
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE proactive_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            INSERT INTO proactive_meta(key,value)
                VALUES('schema_version','rwkv-lh.proactive.v1');
            CREATE TABLE proactive_triggers (
                trigger_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                payload_json TEXT NOT NULL,
                interval_seconds INTEGER NOT NULL,
                next_fire_at TEXT NOT NULL,
                max_attempts INTEGER NOT NULL,
                approval_kind TEXT NOT NULL DEFAULT '',
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE TABLE proactive_jobs (
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
                lease_owner TEXT NOT NULL DEFAULT '',
                lease_until TEXT NOT NULL DEFAULT '',
                last_error TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )

    store = ProactiveStore(root)
    migrated = store.enqueue(
        {"request": "migrated"},
        due_at=T0,
        concurrency_key="workspace:/migrated",
    )
    with sqlite3.connect(path) as connection:
        version = connection.execute(
            "SELECT value FROM proactive_meta WHERE key='schema_version'"
        ).fetchone()[0]
        trigger_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(proactive_triggers)")
        }
        job_columns = {
            row[1]
            for row in connection.execute("PRAGMA table_info(proactive_jobs)")
        }

    assert version == "rwkv-lh.proactive.v2"
    assert "concurrency_key" in trigger_columns
    assert "concurrency_key" in job_columns
    assert migrated.concurrency_key == "workspace:/migrated"


def test_invalid_terminal_transition_does_not_emit_notification(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    job = store.enqueue({"request": "not claimed"}, due_at=T0)
    before = store.notifications()

    for operation in (
        lambda: store.complete(
            job.job_id, worker_id="worker", lease_generation=0
        ),
        lambda: store.retry(
            job.job_id,
            "invalid",
            worker_id="worker",
            lease_generation=0,
            delay_seconds=1,
        ),
        lambda: store.fail(
            job.job_id, "invalid", worker_id="worker", lease_generation=0
        ),
    ):
        try:
            operation()
        except LeaseFenceError:
            pass
        else:
            raise AssertionError("invalid lifecycle transition was accepted")

    assert store.notifications() == before


def test_takeover_fences_all_late_writes_from_old_worker(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    job = store.enqueue({"request": "fenced"}, due_at=T0)
    first = store.claim("worker-A", lease_seconds=10, now=T0)
    assert first is not None
    second = store.claim("worker-B", lease_seconds=30, now=T0 + timedelta(seconds=11))
    assert second is not None
    assert second.job_id == job.job_id
    assert second.lease_generation > first.lease_generation
    before = store.notifications()

    stale_writes = (
        lambda: store.bind_run(
            job.job_id,
            "RUN-STALE",
            worker_id="worker-A",
            lease_generation=first.lease_generation,
        ),
        lambda: store.complete(
            job.job_id,
            worker_id="worker-A",
            lease_generation=first.lease_generation,
            run_id="RUN-STALE",
        ),
        lambda: store.retry(
            job.job_id,
            "stale",
            worker_id="worker-A",
            lease_generation=first.lease_generation,
            delay_seconds=1,
        ),
        lambda: store.fail(
            job.job_id,
            "stale",
            worker_id="worker-A",
            lease_generation=first.lease_generation,
        ),
    )
    for operation in stale_writes:
        with pytest.raises(LeaseFenceError):
            operation()

    assert store.notifications() == before
    store.complete(
        job.job_id,
        worker_id="worker-B",
        lease_generation=second.lease_generation,
        run_id="RUN-CURRENT",
    )
    persisted = store.jobs()[0]
    assert persisted.status == JobStatus.COMPLETED
    assert persisted.run_id == "RUN-CURRENT"


def test_expired_lease_cannot_commit_before_takeover(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    past = datetime.now(timezone.utc) - timedelta(seconds=30)
    job = store.enqueue({"request": "expired"}, due_at=past)
    claimed = store.claim("worker-A", lease_seconds=10, now=past)
    assert claimed is not None

    with pytest.raises(LeaseFenceError):
        store.complete(
            job.job_id,
            worker_id="worker-A",
            lease_generation=claimed.lease_generation,
        )

    assert store.jobs()[0].status == JobStatus.RUNNING


def test_worker_binds_run_and_completes_job(tmp_path) -> None:
    store = ProactiveStore(tmp_path / "control")
    job = store.enqueue({"request": "do work"}, due_at=T0)
    worker = ProactiveWorker(
        store,
        lambda _job: ProactiveOutcome(True, run_id="RUN-42"),
        worker_id="worker",
    )

    worker.run_once(now=T0)

    persisted = store.jobs()[0]
    assert persisted.job_id == job.job_id
    assert persisted.status == JobStatus.COMPLETED
    assert persisted.run_id == "RUN-42"
