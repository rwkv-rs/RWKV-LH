# LH-Control-30 Architecture Regression

- Started: `2026-08-13T12:44:59+00:00`
- Finished: `2026-08-13T12:45:09+00:00`
- Passed: `12/30`
- Scope: deterministic architecture fixtures for Controller, persistence, verification, recovery, idempotency, dependency, scope and request-level sampling regressions.
- Non-claim: this result does not show that RWKV independently planned and completed 30 long-horizon tasks.

| Task | Level | Result | Actual |
| --- | --- | --- | --- |
| LH-B01 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B02 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B03 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B04 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B05 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B06 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B07 | basic | PASS | blocked |
| LH-B08 | basic | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-B09 | basic | PASS | context_built |
| LH-B10 | basic | PASS | model_requests_recorded |
| LH-M01 | medium | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-M02 | medium | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-M03 | medium | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-M04 | medium | PASS | completed |
| LH-M05 | medium | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-M06 | medium | PASS | plan_rejected |
| LH-M07 | medium | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-M08 | medium | PASS | blocked |
| LH-M09 | medium | PASS | blocked |
| LH-M10 | medium | FAIL | KeyError: 'LH-M10-A' |
| LH-H01 | hard | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-H02 | hard | PASS | blocked |
| LH-H03 | hard | PASS | checkpoint_recovered |
| LH-H04 | hard | PASS | lease_competition |
| LH-H05 | hard | PASS | context_built |
| LH-H06 | hard | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-H07 | hard | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-H08 | hard | PASS | concurrent_model_requests |
| LH-H09 | hard | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |
| LH-H10 | hard | FAIL | TypeError: FixtureProofModel.commit_criterion_evidence() got an unexpected keyword argument 'criterion_ids' |

Detailed event, tool, retry, temperature, recovery, and verification data is stored in `results.json` and each case JSON.
