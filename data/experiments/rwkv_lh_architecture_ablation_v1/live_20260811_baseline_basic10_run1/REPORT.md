# RWKV-LH ablation: baseline

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 1
- External acceptance passed: 3
- Strict E2E passed: 1

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | PASS | PASS | PASS | 21 | 4 | 4 | 0 |
| E2E-B02 | basic | FAIL | PASS | FAIL | 19 | 7 | 3 | 0 |
| E2E-B03 | basic | FAIL | FAIL | FAIL | 38 | 4 | 6 | 0 |
| E2E-B04 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B05 | basic | FAIL | PASS | FAIL | 86 | 9 | 16 | 0 |
| E2E-B06 | basic | FAIL | FAIL | FAIL | 20 | 4 | 3 | 0 |
| E2E-B07 | basic | FAIL | FAIL | FAIL | 51 | 5 | 9 | 0 |
| E2E-B08 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 93 | 7 | 15 | 0 |
| E2E-B10 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
