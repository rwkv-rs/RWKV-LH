"""Owned multi-process deployment for Router, remote RWKV and product services."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from rwkv_lh.runtime.openai_compat import OpenAICompatibleRWKVClient
from rwkv_lh.exact_tool_selector.network_client import (
    NetworkExactToolSelectorSettings,
)
from rwkv_lh.runtime.settings import PROJECT_ROOT, load_local_env


STACK_SCHEMA_VERSION = "rwkv-lh.runtime-stack.v1"
PROCESS_SCHEMA_VERSION = "rwkv-lh.owned-process.v1"
SAFE_UNIT = re.compile(r"^[A-Za-z0-9_.@-]+$")
SAFE_SSH_ALIAS = re.compile(r"^[A-Za-z0-9_.@-]+$")


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError(f"runtime record must be an object: {path}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".pending")
    pending.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    os.replace(pending, path)


def _proc_identity(pid: int) -> tuple[int, str] | None:
    proc = Path("/proc") / str(pid)
    try:
        if proc.stat().st_uid != os.getuid():
            return None
        stat = (proc / "stat").read_text(encoding="utf-8")
        closing = stat.rfind(")")
        fields = stat[closing + 2 :].split()
        if not fields or fields[0] == "Z":
            return None
        start_ticks = int(fields[19])
        command = (proc / "cmdline").read_bytes()
        if not command:
            return None
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        return None
    return start_ticks, hashlib.sha256(command).hexdigest()


@dataclass(frozen=True)
class RuntimeStackSettings:
    mode: str
    state_dir: Path
    remote_ssh_alias: str
    remote_service: str
    remote_port: int
    main_base_url: str

    @classmethod
    def from_env(cls) -> "RuntimeStackSettings":
        load_local_env()
        settings = cls(
            mode=os.environ.get("RWKV_RUNTIME_MODE", "managed-remote")
            .strip()
            .casefold(),
            state_dir=Path(
                os.environ.get("RWKV_RUNTIME_STATE_DIR", PROJECT_ROOT / "data/runtime")
            ).expanduser(),
            remote_ssh_alias=os.environ.get(
                "RWKV_REMOTE_SSH_ALIAS", "rwkv-8222"
            ).strip(),
            remote_service=os.environ.get(
                "RWKV_REMOTE_SERVICE",
                "helicopter-vllm-g1i-13p3b-rwkv-lh-stage1-selector-gpu0.service",
            ).strip(),
            remote_port=int(os.environ.get("RWKV_REMOTE_PORT", "18070")),
            main_base_url=os.environ.get(
                "RWKV_BASE_URL", "http://127.0.0.1:29613/v1"
            ).rstrip("/"),
        )
        settings.validate()
        return settings

    def validate(self) -> None:
        if self.mode not in {"external", "managed-remote"}:
            raise ValueError("RWKV_RUNTIME_MODE must be external or managed-remote")
        parsed = urlparse(self.main_base_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("main RWKV URL must be absolute HTTP(S)")
        if not 1 <= self.remote_port <= 65535:
            raise ValueError("RWKV remote port is invalid")
        if (
            not SAFE_SSH_ALIAS.fullmatch(self.remote_ssh_alias)
            or self.remote_ssh_alias.startswith("-")
            or not SAFE_UNIT.fullmatch(self.remote_service)
            or self.remote_service.startswith("-")
        ):
            raise ValueError("RWKV remote SSH alias/service is invalid")


class RuntimeStackManager:
    def __init__(self, settings: RuntimeStackSettings | None = None) -> None:
        self.settings = settings or RuntimeStackSettings.from_env()
        self.state_dir = self.settings.state_dir.resolve()
        self.process_dir = self.state_dir / "processes"
        self.log_dir = self.state_dir / "logs"
        self.lock_path = self.state_dir / "stack.lock"
        self.remote_record = self.state_dir / "remote.json"

    def _locked(self):
        self.state_dir.mkdir(parents=True, exist_ok=True)
        stream = self.lock_path.open("a+")
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        return stream

    def _record_path(self, name: str) -> Path:
        return self.process_dir / f"{name}.json"

    def _owned_record(self, name: str) -> dict[str, Any] | None:
        path = self._record_path(name)
        if not path.is_file():
            return None
        record = _read_json(path)
        if record.get("schema_version") != PROCESS_SCHEMA_VERSION:
            raise RuntimeError(f"unsupported owned process record: {path}")
        return record

    def _record_alive(self, record: Mapping[str, Any]) -> bool:
        identity = _proc_identity(int(record.get("pid") or 0))
        return identity == (
            int(record.get("start_ticks") or -1),
            str(record.get("command_digest") or ""),
        )

    def _refresh_reexecuted_record(
        self,
        name: str,
        record: Mapping[str, Any],
    ) -> dict[str, Any] | None:
        """Refresh only the command digest after an owned launcher calls exec(2)."""

        pid = int(record.get("pid") or 0)
        identity = _proc_identity(pid)
        if identity is None or identity[0] != int(record.get("start_ticks") or -1):
            return None
        try:
            if os.getpgid(pid) != pid:
                return None
        except ProcessLookupError:
            return None
        refreshed = {**record, "command_digest": identity[1]}
        _atomic_json(self._record_path(name), refreshed)
        return refreshed

    def _spawn(
        self,
        name: str,
        command: Sequence[str],
        *,
        cwd: Path,
        environment: Mapping[str, str],
    ) -> dict[str, Any]:
        current = self._owned_record(name)
        if current is not None and self._record_alive(current):
            return current
        self.process_dir.mkdir(parents=True, exist_ok=True)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"{name}.log"
        log = log_path.open("ab", buffering=0)
        try:
            process = subprocess.Popen(
                list(command),
                cwd=cwd,
                env=dict(environment),
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        finally:
            log.close()
        identity = None
        for _ in range(100):
            if process.poll() is not None:
                break
            identity = _proc_identity(process.pid)
            if identity is not None:
                break
            time.sleep(0.01)
        if identity is None:
            raise RuntimeError(f"{name} process did not establish an owned identity")
        record = {
            "schema_version": PROCESS_SCHEMA_VERSION,
            "name": name,
            "pid": process.pid,
            "start_ticks": identity[0],
            "command_digest": identity[1],
            "cwd": str(cwd),
            "log": str(log_path),
            "started_at_unix": time.time(),
        }
        _atomic_json(self._record_path(name), record)
        return record

    def _stop_owned(self, name: str, timeout_seconds: float = 20.0) -> bool:
        record = self._owned_record(name)
        if record is None:
            return False
        path = self._record_path(name)
        if not self._record_alive(record):
            path.unlink(missing_ok=True)
            return False
        pid = int(record["pid"])
        if os.getpgid(pid) != pid:
            raise RuntimeError(f"refusing to stop non-session-owned process {name}")
        os.killpg(pid, signal.SIGTERM)
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline and self._record_alive(record):
            time.sleep(0.1)
        if self._record_alive(record):
            os.killpg(pid, signal.SIGKILL)
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and self._record_alive(record):
                time.sleep(0.05)
        if self._record_alive(record):
            raise RuntimeError(f"owned process {name} did not stop")
        path.unlink(missing_ok=True)
        return True

    @staticmethod
    def _run(command: Sequence[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            list(command),
            cwd=cwd,
            check=False,
            capture_output=True,
            text=True,
        )

    def _remote_active(self) -> bool:
        completed = self._run(
            [
                "ssh",
                self.settings.remote_ssh_alias,
                "systemctl",
                "--user",
                "is-active",
                self.settings.remote_service,
            ]
        )
        return completed.returncode == 0 and completed.stdout.strip() == "active"

    def _ensure_remote(self) -> dict[str, Any]:
        if self.settings.mode == "external":
            return {"managed": False, "active": None, "started_by_manager": False}
        prior_owned = False
        if self.remote_record.is_file():
            prior = _read_json(self.remote_record)
            prior_owned = bool(
                prior.get("started_by_manager") is True
                and prior.get("ssh_alias") == self.settings.remote_ssh_alias
                and prior.get("service") == self.settings.remote_service
            )
        active = self._remote_active()
        if not active:
            completed = self._run(
                [
                    "ssh",
                    self.settings.remote_ssh_alias,
                    "systemctl",
                    "--user",
                    "start",
                    self.settings.remote_service,
                ]
            )
            if completed.returncode != 0:
                detail = (completed.stderr or completed.stdout).strip()[-2000:]
                raise RuntimeError(f"remote RWKV service failed to start: {detail}")
        record = {
            "schema_version": STACK_SCHEMA_VERSION,
            "ssh_alias": self.settings.remote_ssh_alias,
            "service": self.settings.remote_service,
            "started_by_manager": prior_owned or not active,
            "recorded_at_unix": time.time(),
        }
        _atomic_json(self.remote_record, record)
        return {"managed": True, "active": True, **record}

    def _main_health(self) -> dict[str, Any]:
        client = OpenAICompatibleRWKVClient()
        try:
            return client.health().to_dict()
        finally:
            client.close()

    def _selector_health(self) -> dict[str, Any]:
        settings = NetworkExactToolSelectorSettings.from_env()
        if settings is None:
            return {
                "available": False,
                "enabled": False,
                "error": "independent Selector identity is not configured",
            }
        try:
            with urllib.request.urlopen(
                settings.base_url.rstrip("/") + "/healthz",
                timeout=2,
            ) as response:
                value = json.loads(response.read().decode("utf-8"))
        except (OSError, ValueError, urllib.error.URLError) as exc:
            return {
                "available": False,
                "enabled": True,
                "error": f"{type(exc).__name__}: {exc}",
            }
        if not isinstance(value, Mapping):
            raise RuntimeError("network Selector health response is not an object")
        if value.get("status") != "ok":
            raise RuntimeError("network Selector health status is not ok")
        identity = value.get("runtime_identity")
        expected = settings.runtime_identity()
        if identity != expected:
            raise RuntimeError(
                "network Selector health identity mismatch: "
                f"expected={expected}, actual={identity}"
            )
        return {
            "available": True,
            "enabled": True,
            "runtime_identity": identity,
        }

    @staticmethod
    def _wait(probe, *, timeout_seconds: float, name: str) -> dict[str, Any]:
        deadline = time.monotonic() + timeout_seconds
        last_error = "not attempted"
        while time.monotonic() < deadline:
            try:
                result = probe()
                if result.get("available") is True:
                    return result
                last_error = str(result.get("error") or "unavailable")
            except Exception as exc:
                last_error = f"{type(exc).__name__}: {exc}"
            time.sleep(0.5)
        raise TimeoutError(f"{name} did not become ready: {last_error[:1000]}")

    def _ensure_tunnel(self) -> dict[str, Any]:
        parsed = urlparse(self.settings.main_base_url)
        if parsed.hostname not in {"127.0.0.1", "::1", "localhost"}:
            return {"required": False, "owned": False}
        health = self._main_health()
        if health.get("available") is True:
            record = self._owned_record("tunnel")
            owned = bool(record and self._record_alive(record))
            return {
                "required": True,
                "owned": owned,
                "adopted_ready_endpoint": not owned,
                **({"process": record} if owned else {}),
            }
        if parsed.port is None:
            raise ValueError("loopback RWKV_BASE_URL must include an explicit port")
        environment = dict(os.environ)
        record = self._spawn(
            "tunnel",
            [
                "ssh",
                "-N",
                "-o",
                "ControlMaster=no",
                "-o",
                "ExitOnForwardFailure=yes",
                "-L",
                f"127.0.0.1:{parsed.port}:127.0.0.1:{self.settings.remote_port}",
                self.settings.remote_ssh_alias,
            ],
            cwd=PROJECT_ROOT,
            environment=environment,
        )
        return {"required": True, "owned": True, "process": record}

    def _ensure_selector(self) -> dict[str, Any]:
        settings = NetworkExactToolSelectorSettings.from_env()
        if settings is None:
            return {"enabled": False, "owned": False}
        health = self._selector_health()
        if health.get("available") is True:
            record = self._owned_record("selector")
            if record is not None and not self._record_alive(record):
                record = self._refresh_reexecuted_record("selector", record)
            owned = bool(record and self._record_alive(record))
            return {
                "enabled": True,
                "owned": owned,
                "adopted_ready_endpoint": not owned,
                "health": health,
                **({"process": record} if owned else {}),
            }
        launcher = Path(
            os.environ.get(
                "RWKV_SELECTOR_LAUNCHER",
                PROJECT_ROOT
                / "scripts/run_network_selector_s60_requirement_byte_tail_zero_service.sh",
            )
        ).expanduser().resolve()
        if not launcher.is_file() or not os.access(launcher, os.X_OK):
            raise RuntimeError(
                f"network Selector launcher is missing or not executable: {launcher}"
            )
        environment = dict(os.environ)
        existing = environment.get("PYTHONPATH", "")
        environment["PYTHONPATH"] = os.pathsep.join(
            [str(PROJECT_ROOT), *([existing] if existing else [])]
        )
        environment["CUDA_VISIBLE_DEVICES"] = "0"
        record = self._spawn(
            "selector",
            [str(launcher)],
            cwd=PROJECT_ROOT,
            environment=environment,
        )
        return {"enabled": True, "owned": True, "process": record}

    def _ensure_product_process(self, name: str, module: str) -> dict[str, Any]:
        environment = dict(os.environ)
        environment.pop("RWKV_STATE_ROUTER_URL", None)
        command = [sys.executable, "-m", module]
        if name == "web":
            asset_root = Path(
                environment.get(
                    "RWKV_WEB_ASSET_ROOT",
                    PROJECT_ROOT / "rwkv_lh/goal_web_assets",
                )
            ).expanduser().resolve()
            data_root = Path(
                environment.get(
                    "RWKV_WEB_DATA_ROOT",
                    PROJECT_ROOT / "data/goal_ui_preview",
                )
            ).expanduser().resolve()
            port = int(environment.get("RWKV_WEB_PORT", "8766"))
            if not 1 <= port <= 65535:
                raise ValueError("RWKV_WEB_PORT must be between 1 and 65535")
            for asset in ("index.html", "styles.css", "app.js"):
                if not (asset_root / asset).is_file():
                    raise RuntimeError(f"Goal Studio asset is missing: {asset_root / asset}")
            environment["RWKV_LH_WEB_ASSET_ROOT"] = str(asset_root)
            command.extend(
                [
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                    "--data-root",
                    str(data_root),
                ]
            )
        record = self._spawn(
            name,
            command,
            cwd=PROJECT_ROOT,
            environment=environment,
        )
        return {"owned": True, "process": record}

    def up(
        self,
        *,
        web: bool = False,
        proactive_worker: bool = False,
        timeout_seconds: float = 180.0,
    ) -> dict[str, Any]:
        with self._locked():
            remote = self._ensure_remote()
            tunnel = self._ensure_tunnel()
            main_health = self._wait(
                self._main_health,
                timeout_seconds=timeout_seconds,
                name="main RWKV endpoint",
            )
            selector = self._ensure_selector()
            selector_health = (
                self._wait(
                    self._selector_health,
                    timeout_seconds=timeout_seconds,
                    name="independent Selector endpoint",
                )
                if selector.get("enabled") is True
                else {"available": False, "enabled": False}
            )
            if selector.get("owned") is True:
                refreshed_selector = self._refresh_reexecuted_record(
                    "selector",
                    dict(selector.get("process") or {}),
                )
                if refreshed_selector is None:
                    raise RuntimeError(
                        "owned Selector changed PID/start identity during startup"
                    )
                selector["process"] = refreshed_selector
            product: dict[str, Any] = {}
            if web:
                product["web"] = self._ensure_product_process(
                    "web", "scripts.run_web_ui"
                )
            if proactive_worker:
                environment = dict(os.environ)
                environment.pop("RWKV_STATE_ROUTER_URL", None)
                product["worker"] = {
                    "owned": True,
                    "process": self._spawn(
                        "worker",
                        [sys.executable, "-m", "scripts.run_long_horizon", "serve"],
                        cwd=PROJECT_ROOT,
                        environment=environment,
                    ),
                }
            result = {
                "schema_version": STACK_SCHEMA_VERSION,
                "mode": self.settings.mode,
                "remote": remote,
                "tunnel": tunnel,
                "main_health": main_health,
                "selector": selector,
                "selector_health": selector_health,
                "product": product,
            }
            _atomic_json(self.state_dir / "last_up.json", result)
            return result

    def down(self) -> dict[str, Any]:
        with self._locked():
            retired_router_stopped = self._stop_owned("router")
            stopped = {
                name: self._stop_owned(name)
                for name in ("worker", "web", "selector", "tunnel")
            }
            remote_stopped = False
            if self.remote_record.is_file():
                remote = _read_json(self.remote_record)
                if remote.get("started_by_manager") is True:
                    completed = self._run(
                        [
                            "ssh",
                            self.settings.remote_ssh_alias,
                            "systemctl",
                            "--user",
                            "stop",
                            self.settings.remote_service,
                        ]
                    )
                    if completed.returncode != 0:
                        raise RuntimeError("failed to stop manager-owned remote service")
                    remote_stopped = True
                self.remote_record.unlink(missing_ok=True)
            return {
                "schema_version": STACK_SCHEMA_VERSION,
                "stopped": stopped,
                "retired_router_stopped": retired_router_stopped,
                "remote_stopped": remote_stopped,
            }

    def status(self, *, probe: bool = True) -> dict[str, Any]:
        processes: dict[str, Any] = {}
        for name in ("tunnel", "selector", "web", "worker"):
            record = self._owned_record(name)
            processes[name] = {
                "owned": record is not None,
                "alive": bool(record and self._record_alive(record)),
                "pid": int(record["pid"]) if record else None,
                "log": str(record["log"]) if record else None,
            }
        result: dict[str, Any] = {
            "schema_version": STACK_SCHEMA_VERSION,
            "mode": self.settings.mode,
            "processes": processes,
        }
        if probe:
            try:
                result["main_health"] = self._main_health()
            except Exception as exc:
                result["main_health"] = {
                    "available": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            try:
                result["selector_health"] = self._selector_health()
            except Exception as exc:
                result["selector_health"] = {
                    "available": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            if self.settings.mode == "managed-remote":
                result["remote_active"] = self._remote_active()
        return result

    def prepare(self) -> dict[str, Any]:
        """The product stack has no separate local engine preparation step."""

        return {
            "schema_version": STACK_SCHEMA_VERSION,
            "component": "product runtime stack",
            "status": "no_prepare_required",
            "reused": True,
        }

__all__ = [
    "PROCESS_SCHEMA_VERSION",
    "RuntimeStackManager",
    "RuntimeStackSettings",
    "STACK_SCHEMA_VERSION",
]
