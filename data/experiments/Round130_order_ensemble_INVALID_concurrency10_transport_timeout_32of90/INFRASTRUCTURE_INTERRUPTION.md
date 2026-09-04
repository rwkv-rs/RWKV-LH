# Round130 concurrency-10 attempt — infrastructure invalidation

**Verdict: INVALID; stopped at 32/90. No score is admissible.**

## Evidence

- The run used the frozen Round130 source and case concurrency 10, which permits at most 30 physical
  K=3 candidate requests at once.
- The SSH forwarding unit remained `active/running` with `NRestarts=0`; this was not a tunnel process
  restart.
- Four completed case audits contain `model_transport_failure`: E2E-H05, E2E-H07, E2E-H10, and
  E2E-LH05.
- E2E-LH05 records 16 `RWKVOutcomeUnknownError` events caused by HTTP `ReadTimeout`. It exhausted the
  controller's transport recovery allowance and ended with status `failed` rather than a model Final
  or the normal max-transition boundary.
- The run was stopped immediately after this auditable infrastructure condition was identified. Its
  24 completed, 7 interrupted, and 1 transport-failed cases are retained only for infrastructure
  diagnosis, not quality scoring.

## Root cause and scope

The prior concurrency experiment proved 160/160 successful requests at concurrency 32 using a
bounded diagnostic payload and 96 output tokens. It did not cover the full E2E distribution: growing
long-horizon prompts, action outputs up to 1800 tokens, terminal outputs up to 1400 tokens, and many
sequential K=3 waves. Under that heavier load, case concurrency 10 saturated request latency beyond
the client's read-timeout boundary. Therefore the diagnostic result cannot justify concurrency 10
for the full Round130 workload.

## Successor decision

Rerun the same frozen source and unchanged quality protocol at the original preregistered case
concurrency 5 (at most 15 simultaneous physical requests). The deleted earlier 61/90 concurrency-5
attempt had no case with status `failed`, so concurrency 5 is the strongest already-observed full-E2E
transport setting. Model failures, interrupted cases, and wrong answers remain valid outcomes.
