"""Schedule independent direct Agent jobs; no planning, State sharing or integration."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from multiprocessing import get_context
from pathlib import Path
import math
from .job_budget import unresolved_assistance


def _execute(job, settings):
    from .agent_integration import DependentJob, run_dependent_job
    if isinstance(job, DependentJob):
        return run_dependent_job(job, settings=settings)
    from .goal_delivery import GoalJob, run_goal_job
    from .assisted_agent import AssistedJob, run_assisted_job
    from .coding_agent import CodingJob, run_coding_job
    from .read_only_agent import run_read_only_job
    if isinstance(job, GoalJob):
        return run_goal_job(job, settings=settings)
    if isinstance(job, AssistedJob):
        return run_assisted_job(job, settings=settings)
    if isinstance(job, CodingJob):
        return run_coding_job(job, settings=settings)
    return run_read_only_job(job, settings=settings)


def _save_failure(job, result):
    from .read_only_agent import _save
    try:
        output = Path(job.output_dir)
        output.mkdir(parents=True, exist_ok=True)
        _save(output / 'BATCH_ERROR.json', result)
    except Exception as exc:
        result['report_persistence_error'] = {'type': type(exc).__name__, 'message': str(exc)}
    return result


def _worker(arguments):
    job, settings = arguments
    try:
        return _execute(job, settings)
    except Exception as exc:
        return _save_failure(job, {'id': job.task_id, 'final': None, 'termination': 'error',
                'termination_reason': 'job_dispatch_failed', 'acceptance': 'unreviewable',
                'generation_started': None, 'trace_complete': False,
                'assistance': unresolved_assistance(job),
                'error': {'type': type(exc).__name__, 'message': str(exc)},
                'output_dir': str(job.output_dir)})


def _overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def validate_agent_jobs(jobs, *, concurrency=1):
    """Preflight all jobs, then execute whole tasks in separate processes.

    Coding jobs copy their source; read-only jobs do not mutate their source.
    Shared input snapshots are allowed. Outputs cannot overlap any input or
    other output. No result is automatically merged or marked accepted.
    """
    from .assisted_agent import AssistedJob, load_parent
    from .coding_agent import CodingJob
    from .read_only_agent import ReadOnlyJob
    from .goal_delivery import GoalJob, validate_goal_job
    jobs = list(jobs)
    if type(concurrency) is not int or concurrency < 1:
        raise ValueError('positive integer concurrency required')
    if not all(isinstance(job, (CodingJob, ReadOnlyJob, AssistedJob)) for job in jobs):
        raise ValueError('unsupported Agent job')
    if len({job.task_id for job in jobs}) != len(jobs):
        raise ValueError('duplicate task IDs')
    sources = []
    for job in jobs:
        if isinstance(job, GoalJob):
            validate_goal_job(job)
        if not str(job.task_id).strip() or not str(job.request).strip():
            raise ValueError('task ID and request are required')
        if (type(job.max_calls) is not int or job.max_calls < 1
                or type(job.max_seconds) not in (int, float)
                or not math.isfinite(job.max_seconds) or job.max_seconds <= 0):
            raise ValueError('positive finite task budgets required')
        if isinstance(job, AssistedJob):
            previous, _, _, source = load_parent(job)
            sources.append(previous)
        elif isinstance(job, ReadOnlyJob):
            if job.tool_scope not in ('files', 'inspect'):
                raise ValueError('unknown read-only tool scope')
            source = Path(job.workspace).resolve()
        else:
            source = Path(job.source_workspace).resolve()
        if not source.is_dir():
            raise ValueError('source workspace must be an existing directory')
        sources.append(source)
    outputs = [Path(job.output_dir).resolve() for job in jobs]
    for index, output in enumerate(outputs):
        if any(_overlap(output, source) for source in sources):
            raise ValueError('audit output overlaps a task workspace')
        if any(_overlap(output, other) for other in outputs[:index]):
            raise ValueError('overlapping task outputs')
        if output.exists():
            raise FileExistsError(output)
    return jobs


def run_agent_jobs(jobs, *, settings, concurrency=1):
    jobs = validate_agent_jobs(jobs, concurrency=concurrency)
    if concurrency == 1:
        return [_worker((job, settings)) for job in jobs]
    results = [None] * len(jobs)
    def lost(index, exc):
        job = jobs[index]
        results[index] = _save_failure(job, {'id': job.task_id, 'final': None, 'termination': 'error',
            'termination_reason': 'worker_process_lost', 'acceptance': 'unreviewable',
            'generation_started': None, 'trace_complete': False,
            'assistance': unresolved_assistance(job),
            'output_dir': str(job.output_dir),
            'error': {'type': type(exc).__name__, 'message': str(exc)}})
    try:
        executor = ProcessPoolExecutor(max_workers=concurrency, mp_context=get_context('spawn'))
    except Exception as exc:
        for index in range(len(jobs)):
            lost(index, exc)
        return results
    with executor as pool:
        futures = {}
        for index, job in enumerate(jobs):
            try:
                futures[pool.submit(_worker, (job, settings))] = index
            except Exception as exc:
                lost(index, exc)
        for future in as_completed(futures):
            index = futures[future]
            try:
                results[index] = future.result()
            except Exception as exc:
                lost(index, exc)
    return results
