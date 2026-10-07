"""One cooperative wall deadline across preparation, execution and delivery.

Signals bound Python work and interrupt blocking calls on the process main
thread. Cleanup and evidence persistence may overrun; this is not a hard OS cap.
"""
from .generation_accounting import count_generation_traces, execution_model_traces
from functools import wraps
import json
import math
from pathlib import Path
import signal
import threading
import time


class WallDeadlineExpired(BaseException):
    """Must not be consumed as a recoverable model/protocol error."""


def unresolved_assistance(job):
    return ('strong_takeover' if getattr(job, 'mode', '') == 'takeover' else
            'strong_advised' if getattr(job, 'mode', '') == 'advice' else 'rwkv_independent')


def task_deadline(function):
    @wraps(function)
    def run(job, *args, **kwargs):
        if (type(job.max_seconds) not in (int, float) or not math.isfinite(job.max_seconds)
                or job.max_seconds <= 0 or type(job.max_calls) is not int or job.max_calls < 1):
            raise ValueError('positive finite task budgets required')
        if threading.current_thread() is not threading.main_thread():
            raise ValueError('task deadline requires process main thread')
        output = Path(job.output_dir).resolve()
        if output.exists():
            raise FileExistsError(output)
        started = time.monotonic()
        old_handler = signal.getsignal(signal.SIGALRM)
        old_timer = signal.getitimer(signal.ITIMER_REAL)
        allowance = min(job.max_seconds, old_timer[0]) if old_timer[0] else job.max_seconds
        def expire(signum, frame):
            raise WallDeadlineExpired('wall budget exhausted')
        signal.signal(signal.SIGALRM, expire)
        signal.setitimer(signal.ITIMER_REAL, allowance)
        try:
            result = function(job, *args, **kwargs)
        except WallDeadlineExpired:
            # No invented answer or usage. Recover only already-persisted events.
            counts = count_generation_traces(execution_model_traces(output))
            calls = counts.started
            returned = counts.returned
            if getattr(job, 'mode', '') == 'advice':
                calls = returned = None  # Advice provider usage is separate; not guessed here.
            result = {'id': job.task_id, 'final': None, 'termination': 'budget',
                'termination_reason': 'wall_budget_exhausted', 'acceptance': 'unreviewable',
                'generation_started': calls, 'generation_returned': returned, 'trace_complete': False,
                'assistance': unresolved_assistance(job)}
        finally:
            signal.setitimer(signal.ITIMER_REAL, 0)
            signal.signal(signal.SIGALRM, old_handler)
            remaining = old_timer[0] - (time.monotonic() - started)
            if old_timer[0] and remaining > 0:
                signal.setitimer(signal.ITIMER_REAL, remaining, old_timer[1])
        elapsed = time.monotonic() - started
        result = {**result, 'end_to_end_seconds': elapsed, 'wall_allowance_exceeded': elapsed > allowance}
        if elapsed > allowance:
            result.update(final=None, status='interrupted', termination='budget',
                          termination_reason='wall_budget_exhausted', acceptance='unreviewable')
        output.mkdir(parents=True, exist_ok=True)
        (output / 'DELIVERY.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        return result
    return run
