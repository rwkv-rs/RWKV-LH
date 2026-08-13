# LH-Control-30 Architecture Regression

- Started: `2026-08-13T09:29:57+00:00`
- Finished: `2026-08-13T09:29:59+00:00`
- Passed: `2/2`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-B09 | basic | PASS | context_built |
| LH-M04 | medium | PASS | completed |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
