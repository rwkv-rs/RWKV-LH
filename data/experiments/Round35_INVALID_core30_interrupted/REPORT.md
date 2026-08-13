# RWKV-E2E-30

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 12
- Case concurrency: 1
- Agent completed: 8
- External acceptance passed: 8
- Strict E2E passed: 6

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 6 | 2 | 1 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 3 | 3 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 11 | 3 | 3 | 0 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 13 | 4 | 4 | 0 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 15 | 5 | 5 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 15 | 5 | 5 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 9 | 2 | 2 | 0 |
| E2E-B08 | basic | basic | PASS | FAIL | FAIL | 13 | 4 | 4 | 0 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 14 | 5 | 5 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 18 | 4 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 7 | 9 | 1 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 1 | 0 | 0 | 0 |
