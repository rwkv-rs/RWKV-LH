"""Local, dependency-free web UI for transparent RWKV-LH manual runs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import mimetypes
import os
import re
import secrets
import signal
import sqlite3
import subprocess
import sys
import threading
import zipfile
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import parse_qs, unquote, urlparse

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.runtime.settings import PROJECT_ROOT, get_runtime_settings
from rwkv_lh.store import LongHorizonStore, StateRecoveryError


SCHEMA_VERSION = "rwkv-lh.manual-web-run.v1"
ASSET_ROOT = Path(__file__).resolve().parent / "web_assets"
RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")
TERMINAL_PHASES = {"finished", "failed", "stopped"}
MAX_REQUEST_BYTES = 6 * 1024 * 1024
MAX_SEED_BYTES = 5 * 1024 * 1024
MAX_TEXT_PREVIEW_BYTES = 1024 * 1024


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def read_json(path: Path, default: Any = None) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.{secrets.token_hex(4)}.tmp")
    temporary.write_text(
        json.dumps(dict(payload), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(temporary, path)


def update_metadata(run_root: Path, **changes: Any) -> dict[str, Any]:
    path = run_root / "metadata.json"
    current = read_json(path, {})
    if not isinstance(current, dict):
        current = {}
    current.update(changes)
    current["updated_at"] = utc_now()
    atomic_write_json(path, current)
    return current


def normalize_run_id(value: str) -> str:
    run_id = str(value or "").strip()
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise ValueError("run_id must use 1-100 ASCII letters, digits, dot, underscore, or dash")
    return run_id


def normalize_relative_path(value: str) -> Path:
    raw = str(value or "").replace("\\", "/").strip()
    relative = Path(raw)
    if (
        not raw
        or relative.is_absolute()
        or re.match(r"^[A-Za-z]:/", raw)
        or ".." in relative.parts
        or "\x00" in raw
    ):
        raise ValueError("file path must be a non-empty workspace-relative path")
    return relative


def within(root: Path, relative: Path) -> Path:
    resolved_root = root.resolve()
    candidate = (resolved_root / relative).resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("path escapes the managed workspace") from exc
    return candidate


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ManualRunRepository:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.runs_root = self.root / "runs"
        self.runs_root.mkdir(parents=True, exist_ok=True)

    def run_root(self, run_id: str) -> Path:
        return self.runs_root / normalize_run_id(run_id)

    def create(self, payload: Mapping[str, Any]) -> dict[str, Any]:
        request = str(payload.get("request") or "").strip()
        if not request:
            raise ValueError("request must not be empty")
        if len(request) > 100_000:
            raise ValueError("request exceeds 100,000 characters")
        raw_constraints = payload.get("constraints") or []
        if not isinstance(raw_constraints, list) or len(raw_constraints) > 32:
            raise ValueError("constraints must be an array with at most 32 items")
        constraints = [str(item).strip() for item in raw_constraints if str(item).strip()]
        if any(len(item) > 5_000 for item in constraints):
            raise ValueError("one constraint exceeds 5,000 characters")
        try:
            max_transitions = int(payload.get("max_transitions", 200))
        except (TypeError, ValueError) as exc:
            raise ValueError("max_transitions must be an integer") from exc
        if not 1 <= max_transitions <= 500:
            raise ValueError("max_transitions must be between 1 and 500")
        raw_seed_files = payload.get("seed_files") or []
        if not isinstance(raw_seed_files, list) or len(raw_seed_files) > 100:
            raise ValueError("seed_files must be an array with at most 100 items")
        seed_files: list[dict[str, str]] = []
        total_seed_bytes = 0
        seen_paths: set[str] = set()
        for item in raw_seed_files:
            if not isinstance(item, Mapping):
                raise ValueError("every seed file must be an object")
            relative = normalize_relative_path(str(item.get("path") or ""))
            normalized_path = relative.as_posix()
            if normalized_path in seen_paths:
                raise ValueError(f"duplicate seed file path: {normalized_path}")
            seen_paths.add(normalized_path)
            content = str(item.get("content") or "")
            total_seed_bytes += len(content.encode("utf-8"))
            seed_files.append({"path": normalized_path, "content": content})
        if total_seed_bytes > MAX_SEED_BYTES:
            raise ValueError("seed file content exceeds 5 MiB")

        supplied_id = str(payload.get("run_id") or "").strip()
        run_id = normalize_run_id(supplied_id) if supplied_id else self.new_run_id()
        run_root = self.run_root(run_id)
        run_root.mkdir(parents=False, exist_ok=False)
        workspace = run_root / "workspace"
        workspace.mkdir()
        (run_root / "state").mkdir()
        for item in seed_files:
            target = within(workspace, Path(item["path"]))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item["content"], encoding="utf-8")
        request_document = {
            "schema_version": SCHEMA_VERSION,
            "source": "local web UI user input",
            "version": "manual-v1",
            "purpose": "Run one transparent, workspace-scoped RWKV-LH manual test.",
            "generated_at": utc_now(),
            "run_id": run_id,
            "request": request,
            "constraints": constraints,
            "max_transitions": max_transitions,
            "seed_files": [
                {
                    "path": item["path"],
                    "size_bytes": len(item["content"].encode("utf-8")),
                    "sha256": hashlib.sha256(item["content"].encode("utf-8")).hexdigest(),
                }
                for item in seed_files
            ],
        }
        atomic_write_json(run_root / "request.json", request_document)
        metadata = {
            "schema_version": SCHEMA_VERSION,
            "run_id": run_id,
            "created_at": utc_now(),
            "updated_at": utc_now(),
            "phase": "queued",
            "active": False,
            "pid": None,
            "resume_count": 0,
            "request_preview": request[:240],
            "max_transitions": max_transitions,
            "state_created": False,
            "error": "",
        }
        atomic_write_json(run_root / "metadata.json", metadata)
        return metadata

    @staticmethod
    def new_run_id() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        return f"UI-{stamp}-{secrets.token_hex(3)}"

    def list_runs(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for path in self.runs_root.iterdir():
            if not path.is_dir() or not RUN_ID_PATTERN.fullmatch(path.name):
                continue
            metadata = read_json(path / "metadata.json", {})
            if isinstance(metadata, dict) and metadata:
                rows.append(metadata)
        rows.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return rows

    def metadata(self, run_id: str) -> dict[str, Any]:
        path = self.run_root(run_id) / "metadata.json"
        metadata = read_json(path)
        if not isinstance(metadata, dict):
            raise FileNotFoundError(f"unknown run: {run_id}")
        return metadata

    def request_document(self, run_id: str) -> dict[str, Any]:
        document = read_json(self.run_root(run_id) / "request.json")
        if not isinstance(document, dict):
            raise FileNotFoundError(f"request document missing: {run_id}")
        return document

    def store(self, run_id: str) -> LongHorizonStore:
        return LongHorizonStore(self.run_root(run_id) / "state", checkpoint_retention=100_000)

    def summary(self, run_id: str) -> dict[str, Any]:
        metadata = self.metadata(run_id)
        output: dict[str, Any] = {"metadata": metadata, "request": self.request_document(run_id)}
        if metadata.get("state_created"):
            try:
                state = self.store(run_id).load(run_id)
            except StateRecoveryError as exc:
                output["state_error"] = f"{type(exc).__name__}: {exc}"
            else:
                output["state"] = {
                    "run_id": state.run_id,
                    "revision": state.revision,
                    "status": state.status.value,
                    "request": state.goal.request,
                    "goal_digest": state.goal.digest,
                    "actions": [
                        {
                            "action_id": action.action_id,
                            "sequence": action.sequence,
                            "operation": action.action_type,
                            "status": action.status.value,
                            "artifact_refs": list(action.artifact_refs),
                        }
                        for action in sorted(
                            state.actions.values(), key=lambda item: item.sequence
                        )
                    ],
                    "artifact_count": len(state.artifacts),
                    "causal_record_count": len(state.causal_order),
                    "model_request_count": len(state.temp_decisions),
                    "errors": state.errors[-8:],
                    "final_output": state.final_output,
                }
        result = read_json(self.run_root(run_id) / "result.json")
        if isinstance(result, dict):
            output["result"] = result
        return output

    def full_state(self, run_id: str) -> dict[str, Any]:
        metadata = self.metadata(run_id)
        if not metadata.get("state_created"):
            return {"run_id": run_id, "state": None}
        return {"run_id": run_id, "state": self.store(run_id).load(run_id).to_dict()}

    def events(self, run_id: str, *, after: int = 0, limit: int = 500) -> dict[str, Any]:
        metadata = self.metadata(run_id)
        if not metadata.get("state_created"):
            return {"events": [], "last_event_id": after}
        records = [
            item for item in self.store(run_id).event_records(run_id) if int(item["event_id"]) > after
        ][: max(1, min(limit, 2_000))]
        return {
            "events": records,
            "last_event_id": int(records[-1]["event_id"]) if records else after,
        }

    def trace(self, run_id: str, *, after: int = 0, limit: int = 300) -> dict[str, Any]:
        self.metadata(run_id)
        path = self.run_root(run_id) / "model_trace.jsonl"
        if not path.is_file():
            return {"events": [], "next_offset": after, "total": 0}
        lines = path.read_text(encoding="utf-8").splitlines()
        start = max(0, int(after))
        selected = lines[start : start + max(1, min(limit, 1_000))]
        records = []
        for line in selected:
            try:
                value = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                records.append(value)
        return {"events": records, "next_offset": start + len(selected), "total": len(lines)}

    def files(self, run_id: str) -> list[dict[str, Any]]:
        self.metadata(run_id)
        workspace = self.run_root(run_id) / "workspace"
        rows = []
        for path in sorted(workspace.rglob("*")):
            if not path.is_file() or path.is_symlink():
                continue
            relative = path.relative_to(workspace).as_posix()
            rows.append(
                {
                    "path": relative,
                    "size_bytes": path.stat().st_size,
                    "sha256": file_sha256(path),
                    "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                }
            )
        return rows

    def file_bytes(self, run_id: str, relative_value: str) -> tuple[bytes, str]:
        self.metadata(run_id)
        workspace = self.run_root(run_id) / "workspace"
        path = within(workspace, normalize_relative_path(relative_value))
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(relative_value)
        return path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream"

    def export_zip(self, run_id: str) -> bytes:
        run_root = self.run_root(run_id)
        self.metadata(run_id)
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(run_root.rglob("*")):
                if (
                    not path.is_file()
                    or path.is_symlink()
                    or path.name == "long_horizon.db"
                    or path.name.endswith(("-wal", "-shm"))
                ):
                    continue
                archive.write(path, arcname=f"{run_id}/{path.relative_to(run_root).as_posix()}")
            database = run_root / "state" / "long_horizon.db"
            if database.is_file():
                source = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
                snapshot = sqlite3.connect(":memory:")
                try:
                    source.backup(snapshot)
                    archive.writestr(
                        f"{run_id}/state/long_horizon.db",
                        snapshot.serialize(),
                    )
                    state = self.store(run_id).load(run_id)
                    archive.writestr(
                        f"{run_id}/state-export.json",
                        json.dumps(state.to_dict(), ensure_ascii=False, indent=2) + "\n",
                    )
                    archive.writestr(
                        f"{run_id}/events-export.json",
                        json.dumps(self.store(run_id).event_records(run_id), ensure_ascii=False, indent=2)
                        + "\n",
                    )
                except StateRecoveryError:
                    pass
                finally:
                    snapshot.close()
                    source.close()
        return buffer.getvalue()


class ManualRunManager:
    def __init__(self, repository: ManualRunRepository):
        self.repository = repository
        self._processes: dict[str, subprocess.Popen[bytes]] = {}
        self._lock = threading.Lock()

    def launch(self, run_id: str, *, resume: bool = False) -> dict[str, Any]:
        metadata = self.repository.metadata(run_id)
        with self._lock:
            process = self._processes.get(run_id)
            if process is not None and process.poll() is None:
                raise RuntimeError("run is already active")
            run_root = self.repository.run_root(run_id)
            request = self.repository.request_document(run_id)
            update_metadata(
                run_root,
                active=True,
                phase="resuming" if resume else "starting",
                pid=None,
                error="",
                resume_count=int(metadata.get("resume_count", 0)) + int(resume),
            )
            log = (run_root / "worker.log").open("ab", buffering=0)
            command = [
                sys.executable,
                "-m",
                "rwkv_lh.web_worker",
                "--run-root",
                str(run_root),
                "--max-transitions",
                str(int(request["max_transitions"])),
            ]
            if resume:
                command.append("--resume")
            process = subprocess.Popen(
                command,
                cwd=str(PROJECT_ROOT),
                env=os.environ.copy(),
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            log.close()
            self._processes[run_id] = process
        current = self.repository.metadata(run_id)
        if current.get("phase") not in TERMINAL_PHASES:
            return update_metadata(
                self.repository.run_root(run_id),
                active=True,
                pid=process.pid,
            )
        return current

    def active(self, run_id: str) -> bool:
        with self._lock:
            process = self._processes.get(run_id)
            if process is not None:
                return process.poll() is None
        metadata = self.repository.metadata(run_id)
        return self._managed_pid_alive(run_id, metadata.get("pid"))

    def _managed_pid_alive(self, run_id: str, raw_pid: Any) -> bool:
        try:
            pid = int(raw_pid)
        except (TypeError, ValueError):
            return False
        if pid < 2:
            return False
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes().replace(b"\x00", b" ").decode(
                "utf-8", errors="replace"
            )
        except OSError:
            return False
        expected_root = str(self.repository.run_root(run_id))
        return "rwkv_lh.web_worker" in command and expected_root in command

    def stop(self, run_id: str) -> dict[str, Any]:
        metadata = self.repository.metadata(run_id)
        with self._lock:
            process = self._processes.get(run_id)
            if process is not None and process.poll() is None:
                pid = process.pid
            elif self._managed_pid_alive(run_id, metadata.get("pid")):
                pid = int(metadata["pid"])
            else:
                raise RuntimeError("run is not active")
            os.killpg(pid, signal.SIGTERM)
        return update_metadata(
            self.repository.run_root(run_id),
            active=False,
            phase="stopped",
            pid=None,
            stopped_at=utc_now(),
        )

    def refresh_metadata(self, run_id: str) -> dict[str, Any]:
        metadata = self.repository.metadata(run_id)
        with self._lock:
            process = self._processes.get(run_id)
            if process is not None:
                code = process.poll()
                if code is not None and metadata.get("active"):
                    phase = metadata.get("phase")
                    if phase not in TERMINAL_PHASES:
                        metadata = update_metadata(
                            self.repository.run_root(run_id),
                            active=False,
                            pid=None,
                            phase="finished" if code == 0 else "failed",
                            exit_code=code,
                        )
            elif metadata.get("active") and not self._managed_pid_alive(
                run_id, metadata.get("pid")
            ):
                metadata = update_metadata(
                    self.repository.run_root(run_id),
                    active=False,
                    pid=None,
                    phase="failed",
                    error="manual UI worker process is no longer present",
                )
        return metadata


class WebServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(
        self,
        server_address: tuple[str, int],
        handler: type[BaseHTTPRequestHandler],
        repository: ManualRunRepository,
        manager: ManualRunManager,
    ):
        super().__init__(server_address, handler)
        self.repository = repository
        self.manager = manager


class WebHandler(BaseHTTPRequestHandler):
    server: WebServer
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        sys.stderr.write(f"{self.log_date_time_string()} {format % args}\n")

    def _headers(self, status: int, media_type: str, length: int, **extra: str) -> None:
        self.send_response(status)
        self.send_header("Content-Type", media_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
        for key, value in extra.items():
            self.send_header(key.replace("_", "-"), value)
        self.end_headers()

    def send_bytes(self, body: bytes, media_type: str, status: int = 200, **headers: str) -> None:
        self._headers(status, media_type, len(body), **headers)
        self.wfile.write(body)

    def send_json(self, payload: Any, status: int = 200) -> None:
        self.send_bytes(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            "application/json; charset=utf-8",
            status,
        )

    def send_error_json(self, status: int, message: str) -> None:
        self.send_json({"error": message}, status)

    def read_body_json(self) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("invalid Content-Length") from exc
        if length < 1 or length > MAX_REQUEST_BYTES:
            raise ValueError("request body must be between 1 byte and 6 MiB")
        raw = self.rfile.read(length)
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSON request body must be an object")
        return value

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        path = parsed.path
        try:
            if path == "/api/capabilities":
                settings = get_runtime_settings()
                self.send_json(
                    {
                        "product": "RWKV-LH Local Lab",
                        "experimental": True,
                        "runtime": {
                            "model": settings.model,
                            "endpoint": settings.base_url,
                            "backend_profile": settings.backend_profile,
                            "max_model_len": settings.max_model_len,
                        },
                        "can": [
                            "曾完整做过：创建精确文本文件并检查内容",
                            "曾完整做过：修改 JSON 指定字段，同时保留无关字段",
                            "曾完整做过：筛选、排序、合并本地 JSON 数据并写出结果",
                            "曾完整做过：计算本地文件 SHA-256，并生成 manifest",
                            "曾完整做过：复制文件、建立子目录和配套清单",
                            "可以尝试：在隔离工作区内修改小型代码或配置，并运行受限检查命令",
                            "可以审计：查看每次模型输入、原始输出、格式转换、文件变化和失败位置",
                        ],
                        "cannot": [
                            "不能像成熟 Coding Agent 一样稳定完成仓库级开发；最新已上传 Strict 是 31/90",
                            "不能搜索网页、操作浏览器、调用外部网站或自动研究资料",
                            "不能直接管理真实 Git 仓库、提交、PR、部署或云服务",
                            "不能处理图片、PDF、Word、Excel、幻灯片等专用文档工作流",
                            "不能安装系统软件，也不能任意执行 shell 或访问隔离工作区外文件",
                            "不能在运行中向用户追问并根据新回答继续多轮协作",
                            "不能用其他模型替 RWKV 修复协议、判断答案或改写最终输出",
                        ],
                        "latest_formal": {
                            "round": "Round46",
                            "strict": "31/90",
                            "external": "32/90",
                            "false_positive": 24,
                            "false_negative": 1,
                        },
                    }
                )
                return
            if path == "/api/runtime/health":
                client = OpenAICompatibleRWKVClient()
                try:
                    health = client.health().to_dict()
                finally:
                    client.close()
                self.send_json(health)
                return
            if path == "/api/runs":
                rows = []
                for item in self.server.repository.list_runs():
                    rows.append(self.server.manager.refresh_metadata(str(item["run_id"])))
                self.send_json({"runs": rows})
                return
            match = re.fullmatch(r"/api/runs/([^/]+)(?:/(.*))?", path)
            if match:
                run_id = normalize_run_id(unquote(match.group(1)))
                suffix = match.group(2) or ""
                self.server.manager.refresh_metadata(run_id)
                query = parse_qs(parsed.query)
                if not suffix:
                    self.send_json(self.server.repository.summary(run_id))
                elif suffix == "state":
                    self.send_json(self.server.repository.full_state(run_id))
                elif suffix == "events":
                    self.send_json(
                        self.server.repository.events(
                            run_id,
                            after=int(query.get("after", ["0"])[0]),
                            limit=int(query.get("limit", ["500"])[0]),
                        )
                    )
                elif suffix == "trace":
                    self.send_json(
                        self.server.repository.trace(
                            run_id,
                            after=int(query.get("after", ["0"])[0]),
                            limit=int(query.get("limit", ["300"])[0]),
                        )
                    )
                elif suffix == "files":
                    self.send_json({"files": self.server.repository.files(run_id)})
                elif suffix.startswith("file/"):
                    body, media_type = self.server.repository.file_bytes(
                        run_id, unquote(suffix.removeprefix("file/"))
                    )
                    self.send_bytes(body, media_type)
                elif suffix == "export":
                    body = self.server.repository.export_zip(run_id)
                    self.send_bytes(
                        body,
                        "application/zip",
                        Content_Disposition=f'attachment; filename="{run_id}-audit.zip"',
                    )
                else:
                    self.send_error_json(404, "unknown run resource")
                return
            if path in {"/", "/index.html"}:
                self.send_asset("index.html")
                return
            if path.startswith("/assets/"):
                self.send_asset(path.removeprefix("/assets/"))
                return
            self.send_error_json(404, "not found")
        except FileNotFoundError as exc:
            self.send_error_json(404, str(exc))
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error_json(400, str(exc))
        except Exception as exc:
            self.send_error_json(500, f"{type(exc).__name__}: {exc}"[:500])

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        try:
            if path == "/api/runs":
                metadata = self.server.repository.create(self.read_body_json())
                launched = self.server.manager.launch(str(metadata["run_id"]))
                self.send_json({"run": launched}, HTTPStatus.CREATED)
                return
            match = re.fullmatch(r"/api/runs/([^/]+)/(resume|stop)", path)
            if not match:
                self.send_error_json(404, "not found")
                return
            run_id = normalize_run_id(unquote(match.group(1)))
            action = match.group(2)
            if action == "resume":
                self.send_json({"run": self.server.manager.launch(run_id, resume=True)})
            else:
                self.send_json({"run": self.server.manager.stop(run_id)})
        except FileNotFoundError as exc:
            self.send_error_json(404, str(exc))
        except (ValueError, json.JSONDecodeError) as exc:
            self.send_error_json(400, str(exc))
        except RuntimeError as exc:
            self.send_error_json(409, str(exc))
        except Exception as exc:
            self.send_error_json(500, f"{type(exc).__name__}: {exc}"[:500])

    def send_asset(self, name: str) -> None:
        relative = normalize_relative_path(name)
        path = within(ASSET_ROOT, relative)
        if not path.is_file():
            raise FileNotFoundError(name)
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        self.send_bytes(path.read_bytes(), media_type)


def build_server(host: str, port: int, root: Path) -> WebServer:
    repository = ManualRunRepository(root)
    manager = ManualRunManager(repository)
    return WebServer((host, port), WebHandler, repository, manager)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local RWKV-LH manual test UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-root", default=str(PROJECT_ROOT / "data" / "manual_runs"))
    parser.add_argument(
        "--allow-remote",
        action="store_true",
        help="Allow a non-loopback bind. No authentication is provided.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.host not in {"127.0.0.1", "::1", "localhost"} and not args.allow_remote:
        raise SystemExit("refusing non-loopback bind without --allow-remote")
    server = build_server(args.host, args.port, Path(args.data_root))
    print(
        json.dumps(
            {
                "url": f"http://{args.host}:{server.server_port}",
                "data_root": str(server.repository.root),
                "authentication": False,
                "scope": "local-only" if not args.allow_remote else "explicit-remote-bind",
            },
            ensure_ascii=False,
        ),
        flush=True,
    )
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


__all__ = [
    "ManualRunManager",
    "ManualRunRepository",
    "WebHandler",
    "build_server",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())
