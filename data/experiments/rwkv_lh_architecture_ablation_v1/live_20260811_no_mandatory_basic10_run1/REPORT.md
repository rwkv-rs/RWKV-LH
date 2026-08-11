# RWKV-LH ablation: no_mandatory_model_cross_check

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 5
- External acceptance passed: 6
- Strict E2E passed: 5

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | PASS | PASS | PASS | 13 | 3 | 3 | 0 |
| E2E-B02 | basic | PASS | PASS | PASS | 10 | 2 | 2 | 0 |
| E2E-B03 | basic | PASS | PASS | PASS | 12 | 3 | 3 | 0 |
| E2E-B04 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B05 | basic | FAIL | PASS | FAIL | 43 | 4 | 8 | 0 |
| E2E-B06 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B07 | basic | PASS | PASS | PASS | 11 | 2 | 2 | 0 |
| E2E-B08 | basic | PASS | PASS | PASS | 14 | 3 | 3 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 76 | 10 | 17 | 0 |
| E2E-B10 | basic | FAIL | FAIL | FAIL | 9 | 4 | 1 | 0 |
