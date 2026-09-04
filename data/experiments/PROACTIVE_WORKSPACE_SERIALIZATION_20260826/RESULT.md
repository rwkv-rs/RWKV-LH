# Proactive workspace serialization result

- Date: 2026-08-26 (Asia/Shanghai)
- Protocol: `rwkv-lh.proactive-workspace-serialization.v1`
- Registered metric: exact deterministic state and notification assertions
- Required threshold: `1.0`
- Observed score: `1.0`
- Outcome: passed

## Root causes and system impact

1. The Controller lease is scoped to one run ID, while separate proactive jobs
   receive separate run IDs. Two workers could therefore claim different jobs
   targeting the same mutable workspace and execute conflicting side effects.
2. Interval triggers materialized every elapsed occurrence even while an earlier
   occurrence was awaiting approval, queued, running, or awaiting retry. A slow or
   blocked run could accumulate an unbounded backlog against the same workspace.
3. SQLite lease fencing prevented a stale worker from writing a job terminal state,
   but lease expiry alone could not stop that worker's still-live handler from
   overlapping a takeover handler's workspace side effects.

The common control-plane fix persists a product-derived concurrency key on jobs and
triggers, serializes claims for an unexpired key, and holds a WSL/Linux process lock
for that key across the complete handler call. A takeover may renew its new SQLite
lease while waiting, but cannot enter the workspace handler until the stale live
handler exits or its process dies. Interval occurrences are coalesced while their
prior occurrence is non-terminal and emit an auditable notification. Existing v1
databases receive an additive v2 migration; unknown versions still fail closed.

The key is derived mechanically from the resolved workspace path. No prompt,
RWKV action choice, retrieval decision, tool argument, evidence, or final answer is
created or rewritten by this control-plane logic.

## Registered regression coverage

- Same concurrency key cannot hold two unexpired running leases.
- Different keys retain independent claim behavior.
- A real child process holds the handler lock against the parent; terminating that
  child releases the OS lock and lets the waiting takeover enter.
- Interval triggers coalesce queued/non-terminal occurrences and preserve one job.
- Coalescing records the active job, status, skipped schedule, and next fire time.
- Trigger occurrences inherit their persisted concurrency key.
- A proactive v1 SQLite database migrates both trigger and job tables to v2.
- Existing approval, retry, dead-letter, takeover fencing, and completion behavior
  remains green.

## Validation record

- Final focused proactive lifecycle:
  `uv run pytest -q -s tests/test_proactive.py` — 16 passed in 3.44 seconds.
- Related proactive, UI, and retrieval paths:
  `uv run pytest -q -s tests/test_proactive.py tests/test_web_ui.py tests/test_retrieval_harness.py tests/test_retrieval_kernel.py`
  — 50 passed in 9.58 seconds.
- Complete repository suite after the final changes:
  `uv run pytest -q -s` — 259 passed in 54.91 seconds.
- Unified Controller product entry point:
  `uv run rwkv-lh-control` — 77 passed in 14.49 seconds.
- Frozen complete benchmark catalog:
  `uv run rwkv-lh-e2e --suite all --validate-only` — `RWKV-E2E-90`,
  90 total, 90 selected, catalog valid.
- Python import/bytecode boundary:
  `uv run python -m compileall -q rwkv_lh scripts tests` — passed.
- Product CLI persistence smoke: an offline one-shot enqueue stored the resolved
  workspace in both the immutable payload and
  `concurrency_key=workspace:<resolved-path>`; `jobs` read the same value back.
- `git diff --check` — passed before this result record and repeated after it.

## Completion decision and model gate

The deterministic engineering harness is ready for another frozen model canary:
the complete repository regression, product entry points, migration, concurrency,
recovery-related lifecycle, dataset catalog, and compilation boundaries are green.

This result does not override the preregistered model-quality gate. The latest R9
route canary remains `FAILED_GATE` (5/7 completed, first-tool exact 5/7,
network/non-network Macro-F1 0.7083, and two failed/unavailable cases), so route120
and real-model Full90 were intentionally not started. Those failures remain state
tuning / Strong Planner contract-data inputs rather than deterministic harness
defects. A new state-tuned checkpoint must first pass the frozen Canary gate before
formal route120 or Full90 execution.
