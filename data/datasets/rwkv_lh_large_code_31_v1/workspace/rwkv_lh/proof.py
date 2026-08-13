"""Bounded deterministic evaluation for RWKV-proposed Goal criterion proofs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.harness import ActionHarness, HarnessError
from rwkv_lh.schema import (
    Attempt,
    CriterionClaim,
    CriterionClaimStatus,
    EvidenceRef,
    ProofExpr,
    RunState,
    TaskNode,
)


class ProofEvaluationError(ValueError):
    """A claim is malformed, out of scope, self-referential, or unequal."""


READ_OPERATOR_ARGUMENTS: dict[str, tuple[str, ...]] = {
    "workspace_text": ("path",),
    "workspace_json": ("path",),
    "workspace_json_pointer": ("path", "pointer"),
    "workspace_sha256": ("path",),
    "workspace_directory_file_set": ("path", "recursive"),
    "workspace_path_exists": ("path", "path_type"),
    "action_output_text": (),
    "action_output_json": (),
    "action_result_json_pointer": ("pointer",),
    "dependency_artifact_text": ("task_id", "artifact_id"),
    "dependency_artifact_json": ("task_id", "artifact_id"),
    "dependency_artifact_json_pointer": (
        "task_id",
        "artifact_id",
        "pointer",
    ),
    "dependency_artifact_sha256": ("task_id", "artifact_id"),
    "dependency_memory_text": ("task_id", "memory_id"),
    "dependency_memory_json": ("task_id", "memory_id"),
    "dependency_memory_json_pointer": ("task_id", "memory_id", "pointer"),
    "dependency_memory_sha256": ("task_id", "memory_id"),
    "goal_literal": ("goal_quote", "value"),
}

ACTUAL_READ_OPERATORS = frozenset(
    name for name in READ_OPERATOR_ARGUMENTS if name != "goal_literal"
)
EXPECTED_READ_OPERATORS = frozenset(
    name
    for name in READ_OPERATOR_ARGUMENTS
    if name == "goal_literal" or name.startswith("dependency_")
)


@dataclass
class _Resolved:
    value: Any
    refs: list[EvidenceRef]


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def value_sha256(value: Any) -> str:
    typed = {"python_type": type(value).__name__, "value": value}
    return hashlib.sha256(_canonical(typed)).hexdigest()


def _typed_equal(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, Mapping):
        return set(left) == set(right) and all(
            _typed_equal(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _typed_equal(a, b) for a, b in zip(left, right, strict=True)
        )
    return bool(left == right)


def _json_pointer(value: Any, pointer: str) -> Any:
    raw = str(pointer or "")
    if raw == "":
        return value
    if not raw.startswith("/"):
        raise ProofEvaluationError("json_pointer must be empty or start with '/'")
    current = value
    for token in raw[1:].split("/"):
        part = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            if not part.isdigit():
                raise ProofEvaluationError("json_pointer list token must be an index")
            index = int(part)
            if index >= len(current):
                raise ProofEvaluationError("json_pointer index is out of range")
            current = current[index]
        elif isinstance(current, Mapping):
            if part not in current:
                raise ProofEvaluationError(f"json_pointer key is missing: {part}")
            current = current[part]
        else:
            raise ProofEvaluationError("json_pointer traverses a scalar")
    return current


class CriterionProofEngine:
    _OPS = {
        "ref",
        "literal",
        "count",
        "sum",
        "group_sum",
        "object",
        "object_set",
        "sort",
        "sha256",
    }

    def __init__(
        self,
        harness: ActionHarness | None = None,
        *,
        artifact_resolver: Callable[[str], Path] | None = None,
        max_depth: int = 8,
        max_nodes: int = 64,
        max_claim_chars: int = 20_000,
        max_value_bytes: int = 2_000_000,
    ):
        self.harness = harness or ActionHarness()
        self.artifact_resolver = artifact_resolver
        self.max_depth = max(1, int(max_depth))
        self.max_nodes = max(1, int(max_nodes))
        self.max_claim_chars = max(1000, int(max_claim_chars))
        self.max_value_bytes = max(1000, int(max_value_bytes))
        self._nodes = 0
        self._ref_counts: dict[str, int] = {}

    def resolve_operator_value(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        operator_value: Mapping[str, Any],
        *,
        side: str,
        claim_id: str,
    ) -> tuple[Any, list[EvidenceRef], dict[str, Any], list[dict[str, Any]]]:
        """Resolve one already-scoped operator value without comparing it.

        The witness catalog uses the exact same normalizer and resolver as final
        proof evaluation. This method does not select an operator or inspect a
        criterion; it only exposes the deterministic result of the supplied
        operator value.
        """

        if side not in {"actual", "expected"}:
            raise ProofEvaluationError("operator side must be actual or expected")
        expression, trace = self._normalize_operator_value(
            operator_value,
            side=side,
        )
        self._nodes = 0
        self._ref_counts = {}
        resolved = self._evaluate(
            expression,
            state,
            task,
            attempt,
            side=side,
            claim_id=claim_id,
            depth=0,
        )
        return resolved.value, resolved.refs, expression, trace

    def evaluate_claim(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        raw_claim: Mapping[str, Any],
        *,
        claim_id: str,
        rwkv_reason: str,
    ) -> CriterionClaim:
        raw = dict(raw_claim)
        criterion_id = str(raw.get("criterion_id") or "")
        subject_task_id = str(raw.get("subject_task_id") or "")
        producer_task_id = str(raw.get("producer_task_id") or "")
        comparison = str(raw.get("comparison") or "")
        actual_raw = raw.get("actual") if isinstance(raw.get("actual"), Mapping) else {}
        expected_raw = (
            raw.get("expected") if isinstance(raw.get("expected"), Mapping) else {}
        )
        claim = CriterionClaim(
            claim_id=claim_id,
            criterion_id=criterion_id,
            subject_task_id=subject_task_id,
            producer_task_id=producer_task_id,
            attempt_id=attempt.attempt_id,
            comparison=comparison,
            actual=ProofExpr.from_dict(actual_raw),
            expected=ProofExpr.from_dict(expected_raw),
            status=CriterionClaimStatus.REJECTED,
            passed=False,
            rwkv_reason=rwkv_reason,
            raw_claim=raw,
        )
        try:
            if len(_canonical(raw)) > self.max_claim_chars:
                raise ProofEvaluationError("claim exceeds the bounded input size")
            if criterion_id not in task.satisfies_criteria:
                raise ProofEvaluationError("claim criterion is not declared by this task")
            allowed_tasks = {task.task_id, *task.dependencies}
            if task.subject_task_id:
                allowed_tasks.add(task.subject_task_id)
            if subject_task_id not in allowed_tasks or subject_task_id not in state.tasks:
                raise ProofEvaluationError("claim subject_task_id is outside task scope")
            if producer_task_id not in allowed_tasks or producer_task_id not in state.tasks:
                raise ProofEvaluationError("claim producer_task_id is outside task scope")
            if comparison != "exact_equals":
                raise ProofEvaluationError("only exact_equals comparison is supported")

            self._nodes = 0
            self._ref_counts = {}
            actual = self._evaluate(
                actual_raw,
                state,
                task,
                attempt,
                side="actual",
                claim_id=claim_id,
                depth=0,
            )
            expected = self._evaluate(
                expected_raw,
                state,
                task,
                attempt,
                side="expected",
                claim_id=claim_id,
                depth=0,
            )
            if not actual.refs:
                raise ProofEvaluationError("actual proof has no observable provenance")
            if not expected.refs:
                raise ProofEvaluationError("expected proof has no independent provenance")
            actual_signatures = {
                self._ref_signature(item) for item in actual.refs
            }
            expected_signatures = {
                self._ref_signature(item) for item in expected.refs
            }
            overlap = sorted(actual_signatures & expected_signatures)
            if overlap:
                raise ProofEvaluationError(
                    f"actual and expected share the same evidence source: {overlap}"
                )
            target_overlap = self._model_written_target_overlap(
                state,
                task,
                attempt,
                actual.refs,
                expected.refs,
            )
            if target_overlap:
                raise ProofEvaluationError(
                    "actual and expected share model-written workspace target "
                    f"lineage: {target_overlap}"
                )
            if not _typed_equal(actual.value, expected.value):
                raise ProofEvaluationError("exact typed proof values are unequal")

            claim.status = CriterionClaimStatus.VERIFIED
            claim.passed = True
            claim.reason = "RWKV semantic pass and independent exact proof passed"
            claim.proof_refs = [*actual.refs, *expected.refs]
            claim.actual_value_sha256 = value_sha256(actual.value)
            claim.expected_value_sha256 = value_sha256(expected.value)
            claim.observation_digest = hashlib.sha256(
                _canonical(
                    {
                        "goal_digest": state.goal.digest,
                        "claim": raw,
                        "actual_value_sha256": claim.actual_value_sha256,
                        "expected_value_sha256": claim.expected_value_sha256,
                        "proof_refs": [
                            {
                                "source_type": item.source_type,
                                "source_id": item.source_id,
                                "path": item.path,
                                "selector": item.selector,
                                "source_sha256": item.source_sha256,
                                "value_sha256": item.value_sha256,
                            }
                            for item in claim.proof_refs
                        ],
                    }
                )
            ).hexdigest()
        except (ProofEvaluationError, HarnessError, OSError, ValueError, TypeError) as exc:
            claim.reason = f"{type(exc).__name__}: {exc}"
        return claim

    def evaluate_linear_assertion(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        raw_assertion: Mapping[str, Any],
        *,
        claim_id: str,
        rwkv_reason: str,
    ) -> CriterionClaim:
        raw = dict(raw_assertion)
        try:
            normalized, trace = self.normalize_linear_assertion(raw)
        except (ProofEvaluationError, TypeError, ValueError) as exc:
            actual = raw.get("actual") if isinstance(raw.get("actual"), Mapping) else {}
            expected = (
                raw.get("expected")
                if isinstance(raw.get("expected"), Mapping)
                else {}
            )
            return CriterionClaim(
                claim_id=claim_id,
                criterion_id=str(raw.get("criterion_id") or ""),
                subject_task_id=str(raw.get("subject_task_id") or ""),
                producer_task_id=str(raw.get("producer_task_id") or ""),
                attempt_id=attempt.attempt_id,
                comparison=str(raw.get("comparison") or ""),
                actual=ProofExpr.from_dict(actual),
                expected=ProofExpr.from_dict(expected),
                status=CriterionClaimStatus.REJECTED,
                passed=False,
                reason=f"{type(exc).__name__}: {exc}",
                rwkv_reason=rwkv_reason,
                raw_claim=raw,
                claim_protocol="linear_typed_assertion.v1",
            )
        claim = self.evaluate_claim(
            state,
            task,
            attempt,
            normalized,
            claim_id=claim_id,
            rwkv_reason=rwkv_reason,
        )
        claim.raw_claim = raw
        claim.claim_protocol = "linear_typed_assertion.v1"
        claim.normalization_trace = trace
        return claim

    def evaluate_operator_assertion(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        raw_assertion: Mapping[str, Any],
        *,
        claim_id: str,
        rwkv_reason: str,
    ) -> CriterionClaim:
        raw = dict(raw_assertion)
        try:
            normalized, trace = self.normalize_operator_assertion(raw)
        except (ProofEvaluationError, TypeError, ValueError) as exc:
            actual = raw.get("actual") if isinstance(raw.get("actual"), Mapping) else {}
            expected = (
                raw.get("expected")
                if isinstance(raw.get("expected"), Mapping)
                else {}
            )
            return CriterionClaim(
                claim_id=claim_id,
                criterion_id=str(raw.get("criterion_id") or ""),
                subject_task_id=str(raw.get("subject_task_id") or ""),
                producer_task_id=str(raw.get("producer_task_id") or ""),
                attempt_id=attempt.attempt_id,
                comparison=str(raw.get("comparison") or ""),
                actual=ProofExpr.from_dict(actual),
                expected=ProofExpr.from_dict(expected),
                status=CriterionClaimStatus.REJECTED,
                passed=False,
                reason=f"{type(exc).__name__}: {exc}",
                rwkv_reason=rwkv_reason,
                raw_claim=raw,
                claim_protocol="read_operator_assertion.v1",
            )
        claim = self.evaluate_claim(
            state,
            task,
            attempt,
            normalized,
            claim_id=claim_id,
            rwkv_reason=rwkv_reason,
        )
        claim.raw_claim = raw
        claim.claim_protocol = "read_operator_assertion.v1"
        claim.normalization_trace = trace
        return claim

    @classmethod
    def normalize_operator_assertion(
        cls,
        raw_assertion: Mapping[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        allowed_claim_fields = {
            "criterion_id",
            "subject_task_id",
            "producer_task_id",
            "comparison",
            "actual",
            "expected",
        }
        extra = sorted(set(raw_assertion) - allowed_claim_fields)
        if extra:
            raise ProofEvaluationError(
                f"operator assertion has unsupported fields: {extra}"
            )
        normalized: dict[str, Any] = {
            "criterion_id": str(raw_assertion.get("criterion_id") or ""),
            "subject_task_id": str(raw_assertion.get("subject_task_id") or ""),
            "producer_task_id": str(raw_assertion.get("producer_task_id") or ""),
            "comparison": str(raw_assertion.get("comparison") or ""),
        }
        trace: list[dict[str, Any]] = []
        for side in ("actual", "expected"):
            value = raw_assertion.get(side)
            if not isinstance(value, Mapping):
                raise ProofEvaluationError(
                    f"operator assertion {side} must be an object"
                )
            expression, value_trace = cls._normalize_operator_value(
                value,
                side=side,
            )
            normalized[side] = expression
            trace.extend(value_trace)
        return normalized, trace

    @classmethod
    def _normalize_operator_value(
        cls,
        value: Mapping[str, Any],
        *,
        side: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        extra = sorted(set(value) - {"read_op", "arguments", "transforms"})
        if extra:
            raise ProofEvaluationError(
                f"operator {side} value has unsupported fields: {extra}"
            )
        read_op = str(value.get("read_op") or "")
        allowed = ACTUAL_READ_OPERATORS if side == "actual" else EXPECTED_READ_OPERATORS
        if read_op not in allowed:
            raise ProofEvaluationError(
                f"unsupported {side} read operator: {read_op}"
            )
        arguments = value.get("arguments")
        if not isinstance(arguments, Mapping):
            raise ProofEvaluationError(
                f"operator {side} arguments must be an object"
            )
        required = set(READ_OPERATOR_ARGUMENTS[read_op])
        missing = sorted(name for name in required if name not in arguments)
        argument_extra = sorted(set(arguments) - required)
        if missing or argument_extra:
            raise ProofEvaluationError(
                f"operator {read_op} argument mismatch: "
                f"missing={missing}, extra={argument_extra}"
            )

        if read_op == "goal_literal":
            expression: dict[str, Any] = {
                "op": "literal",
                "goal_quote": str(arguments.get("goal_quote") or ""),
                "value": arguments.get("value"),
            }
        else:
            source, selector_kind = cls._operator_source_selector(read_op)
            expression = {
                "op": "ref",
                "source": source,
                "selector": {"kind": selector_kind},
            }
            for name in ("path", "task_id", "artifact_id", "memory_id"):
                if name in arguments:
                    raw_value = arguments[name]
                    if not isinstance(raw_value, str) or not raw_value:
                        raise ProofEvaluationError(
                            f"operator {read_op} {name} must be a non-empty string"
                        )
                    expression[name] = raw_value
            if "pointer" in arguments:
                pointer = arguments["pointer"]
                if not isinstance(pointer, str):
                    raise ProofEvaluationError(
                        f"operator {read_op} pointer must be a string"
                    )
                expression["selector"]["pointer"] = pointer
            if "recursive" in arguments:
                recursive = arguments["recursive"]
                if type(recursive) is not bool:
                    raise ProofEvaluationError(
                        f"operator {read_op} recursive must be boolean"
                    )
                expression["selector"]["recursive"] = recursive
            if "path_type" in arguments:
                path_type = arguments["path_type"]
                if path_type not in {"any", "file", "directory"}:
                    raise ProofEvaluationError(
                        f"operator {read_op} path_type must be any, file, or directory"
                    )
                expression["selector"]["path_type"] = path_type

        trace = [
            {
                "side": side,
                "operation": "read_operator_to_expression",
                "read_op": read_op,
            }
        ]
        transforms = value.get("transforms")
        if not isinstance(transforms, list):
            raise ProofEvaluationError("operator transforms must be an array")
        for index, transform in enumerate(transforms, start=1):
            if not isinstance(transform, Mapping):
                raise ProofEvaluationError("operator transform must be an object")
            transform_op = str(transform.get("transform_op") or "")
            allowed_fields = {
                "count": {"transform_op"},
                "sum": {"transform_op"},
                "object_set": {"transform_op"},
                "sort": {"transform_op"},
                "sha256": {"transform_op"},
                "group_sum": {
                    "transform_op",
                    "group_pointer",
                    "value_pointer",
                },
            }
            if transform_op not in allowed_fields:
                raise ProofEvaluationError(
                    f"unsupported operator transform: {transform_op}"
                )
            transform_extra = sorted(set(transform) - allowed_fields[transform_op])
            transform_missing = sorted(
                allowed_fields[transform_op] - set(transform)
            )
            if transform_extra or transform_missing:
                raise ProofEvaluationError(
                    f"operator transform {transform_op} field mismatch: "
                    f"missing={transform_missing}, extra={transform_extra}"
                )
            wrapped = {"op": transform_op, "arg": expression}
            for name in ("group_pointer", "value_pointer"):
                if name in transform:
                    pointer = transform[name]
                    if not isinstance(pointer, str):
                        raise ProofEvaluationError(
                            f"operator transform {name} must be a string"
                        )
                    wrapped[name] = pointer
            expression = wrapped
            trace.append(
                {
                    "side": side,
                    "operation": "wrap_transform",
                    "index": index,
                    "op": transform_op,
                }
            )
        return expression, trace

    @staticmethod
    def _operator_source_selector(read_op: str) -> tuple[str, str]:
        if read_op.startswith("workspace_"):
            source = "workspace"
            suffix = read_op.removeprefix("workspace_")
        elif read_op.startswith("action_"):
            source = "action_result"
            suffix = read_op.removeprefix("action_")
        elif read_op.startswith("dependency_artifact_"):
            source = "dependency_artifact"
            suffix = read_op.removeprefix("dependency_artifact_")
        elif read_op.startswith("dependency_memory_"):
            source = "dependency_memory"
            suffix = read_op.removeprefix("dependency_memory_")
        else:
            raise ProofEvaluationError(f"unsupported read operator: {read_op}")
        selector = {
            "output_text": "output_text",
            "output_json": "output_json",
            "result_json_pointer": "json_pointer",
            "directory_file_set": "directory_file_set",
            "path_exists": "path_exists",
            "json_pointer": "json_pointer",
            "text": "text",
            "json": "json",
            "sha256": "sha256",
        }.get(suffix)
        if selector is None:
            raise ProofEvaluationError(f"unsupported read operator: {read_op}")
        return source, selector

    @classmethod
    def normalize_linear_assertion(
        cls,
        raw_assertion: Mapping[str, Any],
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        allowed_claim_fields = {
            "criterion_id",
            "subject_task_id",
            "producer_task_id",
            "comparison",
            "actual",
            "expected",
        }
        extra = sorted(set(raw_assertion) - allowed_claim_fields)
        if extra:
            raise ProofEvaluationError(
                f"linear assertion has unsupported fields: {extra}"
            )
        trace: list[dict[str, Any]] = []
        normalized: dict[str, Any] = {
            "criterion_id": str(raw_assertion.get("criterion_id") or ""),
            "subject_task_id": str(raw_assertion.get("subject_task_id") or ""),
            "producer_task_id": str(raw_assertion.get("producer_task_id") or ""),
            "comparison": str(raw_assertion.get("comparison") or ""),
        }
        for side in ("actual", "expected"):
            value = raw_assertion.get(side)
            if not isinstance(value, Mapping):
                raise ProofEvaluationError(
                    f"linear assertion {side} must be an object"
                )
            expression, side_trace = cls._normalize_linear_value(value, side=side)
            normalized[side] = expression
            trace.extend(side_trace)
        return normalized, trace

    @classmethod
    def _normalize_linear_value(
        cls,
        value: Mapping[str, Any],
        *,
        side: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        allowed_fields = {
            "source",
            "path",
            "task_id",
            "artifact_id",
            "memory_id",
            "selector",
            "goal_quote",
            "value",
            "transforms",
        }
        extra = sorted(set(value) - allowed_fields)
        if extra:
            raise ProofEvaluationError(
                f"linear {side} value has unsupported fields: {extra}"
            )
        source = str(value.get("source") or "")
        trace: list[dict[str, Any]] = []
        if source == "goal_literal":
            if side != "expected":
                raise ProofEvaluationError("goal_literal is forbidden on actual")
            allowed_for_source = {"source", "goal_quote", "value", "transforms"}
            source_extra = sorted(set(value) - allowed_for_source)
            if source_extra:
                raise ProofEvaluationError(
                    f"linear {side} goal_literal has incompatible fields: "
                    f"{source_extra}"
                )
            if "value" not in value:
                raise ProofEvaluationError("goal_literal requires a typed value")
            expression: dict[str, Any] = {
                "op": "literal",
                "goal_quote": str(value.get("goal_quote") or ""),
                "value": value.get("value"),
            }
            trace.append(
                {
                    "side": side,
                    "operation": "source_to_literal",
                    "source": source,
                }
            )
        elif source in {
            "workspace",
            "action_result",
            "dependency_artifact",
            "dependency_memory",
        }:
            source_fields = {
                "workspace": {"source", "path", "selector", "transforms"},
                "action_result": {"source", "selector", "transforms"},
                "dependency_artifact": {
                    "source",
                    "task_id",
                    "artifact_id",
                    "selector",
                    "transforms",
                },
                "dependency_memory": {
                    "source",
                    "task_id",
                    "memory_id",
                    "selector",
                    "transforms",
                },
            }
            source_extra = sorted(set(value) - source_fields[source])
            if source_extra:
                raise ProofEvaluationError(
                    f"linear {side} {source} has incompatible fields: "
                    f"{source_extra}"
                )
            required_fields = {
                "workspace": ("path",),
                "action_result": (),
                "dependency_artifact": ("task_id", "artifact_id"),
                "dependency_memory": ("task_id", "memory_id"),
            }
            missing = [
                name
                for name in required_fields[source]
                if not str(value.get(name) or "")
            ]
            if missing:
                raise ProofEvaluationError(
                    f"linear {side} {source} is missing required fields: {missing}"
                )
            selector = value.get("selector")
            if not isinstance(selector, Mapping):
                raise ProofEvaluationError(
                    f"linear {side} ref requires selector object"
                )
            expression = {
                "op": "ref",
                "source": source,
                "selector": dict(selector),
            }
            for field_name in ("path", "task_id", "artifact_id", "memory_id"):
                field_value = str(value.get(field_name) or "")
                if field_value:
                    expression[field_name] = field_value
            trace.append(
                {
                    "side": side,
                    "operation": "source_to_ref",
                    "source": source,
                }
            )
        else:
            raise ProofEvaluationError(f"unsupported linear source: {source}")

        transforms = value.get("transforms") or []
        if not isinstance(transforms, list):
            raise ProofEvaluationError("linear transforms must be an array")
        for index, transform in enumerate(transforms, start=1):
            if not isinstance(transform, Mapping):
                raise ProofEvaluationError("linear transform must be an object")
            op = str(transform.get("op") or "")
            allowed_transform_fields = {
                "count": {"op"},
                "sum": {"op"},
                "group_sum": {"op", "group_pointer", "value_pointer"},
                "object_set": {"op"},
                "sort": {"op"},
                "sha256": {"op"},
            }
            if op not in allowed_transform_fields:
                raise ProofEvaluationError(f"unsupported linear transform: {op}")
            transform_extra = sorted(
                set(transform) - allowed_transform_fields[op]
            )
            if transform_extra:
                raise ProofEvaluationError(
                    f"linear transform has unsupported fields: {transform_extra}"
                )
            wrapped = {"op": op, "arg": expression}
            for field_name in ("group_pointer", "value_pointer"):
                if field_name in transform:
                    wrapped[field_name] = transform[field_name]
            expression = wrapped
            trace.append(
                {
                    "side": side,
                    "operation": "wrap_transform",
                    "index": index,
                    "op": op,
                }
            )
        return expression, trace

    def _evaluate(
        self,
        expression: Mapping[str, Any],
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        *,
        side: str,
        claim_id: str,
        depth: int,
    ) -> _Resolved:
        if depth > self.max_depth:
            raise ProofEvaluationError("proof expression depth limit exceeded")
        self._nodes += 1
        if self._nodes > self.max_nodes:
            raise ProofEvaluationError("proof expression node limit exceeded")
        if not isinstance(expression, Mapping):
            raise ProofEvaluationError("proof expression must be an object")
        op = str(expression.get("op") or "")
        if op not in self._OPS:
            raise ProofEvaluationError(f"unsupported proof op: {op}")
        allowed_keys = {
            "literal": {"op", "goal_quote", "value"},
            "ref": {
                "op",
                "source",
                "path",
                "task_id",
                "artifact_id",
                "memory_id",
                "selector",
            },
            "object": {"op", "entries"},
            "count": {"op", "arg"},
            "sum": {"op", "arg"},
            "group_sum": {"op", "arg", "group_pointer", "value_pointer"},
            "object_set": {"op", "arg"},
            "sort": {"op", "arg"},
            "sha256": {"op", "arg"},
        }[op]
        extra_keys = sorted(set(expression) - allowed_keys)
        if extra_keys:
            raise ProofEvaluationError(
                f"proof expression has unsupported fields: {extra_keys}"
            )
        if op == "literal":
            if side != "expected":
                raise ProofEvaluationError("literal is forbidden on the actual side")
            quote = str(expression.get("goal_quote") or "")
            if not quote or quote not in state.goal.original_request:
                raise ProofEvaluationError(
                    "literal requires an exact non-empty Goal.original_request quote"
                )
            value = expression.get("value")
            self._bounded_value(value)
            source_digest = hashlib.sha256(quote.encode("utf-8")).hexdigest()
            ref = EvidenceRef(
                evidence_ref_id="",
                source_type="goal_literal",
                source_id=state.goal.goal_id,
                selector={"goal_quote": quote},
                source_sha256=source_digest,
                value_sha256=value_sha256(value),
                metadata={"quote_start": state.goal.original_request.index(quote)},
            )
            return self._with_ids(_Resolved(value, [ref]), claim_id, side)
        if op == "ref":
            return self._resolve_ref(
                expression,
                state,
                task,
                attempt,
                side=side,
                claim_id=claim_id,
            )

        if op == "object":
            entries = expression.get("entries")
            if not isinstance(entries, Mapping) or not entries:
                raise ProofEvaluationError("object requires non-empty entries")
            value: dict[str, Any] = {}
            refs: list[EvidenceRef] = []
            for key in sorted(entries):
                resolved = self._evaluate(
                    entries[key],
                    state,
                    task,
                    attempt,
                    side=side,
                    claim_id=claim_id,
                    depth=depth + 1,
                )
                value[str(key)] = resolved.value
                refs.extend(resolved.refs)
            self._bounded_value(value)
            return _Resolved(value, refs)

        arg_expression = expression.get("arg")
        if not isinstance(arg_expression, Mapping):
            raise ProofEvaluationError(f"{op} requires an arg expression")
        resolved = self._evaluate(
            arg_expression,
            state,
            task,
            attempt,
            side=side,
            claim_id=claim_id,
            depth=depth + 1,
        )
        value = resolved.value
        if op == "count":
            if not isinstance(value, (str, list, dict)):
                raise ProofEvaluationError("count input must be string/list/object")
            output: Any = len(value)
        elif op == "sum":
            if not isinstance(value, list) or not all(
                type(item) in {int, float} for item in value
            ):
                raise ProofEvaluationError("sum input must be a numeric array")
            output = sum(value)
        elif op == "group_sum":
            if not isinstance(value, list) or not all(
                isinstance(item, Mapping) for item in value
            ):
                raise ProofEvaluationError("group_sum input must be an object array")
            group_pointer = str(expression.get("group_pointer") or "")
            value_pointer = str(expression.get("value_pointer") or "")
            grouped: dict[str, int | float] = {}
            for item in value:
                group = _json_pointer(item, group_pointer)
                number = _json_pointer(item, value_pointer)
                if not isinstance(group, str) or type(number) not in {int, float}:
                    raise ProofEvaluationError(
                        "group_sum group must be string and value numeric"
                    )
                grouped[group] = grouped.get(group, 0) + number
            output = grouped
        elif op == "object_set":
            if not isinstance(value, list):
                raise ProofEvaluationError("object_set input must be an array")
            canonical_items = {_canonical(item): item for item in value}
            output = [canonical_items[key] for key in sorted(canonical_items)]
        elif op == "sort":
            if not isinstance(value, list):
                raise ProofEvaluationError("sort input must be an array")
            output = sorted(value, key=_canonical)
        elif op == "sha256":
            raw = value.encode("utf-8") if isinstance(value, str) else _canonical(value)
            output = hashlib.sha256(raw).hexdigest()
        else:
            raise ProofEvaluationError(f"unhandled proof op: {op}")
        self._bounded_value(output)
        return _Resolved(output, resolved.refs)

    def _resolve_ref(
        self,
        expression: Mapping[str, Any],
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        *,
        side: str,
        claim_id: str,
    ) -> _Resolved:
        source = str(expression.get("source") or "")
        selector = expression.get("selector") or {"kind": "text"}
        if not isinstance(selector, Mapping):
            raise ProofEvaluationError("ref selector must be an object")
        selector_dict = dict(selector)
        selector_extra = sorted(
            set(selector_dict) - {"kind", "pointer", "recursive", "path_type"}
        )
        if selector_extra:
            raise ProofEvaluationError(
                f"proof selector has unsupported fields: {selector_extra}"
            )
        path = ""
        source_id = ""
        source_bytes = b""
        base_value: Any
        source_type = source

        if source == "workspace":
            if side == "expected":
                raise ProofEvaluationError(
                    "expected proof cannot reference mutable workspace state"
                )
            path = str(expression.get("path") or "")
            selector_kind = str(selector_dict.get("kind") or "text")
            resolved_path = self.harness.resolve_path(
                state.goal,
                path,
                must_exist=selector_kind != "path_exists",
            )
            source_id = path
            base_value, source_bytes = self._read_path(resolved_path, selector_dict)
        elif source == "action_result":
            if side == "expected":
                raise ProofEvaluationError(
                    "expected proof cannot reference the current action result"
                )
            source_id = attempt.attempt_id
            raw_result = attempt.tool_result or {}
            source_bytes = _canonical(raw_result)
            base_value = self._select_value(raw_result, selector_dict)
        elif source in {"dependency_artifact", "dependency_memory"}:
            dependency_task_id = str(expression.get("task_id") or "")
            if dependency_task_id not in task.dependencies:
                raise ProofEvaluationError("proof ref is not a direct dependency")
            if source == "dependency_artifact":
                artifact_id = str(expression.get("artifact_id") or "")
                artifact = state.artifacts.get(artifact_id)
                if artifact is None or artifact.task_id != dependency_task_id:
                    raise ProofEvaluationError("dependency artifact is missing or misowned")
                if artifact.path.startswith("store:"):
                    if self.artifact_resolver is None:
                        raise ProofEvaluationError(
                            "dependency artifact store resolver is unavailable"
                        )
                    resolved_path = self.artifact_resolver(artifact.path)
                else:
                    resolved_path = self.harness.resolve_path(
                        state.goal,
                        artifact.path,
                        must_exist=True,
                    )
                if not resolved_path.is_file():
                    raise ProofEvaluationError("dependency artifact is not a file")
                current = hashlib.sha256(resolved_path.read_bytes()).hexdigest()
                if current != artifact.sha256:
                    raise ProofEvaluationError("dependency artifact hash changed")
                path = artifact.path
                source_id = artifact_id
                base_value, source_bytes = self._read_path(
                    resolved_path,
                    selector_dict,
                )
            else:
                memory_id = str(expression.get("memory_id") or "")
                memory = state.memory_index.get(memory_id)
                if memory is None or memory.task_id != dependency_task_id:
                    raise ProofEvaluationError("dependency memory is missing or misowned")
                source_id = memory_id
                source_bytes = memory.content.encode("utf-8")
                base_value = self._select_text(memory.content, selector_dict)
        else:
            raise ProofEvaluationError(f"unsupported ref source: {source}")

        self._bounded_value(base_value)
        ref = EvidenceRef(
            evidence_ref_id="",
            source_type=source_type,
            source_id=source_id,
            path=path,
            selector=selector_dict,
            source_sha256=hashlib.sha256(source_bytes).hexdigest(),
            value_sha256=value_sha256(base_value),
        )
        return self._with_ids(_Resolved(base_value, [ref]), claim_id, side)

    def _read_path(
        self,
        path: Path,
        selector: Mapping[str, Any],
    ) -> tuple[Any, bytes]:
        kind = str(selector.get("kind") or "text")
        if kind == "path_exists":
            path_type = str(selector.get("path_type") or "any")
            if path_type not in {"any", "file", "directory"}:
                raise ProofEvaluationError(
                    "path_exists path_type must be any, file, or directory"
                )
            exists = path.exists()
            if path_type == "file":
                exists = path.is_file()
            elif path_type == "directory":
                exists = path.is_dir()
            descriptor = {
                "path": str(path),
                "path_type": path_type,
                "exists": exists,
            }
            return exists, _canonical(descriptor)
        if path.is_dir():
            if kind != "directory_file_set":
                raise ProofEvaluationError(
                    "directory ref requires directory_file_set selector"
                )
            recursive = bool(selector.get("recursive", True))
            candidates = path.rglob("*") if recursive else path.iterdir()
            files: list[str] = []
            for item in sorted(candidates):
                if item.is_symlink():
                    raise ProofEvaluationError("directory proof does not follow symlinks")
                if item.is_file():
                    files.append(item.relative_to(path).as_posix())
            raw = _canonical(files)
            return files, raw
        if not path.is_file():
            raise ProofEvaluationError("workspace ref requires a file or directory")
        raw = path.read_bytes()
        if len(raw) > self.max_value_bytes:
            raise ProofEvaluationError("proof source exceeds byte limit")
        if kind == "sha256":
            return hashlib.sha256(raw).hexdigest(), raw
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ProofEvaluationError("proof source is not UTF-8") from exc
        if kind == "text":
            return text, raw
        if kind == "json":
            return json.loads(text), raw
        if kind == "json_pointer":
            return _json_pointer(json.loads(text), str(selector.get("pointer") or "")), raw
        raise ProofEvaluationError(f"unsupported file selector: {kind}")

    def _select_text(self, text: str, selector: Mapping[str, Any]) -> Any:
        kind = str(selector.get("kind") or "text")
        if kind == "text":
            return text
        if kind == "json":
            return json.loads(text)
        if kind == "json_pointer":
            return _json_pointer(
                json.loads(text),
                str(selector.get("pointer") or ""),
            )
        if kind == "sha256":
            return hashlib.sha256(text.encode("utf-8")).hexdigest()
        raise ProofEvaluationError(f"unsupported memory selector: {kind}")

    @staticmethod
    def _select_value(value: Any, selector: Mapping[str, Any]) -> Any:
        kind = str(selector.get("kind") or "json_pointer")
        if kind == "json_pointer":
            return _json_pointer(value, str(selector.get("pointer") or ""))
        if kind == "output_text":
            return str(value.get("output") or "") if isinstance(value, Mapping) else ""
        if kind == "output_json":
            if not isinstance(value, Mapping):
                raise ProofEvaluationError("action result is not an object")
            return json.loads(str(value.get("output") or ""))
        raise ProofEvaluationError(f"unsupported action-result selector: {kind}")

    def _bounded_value(self, value: Any) -> None:
        try:
            size = len(_canonical(value))
        except (TypeError, ValueError) as exc:
            raise ProofEvaluationError("proof value is not canonical JSON") from exc
        if size > self.max_value_bytes:
            raise ProofEvaluationError("proof value exceeds byte limit")

    def _with_ids(self, resolved: _Resolved, claim_id: str, side: str) -> _Resolved:
        for item in resolved.refs:
            if not item.evidence_ref_id:
                self._ref_counts[side] = self._ref_counts.get(side, 0) + 1
                item.evidence_ref_id = (
                    f"ER-{claim_id}-{side}-{self._ref_counts[side]}"
                )
        return resolved

    @staticmethod
    def _action_target_path(task: TaskNode | None) -> str:
        if task is None:
            return ""
        action_type = str(task.action.action_type or "")
        if action_type not in {
            "write_file",
            "write_json",
            "append_file",
            "copy_file",
        }:
            return ""
        field = "destination" if action_type == "copy_file" else "path"
        return str(task.action.arguments.get(field) or "")

    def _canonical_workspace_target(self, state: RunState, path: str) -> str:
        raw = str(path or "")
        if not raw or raw.startswith("store:"):
            return ""
        try:
            return str(
                self.harness.resolve_path(
                    state.goal,
                    raw,
                    must_exist=False,
                )
            )
        except (OSError, ValueError):
            return ""

    def _model_written_target_overlap(
        self,
        state: RunState,
        task: TaskNode,
        attempt: Attempt,
        actual_refs: list[EvidenceRef],
        expected_refs: list[EvidenceRef],
    ) -> list[str]:
        """Return target paths where expected provenance descends from a model mutation.

        Different opaque IDs are not independent when one side is a prior
        artifact/memory emitted by a model-selected write to the same scoped
        target currently being observed. A read-only snapshot remains eligible
        only when no earlier audited model mutation to that same target can be
        established before the snapshot attempt began.
        """

        actual_targets = {
            target
            for ref in actual_refs
            for target in [self._canonical_workspace_target(state, ref.path)]
            if target
        }
        if any(
            ref.source_type == "action_result"
            and ref.source_id == attempt.attempt_id
            for ref in actual_refs
        ):
            action_path = str(task.action.arguments.get("path") or "")
            if task.action.action_type == "copy_file":
                action_path = str(task.action.arguments.get("destination") or "")
            target = self._canonical_workspace_target(state, action_path)
            if target:
                actual_targets.add(target)

        expected_model_written_targets: set[str] = set()
        for ref in expected_refs:
            owner_task_id = ""
            artifact_path = ""
            if ref.source_type == "dependency_artifact":
                artifact = state.artifacts.get(ref.source_id)
                if artifact is None:
                    continue
                owner_task_id = artifact.task_id
                artifact_path = artifact.path
            elif ref.source_type == "dependency_memory":
                memory = state.memory_index.get(ref.source_id)
                if memory is None:
                    continue
                owner_task_id = memory.task_id
            else:
                continue
            owner = state.tasks.get(owner_task_id)
            mutation_path = self._action_target_path(owner)
            mutation_target = self._canonical_workspace_target(
                state, mutation_path
            )
            if mutation_target:
                if artifact_path:
                    artifact_target = self._canonical_workspace_target(
                        state, artifact_path
                    )
                    if artifact_target != mutation_target:
                        continue
                expected_model_written_targets.add(mutation_target)
                continue

            snapshot_path = artifact_path
            if not snapshot_path and owner is not None:
                snapshot_path = str(owner.action.arguments.get("path") or "")
            snapshot_target = self._canonical_workspace_target(
                state, snapshot_path
            )
            if not snapshot_target or snapshot_target not in actual_targets:
                continue
            snapshot_attempt = self._source_attempt(state, ref)
            if snapshot_attempt is None or not snapshot_attempt.started_at:
                continue
            for candidate in state.tasks.values():
                candidate_target = self._canonical_workspace_target(
                    state,
                    self._action_target_path(candidate),
                )
                if candidate_target != snapshot_target:
                    continue
                if self._task_mutation_completed_before(
                    state,
                    candidate,
                    snapshot_attempt.started_at,
                ):
                    expected_model_written_targets.add(snapshot_target)
                    break
        return sorted(actual_targets & expected_model_written_targets)

    @staticmethod
    def _source_attempt(
        state: RunState,
        ref: EvidenceRef,
    ) -> Attempt | None:
        if ref.source_type == "dependency_memory":
            memory_attempt_id = (
                ref.source_id[2:] if ref.source_id.startswith("M-") else ""
            )
            return state.attempts.get(memory_attempt_id)
        if ref.source_type == "dependency_artifact":
            for attempt in state.attempts.values():
                if ref.source_id in attempt.artifact_refs:
                    return attempt
        return None

    @staticmethod
    def _task_mutation_completed_before(
        state: RunState,
        task: TaskNode,
        snapshot_started_at: str,
    ) -> bool:
        for attempt_id in task.attempt_ids:
            attempt = state.attempts.get(attempt_id)
            if attempt is None or not attempt.ended_at:
                continue
            status = getattr(attempt.status, "value", attempt.status)
            if str(status) != "succeeded":
                continue
            if str(attempt.ended_at) <= str(snapshot_started_at):
                return True
        return False

    @staticmethod
    def _ref_signature(ref: EvidenceRef) -> str:
        # A workspace path and a dependency artifact at the same current path
        # are the same observable source for self-reference purposes.
        source = f"path:{ref.path}" if ref.path else f"{ref.source_type}:{ref.source_id}"
        return json.dumps(
            {"source": source, "selector": ref.selector},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )


__all__ = [
    "ACTUAL_READ_OPERATORS",
    "CriterionProofEngine",
    "EXPECTED_READ_OPERATORS",
    "ProofEvaluationError",
    "READ_OPERATOR_ARGUMENTS",
    "value_sha256",
]
