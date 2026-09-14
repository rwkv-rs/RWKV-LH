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
from types import SimpleNamespace

import pytest

from rwkv_lh.schema import CausalEventDraft, GoalState, RunState, RunStatus
from rwkv_lh.store import LongHorizonStore
from rwkv_lh.web_ui import (
    ManualRunRepository,
    build_server,
    normalize_relative_path,
)
from rwkv_lh.web_worker import result_payload, run as run_web_worker


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
    assert request["execution_mode"] == "goal"
    assert request["seed_files"][0]["sha256"]
    assert (repository.run_root(metadata["run_id"]) / "workspace/input.txt").read_text() == "alpha\n"


def test_manual_repository_rejects_retired_architecture_selection(tmp_path: Path) -> None:
    repository = ManualRunRepository(tmp_path)
    with pytest.raises(ValueError, match="retired"):
        repository.create(
            {"request": "test", "state_router_shadow": True, "seed_files": []}
        )
    with pytest.raises(ValueError, match="direct_rwkv"):
        repository.create(
            {"request": "test", "supervisor_mode": "contract_graph"}
        )


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


def test_direct_worker_uses_shared_loop_and_preserves_answer(tmp_path, monkeypatch):
    from rwkv_lh import web_worker
    from test_read_only_agent import factory
    from test_unified_controller import call, settings
    repository, metadata = create_repository_run(tmp_path, "UI-DIRECT")
    root = repository.run_root(metadata["run_id"])
    monkeypatch.setattr(web_worker, "direct_settings", settings)
    monkeypatch.setattr(web_worker, "create_model_session", factory([
        call("read_file", path="input.txt"),
        call("final_answer", text="  原始回答\n"),
    ]))
    assert run_web_worker(root, resume=False, max_transitions=2) == 0
    summary = repository.summary(metadata["run_id"])
    assert summary["result"]["final_output"] == "  原始回答\n"
    assert summary["result"]["acceptance"] == "not_evaluated"
    assert summary["result"]["generation_started"] == 2
    assert repository.trace(metadata["run_id"])["total"] > 0
    assert repository.events(metadata["run_id"])["events"]
    assert summary["state"]["actions"][0]["operation"] == "read_file"


def test_direct_worker_budget_stops_without_forced_answer(tmp_path, monkeypatch):
    from rwkv_lh import web_worker
    from test_read_only_agent import factory
    from test_unified_controller import call, settings
    repository, metadata = create_repository_run(tmp_path, "UI-BUDGET")
    root = repository.run_root(metadata["run_id"])
    monkeypatch.setattr(web_worker, "direct_settings", settings)
    monkeypatch.setattr(web_worker, "create_model_session", factory([call("read_file", path="input.txt")]))
    assert run_web_worker(root, resume=False, max_transitions=1) == 1
    result = repository.summary(metadata["run_id"])["result"]
    assert result["final_output"] is None
    assert result["termination"] == "budget"
    assert repository.metadata(metadata["run_id"])["status"] == "interrupted"
    with pytest.raises(ValueError, match="resume"):
        run_web_worker(root, resume=True, max_transitions=1)


def test_frontend_defaults_direct_and_rejects_unsupported_scope(tmp_path):
    repository, metadata = create_repository_run(tmp_path)
    request = repository.request_document(metadata["run_id"])
    assert request["runtime"] == "direct_rwkv"
    assert request["tool_scope"] == "files"
    assert request["max_seconds"] == 300
    with pytest.raises(ValueError, match="tool_scope"):
        repository.create({"request": "test", "tool_scope": "invented"})


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
        assert capabilities["latest_formal"] is None
        assert capabilities["latest_diagnostic"] is None
        assert capabilities["validation_status"] == "fixed_task_diagnostics_only"
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
        assert summary["request"]["retrieval_policy"]["mode"] == "offline"
        assert Path(summary["request"]["run_id"]).name == run_id
        assert repository.run_root(run_id).parent == (tmp_path / "runs").resolve()
        status, missing = request_json(
            base + f"/api/runs/{run_id}/stop",
            method="POST",
            payload={},
        )
        assert status == 404
        assert missing["error"] == "not found"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_browser_direct_demo_submission_and_raw_result(tmp_path, monkeypatch):
    from playwright.sync_api import sync_playwright, expect
    from rwkv_lh import web_worker
    from test_read_only_agent import factory
    from test_unified_controller import call, settings
    server = build_server('127.0.0.1', 0, tmp_path)
    fake = FakeManager(server.repository)
    server.manager = fake
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    monkeypatch.setattr(web_worker, 'direct_settings', settings)
    monkeypatch.setattr(web_worker, 'create_model_session', factory([
        call('read_file', path='verify_public.py'),
        call('final_answer', text='  仅健康检查，不证明事务。\n'),
    ]))
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/api/runtime/topology', lambda route: route.fulfill(
                json={'executor': {'available': True, 'model': 'test'}, 'harness': {'available': True}}))
            page.goto(f'http://127.0.0.1:{server.server_port}')
            page.locator('[data-demo="read-health"]').click()
            expect(page.locator('.seed-path')).to_have_value('verify_public.py')
            expect(page.locator('#toolScope')).to_have_value('files')
            page.locator('#startButton').click()
            expect(page.locator('#runView')).to_be_visible()
            run_id = fake.launched[0]
            assert run_web_worker(server.repository.run_root(run_id), resume=False, max_transitions=2) == 0
            page.evaluate('pollRun()')
            expect(page.locator('#finalOutput')).to_have_text('  仅健康检查，不证明事务。\n', use_inner_text=False)
            assert page.locator('#finalOutput').text_content() == '  仅健康检查，不证明事务。\n'
            expect(page.locator('#runStatus')).to_have_text('submitted')
            expect(page.locator('#acceptanceBadge')).to_have_text('未进行外部验收')
            expect(page.locator('#resumeButton')).to_be_hidden()
            page.locator('[data-tab="execution"]').click()
            expect(page.locator('#actionList')).to_contain_text('read_file')
            with page.expect_download() as download_info:
                page.locator('#exportButton').click()
            download_info.value.save_as(tmp_path / 'browser-audit.zip')
            history = page.locator('#runList').bounding_box()
            item = page.locator('.run-item').first.bounding_box()
            assert item['width'] <= history['width']
            # Switching task IDs must not temporarily attach the previous
            # answer to the new identity while its response is delayed.
            server.repository.create({'run_id': 'UI-NEXT', 'request': 'A different task'})
            page.evaluate('loadRuns()')
            pending = []
            page.route('**/api/runs/UI-NEXT', lambda route: pending.append(route))
            page.locator('[data-run-id="UI-NEXT"]').click()
            expect(page.locator('#runId')).to_have_text('UI-NEXT')
            expect(page.locator('#finalOutput')).not_to_contain_text('仅健康检查', timeout=1000)
            expect(page.locator('#runStatus')).not_to_have_text('submitted', timeout=1000)
            for route in pending:
                route.abort()
            assert not errors
            browser.close()
    finally:
        server.shutdown(); server.server_close(); thread.join(timeout=5)


def test_direct_coding_worker_serves_modified_copy_and_exports_state(tmp_path, monkeypatch):
    from rwkv_lh import web_worker
    from test_read_only_agent import factory
    from test_unified_controller import call, settings
    repository = ManualRunRepository(tmp_path)
    metadata = repository.create({'request': 'write output', 'tool_scope': 'coding'})
    run_id = metadata['run_id']
    monkeypatch.setattr(web_worker, 'direct_settings', settings)
    monkeypatch.setattr(web_worker, 'create_model_session', factory([
        call('write_file', path='out.txt', content='delivered'), call('final_answer', text='written')]))
    assert run_web_worker(repository.run_root(run_id), resume=False, max_transitions=2) == 0
    assert repository.file_bytes(run_id, 'out.txt')[0] == b'delivered'
    assert not (repository.run_root(run_id) / 'workspace/out.txt').exists()
    assert repository.trace(run_id)['total'] > 0
    archive = zipfile.ZipFile(io.BytesIO(repository.export_zip(run_id)))
    assert f'{run_id}/delivery/execution/state/long_horizon.db' in archive.namelist()
    assert f'{run_id}/state-export.json' in archive.namelist()
