"""Bounded working-memory projection for one active task."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Callable, Iterable

from rwkv_lh.schema import MemoryEntry, RunState, TaskNode
from rwkv_lh.runtime.settings import get_runtime_settings
from rwkv_lh.token_budget import get_token_count, smart_truncate


@dataclass(frozen=True)
class MemoryBudgets:
    total_input: int = 13600
    goal: int = 1200
    task: int = 1600
    causal_state: int = 2200
    dependencies: int = 3000
    evidence: int = 5000
    failure: int = 1200
    action_contract: int = 1600


@dataclass
class ContextBundle:
    goal: str
    task: str
    schema_version: str = "rwkv-lh.execution-capsule.v1"
    causal_state: str = ""
    dependencies: list[str] = field(default_factory=list)
    evidence: list[str] = field(default_factory=list)
    failure: str = ""
    action_contract: str = ""
    selected_memory_ids: list[str] = field(default_factory=list)
    excluded_memory_ids: list[str] = field(default_factory=list)
    token_counts: dict[str, int] = field(default_factory=dict)
    capsule_digest: str = ""

    @property
    def total_tokens(self) -> int:
        return int(self.token_counts.get("total", 0))

    def to_prompt(self) -> str:
        sections = [self.goal, self.task]
        if self.causal_state:
            sections.append("CURRENT CAUSAL STATE\n" + self.causal_state)
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
            schema_version=self.schema_version,
            goal=self.goal,
            task=self.task,
            causal_state=self.causal_state,
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "capsule_digest": self.capsule_digest,
            "goal": self.goal,
            "task": self.task,
            "causal_state": self.causal_state,
            "dependencies": list(self.dependencies),
            "evidence": list(self.evidence),
            "failure": self.failure,
            "action_contract": self.action_contract,
            "selected_memory_ids": list(self.selected_memory_ids),
            "excluded_memory_ids": list(self.excluded_memory_ids),
            "token_counts": dict(self.token_counts),
        }

    def refresh_token_counts(self) -> None:
        self.token_counts = {
            "goal": get_token_count(self.goal),
            "task": get_token_count(self.task),
            "causal_state": get_token_count(self.causal_state),
            "dependencies": get_token_count("\n\n".join(self.dependencies)),
            "evidence": get_token_count("\n\n".join(self.evidence)),
            "failure": get_token_count(self.failure),
            "action_contract": get_token_count(self.action_contract),
            "total": get_token_count(self.to_prompt()),
        }
        self.capsule_digest = hashlib.sha256(
            self.to_prompt().encode("utf-8")
        ).hexdigest()


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
        goal = self._bounded(self._goal_text(state, task), self.budgets.goal)
        task_text = self._bounded(self._task_text(task), self.budgets.task)
        causal_state = self._bounded(
            self._causal_state_text(state, task),
            self.budgets.causal_state,
        )
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
            causal_state=causal_state,
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
        """Project only the active Task contract and its real observations."""

        dependency_entries = self._dependency_entries(state, task)
        current_entries = [
            entry
            for entry in sorted(
                state.memory_index.values(),
                key=lambda item: (item.created_at, item.memory_id),
            )
            if entry.task_id == task.task_id
        ]
        dependencies, dependency_ids = self._pack_entries(
            dependency_entries,
            self.budgets.dependencies,
            renderer=lambda entry: self._phase_observation_text(state, entry),
        )
        evidence, evidence_ids = self._pack_entries(
            current_entries,
            self.budgets.evidence,
            renderer=lambda entry: self._phase_observation_text(state, entry),
        )
        selected = list(dict.fromkeys([*dependency_ids, *evidence_ids]))
        bundle = ContextBundle(
            schema_version="rwkv-lh.task-postcondition-capsule.v1",
            goal=self._bounded(
                "TASK-LOCAL VALIDATION SCOPE\n"
                + json.dumps(
                    {
                        "goal_digest": state.goal.digest,
                        "constraints": list(state.goal.constraints),
                        "workspace_scope": ".",
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                self.budgets.goal,
            ),
            task=self._bounded(
                self._task_contract_text(task, include_committed_action=True),
                self.budgets.task,
            ),
            dependencies=dependencies,
            evidence=evidence,
            selected_memory_ids=selected,
            excluded_memory_ids=sorted(set(state.memory_index) - set(selected)),
        )
        bundle.refresh_token_counts()
        return bundle.projected(self.budgets.total_input)

    def build_action_commit(
        self,
        state: RunState,
        task: TaskNode,
    ) -> ContextBundle:
        """Project one action-selection capsule without internal placeholders."""

        dependency_entries = self._dependency_entries(state, task)
        explicit_refs = self._explicit_memory_refs(task)
        current_entries = [
            entry
            for entry in sorted(
                state.memory_index.values(),
                key=lambda item: (item.created_at, item.memory_id),
            )
            if entry.task_id == task.task_id or entry.memory_id in explicit_refs
        ]
        dependencies, dependency_ids = self._pack_entries(
            dependency_entries,
            self.budgets.dependencies,
            renderer=lambda entry: self._phase_observation_text(state, entry),
        )
        evidence, evidence_ids = self._pack_entries(
            current_entries,
            self.budgets.evidence,
            renderer=lambda entry: self._phase_observation_text(state, entry),
        )
        selected = list(dict.fromkeys([*dependency_ids, *evidence_ids]))
        bundle = ContextBundle(
            schema_version="rwkv-lh.action-commit-capsule.v1",
            goal=self._bounded(self._goal_text(state, task), self.budgets.goal),
            task=self._bounded(
                self._task_contract_text(task, include_committed_action=False),
                self.budgets.task,
            ),
            dependencies=dependencies,
            evidence=evidence,
            failure=self._bounded(
                self._failure_text(state, task),
                self.budgets.failure,
            ),
            selected_memory_ids=selected,
            excluded_memory_ids=sorted(set(state.memory_index) - set(selected)),
        )
        bundle.refresh_token_counts()
        return bundle.projected(self.budgets.total_input)

    def build_recovery(
        self,
        state: RunState,
        task: TaskNode,
    ) -> ContextBundle:
        """Project the failed Task, real observations, and compact lineage only."""

        bundle = self.build_action_commit(state, task)
        bundle.schema_version = "rwkv-lh.recovery-capsule.v1"
        bundle.task = self._bounded(
            self._task_contract_text(task, include_committed_action=True),
            self.budgets.task,
        )
        bundle.refresh_token_counts()
        return bundle.projected(self.budgets.total_input)

    def build_goal_validation(
        self,
        state: RunState,
        *,
        criterion_ids: list[str],
        selected_memory_ids: list[str],
    ) -> ContextBundle:
        """Project one compact Goal-evidence view at a closed causal frontier."""

        claimed = [
            criterion.to_dict()
            for criterion in state.goal.success_criteria
            if criterion.criterion_id in set(criterion_ids)
        ]
        completed = [
            {
                "task_id": task.task_id,
                "title": task.title,
                "dependencies": list(task.dependencies),
                "postcondition": task.postcondition,
                "attempt_id": task.attempt_ids[-1] if task.attempt_ids else "",
                "output_refs": [
                    ref for ref in task.output_refs if ref in state.memory_index
                ],
            }
            for task in sorted(
                state.tasks.values(),
                key=lambda item: (item.insertion_order, item.task_id),
            )
            if task.active and task.status.value == "completed"
        ]
        selected = list(dict.fromkeys(selected_memory_ids))
        bundle = ContextBundle(
            schema_version="rwkv-lh.goal-evidence-capsule.v1",
            goal=self._bounded(
                "IMMUTABLE GOAL EVIDENCE SCOPE\n"
                + json.dumps(
                    {
                        "objective": state.goal.objective,
                        "original_request": state.goal.original_request,
                        "constraints": list(state.goal.constraints),
                        "claimed_criteria": claimed,
                        "goal_digest": state.goal.digest,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                self.budgets.goal,
            ),
            task=(
                "GOAL EVIDENCE FRONTIER\n"
                "All active required Tasks are complete. Decide only whether the "
                "catalogued causal observations establish every claimed criterion."
            ),
            causal_state=self._bounded(
                json.dumps(
                    {"completed_active_tasks": completed},
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                self.budgets.causal_state,
            ),
            selected_memory_ids=selected,
            excluded_memory_ids=sorted(set(state.memory_index) - set(selected)),
        )
        bundle.refresh_token_counts()
        return bundle.projected(self.budgets.total_input)

    @staticmethod
    def _goal_text(state: RunState, task: TaskNode) -> str:
        bound_ids = set(task.advances_criteria) | set(task.satisfies_criteria)
        criteria = [
            item.to_dict()
            for item in state.goal.success_criteria
            if item.criterion_id in bound_ids
        ]
        return (
            "IMMUTABLE GOAL\n"
            + json.dumps(
                {
                    "objective": state.goal.objective,
                    "original_request": state.goal.original_request,
                    "constraints": list(state.goal.constraints),
                    "task_bound_success_criteria": criteria,
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
                    "advances_criteria": task.advances_criteria,
                    "satisfies_criteria": task.satisfies_criteria,
                    "subject_task_id": task.subject_task_id,
                    "recovery_lineage_id": task.recovery_lineage_id,
                    "operation_kind": task.operation_kind,
                    "subject_key": task.subject_key,
                    "member_key": task.member_key,
                    "phase_key": task.phase_key,
                    "effect_targets": task.effect_targets,
                    "expected_outcomes": task.expected_outcomes,
                    "dependency_outcomes": task.dependency_outcomes,
                    "postcondition": task.postcondition,
                    "outcome_type": task.outcome_type,
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
    def _task_contract_text(
        task: TaskNode,
        *,
        include_committed_action: bool,
    ) -> str:
        contract: dict[str, Any] = {
            "task_id": task.task_id,
            "title": task.title,
            "description": task.description,
            "dependencies": list(task.dependencies),
            "postcondition": task.postcondition,
        }
        if (
            include_committed_action
            and task.action.action_type
            and task.action.action_type != "model_action"
        ):
            contract["committed_action"] = {
                "name": task.action.action_type,
                "arguments": dict(task.action.arguments),
            }
        return "ACTIVE TASK CONTRACT\n" + json.dumps(
            contract,
            ensure_ascii=False,
            indent=2,
        )

    @staticmethod
    def _causal_state_text(state: RunState, task: TaskNode) -> str:
        dependency_rows: list[dict[str, Any]] = []
        related_targets = set(task.effect_targets)
        for dependency_id in task.dependencies:
            dependency = state.tasks.get(dependency_id)
            if dependency is None:
                continue
            related_targets.update(dependency.effect_targets)
            dependency_rows.append(
                {
                    "task_id": dependency.task_id,
                    "status": dependency.status.value,
                    "outcome_type": dependency.outcome_type,
                    "commit_status": dependency.postcondition_commit_status.value,
                    "subject_key": dependency.subject_key,
                    "member_key": dependency.member_key,
                    "phase_key": dependency.phase_key,
                    "postcondition": dependency.postcondition,
                    "effect_targets": list(dependency.effect_targets),
                    "output_refs": list(dependency.output_refs),
                    "allowed_outcomes_for_active_task": task.dependency_outcomes.get(
                        dependency_id,
                        [],
                    ),
                }
            )
        related_task_rows = [
            {
                "task_id": candidate.task_id,
                "status": candidate.status.value,
                "outcome_type": candidate.outcome_type,
                "commit_status": candidate.postcondition_commit_status.value,
                "member_key": candidate.member_key,
                "phase_key": candidate.phase_key,
                "effect_targets": list(candidate.effect_targets),
            }
            for candidate in sorted(
                state.tasks.values(),
                key=lambda item: (item.insertion_order, item.task_id),
            )
            if candidate.active
            and candidate.task_id != task.task_id
            and task.subject_key
            and candidate.subject_key == task.subject_key
        ][-16:]
        revision_rows: list[dict[str, Any]] = []
        for target in sorted(related_targets):
            for revision in state.artifact_revisions.get(target, [])[-2:]:
                revision_rows.append(asdict(revision))
        payload: dict[str, Any] = {
            "schema_version": "rwkv-lh.causal-state.v1",
            "goal_digest": state.goal.digest,
            "active_task_id": task.task_id,
            "direct_dependencies": dependency_rows,
            "same_subject_ledger": related_task_rows,
            "related_artifact_revisions": revision_rows[-16:],
        }
        payload["projection_digest"] = hashlib.sha256(
            json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        ).hexdigest()
        return json.dumps(payload, ensure_ascii=False, indent=2)

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
    def _phase_observation_text(state: RunState, entry: MemoryEntry) -> str:
        """Expose observed data while omitting internal audit object fields."""

        content = entry.content.strip() or entry.summary.strip()
        if entry.kind == "post_action_workspace_snapshot":
            try:
                parsed = json.loads(content)
            except (TypeError, ValueError):
                parsed = None
            if isinstance(parsed, dict):
                observation = {
                    key: parsed[key]
                    for key in (
                        "path",
                        "content",
                        "content_included",
                        "omission_reason",
                        "sha256",
                        "size_bytes",
                    )
                    if key in parsed
                }
                content = json.dumps(
                    observation,
                    ensure_ascii=False,
                    indent=2,
                )
        observed_artifacts = [
            {
                "path": state.artifacts[artifact_ref].path,
                "sha256": state.artifacts[artifact_ref].sha256,
                "media_type": state.artifacts[artifact_ref].media_type,
            }
            for artifact_ref in entry.artifact_refs
            if artifact_ref in state.artifacts
        ]
        artifact_section = (
            "\nobserved_artifacts:\n"
            + json.dumps(observed_artifacts, ensure_ascii=False, indent=2)
            if observed_artifacts
            else ""
        )
        return (
            f"[{entry.memory_id}] observed_kind={entry.kind} "
            f"producer_task={entry.task_id}\n"
            f"observed_data:\n{content}{artifact_section}"
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
        selected: list[MemoryEntry] = []
        seen: set[str] = set()
        for dependency_id in task.dependencies:
            dependency = state.tasks.get(dependency_id)
            if dependency is None:
                continue
            # output_refs is replaced on every attempt, so it is the
            # authoritative latest projection for this dependency.
            output_refs = list(dependency.output_refs)
            if not output_refs:
                # Schema-v1 checkpoints and deterministic control fixtures
                # predate Task.output_refs. Owner identity is the only
                # available provenance in that case; never mix it with a
                # non-empty current projection.
                output_refs = [
                    entry.memory_id
                    for entry in sorted(
                        state.memory_index.values(),
                        key=lambda item: (item.created_at, item.memory_id),
                    )
                    if entry.task_id == dependency_id
                ]
            for output_ref in output_refs:
                entry = state.memory_index.get(output_ref)
                if entry is None or entry.memory_id in seen:
                    continue
                selected.append(entry)
                seen.add(entry.memory_id)
        return selected

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
        current_refs = list(task.output_refs)
        provenance_refs = [
            entry.memory_id
            for entry in state.memory_index.values()
            if entry.evidence_refs
            or any(str(tag).casefold() in task_terms for tag in entry.tags)
        ]
        ordered_ids = list(
            dict.fromkeys(
                [
                    *sorted(explicit_refs),
                    *current_refs,
                    *sorted(provenance_refs),
                ]
            )
        )
        dependencies = set(task.dependencies)
        selected: list[MemoryEntry] = []
        for memory_id in ordered_ids:
            if memory_id in excluded_ids or memory_id not in state.memory_index:
                continue
            entry = state.memory_index[memory_id]
            if (
                entry.kind == "post_action_workspace_snapshot"
                and entry.task_id != task.task_id
                and entry.task_id not in dependencies
            ):
                continue
            selected.append(entry)
        return selected

    def _pack_entries(
        self,
        entries: Iterable[MemoryEntry],
        budget: int,
        *,
        renderer: Callable[[MemoryEntry], str] | None = None,
    ) -> tuple[list[str], list[str]]:
        remaining = max(0, int(budget))
        output: list[str] = []
        selected_ids: list[str] = []
        for entry in entries:
            if remaining <= 0:
                break
            text = (renderer or self._entry_text)(entry)
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
                latest = next(
                    (
                        dict(item)
                        for item in reversed(lineage.decision_history)
                        if item.get("type") in {"failure", "decision"}
                    ),
                    {},
                )
                return json.dumps(
                    {
                        "lineage_id": lineage.lineage_id,
                        "root_task_id": lineage.root_task_id,
                        "failed_task_id": lineage.failed_task_id,
                        "subject_task_id": lineage.subject_task_id,
                        "failure_fingerprint": lineage.failure_fingerprint,
                        "same_failure_count": lineage.same_failure_count,
                        "remaining_budget": lineage.remaining_budget,
                        "latest_material_event": latest,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
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
