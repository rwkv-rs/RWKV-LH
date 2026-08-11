# RWKV-LH ablation: minimal_validation_and_recovery

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 5
- External acceptance passed: 5
- Strict E2E passed: 4

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | PASS | PASS | PASS | 20 | 4 | 5 | 0 |
| E2E-B02 | basic | FAIL | FAIL | FAIL | 10 | 9 | 1 | 0 |
| E2E-B03 | basic | FAIL | FAIL | FAIL | 9 | 3 | 2 | 0 |
| E2E-B04 | basic | PASS | PASS | PASS | 19 | 5 | 5 | 0 |
| E2E-B05 | basic | FAIL | PASS | FAIL | 65 | 12 | 22 | 0 |
| E2E-B06 | basic | PASS | FAIL | FAIL | 25 | 5 | 7 | 0 |
| E2E-B07 | basic | PASS | PASS | PASS | 9 | 2 | 2 | 0 |
| E2E-B08 | basic | PASS | PASS | PASS | 22 | 5 | 6 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 29 | 7 | 8 | 0 |
| E2E-B10 | basic | FAIL | FAIL | FAIL | 16 | 4 | 3 | 0 |
