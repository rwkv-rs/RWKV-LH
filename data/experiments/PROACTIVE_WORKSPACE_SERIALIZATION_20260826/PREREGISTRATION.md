# Proactive workspace serialization preregistration

- Date: 2026-08-26
- Version: `rwkv-lh.proactive-workspace-serialization.v1`
- Purpose: prevent different proactive jobs from executing concurrently against
  one mutable workspace, and prevent interval triggers from accumulating new
  occurrences while an earlier occurrence is still non-terminal.
- Dataset: deterministic SQLite lifecycle fixtures in `tests/test_proactive.py`;
  no model-generated or external evaluation data is used.
- Source: proactive control-plane audit after the protocol-boundary remediation.

## Frozen behavior

1. One optional persisted `concurrency_key` is attached to a job and inherited
   by interval occurrences.
2. At most one unexpired running lease may exist for a non-empty key. Jobs with
   different keys and jobs without a key retain the existing scheduling behavior.
3. A worker holds one process-safe local file lock for the non-empty key across
   the complete handler call. If a stale worker remains alive after its SQLite
   lease expires, a takeover worker may renew its new lease while waiting but
   cannot overlap the stale handler's workspace side effects. Process death
   releases this lock through the operating system.
4. The product CLI derives the key only from the resolved workspace path; it
   does not parse task text or choose model actions.
5. If an interval occurrence becomes due while an earlier occurrence from that
   trigger is queued, awaiting approval, running, or awaiting retry, the new
   occurrence is coalesced and the trigger advances to its next future time.
6. Coalescing produces a lifecycle notification and never changes the earlier
   job payload, run ID, attempts, approval, or lease.
7. Existing proactive v1 SQLite databases migrate additively; unknown schema
   versions continue to fail closed.

## Fixed validation

- Exact state/notification assertions for same-key serialization, different-key
  parallel claim, process-safe handler exclusion, interval coalescing, and v1
  database migration.
- Existing proactive lifecycle regression must remain green.
- Complete repository pytest, Python compilation, and `git diff --check` must pass.
- Acceptance threshold: every registered assertion passes (`1.0`); no partial
  credit or post-run change to the behavior above.
