"""Mechanical provenance checks for observation-conditioned Executor arguments.

The model may use a summary to navigate, but a summary cannot authorize an exact
path, cursor, read-modify-write base revision, or source literal.  This module
checks those fields against the exact Harness projections that were actually in
the Executor fact scope and returns a compact, content-addressed audit record.
"""

from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from typing import Any, Mapping, Sequence

from rwkv_lh.model_io import canonical_digest
from rwkv_lh.observation_funnel import OBSERVATION_PROJECTION_VERSION


EXECUTOR_ARGUMENT_PROVENANCE_VERSION = (
    "rwkv-lh.executor-argument-provenance.v2"
)
RMW_OPERATIONS = frozenset({"patch_json", "replace_text", "remove_line"})
READ_OPERATIONS = frozenset({"read_file", "read_json"})
PAGED_OPERATIONS = frozenset({"list_directory", "search_text"})
COMMAND_OPERATIONS = frozenset({"check_command", "run_command"})
_SHA256_RE = re.compile(r"[0-9a-f]{64}")


class ExecutorProvenanceError(ValueError):
    """An exact Executor argument has no matching authoritative observation."""


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and _SHA256_RE.fullmatch(value) is not None


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _fact_projection(fact: Mapping[str, Any]) -> Mapping[str, Any]:
    operation = str(fact.get("operation") or "")
    if not operation:
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} has no operation identity"
        )
    result = fact.get("result")
    if not isinstance(result, Mapping):
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} has no projected result"
        )
    observation = result.get("observation")
    if not isinstance(observation, Mapping):
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} has no typed observation"
        )
    if observation.get("projection_version") != OBSERVATION_PROJECTION_VERSION:
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} uses another projection version"
        )
    if observation.get("summary_fact_authority") is not False:
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} grants authority to a summary"
        )
    if (
        result.get("action_type") != operation
        or observation.get("operation") != operation
    ):
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} has conflicting operation identities"
        )
    if not _is_sha256(observation.get("raw_result_sha256")):
        raise ExecutorProvenanceError(
            f"bound fact {fact.get('action_id')!r} has no raw-result identity"
        )
    return result


def _validated_fragment(
    action_id: str,
    span: Mapping[str, Any],
    *,
    content_key: str = "content",
    digest_key: str = "content_sha256",
    span_id_key: str = "span_id",
) -> dict[str, Any] | None:
    content = span.get(content_key)
    if not isinstance(content, str) or not content:
        return None
    content_sha256 = str(span.get(digest_key) or "")
    if content_sha256 != _sha256_text(content):
        raise ExecutorProvenanceError(
            f"bound fact {action_id!r} contains a fragment with invalid content SHA-256"
        )
    source_ref = str(span.get("source_ref") or "")
    snapshot_sha256 = str(span.get("snapshot_sha256") or "")
    raw_start_byte = span.get("start_byte")
    raw_end_byte = span.get("end_byte")
    if (
        isinstance(raw_start_byte, bool)
        or not isinstance(raw_start_byte, int)
        or isinstance(raw_end_byte, bool)
        or not isinstance(raw_end_byte, int)
    ):
        raise ExecutorProvenanceError(
            f"bound fact {action_id!r} contains a fragment without an exact byte range"
        )
    start_byte = raw_start_byte
    end_byte = raw_end_byte
    if (
        not source_ref
        or not _is_sha256(snapshot_sha256)
        or start_byte < 0
        or end_byte < start_byte
        or end_byte - start_byte != len(content.encode("utf-8"))
    ):
        raise ExecutorProvenanceError(
            f"bound fact {action_id!r} contains an invalid exact fragment locator"
        )
    identity = {
        "source_ref": source_ref,
        "snapshot_sha256": snapshot_sha256,
        "start_byte": start_byte,
        "end_byte": end_byte,
        "content_sha256": content_sha256,
    }
    span_id = str(span.get(span_id_key) or "")
    expected_span_id = f"OBS-SPAN-{canonical_digest(identity)[:20]}"
    if span_id != expected_span_id:
        raise ExecutorProvenanceError(
            f"bound fact {action_id!r} contains a fragment with an invalid span ID"
        )
    return {
        "action_id": action_id,
        "span_id": span_id,
        **identity,
        "content": content,
    }


def _fragments(fact: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    action_id = str(fact.get("action_id") or "")
    result = _fact_projection(fact)
    observation = result["observation"]
    selected: list[dict[str, Any]] = []
    for span in observation.get("exact_spans") or ():
        if isinstance(span, Mapping):
            fragment = _validated_fragment(action_id, span)
            if fragment is not None:
                selected.append(fragment)
    for span in result.get("exact_spans") or ():
        if isinstance(span, Mapping):
            fragment = _validated_fragment(action_id, span)
            if fragment is not None:
                selected.append(fragment)
    structured = result.get("structured_output")
    if (
        str(fact.get("operation") or "") == "search_text"
        and isinstance(structured, Mapping)
    ):
        source_snapshots = structured.get("source_snapshots")
        if not isinstance(source_snapshots, Mapping):
            raise ExecutorProvenanceError(
                f"bound fact {action_id!r} search result has no source snapshots"
            )
        for match in structured.get("matches") or ():
            if not isinstance(match, Mapping):
                continue
            path = str(match.get("path") or "")
            line_text = match.get("line_text")
            line_sha256 = str(match.get("line_text_sha256") or "")
            snapshot_sha256 = str(match.get("source_snapshot_sha256") or "")
            span_id = str(match.get("source_span_id") or "")
            try:
                start_byte = int(match["line_text_start_byte"])
                end_byte = int(match["line_text_end_byte"])
            except (KeyError, TypeError, ValueError) as exc:
                raise ExecutorProvenanceError(
                    f"bound fact {action_id!r} search match lacks an exact byte range"
                ) from exc
            identity = {
                "source_ref": path,
                "snapshot_sha256": snapshot_sha256,
                "start_byte": start_byte,
                "end_byte": end_byte,
                "content_sha256": line_sha256,
            }
            if (
                not path
                or not isinstance(line_text, str)
                or not line_text
                or line_sha256 != _sha256_text(line_text)
                or not _is_sha256(snapshot_sha256)
                or source_snapshots.get(path) != snapshot_sha256
                or start_byte < 0
                or end_byte - start_byte != len(line_text.encode("utf-8"))
                or span_id != f"OBS-SPAN-{canonical_digest(identity)[:20]}"
            ):
                raise ExecutorProvenanceError(
                    f"bound fact {action_id!r} search match failed exact lineage validation"
                )
            selected.append(
                {
                    "action_id": action_id,
                    "span_id": span_id,
                    **identity,
                    "content": line_text,
                }
            )
    for stream in result.get("command_streams") or ():
        if not isinstance(stream, Mapping):
            continue
        stream_name = str(stream.get("stream") or "")
        stream_sha256 = str(stream.get("stream_sha256") or "")
        for span in stream.get("exact_spans") or ():
            if not isinstance(span, Mapping):
                continue
            fragment = _validated_fragment(action_id, span)
            if fragment is None:
                continue
            if (
                fragment["source_ref"]
                != f"command:{fact.get('operation')}:{stream_name}"
                or fragment["snapshot_sha256"] != stream_sha256
            ):
                raise ExecutorProvenanceError(
                    f"bound fact {action_id!r} command fragment has conflicting stream identity"
                )
            fragment["stream"] = stream_name
            selected.append(fragment)
    return tuple(selected)


def _narrow_fragment(
    fragment: Mapping[str, Any],
    literal: str,
    *,
    line_exact: bool = False,
) -> dict[str, Any] | None:
    if not literal:
        return None
    content = str(fragment["content"])
    character_start = -1
    if line_exact:
        cursor = 0
        for physical_line in content.splitlines(keepends=True):
            line = physical_line.rstrip("\r\n")
            if line == literal:
                character_start = cursor
                break
            cursor += len(physical_line)
        if character_start < 0 and content and not content.endswith(("\n", "\r")):
            tail_start = content.rfind("\n") + 1
            if content[tail_start:] == literal:
                character_start = tail_start
    else:
        character_start = content.find(literal)
    if character_start < 0:
        return None
    character_end = character_start + len(literal)
    match_start = int(fragment["start_byte"]) + len(
        content[:character_start].encode("utf-8")
    )
    match_end = int(fragment["start_byte"]) + len(
        content[:character_end].encode("utf-8")
    )
    return {
        "action_id": str(fragment["action_id"]),
        "parent_span_id": str(fragment["span_id"]),
        "source_ref": str(fragment["source_ref"]),
        "snapshot_sha256": str(fragment["snapshot_sha256"]),
        "start_byte": match_start,
        "end_byte": match_end,
        "content_sha256": _sha256_text(literal),
        "match_mode": "complete_line" if line_exact else "exact_substring",
    }


def _find_literal(
    facts: Sequence[Mapping[str, Any]],
    literal: str,
    *,
    action_id: str = "",
    line_exact: bool = False,
    source_ref: str = "",
    snapshot_sha256: str = "",
) -> dict[str, Any] | None:
    for fact in reversed(facts):
        if action_id and str(fact.get("action_id") or "") != action_id:
            continue
        for fragment in _fragments(fact):
            if source_ref and fragment["source_ref"] != source_ref:
                continue
            if (
                snapshot_sha256
                and fragment["snapshot_sha256"] != snapshot_sha256
            ):
                continue
            locator = _narrow_fragment(fragment, literal, line_exact=line_exact)
            if locator is not None:
                return locator
    return None


def _artifact_identity(
    fact: Mapping[str, Any],
    path: str,
    base_sha256: str,
) -> dict[str, Any] | None:
    result = _fact_projection(fact)
    if result.get("success") is not True:
        return None
    observation = result["observation"]
    artifact = observation.get("source_artifact")
    if isinstance(artifact, Mapping):
        if artifact.get("path") != path or artifact.get("sha256") != base_sha256:
            return None
        size_bytes = artifact.get("size_bytes")
        if (
            not _is_sha256(base_sha256)
            or isinstance(size_bytes, bool)
            or not isinstance(size_bytes, int)
            or size_bytes < 0
        ):
            raise ExecutorProvenanceError(
                f"bound fact {fact.get('action_id')!r} has an invalid source artifact identity"
            )
        return {
            "action_id": str(fact.get("action_id") or ""),
            "source_ref": path,
            "snapshot_sha256": base_sha256,
            "size_bytes": size_bytes,
            "authority": "harness_file_artifact_identity",
        }

    if str(fact.get("operation") or "") != "search_text":
        return None
    structured = result.get("structured_output")
    if not isinstance(structured, Mapping):
        return None
    snapshots = structured.get("source_snapshots")
    if not isinstance(snapshots, Mapping) or snapshots.get(path) != base_sha256:
        return None
    matching_fragments = [
        fragment
        for fragment in _fragments(fact)
        if fragment["source_ref"] == path
        and fragment["snapshot_sha256"] == base_sha256
    ]
    if not matching_fragments or not _is_sha256(base_sha256):
        return None
    return {
        "action_id": str(fact.get("action_id") or ""),
        "source_ref": path,
        "snapshot_sha256": base_sha256,
        "observed_span_ids": [item["span_id"] for item in matching_fragments],
        "authority": "harness_search_source_snapshot_identity",
    }


def _binding(
    pointer: str,
    value: Any,
    authority: str,
    locator: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "argument_pointer": pointer,
        "argument_value_sha256": canonical_digest(value),
        "authority": authority,
        "locator": deepcopy(dict(locator)),
    }


def _require_literal(
    facts: Sequence[Mapping[str, Any]],
    literal: str,
    *,
    pointer: str,
    action_id: str = "",
    line_exact: bool = False,
    source_ref: str = "",
    snapshot_sha256: str = "",
) -> dict[str, Any]:
    locator = _find_literal(
        facts,
        literal,
        action_id=action_id,
        line_exact=line_exact,
        source_ref=source_ref,
        snapshot_sha256=snapshot_sha256,
    )
    if locator is None:
        raise ExecutorProvenanceError(
            f"{pointer} is not present in an exact fragment from the bound fact scope"
        )
    return _binding(pointer, literal, "exact_utf8_fragment", locator)


def _literal_requirement_binding(
    pointer: str,
    value: str,
    requirement: str,
) -> dict[str, Any] | None:
    if not _requirement_contains(requirement, value):
        return None
    return _binding(
        pointer,
        value,
        "literal_current_requirement",
        {
            "requirement_sha256": _sha256_text(requirement),
            "literal_sha256": _sha256_text(value),
        },
    )


def _top_level_json_key_locator(
    fact: Mapping[str, Any],
    path: str,
    key: str,
) -> dict[str, Any] | None:
    """Locate one key only after the complete canonical top-level object is seen."""

    result = _fact_projection(fact)
    observation = result["observation"]
    if str(fact.get("operation") or "") != "read_json":
        return None
    if observation.get("projection_complete") is not True:
        return None
    metadata = result.get("metadata")
    if not isinstance(metadata, Mapping):
        return None
    canonical_size = metadata.get("canonical_size_bytes")
    if (
        isinstance(canonical_size, bool)
        or not isinstance(canonical_size, int)
        or canonical_size < 2
    ):
        return None
    expected_source_ref = f"{path}#canonical-json"
    for fragment in _fragments(fact):
        content = str(fragment["content"])
        if (
            fragment["source_ref"] != expected_source_ref
            or fragment["start_byte"] != 0
            or fragment["end_byte"] != canonical_size
            or fragment["snapshot_sha256"] != _sha256_text(content)
        ):
            continue
        try:
            value = json.loads(content)
        except json.JSONDecodeError:
            continue
        if not isinstance(value, dict) or key not in value:
            continue
        decoder = json.JSONDecoder()
        depth = 0
        index = 0
        while index < len(content):
            character = content[index]
            if character == '"':
                try:
                    decoded, end = decoder.raw_decode(content, idx=index)
                except json.JSONDecodeError:
                    break
                after = end
                while after < len(content) and content[after].isspace():
                    after += 1
                if (
                    depth == 1
                    and decoded == key
                    and after < len(content)
                    and content[after] == ":"
                ):
                    marker_end = after + 1
                    start_byte = len(content[:index].encode("utf-8"))
                    end_byte = len(content[:marker_end].encode("utf-8"))
                    return {
                        "action_id": str(fact.get("action_id") or ""),
                        "parent_span_id": str(fragment["span_id"]),
                        "source_ref": expected_source_ref,
                        "snapshot_sha256": str(fragment["snapshot_sha256"]),
                        "start_byte": start_byte,
                        "end_byte": end_byte,
                        "content_sha256": _sha256_text(content[index:marker_end]),
                        "match_mode": "complete_canonical_top_level_json_key",
                    }
                index = end
                continue
            if character in "{[":
                depth += 1
            elif character in "}]":
                depth -= 1
                if depth < 0:
                    break
            index += 1
    return None


def _rmw_bindings(
    operation: str,
    arguments: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
    requirement: str,
) -> list[dict[str, Any]]:
    path = arguments.get("path")
    base_sha256 = arguments.get("base_sha256")
    if not isinstance(path, str) or not path or not _is_sha256(base_sha256):
        raise ExecutorProvenanceError(
            f"{operation} requires a path and lowercase base_sha256"
        )
    selected_fact: Mapping[str, Any] | None = None
    artifact: dict[str, Any] | None = None
    required_read_operations = (
        ("read_json",)
        if operation == "patch_json"
        else ("read_file", "search_text")
    )
    for fact in reversed(facts):
        if str(fact.get("operation") or "") not in required_read_operations:
            continue
        artifact = _artifact_identity(fact, path, str(base_sha256))
        if artifact is not None:
            selected_fact = fact
            break
    if selected_fact is None or artifact is None:
        raise ExecutorProvenanceError(
            f"{operation} base_sha256 is not the observed artifact identity for {path!r}"
        )
    action_id = str(selected_fact.get("action_id") or "")
    bindings = [
        _binding("/path", path, str(artifact["authority"]), artifact),
        _binding(
            "/base_sha256",
            base_sha256,
            str(artifact["authority"]),
            artifact,
        ),
    ]
    if operation == "replace_text":
        old = arguments.get("old")
        if not isinstance(old, str) or not old:
            raise ExecutorProvenanceError("replace_text /old must be non-empty")
        bindings.append(
            _require_literal(
                facts,
                old,
                pointer="/old",
                action_id=action_id,
                source_ref=path,
                snapshot_sha256=str(base_sha256),
            )
        )
        if "size_bytes" in artifact and int(
            bindings[-1]["locator"]["end_byte"]
        ) > int(artifact["size_bytes"]):
            raise ExecutorProvenanceError(
                "replace_text /old lies outside the bound source artifact"
            )
        new = arguments.get("new")
        if not isinstance(new, str):
            raise ExecutorProvenanceError("replace_text /new must be a string")
        requirement_binding = _literal_requirement_binding(
            "/new", new, requirement
        )
        if requirement_binding is not None:
            bindings.append(requirement_binding)
    elif operation == "remove_line":
        text = arguments.get("text")
        if not isinstance(text, str):
            raise ExecutorProvenanceError("remove_line /text must be a string")
        bindings.append(
            _require_literal(
                facts,
                text,
                pointer="/text",
                action_id=action_id,
                line_exact=True,
                source_ref=path,
                snapshot_sha256=str(base_sha256),
            )
        )
        if "size_bytes" in artifact and int(
            bindings[-1]["locator"]["end_byte"]
        ) > int(artifact["size_bytes"]):
            raise ExecutorProvenanceError(
                "remove_line /text lies outside the bound source artifact"
            )
    else:
        updates = arguments.get("updates")
        if not isinstance(updates, Mapping) or not updates:
            raise ExecutorProvenanceError("patch_json /updates must be a non-empty object")
        for key in updates:
            if not isinstance(key, str):
                raise ExecutorProvenanceError("patch_json update keys must be strings")
            locator = _top_level_json_key_locator(selected_fact, path, key)
            if locator is None:
                raise ExecutorProvenanceError(
                    f"/updates/{_pointer_token(key)} key is not a structurally verified "
                    "top-level key in the complete canonical JSON fragment"
                )
            bindings.append(
                _binding(
                    f"/updates/{_pointer_token(key)}#key",
                    key,
                    "exact_canonical_json_key",
                    locator,
                )
            )
    return bindings


def _continuation_binding(
    operation: str,
    arguments: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    pointer: str
    field: str
    selected_value: Any
    if operation in READ_OPERATIONS:
        selected_value = arguments.get("start_byte", 0)
        if isinstance(selected_value, bool) or not isinstance(selected_value, int):
            raise ExecutorProvenanceError(f"{operation} /start_byte must be an integer")
        if selected_value == 0:
            return []
        pointer, field = "/start_byte", "next_start_byte"
    else:
        selected_value = arguments.get("start_after", "")
        if not isinstance(selected_value, str):
            raise ExecutorProvenanceError(f"{operation} /start_after must be a string")
        if not selected_value:
            return []
        pointer, field = "/start_after", "next_cursor"
    path = str(arguments.get("path") or ".")
    for fact in reversed(facts):
        if str(fact.get("operation") or "") != operation:
            continue
        prior_arguments = fact.get("arguments")
        if not isinstance(prior_arguments, Mapping):
            continue
        if str(prior_arguments.get("path") or ".") != path:
            continue
        result = _fact_projection(fact)
        metadata = result.get("metadata")
        if not isinstance(metadata, Mapping) or metadata.get(field) != selected_value:
            continue
        locator = {
            "action_id": str(fact.get("action_id") or ""),
            "result_pointer": f"/metadata/{field}",
            "raw_result_sha256": str(result["observation"].get("raw_result_sha256") or ""),
            "source_operation": operation,
            "source_path": path,
        }
        return [_binding(pointer, selected_value, "harness_continuation", locator)]
    raise ExecutorProvenanceError(
        f"{operation} {pointer} does not equal the bound same-source {field}"
    )


def _requirement_contains(requirement: str, literal: str) -> bool:
    if not literal or literal not in requirement:
        return False
    token_character = r"A-Za-z0-9_.\-/"
    return (
        re.search(
            rf"(?<![{token_character}]){re.escape(literal)}(?![{token_character}])",
            requirement,
        )
        is not None
    )


def _structured_path_locator(
    facts: Sequence[Mapping[str, Any]], path: str
) -> dict[str, Any] | None:
    for fact in reversed(facts):
        result = _fact_projection(fact)
        structured = result.get("structured_output")
        if not isinstance(structured, Mapping):
            continue
        operation = str(fact.get("operation") or "")
        item_key = "matches" if operation == "search_text" else "entries"
        for index, item in enumerate(structured.get(item_key) or ()):
            if not isinstance(item, Mapping) or item.get("path") != path:
                continue
            locator: dict[str, Any] = {
                "action_id": str(fact.get("action_id") or ""),
                "result_pointer": f"/structured_output/{item_key}/{index}/path",
                "raw_result_sha256": str(result["observation"].get("raw_result_sha256") or ""),
                "source_operation": operation,
            }
            if operation == "search_text":
                line_text = item.get("line_text")
                line_sha = str(item.get("line_text_sha256") or "")
                snapshot_sha = str(item.get("source_snapshot_sha256") or "")
                span_id = str(item.get("source_span_id") or "")
                try:
                    start_byte = int(item["line_text_start_byte"])
                    end_byte = int(item["line_text_end_byte"])
                except (KeyError, TypeError, ValueError) as exc:
                    raise ExecutorProvenanceError(
                        "search_text path item lacks an exact source-line locator"
                    ) from exc
                identity = {
                    "source_ref": path,
                    "snapshot_sha256": snapshot_sha,
                    "start_byte": start_byte,
                    "end_byte": end_byte,
                    "content_sha256": line_sha,
                }
                if (
                    not isinstance(line_text, str)
                    or line_sha != _sha256_text(line_text)
                    or not _is_sha256(snapshot_sha)
                    or end_byte - start_byte != len(line_text.encode("utf-8"))
                    or span_id != f"OBS-SPAN-{canonical_digest(identity)[:20]}"
                ):
                    raise ExecutorProvenanceError(
                        "search_text path item failed its exact source-line identity"
                    )
                locator.update(
                    {
                        "source_span_id": span_id,
                        "source_ref": path,
                        "snapshot_sha256": snapshot_sha,
                        "start_byte": start_byte,
                        "end_byte": end_byte,
                        "content_sha256": line_sha,
                    }
                )
            return locator
    return None


def _path_discovery_binding(
    operation: str,
    arguments: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
    requirement: str,
    execution_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    if operation not in {"read_file", "read_json", "file_digest"}:
        return []
    path = arguments.get("path")
    if not isinstance(path, str) or not path:
        return []
    target_contract = execution_state.get("target_contract")
    if isinstance(target_contract, Mapping) and target_contract.get(
        "schema_version"
    ) == "rwkv-lh.goal-step-target-contract.v1":
        compatible = target_contract.get("compatible_targets_by_operation")
        operation_paths = (
            compatible.get(operation)
            if isinstance(compatible, Mapping)
            else None
        )
        if (
            isinstance(operation_paths, list)
            and path in operation_paths
            and all(isinstance(item, str) for item in operation_paths)
        ):
            descriptors = target_contract.get("target_descriptors")
            descriptor = next(
                (
                    dict(item)
                    for item in descriptors or ()
                    if isinstance(item, Mapping) and item.get("path") == path
                ),
                None,
            )
            if descriptor is None:
                raise ExecutorProvenanceError(
                    "Controller target contract names a path without its Harness descriptor"
                )
            return [
                _binding(
                    "/path",
                    path,
                    "controller_harness_target_contract",
                    {
                        "target_contract_sha256": canonical_digest(target_contract),
                        "phase": str(target_contract.get("phase") or ""),
                        "descriptor": descriptor,
                    },
                )
            ]
    discovery_facts = [
        fact
        for fact in facts
        if str(fact.get("operation") or "") in {"search_text", "list_directory"}
    ]
    if not discovery_facts:
        return []
    locator = _structured_path_locator(discovery_facts, path)
    if locator is not None:
        return [_binding("/path", path, "literal_structured_path", locator)]
    literal_locator = _find_literal(facts, path)
    if literal_locator is not None:
        return [_binding("/path", path, "exact_utf8_fragment", literal_locator)]
    if _requirement_contains(requirement, path):
        return [
            _binding(
                "/path",
                path,
                "literal_current_requirement",
                {
                    "requirement_sha256": _sha256_text(requirement),
                    "literal_sha256": _sha256_text(path),
                },
            )
        ]
    raise ExecutorProvenanceError(
        f"/path {path!r} is not an exact item in the bound discovery observation"
    )


def _same_command_family(previous: Sequence[str], current: Sequence[str]) -> bool:
    if not previous or not current or previous[0] != current[0]:
        return False
    if len(previous) >= 2 and len(current) >= 2:
        return previous[1] == current[1]
    return True


def _command_repair_bindings(
    operation: str,
    arguments: Mapping[str, Any],
    facts: Sequence[Mapping[str, Any]],
    requirement: str,
    execution_state: Mapping[str, Any],
) -> list[dict[str, Any]]:
    del execution_state
    if operation not in COMMAND_OPERATIONS:
        return []
    argv = arguments.get("argv")
    if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
        return []
    prior_fact: Mapping[str, Any] | None = None
    prior_argv: list[str] = []
    for fact in reversed(facts):
        if str(fact.get("operation") or "") not in COMMAND_OPERATIONS:
            continue
        result = _fact_projection(fact)
        prior_arguments = fact.get("arguments")
        candidate = (
            list(prior_arguments.get("argv") or ())
            if isinstance(prior_arguments, Mapping)
            else []
        )
        if (
            result.get("success") is False
            and all(isinstance(item, str) for item in candidate)
            and _same_command_family(candidate, argv)
        ):
            prior_fact, prior_argv = fact, candidate
            break
    if prior_fact is None:
        return []
    bindings: list[dict[str, Any]] = []
    for index, item in enumerate(argv):
        if index < len(prior_argv) and item == prior_argv[index]:
            continue
        pointer = f"/argv/{index}"
        locator = _find_literal((prior_fact,), item)
        if locator is not None:
            bindings.append(_binding(pointer, item, "exact_command_stream", locator))
            continue
        if _requirement_contains(requirement, item):
            bindings.append(
                _binding(
                    pointer,
                    item,
                    "literal_current_requirement",
                    {
                        "requirement_sha256": _sha256_text(requirement),
                        "literal_sha256": _sha256_text(item),
                    },
                )
            )
            continue
        raise ExecutorProvenanceError(
            f"{pointer} changed during command repair but is absent from exact stderr/stdout"
        )
    return bindings


def validate_executor_argument_provenance(
    operation: str,
    arguments: Mapping[str, Any],
    *,
    current_requirement: str,
    fact_records: Sequence[Mapping[str, Any]],
    execution_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Validate source-derived fields and return their exact evidence locators."""

    selected_operation = str(operation or "").strip()
    selected_arguments = dict(arguments)
    selected_requirement = str(current_requirement or "").strip()
    selected_execution_state = dict(execution_state or {})
    facts = tuple(dict(item) for item in fact_records)
    action_ids = tuple(str(item.get("action_id") or "") for item in facts)
    if any(not item for item in action_ids) or len(set(action_ids)) != len(action_ids):
        raise ExecutorProvenanceError(
            "Executor fact scope requires unique non-empty action IDs"
        )
    for fact in facts:
        _fact_projection(fact)

    bindings: list[dict[str, Any]] = []
    if selected_operation in RMW_OPERATIONS:
        bindings.extend(
            _rmw_bindings(
                selected_operation,
                selected_arguments,
                facts,
                selected_requirement,
            )
        )
    if selected_operation in READ_OPERATIONS | PAGED_OPERATIONS:
        bindings.extend(
            _continuation_binding(selected_operation, selected_arguments, facts)
        )
    bindings.extend(
        _path_discovery_binding(
            selected_operation,
            selected_arguments,
            facts,
            selected_requirement,
            selected_execution_state,
        )
    )
    bindings.extend(
        _command_repair_bindings(
            selected_operation,
            selected_arguments,
            facts,
            selected_requirement,
            selected_execution_state,
        )
    )
    return {
        "schema_version": EXECUTOR_ARGUMENT_PROVENANCE_VERSION,
        "operation": selected_operation,
        "fact_action_ids": list(action_ids),
        "fact_projection_sha256": canonical_digest(facts),
        "execution_state_sha256": canonical_digest(selected_execution_state),
        "checked_argument_count": len(bindings),
        "bindings": bindings,
        "summary_fact_authority": False,
        "passed": True,
    }


__all__ = [
    "EXECUTOR_ARGUMENT_PROVENANCE_VERSION",
    "ExecutorProvenanceError",
    "validate_executor_argument_provenance",
]
