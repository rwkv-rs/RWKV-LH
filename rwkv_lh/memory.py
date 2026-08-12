"""Bounded working-memory projection for one active task."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Iterable

from rwkv_lh.schema import MemoryEntry, RunState, TaskNode
from rwkv_lh.runtime.settings import get_runtime_settings
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

    def projected(self, total_input: int) -> "ContextBundle":
        """Return a smaller prompt projection without truncating Goal or task."""

        limit = max(1, int(total_input))
        bundle = ContextBundle(
            goal=self.goal,
            task=self.task,
            dependencies=list(self.dependencies),
            evidence=list(self.evidence),
            failure=self.failure,
            action_contract=self.action_contract,
            selected_memory_ids=list(self.selected_memory_ids),
            excluded_memory_ids=list(self.excluded_memory_ids),
        )
        # General evidence is least authoritative. Dependency observations and
        # the latest material failure remain available for as long as possible.
        while bundle.evidence and get_token_count(bundle.to_prompt()) > limit:
            bundle.evidence.pop()
        while bundle.dependencies and get_token_count(bundle.to_prompt()) > limit:
            bundle.dependencies.pop()
        if get_token_count(bundle.to_prompt()) > limit:
            bundle.action_contract = ""
        if get_token_count(bundle.to_prompt()) > limit:
            bundle.failure = ""
        if get_token_count(bundle.to_prompt()) > limit:
            raise ValueError(
                "immutable goal and active task exceed the request-specific prompt budget"
            )
        bundle.refresh_token_counts()
        return bundle

    def refresh_token_counts(self) -> None:
        self.token_counts = {
            "goal": get_token_count(self.goal),
            "task": get_token_count(self.task),
            "dependencies": get_token_count("\n\n".join(self.dependencies)),
            "evidence": get_token_count("\n\n".join(self.evidence)),
            "failure": get_token_count(self.failure),
            "action_contract": get_token_count(self.action_contract),
            "total": get_token_count(self.to_prompt()),
        }


class WorkingMemoryBuilder:
    def __init__(self, budgets: MemoryBudgets | None = None):
        self.budgets = budgets or MemoryBudgets()

    def build(
        self,
        state: RunState,
        task: TaskNode,
        *,
        action_contract: str = "",
        max_output_tokens: int | None = None,
        prompt_overhead_tokens: int = 0,
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
        total_limit = self.budgets.total_input
        if max_output_tokens is not None:
            request_limit = (
                get_runtime_settings().max_prompt_tokens(max_output_tokens)
                - max(0, int(prompt_overhead_tokens))
            )
            if request_limit < 1:
                raise ValueError("prompt overhead leaves no working-memory budget")
            total_limit = min(total_limit, request_limit)
        return bundle.projected(total_limit)

    def build_task_validation(
        self,
        state: RunState,
        task: TaskNode,
    ) -> ContextBundle:
        """Project a task-local, read-only validation lane.

        The validation model receives only the criteria directly claimed by
        this task, its dependencies, its observations, and the current
        recovery lineage. It does not receive unrelated Goal outcomes.
        """

        bundle = self.build(state, task)
        claimed = [
            asdict(criterion)
            for criterion in state.goal.success_criteria
            if criterion.criterion_id in task.satisfies_criteria
        ]
        bundle.goal = self._bounded(
            "TASK VALIDATION SCOPE\n"
            + json.dumps(
                {
                    "goal_digest": state.goal.digest,
                    "constraints": list(state.goal.constraints),
                    "claimed_criteria": claimed,
                },
                ensure_ascii=False,
                indent=2,
            ),
            self.budgets.goal,
        )
        explicit_refs = self._explicit_memory_refs(task)
        allowed_ids = {
            entry.memory_id
            for entry in state.memory_index.values()
            if entry.task_id == task.task_id
            or entry.task_id in task.dependencies
            or entry.memory_id in explicit_refs
        }
        bundle.evidence = [
            item
            for item in bundle.evidence
            if any(item.startswith(f"[{memory_id}]") for memory_id in allowed_ids)
        ]
        bundle.selected_memory_ids = [
            memory_id
            for memory_id in bundle.selected_memory_ids
            if memory_id in allowed_ids
        ]
        bundle.excluded_memory_ids = sorted(
            set(state.memory_index) - set(bundle.selected_memory_ids)
        )
        bundle.refresh_token_counts()
        return bundle.projected(self.budgets.total_input)

    @staticmethod
    def _goal_text(state: RunState) -> str:
        criteria = [asdict(item) for item in state.goal.success_criteria]
        return (
            "IMMUTABLE GOAL\n"
            + json.dumps(
                {
                    "objective": state.goal.objective,
                    "original_request": state.goal.original_request,
                    "constraints": list(state.goal.constraints),
                    "success_criteria": criteria,
                    "workspace_scope": ".",
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
                    "satisfies_criteria": task.satisfies_criteria,
                    "subject_task_id": task.subject_task_id,
                    "recovery_lineage_id": task.recovery_lineage_id,
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
        if task.recovery_lineage_id:
            lineage = state.recovery_states.get(task.recovery_lineage_id)
            if lineage is not None:
                return json.dumps(asdict(lineage), ensure_ascii=False, indent=2)
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

__all__ = ["ContextBundle", "MemoryBudgets", "WorkingMemoryBuilder"]
