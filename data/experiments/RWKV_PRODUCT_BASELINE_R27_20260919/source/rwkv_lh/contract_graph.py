"""Typed contract graph shared by the strong planner and RWKV atom runtime."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Protocol, Sequence

from rwkv_lh.supervisor import SupervisorAtom


OBLIGATION_SCHEMA_VERSION = "rwkv-lh.contract-obligation.v1"
OBLIGATION_SCHEMA_VERSION_V2 = "rwkv-lh.contract-obligation.v2"
ASSERTION_SCHEMA_VERSION = "rwkv-lh.contract-assertion.v1"
GRAPH_NODE_SCHEMA_VERSION = "rwkv-lh.contract-graph-node.v1"
GRAPH_PATCH_SCHEMA_VERSION = "rwkv-lh.contract-graph-patch.v1"
GRAPH_NODE_SCHEMA_VERSION_V2 = "rwkv-lh.contract-graph-node.v2"
GRAPH_PATCH_SCHEMA_VERSION_V2 = "rwkv-lh.contract-graph-patch.v2"
GRAPH_REVIEW_SCHEMA_VERSION = "rwkv-lh.contract-graph-review.v1"
RESULT_CAPSULE_SCHEMA_VERSION = "rwkv-lh.result-capsule.v1"
EXECUTION_BATCH_SCHEMA_VERSION = "rwkv-lh.contract-execution-batch.v1"

_REQUEST_PATH_SUFFIXES = (
    "json",
    "jsonl",
    "md",
    "txt",
    "csv",
    "yaml",
    "yml",
    "toml",
    "py",
    "js",
    "mjs",
    "cjs",
    "jsx",
    "ts",
    "tsx",
    "html",
    "css",
    "xml",
    "sh",
    "ini",
    "cfg",
    "sql",
)
_REQUEST_PATH_PATTERN = re.compile(
    r"(?<![A-Za-z0-9_.-])[A-Za-z0-9_.-]+(?:/[A-Za-z0-9_.-]+)*"
    rf"\.(?:{'|'.join(_REQUEST_PATH_SUFFIXES)})",
    flags=re.IGNORECASE,
)
_REQUEST_FILE_SEGMENT_PATTERN = re.compile(
    rf".+\.(?:{'|'.join(_REQUEST_PATH_SUFFIXES)})$",
    flags=re.IGNORECASE,
)


def _digest(value: Mapping[str, Any]) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _identifier(name: str, value: Any) -> str:
    text = str(value or "").strip()
    if not text or len(text) > 160:
        raise ValueError(f"{name} must be a non-empty bounded identifier")
    if any(character.isspace() for character in text):
        raise ValueError(f"{name} cannot contain whitespace")
    return text


def _text(name: str, value: Any, *, max_chars: int) -> str:
    text = str(value or "").strip()
    if not text:
        raise ValueError(f"{name} must be non-empty")
    if len(text) > max_chars:
        raise ValueError(f"{name} exceeds {max_chars} characters")
    return text


def _items(
    name: str,
    values: Sequence[Any],
    *,
    required: bool,
    max_items: int,
    max_chars: int,
) -> tuple[str, ...]:
    selected = tuple(
        _text(f"{name}[{index}]", value, max_chars=max_chars)
        for index, value in enumerate(values)
    )
    if required and not selected:
        raise ValueError(f"{name} must not be empty")
    if len(selected) > max_items:
        raise ValueError(f"{name} exceeds {max_items} items")
    if len(set(selected)) != len(selected):
        raise ValueError(f"{name} contains duplicates")
    return selected


def extract_request_paths(immutable_request: str) -> tuple[str, ...]:
    """Extract public file paths, including slash-delimited sibling notation.

    Natural-language requests often abbreviate sibling files as
    ``storage.py/service.py`` or ``index.html/styles.css/app.js``.  Treating the
    whole token as a nested path makes an otherwise correct typed contract
    impossible.  A slash remains a directory separator until a component itself
    has a recognized file suffix; the next component then starts a sibling path.
    """

    selected: list[str] = []
    for match in _REQUEST_PATH_PATTERN.finditer(str(immutable_request or "")):
        token = match.group(0).rstrip(".,;:)")
        current: list[str] = []
        for segment in token.split("/"):
            current.append(segment)
            if _REQUEST_FILE_SEGMENT_PATTERN.fullmatch(segment):
                selected.append("/".join(current))
                current = []
        if current:
            selected.append("/".join(current))
    return tuple(dict.fromkeys(path for path in selected if path))


class ContractAssertionKind(str, Enum):
    """Deterministic relations that can be evaluated from public results."""

    ARTIFACT_EXISTS = "artifact_exists"
    TEXT_EXACT = "text_exact"
    TEXT_CONTAINS = "text_contains"
    TEXT_EXCLUDES = "text_excludes"
    TEXT_TEMPLATE = "text_template"
    TEXT_REMOVE_ONLY = "text_remove_only"
    TRAILING_NEWLINE = "trailing_newline"
    JSON_REQUIRED_KEYS = "json_required_keys"
    JSON_EXACT_KEYS = "json_exact_keys"
    JSON_VALUE_EQUALS = "json_value_equals"
    JSON_VALUE_FROM_SOURCE = "json_value_from_source"
    JSON_PRESERVE = "json_preserve"
    SEQUENCE_SORTED = "sequence_sorted"
    NUMERIC_AGGREGATE = "numeric_aggregate"
    DIGEST_EQUAL = "digest_equal"
    COMMAND_SUCCEEDED = "command_succeeded"
    SEMANTIC_REVIEW = "semantic_review"


class ObligationPhase(str, Enum):
    """Boundary at which an immutable user obligation can be satisfied."""

    EXECUTION_EVIDENCE = "execution_evidence"
    FINAL_PRESENTATION = "final_presentation"


@dataclass(frozen=True)
class ContractExecutionBatch:
    """Minimal durable handoff from the contract scheduler to RWKV workers."""

    stage_id: str
    stage_index: int
    graph_revision: int
    node_ids: tuple[str, ...]
    request_digest: str
    schema_version: str = EXECUTION_BATCH_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        stage_index: int,
        graph_revision: int,
        node_ids: Sequence[Any],
        request_digest: Any,
    ) -> "ContractExecutionBatch":
        if int(stage_index) < 1:
            raise ValueError("contract execution batch index must be positive")
        if int(graph_revision) < 1:
            raise ValueError("contract execution batch graph revision must be positive")
        selected_ids = _items(
            "contract_batch.node_ids",
            node_ids,
            required=True,
            max_items=16,
            max_chars=160,
        )
        digest = _text("request_digest", request_digest, max_chars=160)
        payload = {
            "stage_index": int(stage_index),
            "graph_revision": int(graph_revision),
            "node_ids": list(selected_ids),
            "request_digest": digest,
        }
        return cls(
            stage_id=f"CONTRACT-BATCH-{_digest(payload)[:20]}",
            stage_index=payload["stage_index"],
            graph_revision=payload["graph_revision"],
            node_ids=selected_ids,
            request_digest=digest,
        )

    @classmethod
    def restore(cls, value: Mapping[str, Any]) -> "ContractExecutionBatch":
        if str(value.get("schema_version") or "") != EXECUTION_BATCH_SCHEMA_VERSION:
            raise ValueError("unsupported contract execution batch schema")
        batch = cls.create(
            stage_index=int(value.get("stage_index", 0) or 0),
            graph_revision=int(value.get("graph_revision", 0) or 0),
            node_ids=value.get("node_ids") or (),
            request_digest=value.get("request_digest"),
        )
        if str(value.get("stage_id") or "") != batch.stage_id:
            raise ValueError("contract execution batch id does not match its content")
        return batch

    @classmethod
    def from_legacy_stage(
        cls,
        *,
        stage_id: Any,
        stage_index: int,
        graph_revision: int,
        node_ids: Sequence[Any],
        request_digest: Any,
    ) -> "ContractExecutionBatch":
        """Project a previously committed SupervisorStage without rewriting history."""

        current = cls.create(
            stage_index=stage_index,
            graph_revision=graph_revision,
            node_ids=node_ids,
            request_digest=request_digest,
        )
        return cls(
            stage_id=_identifier("legacy contract stage_id", stage_id),
            stage_index=current.stage_index,
            graph_revision=current.graph_revision,
            node_ids=current.node_ids,
            request_digest=current.request_digest,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "stage_id": self.stage_id,
            "stage_index": self.stage_index,
            "graph_revision": self.graph_revision,
            "node_ids": list(self.node_ids),
            "request_digest": self.request_digest,
        }


@dataclass(frozen=True)
class ContractSourceRef:
    path: str
    pointer: str = ""

    @classmethod
    def create(cls, *, path: Any, pointer: Any = "") -> "ContractSourceRef":
        selected_path = str(path or "").strip().replace("\\", "/")
        selected_pointer = str(pointer or "").strip()
        if not selected_path or len(selected_path) > 500:
            raise ValueError("contract assertion source path must be non-empty")
        if selected_pointer and not selected_pointer.startswith("/"):
            raise ValueError("contract assertion source pointer must be a JSON pointer")
        if len(selected_pointer) > 500:
            raise ValueError("contract assertion source pointer is too long")
        return cls(path=selected_path, pointer=selected_pointer)

    def to_dict(self) -> dict[str, str]:
        return {"path": self.path, "pointer": self.pointer}

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContractSourceRef":
        return cls.create(path=value.get("path"), pointer=value.get("pointer"))


@dataclass(frozen=True)
class ContractAssertion:
    assertion_id: str
    kind: ContractAssertionKind
    target_path: str
    target_pointer: str
    sources: tuple[ContractSourceRef, ...]
    expected: str
    keys: tuple[str, ...]
    order: str
    algorithm: str
    schema_version: str = ASSERTION_SCHEMA_VERSION

    def local_evaluation_issue(self) -> str:
        """Return why this assertion is unsafe for deterministic local review.

        The Planner may describe relations that are meaningful to a semantic
        Reviewer but are not encoded by this compact DSL.  Such assertions stay
        in the frozen user contract, but must not be interpreted as a different
        relation and turned into a deterministic contradiction.
        """

        if self.kind == ContractAssertionKind.SEMANTIC_REVIEW:
            return "assertion explicitly requires semantic Reviewer evaluation"

        text_kinds = {
            ContractAssertionKind.TEXT_EXACT,
            ContractAssertionKind.TEXT_CONTAINS,
            ContractAssertionKind.TEXT_EXCLUDES,
            ContractAssertionKind.TEXT_TEMPLATE,
            ContractAssertionKind.TEXT_REMOVE_ONLY,
            ContractAssertionKind.TRAILING_NEWLINE,
        }
        source_kinds = {
            ContractAssertionKind.JSON_VALUE_FROM_SOURCE,
            ContractAssertionKind.JSON_PRESERVE,
            ContractAssertionKind.NUMERIC_AGGREGATE,
            ContractAssertionKind.TEXT_TEMPLATE,
            ContractAssertionKind.TEXT_REMOVE_ONLY,
            ContractAssertionKind.DIGEST_EQUAL,
        }
        if self.kind in text_kinds and self.target_pointer:
            return "text assertions cannot select a JSON pointer"
        non_json_suffixes = (
            ".txt",
            ".md",
            ".csv",
            ".jsonl",
            ".log",
            ".yaml",
            ".yml",
            ".toml",
            ".py",
            ".js",
            ".ts",
            ".html",
            ".xml",
        )
        if any(
            source.pointer and source.path.casefold().endswith(non_json_suffixes)
            for source in self.sources
        ):
            return "a JSON pointer cannot be applied to an explicitly non-JSON source"
        if self.sources and self.kind not in source_kinds:
            return "this assertion kind does not consume source references"
        if self.kind == ContractAssertionKind.TEXT_TEMPLATE:
            if not self.sources:
                return "text_template requires one or more source references"
            if not re.search(r"(?<!\{)\{[^{}]+\}(?!\})", self.expected):
                return "text_template expected value has no executable placeholder"
            if self.order and len(self.sources) != 1:
                return "ordered text_template requires exactly one object-list source"
            if self.order and len(self.keys) != 1:
                return "ordered text_template requires exactly one sort key"
            if self.keys and not self.order:
                return "text_template sort keys require an explicit order"
        if self.kind == ContractAssertionKind.TEXT_REMOVE_ONLY:
            if len(self.sources) != 1:
                return "text_remove_only requires exactly one baseline source"
            if not self.expected:
                return "text_remove_only requires exact removed text"
            if self.sources[0].pointer:
                return "text_remove_only cannot use a JSON pointer"
        if self.kind in {
            ContractAssertionKind.JSON_VALUE_FROM_SOURCE,
            ContractAssertionKind.JSON_PRESERVE,
        }:
            if len(self.sources) != 1:
                return "direct JSON source equality requires exactly one source"
            if self.expected.strip():
                return "direct JSON source equality cannot encode a prose transformation"
        if self.kind == ContractAssertionKind.NUMERIC_AGGREGATE:
            if not self.sources:
                return "numeric_aggregate requires source references"
            if self.algorithm not in {"count", "sum", "minimum", "maximum"}:
                return "aggregate algorithm is not implemented by the local evaluator"
            if self.expected.strip():
                return "numeric_aggregate cannot encode an additional prose transformation"
        if self.kind == ContractAssertionKind.DIGEST_EQUAL:
            if len(self.sources) > 1:
                return "digest_equal supports at most one source"
            if self.sources and self.expected.strip():
                return "digest_equal cannot combine a source with an expected digest"
            if not self.sources and not re.fullmatch(r"[0-9a-fA-F]{64}", self.expected.strip()):
                return "digest_equal expected value must be a SHA256 digest"
        if self.kind in {
            ContractAssertionKind.JSON_REQUIRED_KEYS,
            ContractAssertionKind.JSON_EXACT_KEYS,
        } and not self.keys:
            return "JSON key assertion requires one or more keys"
        if self.kind == ContractAssertionKind.SEQUENCE_SORTED and not self.order:
            return "sequence_sorted requires an explicit order"
        return ""

    @classmethod
    def create(
        cls,
        *,
        assertion_id: Any,
        kind: ContractAssertionKind | str,
        target_path: Any = "",
        target_pointer: Any = "",
        sources: Sequence[ContractSourceRef | Mapping[str, Any]] = (),
        expected: Any = "",
        keys: Sequence[Any] = (),
        order: Any = "",
        algorithm: Any = "",
    ) -> "ContractAssertion":
        selected_kind = (
            kind if isinstance(kind, ContractAssertionKind) else ContractAssertionKind(str(kind))
        )
        path = str(target_path or "").strip().replace("\\", "/")
        pointer = str(target_pointer or "").strip()
        if pointer and not pointer.startswith("/"):
            raise ValueError("contract assertion target pointer must be a JSON pointer")
        if len(path) > 500 or len(pointer) > 500:
            raise ValueError("contract assertion target is too long")
        if selected_kind not in {
            ContractAssertionKind.COMMAND_SUCCEEDED,
            ContractAssertionKind.SEMANTIC_REVIEW,
        } and not path:
            raise ValueError("contract assertion target_path must be non-empty")
        selected_sources = tuple(
            item
            if isinstance(item, ContractSourceRef)
            else ContractSourceRef.from_dict(item)
            for item in sources
        )
        if len(selected_sources) > 8:
            raise ValueError("contract assertion sources exceed 8 items")
        selected_expected = str(expected if expected is not None else "")
        if len(selected_expected) > 2400:
            raise ValueError("contract assertion expected value is too long")
        selected_keys = _items(
            "assertion.keys", keys, required=False, max_items=32, max_chars=160
        )
        selected_order = str(order or "").strip().casefold()
        if selected_order not in {"", "ascending", "descending"}:
            raise ValueError("contract assertion order is unsupported")
        if selected_kind == ContractAssertionKind.TEXT_TEMPLATE:
            if selected_order and len(selected_sources) != 1:
                raise ValueError(
                    "ordered text_template requires exactly one object-list source"
                )
            if selected_order and len(selected_keys) != 1:
                raise ValueError(
                    "ordered text_template requires exactly one sort key"
                )
            if selected_keys and not selected_order:
                raise ValueError(
                    "text_template sort keys require an explicit order"
                )
        selected_algorithm = str(algorithm or "").strip().casefold()
        if selected_algorithm not in {
            "",
            "sum",
            "count",
            "minimum",
            "maximum",
            "sha256",
            "bytes",
            "lines",
        }:
            raise ValueError("contract assertion algorithm is unsupported")
        return cls(
            assertion_id=_identifier("assertion_id", assertion_id),
            kind=selected_kind,
            target_path=path,
            target_pointer=pointer,
            sources=selected_sources,
            expected=selected_expected,
            keys=selected_keys,
            order=selected_order,
            algorithm=selected_algorithm,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "assertion_id": self.assertion_id,
            "kind": self.kind.value,
            "target_path": self.target_path,
            "target_pointer": self.target_pointer,
            "sources": [item.to_dict() for item in self.sources],
            "expected": self.expected,
            "keys": list(self.keys),
            "order": self.order,
            "algorithm": self.algorithm,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ContractAssertion":
        if str(value.get("schema_version") or ASSERTION_SCHEMA_VERSION) != ASSERTION_SCHEMA_VERSION:
            raise ValueError("unsupported contract assertion schema")
        return cls.create(
            assertion_id=value.get("assertion_id"),
            kind=str(value.get("kind") or ""),
            target_path=value.get("target_path"),
            target_pointer=value.get("target_pointer"),
            sources=(
                item for item in value.get("sources") or () if isinstance(item, Mapping)
            ),
            expected=value.get("expected"),
            keys=value.get("keys") or (),
            order=value.get("order"),
            algorithm=value.get("algorithm"),
        )


@dataclass(frozen=True)
class ContractObligation:
    obligation_id: str
    request_clause: str
    predicate: str
    evidence_kinds: tuple[str, ...]
    assertions: tuple[ContractAssertion, ...] = ()
    required: bool = True
    phase: ObligationPhase = ObligationPhase.EXECUTION_EVIDENCE
    schema_version: str = OBLIGATION_SCHEMA_VERSION_V2

    @classmethod
    def create(
        cls,
        immutable_request: str,
        *,
        obligation_id: str,
        request_clause: str,
        predicate: str,
        evidence_kinds: Sequence[str],
        assertions: Sequence[ContractAssertion | Mapping[str, Any]] = (),
        required: bool = True,
        phase: ObligationPhase | str = ObligationPhase.EXECUTION_EVIDENCE,
        schema_version: str = OBLIGATION_SCHEMA_VERSION_V2,
    ) -> "ContractObligation":
        request = str(immutable_request or "")
        clause = _text("request_clause", request_clause, max_chars=2400)
        if clause not in request:
            raise ValueError("obligation request_clause must be verbatim request text")
        if required is not True:
            raise ValueError(
                "immutable-request contract obligations must be required"
            )
        predicate_text = _text("predicate", predicate, max_chars=2400)
        introduced_keys = {
            match.group(1)
            for match in re.finditer(
                r"(?:explicit\s+)?keys?\s+[`\"]([A-Za-z][A-Za-z0-9_]*)[`\"]",
                predicate_text,
                flags=re.IGNORECASE,
            )
            if match.group(1) not in request
        }
        if introduced_keys:
            raise ValueError(
                "obligation predicate introduced explicit JSON keys absent from the "
                f"immutable request: {sorted(introduced_keys)}"
            )
        selected_assertions = tuple(
            item
            if isinstance(item, ContractAssertion)
            else ContractAssertion.from_dict(item)
            for item in assertions
        )
        if len(selected_assertions) > 32:
            raise ValueError("contract obligation assertions exceed 32 items")
        assertion_ids = [item.assertion_id for item in selected_assertions]
        if len(set(assertion_ids)) != len(assertion_ids):
            raise ValueError("contract obligation assertion ids contain duplicates")
        selected_phase = (
            phase if isinstance(phase, ObligationPhase) else ObligationPhase(str(phase))
        )
        if selected_phase == ObligationPhase.FINAL_PRESENTATION and selected_assertions:
            raise ValueError("final-presentation obligation cannot require tool assertions")
        if schema_version not in {
            OBLIGATION_SCHEMA_VERSION,
            OBLIGATION_SCHEMA_VERSION_V2,
        }:
            raise ValueError("unsupported contract obligation schema")
        if (
            schema_version == OBLIGATION_SCHEMA_VERSION
            and selected_phase != ObligationPhase.EXECUTION_EVIDENCE
        ):
            raise ValueError("v1 contract obligations only support execution evidence")
        return cls(
            obligation_id=_identifier("obligation_id", obligation_id),
            request_clause=clause,
            predicate=predicate_text,
            evidence_kinds=_items(
                "evidence_kinds",
                evidence_kinds,
                required=(
                    selected_phase == ObligationPhase.EXECUTION_EVIDENCE
                ),
                max_items=8,
                max_chars=80,
            ),
            assertions=selected_assertions,
            required=required,
            phase=selected_phase,
            schema_version=schema_version,
        )

    def to_dict(self) -> dict[str, Any]:
        value = {
            "schema_version": self.schema_version,
            "obligation_id": self.obligation_id,
            "request_clause": self.request_clause,
            "predicate": self.predicate,
            "evidence_kinds": list(self.evidence_kinds),
            "assertions": [item.to_dict() for item in self.assertions],
            "required": self.required,
        }
        if self.schema_version == OBLIGATION_SCHEMA_VERSION_V2:
            value["phase"] = self.phase.value
        return value

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        immutable_request: str,
    ) -> "ContractObligation":
        supplied_schema = str(value.get("schema_version") or OBLIGATION_SCHEMA_VERSION)
        if supplied_schema not in {
            OBLIGATION_SCHEMA_VERSION,
            OBLIGATION_SCHEMA_VERSION_V2,
        }:
            raise ValueError("unsupported contract obligation schema")
        return cls.create(
            immutable_request,
            obligation_id=str(value.get("obligation_id") or ""),
            request_clause=str(value.get("request_clause") or ""),
            predicate=str(value.get("predicate") or ""),
            evidence_kinds=value.get("evidence_kinds") or (),
            assertions=(
                item for item in value.get("assertions") or () if isinstance(item, Mapping)
            ),
            # Migrate unsafe v1 planner-authored optional flags to the local
            # invariant: immutable user obligations are always mandatory.
            required=True,
            phase=(
                value.get("phase")
                if supplied_schema == OBLIGATION_SCHEMA_VERSION_V2
                else ObligationPhase.EXECUTION_EVIDENCE.value
            ),
            schema_version=supplied_schema,
        )


@dataclass(frozen=True)
class ContractGraphNode:
    node_id: str
    obligation_ids: tuple[str, ...]
    atom: SupervisorAtom
    schema_version: str = GRAPH_NODE_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        node_id: str,
        obligation_ids: Sequence[str],
        atom: SupervisorAtom,
    ) -> "ContractGraphNode":
        identifier = _identifier("node_id", node_id)
        if identifier != atom.atom_id:
            raise ValueError("graph node_id must equal its atom_id")
        obligations = tuple(
            _identifier(f"obligation_ids[{index}]", value)
            for index, value in enumerate(obligation_ids)
        )
        if not obligations:
            raise ValueError("graph node must bind at least one obligation")
        if len(set(obligations)) != len(obligations):
            raise ValueError("graph node obligation_ids contain duplicates")
        node_schema = (
            GRAPH_NODE_SCHEMA_VERSION_V2
            if atom.operation_allowset_source
            else GRAPH_NODE_SCHEMA_VERSION
        )
        return cls(identifier, obligations, atom, node_schema)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "node_id": self.node_id,
            "obligation_ids": list(self.obligation_ids),
            "atom": self.atom.to_dict(),
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        immutable_request: str,
    ) -> "ContractGraphNode":
        supplied_schema = str(
            value.get("schema_version") or GRAPH_NODE_SCHEMA_VERSION
        )
        if supplied_schema not in {
            GRAPH_NODE_SCHEMA_VERSION,
            GRAPH_NODE_SCHEMA_VERSION_V2,
        }:
            raise ValueError("unsupported contract graph node schema")
        atom_value = value.get("atom")
        if not isinstance(atom_value, Mapping):
            raise ValueError("contract graph node has no atom")
        node = cls.create(
            node_id=str(value.get("node_id") or ""),
            obligation_ids=value.get("obligation_ids") or (),
            atom=SupervisorAtom.from_dict(
                atom_value,
                immutable_request=immutable_request,
            ),
        )
        if node.schema_version != supplied_schema:
            raise ValueError("contract graph node schema does not match its authority")
        return node


@dataclass(frozen=True)
class ContractGraphPatch:
    patch_id: str
    base_revision: int
    summary: str
    new_obligations: tuple[ContractObligation, ...]
    new_nodes: tuple[ContractGraphNode, ...]
    schema_version: str = GRAPH_PATCH_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        request_digest: str,
        base_revision: int,
        summary: str,
        new_obligations: Sequence[ContractObligation],
        new_nodes: Sequence[ContractGraphNode],
        existing_obligation_ids: Sequence[str] = (),
        existing_node_ids: Sequence[str] = (),
    ) -> "ContractGraphPatch":
        if isinstance(base_revision, bool) or not isinstance(base_revision, int):
            raise ValueError("base_revision must be an integer")
        if base_revision < 0:
            raise ValueError("base_revision must not be negative")
        obligations = tuple(new_obligations)
        nodes = tuple(new_nodes)
        existing_obligations = tuple(
            _identifier(f"existing_obligation_ids[{index}]", value)
            for index, value in enumerate(existing_obligation_ids)
        )
        existing_nodes = tuple(
            _identifier(f"existing_node_ids[{index}]", value)
            for index, value in enumerate(existing_node_ids)
        )
        if not obligations and not nodes:
            raise ValueError("a graph patch must add obligations or nodes")
        obligation_ids = [item.obligation_id for item in obligations]
        node_ids = [item.node_id for item in nodes]
        if len(set(obligation_ids)) != len(obligation_ids):
            raise ValueError("graph patch contains duplicate obligation ids")
        if len(set(node_ids)) != len(node_ids):
            raise ValueError("graph patch contains duplicate node ids")
        if set(obligation_ids) & set(existing_obligations):
            raise ValueError("graph patch cannot redefine an existing obligation")
        if set(node_ids) & set(existing_nodes):
            raise ValueError("graph patch cannot redefine an existing node")
        all_obligation_ids = set(existing_obligations) | set(obligation_ids)
        all_node_ids = set(existing_nodes) | set(node_ids)
        for node in nodes:
            unknown_obligations = set(node.obligation_ids) - all_obligation_ids
            if unknown_obligations:
                raise ValueError(
                    f"graph node {node.node_id} references unknown obligations: "
                    f"{sorted(unknown_obligations)}"
                )
            unknown_dependencies = set(node.atom.depends_on) - all_node_ids
            if unknown_dependencies:
                raise ValueError(
                    f"graph node {node.node_id} references unknown dependencies: "
                    f"{sorted(unknown_dependencies)}"
                )
        graph = {
            node.node_id: tuple(node.atom.depends_on) for node in nodes
        }
        cls._assert_acyclic(graph)
        payload = {
            "request_digest": str(request_digest),
            "base_revision": base_revision,
            "summary": _text("summary", summary, max_chars=4000),
            "new_obligations": [item.to_dict() for item in obligations],
            "new_nodes": [item.to_dict() for item in nodes],
        }
        node_versions = {item.schema_version for item in nodes}
        if len(node_versions) > 1:
            raise ValueError("a graph patch cannot mix v1 and v2 node authorities")
        patch_schema = (
            GRAPH_PATCH_SCHEMA_VERSION_V2
            if node_versions == {GRAPH_NODE_SCHEMA_VERSION_V2}
            else GRAPH_PATCH_SCHEMA_VERSION
        )
        return cls(
            patch_id=f"PATCH-{_digest(payload)[:20]}",
            base_revision=base_revision,
            summary=payload["summary"],
            new_obligations=obligations,
            new_nodes=nodes,
            schema_version=patch_schema,
        )

    @staticmethod
    def _assert_acyclic(graph: Mapping[str, Sequence[str]]) -> None:
        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(node_id: str) -> None:
            if node_id in visited or node_id not in graph:
                return
            if node_id in visiting:
                raise ValueError("graph patch contains a dependency cycle")
            visiting.add(node_id)
            for dependency in graph[node_id]:
                visit(str(dependency))
            visiting.remove(node_id)
            visited.add(node_id)

        for node_id in graph:
            visit(node_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "patch_id": self.patch_id,
            "base_revision": self.base_revision,
            "summary": self.summary,
            "new_obligations": [item.to_dict() for item in self.new_obligations],
            "new_nodes": [item.to_dict() for item in self.new_nodes],
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        immutable_request: str,
        request_digest: str,
        existing_obligation_ids: Sequence[str] = (),
        existing_node_ids: Sequence[str] = (),
    ) -> "ContractGraphPatch":
        supplied_schema = str(
            value.get("schema_version") or GRAPH_PATCH_SCHEMA_VERSION
        )
        if supplied_schema not in {
            GRAPH_PATCH_SCHEMA_VERSION,
            GRAPH_PATCH_SCHEMA_VERSION_V2,
        }:
            raise ValueError("unsupported contract graph patch schema")
        patch = cls.create(
            request_digest=request_digest,
            base_revision=int(value.get("base_revision", 0) or 0),
            summary=str(value.get("summary") or ""),
            new_obligations=(
                ContractObligation.from_dict(item, immutable_request=immutable_request)
                for item in value.get("new_obligations") or ()
                if isinstance(item, Mapping)
            ),
            new_nodes=(
                ContractGraphNode.from_dict(item, immutable_request=immutable_request)
                for item in value.get("new_nodes") or ()
                if isinstance(item, Mapping)
            ),
            existing_obligation_ids=existing_obligation_ids,
            existing_node_ids=existing_node_ids,
        )
        supplied_id = str(value.get("patch_id") or "")
        if supplied_id and supplied_id != patch.patch_id:
            raise ValueError("contract graph patch id does not match its content")
        if patch.schema_version != supplied_schema:
            raise ValueError("contract graph patch schema does not match node authority")
        return patch


class ObligationVerdictStatus(str, Enum):
    SATISFIED = "satisfied"
    CONTRADICTED = "contradicted"
    INSUFFICIENT = "insufficient"


@dataclass(frozen=True)
class ObligationVerdict:
    obligation_id: str
    status: ObligationVerdictStatus
    evidence_refs: tuple[str, ...]
    reason: str

    @classmethod
    def create(
        cls,
        *,
        obligation_id: str,
        status: ObligationVerdictStatus | str,
        evidence_refs: Sequence[str],
        reason: str,
    ) -> "ObligationVerdict":
        selected = (
            status
            if isinstance(status, ObligationVerdictStatus)
            else ObligationVerdictStatus(str(status))
        )
        refs = tuple(
            _identifier(f"evidence_refs[{index}]", value)
            for index, value in enumerate(evidence_refs)
        )
        if selected in {
            ObligationVerdictStatus.SATISFIED,
            ObligationVerdictStatus.CONTRADICTED,
        } and not refs:
            raise ValueError(f"{selected.value} verdict requires evidence refs")
        if len(set(refs)) != len(refs):
            raise ValueError("verdict evidence_refs contain duplicates")
        return cls(
            obligation_id=_identifier("obligation_id", obligation_id),
            status=selected,
            evidence_refs=refs,
            reason=_text("reason", reason, max_chars=2000),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "obligation_id": self.obligation_id,
            "status": self.status.value,
            "evidence_refs": list(self.evidence_refs),
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ContractGraphReview:
    review_id: str
    graph_revision: int
    summary: str
    verdicts: tuple[ObligationVerdict, ...]
    schema_version: str = GRAPH_REVIEW_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        graph_revision: int,
        summary: str,
        verdicts: Sequence[ObligationVerdict],
        obligation_ids: Sequence[str],
        evidence_ids: Sequence[str],
    ) -> "ContractGraphReview":
        if graph_revision < 1:
            raise ValueError("graph review requires a positive revision")
        selected = tuple(verdicts)
        ids = [item.obligation_id for item in selected]
        if len(set(ids)) != len(ids):
            raise ValueError("graph review contains duplicate obligation verdicts")
        if set(ids) != set(obligation_ids):
            missing = set(obligation_ids) - set(ids)
            extra = set(ids) - set(obligation_ids)
            raise ValueError(
                "graph review must return exactly one verdict per obligation: "
                f"missing={sorted(missing)} extra={sorted(extra)}"
            )
        unknown = set(ids) - set(obligation_ids)
        if unknown:
            raise ValueError(f"graph review references unknown obligations: {sorted(unknown)}")
        known_evidence = set(evidence_ids)
        invalid_refs = {
            ref
            for verdict in selected
            for ref in verdict.evidence_refs
            if ref not in known_evidence
        }
        if invalid_refs:
            raise ValueError(
                f"graph review references unknown evidence: {sorted(invalid_refs)}"
            )
        payload = {
            "graph_revision": graph_revision,
            "summary": _text("summary", summary, max_chars=4000),
            "verdicts": [item.to_dict() for item in selected],
        }
        return cls(
            review_id=f"GRAPH-REVIEW-{_digest(payload)[:20]}",
            graph_revision=graph_revision,
            summary=payload["summary"],
            verdicts=selected,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "graph_revision": self.graph_revision,
            "summary": self.summary,
            "verdicts": [item.to_dict() for item in self.verdicts],
        }

    @classmethod
    def from_dict(
        cls,
        value: Mapping[str, Any],
        *,
        obligation_ids: Sequence[str],
        evidence_ids: Sequence[str],
    ) -> "ContractGraphReview":
        if str(value.get("schema_version") or GRAPH_REVIEW_SCHEMA_VERSION) != (
            GRAPH_REVIEW_SCHEMA_VERSION
        ):
            raise ValueError("unsupported contract graph review schema")
        review = cls.create(
            graph_revision=int(value.get("graph_revision", 0) or 0),
            summary=str(value.get("summary") or ""),
            verdicts=(
                ObligationVerdict.create(
                    obligation_id=str(item.get("obligation_id") or ""),
                    status=str(item.get("status") or ""),
                    evidence_refs=item.get("evidence_refs") or (),
                    reason=str(item.get("reason") or ""),
                )
                for item in value.get("verdicts") or ()
                if isinstance(item, Mapping)
            ),
            obligation_ids=obligation_ids,
            evidence_ids=evidence_ids,
        )
        supplied_id = str(value.get("review_id") or "")
        if supplied_id and supplied_id != review.review_id:
            raise ValueError("contract graph review id does not match its content")
        return review


@dataclass(frozen=True)
class ResultCapsule:
    """The only result fact allowed across the strong-model boundary.

    A capsule contains final operation observations, durable artifact identities, or
    a compact committed controller outcome such as ``replan_applied``.  It
    intentionally has no prompt, transcript, intermediate decision, rejection,
    model request, or natural-language worker summary field.  The one explicit
    exception is a ``final_answer`` capsule created by the Controller so an
    independent Reviewer can validate the exact, unmodified RWKV presentation.
    """

    evidence_id: str
    node_id: str
    observation_id: str
    node_status: str
    operation: str
    result: Mapping[str, Any]
    artifacts: tuple[Mapping[str, Any], ...]
    workspace_revision: str
    error_type: str = ""
    error_message: str = ""
    schema_version: str = RESULT_CAPSULE_SCHEMA_VERSION

    @classmethod
    def create(
        cls,
        *,
        node_id: str,
        observation_id: str = "terminal",
        node_status: str,
        operation: str,
        result: Mapping[str, Any] | None,
        artifacts: Sequence[Mapping[str, Any]] = (),
        workspace_revision: str = "",
        error_type: str = "",
        error_message: str = "",
    ) -> "ResultCapsule":
        status = _identifier("node_status", node_status)
        if status not in {"completed", "failed", "interrupted"}:
            raise ValueError("result capsule has unsupported node_status")
        selected_result = dict(result or {})
        selected_artifacts = tuple(dict(item) for item in artifacts)
        payload = {
            "schema_version": RESULT_CAPSULE_SCHEMA_VERSION,
            "node_id": _identifier("node_id", node_id),
            "observation_id": _identifier("observation_id", observation_id),
            "node_status": status,
            "operation": _identifier("operation", operation),
            "result": selected_result,
            "artifacts": list(selected_artifacts),
            "workspace_revision": str(workspace_revision or ""),
            "error_type": str(error_type or "")[:160],
            "error_message": str(error_message or "")[:2000],
        }
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        if len(encoded) > 24_000:
            raise ValueError("result capsule exceeds 24000 serialized characters")
        return cls(
            evidence_id=f"EVID-{hashlib.sha256(encoded.encode('utf-8')).hexdigest()[:20]}",
            node_id=payload["node_id"],
            observation_id=payload["observation_id"],
            node_status=status,
            operation=payload["operation"],
            result=selected_result,
            artifacts=selected_artifacts,
            workspace_revision=payload["workspace_revision"],
            error_type=payload["error_type"],
            error_message=payload["error_message"],
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "evidence_id": self.evidence_id,
            "node_id": self.node_id,
            "observation_id": self.observation_id,
            "node_status": self.node_status,
            "operation": self.operation,
            "result": dict(self.result),
            "artifacts": [dict(item) for item in self.artifacts],
            "workspace_revision": self.workspace_revision,
            "error_type": self.error_type,
            "error_message": self.error_message,
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ResultCapsule":
        if str(value.get("schema_version") or RESULT_CAPSULE_SCHEMA_VERSION) != (
            RESULT_CAPSULE_SCHEMA_VERSION
        ):
            raise ValueError("unsupported result capsule schema")
        capsule = cls.create(
            node_id=str(value.get("node_id") or ""),
            observation_id=str(value.get("observation_id") or "terminal"),
            node_status=str(value.get("node_status") or ""),
            operation=str(value.get("operation") or ""),
            result=(value.get("result") if isinstance(value.get("result"), Mapping) else {}),
            artifacts=(
                item
                for item in value.get("artifacts") or ()
                if isinstance(item, Mapping)
            ),
            workspace_revision=str(value.get("workspace_revision") or ""),
            error_type=str(value.get("error_type") or ""),
            error_message=str(value.get("error_message") or ""),
        )
        if str(value.get("evidence_id") or "") != capsule.evidence_id:
            raise ValueError("result capsule evidence id does not match its content")
        return capsule


_CONTENT_MUTATION_OPERATIONS = frozenset(
    {
        "write_file",
        "write_json",
        "patch_json",
        "replace_text",
        "remove_line",
        "append_file",
    }
)
_CONTENT_OBSERVATION_OPERATIONS = frozenset({"read_file", "read_json"})


def _scope_covers_path(root: str, path: str) -> bool:
    selected_root = str(root or "").strip().replace("\\", "/").rstrip("/")
    selected_path = str(path or "").strip().replace("\\", "/").rstrip("/")
    if not selected_root or not selected_path:
        return False
    if selected_root == ".":
        return True
    return (
        selected_root == selected_path
        or selected_path.startswith(selected_root + "/")
        or selected_root.startswith(selected_path + "/")
    )


def validate_content_mutation_dependencies(
    patch: ContractGraphPatch,
    *,
    existing_nodes: Mapping[str, ContractGraphNode],
    result_capsules: Sequence[ResultCapsule],
    visible_paths: Sequence[str],
) -> None:
    """Require existing-content writers to consume the latest exact observation.

    RWKV atoms are isolated causal lanes.  A correction writer that merely sees a
    planner objective cannot safely preserve an existing artifact; it must directly
    receive the latest successful ``read_file``/``read_json`` result through its
    dependency handoff.
    """

    visible = tuple(str(item) for item in visible_paths if str(item or ""))
    successful_observation_nodes = {
        item.node_id
        for item in result_capsules
        if item.node_status == "completed"
        and item.operation in _CONTENT_OBSERVATION_OPERATIONS
        and bool(item.result.get("success"))
    }
    prior_observers = [
        node
        for node in existing_nodes.values()
        if node.node_id in successful_observation_nodes
        and any(
            operation in _CONTENT_OBSERVATION_OPERATIONS
            for operation in node.atom.allowed_operations
        )
    ]
    new_observers = {
        node.node_id: node
        for node in patch.new_nodes
        if any(
            operation in _CONTENT_OBSERVATION_OPERATIONS
            for operation in node.atom.allowed_operations
        )
    }

    for writer in patch.new_nodes:
        if not any(
            operation in _CONTENT_MUTATION_OPERATIONS
            for operation in writer.atom.allowed_operations
        ):
            continue
        for target in writer.atom.write_roots:
            if not any(_scope_covers_path(target, path) for path in visible):
                continue
            direct_new = [
                node
                for node_id, node in new_observers.items()
                if node_id in writer.atom.depends_on
                and any(
                    _scope_covers_path(root, target)
                    for root in node.atom.read_roots
                )
            ]
            matching_prior = [
                node
                for node in prior_observers
                if any(
                    _scope_covers_path(root, target)
                    for root in node.atom.read_roots
                )
            ]
            if direct_new:
                continue
            if any(
                operation in _CONTENT_OBSERVATION_OPERATIONS
                for operation in writer.atom.allowed_operations
            ) and any(
                _scope_covers_path(root, target)
                for root in writer.atom.read_roots
            ):
                # A narrow transaction can inspect the exact target immediately
                # before mutating it and then verify it without a cross-node handoff.
                continue
            if not matching_prior:
                raise ValueError(
                    f"content mutation {writer.node_id} must directly depend on a "
                    f"successful read_file/read_json observation of existing target {target}"
                )
            latest = matching_prior[-1]
            if latest.node_id not in writer.atom.depends_on:
                raise ValueError(
                    f"content mutation {writer.node_id} must directly depend on latest "
                    f"content observation {latest.node_id} for existing target {target}"
                )


def validate_contract_assertion_coverage(
    immutable_request: str,
    obligations: Sequence[ContractObligation],
) -> None:
    """Reject typed contracts that omit mechanically identifiable user material.

    This is deliberately lexical and fail-closed.  It does not invent a contract or
    inspect hidden acceptance; it only checks that exact public request literals and
    relations have a typed representation before local acceptance is possible.
    """

    selected = tuple(
        item
        for item in obligations
        if item.phase == ObligationPhase.EXECUTION_EVIDENCE
    )
    if not selected or any(not item.assertions for item in selected):
        raise ValueError("every execution-evidence obligation requires typed assertions")
    assertions = tuple(
        assertion for obligation in selected for assertion in obligation.assertions
    )
    encoded = json.dumps(
        {
            "assertions": [item.to_dict() for item in assertions],
            "presentation_predicates": [
                item.predicate
                for item in obligations
                if item.phase == ObligationPhase.FINAL_PRESENTATION
            ],
        },
        ensure_ascii=False,
        sort_keys=True,
    )
    exact_literals = tuple(
        dict.fromkeys(
            match.group(1)
            for match in re.finditer(r"`([^`\r\n]+)`", immutable_request)
            if match.group(1)
        )
    )
    missing_literals = [item for item in exact_literals if item not in encoded]
    if missing_literals:
        raise ValueError(
            "typed assertions omit exact request literals: "
            f"{missing_literals[:8]}"
        )

    request_paths = extract_request_paths(immutable_request)
    typed_paths = {
        path
        for assertion in assertions
        for path in (
            assertion.target_path,
            *(source.path for source in assertion.sources),
        )
        if path
    }
    missing_paths = [path for path in request_paths if path not in typed_paths]
    if missing_paths:
        raise ValueError(
            f"typed assertions omit request paths: {missing_paths[:8]}"
        )

    normalized = immutable_request.casefold()
    if any(term in normalized for term in ("sorted", "sort by", "ordering", "order by")):
        if not any(
            item.kind == ContractAssertionKind.SEQUENCE_SORTED or bool(item.order)
            for item in assertions
        ):
            raise ValueError("typed assertions omit the requested ordering relation")
    if any(term in normalized for term in ("trailing newline", "final newline", "line ending")):
        if not any(item.kind == ContractAssertionKind.TRAILING_NEWLINE for item in assertions):
            raise ValueError("typed assertions omit the requested newline relation")
    if re.search(r"\b(?:sha-?256|digest|hash)\b", normalized):
        if not any(
            item.kind == ContractAssertionKind.DIGEST_EQUAL
            or item.algorithm == "sha256"
            for item in assertions
        ):
            raise ValueError("typed assertions omit the requested digest relation")
    if (
        len(request_paths) >= 2
        and re.search(r"\bread\b", normalized)
        and re.search(r"\b(?:create|write|generate|build)\b", normalized)
        and not any(item.sources for item in assertions)
    ):
        raise ValueError("typed assertions omit the input-to-output source relation")


@dataclass(frozen=True)
class ContractPlanRequest:
    run_id: str
    request: str
    request_digest: str
    graph_revision: int
    obligations: tuple[Mapping[str, Any], ...]
    nodes: tuple[Mapping[str, Any], ...]
    latest_review: Mapping[str, Any] | None
    result_capsules: tuple[ResultCapsule, ...]
    available_operations: tuple[Mapping[str, Any], ...]
    workspace_manifest: Mapping[str, Any]
    node_statuses: Mapping[str, str] = field(default_factory=dict)
    finalizer_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        node_ids = {
            str(item.get("node_id") or "")
            for item in self.nodes
            if isinstance(item, Mapping)
        }
        statuses = {
            str(node_id): str(status)
            for node_id, status in self.node_statuses.items()
        }
        unknown_statuses = set(statuses) - node_ids
        if unknown_statuses:
            raise ValueError(
                "contract plan node statuses reference unknown nodes: "
                f"{sorted(unknown_statuses)}"
            )
        invalid_statuses = {
            node_id: status
            for node_id, status in statuses.items()
            if status not in {"pending", "completed", "failed", "interrupted"}
        }
        if invalid_statuses:
            raise ValueError(
                f"contract plan node statuses are invalid: {invalid_statuses}"
            )
        unsatisfied = {
            str(item.get("obligation_id") or "")
            for item in (self.latest_review or {}).get("verdicts") or ()
            if isinstance(item, Mapping)
            and str(item.get("status") or "") != "satisfied"
        }
        if self.graph_revision > 0 and self.latest_review is not None:
            obligations = [
                (
                    dict(item)
                    if str(item.get("obligation_id") or "") in unsatisfied
                    else {
                        "obligation_id": str(item.get("obligation_id") or ""),
                        "status": "satisfied",
                    }
                )
                for item in self.obligations
            ]
            nodes = []
            for item in self.nodes:
                atom = item.get("atom") if isinstance(item.get("atom"), Mapping) else {}
                nodes.append(
                    {
                        "node_id": str(item.get("node_id") or ""),
                        "status": statuses.get(
                            str(item.get("node_id") or ""),
                            "pending",
                        ),
                        "obligation_ids": list(item.get("obligation_ids") or ()),
                        "role": str(atom.get("role") or ""),
                        "depends_on": list(atom.get("depends_on") or ()),
                        "read_roots": list(atom.get("read_roots") or ()),
                        "write_roots": list(atom.get("write_roots") or ()),
                        "atom_kind": str(atom.get("atom_kind") or "legacy"),
                        "effect_ceiling": str(
                            atom.get("effect_ceiling") or "legacy"
                        ),
                        "operation_allowset_source": str(
                            atom.get("operation_allowset_source") or "legacy"
                        ),
                    }
                )
        else:
            obligations = [dict(item) for item in self.obligations]
            nodes = [dict(item) for item in self.nodes]
        capabilities_by_key: dict[tuple[str, ...], dict[str, str]] = {}
        for item in self.available_operations:
            selected = {
                "capability_class": str(item.get("capability_class") or ""),
                "network_access": str(item.get("network_access") or ""),
                "data_boundary": str(item.get("data_boundary") or ""),
                "side_effect_class": str(item.get("side_effect_class") or ""),
                "scope_mode": str(item.get("scope_mode") or ""),
            }
            key = tuple(selected[name] for name in sorted(selected))
            capabilities_by_key[key] = selected
        capabilities = [
            capabilities_by_key[key] for key in sorted(capabilities_by_key)
        ]
        return {
            "contract_version": "rwkv-lh.contract-graph-planner.v2",
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "graph_revision": self.graph_revision,
            "obligations": obligations,
            "nodes": nodes,
            "latest_review": (
                dict(self.latest_review) if self.latest_review is not None else None
            ),
            "result_capsules": [item.to_dict() for item in self.result_capsules],
            "available_capabilities": capabilities,
            "workspace_manifest": dict(self.workspace_manifest),
            "finalizer_required": self.finalizer_required,
        }


@dataclass(frozen=True)
class ContractReviewRequest:
    run_id: str
    request: str
    request_digest: str
    graph_revision: int
    obligations: tuple[Mapping[str, Any], ...]
    nodes: tuple[Mapping[str, Any], ...]
    result_capsules: tuple[ResultCapsule, ...]
    workspace_manifest: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "request": self.request,
            "request_digest": self.request_digest,
            "graph_revision": self.graph_revision,
            "obligations": [dict(item) for item in self.obligations],
            "result_capsules": [item.to_dict() for item in self.result_capsules],
            "workspace_manifest": dict(self.workspace_manifest),
        }


class ContractGraphSupervisor(Protocol):
    provider_name: str
    model_name: str

    def plan_contract_graph(self, request: ContractPlanRequest) -> ContractGraphPatch: ...

    def review_contract_graph(
        self,
        request: ContractReviewRequest,
    ) -> ContractGraphReview: ...


__all__ = [
    "ContractAssertion",
    "ContractAssertionKind",
    "ContractExecutionBatch",
    "ContractSourceRef",
    "ContractGraphNode",
    "ContractGraphPatch",
    "ContractGraphReview",
    "ContractGraphSupervisor",
    "ContractObligation",
    "ContractPlanRequest",
    "ContractReviewRequest",
    "ObligationVerdict",
    "ObligationVerdictStatus",
    "ObligationPhase",
    "OBLIGATION_SCHEMA_VERSION_V2",
    "ResultCapsule",
    "GRAPH_NODE_SCHEMA_VERSION_V2",
    "GRAPH_PATCH_SCHEMA_VERSION_V2",
    "validate_contract_assertion_coverage",
    "validate_content_mutation_dependencies",
]
