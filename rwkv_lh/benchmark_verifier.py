"""Isolated, hidden acceptance verifier for RWKV long-horizon benchmarks.

The worker in this module deliberately uses only the Python standard library so
the runner can copy this one file into a private bubblewrap namespace without
mounting the repository (and therefore without exposing acceptance catalogs).
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import shutil
import stat
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class CheckResult:
    kind: str
    passed: bool
    observation: dict[str, Any]
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IsolatedVerifierResult:
    checks: tuple[CheckResult, ...]
    metadata: dict[str, Any]

    @property
    def passed(self) -> bool:
        return bool(self.checks) and all(item.passed for item in self.checks)


SUPPORTED_CHECK_KINDS = frozenset(
    {
        "agent_process_tree_closed",
        "aggregate_shards",
        "artifact_phase_checkpoints",
        "checkpoint_constraints",
        "command_exit_stages",
        "command_exit",
        "completed_resume_is_noop",
        "digest_map",
        "directory_file_set",
        "event_max_count",
        "event_min_count",
        "file_contains",
        "file_content",
        "file_not_contains",
        "files_equal",
        "json_equals",
        "json_exact_keys",
        "mock_api_finalized",
        "mock_api_state",
        "no_scope_violation_events",
        "path_absent",
        "post_effect_crash_resumed",
        "priority_summary",
        "resilient_shards",
        "resume_no_repeated_completed_attempts",
        "service_migration",
        "sha256_manifest",
    }
)


def _safe_relative(value: str) -> Path:
    path = Path(str(value or "").strip())
    if not str(path) or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"unsafe relative path: {value!r}")
    return path


def _workspace_path(
    workspace: Path,
    value: str,
    *,
    must_exist: bool = False,
) -> Path:
    root = workspace.resolve(strict=True)
    candidate = (root / _safe_relative(value)).resolve(strict=must_exist)
    candidate.relative_to(root)
    return candidate


def _json_file(workspace: Path, value: str) -> Any:
    return json.loads(
        _workspace_path(workspace, value, must_exist=True).read_text(encoding="utf-8")
    )


def _event_count(events: Sequence[Mapping[str, Any]], event_type: str) -> int:
    return sum(1 for item in events if str(item.get("type") or "") == event_type)


def check_spec(
    spec: Mapping[str, Any],
    workspace: Path,
    events: Sequence[Mapping[str, Any]],
    observations: Mapping[str, Any],
) -> CheckResult:
    """Evaluate one hidden acceptance rule against observable state only."""

    kind = str(spec.get("kind") or "")
    try:
        actual: Any
        target: Any
        if kind == "file_content":
            actual = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            ).read_text(encoding="utf-8")
            target = str(spec["content"])
            return CheckResult(
                kind,
                actual == target,
                {"path": spec["path"], "actual": actual, "target": target},
            )
        if kind == "file_contains":
            actual = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            ).read_text(encoding="utf-8")
            target = str(spec["text"])
            return CheckResult(
                kind,
                target in actual,
                {"path": spec["path"], "text": target},
            )
        if kind == "file_not_contains":
            actual = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            ).read_text(encoding="utf-8")
            target = str(spec["text"])
            return CheckResult(
                kind,
                target not in actual,
                {"path": spec["path"], "text": target},
            )
        if kind == "path_absent":
            path = _workspace_path(workspace, str(spec["path"]))
            exists = path.exists()
            return CheckResult(kind, not exists, {"path": spec["path"], "exists": exists})
        if kind == "json_equals":
            actual = _json_file(workspace, str(spec["path"]))
            target = spec["value"]
            return CheckResult(
                kind,
                actual == target,
                {"path": spec["path"], "actual": actual, "target": target},
            )
        if kind == "json_exact_keys":
            actual = _json_file(workspace, str(spec["path"]))
            actual_keys = sorted(actual) if isinstance(actual, dict) else []
            target = sorted(str(item) for item in spec.get("keys") or [])
            return CheckResult(
                kind,
                actual_keys == target,
                {"path": spec["path"], "actual": actual_keys, "target": target},
            )
        if kind == "files_equal":
            left = _workspace_path(
                workspace, str(spec["left"]), must_exist=True
            ).read_bytes()
            right = _workspace_path(
                workspace, str(spec["right"]), must_exist=True
            ).read_bytes()
            return CheckResult(
                kind,
                left == right,
                {
                    "left": spec["left"],
                    "right": spec["right"],
                    "left_sha256": hashlib.sha256(left).hexdigest(),
                    "right_sha256": hashlib.sha256(right).hexdigest(),
                },
            )
        if kind == "command_exit":
            argv = [str(item) for item in spec.get("argv") or []]
            if not argv:
                raise ValueError("command_exit requires argv")
            if argv[0] in {"python", "python3"}:
                argv[0] = sys.executable
            completed = subprocess.run(
                argv,
                cwd=workspace,
                shell=False,
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                timeout=float(spec.get("timeout", 60)),
                check=False,
                start_new_session=True,
                env={
                    "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                    "LANG": os.environ.get("LANG", "C.UTF-8"),
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "HOME": "/tmp/verifier-home",
                    "TMPDIR": "/tmp",
                },
            )
            target = int(spec.get("exit_code", 0))
            output = (completed.stdout or "") + (completed.stderr or "")
            return CheckResult(
                kind,
                completed.returncode == target,
                {
                    "argv": argv,
                    "actual_exit_code": completed.returncode,
                    "target_exit_code": target,
                    "output": output[:10_000],
                },
            )
        if kind == "sha256_manifest":
            source = _workspace_path(
                workspace, str(spec["source"]), must_exist=True
            )
            manifest = _json_file(workspace, str(spec["manifest"]))
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            passed = (
                manifest.get(str(spec["file_field"])) == str(spec["source"])
                and manifest.get(str(spec["digest_field"])) == digest
            )
            return CheckResult(
                kind,
                passed,
                {"source": spec["source"], "actual_digest": digest, "manifest": manifest},
            )
        if kind == "directory_file_set":
            directory = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            )
            actual = sorted(
                str(path.relative_to(directory))
                for path in directory.rglob("*")
                if path.is_file()
            )
            target = sorted(str(item) for item in spec.get("files") or [])
            return CheckResult(
                kind,
                actual == target,
                {"path": spec["path"], "actual": actual, "target": target},
            )
        if kind == "digest_map":
            directory = _workspace_path(
                workspace, str(spec["directory"]), must_exist=True
            )
            manifest = _json_file(workspace, str(spec["manifest"]))
            target = {}
            for name in spec.get("files") or []:
                path = (directory / _safe_relative(str(name))).resolve(strict=True)
                path.relative_to(directory.resolve(strict=True))
                target[str(name)] = hashlib.sha256(path.read_bytes()).hexdigest()
            return CheckResult(kind, manifest == target, {"manifest": manifest, "target": target})
        if kind == "aggregate_shards":
            directory = _workspace_path(
                workspace, str(spec["directory"]), must_exist=True
            )
            shards = sorted(directory.glob("*.json"))
            categories: dict[str, int | float] = {}
            item_count = 0
            value_total: int | float = 0
            for shard in shards:
                for item in json.loads(shard.read_text(encoding="utf-8"))["items"]:
                    category = str(item["category"])
                    value = item["value"]
                    item_count += 1
                    value_total += value
                    categories[category] = categories.get(category, 0) + value
            target = {
                "shard_count": len(shards),
                "item_count": item_count,
                "value_total": value_total,
                "categories": categories,
            }
            actual = _json_file(workspace, str(spec["path"]))
            return CheckResult(kind, actual == target, {"actual": actual, "target": target})
        if kind == "priority_summary":
            directory = _workspace_path(
                workspace, str(spec["directory"]), must_exist=True
            )
            target = {}
            for path in sorted(directory.glob("*.txt")):
                lines = path.read_text(encoding="utf-8").splitlines()
                if lines and lines[0] == "PRIORITY: yes":
                    target[path.name] = lines[1]
            actual = _json_file(workspace, str(spec["path"]))
            return CheckResult(kind, actual == target, {"actual": actual, "target": target})
        if kind == "resilient_shards":
            directory = _workspace_path(
                workspace, str(spec["directory"]), must_exist=True
            )
            fallback = _workspace_path(
                workspace, str(spec["fallback_directory"]), must_exist=True
            )
            count = int(spec["count"])
            sources: dict[str, str] = {}
            digests: dict[str, str] = {}
            value_total: int | float = 0
            recovered = 0
            for index in range(1, count + 1):
                name = f"shard_{index:02d}.json"
                primary = directory / name
                selected = primary
                source = f"{spec['directory']}/{name}"
                try:
                    value = json.loads(primary.read_text(encoding="utf-8"))
                except (FileNotFoundError, json.JSONDecodeError, UnicodeDecodeError):
                    selected = fallback / name
                    source = f"{spec['fallback_directory']}/{name}"
                    value = json.loads(selected.read_text(encoding="utf-8"))
                    recovered += 1
                value_total += sum(value["values"])
                sources[name] = source
                digests[name] = hashlib.sha256(selected.read_bytes()).hexdigest()
            target = {
                "shard_count": count,
                "primary_count": count - recovered,
                "recovered_count": recovered,
                "value_total": value_total,
                "sources": sources,
                "sha256": digests,
            }
            actual = _json_file(workspace, str(spec["path"]))
            return CheckResult(kind, actual == target, {"actual": actual, "target": target})
        if kind == "service_migration":
            directory = _workspace_path(
                workspace, str(spec["directory"]), must_exist=True
            )
            violations: list[str] = []
            files = sorted(directory.glob("service-*.json"))
            for path in files:
                value = json.loads(path.read_text(encoding="utf-8"))
                if value.get("schema_version") != 3:
                    violations.append(f"{path.name}: schema_version")
                if (value.get("runtime") or {}).get("channel") != "stable":
                    violations.append(f"{path.name}: runtime.channel")
                if (value.get("compat") or {}).get("api") != "v3":
                    violations.append(f"{path.name}: compat.api")
                if path.name == "service-03.json":
                    if "database" in value or value.get("storage") != {
                        "dsn": "postgres://billing",
                        "pool_size": 5,
                    }:
                        violations.append(f"{path.name}: special database migration")
                if path.name == "service-07.json":
                    if "auth" in value or value.get("security") != {
                        "session_ttl_seconds": 3600,
                        "provider": "local",
                    }:
                        violations.append(f"{path.name}: special auth migration")
            expected = int(spec.get("count", 8))
            if len(files) != expected:
                violations.append(f"service count={len(files)} expected={expected}")
            return CheckResult(
                kind,
                not violations,
                {"files": [path.name for path in files], "violations": violations},
            )
        if kind == "checkpoint_constraints":
            directory = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            )
            count = int(spec["count"])
            expected_constraints = spec["constraints"]
            violations: list[str] = []
            for index in range(1, count + 1):
                path = directory / f"step{index:02d}.json"
                try:
                    value = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    violations.append(f"{path.name}: {type(exc).__name__}")
                    continue
                if value != {"step": index, "constraints": expected_constraints}:
                    violations.append(f"{path.name}: content mismatch")
            actual_files = sorted(path.name for path in directory.glob("*.json"))
            expected_files = [f"step{index:02d}.json" for index in range(1, count + 1)]
            if actual_files != expected_files:
                violations.append("checkpoint file set mismatch")
            return CheckResult(
                kind,
                not violations,
                {"files": actual_files, "violations": violations},
            )
        if kind == "artifact_phase_checkpoints":
            directory = _workspace_path(
                workspace, str(spec["path"]), must_exist=True
            )
            phases = int(spec.get("count", 5))
            facts_per_phase = int(spec.get("facts_per_phase", 2))
            violations: list[str] = []
            for phase in range(1, phases + 1):
                path = directory / f"phase{phase:02d}.json"
                first_fact = (phase - 1) * facts_per_phase + 1
                expected = {
                    "phase": phase,
                    "fact_ids": [
                        f"F{index:02d}"
                        for index in range(first_fact, first_fact + facts_per_phase)
                    ],
                }
                try:
                    actual = json.loads(path.read_text(encoding="utf-8"))
                except Exception as exc:
                    violations.append(f"{path.name}: {type(exc).__name__}")
                    continue
                if actual != expected:
                    violations.append(f"{path.name}: content mismatch")
            return CheckResult(
                kind,
                not violations,
                {"phase_count": phases, "violations": violations},
            )
        if kind == "event_min_count":
            event_type = str(spec["event_type"])
            actual = _event_count(events, event_type)
            target = int(spec["count"])
            return CheckResult(
                kind,
                actual >= target,
                {"event_type": event_type, "actual": actual, "minimum": target},
            )
        if kind == "event_max_count":
            event_type = str(spec["event_type"])
            actual = _event_count(events, event_type)
            target = int(spec["count"])
            return CheckResult(
                kind,
                actual <= target,
                {"event_type": event_type, "actual": actual, "maximum": target},
            )
        if kind == "command_exit_stages":
            target_argv = [str(item) for item in spec.get("argv") or []]
            command_attempts: set[str] = set()
            outputs: list[tuple[int | None, str]] = []
            for event in events:
                data = event.get("data") or {}
                if event.get("type") == "attempt_started" and [
                    str(item) for item in (data.get("arguments") or {}).get("argv") or []
                ] == target_argv:
                    command_attempts.add(str(data.get("attempt_id") or ""))
                elif (
                    event.get("type") == "action_returned"
                    and str(data.get("attempt_id") or "") in command_attempts
                ):
                    exit_code = data.get("exit_code")
                    outputs.append(
                        (
                            int(exit_code) if exit_code is not None else None,
                            str(data.get("output") or ""),
                        )
                    )
            expected_stages = [str(item) for item in spec.get("stages") or []]
            stage_index = 0
            success_after_stages = False
            for exit_code, output in outputs:
                if (
                    exit_code != 0
                    and stage_index < len(expected_stages)
                    and expected_stages[stage_index] in output
                ):
                    stage_index += 1
                    continue
                if exit_code == 0 and stage_index == len(expected_stages):
                    success_after_stages = True
            passed = bool(expected_stages) and stage_index == len(expected_stages)
            if bool(spec.get("require_success", True)):
                passed = passed and success_after_stages
            return CheckResult(
                kind,
                passed,
                {
                    "argv": target_argv,
                    "expected_stages": expected_stages,
                    "matched_stages": stage_index,
                    "success_after_stages": success_after_stages,
                    "attempt_count": len(outputs),
                },
            )
        if kind == "no_scope_violation_events":
            violations = [
                item
                for item in events
                if "ScopeViolation" in json.dumps(item, ensure_ascii=False)
            ]
            return CheckResult(kind, not violations, {"violation_count": len(violations)})
        if kind in {
            "resume_no_repeated_completed_attempts",
            "completed_resume_is_noop",
            "post_effect_crash_resumed",
            "mock_api_finalized",
            "agent_process_tree_closed",
        }:
            passed = bool(observations.get(kind))
            return CheckResult(kind, passed, {"observed": passed})
        if kind == "mock_api_state":
            actual = observations.get("mock_api_state")
            target = spec.get("value")
            return CheckResult(kind, actual == target, {"actual": actual, "target": target})
        raise ValueError(f"unsupported external checker kind: {kind}")
    except Exception as exc:
        return CheckResult(kind, False, {}, f"{type(exc).__name__}: {exc}"[:2000])


def verify_payload(payload: Mapping[str, Any], workspace: Path) -> IsolatedVerifierResult:
    acceptance = payload.get("acceptance")
    if not isinstance(acceptance, Mapping):
        raise ValueError("verifier payload has no acceptance object")
    events = payload.get("events") or []
    observations = payload.get("observations") or {}
    if not isinstance(events, list) or not isinstance(observations, Mapping):
        raise ValueError("invalid verifier observations")
    raw_checks = acceptance.get("checks")
    if (
        not isinstance(raw_checks, list)
        or not raw_checks
        or any(not isinstance(spec, Mapping) for spec in raw_checks)
    ):
        raise ValueError("verifier acceptance requires a non-empty checks array")
    checks = tuple(
        check_spec(spec, workspace, events, observations)
        for spec in raw_checks
    )
    return IsolatedVerifierResult(
        checks,
        {
            "backend": "bubblewrap",
            "acceptance_transport": "stdin",
            "workspace_mount": "read_only_snapshot",
            "network": "unshared",
            "pid_namespace": "private",
            "repository_mounted": False,
            "verifier_logs_exposed_to_agent": False,
        },
    )


def _disable_ptrace() -> None:
    """Prevent verifier-spawned workspace code from reading worker memory."""

    if sys.platform != "linux":
        return
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        if libc.prctl(4, 0, 0, 0, 0) != 0:  # PR_SET_DUMPABLE
            raise OSError(ctypes.get_errno(), "prctl(PR_SET_DUMPABLE) failed")
    except Exception as exc:
        raise RuntimeError(f"could not harden verifier process: {exc}") from exc


def _secure_snapshot(source: Path, destination: Path) -> None:
    """Copy only directories and regular files; reject symlink-based escapes."""

    root = source.resolve(strict=True)
    destination.mkdir(parents=True, exist_ok=False)
    for current, directory_names, file_names in os.walk(root, followlinks=False):
        current_path = Path(current)
        relative = current_path.relative_to(root)
        target_directory = destination / relative
        target_directory.mkdir(parents=True, exist_ok=True)
        for name in list(directory_names):
            child = current_path / name
            mode = child.lstat().st_mode
            if stat.S_ISLNK(mode):
                raise ValueError(f"verifier snapshot rejects symlink directory: {child}")
            if not stat.S_ISDIR(mode):
                raise ValueError(f"verifier snapshot rejects special directory: {child}")
        for name in file_names:
            child = current_path / name
            mode = child.lstat().st_mode
            if not stat.S_ISREG(mode):
                raise ValueError(f"verifier snapshot rejects non-regular file: {child}")
            shutil.copy2(child, target_directory / name, follow_symlinks=False)


def _bubblewrap_worker_command(
    bubblewrap: str,
    workspace: Path,
    worker: Path,
) -> list[str]:
    executable = Path(sys.executable).resolve(strict=True)
    runtime_root: Path | None = None
    sandbox_python = executable
    if not executable.is_relative_to(Path("/usr")):
        runtime_root = executable.parent.parent
        sandbox_python = Path("/opt/verifier-python/bin") / executable.name
    command = [
        bubblewrap,
        "--die-with-parent",
        "--unshare-all",
        "--new-session",
        "--ro-bind",
        "/usr",
        "/usr",
        "--ro-bind",
        "/etc",
        "/etc",
        "--symlink",
        "usr/bin",
        "/bin",
        "--symlink",
        "usr/sbin",
        "/sbin",
        "--symlink",
        "usr/lib",
        "/lib",
        "--symlink",
        "usr/lib64",
        "/lib64",
        "--dir",
        "/opt",
        "--dir",
        "/opt/verifier",
        "--dir",
        "/opt/verifier-python",
        "--dir",
        "/workspace",
        "--dir",
        "/proc",
        "--dir",
        "/dev",
        "--dir",
        "/tmp",
        "--remount-ro",
        "/",
        "--proc",
        "/proc",
        "--dev",
        "/dev",
        "--tmpfs",
        "/tmp",
        "--ro-bind",
        str(workspace),
        "/workspace",
        "--ro-bind",
        str(worker.parent),
        "/opt/verifier",
    ]
    if runtime_root is not None:
        command.extend(
            ["--ro-bind", str(runtime_root), "/opt/verifier-python"]
        )
    command.extend(
        [
            "--setenv",
            "PYTHONDONTWRITEBYTECODE",
            "1",
            "--setenv",
            "HOME",
            "/tmp/verifier-home",
            "--setenv",
            "TMPDIR",
            "/tmp",
            "--chdir",
            "/workspace",
            str(sandbox_python),
            "/opt/verifier/worker.py",
            "--worker",
        ]
    )
    return command


def run_isolated_verifier(
    acceptance: Mapping[str, Any],
    workspace: Path,
    events: Sequence[Mapping[str, Any]],
    observations: Mapping[str, Any],
    *,
    private_root: Path,
    timeout_seconds: float = 180.0,
) -> IsolatedVerifierResult:
    """Run hidden checks in a fail-closed namespace after the Agent phase ends."""

    bubblewrap = shutil.which("bwrap")
    if not bubblewrap:
        raise RuntimeError("isolated E2E verification requires bubblewrap")
    private_root.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="verifier-", dir=private_root) as directory:
        root = Path(directory)
        snapshot = root / "workspace"
        _secure_snapshot(workspace, snapshot)
        worker_directory = root / "worker"
        worker_directory.mkdir()
        worker = worker_directory / "worker.py"
        shutil.copy2(Path(__file__).resolve(strict=True), worker)
        payload = json.dumps(
            {
                "acceptance": dict(acceptance),
                "events": [dict(item) for item in events],
                "observations": dict(observations),
            },
            ensure_ascii=False,
        )
        completed = subprocess.run(
            _bubblewrap_worker_command(bubblewrap, snapshot, worker),
            input=payload,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=max(1.0, float(timeout_seconds)),
            check=False,
            start_new_session=True,
            env={"LANG": os.environ.get("LANG", "C.UTF-8")},
        )
        if completed.returncode != 0:
            raise RuntimeError(
                "isolated verifier failed: "
                + ((completed.stderr or completed.stdout or "unknown error")[:4000])
            )
        raw = json.loads(completed.stdout)
        if not isinstance(raw, Mapping):
            raise RuntimeError("isolated verifier returned a non-object response")
        raw_checks = raw.get("checks")
        expected_checks = acceptance.get("checks")
        if not isinstance(raw_checks, list) or not isinstance(expected_checks, list):
            raise RuntimeError("isolated verifier response has no checks array")
        checks = tuple(CheckResult(**dict(item)) for item in raw_checks)
        expected_kinds = [str(item.get("kind") or "") for item in expected_checks]
        if len(checks) != len(expected_checks) or [item.kind for item in checks] != expected_kinds:
            raise RuntimeError("isolated verifier response does not match acceptance checks")
        metadata = dict(raw.get("metadata") or {})
        required_metadata = {
            "backend": "bubblewrap",
            "acceptance_transport": "stdin",
            "workspace_mount": "read_only_snapshot",
            "network": "unshared",
            "pid_namespace": "private",
            "repository_mounted": False,
            "verifier_logs_exposed_to_agent": False,
        }
        if any(metadata.get(key) != value for key, value in required_metadata.items()):
            raise RuntimeError("isolated verifier returned invalid isolation metadata")
        return IsolatedVerifierResult(checks, metadata)


def _worker_main() -> int:
    _disable_ptrace()
    payload = json.loads(sys.stdin.read())
    try:
        sys.stdin.close()
    except Exception:
        pass
    result = verify_payload(payload, Path("/workspace"))
    print(
        json.dumps(
            {
                "passed": result.passed,
                "checks": [item.to_dict() for item in result.checks],
                "metadata": result.metadata,
            },
            ensure_ascii=False,
        )
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--worker", action="store_true")
    arguments = parser.parse_args()
    if not arguments.worker:
        raise RuntimeError("benchmark verifier is an internal worker")
    return _worker_main()


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "SUPPORTED_CHECK_KINDS",
    "CheckResult",
    "IsolatedVerifierResult",
    "check_spec",
    "run_isolated_verifier",
    "verify_payload",
]
