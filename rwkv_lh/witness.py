"""Transparent witness catalogs for RWKV-owned criterion evidence choices."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from rwkv_lh.proof import CriterionProofEngine, ProofEvaluationError, value_sha256
from rwkv_lh.schema import Attempt, RunState, TaskNode, WitnessIntentState


WITNESS_CATALOG_SCHEMA = "long-horizon.witness-catalog.v1"
ACTUAL_WITNESS_SOURCE_KINDS = frozenset(
    {
        "action_output",
        "action_result",
        "workspace",
        "dependency_artifact",
        "dependency_memory",
    }
)
EXPECTED_WITNESS_SOURCE_KINDS = frozenset(
    {"goal_literal", "dependency_artifact", "dependency_memory"}
)


class WitnessCatalogError(ValueError):
    """The deterministic catalog is incomplete or a selected handle is invalid."""


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _pointer_token(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _json_pointers(value: Any, *, max_nodes: int) -> list[str]:
    pointers: list[str] = []

    def visit(current: Any, pointer: str) -> None:
        if len(pointers) >= max_nodes:
            raise WitnessCatalogError("JSON value exceeds witness pointer bound")
        pointers.append(pointer)
        if isinstance(current, Mapping):
            for key in sorted(current, key=str):
                visit(current[key], f"{pointer}/{_pointer_token(str(key))}")
        elif isinstance(current, list):
            for index, item in enumerate(current):
                visit(item, f"{pointer}/{index}")

    visit(value, "")
    return pointers


def _read_pointer(value: Any, pointer: str) -> Any:
    current = value
    if pointer == "":
        return current
    for raw in pointer[1:].split("/"):
        token = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            current = current[int(token)]
        else:
            current = current[token]
    return current


def _transform_variants(value: Any, *, max_group_pairs: int) -> list[list[dict[str, Any]]]:
    variants: list[list[dict[str, Any]]] = [[]]
    if isinstance(value, (str, list, dict)):
        variants.append([{"transform_op": "count"}])
    if isinstance(value, list):
        variants.extend(
            [
                [{"transform_op": "object_set"}],
                [{"transform_op": "sort"}],
            ]
        )
        if all(type(item) in {int, float} for item in value):
            variants.append([{"transform_op": "sum"}])
        if value and all(isinstance(item, Mapping) for item in value):
            pointer_sets = [
                set(_json_pointers(item, max_nodes=256)) - {""}
                for item in value
            ]
            common = sorted(set.intersection(*pointer_sets)) if pointer_sets else []
            group_pointers = [
                pointer
                for pointer in common
                if all(isinstance(_read_pointer(item, pointer), str) for item in value)
            ]
            value_pointers = [
                pointer
                for pointer in common
                if all(
                    type(_read_pointer(item, pointer)) in {int, float}
                    for item in value
                )
            ]
            pairs = [
                (group_pointer, value_pointer)
                for group_pointer in group_pointers
                for value_pointer in value_pointers
            ]
            if len(pairs) > max_group_pairs:
                raise WitnessCatalogError("group_sum transform catalog exceeds bound")
            variants.extend(
                [
                    {
                        "transform_op": "group_sum",
                        "group_pointer": group_pointer,
                        "value_pointer": value_pointer,
                    }
                ]
                for group_pointer, value_pointer in pairs
            )
    variants.append([{"transform_op": "sha256"}])
    return variants


def _preview(value: Any, *, limit: int) -> tuple[Any, bool]:
    encoded = _canonical(value).decode("utf-8")
    if len(encoded) <= limit:
        return value, False
    return encoded[:limit] + "…", True


def _source_descriptor(
    source_kind: str,
    owner_task_id: str,
    operator_value: Mapping[str, Any],
    intent_id: str,
) -> dict[str, Any]:
    arguments = operator_value.get("arguments") or {}
    locator: dict[str, Any]
    if source_kind == "workspace":
        locator = {"path": arguments.get("path")}
    elif source_kind in {"action_output", "action_result"}:
        locator = {"attempt_channel": source_kind}
    elif source_kind == "dependency_artifact":
        locator = {
            "task_id": arguments.get("task_id"),
            "artifact_id": arguments.get("artifact_id"),
        }
    elif source_kind == "dependency_memory":
        locator = {
            "task_id": arguments.get("task_id"),
            "memory_id": arguments.get("memory_id"),
        }
    else:
        locator = {"intent_id": intent_id}
    return {
        "source_kind": source_kind,
        "owner_task_id": owner_task_id,
        "intent_id": intent_id,
        "locator": locator,
    }


class WitnessCatalogBuilder:
    """Enumerate all structurally valid scoped reads without criterion semantics."""

    def __init__(
        self,
        proof_engine: CriterionProofEngine,
        *,
        max_json_nodes: int = 2048,
        max_handles: int = 4096,
        max_group_pairs: int = 64,
        preview_chars: int = 320,
    ):
        self.proof_engine = proof_engine
        self.max_json_nodes = max(1, int(max_json_nodes))
        self.max_handles = max(1, int(max_handles))
        self.max_group_pairs = max(1, int(max_group_pairs))
        self.preview_chars = max(32, int(preview_chars))

    def build(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        intents: Sequence[WitnessIntentState],
    ) -> dict[str, Any]:
        snapshot = self.proof_engine.harness.workspace_observation_snapshot(
            state.goal
        )
        if not snapshot.get("cacheable"):
            raise WitnessCatalogError(
                "workspace witness snapshot is incomplete: "
                f"{snapshot.get('reason') or 'unknown'}"
            )
        candidates: list[dict[str, Any]] = []

        def add_base(
            source_kind: str,
            owner_task_id: str,
            operator_value: Mapping[str, Any],
            eligible_sides: Sequence[str],
            *,
            intent_id: str = "",
        ) -> Any | None:
            side = "expected" if tuple(eligible_sides) == ("expected",) else "actual"
            try:
                base_value, _, _, _ = self.proof_engine.resolve_operator_value(
                    state,
                    task,
                    attempt,
                    operator_value,
                    side=side,
                    claim_id="CATALOG",
                )
                variants = _transform_variants(
                    base_value,
                    max_group_pairs=self.max_group_pairs,
                )
            except WitnessCatalogError:
                raise
            except (ProofEvaluationError, OSError, ValueError, TypeError):
                return None
            for transforms in variants:
                derived = {
                    "read_op": str(operator_value["read_op"]),
                    "arguments": dict(operator_value.get("arguments") or {}),
                    "transforms": transforms,
                }
                try:
                    resolved, refs, _, trace = self.proof_engine.resolve_operator_value(
                        state,
                        task,
                        attempt,
                        derived,
                        side=side,
                        claim_id="CATALOG",
                    )
                except (ProofEvaluationError, OSError, ValueError, TypeError):
                    continue
                reference_records = [
                    {
                        "source_type": ref.source_type,
                        "source_id": ref.source_id,
                        "path": ref.path,
                        "selector": ref.selector,
                        "source_sha256": ref.source_sha256,
                        "value_sha256": ref.value_sha256,
                    }
                    for ref in refs
                ]
                visible, truncated = _preview(resolved, limit=self.preview_chars)
                candidates.append(
                    {
                        "eligible_sides": sorted(set(eligible_sides)),
                        "source_kind": source_kind,
                        "owner_task_id": owner_task_id,
                        "intent_id": intent_id,
                        "source_descriptor": _source_descriptor(
                            source_kind,
                            owner_task_id,
                            derived,
                            intent_id,
                        ),
                        "operator_value": derived,
                        "value_type": type(resolved).__name__,
                        "value_preview": visible,
                        "value_preview_truncated": truncated,
                        "value_sha256": value_sha256(resolved),
                        "source_refs": reference_records,
                        "normalization_trace": trace,
                    }
                )
                if len(candidates) > self.max_handles:
                    raise WitnessCatalogError("witness handle catalog exceeds bound")
            return base_value

        action_output = {
            "read_op": "action_output_text",
            "arguments": {},
            "transforms": [],
        }
        add_base("action_output", task.task_id, action_output, ("actual",))
        action_json = {
            "read_op": "action_output_json",
            "arguments": {},
            "transforms": [],
        }
        add_base("action_output", task.task_id, action_json, ("actual",))
        action_result = attempt.tool_result or {}
        for pointer in _json_pointers(action_result, max_nodes=self.max_json_nodes):
            add_base(
                "action_result",
                task.task_id,
                {
                    "read_op": "action_result_json_pointer",
                    "arguments": {"pointer": pointer},
                    "transforms": [],
                },
                ("actual",),
            )

        directory_paths = {"."}
        file_paths: list[str] = []
        for entry in snapshot.get("entries") or []:
            if not isinstance(entry, Mapping):
                continue
            path = str(entry.get("path") or "")
            if entry.get("type") == "directory":
                directory_paths.add(path)
            elif entry.get("type") == "file":
                file_paths.append(path)
        for path in sorted(directory_paths):
            for recursive in (False, True):
                add_base(
                    "workspace",
                    task.task_id,
                    {
                        "read_op": "workspace_directory_file_set",
                        "arguments": {"path": path, "recursive": recursive},
                        "transforms": [],
                    },
                    ("actual",),
                )
            add_base(
                "workspace",
                task.task_id,
                {
                    "read_op": "workspace_path_exists",
                    "arguments": {"path": path, "path_type": "directory"},
                    "transforms": [],
                },
                ("actual",),
            )
        for path in sorted(file_paths):
            for read_op, arguments in (
                ("workspace_text", {"path": path}),
                ("workspace_sha256", {"path": path}),
                (
                    "workspace_path_exists",
                    {"path": path, "path_type": "file"},
                ),
            ):
                add_base(
                    "workspace",
                    task.task_id,
                    {"read_op": read_op, "arguments": arguments, "transforms": []},
                    ("actual",),
                )
            parsed = add_base(
                "workspace",
                task.task_id,
                {
                    "read_op": "workspace_json",
                    "arguments": {"path": path},
                    "transforms": [],
                },
                ("actual",),
            )
            if parsed is not None:
                for pointer in _json_pointers(parsed, max_nodes=self.max_json_nodes):
                    add_base(
                        "workspace",
                        task.task_id,
                        {
                            "read_op": "workspace_json_pointer",
                            "arguments": {"path": path, "pointer": pointer},
                            "transforms": [],
                        },
                        ("actual",),
                    )

        for artifact in sorted(
            (
                item
                for item in state.artifacts.values()
                if item.task_id in task.dependencies
            ),
            key=lambda item: (item.task_id, item.artifact_id),
        ):
            common = {"task_id": artifact.task_id, "artifact_id": artifact.artifact_id}
            for suffix in ("text", "sha256"):
                add_base(
                    "dependency_artifact",
                    artifact.task_id,
                    {
                        "read_op": f"dependency_artifact_{suffix}",
                        "arguments": dict(common),
                        "transforms": [],
                    },
                    ("actual", "expected"),
                )
            parsed = add_base(
                "dependency_artifact",
                artifact.task_id,
                {
                    "read_op": "dependency_artifact_json",
                    "arguments": dict(common),
                    "transforms": [],
                },
                ("actual", "expected"),
            )
            if parsed is not None:
                for pointer in _json_pointers(parsed, max_nodes=self.max_json_nodes):
                    add_base(
                        "dependency_artifact",
                        artifact.task_id,
                        {
                            "read_op": "dependency_artifact_json_pointer",
                            "arguments": {**common, "pointer": pointer},
                            "transforms": [],
                        },
                        ("actual", "expected"),
                    )

        for memory in sorted(
            (
                item
                for item in state.memory_index.values()
                if item.task_id in task.dependencies
            ),
            key=lambda item: (item.task_id, item.memory_id),
        ):
            common = {"task_id": memory.task_id, "memory_id": memory.memory_id}
            for suffix in ("text", "sha256"):
                add_base(
                    "dependency_memory",
                    memory.task_id,
                    {
                        "read_op": f"dependency_memory_{suffix}",
                        "arguments": dict(common),
                        "transforms": [],
                    },
                    ("actual", "expected"),
                )
            parsed = add_base(
                "dependency_memory",
                memory.task_id,
                {
                    "read_op": "dependency_memory_json",
                    "arguments": dict(common),
                    "transforms": [],
                },
                ("actual", "expected"),
            )
            if parsed is not None:
                for pointer in _json_pointers(parsed, max_nodes=self.max_json_nodes):
                    add_base(
                        "dependency_memory",
                        memory.task_id,
                        {
                            "read_op": "dependency_memory_json_pointer",
                            "arguments": {**common, "pointer": pointer},
                            "transforms": [],
                        },
                        ("actual", "expected"),
                    )

        for intent in sorted(intents, key=lambda item: item.intent_id):
            if intent.expected_source_kind != "goal_literal":
                continue
            literal = intent.expected_goal_literal
            add_base(
                "goal_literal",
                state.goal.goal_id,
                {
                    "read_op": "goal_literal",
                    "arguments": {
                        "goal_quote": literal.get("goal_quote"),
                        "value": literal.get("value"),
                    },
                    "transforms": [],
                },
                ("expected",),
                intent_id=intent.intent_id,
            )

        candidates.sort(
            key=lambda item: _canonical(
                {
                    "source_descriptor": item["source_descriptor"],
                    "operator_value": item["operator_value"],
                }
            )
        )
        source_keys = sorted(
            {_canonical(item["source_descriptor"]) for item in candidates}
        )
        # Source IDs are descriptor-derived so adding an RWKV-selected Goal
        # literal after the discovery pass cannot renumber an already selected
        # action/workspace/dependency source.
        source_id_by_key: dict[bytes, str] = {}
        used_source_ids: set[str] = set()
        for key in source_keys:
            source_id = f"WS-{hashlib.sha256(key).hexdigest()[:16]}"
            if source_id in used_source_ids:
                raise WitnessCatalogError("witness source ID hash collision")
            used_source_ids.add(source_id)
            source_id_by_key[key] = source_id
        handles: list[dict[str, Any]] = []
        candidates_by_source: dict[str, list[dict[str, Any]]] = {}
        for index, candidate in enumerate(candidates, start=1):
            source_descriptor = candidate.pop("source_descriptor")
            source_handle_id = source_id_by_key[_canonical(source_descriptor)]
            handle = {
                "handle_id": f"WH-{index:04d}",
                "source_handle_id": source_handle_id,
                **candidate,
            }
            handles.append(handle)
            candidates_by_source.setdefault(source_handle_id, []).append(handle)

        def source_preview_key(handle: Mapping[str, Any]) -> tuple[Any, ...]:
            operator = handle.get("operator_value") or {}
            read_op = str(operator.get("read_op") or "")
            arguments = operator.get("arguments") or {}
            priority = {
                "action_output_text": 0,
                "action_output_json": 1,
                "action_result_json_pointer": 2,
                "workspace_text": 0,
                "workspace_json": 1,
                "workspace_json_pointer": 2,
                "workspace_directory_file_set": 3,
                "workspace_sha256": 4,
                "workspace_path_exists": 5,
                "dependency_artifact_text": 0,
                "dependency_artifact_json": 1,
                "dependency_artifact_json_pointer": 2,
                "dependency_artifact_sha256": 3,
                "dependency_memory_text": 0,
                "dependency_memory_json": 1,
                "dependency_memory_json_pointer": 2,
                "dependency_memory_sha256": 3,
                "goal_literal": 0,
            }.get(read_op, 99)
            root_pointer_penalty = int(arguments.get("pointer") not in {None, ""})
            transform_penalty = int(bool(operator.get("transforms")))
            return (
                transform_penalty,
                priority,
                root_pointer_penalty,
                _canonical(operator),
            )

        sources: list[dict[str, Any]] = []
        for source_key in source_keys:
            source_handle_id = source_id_by_key[source_key]
            source_handles = candidates_by_source[source_handle_id]
            descriptor = json.loads(source_key.decode("utf-8"))
            preview_handle = min(source_handles, key=source_preview_key)
            sources.append(
                {
                    "source_handle_id": source_handle_id,
                    **descriptor,
                    "eligible_sides": sorted(
                        {
                            side
                            for handle in source_handles
                            for side in handle.get("eligible_sides") or []
                        }
                    ),
                    "read_ops": sorted(
                        {
                            str((handle.get("operator_value") or {}).get("read_op") or "")
                            for handle in source_handles
                        }
                    ),
                    "handle_count": len(source_handles),
                    "source_preview_type": preview_handle.get("value_type"),
                    "source_preview": preview_handle.get("value_preview"),
                    "source_preview_truncated": preview_handle.get(
                        "value_preview_truncated"
                    ),
                }
            )
        digest_payload = {
            "schema_version": WITNESS_CATALOG_SCHEMA,
            "goal_digest": state.goal.digest,
            "task_id": task.task_id,
            "attempt_id": attempt.attempt_id,
            "workspace_digest": snapshot.get("digest"),
            "sources": sources,
            "handles": handles,
        }
        digest = hashlib.sha256(_canonical(digest_payload)).hexdigest()
        return {
            **digest_payload,
            "catalog_digest": digest,
            "complete": True,
            "handle_count": len(handles),
            "source_count": len(sources),
            "bounds": {
                "max_json_nodes": self.max_json_nodes,
                "max_handles": self.max_handles,
                "max_group_pairs": self.max_group_pairs,
                "preview_chars": self.preview_chars,
            },
        }


def witness_source_prompt_view(
    catalog: Mapping[str, Any],
    intents: Sequence[WitnessIntentState],
) -> list[dict[str, Any]]:
    """Show every raw source compatible with RWKV-precommitted ownership."""

    sources = [
        item for item in catalog.get("sources") or [] if isinstance(item, Mapping)
    ]
    result: list[dict[str, Any]] = []
    for intent in intents:
        actual: list[dict[str, Any]] = []
        expected: list[dict[str, Any]] = []
        for source in sources:
            compact = {
                "source_handle_id": source.get("source_handle_id"),
                "owner_task_id": source.get("owner_task_id"),
                "locator": source.get("locator"),
                "read_ops": source.get("read_ops"),
                "derived_handle_count": source.get("handle_count"),
                "source_preview_type": source.get("source_preview_type"),
                "source_preview": source.get("source_preview"),
                "source_preview_truncated": source.get(
                    "source_preview_truncated"
                ),
            }
            if (
                "actual" in (source.get("eligible_sides") or [])
                and source.get("source_kind") == intent.actual_source_kind
                and source.get("owner_task_id") == intent.producer_task_id
            ):
                actual.append(compact)
            if (
                "expected" in (source.get("eligible_sides") or [])
                and source.get("source_kind") == intent.expected_source_kind
                and (
                    source.get("source_kind") != "goal_literal"
                    or source.get("intent_id") == intent.intent_id
                )
            ):
                expected.append(compact)
        result.append(
            {
                "intent": {
                    "intent_id": intent.intent_id,
                    "criterion_id": intent.criterion_id,
                    "subject_task_id": intent.subject_task_id,
                    "producer_task_id": intent.producer_task_id,
                    "comparison": intent.comparison,
                    "actual_source_kind": intent.actual_source_kind,
                    "expected_source_kind": intent.expected_source_kind,
                    "expected_goal_literal": intent.expected_goal_literal,
                    "revision": intent.revision,
                },
                "actual_sources": actual,
                "expected_sources": expected,
            }
        )
    return result


def witness_prompt_view(
    catalog: Mapping[str, Any],
    intents: Sequence[WitnessIntentState],
    source_selections: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Losslessly group compatible handles for bounded progressive disclosure."""

    handles = [item for item in catalog.get("handles") or [] if isinstance(item, Mapping)]
    selected_by_intent = {
        str(item.get("intent_id") or ""): dict(item)
        for item in source_selections or []
        if isinstance(item, Mapping)
    }

    def grouped(selected: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        by_base: dict[bytes, dict[str, Any]] = {}
        for handle in selected:
            operator = handle.get("operator_value") or {}
            key_payload = {
                "owner_task_id": handle.get("owner_task_id"),
                "read_op": operator.get("read_op"),
                "arguments": operator.get("arguments") or {},
            }
            key = _canonical(key_payload)
            group = by_base.setdefault(
                key,
                {
                    **key_payload,
                    "variants": [],
                },
            )
            group["variants"].append(
                {
                    "handle_id": handle.get("handle_id"),
                    "transforms": operator.get("transforms") or [],
                    "value_type": handle.get("value_type"),
                    "value_preview": handle.get("value_preview"),
                }
            )
        return [by_base[key] for key in sorted(by_base)]

    result: list[dict[str, Any]] = []
    for intent in intents:
        source_selection = selected_by_intent.get(intent.intent_id, {})
        actual_source_id = str(
            source_selection.get("actual_source_handle_id") or ""
        )
        expected_source_id = str(
            source_selection.get("expected_source_handle_id") or ""
        )
        actual: list[Mapping[str, Any]] = []
        expected: list[Mapping[str, Any]] = []
        for handle in handles:
            if (
                "actual" in (handle.get("eligible_sides") or [])
                and handle.get("source_kind") == intent.actual_source_kind
                and handle.get("owner_task_id") == intent.producer_task_id
                and (
                    not source_selections
                    or handle.get("source_handle_id") == actual_source_id
                )
            ):
                actual.append(handle)
            if (
                "expected" in (handle.get("eligible_sides") or [])
                and handle.get("source_kind") == intent.expected_source_kind
                and (
                    handle.get("source_kind") != "goal_literal"
                    or handle.get("intent_id") == intent.intent_id
                )
                and (
                    not source_selections
                    or handle.get("source_handle_id") == expected_source_id
                )
            ):
                expected.append(handle)
        result.append(
            {
                "intent": {
                    "intent_id": intent.intent_id,
                    "criterion_id": intent.criterion_id,
                    "subject_task_id": intent.subject_task_id,
                    "producer_task_id": intent.producer_task_id,
                    "comparison": intent.comparison,
                    "actual_source_kind": intent.actual_source_kind,
                    "expected_source_kind": intent.expected_source_kind,
                    "expected_goal_literal": intent.expected_goal_literal,
                    "revision": intent.revision,
                },
                "rwkv_source_selection": source_selection,
                "actual_source_groups": grouped(actual),
                "expected_source_groups": grouped(expected),
            }
        )
    return result


def expand_witness_bindings(
    intents: Sequence[WitnessIntentState],
    bindings: Sequence[Mapping[str, Any]],
    catalog: Mapping[str, Any],
    source_selections: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    intent_by_id = {item.intent_id: item for item in intents}
    handle_by_id = {
        str(item.get("handle_id") or ""): item
        for item in catalog.get("handles") or []
        if isinstance(item, Mapping)
    }
    source_selection_by_intent = {
        str(item.get("intent_id") or ""): dict(item)
        for item in source_selections or []
        if isinstance(item, Mapping)
    }
    if len(bindings) != len(intents):
        raise WitnessCatalogError("witness binding count does not match intents")
    seen: set[str] = set()
    assertions: list[dict[str, Any]] = []
    expected_fields = {
        "intent_id",
        "criterion_id",
        "actual_handle_id",
        "expected_handle_id",
    }
    for binding in bindings:
        if set(binding) != expected_fields:
            raise WitnessCatalogError(
                f"witness binding fields must be exactly {sorted(expected_fields)}"
            )
        intent_id = str(binding.get("intent_id") or "")
        intent = intent_by_id.get(intent_id)
        if intent is None or intent_id in seen:
            raise WitnessCatalogError("witness binding intent is unknown or duplicated")
        seen.add(intent_id)
        if str(binding.get("criterion_id") or "") != intent.criterion_id:
            raise WitnessCatalogError("witness binding criterion does not match intent")
        actual = handle_by_id.get(str(binding.get("actual_handle_id") or ""))
        expected = handle_by_id.get(str(binding.get("expected_handle_id") or ""))
        if actual is None or expected is None:
            raise WitnessCatalogError("witness binding selected an unknown handle")
        if "actual" not in (actual.get("eligible_sides") or []):
            raise WitnessCatalogError("actual witness handle is not actual-eligible")
        if "expected" not in (expected.get("eligible_sides") or []):
            raise WitnessCatalogError("expected witness handle is not expected-eligible")
        if actual.get("source_kind") != intent.actual_source_kind:
            raise WitnessCatalogError("actual witness handle changes the precommitted source kind")
        if expected.get("source_kind") != intent.expected_source_kind:
            raise WitnessCatalogError("expected witness handle changes the precommitted source kind")
        if actual.get("owner_task_id") != intent.producer_task_id:
            raise WitnessCatalogError("actual witness owner does not match producer_task_id")
        if (
            expected.get("source_kind") == "goal_literal"
            and expected.get("intent_id") != intent.intent_id
        ):
            raise WitnessCatalogError("goal literal handle belongs to another intent")
        if source_selections is not None:
            selection = source_selection_by_intent.get(intent.intent_id)
            if selection is None:
                raise WitnessCatalogError(
                    "witness source selections do not exactly cover intents"
                )
            if actual.get("source_handle_id") != selection.get(
                "actual_source_handle_id"
            ):
                raise WitnessCatalogError(
                    "actual witness handle changes the RWKV-selected raw source"
                )
            if expected.get("source_handle_id") != selection.get(
                "expected_source_handle_id"
            ):
                raise WitnessCatalogError(
                    "expected witness handle changes the RWKV-selected raw source"
                )
        assertions.append(
            {
                "criterion_id": intent.criterion_id,
                "subject_task_id": intent.subject_task_id,
                "producer_task_id": intent.producer_task_id,
                "comparison": intent.comparison,
                "actual": dict(actual.get("operator_value") or {}),
                "expected": dict(expected.get("operator_value") or {}),
            }
        )
    if seen != set(intent_by_id):
        raise WitnessCatalogError("witness bindings do not exactly cover intents")
    return assertions


__all__ = [
    "ACTUAL_WITNESS_SOURCE_KINDS",
    "EXPECTED_WITNESS_SOURCE_KINDS",
    "WITNESS_CATALOG_SCHEMA",
    "WitnessCatalogBuilder",
    "WitnessCatalogError",
    "expand_witness_bindings",
    "witness_prompt_view",
    "witness_source_prompt_view",
]
