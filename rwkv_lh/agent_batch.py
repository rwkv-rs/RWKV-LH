"""Schedule independent direct Agent jobs; no planning, State sharing or integration."""
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from pathlib import Path
import math


def _execute(job, settings):
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


def _worker(arguments):
    job, settings = arguments
    try:
        return _execute(job, settings)
    except Exception as exc:
        return {'id': job.task_id, 'final': None, 'termination': 'error',
                'termination_reason': 'job_dispatch_failed', 'acceptance': 'not_evaluated',
                'assistance': ('strong_takeover' if getattr(job, 'mode', '') == 'takeover' else
                               'strong_advised' if getattr(job, 'mode', '') == 'advice' else 'rwkv_independent'),
                'error': {'type': type(exc).__name__, 'message': str(exc)},
                'output_dir': str(job.output_dir)}


def _overlap(a, b):
    return a == b or a in b.parents or b in a.parents


def run_agent_jobs(jobs, *, settings, concurrency=1):
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
    if concurrency == 1:
        return [_worker((job, settings)) for job in jobs]
    with ProcessPoolExecutor(max_workers=concurrency, mp_context=get_context('spawn')) as pool:
        return list(pool.map(_worker, [(job, settings) for job in jobs]))
