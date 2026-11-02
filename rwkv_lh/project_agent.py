"""Product entry: start a session, recover it, or continue it with the user's next request.

Every entry delivers the same DELIVERY.json shape. A follow-up request continues
the same ledger, conversation and State; it never restarts from a combined prompt.
"""
import json
import time
from pathlib import Path

from .job_budget import task_deadline, WallDeadlineExpired
from .workspace_snapshot import copy_verified_workspace, tree_identity, file_inventory
from .project_ledger import ProjectLedger
from .project_runtime import ProjectRuntime, BUDGET_REASONS
from .project_sessions import ProjectSessions
from .model_session import create_model_session
from .generation_accounting import (count_generation_traces, execution_model_traces,
                                    project_generation_accounting)


def termination(reason):
    """Coarse outcome for scripts: the agent declared, a budget stopped it, or it stopped otherwise."""
    return ('agent_finished' if reason == 'model_finished' else
            'budget' if reason in BUDGET_REASONS else 'stopped')


def _deliver(output, runtime):
    try:
        result = runtime.run()
    except WallDeadlineExpired:
        result = runtime.result('wall_budget_exhausted')
        result.update(status='interrupted', model_finished=False, completed=False, acceptance='not_evaluated')
    state = runtime.db.state()
    counts = count_generation_traces(execution_model_traces(output))
    result.update(project_generation_accounting(counts, budget_reserved=state['calls'],
        pending_operation=state['pending'], evidence=state['evidence'].values()))
    result.update(id=state.get('task_id', output.name), termination=termination(result['termination_reason']),
        source_workspace=state.get('source_workspace'), output_dir=str(output))
    actual = tree_identity(state['workspace'])
    original = json.loads((output / 'INITIAL_TREE.json').read_text())
    result.update(changed_files=sorted(p for p in original.keys() | actual.keys() if original.get(p) != actual.get(p)),
                  final_tree=actual, final_files=file_inventory(actual))
    (output / 'DELIVERY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
    return result


@task_deadline
def run_project_job(job, *, settings, session_factory=create_model_session, agent_port=None):
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
        max_calls=job.max_calls, max_seconds=job.max_seconds, writable=job.writable_paths,
        protected_paths=job.protected_paths, rejection_limit=job.rejection_limit)
    db.update('project_bound', lambda state: state.update(task_id=job.task_id, source_workspace=str(source),
        elapsed=time.monotonic() - started, record_generation_snapshots=job.record_generation_snapshots))
    port = agent_port or ProjectSessions(settings, db.root, session_factory=session_factory)
    return _deliver(output, ProjectRuntime(db, port))


def resume_project(output, *, settings, agent_port=None):
    """Recover confirmed work of the current request; unknown operations stay blocked."""
    output = Path(output).resolve(strict=True)
    db = ProjectLedger(output / 'execution')
    port = agent_port or ProjectSessions(settings, db.root)
    return _deliver(output, ProjectRuntime(db, port))


def continue_project(output, request, *, settings, extra_calls=0, extra_seconds=0.0, agent_port=None):
    """The user's follow-up request in the same session, State and workspace."""
    output = Path(output).resolve(strict=True)
    db = ProjectLedger(output / 'execution')
    with db.lease():
        db.add_request(request, extra_calls=extra_calls, extra_seconds=extra_seconds)
    port = agent_port or ProjectSessions(settings, db.root)
    return _deliver(output, ProjectRuntime(db, port))
