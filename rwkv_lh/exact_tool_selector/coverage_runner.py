"""Fail-closed exact-tool coverage collection with immutable raw RWKV records."""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import threading
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.model_io import (
    FINAL_ANSWER_DEFINITION,
    ModelCommand,
    parse_model_command_with_trace,
)
from rwkv_lh.model_session import (
    CandidateGeneration,
    CompletionClient,
    ModelSession,
    SessionSampling,
)
from rwkv_lh.runtime.settings import RuntimeSettings
from rwkv_lh.schema import GoalState, ModelLaneKind, TaskAction

JOURNAL_SCHEMA = "rwkv-lh.exact-tool-coverage-journal.v1"
ATTEMPT_SCHEMA = "rwkv-lh.exact-tool-coverage-attempt.v1"
RUNNER_SCHEMA = "rwkv-lh.exact-tool-coverage-runner.v1"
_SHA256 = frozenset("0123456789abcdef")
_FORBIDDEN_DECODING_FIELDS = {
    "allowed_token_ids",
    "bad_words",
    "grammar",
    "guided_choice",
    "guided_decoding",
    "guided_json",
    "guided_regex",
    "logit_bias",
}


class CoverageRunnerError(RuntimeError):
    """The attempt cannot be admitted without changing its raw causal record."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _require_sha256(name: str, value: str, *, allow_empty: bool = False) -> None:
    if allow_empty and not value:
        return
    if len(value) != 64 or any(character not in _SHA256 for character in value):
        raise ValueError(f"{name} must be a lowercase SHA-256")


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class ExecutorIdentity:
    model: str
    model_sha256: str
    engine_revision: str
    engine_diff_sha256: str
    profile_id: str
    profile_sha256: str

    def __post_init__(self) -> None:
        if not self.model.strip() or not self.engine_revision.strip():
            raise ValueError("Executor model and engine revision must be non-empty")
        _require_sha256("model_sha256", self.model_sha256)
        _require_sha256("engine_diff_sha256", self.engine_diff_sha256)
        if bool(self.profile_id) != bool(self.profile_sha256):
            raise ValueError("Executor profile ID and SHA must be configured together")
        _require_sha256(
            "profile_sha256", self.profile_sha256, allow_empty=not self.profile_id
        )

    def to_dict(self) -> dict[str, str]:
        return asdict(self)


@dataclass(frozen=True)
class CoverageAttemptResult:
    attempt_id: str
    case_id: str
    label: str
    accepted: bool
    raw_output_sha256: str = ""
    error: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class AppendOnlyHashJournal:
    """Fsync every hash-chained JSONL record and reject altered history."""

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._sequence = 0
        self._previous_sha256 = ""
        if self.path.exists():
            records = self.verify(self.path)
            if records:
                self._sequence = int(records[-1]["sequence"])
                self._previous_sha256 = str(records[-1]["record_sha256"])

    @staticmethod
    def verify(path: Path) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        previous = ""
        for expected_sequence, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise CoverageRunnerError(
                    "coverage journal contains invalid JSON"
                ) from exc
            if not isinstance(record, dict):
                raise CoverageRunnerError("coverage journal record must be an object")
            received_sha = str(record.get("record_sha256") or "")
            unsigned = {
                key: value for key, value in record.items() if key != "record_sha256"
            }
            if (
                record.get("schema_version") != JOURNAL_SCHEMA
                or record.get("sequence") != expected_sequence
                or record.get("previous_record_sha256") != previous
                or canonical_sha256(unsigned) != received_sha
            ):
                raise CoverageRunnerError("coverage journal hash chain is invalid")
            records.append(record)
            previous = received_sha
        return records

    def append(self, event_type: str, payload: Mapping[str, Any]) -> dict[str, Any]:
        if not event_type.strip():
            raise ValueError("journal event type must be non-empty")
        with self._lock:
            descriptor = os.open(
                self.path,
                os.O_APPEND | os.O_CREAT | os.O_WRONLY,
                0o600,
            )
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                current = self.verify(self.path) if self.path.exists() else []
                disk_sequence = int(current[-1]["sequence"]) if current else 0
                disk_previous = str(current[-1]["record_sha256"]) if current else ""
                if (
                    disk_sequence != self._sequence
                    or disk_previous != self._previous_sha256
                ):
                    raise CoverageRunnerError("coverage journal changed during append")
                unsigned = {
                    "schema_version": JOURNAL_SCHEMA,
                    "sequence": self._sequence + 1,
                    "previous_record_sha256": self._previous_sha256,
                    "recorded_at": _utc_now(),
                    "event_type": event_type,
                    "payload": dict(payload),
                }
                record = {**unsigned, "record_sha256": canonical_sha256(unsigned)}
                encoded = (canonical_json(record) + "\n").encode("utf-8")
                offset = 0
                while offset < len(encoded):
                    offset += os.write(descriptor, encoded[offset:])
                os.fsync(descriptor)
                self._sequence += 1
                self._previous_sha256 = str(record["record_sha256"])
                return record
            finally:
                fcntl.flock(descriptor, fcntl.LOCK_UN)
                os.close(descriptor)


def _relative_path(value: str) -> Path:
    path = Path(str(value or ""))
    if not str(path) or path.is_absolute() or ".." in path.parts:
        raise CoverageRunnerError(f"fixture path is not workspace-relative: {value!r}")
    return path


def materialize_workspace(case: Mapping[str, Any], root: Path) -> None:
    root.mkdir(parents=True, exist_ok=False)
    fixture = case.get("workspace")
    if not isinstance(fixture, Mapping):
        raise CoverageRunnerError("coverage case has no workspace fixture")
    directories = fixture.get("directories")
    files = fixture.get("files")
    if not isinstance(directories, list) or not isinstance(files, list):
        raise CoverageRunnerError("coverage workspace fixture is malformed")
    for value in sorted(
        (str(item) for item in directories), key=lambda item: item.count("/")
    ):
        (root / _relative_path(value)).mkdir(parents=True, exist_ok=True)
    for item in files:
        if not isinstance(item, Mapping):
            raise CoverageRunnerError("coverage fixture file must be an object")
        target = root / _relative_path(str(item.get("path") or ""))
        target.parent.mkdir(parents=True, exist_ok=True)
        content = item.get("content_utf8")
        if not isinstance(content, str):
            raise CoverageRunnerError("coverage fixture content must be UTF-8 text")
        raw = content.encode("utf-8")
        if len(raw) != item.get("bytes") or hashlib.sha256(raw).hexdigest() != item.get(
            "sha256"
        ):
            raise CoverageRunnerError("coverage fixture file digest mismatch")
        with target.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())


def workspace_snapshot(root: Path) -> dict[str, Any]:
    directories: list[str] = []
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(
        root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()
    ):
        relative = path.relative_to(root).as_posix()
        if path.is_symlink():
            raise CoverageRunnerError(f"workspace contains a symlink: {relative}")
        if path.is_dir():
            directories.append(relative)
        elif path.is_file():
            raw = path.read_bytes()
            files[relative] = {
                "bytes": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        else:
            raise CoverageRunnerError(
                f"workspace contains unsupported path: {relative}"
            )
    snapshot = {"directories": directories, "files": files}
    return {**snapshot, "sha256": canonical_sha256(snapshot)}


def _file_bytes(root: Path, relative: str) -> bytes:
    path = root / _relative_path(relative)
    if not path.is_file():
        raise CoverageRunnerError(f"expected regular file is absent: {relative}")
    return path.read_bytes()


def _assert_unexpected_files_unchanged(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    allowed: Sequence[str] = (),
) -> None:
    allowed_paths = set(allowed)
    before_files = dict(before["files"])
    after_files = dict(after["files"])
    for path in (set(before_files) | set(after_files)) - allowed_paths:
        if before_files.get(path) != after_files.get(path):
            raise CoverageRunnerError(f"unexpected workspace file mutation: {path}")


def _allowed_parent_directories(paths: Sequence[str]) -> set[str]:
    result: set[str] = set()
    for value in paths:
        parent = _relative_path(value).parent
        while str(parent) not in {"", "."}:
            result.add(parent.as_posix())
            parent = parent.parent
    return result


def _assert_unexpected_directories_unchanged(
    before: Mapping[str, Any],
    after: Mapping[str, Any],
    allowed_new: Sequence[str] = (),
) -> None:
    before_directories = set(before["directories"])
    after_directories = set(after["directories"])
    if before_directories - after_directories:
        raise CoverageRunnerError("Executor unexpectedly removed workspace directories")
    unexpected = (after_directories - before_directories) - set(allowed_new)
    if unexpected:
        raise CoverageRunnerError(
            f"Executor unexpectedly created workspace directories: {sorted(unexpected)}"
        )


def _require_json_object(raw: str, kind: str) -> dict[str, Any]:
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CoverageRunnerError(f"{kind} result is not JSON") from exc
    if not isinstance(value, dict):
        raise CoverageRunnerError(f"{kind} result must be an object")
    return value


def verify_operation_result(
    case: Mapping[str, Any],
    result: ActionResult,
    root: Path,
    before: Mapping[str, Any],
    after: Mapping[str, Any],
) -> dict[str, Any]:
    label = str(case.get("label") or "")
    verifier = case.get("verifier")
    if (
        not result.success
        or result.action_type != label
        or not isinstance(verifier, Mapping)
    ):
        raise CoverageRunnerError("Harness action did not return the expected success")
    verifier_type = str(verifier.get("type") or "")
    allowed_files: list[str] = []
    allowed_directories: set[str] = set()

    if verifier_type == "directory_metadata_exact":
        payload = _require_json_object(result.output, verifier_type)
        expected_entries: list[dict[str, Any]] = []
        prefix = str(verifier["root"]).rstrip("/") + "/"
        for path in before["directories"]:
            if str(path).startswith(prefix):
                expected_entries.append({"path": path, "type": "directory"})
        for path, metadata in before["files"].items():
            if str(path).startswith(prefix):
                expected_entries.append(
                    {"path": path, "type": "file", "size_bytes": metadata["bytes"]}
                )
        expected_entries.sort(key=lambda item: item["path"])
        if payload.get("entries") != expected_entries or payload.get(
            "entry_count"
        ) != verifier.get("entry_count"):
            raise CoverageRunnerError("list_directory result differs from fixture")
    elif verifier_type == "search_text_exact":
        payload = _require_json_object(result.output, verifier_type)
        locators = [
            f"{item.get('path')}:{item.get('line_number')}"
            for item in payload.get("matches", [])
            if isinstance(item, Mapping)
        ]
        if (
            locators != verifier.get("ordered_locators")
            or payload.get("complete") is not True
        ):
            raise CoverageRunnerError("search_text locators differ from fixture")
    elif verifier_type == "read_file_exact":
        if (
            hashlib.sha256(result.output.encode()).hexdigest()
            != verifier.get("content_sha256")
            or result.metadata.get("complete") is not True
        ):
            raise CoverageRunnerError("read_file result differs from fixture")
    elif verifier_type == "read_json_canonical_exact":
        if (
            json.loads(result.output) != verifier.get("value")
            or result.metadata.get("complete") is not True
        ):
            raise CoverageRunnerError("read_json result differs from fixture")
    elif verifier_type == "file_digest_exact":
        payload = _require_json_object(result.output, verifier_type)
        if (
            payload.get("path") != verifier.get("path")
            or payload.get("sha256") != verifier.get("sha256")
            or payload.get("size_bytes") != verifier.get("bytes")
        ):
            raise CoverageRunnerError("file_digest result differs from fixture")
    elif verifier_type == "file_content_exact":
        path = str(verifier["path"])
        allowed_files = [path]
        if _file_bytes(root, path) != str(verifier["content_utf8"]).encode():
            raise CoverageRunnerError("write_file result differs from fixture")
    elif verifier_type == "json_value_exact":
        path = str(verifier["path"])
        allowed_files = [path]
        if json.loads(_file_bytes(root, path)) != verifier.get("value"):
            raise CoverageRunnerError("write_json result differs from fixture")
    elif verifier_type == "json_patch_exact":
        path = str(verifier["path"])
        allowed_files = [path]
        expected = {**dict(verifier["before"]), **dict(verifier["updates"])}
        if json.loads(_file_bytes(root, path)) != expected:
            raise CoverageRunnerError("patch_json result differs from fixture")
    elif verifier_type in {
        "replace_text_exact",
        "remove_line_exact",
        "append_once_exact",
    }:
        path = str(verifier["path"])
        allowed_files = [path]
        if _file_bytes(root, path) != str(verifier["after"]).encode():
            raise CoverageRunnerError(f"{label} result differs from fixture")
    elif verifier_type == "directory_exists_exact":
        path = str(verifier["path"])
        if not (root / _relative_path(path)).is_dir():
            raise CoverageRunnerError("make_directory target is absent")
        allowed_directories = _allowed_parent_directories([path]) | {path}
    elif verifier_type == "copy_exact":
        source = str(verifier["source"])
        destination = str(verifier["destination"])
        allowed_files = [destination]
        if hashlib.sha256(_file_bytes(root, source)).hexdigest() != verifier.get(
            "sha256"
        ) or hashlib.sha256(_file_bytes(root, destination)).hexdigest() != verifier.get(
            "sha256"
        ):
            raise CoverageRunnerError("copy_file result differs from fixture")
    elif verifier_type == "move_exact":
        source = str(verifier["source"])
        destination = str(verifier["destination"])
        allowed_files = [source, destination]
        if (root / _relative_path(source)).exists() or hashlib.sha256(
            _file_bytes(root, destination)
        ).hexdigest() != verifier.get("sha256"):
            raise CoverageRunnerError("move_file result differs from fixture")
    elif verifier_type == "path_absent_siblings_unchanged":
        path = str(verifier["path"])
        sibling = str(verifier["sibling_path"])
        allowed_files = [path]
        if (root / _relative_path(path)).exists() or hashlib.sha256(
            _file_bytes(root, sibling)
        ).hexdigest() != verifier.get("sibling_sha256"):
            raise CoverageRunnerError("delete_file scope verifier failed")
    elif verifier_type == "evidence_span_exact":
        expected_locator = (
            f"{verifier['path']}#L{verifier['start_line']}-L{verifier['end_line']}"
        )
        if (
            result.output != verifier.get("quote")
            or len(result.evidence) != 1
            or result.evidence[0].get("locator") != expected_locator
            or result.evidence[0].get("quote") != verifier.get("quote")
        ):
            raise CoverageRunnerError("bind_evidence result differs from fixture")
    elif verifier_type == "read_only_command_exact":
        if result.exit_code != verifier.get("expected_exit_code"):
            raise CoverageRunnerError("check_command exit code differs from fixture")
    elif verifier_type == "mutating_command_effect_exact":
        path = str(verifier["path"])
        allowed_files = [path]
        if (
            result.exit_code != verifier.get("expected_exit_code")
            or _file_bytes(root, path) != str(verifier["content_utf8"]).encode()
        ):
            raise CoverageRunnerError("run_command effect differs from fixture")
    else:
        raise CoverageRunnerError(f"unsupported coverage verifier: {verifier_type}")

    if (
        verifier_type
        in {
            "directory_metadata_exact",
            "search_text_exact",
            "read_file_exact",
            "read_json_canonical_exact",
            "file_digest_exact",
            "evidence_span_exact",
            "read_only_command_exact",
        }
        and before != after
    ):
        raise CoverageRunnerError(f"read-only operation mutated workspace: {label}")
    _assert_unexpected_files_unchanged(before, after, allowed_files)
    allowed_directories |= _allowed_parent_directories(allowed_files)
    _assert_unexpected_directories_unchanged(before, after, sorted(allowed_directories))
    return {
        "verifier_type": verifier_type,
        "passed": True,
        "before_sha256": before["sha256"],
        "after_sha256": after["sha256"],
    }


class ExactToolCoverageRunner:
    """Collect one-attempt causal records without retries, repair, or output rewriting."""

    def __init__(
        self,
        *,
        output_root: Path,
        runtime_settings: RuntimeSettings,
        executor_identity: ExecutorIdentity,
        fixture_manifest_sha256: str,
        completion_client_factory: Callable[[Mapping[str, Any]], CompletionClient],
        sampling: SessionSampling | None = None,
        max_output_tokens: int = 512,
        harness: ActionHarness | None = None,
    ) -> None:
        runtime_settings.validate()
        _require_sha256("fixture_manifest_sha256", fixture_manifest_sha256)
        if runtime_settings.retry_attempts != 1:
            raise ValueError("coverage collection forbids hidden generation retries")
        if not runtime_settings.return_token_ids:
            raise ValueError("coverage collection requires returned token IDs")
        if runtime_settings.model != executor_identity.model:
            raise ValueError("runtime and Executor model identities differ")
        if (
            runtime_settings.state_profile_id != executor_identity.profile_id
            or runtime_settings.state_profile_sha256 != executor_identity.profile_sha256
        ):
            raise ValueError("runtime and Executor profile identities differ")
        selected_sampling = sampling or SessionSampling()
        forbidden = _FORBIDDEN_DECODING_FIELDS & set(asdict(selected_sampling))
        if forbidden:
            raise ValueError(
                f"forbidden decoding fields configured: {sorted(forbidden)}"
            )
        self.output_root = output_root.resolve()
        self.output_root.mkdir(parents=True, exist_ok=True)
        self.runtime_settings = runtime_settings
        self.executor_identity = executor_identity
        self.fixture_manifest_sha256 = fixture_manifest_sha256
        self.completion_client_factory = completion_client_factory
        self.sampling = selected_sampling
        self.max_output_tokens = max(1, int(max_output_tokens))
        self.harness = harness or ActionHarness()
        self.journal = AppendOnlyHashJournal(self.output_root / "journal.jsonl")
        self._raw_commits: dict[str, str] = {}

    def _audit_hook(self, attempt_id: str) -> Callable[[Mapping[str, Any]], None]:
        def commit(event: Mapping[str, Any]) -> None:
            selected = dict(event)
            selected_type = str(selected.get("type") or "")
            if selected_type == "model_session_generation_returned":
                raw_generation = selected.get("raw_generation")
                if not isinstance(raw_generation, Mapping):
                    raise CoverageRunnerError("returned generation lacks raw record")
                raw = raw_generation.get("raw_output")
                raw_sha = raw_generation.get("raw_output_sha256")
                if (
                    not isinstance(raw, str)
                    or hashlib.sha256(raw.encode()).hexdigest() != raw_sha
                    or raw_generation.get("postprocessed") is not False
                ):
                    raise CoverageRunnerError(
                        "returned raw generation is not byte exact"
                    )
                record = self.journal.append(
                    "rwkv_raw_generation_committed",
                    {
                        "attempt_id": attempt_id,
                        "raw_generation": dict(raw_generation),
                        "model_session_event": selected,
                        "raw_output_modified": False,
                    },
                )
                self._raw_commits[str(raw_generation.get("candidate_id") or "")] = str(
                    record["record_sha256"]
                )
            else:
                self.journal.append(
                    "model_session_event",
                    {"attempt_id": attempt_id, "event": selected},
                )

        return commit

    def _definition(self, label: str) -> dict[str, Any]:
        if label == "final_answer":
            return dict(FINAL_ANSWER_DEFINITION)
        definitions = self.harness.g1i_tool_definitions([label])
        if len(definitions) != 1:
            raise CoverageRunnerError("Executor requires exactly one tool definition")
        return definitions[0]

    @staticmethod
    def _execution_target(case: Mapping[str, Any]) -> dict[str, Any]:
        label = str(case["label"])
        if label == "final_answer":
            return {
                "required_facts": list(case["verifier"]["required_facts"]),
                "verified_evidence_path": case["verifier"]["evidence_path"],
                "verified_evidence_sha256": case["verifier"]["evidence_sha256"],
            }
        contract = case.get("executor_contract")
        if not isinstance(contract, Mapping):
            raise CoverageRunnerError("coverage case lacks an Executor contract")
        arguments = contract.get("expected_arguments")
        if not isinstance(arguments, Mapping):
            raise CoverageRunnerError("coverage Executor target is malformed")
        return dict(arguments)

    def _assignment(self, case: Mapping[str, Any]) -> str:
        projection = case["selector_projection"]
        return canonical_json(
            {
                "schema_version": "rwkv-lh.exact-tool-executor-assignment.v1",
                "task_request": projection["task_request"],
                "stage_objective": projection["stage_objective"],
                "controller_selected_operation": case["label"],
                "execution_target": self._execution_target(case),
                "requirements": [
                    "Use only the controller-selected operation.",
                    "Bind its complete parameters to the execution target.",
                    "Return one direct JSON function call and no prose.",
                ],
            }
        )

    def _validate_candidate_identity(self, candidate: CandidateGeneration) -> None:
        if candidate.candidate_id not in self._raw_commits:
            raise CoverageRunnerError("candidate was exposed before raw journal commit")
        if not candidate.raw_token_ids:
            raise CoverageRunnerError("Executor response omitted raw token IDs")
        if not candidate.response_id or not candidate.finish_reason:
            raise CoverageRunnerError("Executor response identity is incomplete")
        if candidate.response_model != self.executor_identity.model:
            raise CoverageRunnerError("Executor response model identity mismatch")
        if (
            candidate.state_profile_id != self.executor_identity.profile_id
            or candidate.state_profile_sha256 != self.executor_identity.profile_sha256
        ):
            raise CoverageRunnerError("Executor response profile identity mismatch")

    def _validate_final(
        self,
        case: Mapping[str, Any],
        command: ModelCommand,
        candidate: CandidateGeneration,
        before: Mapping[str, Any],
        after: Mapping[str, Any],
    ) -> dict[str, Any]:
        if command.name != "final_answer" or set(command.arguments) != {"text"}:
            raise CoverageRunnerError("final boundary must contain one text parameter")
        text = command.arguments.get("text")
        if not isinstance(text, str) or not text.strip() or text != text.strip():
            raise CoverageRunnerError(
                "final answer text must be non-empty and unpadded"
            )
        for fact in case["verifier"]["required_facts"]:
            if str(fact).casefold() not in text.casefold():
                raise CoverageRunnerError(f"final answer omitted required fact: {fact}")
        if before != after:
            raise CoverageRunnerError("final_answer mutated the workspace")
        text_sha = hashlib.sha256(text.encode()).hexdigest()
        return {
            "raw_rwkv_final_output": candidate.raw_output,
            "raw_rwkv_final_output_sha256": candidate.raw_output_sha256,
            "decoded_final_answer_text": text,
            "decoded_final_answer_text_sha256": text_sha,
            "delivered_final_output": text,
            "delivered_final_output_sha256": text_sha,
            "terminal_final_output": text,
            "terminal_final_output_sha256": text_sha,
            "byte_exact_match": True,
            "controller_rewritten": False,
        }

    def run_case(self, case: Mapping[str, Any]) -> CoverageAttemptResult:
        case_id = str(case.get("case_id") or "")
        label = str(case.get("label") or "")
        if not case_id or not label:
            raise CoverageRunnerError("coverage case identity is incomplete")
        attempt_id = f"ATT-{case_id}-{uuid4().hex[:12]}"
        workspace = self.output_root / "workspaces" / attempt_id
        case_digest = canonical_sha256(case)
        self.journal.append(
            "attempt_started",
            {
                "schema_version": ATTEMPT_SCHEMA,
                "attempt_id": attempt_id,
                "case_id": case_id,
                "case_sha256": case_digest,
                "label": label,
                "fixture_manifest_sha256": self.fixture_manifest_sha256,
                "executor_identity": self.executor_identity.to_dict(),
                "sampling": self.sampling.to_dict(),
                "max_output_tokens": self.max_output_tokens,
                "automatic_retry_count": 0,
                "forbidden_decoding_fields": [],
            },
        )
        if label == "ABSTAIN":
            verifier = case.get("verifier")
            if (
                not isinstance(verifier, Mapping)
                or verifier.get("type") != "mechanical_abstain_boundary"
                or verifier.get("raw_output_applicable") is not False
                or case.get("executor_contract") is not None
            ):
                raise CoverageRunnerError("ABSTAIN fixture is not mechanically bounded")
            self.journal.append(
                "attempt_finished",
                {
                    "attempt_id": attempt_id,
                    "case_id": case_id,
                    "label": label,
                    "accepted": True,
                    "executor_called": False,
                    "raw_output_applicable": False,
                    "boundary_rule_id": verifier["rule_id"],
                    "boundary_rule_input_sha256": verifier["rule_input_sha256"],
                },
            )
            return CoverageAttemptResult(attempt_id, case_id, label, True)

        raw_sha = ""
        try:
            materialize_workspace(case, workspace)
            before = workspace_snapshot(workspace)
            self.journal.append(
                "workspace_materialized",
                {
                    "attempt_id": attempt_id,
                    "workspace": str(workspace),
                    "snapshot": before,
                },
            )
            client = self.completion_client_factory(case)
            session = ModelSession(
                client=client,
                settings=self.runtime_settings,
                audit_hook=self._audit_hook(attempt_id),
            )
            checkpoint = session.bootstrap(
                ModelLaneKind.ACTION,
                self._assignment(case),
                [self._definition(label)],
                lane_id=f"L-EXECUTOR-{attempt_id}",
            )
            candidate = session.generate(
                checkpoint,
                sampling=self.sampling,
                max_output_tokens=self.max_output_tokens,
                json_output=True,
            )
            raw_sha = candidate.raw_output_sha256
            self._validate_candidate_identity(candidate)
            command, normalization = parse_model_command_with_trace(
                candidate.raw_output
            )
            self.journal.append(
                "raw_generation_parsed_derived_view",
                {
                    "attempt_id": attempt_id,
                    "candidate_id": candidate.candidate_id,
                    "raw_record_sha256": self._raw_commits[candidate.candidate_id],
                    "raw_output_sha256": raw_sha,
                    "raw_output_modified": False,
                    "parsed_command": command.to_dict(),
                    "normalization": normalization.to_dict(),
                },
            )
            if command.name != label:
                raise CoverageRunnerError(
                    f"Executor returned {command.name!r}, expected {label!r}"
                )
            after_generation = workspace_snapshot(workspace)
            if before != after_generation:
                raise CoverageRunnerError(
                    "model generation mutated the fixture workspace"
                )
            if label == "final_answer":
                final_boundary = self._validate_final(
                    case,
                    command,
                    candidate,
                    before,
                    after_generation,
                )
                verification: dict[str, Any] = {
                    "verifier_type": "final_text_nonempty_byte_exact",
                    "passed": True,
                    "output_non_intervention": final_boundary,
                }
                action_result: dict[str, Any] | None = None
            else:
                expected_contract = case["executor_contract"]
                expected_action = self.harness.normalize_action(
                    TaskAction(label, dict(expected_contract["expected_arguments"]))
                )
                actual_action = self.harness.normalize_action(
                    TaskAction(label, dict(command.arguments))
                )
                if actual_action.arguments != expected_action.arguments:
                    raise CoverageRunnerError(
                        "Executor arguments differ from frozen target"
                    )
                self.journal.append(
                    "harness_execution_started",
                    {
                        "attempt_id": attempt_id,
                        "operation": label,
                        "arguments": dict(actual_action.arguments),
                        "workspace_before_sha256": before["sha256"],
                    },
                )
                goal = GoalState.create(
                    goal_id=f"G-{attempt_id}",
                    request=str(case["selector_projection"]["task_request"]),
                    constraints=("isolated exact-tool coverage fixture",),
                    workspace_root=workspace,
                )
                result = self.harness.execute(actual_action, goal)
                after = workspace_snapshot(workspace)
                verification = verify_operation_result(
                    case, result, workspace, before, after
                )
                action_result = result.to_dict()
            self.journal.append(
                "attempt_finished",
                {
                    "attempt_id": attempt_id,
                    "case_id": case_id,
                    "label": label,
                    "accepted": True,
                    "executor_called": True,
                    "raw_output_sha256": raw_sha,
                    "raw_output_modified": False,
                    "action_result": action_result,
                    "verification": verification,
                },
            )
            return CoverageAttemptResult(
                attempt_id, case_id, label, True, raw_output_sha256=raw_sha
            )
        except Exception as exc:  # noqa: BLE001 - every failed attempt must be journaled
            error = f"{type(exc).__name__}: {exc}"[:2000]
            self.journal.append(
                "attempt_finished",
                {
                    "attempt_id": attempt_id,
                    "case_id": case_id,
                    "label": label,
                    "accepted": False,
                    "raw_output_sha256": raw_sha,
                    "raw_output_modified": False,
                    "error": error,
                },
            )
            return CoverageAttemptResult(
                attempt_id,
                case_id,
                label,
                False,
                raw_output_sha256=raw_sha,
                error=error,
            )


__all__ = [
    "AppendOnlyHashJournal",
    "CoverageAttemptResult",
    "CoverageRunnerError",
    "ExactToolCoverageRunner",
    "ExecutorIdentity",
    "canonical_json",
    "canonical_sha256",
    "file_sha256",
    "materialize_workspace",
    "verify_operation_result",
    "workspace_snapshot",
]
