# RWKV-LH ablation: no_model_failure_analysis

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 5
- Strict E2E passed: 3

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | FAIL | FAIL | FAIL | 6 | 3 | 1 | 0 |
| E2E-B02 | basic | FAIL | PASS | FAIL | 22 | 9 | 7 | 0 |
| E2E-B03 | basic | FAIL | FAIL | FAIL | 6 | 3 | 0 | 0 |
| E2E-B04 | basic | PASS | PASS | PASS | 32 | 7 | 7 | 0 |
| E2E-B05 | basic | FAIL | PASS | FAIL | 16 | 4 | 4 | 0 |
| E2E-B06 | basic | FAIL | FAIL | FAIL | 12 | 4 | 2 | 0 |
| E2E-B07 | basic | PASS | PASS | PASS | 26 | 5 | 6 | 0 |
| E2E-B08 | basic | PASS | PASS | PASS | 22 | 4 | 4 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 22 | 5 | 6 | 0 |
| E2E-B10 | basic | FAIL | FAIL | FAIL | 10 | 4 | 2 | 0 |
