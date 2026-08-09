"""Deterministic postcondition validation for Long-Horizon tasks."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping

from rwkv_lh.harness import ActionHarness, ActionResult
from rwkv_lh.schema import GoalState, RunState, TaskNode, ValidationResult, ValidationSpec


@dataclass(frozen=True)
class ValidationSummary:
    passed: bool
    required_passed: bool
    results: tuple[ValidationResult, ...]


class ValidationEngine:
    supported_kinds = {
        "action_succeeded",
        "file_exists",
        "file_absent",
        "file_contains",
        "file_not_contains",
        "file_content",
        "json_field_equals",
        "json_schema",
        "command_exit_code",
        "hash_changed",
        "hash_equals",
        "http_status",
        "response_field",
        "evidence_bound",
        "memory_ref_exists",
        "model_cross_check",
    }

    def __init__(
        self,
        harness: ActionHarness | None = None,
        *,
        model_cross_check: Callable[[TaskNode, ActionResult, ValidationSpec], ValidationResult] | None = None,
    ):
        self.harness = harness or ActionHarness()
        self.model_cross_check = model_cross_check

    def validate(
        self,
        task: TaskNode,
        action_result: ActionResult,
        goal: GoalState,
        state: RunState | None = None,
        cross_check: Callable[[TaskNode, ActionResult, ValidationSpec], ValidationResult] | None = None,
    ) -> ValidationSummary:
        specs = list(task.completion_criteria)
        if not specs:
            results = (
                ValidationResult(
                    kind="action_succeeded",
                    passed=action_result.success,
                    required=True,
                    message="action reported success" if action_result.success else "action failed",
                    evidence={"error": action_result.error},
                ),
            )
            return ValidationSummary(action_result.success, action_result.success, results)
        results = tuple(
            self._validate_spec(spec, task, action_result, goal, state, cross_check)
            for spec in specs
        )
        required_passed = all(result.passed for result in results if result.required)
        return ValidationSummary(
            passed=required_passed and all(result.passed or not result.required for result in results),
            required_passed=required_passed,
            results=results,
        )

    def _validate_spec(
        self,
        spec: ValidationSpec,
        task: TaskNode,
        action_result: ActionResult,
        goal: GoalState,
        state: RunState | None,
        cross_check: Callable[[TaskNode, ActionResult, ValidationSpec], ValidationResult] | None,
    ) -> ValidationResult:
        kind = str(spec.kind or "").strip()
        try:
            if kind == "model_cross_check" and cross_check is not None:
                return cross_check(task, action_result, spec)
            passed, message, evidence = self._run(kind, spec.parameters, action_result, goal, state)
            return ValidationResult(kind, passed, spec.required, message, evidence)
        except Exception as exc:
            return ValidationResult(
                kind,
                False,
                spec.required,
                f"{type(exc).__name__}: {exc}",
                {},
            )

    def _run(
        self,
        kind: str,
        parameters: Mapping[str, Any],
        action_result: ActionResult,
        goal: GoalState,
        state: RunState | None,
    ) -> tuple[bool, str, dict[str, Any]]:
        if kind == "action_succeeded":
            return action_result.success, "action success flag", {"error": action_result.error}
        if kind in {"file_exists", "file_absent"}:
            path = self.harness.resolve_path(goal, parameters.get("path", ""))
            exists = path.exists()
            expected = kind == "file_exists"
            return exists == expected, f"path exists={exists}", {"path": str(path)}
        if kind in {"file_contains", "file_not_contains"}:
            path = self.harness.resolve_path(goal, parameters.get("path", ""), must_exist=True)
            needle = str(parameters.get("text") or parameters.get("value") or "")
            content = path.read_text(encoding="utf-8")
            present = needle in content
            expected = kind == "file_contains"
            return present == expected, f"text present={present}", {"path": str(path), "text": needle}
        if kind == "file_content":
            path = self.harness.resolve_path(goal, parameters.get("path", ""), must_exist=True)
            content = path.read_text(encoding="utf-8")
            expected = str(parameters.get("expected_content") or parameters.get("expected") or "")
            exact = bool(parameters.get("exact_match", True))
            passed = content == expected if exact else expected in content
            return passed, f"content_match={passed}", {"path": str(path), "expected": expected, "exact_match": exact}
        if kind in {"hash_equals", "hash_changed"}:
            path = self.harness.resolve_path(goal, parameters.get("path", ""), must_exist=True)
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            expected = str(parameters.get("sha256") or parameters.get("before_sha256") or "")
            passed = actual == expected if kind == "hash_equals" else actual != expected
            return passed, f"sha256={actual}", {"path": str(path), "actual": actual, "expected": expected}
        if kind == "json_field_equals":
            path = self.harness.resolve_path(goal, parameters.get("path", ""), must_exist=True)
            value: Any = json.loads(path.read_text(encoding="utf-8"))
            field_path = parameters.get("field") or parameters.get("field_path") or []
            parts = field_path if isinstance(field_path, list) else str(field_path).split(".")
            for part in parts:
                value = value[int(part)] if isinstance(value, list) else value[str(part)]
            expected = parameters.get("expected")
            return value == expected, f"field value={value!r}", {"path": str(path), "actual": value, "expected": expected}
        if kind == "json_schema":
            path = self.harness.resolve_path(goal, parameters.get("path", ""), must_exist=True)
            value = json.loads(path.read_text(encoding="utf-8"))
            expected_type = str(parameters.get("type") or "object")
            type_map = {"object": dict, "array": list, "string": str, "number": (int, float), "boolean": bool}
            passed = isinstance(value, type_map.get(expected_type, object))
            missing = [key for key in parameters.get("required", []) if not isinstance(value, dict) or key not in value]
            return passed and not missing, f"type={type(value).__name__}, missing={missing}", {"missing": missing}
        if kind == "command_exit_code":
            expected = int(parameters.get("expected", 0))
            return action_result.exit_code == expected, f"exit_code={action_result.exit_code}", {"expected": expected}
        if kind == "evidence_bound":
            evidence = action_result.evidence
            valid = [
                item
                for item in evidence
                if item.get("source") or item.get("url") or item.get("locator") or item.get("span")
            ]
            return bool(valid), f"bound evidence count={len(valid)}", {"evidence": valid[:20]}
        if kind == "response_field":
            value: Any = action_result.metadata.get("response", {})
            field_path = parameters.get("field") or ""
            for part in str(field_path).split("."):
                value = value[int(part)] if isinstance(value, list) else value[str(part)]
            expected = parameters.get("expected")
            return value == expected, f"response field={value!r}", {"actual": value, "expected": expected}
        if kind == "http_status":
            actual = action_result.metadata.get("status_code")
            expected = int(parameters.get("expected", 200))
            return actual == expected, f"status_code={actual}", {"expected": expected}
        if kind == "memory_ref_exists":
            memory_id = str(parameters.get("memory_id") or "")
            passed = state is not None and memory_id in state.memory_index
            return passed, f"memory_ref_exists={passed}", {"memory_id": memory_id}
        if kind == "model_cross_check":
            if self.model_cross_check is None:
                return False, "model cross-check adapter is unavailable", {}
            result = self.model_cross_check(task, action_result, ValidationSpec(kind, dict(parameters), True))
            return result.passed, result.message, result.evidence
        raise ValueError(f"unsupported validation kind: {kind}")


__all__ = ["ValidationEngine", "ValidationSummary"]
