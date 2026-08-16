from __future__ import annotations

import io
import json
import sqlite3
import threading
import urllib.error
import urllib.request
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from rwkv_lh.schema import GoalState, RunState
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.web_ui import (
    ManualRunRepository,
    build_server,
    normalize_relative_path,
)
from rwkv_lh.web_worker import result_payload


def create_repository_run(root: Path, run_id: str = "UI-TEST") -> tuple[ManualRunRepository, dict]:
    repository = ManualRunRepository(root)
    metadata = repository.create(
        {
            "run_id": run_id,
            "request": "Read input.txt and create result.txt.",
            "constraints": ["Do not access files outside the workspace."],
            "max_transitions": 20,
            "seed_files": [{"path": "input.txt", "content": "alpha\n"}],
        }
    )
    return repository, metadata


def test_manual_repository_records_source_version_purpose_and_seed_hash(tmp_path: Path) -> None:
    repository, metadata = create_repository_run(tmp_path)
    request = repository.request_document(metadata["run_id"])
    assert request["source"] == "local web UI user input"
    assert request["version"] == "manual-v1"
    assert "transparent" in request["purpose"]
    assert request["seed_files"][0]["sha256"]
    assert (repository.run_root(metadata["run_id"]) / "workspace/input.txt").read_text() == "alpha\n"


@pytest.mark.parametrize("value", ["../secret", "/etc/passwd", "a/../../b", "", "C:\\secret"])
def test_workspace_relative_path_rejects_escape(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_relative_path(value)


def test_manual_repository_rejects_duplicate_or_oversized_seed_files(tmp_path: Path) -> None:
    repository = ManualRunRepository(tmp_path)
    with pytest.raises(ValueError, match="duplicate"):
        repository.create(
            {
                "request": "test",
                "seed_files": [
                    {"path": "same.txt", "content": "a"},
                    {"path": "same.txt", "content": "b"},
                ],
            }
        )
    with pytest.raises(ValueError, match="5 MiB"):
        repository.create(
            {"request": "test", "seed_files": [{"path": "huge.txt", "content": "x" * (5 * 1024 * 1024 + 1)}]}
        )


def test_result_payload_preserves_controller_final_output_exactly(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    goal = GoalState.create(
        request="Preserve output",
        constraints=[],
        workspace_root=workspace,
    )
    state = RunState(run_id="UI-OUTPUT", goal=goal)
    raw = "  RWKV 原始输出\n```json\n{\"x\":1}\n```\n\u0000tail  "
    state.final_output = raw
    payload = result_payload(state, raw, 4)
    assert payload["final_output"] == raw
    assert payload["persisted_final_output"] == raw
    assert payload["final_output_matches_persisted_rwkv"] is True


def test_export_contains_consistent_sqlite_snapshot_and_full_state_exports(tmp_path: Path) -> None:
    repository, metadata = create_repository_run(tmp_path, "UI-EXPORT")
    run_root = repository.run_root(metadata["run_id"])
    goal = GoalState.create(
        request="Export state",
        constraints=[],
        workspace_root=run_root / "workspace",
    )
    store = LongHorizonStore(run_root / "state", checkpoint_retention=100_000)
    store.create_run(goal, metadata["run_id"])
    from rwkv_lh.web_ui import update_metadata

    update_metadata(run_root, state_created=True)
    archive = zipfile.ZipFile(io.BytesIO(repository.export_zip(metadata["run_id"])))
    names = set(archive.namelist())
    assert "UI-EXPORT/state/long_horizon.db" in names
    assert "UI-EXPORT/state-export.json" in names
    assert "UI-EXPORT/events-export.json" in names
    snapshot = tmp_path / "snapshot.db"
    snapshot.write_bytes(archive.read("UI-EXPORT/state/long_horizon.db"))
    with sqlite3.connect(snapshot) as connection:
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        assert connection.execute("SELECT COUNT(*) FROM runs").fetchone()[0] == 1


@dataclass
class FakeManager:
    repository: ManualRunRepository
    launched: list[str] = field(default_factory=list)

    def refresh_metadata(self, run_id: str) -> dict:
        return self.repository.metadata(run_id)

    def launch(self, run_id: str, *, resume: bool = False) -> dict:
        self.launched.append(run_id)
        return self.repository.metadata(run_id)

    def stop(self, run_id: str) -> dict:
        return self.repository.metadata(run_id)


def request_json(url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
    body = json.dumps(payload).encode() if payload is not None else None
    request = urllib.request.Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        response = urllib.request.urlopen(request, timeout=5)
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read())
    return response.status, json.loads(response.read())


def test_http_api_serves_ui_capabilities_and_creates_scoped_run_without_model(tmp_path: Path) -> None:
    repository = ManualRunRepository(tmp_path)
    server = build_server("127.0.0.1", 0, tmp_path)
    fake = FakeManager(repository)
    server.repository = repository
    server.manager = fake  # type: ignore[assignment]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        status, capabilities = request_json(base + "/api/capabilities")
        assert status == 200
        assert capabilities["latest_formal"]["strict"] == "31/90"
        assert capabilities["experimental"] is True
        status, created = request_json(
            base + "/api/runs",
            method="POST",
            payload={"request": "Create hello.txt", "seed_files": []},
        )
        assert status == 201
        run_id = created["run"]["run_id"]
        assert fake.launched == [run_id]
        status, summary = request_json(base + f"/api/runs/{run_id}")
        assert status == 200
        assert summary["request"]["request"] == "Create hello.txt"
        assert Path(summary["request"]["run_id"]).name == run_id
        assert repository.run_root(run_id).parent == (tmp_path / "runs").resolve()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
