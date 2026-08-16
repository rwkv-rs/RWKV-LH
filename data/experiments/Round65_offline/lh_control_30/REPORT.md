# LH-Control-30 Architecture Regression

- Started: `2026-08-14T03:10:48+00:00`
- Finished: `2026-08-14T03:10:56+00:00`
- Passed: `30/30`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-B01 | basic | PASS | completed |
| LH-B02 | basic | PASS | completed |
| LH-B03 | basic | PASS | completed |
| LH-B04 | basic | PASS | completed |
| LH-B05 | basic | PASS | completed |
| LH-B06 | basic | PASS | completed |
| LH-B07 | basic | PASS | blocked |
| LH-B08 | basic | PASS | completed |
| LH-B09 | basic | PASS | context_built |
| LH-B10 | basic | PASS | model_requests_recorded |
| LH-M01 | medium | PASS | completed |
| LH-M02 | medium | PASS | completed |
| LH-M03 | medium | PASS | completed |
| LH-M04 | medium | PASS | completed |
| LH-M05 | medium | PASS | completed |
| LH-M06 | medium | PASS | plan_rejected |
| LH-M07 | medium | PASS | completed |
| LH-M08 | medium | PASS | blocked |
| LH-M09 | medium | PASS | blocked |
| LH-M10 | medium | PASS | concurrent_runs_finished |
| LH-H01 | hard | PASS | completed |
| LH-H02 | hard | PASS | blocked |
| LH-H03 | hard | PASS | checkpoint_recovered |
| LH-H04 | hard | PASS | lease_competition |
| LH-H05 | hard | PASS | context_built |
| LH-H06 | hard | PASS | completed |
| LH-H07 | hard | PASS | completed |
| LH-H08 | hard | PASS | concurrent_model_requests |
| LH-H09 | hard | PASS | completed |
| LH-H10 | hard | PASS | completed |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
