"""Scoped action harness with explicit side-effect and idempotency metadata."""

from __future__ import annotations

import hashlib
import json
import mimetypes
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.schema import GoalState, TaskAction, ValidationSpec


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
    # Failure observations may only be reused when the action is explicitly
    # confined to deterministic workspace state. Extensions default closed;
    # an external or time-sensitive action must never opt in.
    failure_observation_cacheable: bool = False


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
    outcome_type: str = "pending"

    def __post_init__(self) -> None:
        if not self.outcome_type or self.outcome_type == "pending":
            self.outcome_type = self.classify_outcome(
                success=self.success,
                exit_code=self.exit_code,
                error=self.error,
            )

    @staticmethod
    def classify_outcome(
        *,
        success: bool,
        exit_code: int | None,
        error: Mapping[str, Any] | None,
    ) -> str:
        if success:
            return "success"
        error_type = str((error or {}).get("type") or "")
        if error_type in {"FileNotFoundError", "NotADirectoryError"}:
            return "not_found"
        if error_type in {
            "JSONDecodeError",
            "UnicodeDecodeError",
            "ValueError",
            "TypeError",
            "HarnessError",
            "ScopeViolation",
        }:
            return "invalid"
        if error_type in {"FileExistsError", "AlreadyExists", "Conflict"}:
            return "conflict"
        if error_type in {"TimeoutExpired", "TimeoutError"}:
            return "timeout"
        if exit_code not in {None, 0} or error_type == "CommandFailed":
            return "nonzero"
        return "failed"

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
            "outcome_type": self.outcome_type,
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
            outcome_type=str(raw.get("outcome_type") or "pending"),
        )


class ActionHarness:
    _required_arguments = {
        "write_file": ("path", "content"),
        "write_json": ("path", "value"),
        "replace_text": ("path", "old", "new"),
        "remove_line": ("path", "text"),
        "append_file": ("path", "content"),
        "delete_file": ("path",),
        "make_directory": ("path",),
        "copy_file": ("source", "destination"),
        "list_directory": (),
        "read_file": ("path",),
        "read_json": ("path",),
        "bind_evidence": ("path", "start_line", "end_line"),
        "check_command": ("argv",),
        "run_command": ("argv",),
        "noop": (),
    }
    _g1i_required_arguments = {
        "write_file": ("path", "content", "overwrite", "create_parents"),
    }
    _verifier_candidates = {
        "write_file": (
            "action_succeeded", "file_exists", "file_contains", "file_content",
            "hash_equals", "model_cross_check",
        ),
        "write_json": (
            "action_succeeded", "file_exists", "file_content", "json_field_equals",
            "json_schema", "hash_equals", "model_cross_check",
        ),
        "replace_text": (
            "action_succeeded", "file_exists", "file_contains", "file_not_contains",
            "file_content", "hash_changed", "model_cross_check",
        ),
        "remove_line": (
            "action_succeeded", "file_exists", "file_not_contains", "file_content",
            "hash_changed", "model_cross_check",
        ),
        "append_file": (
            "action_succeeded", "file_exists", "file_contains", "file_content",
            "hash_changed", "model_cross_check",
        ),
        "delete_file": ("action_succeeded", "file_absent"),
        "make_directory": ("action_succeeded", "file_exists"),
        "copy_file": (
            "action_succeeded", "file_exists", "model_cross_check",
        ),
        "list_directory": ("action_succeeded", "model_cross_check"),
        "read_file": (
            "action_succeeded", "file_exists", "model_cross_check",
        ),
        "read_json": (
            "action_succeeded", "file_exists", "json_field_equals", "json_schema",
            "model_cross_check",
        ),
        "bind_evidence": ("action_succeeded", "evidence_bound", "model_cross_check"),
        "check_command": ("action_succeeded", "command_exit_code", "model_cross_check"),
        "run_command": ("action_succeeded", "command_exit_code", "model_cross_check"),
        "noop": ("action_succeeded", "memory_ref_exists", "model_cross_check"),
    }

    _definitions = {
        "write_file": ActionDefinition(
            "write_file", "Atomically write UTF-8 text inside the workspace.", False, True, True, 30.0,
            {
                "path": "relative path",
                "content": "text",
                "overwrite": {
                    "type": "boolean",
                    "const": True,
                    "description": "must be true to preserve idempotent retry",
                },
                "create_parents": "boolean",
            },
            ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "write_json": ActionDefinition(
            "write_json", "Atomically serialize a JSON value inside the workspace.", False, True, True, 30.0,
            {"path": "relative path", "value": "any JSON value"}, ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "replace_text": ActionDefinition(
            "replace_text", "Replace an exact text occurrence in an existing UTF-8 file.", False, True, True, 30.0,
            {
                "path": "relative path",
                "old": "exact text",
                "new": "replacement",
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "positive replacement count",
                },
            },
            ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "remove_line": ActionDefinition(
            "remove_line", "Remove a complete UTF-8 text line from an existing file.", False, True, True, 30.0,
            {"path": "relative path", "text": "line text without newline", "all": "boolean"},
            ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "append_file": ActionDefinition(
            "append_file", "Append UTF-8 text; this action is non-idempotent.", False, True, False, 30.0,
            {"path": "relative path", "content": "text"}, ("file_contains",),
        ),
        "delete_file": ActionDefinition(
            "delete_file", "Delete one explicitly scoped path.", False, True, True, 30.0,
            {"path": "relative path", "missing_ok": "boolean", "recursive": "boolean"}, ("file_absent",),
            failure_observation_cacheable=True,
        ),
        "make_directory": ActionDefinition(
            "make_directory", "Create a directory inside the workspace.", False, True, True, 30.0,
            {"path": "relative path", "parents": "boolean"}, ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "copy_file": ActionDefinition(
            "copy_file", "Copy one scoped file to another scoped path.", False, True, True, 30.0,
            {"source": "relative path", "destination": "relative path"}, ("file_exists",),
            failure_observation_cacheable=True,
        ),
        "list_directory": ActionDefinition(
            "list_directory",
            "List bounded file and directory metadata inside the workspace without reading file contents.",
            True,
            False,
            True,
            30.0,
            {
                "path": "relative directory; defaults to workspace root",
                "recursive": "boolean",
                "max_entries": "positive integer up to 1024",
                "start_after": "optional prior page next_cursor path",
            },
            failure_observation_cacheable=True,
        ),
        "read_file": ActionDefinition(
            "read_file", "Read a UTF-8 file without modifying it.", True, False, True, 30.0,
            {
                "path": "relative path",
                "start_char": "zero-based non-negative integer",
                "max_chars": "positive integer up to 16000",
            },
            failure_observation_cacheable=True,
        ),
        "read_json": ActionDefinition(
            "read_json", "Parse a JSON file and return normalized structured content without modifying it.",
            True, False, True, 30.0,
            {"path": "relative path", "max_chars": "positive integer"},
            failure_observation_cacheable=True,
        ),
        "bind_evidence": ActionDefinition(
            "bind_evidence", "Read an exact line span and retain its source locator and quote.", True, False, True, 30.0,
            {"path": "relative path", "start_line": "1-based integer", "end_line": "inclusive 1-based integer", "source": "source label or URL"},
            ("evidence_bound",),
            failure_observation_cacheable=True,
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
        sandbox_commands: bool = True,
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
        self.sandbox_commands = bool(sandbox_commands)
        self._bubblewrap = shutil.which("bwrap") if self.sandbox_commands else None
        self._definitions = dict(type(self)._definitions)
        self._handlers: dict[str, Callable[[GoalState, dict[str, Any]], ActionResult]] = {
            "write_file": self._write_file,
            "write_json": self._write_json,
            "replace_text": self._replace_text,
            "remove_line": self._remove_line,
            "append_file": self._append_file,
            "delete_file": self._delete_file,
            "make_directory": self._make_directory,
            "copy_file": self._copy_file,
            "list_directory": self._list_directory,
            "read_file": self._read_file,
            "read_json": self._read_json,
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
                "runtime_capabilities": self.runtime_capabilities(),
                "actions": {
                    name: self.action_definition_contract(name)
                    for name in self._definitions
                }
            },
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def runtime_capabilities() -> dict[str, Any]:
        return {
            "command_execution": "argv only; shell=False; workspace scoped",
            "python": {
                "canonical_argv_prefix": ["python", "-m"],
                "resolved_by_harness": str(Path(sys.executable).resolve()),
                "python_alias_available": True,
                "pytest_invocation": ["python", "-m", "pytest"],
            },
            "network": "shared only inside the command sandbox",
        }

    @staticmethod
    def _json_schema_property(specification: Any) -> dict[str, Any]:
        """Convert the authoritative argument description into JSON Schema."""

        if isinstance(specification, Mapping):
            return dict(specification)
        description = str(specification or "").strip()
        lowered = description.casefold()
        schema: dict[str, Any] = {"description": description}
        if "any json value" in lowered:
            return schema
        if "boolean" in lowered:
            schema["type"] = "boolean"
        elif "array" in lowered:
            schema.update({"type": "array", "items": {"type": "string"}})
        elif "integer" in lowered:
            schema["type"] = "integer"
        elif "seconds" in lowered:
            schema["type"] = "number"
        elif "object" in lowered:
            schema["type"] = "object"
        else:
            schema["type"] = "string"
        return schema

    def g1i_tool_definitions(
        self,
        action_types: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the single authoritative tool list for G1i prompting."""

        selected = (
            list(self._definitions)
            if action_types is None
            else [str(item or "").strip() for item in action_types]
        )
        definitions: list[dict[str, Any]] = []
        for name in selected:
            definition = self.definition(name)
            definitions.append(
                {
                    "name": name,
                    "description": definition.description,
                    "parameters": {
                        "type": "object",
                        "properties": {
                            argument: self._json_schema_property(specification)
                            for argument, specification in definition.argument_schema.items()
                        },
                        "required": list(
                            self._g1i_required_arguments.get(
                                name,
                                self._required_arguments.get(name, ()),
                            )
                        ),
                        "additionalProperties": False,
                    },
                }
            )
        return definitions

    def deterministic_verification_specs(
        self,
        action: TaskAction,
    ) -> list[ValidationSpec] | None:
        """Build observable postconditions for built-in actions without a model call."""

        name = str(action.action_type or "").strip()
        if name not in type(self)._definitions:
            return None
        arguments = action.arguments
        specs = [ValidationSpec("action_succeeded", {}, True)]
        path = str(arguments.get("path") or "")
        if name == "write_file":
            specs.append(
                ValidationSpec(
                    "file_content",
                    {
                        "path": path,
                        "expected_content": str(arguments.get("content") or ""),
                        "exact_match": True,
                    },
                    True,
                )
            )
        elif name == "write_json":
            specs.append(
                ValidationSpec(
                    "json_field_equals",
                    {
                        "path": path,
                        "field_path": [],
                        "expected": arguments.get("value"),
                    },
                    True,
                )
            )
        elif name in {"replace_text", "remove_line"}:
            specs.append(ValidationSpec("file_exists", {"path": path}, True))
        elif name == "append_file":
            specs.append(
                ValidationSpec(
                    "file_contains",
                    {"path": path, "text": str(arguments.get("content") or "")},
                    True,
                )
            )
        elif name == "delete_file":
            specs.append(ValidationSpec("file_absent", {"path": path}, True))
        elif name == "make_directory":
            specs.append(ValidationSpec("file_exists", {"path": path}, True))
        elif name == "copy_file":
            specs.append(
                ValidationSpec(
                    "file_exists",
                    {"path": str(arguments.get("destination") or "")},
                    True,
                )
            )
        elif name in {"read_file", "read_json"}:
            specs.append(ValidationSpec("file_exists", {"path": path}, True))
        elif name == "bind_evidence":
            specs.append(ValidationSpec("evidence_bound", {}, True))
        elif name in {"check_command", "run_command"}:
            specs.append(
                ValidationSpec("command_exit_code", {"expected": 0}, True)
            )
        return specs

    def action_definition_contract(self, action_type: str) -> dict[str, Any]:
        """Return the exact argument and recovery contract for one selected action."""

        definition = self.definition(action_type)
        contract = {
            "description": definition.description,
            "read_only": definition.read_only,
            "side_effect": definition.side_effect,
            "idempotent": definition.idempotent,
            "default_timeout": definition.default_timeout,
            "arguments": definition.argument_schema,
            "required_arguments": list(
                self._required_arguments.get(definition.name, ())
            ),
            "required_postconditions": list(definition.required_postconditions),
        }
        if definition.name in {"run_command", "check_command"}:
            contract["runtime_capabilities"] = self.runtime_capabilities()
        return contract

    def verifier_candidates(self, action_type: str) -> tuple[str, ...]:
        """Return verifier kinds that can observe the selected action's effects."""

        definition = self.definition(action_type)
        candidates = list(self._verifier_candidates.get(definition.name, ()))
        candidates.extend(definition.required_postconditions)
        if "action_succeeded" not in candidates:
            candidates.insert(0, "action_succeeded")
        return tuple(dict.fromkeys(candidates))

    def validate_action_contract(self, action: TaskAction) -> None:
        """Reject malformed model actions before they reach a side-effecting handler."""

        definition = self.definition(action.action_type)
        arguments = action.arguments
        if not isinstance(arguments, Mapping):
            raise HarnessError("action arguments must be an object")
        required = self._required_arguments.get(definition.name, ())
        missing = [name for name in required if name not in arguments]
        if missing:
            raise HarnessError(
                f"action {definition.name} is missing required arguments: {missing}"
            )
        unknown = sorted(set(arguments) - set(definition.argument_schema))
        if unknown:
            raise HarnessError(
                f"action {definition.name} has unknown arguments: {unknown}"
            )
        for name in ("path", "source", "destination", "cwd"):
            if name in arguments and (
                not isinstance(arguments[name], str) or not arguments[name].strip()
            ):
                raise HarnessError(
                    f"action {definition.name} argument {name} must be a non-empty string"
                )
            if name in arguments and Path(arguments[name]).is_absolute():
                raise HarnessError(
                    f"action {definition.name} argument {name} must be workspace-relative"
                )
        if definition.name == "replace_text" and "count" in arguments:
            count = arguments["count"]
            if isinstance(count, bool) or not isinstance(count, int) or count < 1:
                raise HarnessError(
                    "action replace_text argument count must be a positive integer"
                )
        if definition.name in {"run_command", "check_command"}:
            argv = arguments.get("argv")
            if not isinstance(argv, list) or not argv or not all(
                isinstance(item, str) and item for item in argv
            ):
                raise HarnessError(
                    f"action {definition.name} argument argv must be a non-empty string array"
                )
        if definition.name == "write_file" and arguments.get("overwrite", True) is not True:
            raise HarnessError(
                "action write_file argument overwrite must be true to preserve idempotent retry"
            )

    def workspace_manifest(
        self,
        goal: GoalState,
        *,
        max_entries: int = 256,
    ) -> dict[str, Any]:
        """Return a bounded metadata-only view of the scoped workspace."""

        root = Path(goal.workspace_root).resolve(strict=True)
        excluded_directories = {".git", ".venv", "node_modules", "__pycache__"}
        entries: list[dict[str, Any]] = []
        truncated = False
        for directory, directory_names, file_names in os.walk(root):
            directory_names[:] = sorted(
                name for name in directory_names if name not in excluded_directories
            )
            current = Path(directory)
            for name in sorted(file_names):
                path = current / name
                try:
                    resolved = path.resolve(strict=True)
                    resolved.relative_to(root)
                    stat = resolved.stat()
                except (FileNotFoundError, OSError, ValueError):
                    continue
                if not resolved.is_file():
                    continue
                entry: dict[str, Any] = {
                    "path": str(resolved.relative_to(root)),
                    "size_bytes": stat.st_size,
                }
                if stat.st_size <= 2_000_000:
                    entry["sha256"] = hashlib.sha256(resolved.read_bytes()).hexdigest()
                entries.append(entry)
                if len(entries) >= max(1, int(max_entries)):
                    truncated = True
                    break
            if truncated:
                break
        return {"entries": entries, "truncated": truncated, "entry_count": len(entries)}

    def workspace_observation_snapshot(
        self,
        goal: GoalState,
        *,
        max_entries: int = 4096,
        max_total_bytes: int = 1_073_741_824,
    ) -> dict[str, Any]:
        """Hash a complete, bounded workspace view for failure reuse.

        This is deliberately stricter than :meth:`workspace_manifest`, which
        is a bounded metadata prompt view. A partial snapshot must never make
        two observations appear equivalent, so any symlink, bound overflow,
        read error, or concurrent file mutation fails closed.
        """

        root = Path(goal.workspace_root).resolve(strict=True)
        entry_limit = max(1, int(max_entries))
        byte_limit = max(1, int(max_total_bytes))
        entries: list[dict[str, Any]] = []
        total_bytes = 0

        def failed(reason: str) -> dict[str, Any]:
            return {
                "schema_version": "rwkv-lh.workspace-observation.v1",
                "cacheable": False,
                "reason": reason,
                "digest": "",
                "entry_count": len(entries),
                "total_bytes": total_bytes,
                "entries": entries,
            }

        try:
            for directory, directory_names, file_names in os.walk(
                root,
                topdown=True,
                followlinks=False,
            ):
                current = Path(directory)
                retained_directories: list[str] = []
                for name in sorted(directory_names):
                    path = current / name
                    if path.is_symlink():
                        return failed(
                            f"symbolic_link_not_cacheable:{path.relative_to(root).as_posix()}"
                        )
                    retained_directories.append(name)
                    if len(entries) >= entry_limit:
                        return failed("workspace_entry_limit_exceeded")
                    entries.append(
                        {
                            "path": path.relative_to(root).as_posix(),
                            "type": "directory",
                        }
                    )
                directory_names[:] = retained_directories

                for name in sorted(file_names):
                    path = current / name
                    relative = path.relative_to(root).as_posix()
                    if path.is_symlink():
                        return failed(f"symbolic_link_not_cacheable:{relative}")
                    if len(entries) >= entry_limit:
                        return failed("workspace_entry_limit_exceeded")
                    before = path.stat()
                    if not path.is_file():
                        return failed(f"non_regular_entry_not_cacheable:{relative}")
                    if total_bytes + before.st_size > byte_limit:
                        return failed("workspace_byte_limit_exceeded")
                    digest = hashlib.sha256(path.read_bytes()).hexdigest()
                    after = path.stat()
                    before_identity = (
                        before.st_dev,
                        before.st_ino,
                        before.st_size,
                        before.st_mtime_ns,
                    )
                    after_identity = (
                        after.st_dev,
                        after.st_ino,
                        after.st_size,
                        after.st_mtime_ns,
                    )
                    if before_identity != after_identity:
                        return failed(f"workspace_changed_during_snapshot:{relative}")
                    total_bytes += after.st_size
                    entries.append(
                        {
                            "path": relative,
                            "type": "file",
                            "size_bytes": after.st_size,
                            "sha256": digest,
                        }
                    )
        except (FileNotFoundError, OSError, ValueError) as exc:
            return failed(f"workspace_snapshot_error:{type(exc).__name__}:{exc}")

        payload = {
            "schema_version": "rwkv-lh.workspace-observation.v1",
            "entries": entries,
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return {
            **payload,
            "cacheable": True,
            "reason": "",
            "digest": hashlib.sha256(encoded).hexdigest(),
            "entry_count": len(entries),
            "total_bytes": total_bytes,
        }

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

    def verification_design_required_postconditions(
        self,
        action_type: str,
    ) -> tuple[str, ...]:
        required = list(self.definition(action_type).required_postconditions)
        if action_type == "write_file" and "file_content" not in required:
            required.append("file_content")
        return tuple(required)

    def missing_verification_design_postconditions(
        self,
        action_type: str,
        validation_kinds: list[str] | tuple[str, ...] | set[str],
    ) -> list[str]:
        available = {str(item or "").strip() for item in validation_kinds}
        missing = self.missing_required_postconditions(action_type, available)
        if action_type == "write_file" and "file_content" not in available:
            missing.append("file_content")
        return sorted(set(missing))

    def execute(self, action: TaskAction, goal: GoalState) -> ActionResult:
        normalized = str(action.action_type or "").strip()
        self.definition(normalized)
        try:
            result = self._handlers[normalized](goal, dict(action.arguments or {}))
            if not result.outcome_type or result.outcome_type == "pending":
                result.outcome_type = ActionResult.classify_outcome(
                    success=result.success,
                    exit_code=result.exit_code,
                    error=result.error,
                )
            return result
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
        expected = arguments.get("count", 1)
        if isinstance(expected, bool) or not isinstance(expected, int) or expected < 1:
            raise HarnessError("replace_text count must be a positive integer")
        occurrences = content.count(old)
        if occurrences < expected:
            if old not in content and content.count(new) >= expected:
                return self._file_result("replace_text", goal, path, output="replacement already present")
            raise HarnessError(f"expected {expected} occurrence(s), found {occurrences}")
        updated = content.replace(old, new, expected)
        self._atomic_write(path, updated)
        return self._file_result("replace_text", goal, path, output=f"replaced {expected} occurrence(s)")

    def _remove_line(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        target = str(arguments.get("text") or "").rstrip("\r\n")
        if not target:
            raise HarnessError("remove_line requires non-empty line text")
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        remove_all = bool(arguments.get("all", True))
        removed = 0
        retained: list[str] = []
        for line in lines:
            is_match = line.rstrip("\r\n") == target
            if is_match and (remove_all or removed == 0):
                removed += 1
                continue
            retained.append(line)
        if removed == 0:
            return self._file_result(
                "remove_line",
                goal,
                path,
                output="line already absent",
            )
        self._atomic_write(path, "".join(retained))
        return self._file_result(
            "remove_line",
            goal,
            path,
            output=f"removed {removed} line(s)",
        )

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

    def _list_directory(
        self,
        goal: GoalState,
        arguments: dict[str, Any],
    ) -> ActionResult:
        root = Path(goal.workspace_root).resolve(strict=True)
        directory = self.resolve_path(
            goal,
            arguments.get("path", "."),
            must_exist=True,
        )
        if not directory.is_dir():
            raise HarnessError("list_directory requires a directory")
        recursive = bool(arguments.get("recursive", False))
        max_entries = max(1, min(1024, int(arguments.get("max_entries", 256))))
        start_after = str(arguments.get("start_after") or "").strip()
        cursor_path = Path(start_after) if start_after else None
        if cursor_path is not None and (
            cursor_path.is_absolute() or ".." in cursor_path.parts
        ):
            raise HarnessError("list_directory start_after is outside workspace scope")
        excluded_directories = {".git", ".venv", "node_modules", "__pycache__"}
        candidates: list[Path] = []
        if recursive:
            for current, directory_names, file_names in os.walk(directory):
                directory_names[:] = sorted(
                    name
                    for name in directory_names
                    if name not in excluded_directories
                )
                current_path = Path(current)
                candidates.extend(current_path / name for name in directory_names)
                candidates.extend(current_path / name for name in sorted(file_names))
        else:
            candidates = sorted(
                (
                    path
                    for path in directory.iterdir()
                    if path.name not in excluded_directories
                ),
                key=lambda path: path.name,
            )
        candidates = sorted(
            candidates,
            key=lambda path: path.relative_to(root).as_posix(),
        )
        if start_after:
            candidates = [
                path
                for path in candidates
                if path.relative_to(root).as_posix() > start_after
            ]

        entries: list[dict[str, Any]] = []
        truncated = False
        for path in candidates:
            if len(entries) >= max_entries:
                truncated = True
                break
            try:
                if path.is_symlink():
                    continue
                resolved = path.resolve(strict=True)
                resolved.relative_to(root)
                stat = resolved.stat()
            except (FileNotFoundError, OSError, ValueError):
                continue
            if resolved.is_dir():
                kind = "directory"
            elif resolved.is_file():
                kind = "file"
            else:
                continue
            entry: dict[str, Any] = {
                "path": resolved.relative_to(root).as_posix(),
                "type": kind,
            }
            if kind == "file":
                entry["size_bytes"] = stat.st_size
            entries.append(entry)

        relative_directory = directory.relative_to(root).as_posix() or "."
        payload: dict[str, Any] = {
            "path": relative_directory,
            "recursive": recursive,
            "entries": entries,
            "entry_count": len(entries),
            "truncated": truncated,
            "next_cursor": entries[-1]["path"] if truncated and entries else "",
        }
        observation_limit = min(self.output_limit_chars, 16_000)
        output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        while entries and len(output) > observation_limit:
            entries.pop()
            payload["entry_count"] = len(entries)
            payload["truncated"] = True
            payload["next_cursor"] = entries[-1]["path"] if entries else start_after
            output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        return ActionResult(
            "list_directory",
            True,
            output=output,
            metadata=dict(payload),
        )

    def _read_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("read_file requires a regular file")
        start = max(0, int(arguments.get("start_char", 0)))
        limit = max(
            1,
            min(
                self.output_limit_chars,
                16_000,
                int(arguments.get("max_chars", 16_000)),
            ),
        )
        content = path.read_text(encoding=str(arguments.get("encoding") or "utf-8"))
        if start > len(content):
            raise HarnessError("read_file start_char is past end of file")
        end = min(len(content), start + limit)
        truncated = end < len(content)
        return ActionResult(
            "read_file",
            True,
            output=content[start:end],
            artifacts=[self._artifact(goal, path)],
            metadata={
                "start_char": start,
                "end_char": end,
                "next_start_char": end if truncated else None,
                "truncated": truncated,
                "complete": not truncated,
                "original_chars": len(content),
            },
        )

    def _read_json(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("read_json requires a regular file")
        value = json.loads(path.read_text(encoding="utf-8"))
        content = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
        limit = max(
            1,
            min(
                self.output_limit_chars,
                int(arguments.get("max_chars", self.output_limit_chars)),
            ),
        )
        truncated = len(content) > limit
        return ActionResult(
            "read_json",
            True,
            output=content[:limit],
            artifacts=[self._artifact(goal, path)],
            metadata={
                "truncated": truncated,
                "original_chars": len(content),
                "json_type": type(value).__name__,
            },
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
        requested_argv = list(argv)
        resolved_argv = list(argv)
        if resolved_argv[0] == "python":
            resolved_argv[0] = str(Path(sys.executable).resolve(strict=True))
        command = list(resolved_argv)
        sandboxed = bool(self._bubblewrap)
        if self._bubblewrap:
            command, sandbox_path = self._bubblewrap_command(goal, cwd, resolved_argv)
            environment["PATH"] = sandbox_path
        completed = subprocess.run(
            command,
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
                "argv": requested_argv,
                "resolved_argv": resolved_argv,
                "executable_resolution": (
                    "python_alias_to_project_runtime"
                    if requested_argv[0] != resolved_argv[0]
                    else "unchanged"
                ),
                "cwd": str(cwd.relative_to(Path(goal.workspace_root))),
                "output_truncated": len(output) > self.output_limit_chars,
                "sandboxed": sandboxed,
                "sandbox_backend": "bubblewrap" if sandboxed else "none",
            },
            error=(
                None
                if completed.returncode == 0
                else {"type": "CommandFailed", "message": f"exit code {completed.returncode}"}
            ),
        )

    def _bubblewrap_command(
        self,
        goal: GoalState,
        cwd: Path,
        argv: list[str],
    ) -> tuple[list[str], str]:
        """Build a read-isolated command sandbox with one writable workspace."""

        workspace = Path(goal.workspace_root).resolve(strict=True)
        sandbox_cwd = Path("/workspace") / cwd.relative_to(workspace)
        child_argv = list(argv)
        executable = child_argv[0]
        resolved_executable: Path | None = None
        if Path(executable).is_absolute():
            resolved_executable = Path(executable).resolve(strict=True)
        elif "/" not in executable:
            located = shutil.which(executable)
            if located:
                resolved_executable = Path(located).resolve(strict=True)

        runtime_root: Path | None = None
        sandbox_runtime = Path("/opt/rwkv-lh-python")
        configured_runtime_root = Path(sys.executable).resolve(strict=True).parent.parent
        if resolved_executable is not None:
            if resolved_executable.is_relative_to(workspace):
                child_argv[0] = str(
                    Path("/workspace") / resolved_executable.relative_to(workspace)
                )
            elif resolved_executable.is_relative_to(Path("/usr")):
                pass
            elif resolved_executable.is_relative_to(configured_runtime_root):
                runtime_root = configured_runtime_root
                child_argv[0] = str(
                    sandbox_runtime / resolved_executable.relative_to(runtime_root)
                )
            else:
                raise HarnessError(
                    "command executable is outside the isolated system/workspace toolchain: "
                    f"{executable}"
                )

        command = [
            str(self._bubblewrap),
            "--die-with-parent",
            "--unshare-all",
            "--share-net",
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
            "/home",
            "--dir",
            "/run",
            "--dir",
            "/opt",
            "--dir",
            "/opt/rwkv-lh-python",
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
            "--bind",
            str(workspace),
            "/workspace",
        ]
        sandbox_path = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
        if runtime_root is not None:
            command.extend(
                [
                    "--ro-bind",
                    str(runtime_root),
                    str(sandbox_runtime),
                ]
            )
            sandbox_path = f"{sandbox_runtime / 'bin'}:{sandbox_path}"
        command.extend(["--chdir", str(sandbox_cwd), *child_argv])
        return command, sandbox_path

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
