"""Scoped action harness with explicit side-effect and idempotency metadata."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.chunks import ChunkingError, slice_text_from_byte_cursor
from rwkv_lh.schema import GoalState, TaskAction, ValidationSpec
from rwkv_lh.token_budget import get_token_count


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
    required_arguments: tuple[str, ...] = ()
    # Capability metadata is part of the same authoritative registration as
    # the model schema and handler.  Existing local definitions derive a safe
    # default from their effect contract; external extensions must declare
    # their network and data boundaries explicitly.
    capability_class: str = ""
    network_access: str = "none"
    data_boundary: str = "workspace"
    side_effect_class: str = ""
    result_schema: str = "rwkv-lh.action-result.v1"
    cache_policy: str = "default"
    recovery_policy: str = ""
    evidence_output: bool = False

    def __post_init__(self) -> None:
        if not self.name.strip() or not self.description.strip():
            raise ValueError("action definition requires name and description")
        if set(self.required_arguments) - set(self.argument_schema):
            raise ValueError(
                f"action {self.name} requires undeclared arguments: "
                f"{sorted(set(self.required_arguments) - set(self.argument_schema))}"
            )
        non_schema = [
            name
            for name, value in self.argument_schema.items()
            if not isinstance(value, Mapping)
        ]
        if non_schema:
            raise ValueError(
                f"action {self.name} arguments must use explicit JSON Schema: {non_schema}"
            )
        if self.network_access not in {"none", "public_web", "structured_source"}:
            raise ValueError(
                f"action {self.name} has unsupported network_access: "
                f"{self.network_access}"
            )
        if not self.capability_class:
            derived_capability = (
                "local.workspace_read"
                if self.read_only and not self.side_effect
                else "local.workspace_mutation"
            )
            object.__setattr__(self, "capability_class", derived_capability)
        if not self.side_effect_class:
            derived_effect = (
                "read_only"
                if self.read_only and not self.side_effect
                else "workspace_mutation"
            )
            object.__setattr__(self, "side_effect_class", derived_effect)
        if not self.recovery_policy:
            object.__setattr__(
                self,
                "recovery_policy",
                "replay_same_action_id" if self.idempotent else "do_not_replay_unknown",
            )
        for field_name in (
            "capability_class",
            "data_boundary",
            "side_effect_class",
            "result_schema",
            "cache_policy",
            "recovery_policy",
        ):
            if not str(getattr(self, field_name) or "").strip():
                raise ValueError(
                    f"action {self.name} requires non-empty {field_name} metadata"
                )

    def parameters_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                name: dict(schema)
                for name, schema in self.argument_schema.items()
            },
            "required": list(self.required_arguments),
            "additionalProperties": False,
        }

    def g1i_definition(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters_schema(),
        }

    def apply_defaults(self, arguments: Mapping[str, Any]) -> dict[str, Any]:
        # JSON-producing models commonly emit ``null`` for an omitted optional
        # field.  Optional null and omission have the same executable meaning in
        # this registry; required fields (including a required arbitrary JSON
        # value) are never removed.
        normalized = {
            name: value
            for name, value in arguments.items()
            if value is not None or name in self.required_arguments
        }
        for name, schema in self.argument_schema.items():
            if name not in normalized and "default" in schema:
                normalized[name] = schema["default"]
        return normalized


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
            "NetworkPolicyRejected",
            "ExternalEvidenceContractError",
        }:
            return (
                "policy_rejected"
                if error_type == "NetworkPolicyRejected"
                else "invalid"
            )
        if error_type in {"FileExistsError", "AlreadyExists", "Conflict"}:
            return "conflict"
        if error_type in {
            "InjectedTransientToolFailure",
            "Transient503",
            "ServiceUnavailable",
            "ConnectionError",
        }:
            return "transient"
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
    _verifier_candidates = {
        "write_file": (
            "action_succeeded", "file_exists", "file_contains", "file_content",
            "hash_equals",
        ),
        "write_json": (
            "action_succeeded", "file_exists", "file_content", "json_field_equals",
            "json_schema", "hash_equals",
        ),
        "patch_json": (
            "action_succeeded", "file_exists", "file_content", "json_field_equals",
            "json_schema", "hash_changed",
        ),
        "replace_text": (
            "action_succeeded", "file_exists", "file_contains", "file_not_contains",
            "file_content", "hash_changed",
        ),
        "remove_line": (
            "action_succeeded", "file_exists", "file_not_contains", "file_content",
            "hash_changed",
        ),
        "append_file": (
            "action_succeeded", "file_exists", "file_contains", "file_content",
            "hash_changed",
        ),
        "delete_file": ("action_succeeded", "file_absent"),
        "make_directory": ("action_succeeded", "file_exists"),
        "copy_file": ("action_succeeded", "file_exists"),
        "move_file": ("action_succeeded", "file_exists", "file_absent"),
        "list_directory": ("action_succeeded",),
        "search_text": ("action_succeeded",),
        "file_digest": ("action_succeeded", "file_exists", "hash_equals"),
        "read_file": ("action_succeeded", "file_exists"),
        "read_json": (
            "action_succeeded", "file_exists", "json_field_equals", "json_schema",
        ),
        "bind_evidence": ("action_succeeded", "evidence_bound"),
        "check_command": ("action_succeeded", "command_exit_code"),
        "run_command": ("action_succeeded", "command_exit_code"),
        "noop": ("action_succeeded", "memory_ref_exists"),
    }

    _definitions = {
        "write_file": ActionDefinition(
            "write_file", "Atomically write UTF-8 text inside the workspace.", False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "content": {"type": "string", "description": "UTF-8 text"},
                "overwrite": {
                    "type": "boolean",
                    "const": True,
                    "default": True,
                    "description": "must be true to preserve idempotent retry",
                },
                "create_parents": {
                    "type": "boolean",
                    "const": True,
                    "default": True,
                    "description": "missing parent directories are created",
                },
            },
            ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path", "content"),
        ),
        "write_json": ActionDefinition(
            "write_json", (
                "Create or replace a complete JSON value atomically from values already "
                "visible in the Task or dependency observations; omitted existing fields "
                "are deleted. RWKV must supply the entire value."
            ), False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "value": {"description": "any JSON value"},
                "overwrite": {
                    "type": "boolean",
                    "const": True,
                    "default": True,
                    "description": "must be true; write_json atomically replaces the complete value",
                },
                "create_parents": {
                    "type": "boolean",
                    "const": True,
                    "default": True,
                    "description": "must be true; missing parent directories are created",
                },
            },
            ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path", "value"),
        ),
        "patch_json": ActionDefinition(
            "patch_json",
            "Update explicit top-level keys in an existing JSON object while preserving every unspecified key.",
            False,
            True,
            True,
            30.0,
            {
                "path": {"type": "string", "description": "relative existing JSON path"},
                "updates": {"type": "object", "description": "explicit top-level replacements"},
            },
            ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path", "updates"),
        ),
        "replace_text": ActionDefinition(
            "replace_text", "Replace an exact text occurrence in an existing UTF-8 file.", False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "old": {"type": "string", "description": "exact text"},
                "new": {"type": "string", "description": "replacement"},
                "count": {
                    "type": "integer",
                    "minimum": 1,
                    "description": "positive replacement count",
                },
                "all": {
                    "type": "boolean",
                    "default": False,
                    "description": "replace every occurrence when true",
                },
            },
            ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path", "old", "new"),
        ),
        "remove_line": ActionDefinition(
            "remove_line", "Remove a complete UTF-8 text line from an existing file.", False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "text": {"type": "string", "description": "line text without newline"},
                "all": {"type": "boolean", "default": False},
            },
            ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path", "text"),
        ),
        "append_file": ActionDefinition(
            "append_file", "Append UTF-8 text; this action is non-idempotent.", False, True, False, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "content": {"type": "string", "description": "UTF-8 text"},
            }, ("file_contains",),
            required_arguments=("path", "content"),
        ),
        "delete_file": ActionDefinition(
            "delete_file", "Delete one explicitly scoped path.", False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "missing_ok": {"type": "boolean", "default": False},
                "recursive": {"type": "boolean", "default": False},
            }, ("file_absent",),
            failure_observation_cacheable=True,
            required_arguments=("path",),
        ),
        "make_directory": ActionDefinition(
            "make_directory", "Create a directory inside the workspace.", False, True, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "parents": {"type": "boolean", "default": True},
            }, ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("path",),
        ),
        "copy_file": ActionDefinition(
            "copy_file", "Duplicate one existing scoped file's exact bytes to a destination; this is the file-copy action.", False, True, True, 30.0,
            {
                "source": {"type": "string", "description": "relative source path"},
                "destination": {"type": "string", "description": "relative destination path"},
            }, ("file_exists",),
            failure_observation_cacheable=True,
            required_arguments=("source", "destination"),
        ),
        "move_file": ActionDefinition(
            "move_file", (
                "Move (rename) one existing scoped file to a destination path; after "
                "success the destination has the exact source bytes and the source no "
                "longer exists. This action is non-idempotent."
            ), False, True, False, 30.0,
            {
                "source": {"type": "string", "description": "relative source path"},
                "destination": {"type": "string", "description": "relative destination path"},
            }, ("file_exists", "file_absent"),
            required_arguments=("source", "destination"),
        ),
        "file_digest": ActionDefinition(
            "file_digest", (
                "Observe the SHA256 hex digest and byte size of one existing scoped "
                "file; read-only and never modifies anything."
            ), True, False, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
            },
            failure_observation_cacheable=True,
            required_arguments=("path",),
        ),
        "list_directory": ActionDefinition(
            "list_directory",
            "List bounded path/type/size metadata only; never reads file contents and never creates or copies files.",
            True,
            False,
            True,
            30.0,
            {
                "path": {"type": "string", "default": ".", "description": "relative directory"},
                "recursive": {"type": "boolean", "default": False},
                "max_entries": {"type": "integer", "minimum": 1, "maximum": 1024, "default": 1024},
                "start_after": {"type": "string", "default": "", "description": "prior page next_cursor path"},
                "max_tokens": {"type": "integer", "minimum": 256, "maximum": 8192, "default": 4096},
            },
            failure_observation_cacheable=True,
        ),
        "search_text": ActionDefinition(
            "search_text",
            (
                "Search workspace UTF-8 lines. mode=regex (default) supports TODO|FIXME; "
                "mode=literal is exact. Returns bounded ordered locators/cursor and never "
                "ranks urgency."
            ),
            True,
            False,
            True,
            30.0,
            {
                "pattern": {
                    "type": "string",
                    "minLength": 1,
                    "description": "literal text or one line-oriented Python regular expression",
                },
                "path": {
                    "type": "string",
                    "default": ".",
                    "description": "workspace-relative file or directory",
                },
                "mode": {
                    "type": "string",
                    "enum": ["literal", "regex"],
                    "default": "regex",
                },
                "case_sensitive": {"type": "boolean", "default": True},
                "recursive": {
                    "type": "boolean",
                    "default": True,
                    "description": "recurse when path is a directory",
                },
                "max_results": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 500,
                    "default": 100,
                },
                "start_after": {
                    "type": "string",
                    "default": "",
                    "description": "opaque prior-page next_cursor; copy exactly",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 256,
                    "maximum": 8192,
                    "default": 4096,
                },
                "max_file_bytes": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 100_000_000,
                    "default": 5_000_000,
                    "description": "skip larger files and report them",
                },
                "max_line_chars": {
                    "type": "integer",
                    "minimum": 80,
                    "maximum": 4000,
                    "default": 800,
                    "description": "maximum returned line excerpt and match text characters",
                },
            },
            failure_observation_cacheable=True,
            required_arguments=("pattern",),
            result_schema="rwkv-lh.search-text-result.v1",
        ),
        "read_file": ActionDefinition(
            "read_file", "Observe one exact tokenizer-bounded UTF-8 byte range; continue only from next_start_byte.", True, False, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "start_byte": {"type": "integer", "minimum": 0, "default": 0},
                "max_tokens": {"type": "integer", "minimum": 256, "maximum": 8192, "default": 4096},
            },
            failure_observation_cacheable=True,
            required_arguments=("path",),
        ),
        "read_json": ActionDefinition(
            "read_json", (
                "Parse an existing JSON file and observe one exact tokenizer-bounded byte "
                "range of its canonical compact representation. It is not applicable to "
                "plain text or key=value content already observed by read_file."
            ),
            True, False, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "start_byte": {
                    "type": "integer",
                    "minimum": 0,
                    "default": 0,
                    "description": "zero-based UTF-8 byte offset in canonical compact JSON",
                },
                "max_tokens": {
                    "type": "integer",
                    "minimum": 256,
                    "maximum": 8192,
                    "default": 4096,
                },
            },
            failure_observation_cacheable=True,
            required_arguments=("path",),
        ),
        "bind_evidence": ActionDefinition(
            "bind_evidence", "Read an exact line span and retain its source locator and quote.", True, False, True, 30.0,
            {
                "path": {"type": "string", "description": "relative path"},
                "start_line": {"type": "integer", "minimum": 1},
                "end_line": {"type": "integer", "minimum": 1},
                "source": {"type": "string", "default": "", "description": "source label or URL"},
                "max_tokens": {"type": "integer", "minimum": 128, "maximum": 4096, "default": 2048},
            },
            ("evidence_bound",),
            failure_observation_cacheable=True,
            required_arguments=("path", "start_line", "end_line"),
        ),
        "check_command": ActionDefinition(
            "check_command", (
                "Run a read-only test, linter, or inspection command with argv and shell "
                "disabled. Set expected_exit_code explicitly when the intended observable "
                "result is nonzero, for example grep returning 1 when no match remains."
            ),
            True, False, True, 120.0,
            {
                "argv": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                "cwd": {"type": "string", "default": ".", "description": "relative directory"},
                "timeout": {"type": "number", "exclusiveMinimum": 0, "maximum": 120.0, "default": 120.0},
                "env": {"type": "object", "default": {}, "description": "explicit environment additions"},
                "expected_exit_code": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "default": 0,
                    "description": "RWKV-declared expected process exit code.",
                },
            },
            ("command_exit_code",),
            required_arguments=("argv",),
            capability_class="local.process_read",
            data_boundary="workspace_process",
            side_effect_class="local_process_read_only",
        ),
        "run_command": ActionDefinition(
            "run_command", (
                "Run a potentially mutating command with argv and shell disabled. Set "
                "expected_exit_code explicitly when the intended result is nonzero."
            ), False, True, False, 120.0,
            {
                "argv": {"type": "array", "items": {"type": "string", "minLength": 1}, "minItems": 1},
                "cwd": {"type": "string", "default": ".", "description": "relative directory"},
                "timeout": {"type": "number", "exclusiveMinimum": 0, "maximum": 120.0, "default": 120.0},
                "env": {"type": "object", "default": {}, "description": "explicit environment additions"},
                "expected_exit_code": {
                    "type": "integer",
                    "minimum": 0,
                    "maximum": 255,
                    "default": 0,
                    "description": "RWKV-declared expected process exit code.",
                },
            },
            ("command_exit_code",),
            required_arguments=("argv",),
            capability_class="local.process_mutation",
            data_boundary="workspace_process",
            side_effect_class="local_process_mutation",
        ),
        "noop": ActionDefinition(
            "noop", "Record an explicit no-op result for control-flow tasks.", True, False, True, 5.0,
            {"output": {"type": "string", "default": ""}},
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
            ]
            | tuple[
                ActionDefinition,
                Callable[[GoalState, dict[str, Any]], ActionResult],
                Callable[[GoalState, dict[str, Any]], ActionResult | None],
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
            "patch_json": self._patch_json,
            "replace_text": self._replace_text,
            "remove_line": self._remove_line,
            "append_file": self._append_file,
            "delete_file": self._delete_file,
            "make_directory": self._make_directory,
            "copy_file": self._copy_file,
            "move_file": self._move_file,
            "list_directory": self._list_directory,
            "search_text": self._search_text,
            "file_digest": self._file_digest,
            "read_file": self._read_file,
            "read_json": self._read_json,
            "bind_evidence": self._bind_evidence,
            "check_command": self._check_command,
            "run_command": self._run_command,
            "noop": self._noop,
        }
        self._recovery_handlers: dict[
            str, Callable[[GoalState, dict[str, Any]], ActionResult | None]
        ] = {}
        for name, item in (actions or {}).items():
            if len(item) == 2:
                definition, handler = item
                recovery_handler = None
            elif len(item) == 3:
                definition, handler, recovery_handler = item
            else:
                raise HarnessError("custom action tuple must contain 2 or 3 items")
            if name != definition.name:
                raise HarnessError("custom action key must match definition.name")
            self.register_action(
                definition,
                handler,
                recovery_handler=recovery_handler,
            )
        self._validate_registry()

    def register_action(
        self,
        definition: ActionDefinition,
        handler: Callable[[GoalState, dict[str, Any]], ActionResult],
        *,
        recovery_handler: (
            Callable[[GoalState, dict[str, Any]], ActionResult | None] | None
        ) = None,
    ) -> None:
        """Register one explicit extension action with recovery metadata."""

        name = str(definition.name or "").strip()
        if not name:
            raise HarnessError("custom action requires a name")
        if name in self._definitions:
            raise HarnessError(f"action is already registered: {name}")
        if not callable(handler):
            raise HarnessError(f"action handler is not callable: {name}")
        if recovery_handler is not None and not callable(recovery_handler):
            raise HarnessError(f"action recovery handler is not callable: {name}")
        self._definitions[name] = definition
        self._handlers[name] = handler
        if recovery_handler is not None:
            self._recovery_handlers[name] = recovery_handler

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

    def g1i_tool_definitions(
        self,
        action_types: tuple[str, ...] | list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Return the single authoritative tool list for G1i prompting."""

        selected = (
            [name for name in self._definitions if name != "noop"]
            if action_types is None
            else [str(item or "").strip() for item in action_types]
        )
        definitions: list[dict[str, Any]] = []
        for name in selected:
            definition = self.definition(name)
            definitions.append(definition.g1i_definition())
        return definitions

    def _validate_registry(self) -> None:
        definition_names = set(self._definitions)
        handler_names = set(self._handlers)
        if definition_names != handler_names:
            raise HarnessError(
                "action registry/handler mismatch: "
                f"missing_handlers={sorted(definition_names - handler_names)}, "
                f"missing_definitions={sorted(handler_names - definition_names)}"
            )
        for name, definition in self._definitions.items():
            if definition.name != name:
                raise HarnessError(
                    f"action registry key {name} differs from definition {definition.name}"
                )
        unknown_recovery = set(self._recovery_handlers) - definition_names
        if unknown_recovery:
            raise HarnessError(
                f"action recovery handler has no definition: {sorted(unknown_recovery)}"
            )

    def deterministic_verification_specs(
        self,
        action: TaskAction,
    ) -> list[ValidationSpec] | None:
        """Build observable postconditions for built-in actions without a model call."""

        name = str(action.action_type or "").strip()
        if name not in self._definitions:
            return None
        arguments = action.arguments
        specs = [ValidationSpec("action_succeeded", {}, True)]
        if name not in type(self)._definitions:
            # Extensions are executable when their own registered contract is
            # fully expressible by the generic action-success observation.
            # Any extension requiring a richer verifier remains fail-closed.
            if set(self._definitions[name].required_postconditions) - {
                "action_succeeded"
            }:
                return None
            return specs
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
        elif name in {"patch_json", "replace_text", "remove_line"}:
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
        elif name == "move_file":
            specs.append(
                ValidationSpec(
                    "file_exists",
                    {"path": str(arguments.get("destination") or "")},
                    True,
                )
            )
            specs.append(
                ValidationSpec(
                    "file_absent",
                    {"path": str(arguments.get("source") or "")},
                    True,
                )
            )
        elif name in {"read_file", "read_json", "file_digest"}:
            specs.append(ValidationSpec("file_exists", {"path": path}, True))
        elif name == "bind_evidence":
            specs.append(ValidationSpec("evidence_bound", {}, True))
        elif name in {"check_command", "run_command"}:
            specs.append(
                ValidationSpec(
                    "command_exit_code",
                    {"expected": int(arguments.get("expected_exit_code", 0))},
                    True,
                )
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
            "required_arguments": list(definition.required_arguments),
            "required_postconditions": list(definition.required_postconditions),
            "capability_class": definition.capability_class,
            "network_access": definition.network_access,
            "data_boundary": definition.data_boundary,
            "side_effect_class": definition.side_effect_class,
            "result_schema": definition.result_schema,
            "cache_policy": definition.cache_policy,
            "recovery_policy": definition.recovery_policy,
            "evidence_output": definition.evidence_output,
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
        required = definition.required_arguments
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
        for argument_name, argument_value in arguments.items():
            schema = definition.argument_schema[argument_name]
            self._validate_argument_schema(
                definition.name,
                argument_name,
                argument_value,
                schema,
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

    def normalize_action(self, action: TaskAction) -> TaskAction:
        """Apply registry defaults, then validate the exact executable action."""

        definition = self.definition(action.action_type)
        explicit, _transformations = self._normalize_explicit_action_interface(
            definition,
            action.arguments or {},
        )
        normalized = TaskAction(
            definition.name,
            definition.apply_defaults(explicit),
        )
        self.validate_action_contract(normalized)
        return normalized

    def normalize_action_with_trace(
        self,
        action: TaskAction,
    ) -> tuple[TaskAction, dict[str, Any]]:
        """Normalize one action and expose every semantics-free interface edit."""

        definition = self.definition(action.action_type)
        raw_arguments = dict(action.arguments or {})
        explicit, interface_transformations = self._normalize_explicit_action_interface(
            definition,
            raw_arguments,
        )
        normalized = TaskAction(
            definition.name,
            definition.apply_defaults(explicit),
        )
        self.validate_action_contract(normalized)
        optional_nulls = sorted(
            name
            for name, value in explicit.items()
            if value is None and name not in definition.required_arguments
        )
        defaults = sorted(
            name
            for name in normalized.arguments
            if name not in explicit or name in optional_nulls
        )
        return normalized, {
            "normalizer_version": "action-arguments.v2",
            "raw_action": {
                "action_type": action.action_type,
                "arguments": raw_arguments,
            },
            "normalized_action": normalized.to_dict(),
            "transformations": [
                *interface_transformations,
                *[f"optional_null:{name}->omitted" for name in optional_nulls],
                *[f"registry_default:{name}" for name in defaults],
            ],
            "controller_semantic_fields_generated": False,
        }

    @staticmethod
    def _normalize_explicit_action_interface(
        definition: ActionDefinition,
        arguments: Mapping[str, Any],
    ) -> tuple[dict[str, Any], list[str]]:
        """Convert a few common argument spellings without inventing values."""

        normalized = dict(arguments)
        transformations: list[str] = []

        def move(alias: str, canonical: str) -> None:
            if alias not in normalized:
                return
            if canonical in normalized:
                if normalized[canonical] != normalized[alias]:
                    raise HarnessError(
                        f"action {definition.name} has conflicting {alias}/{canonical} values"
                    )
                normalized.pop(alias)
                transformations.append(
                    f"explicit_alias:{alias}=duplicate_{canonical}->omitted"
                )
                return
            normalized[canonical] = normalized.pop(alias)
            transformations.append(f"explicit_alias:{alias}->{canonical}")

        if definition.name == "write_json" and "content" in normalized:
            content = normalized.get("content")
            if isinstance(content, str):
                try:
                    content = json.loads(content)
                except json.JSONDecodeError as exc:
                    raise HarnessError(
                        "write_json content string must contain one valid JSON value"
                    ) from exc
                normalized["content"] = content
                transformations.append("explicit_json:content_string->json_value")
            move("content", "value")
        if definition.name == "replace_text":
            move("text", "new")
            if isinstance(normalized.get("count"), str) and str(
                normalized["count"]
            ).casefold() == "all":
                if normalized.get("all") not in {None, True}:
                    raise HarnessError(
                        "replace_text has conflicting count='all' and all=false"
                    )
                normalized.pop("count")
                normalized["all"] = True
                transformations.append("explicit_value:count=all->all=true")
        if definition.name in {"run_command", "check_command"} and "timeout_ms" in normalized:
            milliseconds = normalized.get("timeout_ms")
            if not isinstance(milliseconds, (int, float)) or isinstance(milliseconds, bool):
                raise HarnessError(
                    f"action {definition.name} timeout_ms must be a number of milliseconds"
                )
            seconds = float(milliseconds) / 1000.0
            if "timeout" in normalized:
                if float(normalized["timeout"]) != seconds:
                    raise HarnessError(
                        f"action {definition.name} has conflicting timeout_ms/timeout values"
                    )
                normalized.pop("timeout_ms")
                transformations.append(
                    "explicit_unit:timeout_ms=duplicate_timeout->omitted"
                )
            else:
                normalized.pop("timeout_ms")
                normalized["timeout"] = seconds
                transformations.append("explicit_unit:timeout_ms->timeout_seconds")
        if definition.name in {"run_command", "check_command"} and "shell" in normalized:
            if normalized["shell"] is not False:
                raise HarnessError(
                    f"action {definition.name} shell must be false"
                )
            normalized.pop("shell")
            transformations.append("fixed_policy:shell=false->omitted")
        if definition.name in {"run_command", "check_command"} and normalized.get("env") == []:
            normalized["env"] = {}
            transformations.append("empty_mapping:env=[]->{}")

        # These fields are observation annotations emitted beside explicit
        # operation values. They never select an operation or alter its data.
        for annotation in (
            "content_included",
            "media_type",
            "omission_reason",
            "schema_version",
            "sha256",
            "size_bytes",
        ):
            if annotation in normalized and annotation not in definition.argument_schema:
                normalized.pop(annotation)
                transformations.append(
                    f"nonsemantic_annotation:{annotation}->raw_audit_only"
                )
        return normalized, transformations

    @staticmethod
    def _validate_argument_schema(
        action_name: str,
        argument_name: str,
        value: Any,
        schema: Mapping[str, Any],
    ) -> None:
        """Validate the same compact JSON Schema fragment exposed to RWKV."""

        expected_type = schema.get("type")
        valid_type = True
        if expected_type == "string":
            valid_type = isinstance(value, str)
        elif expected_type == "boolean":
            valid_type = isinstance(value, bool)
        elif expected_type == "integer":
            valid_type = isinstance(value, int) and not isinstance(value, bool)
        elif expected_type == "number":
            valid_type = (
                isinstance(value, (int, float)) and not isinstance(value, bool)
            )
        elif expected_type == "object":
            valid_type = isinstance(value, Mapping)
        elif expected_type == "array":
            valid_type = isinstance(value, list)
        if not valid_type:
            raise HarnessError(
                f"action {action_name} argument {argument_name} must have type {expected_type}"
            )
        if "const" in schema and value != schema["const"]:
            raise HarnessError(
                f"action {action_name} argument {argument_name} must equal {schema['const']!r}"
            )
        if "enum" in schema and value not in schema["enum"]:
            raise HarnessError(
                f"action {action_name} argument {argument_name} must be one of "
                f"{list(schema['enum'])!r}"
            )
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if "minimum" in schema and value < schema["minimum"]:
                raise HarnessError(
                    f"action {action_name} argument {argument_name} must be at least {schema['minimum']}"
                )
            if "maximum" in schema and value > schema["maximum"]:
                raise HarnessError(
                    f"action {action_name} argument {argument_name} must be at most {schema['maximum']}"
                )
            if "exclusiveMinimum" in schema and value <= schema["exclusiveMinimum"]:
                raise HarnessError(
                    f"action {action_name} argument {argument_name} must be greater than {schema['exclusiveMinimum']}"
                )
        if isinstance(value, str) and "minLength" in schema and len(value) < int(schema["minLength"]):
            raise HarnessError(
                f"action {action_name} argument {argument_name} is shorter than minLength"
            )
        if isinstance(value, list):
            if "minItems" in schema and len(value) < int(schema["minItems"]):
                raise HarnessError(
                    f"action {action_name} argument {argument_name} has too few items"
                )
            if "maxItems" in schema and len(value) > int(schema["maxItems"]):
                raise HarnessError(
                    f"action {action_name} argument {argument_name} has too many items"
                )
            if schema.get("uniqueItems") is True:
                canonical_items = [
                    json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                    for item in value
                ]
                if len(set(canonical_items)) != len(canonical_items):
                    raise HarnessError(
                        f"action {action_name} argument {argument_name} items must be unique"
                    )
            item_schema = schema.get("items")
            if isinstance(item_schema, Mapping):
                for index, item in enumerate(value):
                    ActionHarness._validate_argument_schema(
                        action_name,
                        f"{argument_name}[{index}]",
                        item,
                        item_schema,
                    )

    def workspace_manifest(
        self,
        goal: GoalState,
        *,
        max_entries: int = 256,
        max_tokens: int = 2048,
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
        payload: dict[str, Any] = {
            "entries": entries,
            "truncated": truncated,
            "complete": not truncated,
            "entry_count": len(entries),
            "next_cursor": entries[-1]["path"] if truncated and entries else "",
        }
        while entries and get_token_count(
            json.dumps(payload, ensure_ascii=False, sort_keys=True)
        ) > max(128, int(max_tokens)):
            entries.pop()
            payload["entry_count"] = len(entries)
            payload["truncated"] = True
            payload["complete"] = False
            payload["next_cursor"] = entries[-1]["path"] if entries else ""
        if not entries and get_token_count(
            json.dumps(payload, ensure_ascii=False, sort_keys=True)
        ) > max(128, int(max_tokens)):
            raise HarnessError("workspace manifest metadata exceeds its token budget")
        return payload

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

    def execute(self, action: TaskAction, goal: GoalState) -> ActionResult:
        normalized = str(action.action_type or "").strip()
        self.definition(normalized)
        try:
            normalized_action = self.normalize_action(action)
            result = self._handlers[normalized](goal, normalized_action.arguments)
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

    def recover_committed_action(
        self,
        action: TaskAction,
        goal: GoalState,
    ) -> ActionResult | None:
        """Read a committed external snapshot without replaying its provider call."""
        normalized = str(action.action_type or "").strip()
        definition = self.definition(normalized)
        if (
            definition.recovery_policy
            != "resume_committed_snapshot_or_do_not_replay_unknown"
        ):
            return None
        handler = self._recovery_handlers.get(normalized)
        if handler is None:
            return None
        try:
            normalized_action = self.normalize_action(action)
            result = handler(goal, normalized_action.arguments)
            if result is not None and (
                not result.outcome_type or result.outcome_type == "pending"
            ):
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
                error={
                    "type": "CommittedSnapshotRecoveryError",
                    "message": f"{type(exc).__name__}: {exc}"[:2000],
                },
            )

    @contextmanager
    def action_transaction(self, goal: GoalState):
        """Serialize a complete observe→execute→observe unit when a wrapper requires it."""

        del goal
        yield

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
        lexical = Path(os.path.abspath(candidate))
        try:
            lexical.relative_to(root)
        except ValueError as exc:
            raise ScopeViolation(f"path escapes goal workspace: {value}") from exc
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

    def _patch_json(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("patch_json requires a regular file")
        current = json.loads(path.read_text(encoding="utf-8"))
        updates = arguments.get("updates")
        if not isinstance(current, dict):
            raise HarnessError("patch_json requires a top-level JSON object")
        if not isinstance(updates, Mapping):
            raise HarnessError("patch_json updates must be an object")
        updated = {**current, **dict(updates)}
        content = json.dumps(updated, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
        self._atomic_write(path, content)
        return self._file_result(
            "patch_json",
            goal,
            path,
            output="top-level JSON keys updated; unspecified keys preserved",
        )

    def _replace_text(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        old = str(arguments.get("old") or "")
        new = str(arguments.get("new") or "")
        if not old:
            raise HarnessError("replace_text requires non-empty old text")
        content = path.read_text(encoding="utf-8")
        replace_all = bool(arguments.get("all", False))
        expected = content.count(old) if replace_all else arguments.get("count", 1)
        if replace_all and expected == 0:
            if new and new in content:
                return self._file_result(
                    "replace_text", goal, path, output="replacement already present"
                )
            raise HarnessError("replace_text found no occurrence to replace")
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

    def _move_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        source = self.resolve_path(goal, arguments.get("source", ""), must_exist=True)
        if not source.is_file():
            raise HarnessError("move_file source must be an existing file")
        destination = self.resolve_path(goal, arguments.get("destination", ""))
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))
        return self._file_result(
            "move_file",
            goal,
            destination,
            output="file moved; source path no longer exists",
        )

    def _file_digest(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("file_digest requires an existing file")
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        relative = str(path.relative_to(Path(goal.workspace_root).resolve()))
        return ActionResult(
            "file_digest",
            True,
            output=json.dumps(
                {"path": relative, "sha256": digest, "size_bytes": len(data)},
                ensure_ascii=False,
                sort_keys=True,
            ),
            artifacts=[self._artifact(goal, path)],
        )

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
        observation_limit = int(arguments.get("max_tokens", 4096))
        output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        while entries and get_token_count(output) > observation_limit:
            entries.pop()
            payload["entry_count"] = len(entries)
            payload["truncated"] = True
            payload["next_cursor"] = entries[-1]["path"] if entries else start_after
            output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if payload["truncated"] and not entries:
            raise HarnessError(
                "one directory entry exceeds list_directory max_tokens"
            )
        return ActionResult(
            "list_directory",
            True,
            output=output,
            # The independent Selector sees only bounded operation/outcome
            # metadata, never this result body.  Keep the completion bit
            # explicit and shape-compatible with every other cursor-bounded
            # local observation.  Omitting it made persistent long-chain
            # inputs differ from the frozen prefix features after the first
            # directory listing even when that listing was complete.
            metadata={
                **payload,
                "complete": not bool(payload["truncated"]),
            },
        )

    @staticmethod
    def _search_cursor(
        contract_digest: str,
        key: tuple[str, int, int, int],
    ) -> str:
        payload = json.dumps(
            {
                "contract": contract_digest,
                "key": [key[0], key[1], key[2], key[3]],
                "version": 1,
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
        return f"search-v1.{encoded}"

    @staticmethod
    def _parse_search_cursor(
        value: str,
        contract_digest: str,
    ) -> tuple[str, int, int, int] | None:
        selected = str(value or "").strip()
        if not selected:
            return None
        prefix = "search-v1."
        if not selected.startswith(prefix):
            raise HarnessError("search_text start_after is not a v1 search cursor")
        encoded = selected[len(prefix):]
        try:
            padding = "=" * (-len(encoded) % 4)
            decoded = base64.urlsafe_b64decode((encoded + padding).encode("ascii"))
            payload = json.loads(decoded.decode("utf-8"))
        except (ValueError, UnicodeError, json.JSONDecodeError) as exc:
            raise HarnessError("search_text start_after is malformed") from exc
        if not isinstance(payload, Mapping) or payload.get("version") != 1:
            raise HarnessError("search_text start_after has an unsupported version")
        if payload.get("contract") != contract_digest:
            raise HarnessError("search_text start_after belongs to a different search contract")
        key = payload.get("key")
        if (
            not isinstance(key, list)
            or len(key) != 4
            or not isinstance(key[0], str)
            or any(
                not isinstance(item, int) or isinstance(item, bool) or item < 1
                for item in key[1:]
            )
        ):
            raise HarnessError("search_text start_after key is malformed")
        return key[0], key[1], key[2], key[3]

    @staticmethod
    def _search_line_excerpt(
        line: str,
        start: int,
        end: int,
        max_chars: int,
    ) -> tuple[str, int, bool]:
        if len(line) <= max_chars:
            return line, 1, False
        left = max(0, start - max_chars // 3)
        right = min(len(line), left + max_chars)
        if end > right:
            right = min(len(line), end)
            left = max(0, right - max_chars)
        return line[left:right], left + 1, True

    def _search_text(
        self,
        goal: GoalState,
        arguments: dict[str, Any],
    ) -> ActionResult:
        pattern = str(arguments.get("pattern") or "")
        if not pattern:
            raise HarnessError("search_text requires a non-empty pattern")
        if len(pattern) > 4096:
            raise HarnessError("search_text pattern exceeds 4096 characters")
        mode = str(arguments.get("mode") or "regex")
        case_sensitive = bool(arguments.get("case_sensitive", True))
        flags = 0 if case_sensitive else re.IGNORECASE
        expression = pattern if mode == "regex" else re.escape(pattern)
        try:
            matcher = re.compile(expression, flags)
        except re.error as exc:
            raise HarnessError(f"search_text regular expression is invalid: {exc}") from exc

        root = Path(goal.workspace_root).resolve(strict=True)
        raw_path = Path(str(arguments.get("path") or "."))
        probe = root
        symlink_component = False
        for part in raw_path.parts:
            if part in {"", "."}:
                continue
            probe /= part
            if probe.is_symlink():
                symlink_component = True
                break

        recursive = bool(arguments.get("recursive", True))
        max_results = int(arguments.get("max_results", 100))
        max_tokens = int(arguments.get("max_tokens", 4096))
        max_file_bytes = int(arguments.get("max_file_bytes", 5_000_000))
        max_line_chars = int(arguments.get("max_line_chars", 800))
        normalized_path = raw_path.as_posix() or "."
        contract = {
            "case_sensitive": case_sensitive,
            "max_file_bytes": max_file_bytes,
            "mode": mode,
            "path": normalized_path,
            "pattern": pattern,
            "recursive": recursive,
        }
        contract_digest = hashlib.sha256(
            json.dumps(
                contract,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        cursor_key = self._parse_search_cursor(
            str(arguments.get("start_after") or ""),
            contract_digest,
        )

        candidates: list[Path] = []
        skipped: list[dict[str, str]] = []
        skipped_count = 0
        excluded_directories: list[str] = []
        if symlink_component:
            skipped_count = 1
            skipped.append({"path": normalized_path, "reason": "symlink"})
        else:
            target = self.resolve_path(goal, raw_path, must_exist=True)
            normalized_path = target.relative_to(root).as_posix() or "."
            contract["path"] = normalized_path
            refreshed_digest = hashlib.sha256(
                json.dumps(
                    contract,
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            if refreshed_digest != contract_digest:
                contract_digest = refreshed_digest
                cursor_key = self._parse_search_cursor(
                    str(arguments.get("start_after") or ""),
                    contract_digest,
                )
            if target.is_file():
                candidates = [target]
            elif target.is_dir():
                excluded = {".git", ".venv", "node_modules", "__pycache__"}
                if recursive:
                    for current, directory_names, file_names in os.walk(
                        target,
                        topdown=True,
                        followlinks=False,
                    ):
                        current_path = Path(current)
                        retained: list[str] = []
                        for name in sorted(directory_names):
                            directory_path = current_path / name
                            relative = directory_path.relative_to(root).as_posix()
                            if name in excluded:
                                excluded_directories.append(relative)
                            elif directory_path.is_symlink():
                                skipped_count += 1
                                if len(skipped) < 20:
                                    skipped.append({"path": relative, "reason": "symlink"})
                            else:
                                retained.append(name)
                        directory_names[:] = retained
                        candidates.extend(current_path / name for name in sorted(file_names))
                else:
                    candidates = [
                        path
                        for path in target.iterdir()
                        if path.is_file() or path.is_symlink()
                    ]
            else:
                raise HarnessError("search_text path must be a file or directory")

        candidates = sorted(
            candidates,
            key=lambda path: path.relative_to(root).as_posix(),
        )
        matches: list[dict[str, Any]] = []
        match_keys: list[tuple[str, int, int, int]] = []
        files_searched = 0
        has_more = False
        stop_scan = False
        for candidate in candidates:
            relative = candidate.relative_to(root).as_posix()
            try:
                if candidate.is_symlink():
                    skipped_count += 1
                    if len(skipped) < 20:
                        skipped.append({"path": relative, "reason": "symlink"})
                    continue
                resolved = candidate.resolve(strict=True)
                resolved.relative_to(root)
                stat = resolved.stat()
                if not resolved.is_file():
                    continue
                if stat.st_size > max_file_bytes:
                    skipped_count += 1
                    if len(skipped) < 20:
                        skipped.append({"path": relative, "reason": "oversized"})
                    continue
                data = resolved.read_bytes()
            except (FileNotFoundError, OSError, ValueError):
                skipped_count += 1
                if len(skipped) < 20:
                    skipped.append({"path": relative, "reason": "read_error"})
                continue
            if b"\x00" in data:
                skipped_count += 1
                if len(skipped) < 20:
                    skipped.append({"path": relative, "reason": "binary_nul"})
                continue
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                skipped_count += 1
                if len(skipped) < 20:
                    skipped.append({"path": relative, "reason": "invalid_utf8"})
                continue
            files_searched += 1
            for line_number, line in enumerate(text.splitlines(), start=1):
                for found in matcher.finditer(line):
                    key = (
                        relative,
                        line_number,
                        found.start() + 1,
                        found.end() + 1,
                    )
                    if cursor_key is not None and key <= cursor_key:
                        continue
                    if len(matches) >= max_results:
                        has_more = True
                        stop_scan = True
                        break
                    excerpt, excerpt_start, line_truncated = self._search_line_excerpt(
                        line,
                        found.start(),
                        found.end(),
                        max_line_chars,
                    )
                    matched_text = found.group(0)
                    matches.append(
                        {
                            "path": relative,
                            "line_number": line_number,
                            "column": found.start() + 1,
                            "end_column": found.end() + 1,
                            "match_text": matched_text[:max_line_chars],
                            "match_text_truncated": len(matched_text) > max_line_chars,
                            "line_text": excerpt,
                            "line_text_start_column": excerpt_start,
                            "line_text_truncated": line_truncated,
                        }
                    )
                    match_keys.append(key)
                if stop_scan:
                    break
            if stop_scan:
                break

        excluded_directory_count = len(excluded_directories)

        def render_payload() -> dict[str, Any]:
            truncated = has_more
            return {
                "schema_version": "rwkv-lh.search-text-result.v1",
                "path": normalized_path,
                "pattern": pattern,
                "mode": mode,
                "case_sensitive": case_sensitive,
                "recursive": recursive,
                "matches": matches,
                "match_count": len(matches),
                "files_considered": len(candidates),
                "files_searched": files_searched,
                "skipped_file_count": skipped_count,
                "skipped_files": skipped,
                "excluded_directory_count": excluded_directory_count,
                "excluded_directories": excluded_directories[:20],
                "truncated": truncated,
                "complete": not truncated,
                "next_cursor": (
                    self._search_cursor(contract_digest, match_keys[-1])
                    if truncated and match_keys
                    else ""
                ),
            }

        payload = render_payload()
        output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        while get_token_count(output) > max_tokens and skipped:
            skipped.pop()
            payload = render_payload()
            output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        while get_token_count(output) > max_tokens and excluded_directories:
            excluded_directories.pop()
            payload = render_payload()
            output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        while get_token_count(output) > max_tokens and matches:
            matches.pop()
            match_keys.pop()
            has_more = True
            payload = render_payload()
            output = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        if get_token_count(output) > max_tokens or (has_more and not matches):
            raise HarnessError("one search_text result exceeds max_tokens")
        return ActionResult(
            "search_text",
            True,
            output=output,
            metadata={
                "contract_digest": contract_digest,
                "match_count": len(matches),
                "files_considered": len(candidates),
                "files_searched": files_searched,
                "skipped_file_count": skipped_count,
                "truncated": bool(payload["truncated"]),
                "complete": bool(payload["complete"]),
                "next_cursor": str(payload["next_cursor"]),
                "observed_tokens": get_token_count(output),
            },
        )

    def _read_file(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("read_file requires a regular file")
        content = path.read_text(encoding=str(arguments.get("encoding") or "utf-8"))
        relative = path.relative_to(Path(goal.workspace_root).resolve()).as_posix()
        try:
            chunk = slice_text_from_byte_cursor(
                relative,
                content,
                start_byte=int(arguments.get("start_byte", 0)),
                max_tokens=int(arguments.get("max_tokens", 4096)),
            )
        except ChunkingError as exc:
            raise HarnessError(str(exc)) from exc
        descriptor = chunk.descriptor
        source_size = len(content.encode("utf-8"))
        truncated = descriptor.core_end < source_size
        return ActionResult(
            "read_file",
            True,
            output=chunk.text,
            artifacts=[self._artifact(goal, path)],
            metadata={
                "chunk": descriptor.to_dict(),
                "start_byte": descriptor.core_start,
                "end_byte": descriptor.core_end,
                "next_start_byte": descriptor.core_end if truncated else None,
                "truncated": truncated,
                "complete": not truncated,
                "eof": descriptor.core_end == source_size,
                "source_size_bytes": source_size,
                "observed_tokens": get_token_count(chunk.text),
            },
        )

    def _read_json(self, goal: GoalState, arguments: dict[str, Any]) -> ActionResult:
        path = self.resolve_path(goal, arguments.get("path", ""), must_exist=True)
        if not path.is_file():
            raise HarnessError("read_json requires a regular file")
        source = path.read_text(encoding="utf-8")
        value = json.loads(source)
        content = json.dumps(
            value,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        source_bytes = len(source.encode("utf-8"))
        relative = path.relative_to(Path(goal.workspace_root).resolve()).as_posix()
        try:
            chunk = slice_text_from_byte_cursor(
                relative + "#canonical-json",
                content,
                start_byte=int(arguments.get("start_byte", 0)),
                max_tokens=int(arguments.get("max_tokens", 4096)),
                media_type="application/json",
            )
        except ChunkingError as exc:
            raise HarnessError(str(exc)) from exc
        descriptor = chunk.descriptor
        compact_size = len(content.encode("utf-8"))
        truncated = descriptor.core_end < compact_size
        return ActionResult(
            "read_json",
            True,
            output=chunk.text,
            artifacts=[self._artifact(goal, path)],
            metadata={
                "chunk": descriptor.to_dict(),
                "start_byte": descriptor.core_start,
                "end_byte": descriptor.core_end,
                "next_start_byte": descriptor.core_end if truncated else None,
                "truncated": truncated,
                "complete": not truncated,
                "eof": descriptor.core_end == compact_size,
                "canonical_size_bytes": compact_size,
                "source_bytes": source_bytes,
                "representation": "compact_lossless_json",
                "json_type": type(value).__name__,
                "observed_tokens": get_token_count(chunk.text),
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
        if get_token_count(quote) > int(arguments.get("max_tokens", 2048)):
            raise HarnessError(
                "evidence span exceeds max_tokens; request a smaller exact line span"
            )
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
            executable_resolution = "python_alias_to_project_runtime"
        else:
            executable_resolution = "unchanged"
            executable = resolved_argv[0]
            runtime_script: Path | None = None
            if "/" not in executable:
                located = shutil.which(executable)
                if located:
                    candidate = Path(located).absolute()
                    project_venv = Path(sys.prefix).absolute()
                    if candidate.is_relative_to(project_venv):
                        runtime_script = candidate
                if runtime_script is None:
                    candidate = Path(sys.executable).parent / executable
                    if candidate.is_file() and os.access(candidate, os.X_OK):
                        runtime_script = candidate.absolute()
            if runtime_script is not None:
                resolved_argv = [
                    str(Path(sys.executable).resolve(strict=True)),
                    str(runtime_script),
                    *resolved_argv[1:],
                ]
                executable_resolution = "project_runtime_console_script"
        project_runtime_requested = executable_resolution in {
            "python_alias_to_project_runtime",
            "project_runtime_console_script",
        }
        if project_runtime_requested:
            site_packages = (
                Path(sys.prefix)
                / "lib"
                / f"python{sys.version_info.major}.{sys.version_info.minor}"
                / "site-packages"
            )
            environment["PYTHONPATH"] = str(site_packages)
        command = list(resolved_argv)
        sandboxed = bool(self._bubblewrap)
        if self._bubblewrap:
            command, sandbox_path = self._bubblewrap_command(
                goal,
                cwd,
                resolved_argv,
                include_project_venv=project_runtime_requested,
            )
            environment["PATH"] = sandbox_path
            if project_runtime_requested:
                environment["PYTHONPATH"] = (
                    "/opt/rwkv-lh-venv/lib/"
                    f"python{sys.version_info.major}.{sys.version_info.minor}/site-packages"
                )
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
        expected_exit_code = int(arguments.get("expected_exit_code", 0))
        exit_code_matched = completed.returncode == expected_exit_code
        return ActionResult(
            "run_command",
            exit_code_matched,
            output=output,
            exit_code=completed.returncode,
            metadata={
                "argv": requested_argv,
                "resolved_argv": resolved_argv,
                "executable_resolution": executable_resolution,
                "cwd": str(cwd.relative_to(Path(goal.workspace_root))),
                "output_truncated": False,
                "sandboxed": sandboxed,
                "sandbox_backend": "bubblewrap" if sandboxed else "none",
                "expected_exit_code": expected_exit_code,
                "exit_code_matched": exit_code_matched,
            },
            error=(
                None
                if exit_code_matched
                else {
                    "type": "CommandFailed",
                    "message": (
                        f"exit code {completed.returncode}; expected "
                        f"{expected_exit_code}"
                    ),
                }
            ),
        )

    def _bubblewrap_command(
        self,
        goal: GoalState,
        cwd: Path,
        argv: list[str],
        *,
        include_project_venv: bool = False,
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
        venv_root = Path(sys.prefix).resolve(strict=True)
        sandbox_venv = Path("/opt/rwkv-lh-venv")
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
        for index, argument in enumerate(child_argv[1:], start=1):
            path = Path(argument)
            if not path.is_absolute() or not path.exists():
                continue
            resolved_argument = path.resolve(strict=True)
            if resolved_argument.is_relative_to(workspace):
                child_argv[index] = str(
                    Path("/workspace") / resolved_argument.relative_to(workspace)
                )
            elif runtime_root is not None and resolved_argument.is_relative_to(
                runtime_root
            ):
                child_argv[index] = str(
                    sandbox_runtime / resolved_argument.relative_to(runtime_root)
                )
            elif resolved_argument.is_relative_to(venv_root):
                child_argv[index] = str(
                    sandbox_venv / resolved_argument.relative_to(venv_root)
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
            "/opt/rwkv-lh-venv",
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
        if include_project_venv or any(
            Path(argument).is_absolute()
            and Path(argument).exists()
            and Path(argument).resolve(strict=True).is_relative_to(venv_root)
            for argument in argv
        ):
            command.extend(
                [
                    "--ro-bind",
                    str(venv_root),
                    str(sandbox_venv),
                ]
            )
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
