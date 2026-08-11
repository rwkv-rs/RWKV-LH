# RWKV-LH ablation: task_local_validation_binding

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 9
- External acceptance passed: 8
- Strict E2E passed: 8

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | PASS | PASS | PASS | 11 | 2 | 2 | 0 |
| E2E-B02 | basic | PASS | PASS | PASS | 109 | 13 | 25 | 0 |
| E2E-B03 | basic | PASS | PASS | PASS | 52 | 8 | 11 | 0 |
| E2E-B04 | basic | PASS | PASS | PASS | 20 | 4 | 4 | 0 |
| E2E-B05 | basic | PASS | PASS | PASS | 31 | 4 | 6 | 0 |
| E2E-B06 | basic | PASS | PASS | PASS | 21 | 4 | 4 | 0 |
| E2E-B07 | basic | PASS | PASS | PASS | 16 | 3 | 3 | 0 |
| E2E-B08 | basic | PASS | PASS | PASS | 35 | 5 | 7 | 0 |
| E2E-B09 | basic | PASS | FAIL | FAIL | 21 | 2 | 4 | 0 |
| E2E-B10 | basic | FAIL | FAIL | FAIL | 43 | 5 | 9 | 0 |
