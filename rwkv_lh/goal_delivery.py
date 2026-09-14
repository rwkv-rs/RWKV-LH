"""Opt-in bounded RWKV-first delivery; terminal routing has no acceptance authority."""
from dataclasses import dataclass
import math
from pathlib import Path
import time

from .coding_agent import CodingJob, run_coding_job
from .assisted_agent import AssistedJob, run_assisted_job
from .read_only_agent import _save


@dataclass(frozen=True)
class GoalJob(CodingJob):
    # max_calls is the total model generation ceiling, not a per-stage allowance.
    rwkv_max_calls: int = 8


STALL_REASONS = frozenset({'generation_budget_exhausted', 'transition_budget_exhausted',
                           'identical_success_budget_exhausted'})


def validate_goal_job(job):
    if (type(job.rwkv_max_calls) is not int or job.rwkv_max_calls < 1
            or type(job.max_calls) is not int or job.max_calls < job.rwkv_max_calls
            or type(job.max_seconds) not in (int, float)
            or not math.isfinite(job.max_seconds) or job.max_seconds <= 0):
        raise ValueError('positive goal budgets required; RWKV allowance cannot exceed total')


def run_goal_job(job, *, settings):
    """Attempt RWKV, then at most one takeover on a recorded no-delivery stall.

    No semantic grading or hidden tests enter routing. A submission is returned
    unchanged for external review. Wall allowance is reduced by elapsed time;
    preparation/cleanup overrun is recorded, not presented as a hard process cap.
    """
    validate_goal_job(job)
    root = Path(job.output_dir).resolve()
    source = Path(job.source_workspace).resolve(strict=True)
    if root == source or root in source.parents or source in root.parents:
        raise ValueError('goal output overlaps source')
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    stages = []
    policy = {'allowed_stall_reasons': sorted(STALL_REASONS), 'max_calls': job.max_calls,
              'rwkv_max_calls': job.rwkv_max_calls, 'max_seconds': job.max_seconds,
              'max_takeovers': 1, 'acceptance_authority': False}
    _save(root / 'POLICY.json', policy)
    first = CodingJob(job.task_id, job.request, str(source), str(root / 'rwkv'),
                      job.rwkv_max_calls, job.max_seconds)
    selected = run_coding_job(first, settings=settings)
    stages.append({'directory': str(root / 'rwkv'), 'assistance': 'rwkv_independent',
                   'termination': selected['termination'], 'reason': selected['termination_reason'],
                   'model_calls': selected['generation_started']})
    spent = selected['generation_started']
    remaining_seconds = job.max_seconds - (time.monotonic() - started)
    eligible = (selected['final'] is None and selected['termination'] == 'budget'
                and selected['termination_reason'] in STALL_REASONS
                and selected.get('trace_complete') is True
                and spent < job.max_calls and remaining_seconds > 0)
    _save(root / 'ROUTING.json', {'takeover': eligible, 'trigger': selected['termination_reason'],
          'remaining_calls': job.max_calls-spent, 'remaining_seconds': max(0, remaining_seconds)})
    if eligible:
        child = AssistedJob(job.task_id + '-takeover', str(root / 'rwkv' / 'execution'),
                            str(root / 'takeover'), 'takeover', job.max_calls-spent, remaining_seconds)
        try:
            selected = run_assisted_job(child, settings=settings)
        except Exception as exc:
            selected = {'id': child.task_id, 'final': None, 'termination': 'error',
                        'termination_reason': 'takeover_failed', 'assistance': 'strong_takeover',
                        'acceptance': 'not_evaluated', 'generation_started': None,
                        'error': {'type': type(exc).__name__, 'message': str(exc)}}
        count = selected['generation_started']
        stages.append({'directory': str(root / 'takeover'), 'assistance': 'strong_takeover',
                       'termination': selected['termination'], 'reason': selected['termination_reason'],
                       'model_calls': count})
        spent = spent + count if count is not None else None
    elapsed = time.monotonic() - started
    delivery = {**selected, 'workflow': {'id': job.task_id, 'policy': policy, 'stages': stages,
                'model_calls': spent, 'end_to_end_seconds': elapsed,
                'wall_allowance_exceeded': elapsed > job.max_seconds}}
    _save(root / 'DELIVERY.json', delivery)
    return delivery
