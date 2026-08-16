# LH-Control-30 Architecture Regression

- Started: `2026-08-14T08:36:33+00:00`
- Finished: `2026-08-14T08:36:34+00:00`
- Passed: `4/4`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-M05 | medium | PASS | completed |
| LH-M09 | medium | PASS | completed |
| LH-H01 | hard | PASS | completed |
| LH-H02 | hard | PASS | blocked |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
