# R130 per-case worker-recycle amendment

**Recorded:** 2026-08-20, before the successor run's first model request.

## Root cause

Reducing case concurrency from 5 to 2 prevented an immediate WSL crash but did not bound retained
memory across the full suite. `ProcessPoolExecutor` reused the same worker process for successive
cases. Large per-case model histories and SQLite-backed state were released logically, but Python's
worker heap remained resident. The concurrency-2 attempt eventually reached about 15.8 GB resident
memory plus 8 GB swap and became memory-cgroup throttled at 30/90.

## Successor scheduling

The successor run uses:

- case concurrency **1**;
- a spawned process worker even at concurrency 1;
- `max_tasks_per_child=1`, forcing the worker to exit after every case so all case-local heap and
  SQLite resources return to the operating system before the next case starts;
- systemd `CPUQuota=300%`, `MemoryHigh=12G`, and `MemoryMax=16G`;
- a fresh output directory; no prior result or workspace is resumed.

This changes only local worker scheduling and lifecycle. Model, frozen architecture, prompts, K=3
order ensemble, suite, sampling, maximum transitions, acceptance, scoring, thresholds, and red lines
remain unchanged. The runner's suite result remains ordered by the preregistered catalog rather than
worker completion order.

## Validity gate

Before the Full90, the executor path must prove that multiple submitted tasks complete with a distinct
worker PID per task while preserving submitted-task result ordering. The source manifest is then
regenerated and checked before the first model request.
