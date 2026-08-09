"""Bounded working-memory projection for one active task."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from rwkv_lh.schema import MemoryEntry, RunState, TaskNode
from rwkv_lh.token_budget import get_token_count, smart_truncate


@dataclass(frozen=True)
class MemoryBudgets:
    total_input: int = 13600
    goal: int = 1200
    task: int = 1600
    dependencies: int = 3000
    evidence: int = 5000
    failure: int = 1200
    action_contract: int = 1600


@dataclass
class ContextBundle:
    goal: str
    task: str
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    failure: str = ""
    action_contract: str = ""
    selected_memory_ids: list[str] = field(default_factory=list)
    excluded_memory_ids: list[str] = field(default_factory=list)
    token_counts: dict[str, int] = field(default_factory=dict)

    @property
    def total_tokens(self) -> int:
        return int(self.token_counts.get("total", 0))

    def to_prompt(self) -> str:
        sections = [self.goal, self.task]
        if self.dependencies:
            sections.append("DEPENDENCY OUTPUTS\n" + "\n\n".join(self.dependencies))
        if self.evidence:
            sections.append("RELEVANT MEMORY / EVIDENCE\n" + "\n\n".join(self.evidence))
        if self.failure:
            sections.append("LAST MATERIAL FAILURE\n" + self.failure)
        if self.action_contract:
            sections.append("ALLOWED ACTION CONTRACT\n" + self.action_contract)
        return "\n\n".join(section for section in sections if section.strip())


class WorkingMemoryBuilder:
    def __init__(self, budgets: MemoryBudgets | None = None):
        self.budgets = budgets or MemoryBudgets()

    def build(
        self,
        state: RunState,
        task: TaskNode,
        *,
        action_contract: str = "",
    ) -> ContextBundle:
        goal = self._bounded(self._goal_text(state), self.budgets.goal)
        task_text = self._bounded(self._task_text(task), self.budgets.task)
        dependency_entries = self._dependency_entries(state, task)
        explicit_refs = self._explicit_memory_refs(task)
        evidence_entries = self._relevant_entries(
            state,
            task,
            excluded_ids={entry.memory_id for entry in dependency_entries},
            explicit_refs=explicit_refs,
        )
        dependencies, dependency_ids = self._pack_entries(
            dependency_entries,
            self.budgets.dependencies,
        )
        evidence, evidence_ids = self._pack_entries(
            evidence_entries,
            self.budgets.evidence,
        )
        failure = self._bounded(self._failure_text(state, task), self.budgets.failure)
        contract = self._bounded(action_contract, self.budgets.action_contract)
        selected = dependency_ids + evidence_ids
        excluded = sorted(set(state.memory_index) - set(selected))
        bundle = ContextBundle(
            goal=goal,
            task=task_text,
            dependencies=dependencies,
            evidence=evidence,
            failure=failure,
            action_contract=contract,
            selected_memory_ids=selected,
            excluded_memory_ids=excluded,
        )
        self._enforce_total_budget(bundle)
        bundle.token_counts = {
            "goal": get_token_count(bundle.goal),
            "task": get_token_count(bundle.task),
            "dependencies": get_token_count("\n\n".join(bundle.dependencies)),
            "evidence": get_token_count("\n\n".join(bundle.evidence)),
            "failure": get_token_count(bundle.failure),
            "action_contract": get_token_count(bundle.action_contract),
            "total": get_token_count(bundle.to_prompt()),
        }
        return bundle

    @staticmethod
    def _goal_text(state: RunState) -> str:
        criteria = [asdict(item) for item in state.goal.success_criteria]
        return (
            "IMMUTABLE GOAL\n"
            + json.dumps(
                {
                    "objective": state.goal.objective,
                    "constraints": list(state.goal.constraints),
                    "success_criteria": criteria,
                    "workspace_root": state.goal.workspace_root,
                    "goal_digest": state.goal.digest,
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    @staticmethod
    def _task_text(task: TaskNode) -> str:
        return (
            "ACTIVE TASK\n"
            + json.dumps(
                {
                    "task_id": task.task_id,
                    "title": task.title,
                    "description": task.description,
                    "dependencies": task.dependencies,
                    "goal_criteria": task.goal_criteria,
                    "inputs": task.inputs,
                    "action": {
                        "type": task.action.action_type,
                        "arguments": task.action.arguments,
                    },
                    "completion_criteria": [asdict(item) for item in task.completion_criteria],
                    "attempt_count": len(task.attempt_ids),
                },
                ensure_ascii=False,
                indent=2,
            )
        )

    @staticmethod
    def _entry_text(entry: MemoryEntry) -> str:
        content = entry.content.strip() or entry.summary.strip()
        return (
            f"[{entry.memory_id}] kind={entry.kind} task={entry.task_id}\n"
            f"summary: {entry.summary.strip()}\n"
            f"content: {content}\n"
            f"artifact_refs: {entry.artifact_refs}\n"
            f"evidence_refs: {entry.evidence_refs}"
        )

    @staticmethod
    def _explicit_memory_refs(task: TaskNode) -> set[str]:
        references: set[str] = set()
        for item in task.inputs:
            raw = str(item.get("ref") or item.get("memory_id") or "").strip()
            if raw.startswith("memory:"):
                raw = raw.split(":", 1)[1]
            if raw:
                references.add(raw)
        return references

    @staticmethod
    def _dependency_entries(state: RunState, task: TaskNode) -> list[MemoryEntry]:
        dependencies = set(task.dependencies)
        return sorted(
            (
                entry
                for entry in state.memory_index.values()
                if entry.task_id in dependencies
            ),
            key=lambda entry: (task.dependencies.index(entry.task_id), entry.created_at, entry.memory_id),
        )

    @staticmethod
    def _relevant_entries(
        state: RunState,
        task: TaskNode,
        *,
        excluded_ids: set[str],
        explicit_refs: set[str],
    ) -> list[MemoryEntry]:
        task_terms = {
            term.casefold()
            for term in f"{task.title} {task.description}".replace("/", " ").split()
            if len(term) >= 3
        }

        def score(entry: MemoryEntry) -> tuple[int, str, str]:
            explicit = int(entry.memory_id in explicit_refs)
            active = int(entry.task_id == task.task_id)
            evidence = int(bool(entry.evidence_refs))
            tag_matches = sum(
                1 for tag in entry.tags if str(tag).casefold() in task_terms
            )
            return (explicit * 100 + active * 50 + evidence * 20 + tag_matches, entry.created_at, entry.memory_id)

        candidates = [
            entry
            for entry in state.memory_index.values()
            if entry.memory_id not in excluded_ids
            and (
                entry.memory_id in explicit_refs
                or entry.task_id == task.task_id
                or bool(entry.evidence_refs)
                or any(str(tag).casefold() in task_terms for tag in entry.tags)
            )
        ]
        return sorted(candidates, key=score, reverse=True)

    def _pack_entries(
        self,
        entries: Iterable[MemoryEntry],
        budget: int,
    ) -> tuple[list[str], list[str]]:
        remaining = max(0, int(budget))
        output: list[str] = []
        selected_ids: list[str] = []
        for entry in entries:
            if remaining <= 0:
                break
            text = self._entry_text(entry)
            tokens = get_token_count(text)
            if tokens > remaining:
                if not output and remaining >= 64:
                    text = self._bounded(text, remaining)
                    tokens = get_token_count(text)
                else:
                    continue
            output.append(text)
            selected_ids.append(entry.memory_id)
            remaining -= tokens
        return output, selected_ids

    @staticmethod
    def _failure_text(state: RunState, task: TaskNode) -> str:
        if task.error:
            return json.dumps(task.error, ensure_ascii=False, indent=2)
        for error in reversed(state.errors):
            if not error.get("task_id") or error.get("task_id") == task.task_id:
                return json.dumps(error, ensure_ascii=False, indent=2)
        return ""

    @staticmethod
    def _bounded(text: str, budget: int) -> str:
        value = str(text or "").strip()
        if not value or get_token_count(value) <= budget:
            return value
        prefix, _ = smart_truncate(value, max_tokens=max(1, budget))
        return prefix.strip()

    def _enforce_total_budget(self, bundle: ContextBundle) -> None:
        fixed = get_token_count("\n\n".join([bundle.goal, bundle.task]))
        remaining = max(0, self.budgets.total_input - fixed)
        mutable = [
            ("dependencies", bundle.dependencies),
            ("evidence", bundle.evidence),
        ]
        for _, values in mutable:
            while values and get_token_count(bundle.to_prompt()) > self.budgets.total_input:
                values.pop()
        if get_token_count(bundle.to_prompt()) > self.budgets.total_input:
            bundle.failure = ""
        if get_token_count(bundle.to_prompt()) > self.budgets.total_input:
            bundle.action_contract = self._bounded(bundle.action_contract, max(0, remaining // 2))
        if get_token_count(bundle.to_prompt()) > self.budgets.total_input:
            raise ValueError("goal and active task exceed working-memory input budget")


__all__ = ["ContextBundle", "MemoryBudgets", "WorkingMemoryBuilder"]
