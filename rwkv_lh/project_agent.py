"""Product project entry and explicit recovery; no legacy-controller fallback."""
import json
import time
from pathlib import Path

from .job_budget import task_deadline, WallDeadlineExpired
from .workspace_snapshot import copy_verified_workspace, tree_identity, file_inventory
from .project_contracts import digest
from .project_ledger import ProjectLedger
from .project_runtime import ProjectRuntime
from .project_sessions import ProjectSessions
from .model_session import create_model_session
from .generation_accounting import (count_generation_traces, execution_model_traces,
                                    project_generation_accounting)


def _deliver(output, runtime):
    try:
        result = runtime.run()
    except WallDeadlineExpired:
        result = runtime.result('wall_budget_exhausted')
        result.update(status='interrupted', final=None, model_finished=False, completed=False, acceptance='not_evaluated')
    state = runtime.db.state()
    counts = count_generation_traces(execution_model_traces(output))
    result.update(project_generation_accounting(counts, budget_reserved=state['calls'],
        pending_operation=state['pending'], evidence=state['evidence'].values()))
    termination = ('model_finished' if result['status'] == 'finished' else
                   'budget' if result['termination_reason'] in ('resource_budget_exhausted', 'wall_budget_exhausted',
                       'model_output_budget_exhausted', 'model_input_budget_exhausted') else 'blocked')
    result.update(id=state.get('task_id', output.name), termination=termination,
        source_workspace=state.get('source_workspace'), output_dir=str(output))
    actual = tree_identity(state['workspace'])
    original = json.loads((output / 'INITIAL_TREE.json').read_text())
    result.update(changed_files=sorted(p for p in original.keys() | actual.keys() if original.get(p) != actual.get(p)),
                  final_tree=actual, final_files=file_inventory(actual))
    (output / 'DELIVERY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


@task_deadline
def run_project_job(job, *, settings, session_factory=create_model_session, roles=None):
    started = time.monotonic()
    if type(job.record_generation_snapshots) is not bool:
        raise ValueError('record_generation_snapshots must be boolean')
    output = Path(job.output_dir).resolve()
    source = Path(job.source_workspace).resolve(strict=True)
    if output == source or output in source.parents or source in output.parents:
        raise ValueError('project output overlaps source')
    original = copy_verified_workspace(source, output / 'workspace', audit_path=output / 'SOURCE_COPY.json')
    (output / 'INITIAL_TREE.json').write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n')
    db = ProjectLedger.create(output / 'execution', request=job.request, workspace=output / 'workspace',
        max_calls=job.max_calls, max_seconds=job.max_seconds, protected_paths=job.protected_paths)
    db.update('project_bound', lambda state: state.update(task_id=job.task_id, source_workspace=str(source),
        elapsed=time.monotonic() - started, record_generation_snapshots=job.record_generation_snapshots))
    ports = roles or ProjectSessions(settings, db.root, session_factory=session_factory, max_calls=job.max_calls)
    return _deliver(output, ProjectRuntime(db, ports))


def resume_project(output, *, settings, roles=None):
    """Resume confirmed work with original total budgets; unknown operations stay blocked."""
    output = Path(output).resolve(strict=True)
    db = ProjectLedger(output / 'execution')
    ports = roles or ProjectSessions(settings, db.root, max_calls=db.state()['max_calls'])
    return _deliver(output, ProjectRuntime(db, ports))
