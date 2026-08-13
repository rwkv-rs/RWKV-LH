# LH-Control-30 Architecture Regression

- Started: `2026-08-13T10:00:38+00:00`
- Finished: `2026-08-13T10:00:41+00:00`
- Passed: `3/30`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-B01 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B02 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B03 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B04 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B05 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B06 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B07 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B08 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B09 | basic | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-B10 | basic | PASS | model_requests_recorded |
| LH-M01 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M02 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M03 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M04 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M05 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M06 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M07 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M08 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M09 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-M10 | medium | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H01 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H02 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H03 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H04 | hard | PASS | lease_competition |
| LH-H05 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H06 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H07 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H08 | hard | PASS | concurrent_model_requests |
| LH-H09 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |
| LH-H10 | hard | FAIL | TypeError: TaskNode.__init__() got an unexpected keyword argument 'goal_criteria' |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
