"""Typed, lineage-preserving projections of durable Harness observations.

The durable :class:`ActionResult` is the authority and remains persisted in
full.  This module builds bounded model-facing packets without slicing a JSON
object or asking a summarizer to reproduce source code.  Code/configuration
facts are always literal UTF-8 spans bound to an immutable source digest and
exact byte range.
"""

from __future__ import annotations

import base64
import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import canonical_digest, canonical_json
from rwkv_lh.schema import ChunkDescriptor


OBSERVATION_PACKET_SCHEMA_VERSION = "rwkv-lh.observation-packet.v1"
OBSERVATION_PROJECTION_VERSION = "typed-lineage-observation-funnel.v1"

LOCAL_EXACT_TEXT_OPERATIONS = frozenset({"read_file", "read_json", "bind_evidence"})
STRUCTURED_PAGE_OPERATIONS = frozenset({"list_directory", "search_text"})
COMMAND_OPERATIONS = frozenset({"check_command", "run_command"})
EXTERNAL_EVIDENCE_OPERATIONS = frozenset({"web_search", "connector_lookup"})
SCALAR_OPERATIONS = frozenset(
    {"file_digest", "calculator", "date_diff", "current_time"}
)
MUTATION_OPERATIONS = frozenset(
    {
        "write_file",
        "write_json",
        "patch_json",
        "replace_text",
        "remove_line",
        "append_file",
        "make_directory",
        "copy_file",
        "move_file",
        "delete_file",
    }
)
REGISTERED_OPERATIONS = frozenset(
    LOCAL_EXACT_TEXT_OPERATIONS
    | STRUCTURED_PAGE_OPERATIONS
    | COMMAND_OPERATIONS
    | EXTERNAL_EVIDENCE_OPERATIONS
    | SCALAR_OPERATIONS
    | MUTATION_OPERATIONS
)

_METADATA_KEYS = (
    "complete",
    "truncated",
    "eof",
    "start_byte",
    "end_byte",
    "next_start_byte",
    "source_size_bytes",
    "canonical_size_bytes",
    "source_bytes",
    "representation",
    "valid_json",
    "parse_outcome_complete",
    "parse_error",
    "json_type",
    "observed_tokens",
    "match_count",
    "files_considered",
    "files_searched",
    "skipped_file_count",
    "next_cursor",
    "expected_exit_code",
    "exit_code_matched",
    "output_truncated",
    "network_policy",
    "provider",
    "request_binding_valid",
    "recovered_committed_snapshot",
    "committed_snapshot_recovery_attempted",
    "base_snapshot_sha256",
    "result_snapshot_sha256",
    "snapshot_transition_verified",
    "chunk",
    "source_start_line",
    "source_end_line",
    "command_streams",
)
_STRUCTURED_FIELD_PRIORITY = (
    "full_name",
    "default_branch",
    "html_url",
    "tag_name",
    "published_at",
    "sha",
    "name",
    "version",
    "info",
    "message",
    "current",
    "current_units",
    "timezone",
    "latitude",
    "longitude",
    "DOI",
    "doi",
    "title",
    "published",
    "author",
    "url",
)
_FOCUS_TOKEN_PATTERN = re.compile(
    r"[A-Za-z_][A-Za-z0-9_./:\-]*|\d+(?:\.\d+)*|[\u3400-\u9fff]{2,}"
)
_FOCUS_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "from",
        "with",
        "this",
        "that",
        "into",
        "only",
        "exact",
        "file",
        "code",
        "use",
        "using",
        "需要",
        "这个",
        "进行",
        "然后",
        "现在",
    }
)


class ObservationProjectionError(ValueError):
    """A result claims exact provenance that its bytes do not satisfy."""


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_text(value: str) -> str:
    return _sha256_bytes(value.encode("utf-8"))


def bounded_model_value(value: Any, *, depth: int = 0) -> Any:
    """Bound diagnostic metadata; never use this helper for factual content."""

    if depth >= 4:
        return None
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value[:2000]
    if isinstance(value, Mapping):
        return {
            str(key)[:160]: projected
            for key, item in list(value.items())[:32]
            if (
                projected := bounded_model_value(item, depth=depth + 1)
            )
            is not None
        }
    if isinstance(value, (list, tuple)):
        return [
            projected
            for item in value[:12]
            if (
                projected := bounded_model_value(item, depth=depth + 1)
            )
            is not None
        ]
    return str(value)[:500]


def _project_structured_value(
    value: Any,
    *,
    budget: int,
    depth: int = 0,
) -> tuple[Any | None, bool]:
    """Pack whole literal fields into a budget without truncating a value."""

    limit = max(2, int(budget))
    if value is None or isinstance(value, (bool, int, float)):
        return (value, len(canonical_json(value)) <= limit)
    if isinstance(value, str):
        return (value, True) if len(canonical_json(value)) <= limit else (None, False)
    if depth >= 4:
        return None, False
    if isinstance(value, Mapping):
        raw_keys = list(value)
        keys = [key for key in _STRUCTURED_FIELD_PRIORITY if key in value]
        keys.extend(key for key in raw_keys if key not in keys)
        projected: dict[str, Any] = {}
        complete = True
        for raw_key in keys:
            key = str(raw_key)
            if len(key) > 160:
                complete = False
                continue
            remaining = limit - len(canonical_json(projected)) - len(
                canonical_json(key)
            ) - 2
            if remaining < 2:
                complete = False
                continue
            item, item_complete = _project_structured_value(
                value[raw_key], budget=remaining, depth=depth + 1
            )
            if item is None and value[raw_key] is not None:
                complete = False
                continue
            candidate = {**projected, key: item}
            if len(canonical_json(candidate)) > limit:
                complete = False
                continue
            projected = candidate
            complete = complete and item_complete
        return projected, complete and len(projected) == len(value)
    if isinstance(value, (list, tuple)):
        projected_items: list[Any] = []
        complete = True
        for raw_item in value:
            remaining = limit - len(canonical_json(projected_items)) - 1
            if remaining < 2:
                complete = False
                break
            item, item_complete = _project_structured_value(
                raw_item, budget=remaining, depth=depth + 1
            )
            if item is None and raw_item is not None:
                complete = False
                break
            candidate = [*projected_items, item]
            if len(canonical_json(candidate)) > limit:
                complete = False
                break
            projected_items = candidate
            complete = complete and item_complete
        return projected_items, complete and len(projected_items) == len(value)
    rendered = str(value)
    return (rendered, True) if len(canonical_json(rendered)) <= limit else (None, False)


def project_structured_value(value: Any, *, budget: int) -> dict[str, Any]:
    """Expose a whole-field-only structured projection with source identity."""

    projected, complete = _project_structured_value(value, budget=budget)
    return {
        "value": projected,
        "projection_complete": complete,
        "source_sha256": canonical_digest(value),
        "fact_authority": "literal_projected_fields_only",
    }


def _focus_terms(*values: str) -> tuple[str, ...]:
    terms: list[str] = []
    for value in values:
        for match in _FOCUS_TOKEN_PATTERN.findall(str(value or "").casefold()):
            if match in _FOCUS_STOPWORDS or len(match) < 2:
                continue
            terms.append(match)
    return tuple(sorted(dict.fromkeys(terms), key=lambda item: (-len(item), item)))


def _match_score(text: str, terms: Sequence[str]) -> tuple[int, int]:
    folded = text.casefold()
    matches = tuple(term for term in terms if term and term in folded)
    return sum(len(term) for term in matches), len(matches)


def _line_bounded_window(
    text: str,
    center: int,
    limit: int,
) -> tuple[int, int]:
    size = max(1, min(int(limit), len(text)))
    start = max(0, min(len(text) - size, int(center) - size // 3))
    end = min(len(text), start + size)
    if start:
        newline = text.find("\n", start, min(end, start + size // 3))
        if newline >= 0:
            start = newline + 1
    if end < len(text):
        newline = text.rfind("\n", max(start, end - size // 3), end)
        if newline > start:
            end = newline + 1
    if end <= start:
        end = min(len(text), start + size)
    return start, end


def _exact_windows(
    text: str,
    *,
    focus_text: str,
    total_chars: int,
) -> tuple[tuple[int, int, str], ...]:
    """Select exact head/focus/tail windows; never synthesize their contents."""

    source = str(text)
    limit = max(256, int(total_chars))
    if len(source) <= limit:
        return ((0, len(source), "complete"),)

    edge = max(256, min(1024, limit // 6))
    focus_budget = max(256, limit - 2 * edge)
    candidates: list[tuple[int, int, str]] = [
        (0, edge, "head"),
        (len(source) - edge, len(source), "tail"),
    ]
    folded = source.casefold()
    match: tuple[int, int, str] | None = None
    for term in _focus_terms(focus_text):
        position = folded.find(term)
        if position >= 0:
            start, end = _line_bounded_window(source, position, focus_budget)
            match = (start, end, "focus_exact_match")
            break
    if match is not None:
        candidates.append(match)
    else:
        middle = len(source) // 2
        start, end = _line_bounded_window(source, middle, focus_budget)
        candidates.append((start, end, "middle_coverage"))

    ordered = sorted(candidates, key=lambda item: (item[0], item[1]))
    merged: list[tuple[int, int, str]] = []
    for start, end, basis in ordered:
        if merged and start <= merged[-1][1]:
            previous_start, previous_end, previous_basis = merged[-1]
            merged[-1] = (
                previous_start,
                max(previous_end, end),
                "+".join(dict.fromkeys((previous_basis, basis))),
            )
        else:
            merged.append((start, end, basis))
    return tuple(merged)


def _line_number(text: str, character_offset: int, base_line: int) -> int:
    return max(1, int(base_line)) + text[:character_offset].count("\n")


def _literal_span(
    source: str,
    *,
    character_start: int,
    character_end: int,
    source_ref: str,
    snapshot_sha256: str,
    source_byte_start: int,
    base_line: int,
    selection_basis: str,
    parent_chunk_id: str = "",
    parent_chunk_sha256: str = "",
) -> dict[str, Any]:
    content = source[character_start:character_end]
    relative_start = len(source[:character_start].encode("utf-8"))
    relative_end = len(source[:character_end].encode("utf-8"))
    start_byte = int(source_byte_start) + relative_start
    end_byte = int(source_byte_start) + relative_end
    content_sha256 = _sha256_text(content)
    end_line_offset = character_end
    if character_end > character_start and source[character_end - 1] == "\n":
        end_line_offset -= 1
    identity = {
        "source_ref": source_ref,
        "snapshot_sha256": snapshot_sha256,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "content_sha256": content_sha256,
    }
    return {
        "span_id": f"OBS-SPAN-{canonical_digest(identity)[:20]}",
        "source_ref": source_ref,
        "snapshot_sha256": snapshot_sha256,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "start_line": _line_number(source, character_start, base_line),
        "end_line": _line_number(source, end_line_offset, base_line),
        "content_sha256": content_sha256,
        "content": content,
        "selection_basis": selection_basis,
        "parent_chunk_id": parent_chunk_id,
        "parent_chunk_sha256": parent_chunk_sha256,
    }


def _base_projection(
    result: Mapping[str, Any],
    operation: str,
) -> tuple[dict[str, Any], dict[str, Any], str]:
    selected = dict(result)
    output = str(selected.get("output") or "")
    raw_metadata = selected.get("metadata")
    source_metadata = (
        dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    )
    metadata = {
        key: deepcopy(source_metadata[key])
        for key in _METADATA_KEYS
        if key in source_metadata
    }
    projected: dict[str, Any] = {
        "success": bool(selected.get("success")),
        "outcome_type": str(selected.get("outcome_type") or "pending"),
        "action_type": operation,
    }
    if selected.get("exit_code") is not None:
        projected["exit_code"] = int(selected["exit_code"])
    if isinstance(selected.get("error"), Mapping):
        projected["error"] = bounded_model_value(selected["error"])
    if metadata:
        projected["metadata"] = metadata
    projected["observation"] = {
        "schema_version": OBSERVATION_PACKET_SCHEMA_VERSION,
        "projection_version": OBSERVATION_PROJECTION_VERSION,
        "operation": operation,
        "adapter_registered": operation in REGISTERED_OPERATIONS,
        "raw_result_sha256": canonical_digest(selected),
        "raw_output_sha256": _sha256_text(output),
        "raw_output_chars": len(output),
        "raw_output_bytes": len(output.encode("utf-8")),
        "raw_result_persisted": True,
        "summary_fact_authority": False,
    }
    return projected, source_metadata, output


def _project_local_exact_text(
    result: Mapping[str, Any],
    operation: str,
    *,
    focus_text: str,
    max_exact_chars: int,
) -> dict[str, Any]:
    projected, source_metadata, output = _base_projection(result, operation)
    observation = projected["observation"]
    source_ref = operation
    snapshot_sha256 = _sha256_text(output)
    source_byte_start = 0
    base_line = int(source_metadata.get("source_start_line", 1) or 1)
    parent_chunk_id = ""
    parent_chunk_sha256 = ""
    source_artifact: dict[str, Any] | None = None
    raw_artifacts = [
        dict(item)
        for item in result.get("artifacts") or ()
        if isinstance(item, Mapping)
    ]
    if raw_artifacts:
        artifact = raw_artifacts[0]
        artifact_path = str(artifact.get("path") or "")
        artifact_sha256 = str(artifact.get("sha256") or "")
        artifact_size = artifact.get("size_bytes")
        if (
            not artifact_path
            or re.fullmatch(r"[0-9a-f]{64}", artifact_sha256) is None
            or isinstance(artifact_size, bool)
            or not isinstance(artifact_size, int)
            or artifact_size < 0
        ):
            raise ObservationProjectionError(
                "local exact observation has an invalid source artifact identity"
            )
        source_artifact = {
            "path": artifact_path,
            "sha256": artifact_sha256,
            "size_bytes": artifact_size,
            "media_type": str(artifact.get("media_type") or ""),
            "fact_authority": "harness_file_artifact_identity",
        }
    raw_chunk = source_metadata.get("chunk")
    if isinstance(raw_chunk, Mapping):
        try:
            descriptor = ChunkDescriptor.from_dict(raw_chunk)
        except (TypeError, ValueError) as exc:
            raise ObservationProjectionError(
                "local exact observation has an invalid ChunkDescriptor"
            ) from exc
        output_bytes = output.encode("utf-8")
        if _sha256_bytes(output_bytes) != descriptor.chunk_sha256:
            raise ObservationProjectionError(
                "local exact observation bytes do not match chunk_sha256"
            )
        if len(output_bytes) != descriptor.byte_end - descriptor.byte_start:
            raise ObservationProjectionError(
                "local exact observation byte range does not match its content"
            )
        source_ref = descriptor.source_ref
        snapshot_sha256 = descriptor.source_sha256
        source_byte_start = descriptor.byte_start
        parent_chunk_id = descriptor.chunk_id
        parent_chunk_sha256 = descriptor.chunk_sha256
        observation["source_chunk"] = descriptor.to_dict()
        observation["source_chunk_integrity_valid"] = True
        if source_artifact is not None:
            expected_path = descriptor.source_ref.removesuffix("#canonical-json")
            if source_artifact["path"] != expected_path:
                raise ObservationProjectionError(
                    "local exact observation artifact path does not match source_ref"
                )
            if operation == "read_file" and (
                source_artifact["sha256"] != descriptor.source_sha256
                or source_artifact["size_bytes"]
                != int(source_metadata.get("source_size_bytes", artifact_size) or 0)
            ):
                raise ObservationProjectionError(
                    "read_file artifact identity does not match its source chunk"
                )
    elif operation == "bind_evidence":
        evidence = [
            item
            for item in result.get("evidence") or ()
            if isinstance(item, Mapping)
        ]
        first = evidence[0] if evidence else {}
        source_ref = str(first.get("source_ref") or first.get("source") or operation)
        snapshot_sha256 = str(first.get("snapshot_sha256") or snapshot_sha256)
        source_byte_start = int(first.get("start_byte", 0) or 0)
        base_line = int(first.get("start_line", 1) or 1)
        if first:
            if str(first.get("content_sha256") or "") != _sha256_text(output):
                raise ObservationProjectionError(
                    "bind_evidence content does not match content_sha256"
                )
            if int(first.get("end_byte", 0) or 0) - source_byte_start != len(
                output.encode("utf-8")
            ):
                raise ObservationProjectionError(
                    "bind_evidence byte range does not match its content"
                )

    windows = _exact_windows(
        output,
        focus_text=focus_text,
        total_chars=max_exact_chars,
    )
    exact_spans = [
        _literal_span(
            output,
            character_start=start,
            character_end=end,
            source_ref=source_ref,
            snapshot_sha256=snapshot_sha256,
            source_byte_start=source_byte_start,
            base_line=base_line,
            selection_basis=basis,
            parent_chunk_id=parent_chunk_id,
            parent_chunk_sha256=parent_chunk_sha256,
        )
        for start, end, basis in windows
        if end > start
    ]
    projection_complete = not output or (
        len(exact_spans) == 1
        and exact_spans[0]["start_byte"] == source_byte_start
        and exact_spans[0]["end_byte"]
        == source_byte_start + len(output.encode("utf-8"))
    )
    source_output_end = source_byte_start + len(output.encode("utf-8"))
    unprojected_ranges: list[dict[str, Any]] = []
    cursor = source_byte_start
    for span in sorted(exact_spans, key=lambda item: int(item["start_byte"])):
        start_byte = int(span["start_byte"])
        end_byte = int(span["end_byte"])
        if start_byte > cursor:
            unprojected_ranges.append(
                {
                    "source_ref": source_ref,
                    "snapshot_sha256": snapshot_sha256,
                    "start_byte": cursor,
                    "end_byte": start_byte,
                }
            )
        cursor = max(cursor, end_byte)
    if cursor < source_output_end:
        unprojected_ranges.append(
            {
                "source_ref": source_ref,
                "snapshot_sha256": snapshot_sha256,
                "start_byte": cursor,
                "end_byte": source_output_end,
            }
        )
    observation.update(
        {
            "adapter": "local_exact_text",
            "payload_kind": "exact_utf8_spans",
            "fact_authority": "exact_spans_only",
            "exact_spans": exact_spans,
            "projection_complete": projection_complete,
            "unprojected_content_exists": not projection_complete,
            "unprojected_byte_ranges": unprojected_ranges,
            "continuation": {
                "complete": bool(source_metadata.get("complete", False)),
                "next_start_byte": source_metadata.get("next_start_byte"),
            },
        }
    )
    if source_artifact is not None:
        observation["source_artifact"] = source_artifact
    if not projection_complete:
        metadata = dict(projected.get("metadata") or {})
        metadata.update(
            {
                "projection_complete": False,
                "projection_truncated": True,
                "complete": False,
            }
        )
        projected["metadata"] = metadata
    return projected


def _search_cursor_after(contract_digest: str, match: Mapping[str, Any]) -> str:
    key = [
        str(match.get("path") or ""),
        int(match.get("line_number", 0) or 0),
        int(match.get("column", 0) or 0),
        int(match.get("end_column", 0) or 0),
    ]
    if not contract_digest or not key[0] or any(value < 1 for value in key[1:]):
        return ""
    payload = json.dumps(
        {"contract": contract_digest, "key": key, "version": 1},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    encoded = base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")
    return f"search-v1.{encoded}"


def _search_match_with_lineage(
    match: Mapping[str, Any],
    source_snapshots: Mapping[str, Any],
) -> dict[str, Any]:
    """Validate and identify one exact source line emitted by ``search_text``."""

    selected = dict(match)
    path = str(selected.get("path") or "")
    content = selected.get("line_text")
    expected_content_sha256 = str(selected.get("line_text_sha256") or "")
    snapshot_sha256 = str(source_snapshots.get(path) or "")
    try:
        start_byte = int(selected.get("line_text_start_byte"))
        end_byte = int(selected.get("line_text_end_byte"))
    except (TypeError, ValueError) as exc:
        raise ObservationProjectionError(
            "search_text match lacks an exact UTF-8 byte range"
        ) from exc
    if (
        not path
        or not isinstance(content, str)
        or re.fullmatch(r"[0-9a-f]{64}", expected_content_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256) is None
        or start_byte < 0
        or end_byte < start_byte
    ):
        raise ObservationProjectionError(
            "search_text match has invalid source-line lineage"
        )
    content_bytes = content.encode("utf-8")
    if (
        end_byte - start_byte != len(content_bytes)
        or _sha256_bytes(content_bytes) != expected_content_sha256
    ):
        raise ObservationProjectionError(
            "search_text match bytes do not match its exact line identity"
        )
    identity = {
        "source_ref": path,
        "snapshot_sha256": snapshot_sha256,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "content_sha256": expected_content_sha256,
    }
    selected.update(
        {
            "source_span_id": f"OBS-SPAN-{canonical_digest(identity)[:20]}",
            "source_snapshot_sha256": snapshot_sha256,
            "fact_authority": "exact_utf8_source_line",
        }
    )
    return selected


def _project_structured_page(
    result: Mapping[str, Any],
    operation: str,
    *,
    arguments: Mapping[str, Any],
    structured_budget: int,
) -> dict[str, Any]:
    projected, source_metadata, output = _base_projection(result, operation)
    observation = projected["observation"]
    try:
        payload = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ObservationProjectionError(
            f"{operation} returned a non-JSON structured result"
        ) from exc
    if not isinstance(payload, Mapping):
        raise ObservationProjectionError(
            f"{operation} structured result must be an object"
        )
    item_key = "entries" if operation == "list_directory" else "matches"
    raw_items = payload.get(item_key)
    if not isinstance(raw_items, list) or any(
        not isinstance(item, Mapping) for item in raw_items
    ):
        raise ObservationProjectionError(
            f"{operation} structured items must be an array of objects"
        )

    raw_source_snapshots = (
        dict(payload.get("source_snapshots") or {})
        if operation == "search_text"
        and isinstance(payload.get("source_snapshots"), Mapping)
        else {}
    )
    base = {
        key: deepcopy(value)
        for key, value in payload.items()
        if key != item_key and key != "source_snapshots"
    }
    diagnostic_arrays_projected = True
    for optional_array in ("skipped_files", "excluded_directories"):
        if (
            optional_array in base
            and len(canonical_json({**base, item_key: []}))
            > max(512, int(structured_budget))
        ):
            base.pop(optional_array)
            diagnostic_arrays_projected = False
    typed_items = [
        _search_match_with_lineage(item, raw_source_snapshots)
        if operation == "search_text"
        else dict(item)
        for item in raw_items
    ]
    retained: list[dict[str, Any]] = []
    for item in typed_items:
        candidate_items = [*retained, item]
        candidate = {**base, item_key: candidate_items}
        if operation == "search_text":
            candidate_paths = {
                str(candidate_item.get("path") or "")
                for candidate_item in candidate_items
                if candidate_item.get("path")
            }
            candidate["source_snapshots"] = {
                str(path): digest
                for path, digest in raw_source_snapshots.items()
                if str(path) in candidate_paths
            }
        if len(canonical_json(candidate)) > max(512, int(structured_budget)):
            break
        retained = candidate_items
    projection_complete = len(retained) == len(raw_items)
    model_payload = {**base, item_key: retained}
    model_payload["entry_count" if operation == "list_directory" else "match_count"] = len(
        retained
    )
    if operation == "search_text":
        retained_paths = {
            str(item.get("path") or "") for item in retained if item.get("path")
        }
        model_payload["source_snapshots"] = {
            str(path): digest
            for path, digest in raw_source_snapshots.items()
            if str(path) in retained_paths
        }
    resume_arguments: dict[str, Any] = {}
    if not projection_complete:
        model_payload["truncated"] = True
        model_payload["complete"] = False
        if operation == "list_directory" and retained:
            projection_cursor = str(retained[-1].get("path") or "")
            model_payload["next_cursor"] = projection_cursor
            resume_arguments = {
                "path": str(arguments.get("path") or payload.get("path") or "."),
                "recursive": bool(arguments.get("recursive", payload.get("recursive", False))),
                "start_after": projection_cursor,
            }
        elif operation == "search_text" and retained:
            projection_cursor = _search_cursor_after(
                str(source_metadata.get("contract_digest") or ""), retained[-1]
            )
            if not projection_cursor:
                raise ObservationProjectionError(
                    "search_text projection cannot produce a lossless continuation cursor"
                )
            model_payload["next_cursor"] = projection_cursor
            resume_arguments = {
                "pattern": str(arguments.get("pattern") or payload.get("pattern") or ""),
                "path": str(arguments.get("path") or payload.get("path") or "."),
                "mode": str(arguments.get("mode") or payload.get("mode") or "regex"),
                "case_sensitive": bool(
                    arguments.get("case_sensitive", payload.get("case_sensitive", True))
                ),
                "recursive": bool(arguments.get("recursive", payload.get("recursive", True))),
                "start_after": projection_cursor,
            }
        else:
            raise ObservationProjectionError(
                f"{operation} cannot project even one complete result item"
            )
        metadata = dict(projected.get("metadata") or {})
        metadata.update(
            {
                "source_complete": bool(source_metadata.get("complete", False)),
                "source_next_cursor": str(source_metadata.get("next_cursor") or ""),
                "complete": False,
                "truncated": True,
                "projection_complete": False,
                "projection_truncated": True,
                "next_cursor": str(model_payload.get("next_cursor") or ""),
            }
        )
        projected["metadata"] = metadata

    projected["structured_output"] = model_payload
    observation.update(
        {
            "adapter": "structured_page",
            "payload_kind": "complete_json_items",
            "fact_authority": "literal_structured_fields",
            "projection_complete": projection_complete,
            "source_item_count": len(raw_items),
            "projected_item_count": len(retained),
            "diagnostic_arrays_projected": diagnostic_arrays_projected,
            "resume_arguments": resume_arguments,
        }
    )
    return projected


def _best_record_per_source(
    records: Sequence[Mapping[str, Any]],
    terms: Sequence[str],
) -> list[Mapping[str, Any]]:
    source_order: list[str] = []
    selected: dict[str, tuple[tuple[int, int], int, Mapping[str, Any]]] = {}
    for index, item in enumerate(records):
        source = item.get("source_object")
        source_id = (
            str(source.get("source_object_id") or "")
            if isinstance(source, Mapping)
            else ""
        )
        identity = source_id or str(item.get("url") or "") or str(
            item.get("evidence_record_id") or ""
        )
        if identity not in selected:
            source_order.append(identity)
        spans = [
            str(span.get("text") or "")
            for span in item.get("exact_spans") or ()
            if isinstance(span, Mapping)
        ]
        searchable = "\n".join(
            (
                str(item.get("title") or ""),
                canonical_json(item.get("structured_fields") or {}),
                *spans,
            )
        )
        score = _match_score(searchable, terms)
        previous = selected.get(identity)
        if previous is None or score > previous[0]:
            selected[identity] = (score, index, item)
    if not terms:
        return [selected[identity][2] for identity in source_order]
    ranked = sorted(
        (selected[identity] for identity in source_order),
        key=lambda item: (-item[0][0], -item[0][1], item[1]),
    )
    return [item[2] for item in ranked]


def _project_external_evidence(
    result: Mapping[str, Any],
    operation: str,
    *,
    arguments: Mapping[str, Any],
    focus_text: str,
    evidence_source_limit: int,
    evidence_span_chars: int,
    structured_field_budget: int,
) -> dict[str, Any]:
    projected, source_metadata, _output = _base_projection(result, operation)
    external = source_metadata.get("external_evidence")
    if not isinstance(external, Mapping):
        return _project_generic(
            result,
            operation,
            focus_text=focus_text,
            max_exact_chars=evidence_span_chars,
        )
    raw_records = [
        item for item in result.get("evidence") or () if isinstance(item, Mapping)
    ]
    query = str(arguments.get("query") or "")
    terms = _focus_terms(query, focus_text)
    source_records = _best_record_per_source(raw_records, terms)
    source_index: list[dict[str, Any]] = []
    for source_rank, item in enumerate(source_records, start=1):
        source = item.get("source_object")
        source_id = (
            str(source.get("source_object_id") or "")
            if isinstance(source, Mapping)
            else ""
        )
        url = str(item.get("url") or "")
        title = str(item.get("title") or "")
        source_index.append(
            {
                "projection_rank": source_rank,
                "source_object_id": source_id,
                "evidence_record_id": str(item.get("evidence_record_id") or ""),
                "snapshot_digest": str(item.get("snapshot_digest") or ""),
                "url": url if len(url) <= 1000 else "",
                "url_sha256": _sha256_text(url),
                "title": title if len(title) <= 500 else "",
                "title_sha256": _sha256_text(title),
                "published": str(item.get("published") or ""),
                "match_score": list(
                    _match_score(
                        "\n".join(
                            (
                                title,
                                canonical_json(item.get("structured_fields") or {}),
                                *(
                                    str(span.get("text") or "")
                                    for span in item.get("exact_spans") or ()
                                    if isinstance(span, Mapping)
                                ),
                            )
                        ),
                        terms,
                    )
                ),
                "fact_authority": "routing_metadata_only",
            }
        )
    bounded_source_index: list[dict[str, Any]] = []
    for item in source_index:
        candidate = [*bounded_source_index, item]
        if len(canonical_json(candidate)) > 6000:
            break
        bounded_source_index = candidate
    records: list[dict[str, Any]] = []
    for item in source_records[: max(1, int(evidence_source_limit))]:
        source = item.get("source_object")
        source_id = (
            str(source.get("source_object_id") or "")
            if isinstance(source, Mapping)
            else ""
        )
        candidate_spans = [
            span
            for span in item.get("exact_spans") or ()
            if isinstance(span, Mapping)
        ]
        candidate_spans.sort(
            key=lambda span: _match_score(str(span.get("text") or ""), terms),
            reverse=True,
        )
        spans: list[dict[str, Any]] = []
        for span in candidate_spans[:1]:
            source_text = str(span.get("text") or "")
            folded = source_text.casefold()
            match_position = next(
                (
                    folded.find(term)
                    for term in terms
                    if term and folded.find(term) >= 0
                ),
                -1,
            )
            if len(source_text) <= max(1, int(evidence_span_chars)):
                start, end, basis = 0, len(source_text), "complete"
            elif match_position >= 0:
                start, end = _line_bounded_window(
                    source_text,
                    match_position,
                    max(1, int(evidence_span_chars)),
                )
                basis = "focus_exact_match"
            else:
                start, end, basis = (
                    0,
                    max(1, int(evidence_span_chars)),
                    "head",
                )
            literal = source_text[start:end]
            locator = (
                dict(span.get("locator") or {})
                if isinstance(span.get("locator"), Mapping)
                else {}
            )
            start_char = int(locator.get("start_char", 0) or 0) + start
            end_char = int(locator.get("start_char", 0) or 0) + end
            projected_span: dict[str, Any] = {
                "source_span_id": str(span.get("span_id") or ""),
                "text": literal,
                "text_sha256": _sha256_text(literal),
                "source_text_chars": len(source_text),
                "source_snapshot_sha256": str(item.get("snapshot_digest") or ""),
                "selection_basis": basis,
                "projection": {
                    "source_offset_start": start,
                    "source_offset_end": end,
                    "document_start_char": start_char,
                    "document_end_char": end_char,
                    "complete_source_span": start == 0 and end == len(source_text),
                },
                "source_locator": bounded_model_value(locator),
            }
            if "start_byte" in locator:
                byte_start = int(locator.get("start_byte", 0) or 0) + len(
                    source_text[:start].encode("utf-8")
                )
                byte_end = int(locator.get("start_byte", 0) or 0) + len(
                    source_text[:end].encode("utf-8")
                )
                projected_span["projection"].update(
                    {
                        "document_start_byte": byte_start,
                        "document_end_byte": byte_end,
                    }
                )
                projected_span["byte_locator_verified"] = True
            else:
                projected_span["byte_locator_verified"] = False
            spans.append(projected_span)
        structured, structured_complete = _project_structured_value(
            item.get("structured_fields") or {},
            budget=max(8, int(structured_field_budget)),
        )
        span_projection_complete = bool(spans) and all(
            bool(span["projection"]["complete_source_span"]) for span in spans
        )
        record_projection_complete = structured_complete and (
            not candidate_spans or span_projection_complete
        )
        records.append(
            {
                "evidence_record_id": str(item.get("evidence_record_id") or ""),
                "source_object_id": source_id,
                "source_object_type": (
                    str(source.get("source_object_type") or "")
                    if isinstance(source, Mapping)
                    else ""
                ),
                "snapshot_digest": str(item.get("snapshot_digest") or ""),
                "url": str(item.get("url") or ""),
                "title": str(item.get("title") or ""),
                "published": str(item.get("published") or ""),
                "structured_fields": structured or {},
                "structured_fields_projection_complete": structured_complete,
                "exact_spans": spans,
                "fact_authority": "exact_spans_or_literal_structured_fields_only",
                "projection_complete": record_projection_complete,
            }
        )
    external_identity = {
        key: bounded_model_value(external.get(key))
        for key in (
            "route_id",
            "request_digest",
            "status",
            "as_of",
            "provider_attempts",
            "truncated",
        )
        if external.get(key) is not None
    }
    projection_complete = (
        len(records) == len(source_records)
        and len(bounded_source_index) == len(source_index)
        and all(bool(record["projection_complete"]) for record in records)
    )
    projected["metadata"] = {
        "network_policy": bounded_model_value(source_metadata.get("network_policy") or {}),
        "provider": str(source_metadata.get("provider") or ""),
        "external_evidence": external_identity,
        "projection_complete": projection_complete,
    }
    projected["evidence"] = records
    projected["evidence_source_index"] = bounded_source_index
    projected["evidence_projection"] = {
        "full_record_count": len(raw_records),
        "full_source_count": len(source_records),
        "projected_source_index_count": len(bounded_source_index),
        "projected_source_count": len(records),
        "content_addressed_full_result_persisted": True,
        "selection_protocol": OBSERVATION_PROJECTION_VERSION,
        "query_digest": _sha256_text(query),
    }
    projected["observation"].update(
        {
            "adapter": "external_evidence",
            "payload_kind": "lineage_bound_evidence",
            "fact_authority": "exact_spans_or_literal_structured_fields_only",
            "projection_complete": projection_complete,
        }
    )
    return projected


def _project_command(
    result: Mapping[str, Any],
    operation: str,
    *,
    focus_text: str,
    max_exact_chars: int,
) -> dict[str, Any]:
    projected, source_metadata, output = _base_projection(result, operation)
    streams = source_metadata.get("command_streams")
    stream_values: list[tuple[str, str]] = []
    if isinstance(streams, Mapping):
        output_bytes = output.encode("utf-8")
        for name in ("stdout", "stderr"):
            value = streams.get(name)
            if isinstance(value, str):
                stream_values.append((name, value))
                continue
            if not isinstance(value, Mapping):
                continue
            try:
                start_byte = int(value.get("start_byte", 0))
                end_byte = int(value.get("end_byte", 0))
                stream_bytes = output_bytes[start_byte:end_byte]
                stream_text = stream_bytes.decode("utf-8")
            except (TypeError, ValueError, UnicodeDecodeError) as exc:
                raise ObservationProjectionError(
                    f"{operation} has an invalid {name} byte range"
                ) from exc
            if (
                start_byte < 0
                or end_byte < start_byte
                or end_byte > len(output_bytes)
                or int(value.get("bytes", len(stream_bytes))) != len(stream_bytes)
                or str(value.get("sha256") or "") != _sha256_bytes(stream_bytes)
            ):
                raise ObservationProjectionError(
                    f"{operation} {name} bytes do not match command_streams metadata"
                )
            stream_values.append((name, stream_text))
    if not stream_values:
        stream_values = [("combined", output)]
    per_stream = max(256, int(max_exact_chars) // max(1, len(stream_values)))
    projected_streams: list[dict[str, Any]] = []
    for stream_name, stream_text in stream_values:
        stream_digest = _sha256_text(stream_text)
        exact_spans = [
            _literal_span(
                stream_text,
                character_start=start,
                character_end=end,
                source_ref=f"command:{operation}:{stream_name}",
                snapshot_sha256=stream_digest,
                source_byte_start=0,
                base_line=1,
                selection_basis=basis,
            )
            for start, end, basis in _exact_windows(
                stream_text,
                focus_text=focus_text,
                total_chars=per_stream,
            )
            if end > start
        ]
        projected_streams.append(
            {
                "stream": stream_name,
                "stream_sha256": stream_digest,
                "stream_chars": len(stream_text),
                "stream_bytes": len(stream_text.encode("utf-8")),
                "projection_complete": (
                    not stream_text
                    or (
                        len(exact_spans) == 1
                        and exact_spans[0]["start_byte"] == 0
                        and exact_spans[0]["end_byte"]
                        == len(stream_text.encode("utf-8"))
                    )
                ),
                "exact_spans": exact_spans,
            }
        )
    projection_complete = all(
        item["projection_complete"] for item in projected_streams
    )
    projected["command_streams"] = projected_streams
    projected["observation"].update(
        {
            "adapter": "command_streams",
            "payload_kind": "exact_utf8_spans",
            "fact_authority": "exit_code_and_exact_stream_spans",
            "projection_complete": projection_complete,
        }
    )
    if not projection_complete:
        metadata = dict(projected.get("metadata") or {})
        metadata.update(
            {
                "projection_complete": False,
                "projection_truncated": True,
                "complete": False,
            }
        )
        projected["metadata"] = metadata
    return projected


def _project_generic(
    result: Mapping[str, Any],
    operation: str,
    *,
    focus_text: str,
    max_exact_chars: int,
) -> dict[str, Any]:
    projected, _source_metadata, output = _base_projection(result, operation)
    if len(output) <= max(256, int(max_exact_chars)):
        projected["output"] = output
        projected["observation"].update(
            {
                "adapter": "literal_output",
                "payload_kind": "literal_scalar_or_receipt",
                "fact_authority": "literal_output",
                "projection_complete": True,
            }
        )
        return projected
    digest = _sha256_text(output)
    exact_spans = [
        _literal_span(
            output,
            character_start=start,
            character_end=end,
            source_ref=f"action:{operation}:output",
            snapshot_sha256=digest,
            source_byte_start=0,
            base_line=1,
            selection_basis=basis,
        )
        for start, end, basis in _exact_windows(
            output,
            focus_text=focus_text,
            total_chars=max_exact_chars,
        )
        if end > start
    ]
    projected["exact_spans"] = exact_spans
    projected["observation"].update(
        {
            "adapter": "generic_exact_output",
            "payload_kind": "exact_utf8_spans",
            "fact_authority": "exact_spans_only",
            "projection_complete": False,
            "unprojected_content_exists": True,
        }
    )
    metadata = dict(projected.get("metadata") or {})
    metadata.update(
        {
            "complete": False,
            "projection_complete": False,
            "projection_truncated": True,
        }
    )
    projected["metadata"] = metadata
    return projected


def project_action_result(
    result: Mapping[str, Any],
    *,
    operation: str = "",
    arguments: Mapping[str, Any] | None = None,
    focus_text: str = "",
    max_exact_chars: int = 6000,
    structured_budget: int = 6000,
    evidence_source_limit: int = 2,
    evidence_span_chars: int = 1200,
    structured_field_budget: int = 1400,
) -> dict[str, Any]:
    """Return one bounded, typed projection with exact factual lineage."""

    selected_operation = str(
        operation or result.get("action_type") or ""
    ).strip()
    selected_arguments = dict(arguments or {})
    if selected_operation in EXTERNAL_EVIDENCE_OPERATIONS or isinstance(
        (result.get("metadata") or {}).get("external_evidence")
        if isinstance(result.get("metadata"), Mapping)
        else None,
        Mapping,
    ):
        return _project_external_evidence(
            result,
            selected_operation,
            arguments=selected_arguments,
            focus_text=focus_text,
            evidence_source_limit=evidence_source_limit,
            evidence_span_chars=evidence_span_chars,
            structured_field_budget=structured_field_budget,
        )
    if selected_operation in LOCAL_EXACT_TEXT_OPERATIONS:
        return _project_local_exact_text(
            result,
            selected_operation,
            focus_text=focus_text,
            max_exact_chars=max_exact_chars,
        )
    if selected_operation in STRUCTURED_PAGE_OPERATIONS:
        return _project_structured_page(
            result,
            selected_operation,
            arguments=selected_arguments,
            structured_budget=structured_budget,
        )
    if selected_operation in COMMAND_OPERATIONS:
        return _project_command(
            result,
            selected_operation,
            focus_text=focus_text,
            max_exact_chars=max_exact_chars,
        )
    return _project_generic(
        result,
        selected_operation,
        focus_text=focus_text,
        max_exact_chars=max_exact_chars,
    )


def _encoded_size(value: Any) -> int:
    return len(canonical_json(value).encode("utf-8"))


def _normalized_exact_span(
    value: Mapping[str, Any],
    *,
    fallback_source_ref: str,
    fallback_snapshot_sha256: str,
) -> dict[str, Any] | None:
    """Return one self-verifying exact span without retaining extra payload fields."""

    content = value.get("content")
    if not isinstance(content, str):
        return None
    content_bytes = content.encode("utf-8")
    content_sha256 = str(value.get("content_sha256") or "")
    try:
        start_byte = int(value.get("start_byte", 0))
        end_byte = int(value.get("end_byte", start_byte + len(content_bytes)))
    except (TypeError, ValueError):
        return None
    if (
        start_byte < 0
        or end_byte - start_byte != len(content_bytes)
        or content_sha256 != _sha256_bytes(content_bytes)
    ):
        return None
    source_ref = str(value.get("source_ref") or fallback_source_ref)
    snapshot_sha256 = str(
        value.get("snapshot_sha256") or fallback_snapshot_sha256
    )
    if not source_ref or re.fullmatch(r"[0-9a-f]{64}", snapshot_sha256) is None:
        return None
    start_line = int(value.get("start_line", value.get("line", 1)) or 1)
    end_line = int(
        value.get(
            "end_line",
            start_line + content.count("\n") - int(content.endswith("\n")),
        )
        or start_line
    )
    identity = {
        "source_ref": source_ref,
        "snapshot_sha256": snapshot_sha256,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "content_sha256": content_sha256,
    }
    return {
        "span_id": f"OBS-SPAN-{canonical_digest(identity)[:20]}",
        **identity,
        "start_line": start_line,
        "end_line": max(start_line, end_line),
        "content": content,
        "selection_basis": str(value.get("selection_basis") or "exact_source_span"),
        **(
            {"parent_chunk_id": str(value["parent_chunk_id"])}
            if value.get("parent_chunk_id")
            else {}
        ),
        **(
            {"parent_chunk_sha256": str(value["parent_chunk_sha256"])}
            if value.get("parent_chunk_sha256")
            else {}
        ),
    }


def _subspan_for_budget(
    span: Mapping[str, Any],
    *,
    focus_text: str,
    max_chars: int,
) -> dict[str, Any] | None:
    """Derive a smaller byte-identical span while updating every lineage field."""

    content = str(span.get("content") or "")
    if not content:
        return None
    width = max(32, min(len(content), int(max_chars)))
    folded = content.casefold()
    center = len(content) // 2
    basis = "budget_middle"
    for term in _focus_terms(focus_text):
        position = folded.find(term)
        if position >= 0:
            center = position
            basis = "budget_focus_exact_match"
            break
    character_start, character_end = _line_bounded_window(content, center, width)
    while (
        len(content[character_start:character_end].encode("utf-8")) > max_chars
        and character_end > character_start + 1
    ):
        character_end -= 1
    selected = content[character_start:character_end]
    if not selected:
        return None
    prefix = content[:character_start]
    selected_bytes = selected.encode("utf-8")
    start_byte = int(span["start_byte"]) + len(prefix.encode("utf-8"))
    start_line = int(span.get("start_line", 1) or 1) + prefix.count("\n")
    end_line = start_line + selected.count("\n") - int(selected.endswith("\n"))
    value = {
        **dict(span),
        "start_byte": start_byte,
        "end_byte": start_byte + len(selected_bytes),
        "start_line": start_line,
        "end_line": max(start_line, end_line),
        "content": selected,
        "content_sha256": _sha256_bytes(selected_bytes),
        "selection_basis": basis,
    }
    identity = {
        "source_ref": str(value["source_ref"]),
        "snapshot_sha256": str(value["snapshot_sha256"]),
        "start_byte": value["start_byte"],
        "end_byte": value["end_byte"],
        "content_sha256": value["content_sha256"],
    }
    value["span_id"] = f"OBS-SPAN-{canonical_digest(identity)[:20]}"
    return value


def compact_action_result_projection(
    projected: Mapping[str, Any],
    *,
    budget: int,
    focus_text: str = "",
) -> dict[str, Any]:
    """Fit a typed observation into a hard byte budget without slicing JSON.

    Low-entropy status and diagnostic fields are retained first. Factual text is
    carried only as complete, hash-verified UTF-8 spans. If a previously selected
    span is too large, a smaller exact subspan is derived and all byte offsets and
    hashes are recomputed. The durable full result remains the sole authority.
    """

    limit = int(budget)
    if limit < 512:
        raise ValueError("compact observation budget must be at least 512 bytes")
    observation = (
        dict(projected.get("observation") or {})
        if isinstance(projected.get("observation"), Mapping)
        else {}
    )
    compact: dict[str, Any] = {
        "projection_version": OBSERVATION_PROJECTION_VERSION,
        "success": bool(projected.get("success")),
        "outcome_type": str(projected.get("outcome_type") or "pending"),
        "action_type": str(projected.get("action_type") or ""),
        "raw_result_sha256": str(observation.get("raw_result_sha256") or ""),
        "full_projection_omitted_for_budget": True,
        "projection_complete": False,
        "fact_authority": "literal_fields_and_exact_spans_only",
    }
    if _encoded_size(compact) > limit:
        raise ValueError("compact observation identity exceeds its byte budget")

    def retain(key: str, value: Any) -> bool:
        candidate = {**compact, key: deepcopy(value)}
        if _encoded_size(candidate) > limit:
            return False
        compact.clear()
        compact.update(candidate)
        return True

    if projected.get("exit_code") is not None:
        retain("exit_code", int(projected["exit_code"]))
    if isinstance(projected.get("error"), Mapping):
        retain("error", projected["error"])

    raw_metadata = projected.get("metadata")
    metadata = dict(raw_metadata) if isinstance(raw_metadata, Mapping) else {}
    compact_metadata: dict[str, Any] = {}
    metadata_priority = (
        "valid_json",
        "parse_outcome_complete",
        "parse_error",
        "complete",
        "truncated",
        "eof",
        "representation",
        "next_start_byte",
        "next_cursor",
        "exit_code_matched",
        "expected_exit_code",
        "output_truncated",
        "match_count",
        "source_size_bytes",
        "canonical_size_bytes",
        "request_binding_valid",
        "snapshot_transition_verified",
    )
    for key in metadata_priority:
        if key not in metadata:
            continue
        candidate_metadata = {**compact_metadata, key: deepcopy(metadata[key])}
        candidate = {**compact, "metadata": candidate_metadata}
        if _encoded_size(candidate) <= limit:
            compact_metadata = candidate_metadata
    if compact_metadata:
        retain("metadata", compact_metadata)

    source_artifact = observation.get("source_artifact")
    if isinstance(source_artifact, Mapping):
        retain("source_artifact", source_artifact)
    source_chunk = observation.get("source_chunk")

    structured_output = projected.get("structured_output")
    if structured_output is not None:
        remaining = max(128, limit - _encoded_size(compact) - 80)
        structured = project_structured_value(
            structured_output,
            budget=remaining,
        )
        retain("structured_output", structured)

    fallback_source_ref = str(
        (source_artifact or {}).get("path")
        if isinstance(source_artifact, Mapping)
        else observation.get("operation")
        or projected.get("action_type")
        or "observation"
    )
    fallback_snapshot_sha256 = str(
        (source_artifact or {}).get("sha256")
        if isinstance(source_artifact, Mapping)
        else observation.get("raw_output_sha256")
        or ""
    )
    raw_spans: list[Mapping[str, Any]] = []

    def collect(value: Any) -> None:
        if isinstance(value, Mapping):
            if isinstance(value.get("content"), str) and value.get("content_sha256"):
                raw_spans.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
            for child in value:
                collect(child)

    collect(observation.get("exact_spans") or ())
    collect(projected.get("exact_spans") or ())
    collect(projected.get("command_streams") or ())
    if isinstance(metadata.get("parse_error"), Mapping):
        collect(metadata["parse_error"].get("source_span"))

    normalized_spans: list[dict[str, Any]] = []
    seen_spans: set[tuple[str, int, int, str]] = set()
    for raw_span in raw_spans:
        span = _normalized_exact_span(
            raw_span,
            fallback_source_ref=fallback_source_ref,
            fallback_snapshot_sha256=fallback_snapshot_sha256,
        )
        if span is None:
            continue
        identity = (
            str(span["source_ref"]),
            int(span["start_byte"]),
            int(span["end_byte"]),
            str(span["content_sha256"]),
        )
        if identity in seen_spans:
            continue
        seen_spans.add(identity)
        normalized_spans.append(span)
    terms = _focus_terms(focus_text)
    normalized_spans.sort(
        key=lambda span: (
            -_match_score(str(span["content"]), terms)[0],
            -_match_score(str(span["content"]), terms)[1],
            len(str(span["content"])),
            int(span["start_byte"]),
        )
    )
    retained_spans: list[dict[str, Any]] = []
    for span in normalized_spans:
        candidate_spans = [*retained_spans, span]
        if _encoded_size({**compact, "exact_spans": candidate_spans}) <= limit:
            retained_spans = candidate_spans
            continue
        for width in (800, 400, 200, 96):
            subspan = _subspan_for_budget(
                span,
                focus_text=focus_text,
                max_chars=width,
            )
            if subspan is None:
                continue
            candidate_spans = [*retained_spans, subspan]
            if _encoded_size({**compact, "exact_spans": candidate_spans}) <= limit:
                retained_spans = candidate_spans
                break
    if retained_spans:
        retain("exact_spans", retained_spans)
    if isinstance(source_chunk, Mapping):
        retain("source_chunk", source_chunk)
    if _encoded_size(compact) > limit:
        raise ValueError("compact observation exceeds its byte budget")
    return compact


__all__ = [
    "COMMAND_OPERATIONS",
    "EXTERNAL_EVIDENCE_OPERATIONS",
    "LOCAL_EXACT_TEXT_OPERATIONS",
    "MUTATION_OPERATIONS",
    "OBSERVATION_PACKET_SCHEMA_VERSION",
    "OBSERVATION_PROJECTION_VERSION",
    "ObservationProjectionError",
    "REGISTERED_OPERATIONS",
    "SCALAR_OPERATIONS",
    "STRUCTURED_PAGE_OPERATIONS",
    "bounded_model_value",
    "compact_action_result_projection",
    "project_action_result",
    "project_structured_value",
]
