"""Scoped action harness with explicit side-effect and idempotency metadata."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.schema import GoalState, TaskAction


class HarnessError(RuntimeError):
    pass


class ScopeViolation(HarnessError):
    pass


@dataclass(frozen=True)
class ActionDefinition:
    name: str
    description: str
    read_only: bool
    side_effect: bool
    idempotent: bool
    default_timeout: float
    argument_schema: dict[str, Any] = field(default_factory=dict)
    required_postconditions: tuple[str, ...] = ()


@dataclass
class ObservedArtifact:
    path: str
    sha256: str
    media_type: str
    size_bytes: int
    summary: str = ""


@dataclass
class ActionResult:
    action_type: str
    success: bool
    output: str = ""
    exit_code: int | None = None
    artifacts: list[ObservedArtifact] = field(default_factory=list)
    evidence: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    error: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "action_type": self.action_type,
            "success": self.success,
            "output": self.output,
            "exit_code": self.exit_code,
            "artifacts": [asdict(item) for item in self.artifacts],
            "evidence": self.evidence,
            "metadata": self.metadata,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any] | None) -> "ActionResult":
        raw = value if isinstance(value, Mapping) else {}
        return cls(
            action_type=str(raw.get("action_type") or ""),
            success=bool(raw.get("success", False)),
            output=str(raw.get("output") or ""),
            exit_code=(int(raw["exit_code"]) if raw.get("exit_code") is not None else None),
            artifacts=[
                ObservedArtifact(**dict(item))
                for item in raw.get("artifacts") or []
                if isinstance(item, Mapping)
            ],
            evidence=[dict(item) for item in raw.get("evidence") or [] if isinstance(item, Mapping)],
            metadata=dict(raw.get("metadata") or {}),
            error=dict(raw["error"]) if isinstance(raw.get("error"), Mapping) else None,
        )


class ActionHarness:
    _definitions = {
        "write_file": ActionDefinition(
            "write_file", "Atomically write UTF-8 text inside the workspace.", False, True, True, 30.0,
            {"path": "relative path", "content": "text", "overwrite": "boolean", "create_parents": "boolean"},
            ("file_exists",),
        ),
        "write_json": ActionDefinition(
            "write_json", "Atomically serialize a JSON value inside the workspace.", False, True, True, 30.0,
            {"path": "relative path", "value": "any JSON value"}, ("file_exists",),
        ),
        "replace_text": ActionDefinition(
            "replace_text", "Replace an exact text occurrence in an existing UTF-8 file.", False, True, True, 30.0,
            {"path": "relative path", "old": "exact text", "new": "replacement", "count": "positive integer"},
            ("file_contains",),
        ),
        "append_file": ActionDefinition(
            "append_file", "Append UTF-8 text; this action is non-idempotent.", False, True, False, 30.0,
            {"path": "relative path", "content": "text"}, ("file_contains",),
        ),
        "delete_file": ActionDefinition(
            "delete_file", "Delete one explicitly scoped path.", False, True, True, 30.0,
            {"path": "relative path", "missing_ok": "boolean", "recursive": "boolean"}, ("file_absent",),
        ),
        "make_directory": ActionDefinition(
            "make_directory", "Create a directory inside the workspace.", False, True, True, 30.0,
            {"path": "relative path", "parents": "boolean"}, ("file_exists",),
        ),
        "copy_file": ActionDefinition(
            "copy_file", "Copy one scoped file to another scoped path.", False, True, True, 30.0,
            {"source": "relative path", "destination": "relative path"}, ("file_exists",),
        ),
        "read_file": ActionDefinition(
            "read_file", "Read a UTF-8 file without modifying it.", True, False, True, 30.0,
            {"path": "relative path", "max_chars": "positive integer"},
        ),
        "bind_evidence": ActionDefinition(
            "bind_evidence", "Read an exact line span and retain its source locator and quote.", True, False, True, 30.0,
            {"path": "relative path", "start_line": "1-based integer", "end_line": "inclusive 1-based integer", "source": "source label or URL"},
            ("evidence_bound",),
        ),
        "check_command": ActionDefinition(
            "check_command", "Run a read-only test, linter, or inspection command with argv and shell disabled.",
            True, False, True, 120.0,
            {"argv": "non-empty string array", "cwd": "relative directory", "timeout": "seconds", "env": "explicit object"},
            ("command_exit_code",),
        ),
        "run_command": ActionDefinition(
            "run_command", "Run a potentially mutating command with argv and shell disabled.", False, True, False, 120.0,
            {"argv": "non-empty string array", "cwd": "relative directory", "timeout": "seconds", "env": "explicit object"},
            ("command_exit_code",),
        ),
        "noop": ActionDefinition(
            "noop", "Record an explicit no-op result for control-flow tasks.", True, False, True, 5.0,
            {"output": "text"},
        ),
    }

    def __init__(
        self,
        *,
        output_limit_chars: int = 100_000,
        actions: Mapping[
            str,
            tuple[
                ActionDefinition,
                Callable[[GoalState, dict[str, Any]], ActionResult],
            ],
        ]
        | None = None,
    ):
        self.output_limit_chars = max(1000, int(output_limit_chars))
        self._definitions = dict(type(self)._definitions)
        self._handlers: dict[str, Callable[[GoalState, dict[str, Any]], ActionResult]] = {
            "write_file": self._write_file,
            "write_json": self._write_json,
            "replace_text": self._replace_text,
            "append_file": self._append_file,
            "delete_file": self._delete_file,
            "make_directory": self._make_directory,
            "copy_file": self._copy_file,
            "read_file": self._read_file,
            "bind_evidence": self._bind_evidence,
            "check_command": self._check_command,
            "run_command": self._run_command,
            "noop": self._noop,
        }
        for name, item in (actions or {}).items():
            definition, handler = item
            if name != definition.name:
                raise HarnessError("custom action key must match definition.name")
            self.register_action(definition, handler)

    def register_action(
        self,
        definition: ActionDefinition,
        handler: Callable[[GoalState, dict[str, Any]], ActionResult],
    ) -> None:
        """Register one explicit extension action with recovery metadata."""

        name = str(definition.name or "").strip()
        if not name:
            raise HarnessError("custom action requires a name")
        if name in self._definitions:
            raise HarnessError(f"action is already registered: {name}")
        if not callable(handler):
            raise HarnessError(f"action handler is not callable: {name}")
        self._definitions[name] = definition
        self._handlers[name] = handler

    def definition(self, action_type: str) -> ActionDefinition:
        normalized = str(action_type or "").strip()
        definition = self._definitions.get(normalized)
        if definition is None:
            raise HarnessError(f"unsupported action type: {normalized}")
        return definition

    def action_contract(self) -> str:
        return json.dumps(
            {
                "actions": {
                name: {
                    "description": definition.description,
                    "read_only": definition.read_only,
                    "side_effect": definition.side_effect,
                    "idempotent": definition.idempotent,
                    "default_timeout": definition.default_timeout,
                    "arguments": definition.argument_schema,
                    "required_postconditions": definition.required_postconditions,
                }
                for name, definition in self._definitions.items()
                }
            },
            ensure_ascii=False,
            indent=2,
        )

    def missing_required_postconditions(
        self,
        action_type: str,
        validation_kinds: list[str] | tuple[str, ...] | set[str],
    ) -> list[str]:
        definition = self.definition(action_type)
        available = {str(item or "").strip() for item in validation_kinds}
        if available & {
            "file_contains",
            "file_not_contains",
            "file_content",
            "json_field_equals",
            "json_schema",
            "hash_changed",
            "hash_equals",
        }:
            available.add("file_exists")
        if "file_content" in available:
            available.add("file_contains")
        if available & {"json_field_equals", "json_schema"}:
            available.add("file_contains")
        return sorted(set(definition.required_postconditions) - available)

    def execute(self, action: TaskAction, goal: GoalState) -> ActionResult:
        normalized = str(action.action_type or "").strip()
        self.definition(normalized)
        try:
            return self._handlers[normalized](goal, dict(action.arguments or {}))
        except Exception as exc:
            return ActionResult(
                action_type=normalized,
                success=False,
                error={"type": type(exc).__name__, "message": str(exc)[:2000]},
            )

    def resolve_path(
        self,
        goal: GoalState,
        value: str | Path,
        *,
        must_exist: bool = False,
    ) -> Path:
        root = Path(goal.workspace_root).resolve(strict=True)
        raw = Path(str(value or "").strip())
        candidate = raw if raw.is_absolute() else root / raw
        resolved = candidate.resolve(strict=must_exist)
        try:
            resolved.relative_to(root)
        except ValueError as exc:
            raise ScopeViolation(f"path escapes goal workspace: {value}") from exc
        return resolved

    def _write_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""))
        content = str(arguments.get("content") or "")
        if path.exists() and not bool(arguments.get("overwrite", True)):
            raise HarnessError(f"file exists and overwrite is false: {path.name}")
        if bool(arguments.get("create_parents", True)):
            path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(path, content)
        return self._file_result("write_file", goal, path, output="file written")

    def _write_json(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        value = arguments.get("value")
        content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self._atomic_write(path, content)
        return self._file_result("write_json", goal, path, output="JSON written")

    def _replace_text(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        old = str(arguments.get("old") or "")
        new = str(arguments.get("new") or "")
        if not old:
            raise HarnessError("replace_text requires non-empty old text")
        content = path.read_text(encoding="utf-8")
        expected = max(1, int(arguments.get("count", 1)))
        occurrences = content.count(old)
        if occurrences < expected:
            if old not in content and content.count(new) >= expected:
                return self._file_result("replace_text", goal, path, output="replacement already present")
            raise HarnessError(f"expected {expected} occurrence(s), found {occurrences}")
        updated = content.replace(old, new, expected)
        self._atomic_write(path, updated)
        return self._file_result("replace_text", goal, path, output=f"replaced {expected} occurrence(s)")

    def _append_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(arguments.get("content") or "")
        with path.open("a", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        return self._file_result("append_file", goal, path, output="content appended")

    def _delete_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""))
        if not path.exists():
            if bool(arguments.get("missing_ok", True)):
                return ActionResult("delete_file", True, output="path already absent")
            raise FileNotFoundError(path)
        if path.is_dir():
            if not bool(arguments.get("recursive", False)):
                path.rmdir()
            else:
                shutil.rmtree(path)
        else:
            path.unlink()
        return ActionResult("delete_file", True, output="path deleted")

    def _make_directory(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""))
        path.mkdir(parents=bool(arguments.get("parents", True)), exist_ok=True)
        return self._file_result("make_directory", goal, path, output="directory created")

    def _copy_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        source = self.resolve_path(goal, arguments.get("source", ""), must_exist=True)
        destination = self.resolve_path(goal, arguments.get("destination", ""))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return self._file_result("copy_file", goal, destination, output="file copied")

    def _read_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("read_file requires a regular file")
        limit = max(1, min(self.output_limit_chars, int(arguments.get("max_chars", self.output_limit_chars))))
        content = path.read_text(encoding=str(arguments.get("encoding") or "utf-8"))
        truncated = len(content) > limit
        return ActionResult(
            "read_file",
            True,
            output=content[:limit],
            artifacts=[self._artifact(goal, path)],
            metadata={"truncated": truncated, "original_chars": len(content)},
        )

    def _bind_evidence(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        lines = path.read_text(encoding="utf-8").splitlines()
        start_line = max(1, int(arguments.get("start_line", 1)))
        end_line = int(arguments.get("end_line", start_line))
        if end_line < start_line or start_line > len(lines):
            raise HarnessError("evidence line span is outside the source")
        end_line = min(end_line, len(lines))
        quote = "\n".join(lines[start_line - 1 : end_line]).strip()
        if not quote:
            raise HarnessError("evidence span is empty")
        relative = str(path.relative_to(Path(goal.workspace_root).resolve()))
        source = str(arguments.get("source") or relative)
        evidence = {
            "source": source,
            "locator": f"{relative}#L{start_line}-L{end_line}",
            "span": {"start_line": start_line, "end_line": end_line},
            "quote": quote,
        }
        return ActionResult(
            "bind_evidence",
            True,
            output=quote,
            artifacts=[self._artifact(goal, path)],
            evidence=[evidence],
        )

    def _run_command(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        argv = arguments.get("argv")
        if not isinstance(argv, list) or not argv or not all(isinstance(item, str) and item for item in argv):
            raise HarnessError("run_command requires a non-empty string argv array")
        cwd = self.resolve_path(goal, arguments.get("cwd", "."), must_exist=True)
        if not cwd.is_dir():
            raise HarnessError("command cwd is not a directory")
        timeout = max(0.1, min(float(arguments.get("timeout", 120.0)), 3600.0))
        inherited_names = ("PATH", "LANG", "LC_ALL", "TZ", "TERM", "SYSTEMROOT")
        environment = {name: os.environ[name] for name in inherited_names if name in os.environ}
        explicit_environment = arguments.get("env") or {}
        if not isinstance(explicit_environment, Mapping):
            raise HarnessError("command env must be an object")
        environment.update({str(key): str(value) for key, value in explicit_environment.items()})
        completed = subprocess.run(
            argv,
            cwd=cwd,
            env=environment,
            shell=False,
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            timeout=timeout,
            check=False,
        )
        output = (completed.stdout or "") + (completed.stderr or "")
        return ActionResult(
            "run_command",
            completed.returncode == 0,
            output=output[: self.output_limit_chars],
            exit_code=completed.returncode,
            metadata={
                "argv": argv,
                "cwd": str(cwd.relative_to(Path(goal.workspace_root))),
                "output_truncated": len(output) > self.output_limit_chars,
            },
            error=(
                None
                if completed.returncode == 0
                else {"type": "CommandFailed", "message": f"exit code {completed.returncode}"}
            ),
        )

    def _check_command(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        result = self._run_command(goal, arguments)
        result.action_type = "check_command"
        return result

    @staticmethod
    def _noop(goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        return ActionResult("noop", True, output=str(arguments.get("output") or "noop"))

    def _file_result(
        self,
        action_type: str,
        goal: GoalState,
        path: Path,
        *,
        output: str,
    ) -> ActionResult:
        return ActionResult(
            action_type,
            True,
            output=output,
            artifacts=[self._artifact(goal, path)],
        )

    @staticmethod
    def _artifact(goal: GoalState, path: Path) -> ObservedArtifact:
        if path.is_file():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            size = path.stat().st_size
        else:
            digest = hashlib.sha256(str(path).encode("utf-8")).hexdigest()
            size = 0
        relative = str(path.relative_to(Path(goal.workspace_root).resolve()))
        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return ObservedArtifact(relative, digest, media_type, size)

    @staticmethod
    def _atomic_write(path: Path, content: str) -> None:
        descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
        finally:
            try:
                os.unlink(temporary)
            except FileNotFoundError:
                pass


__all__ = [
    "ActionDefinition",
    "ActionHarness",
    "ActionResult",
    "HarnessError",
    "ObservedArtifact",
    "ScopeViolation",
]
