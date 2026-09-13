"""Coding tasks in a copied workspace, using the production execution loop."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import shutil

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
    entries = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            entries[str(path.relative_to(root))] = 'symlink:' + str(path.readlink())
        elif path.is_file():
            entries[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return entries


class _RecordedHarness(ActionHarness):
    def __init__(self, output):
        super().__init__()
        self.output = output
        self.index = 0

    def execute(self, action, goal):
        self.index += 1
        directory = self.output / 'tool_snapshots' / f'{self.index:03d}'
        directory.mkdir(parents=True)
        shutil.copytree(goal.workspace_root, directory / 'before', symlinks=True)
        _save(directory / 'call.json', {'action_type': action.action_type, 'arguments': action.arguments})
        try:
            return super().execute(action, goal)
        finally:
            shutil.copytree(goal.workspace_root, directory / 'after', symlinks=True)


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
    for path in source.rglob('*'):
        if '.git' in path.relative_to(source).parts:
            continue
        if path.is_symlink():
            raise ValueError(f'source symlink not supported: {path.relative_to(source)}')
        if not path.is_dir() and not path.is_file():
            raise ValueError(f'source special file not supported: {path.relative_to(source)}')
    workspace = output / 'workspace'
    execution = output / 'execution'
    shutil.copytree(source, workspace, ignore=shutil.ignore_patterns('.git'), symlinks=True)
    before = _inventory(workspace)
    _save(output / 'INITIAL_FILES.json', before)
    inner = ReadOnlyJob(job.task_id, job.request, str(workspace), str(execution),
                        job.max_calls, job.max_seconds, tool_scope='coding')
    result = _run_job(inner, settings=settings, session_factory=session_factory,
                      harness_factory=lambda: _RecordedHarness(execution),
                      controller_type=LongHorizonController, allowed_scopes=('coding',))
    after = _inventory(workspace)
    delivery = {**result, 'workspace': str(workspace), 'source_workspace': str(source),
                'changed_files': sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p)),
                'final_files': after}
    _save(output / 'DELIVERY.json', delivery)
    return delivery
