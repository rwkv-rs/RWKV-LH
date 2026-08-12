"""Deterministic Task Graph invariants and transitions."""

from __future__ import annotations

from collections import deque
from typing import Iterable

from rwkv_lh.schema import TaskNode, TaskStatus


class TaskGraphError(ValueError):
    pass


class TaskGraph:
    _allowed_transitions = {
        TaskStatus.PENDING: {TaskStatus.RUNNING, TaskStatus.BLOCKED},
        TaskStatus.RUNNING: {
            TaskStatus.COMPLETED,
            TaskStatus.FAILED,
            TaskStatus.BLOCKED,
        },
        TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.BLOCKED},
        TaskStatus.COMPLETED: set(),
        TaskStatus.BLOCKED: set(),
    }

    def __init__(self, tasks: dict[str, TaskNode] | None = None):
        self.tasks = tasks if tasks is not None else {}
        self.validate()

    def validate(self) -> None:
        for key, task in self.tasks.items():
            if not task.task_id or task.task_id != key:
                raise TaskGraphError("task mapping key must equal non-empty task_id")
            if not task.title or not task.description:
                raise TaskGraphError(f"task {key} requires title and description")
            unknown = sorted(set(task.dependencies) - set(self.tasks))
            if unknown:
                raise TaskGraphError(f"task {key} has unknown dependencies: {unknown}")
            if key in task.dependencies:
                raise TaskGraphError(f"task {key} cannot depend on itself")
            if task.superseded_by is not None:
                if task.superseded_by not in self.tasks:
                    raise TaskGraphError(
                        f"task {key} has unknown replacement: {task.superseded_by}"
                    )
                if task.superseded_by == key:
                    raise TaskGraphError(f"task {key} cannot supersede itself")
        self._validate_acyclic()
        for task_id in self.tasks:
            self._effective_task_id(task_id)
        self._validate_effective_acyclic()

    def _validate_acyclic(self) -> None:
        indegree = {task_id: 0 for task_id in self.tasks}
        dependents: dict[str, list[str]] = {task_id: [] for task_id in self.tasks}
        for task_id, task in self.tasks.items():
            indegree[task_id] = len(task.dependencies)
            for dependency in task.dependencies:
                dependents[dependency].append(task_id)
        queue = deque(sorted(key for key, count in indegree.items() if count == 0))
        visited = 0
        while queue:
            task_id = queue.popleft()
            visited += 1
            for dependent in dependents[task_id]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
        if visited != len(self.tasks):
            raise TaskGraphError("task graph contains a dependency cycle")

    def add_tasks(self, tasks: Iterable[TaskNode]) -> None:
        additions = list(tasks)
        if not additions:
            return
        existing_ids = set(self.tasks)
        new_ids = [task.task_id for task in additions]
        if len(new_ids) != len(set(new_ids)):
            raise TaskGraphError("new task ids must be unique")
        overlap = sorted(existing_ids & set(new_ids))
        if overlap:
            raise TaskGraphError(f"cannot replace existing tasks: {overlap}")
        next_order = max(
            (task.insertion_order for task in self.tasks.values()),
            default=-1,
        ) + 1
        for offset, task in enumerate(additions):
            task.insertion_order = next_order + offset
            self.tasks[task.task_id] = task
        try:
            self.validate()
        except Exception:
            for task in additions:
                self.tasks.pop(task.task_id, None)
            raise

    @staticmethod
    def materialize_model_tasks(
        tasks: Iterable[TaskNode],
        *,
        existing_ids: Iterable[str] = (),
        next_sequence: int = 1,
    ) -> tuple[list[TaskNode], dict[str, str], int]:
        """Allocate global task ids and deterministically rewrite local refs.

        Model-emitted ids are local references only. They never become global
        structure ids directly, which prevents reuse and supersede corruption
        from crossing the model/Controller boundary.
        """

        proposals = [TaskNode.from_dict(task.to_dict()) for task in tasks]
        if not proposals:
            raise TaskGraphError("model task proposal is empty")
        local_ids = [task.task_id for task in proposals]
        if any(not task_id for task_id in local_ids):
            raise TaskGraphError("model tasks require non-empty local ids")
        if len(local_ids) != len(set(local_ids)):
            raise TaskGraphError("model task local ids must be unique")
        reserved = {str(item) for item in existing_ids}
        sequence = max(1, int(next_sequence))
        mapping: dict[str, str] = {}
        for local_id in local_ids:
            while f"T{sequence}" in reserved:
                sequence += 1
            allocated = f"T{sequence}"
            sequence += 1
            reserved.add(allocated)
            mapping[local_id] = allocated
        local_set = set(local_ids)
        for task in proposals:
            local_id = task.task_id
            task.task_id = mapping[local_id]
            task.dependencies = [
                mapping[dependency] if dependency in local_set else dependency
                for dependency in task.dependencies
            ]
            task.active = True
            task.status = TaskStatus.PENDING
            task.attempt_ids = []
            task.output_refs = []
            task.error = None
            task.superseded_by = None
        return proposals, mapping, sequence

    def ready_tasks(self) -> list[TaskNode]:
        ready = []
        for task in self.tasks.values():
            if not task.active or task.status != TaskStatus.PENDING:
                continue
            if all(
                self._dependency_satisfied(dependency)
                for dependency in task.dependencies
            ):
                ready.append(task)
        return sorted(
            ready,
            key=lambda item: (
                0 if item.required else 1,
                -item.priority,
                item.insertion_order,
                item.task_id,
            ),
        )

    def transition(self, task_id: str, status: TaskStatus) -> TaskNode:
        task = self.tasks.get(task_id)
        if task is None:
            raise TaskGraphError(f"unknown task: {task_id}")
        if status == task.status:
            return task
        if status not in self._allowed_transitions[task.status]:
            raise TaskGraphError(
                f"invalid task transition: {task.status.value} -> {status.value}"
            )
        if status == TaskStatus.RUNNING:
            unmet = [
                dependency
                for dependency in task.dependencies
                if not self._dependency_satisfied(dependency)
            ]
            if unmet:
                raise TaskGraphError(f"task {task_id} has unmet dependencies: {unmet}")
        task.status = status
        return task

    def supersede(self, task_id: str, replacement_id: str) -> None:
        task = self.tasks.get(task_id)
        replacement = self.tasks.get(replacement_id)
        if task is None or replacement is None:
            raise TaskGraphError("supersede requires existing task and replacement")
        if task.status == TaskStatus.COMPLETED:
            raise TaskGraphError("completed tasks cannot be superseded")
        previous_active = task.active
        previous_replacement = task.superseded_by
        task.active = False
        task.superseded_by = replacement_id
        try:
            self.validate()
        except Exception:
            task.active = previous_active
            task.superseded_by = previous_replacement
            raise

    def _effective_task_id(self, task_id: str) -> str:
        current = task_id
        visited: set[str] = set()
        while not self.tasks[current].active and self.tasks[current].superseded_by:
            if current in visited:
                raise TaskGraphError("task supersede chain contains a cycle")
            visited.add(current)
            current = str(self.tasks[current].superseded_by)
            if current not in self.tasks:
                raise TaskGraphError(f"unknown replacement task: {current}")
        return current

    def _dependency_satisfied(self, task_id: str) -> bool:
        effective = self.tasks[self._effective_task_id(task_id)]
        return effective.active and effective.status == TaskStatus.COMPLETED

    def _validate_effective_acyclic(self) -> None:
        active_ids = {task_id for task_id, task in self.tasks.items() if task.active}
        indegree = {task_id: 0 for task_id in active_ids}
        dependents: dict[str, list[str]] = {task_id: [] for task_id in active_ids}
        for task_id in active_ids:
            effective_dependencies = {
                self._effective_task_id(dependency)
                for dependency in self.tasks[task_id].dependencies
            }
            if task_id in effective_dependencies:
                raise TaskGraphError(
                    f"task {task_id} depends on itself through a replacement"
                )
            for dependency in effective_dependencies:
                if dependency not in active_ids:
                    raise TaskGraphError(
                        f"task {task_id} depends on inactive task {dependency}"
                    )
                indegree[task_id] += 1
                dependents[dependency].append(task_id)
        queue = deque(sorted(task_id for task_id, count in indegree.items() if count == 0))
        visited = 0
        while queue:
            task_id = queue.popleft()
            visited += 1
            for dependent in dependents[task_id]:
                indegree[dependent] -= 1
                if indegree[dependent] == 0:
                    queue.append(dependent)
        if visited != len(active_ids):
            raise TaskGraphError("effective task graph contains a replacement cycle")

    def required_complete(self) -> bool:
        required = [
            task
            for task in self.tasks.values()
            if task.active and task.required
        ]
        return bool(required) and all(
            task.status == TaskStatus.COMPLETED for task in required
        )

    def unresolved_required(self) -> list[TaskNode]:
        return [
            task
            for task in self.tasks.values()
            if task.active and task.required and task.status != TaskStatus.COMPLETED
        ]


__all__ = ["TaskGraph", "TaskGraphError"]
