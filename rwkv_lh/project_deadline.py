"""Cooperative wall budget, including restored projects and nested entry deadlines."""
from contextlib import contextmanager
import signal
import threading
import time

from .job_budget import WallDeadlineExpired


@contextmanager
def project_deadline(seconds):
    if threading.current_thread() is not threading.main_thread():
        raise ValueError('project execution requires a process main thread')
    if seconds <= 0:
        raise WallDeadlineExpired('project wall budget exhausted')
    previous_handler = signal.getsignal(signal.SIGALRM)
    previous_timer = signal.getitimer(signal.ITIMER_REAL)
    allowance = min(seconds, previous_timer[0]) if previous_timer[0] else seconds
    started = time.monotonic()
    def expire(*args):
        raise WallDeadlineExpired('project wall budget exhausted')
    signal.signal(signal.SIGALRM, expire)
    signal.setitimer(signal.ITIMER_REAL, allowance)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        remaining = previous_timer[0] - (time.monotonic() - started)
        if previous_timer[0] and remaining > 0:
            signal.setitimer(signal.ITIMER_REAL, remaining, previous_timer[1])
