# LH-Control-30 Architecture Regression

- Started: `2026-08-13T01:39:54+00:00`
- Finished: `2026-08-13T01:39:57+00:00`
- Passed: `2/30`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-B01 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 8 |
| LH-B02 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 8 |
| LH-B03 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 12 |
| LH-B04 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 8 |
| LH-B05 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 12 |
| LH-B06 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 8 |
| LH-B07 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 5 |
| LH-B08 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 8 |
| LH-B09 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 1 |
| LH-B10 | basic | FAIL | ConcurrentStateError: stale state revision: expected -1, found 6 |
| LH-M01 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 18 |
| LH-M02 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 17 |
| LH-M03 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 18 |
| LH-M04 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 25 |
| LH-M05 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 9 |
| LH-M06 | medium | PASS | plan_rejected |
| LH-M07 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 13 |
| LH-M08 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 5 |
| LH-M09 | medium | FAIL | ConcurrentStateError: stale state revision: expected -1, found 5 |
| LH-M10 | medium | FAIL | FileExistsError: [Errno 17] File exists: '/home/chase/GitHub/RWKV-LH/data/experiments/Round21_pre_run/lh_control_30/cases/LH-M10/workspace-A' |
| LH-H01 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 6 |
| LH-H02 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 2 |
| LH-H03 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 1 |
| LH-H04 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 0 |
| LH-H05 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 1 |
| LH-H06 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 13 |
| LH-H07 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 13 |
| LH-H08 | hard | PASS | concurrent_model_requests |
| LH-H09 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 67 |
| LH-H10 | hard | FAIL | ConcurrentStateError: stale state revision: expected -1, found 23 |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
