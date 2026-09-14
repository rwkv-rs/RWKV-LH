"""Coding tasks in a copied workspace, using the production execution loop."""
from .job_budget import task_deadline
from dataclasses import dataclass
from pathlib import Path
import shutil

from .workspace_snapshot import tree_identity, file_inventory, copy_verified_workspace
from .controller import LongHorizonController
from .harness import ActionHarness
from .model_session import create_model_session
from .read_only_agent import ReadOnlyJob, _run_job, _save


@dataclass(frozen=True)
class CodingJob:
    task_id: str
    request: str
    source_workspace: str
    output_dir: str
    max_calls: int = 12
    max_seconds: float = 600


def _inventory(root):
    return file_inventory(tree_identity(root, allow_links=True))


class _RecordedHarness(ActionHarness):
    def __init__(self, output):
        super().__init__()
        self.output = output
        self.index = 0

    def execute(self, action, goal):
        self.index += 1
        directory = self.output / 'tool_snapshots' / f'{self.index:03d}'
        directory.mkdir(parents=True)
        definition = self.definition(action.action_type)
        snapshot_needed = not definition.read_only or definition.side_effect
        if snapshot_needed:
            shutil.copytree(goal.workspace_root, directory / 'before', symlinks=True)
        _save(directory / 'call.json', {'action_type': action.action_type, 'arguments': action.arguments,
              'snapshot_policy': 'before_after' if snapshot_needed else 'observation_only'})
        try:
            return super().execute(action, goal)
        finally:
            if snapshot_needed:
                shutil.copytree(goal.workspace_root, directory / 'after', symlinks=True)


@task_deadline
def run_coding_job(job, *, settings, session_factory=create_model_session):
    """Deliver original answers and file changes; submission does not assert acceptance.

    Workspace copying isolates artifacts, not arbitrary host processes. Existing
    command-tool permissions still apply. V1 accepts regular-file source trees.
    """
    source = Path(job.source_workspace).resolve(strict=True)
    output = Path(job.output_dir).resolve()
    if not source.is_dir():
        raise ValueError('source workspace must be a directory')
    if source == output or source in output.parents or output in source.parents:
        raise ValueError('source and output must not overlap')
    if output.exists():
        raise FileExistsError(output)
    workspace = output / 'workspace'
    execution = output / 'execution'
    before_tree = copy_verified_workspace(source, workspace, audit_path=output / 'SOURCE_COPY.json')
    before = file_inventory(before_tree)
    _save(output / 'INITIAL_TREE.json', before_tree)
    _save(output / 'INITIAL_FILES.json', before)
    inner = ReadOnlyJob(job.task_id, job.request, str(workspace), str(execution),
                        job.max_calls, job.max_seconds, tool_scope='coding')
    result = _run_job(inner, settings=settings, session_factory=session_factory,
                      harness_factory=lambda: _RecordedHarness(execution),
                      controller_type=LongHorizonController, allowed_scopes=('coding',))
    if result['termination_reason'] == 'wall_budget_exhausted':
        return {**result, 'workspace': str(workspace), 'source_workspace': str(source),
                'changed_files': None, 'final_files': None, 'final_tree': None}
    after_tree = tree_identity(workspace, allow_links=True)
    after = file_inventory(after_tree)
    delivery = {**result, 'workspace': str(workspace), 'source_workspace': str(source),
                'changed_files': sorted(p for p in before_tree.keys() | after_tree.keys() if before_tree.get(p) != after_tree.get(p)),
                'final_files': after, 'final_tree': after_tree}
    _save(output / 'DELIVERY.json', delivery)
    return delivery
