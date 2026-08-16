# RWKV-E2E-30

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 13
- Case concurrency: 1
- Agent completed: 11
- External acceptance passed: 8
- Strict E2E passed: 8

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 3 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 3 | 2 | 0 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 7 | 5 | 1 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 4 | 2 | 1 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 4 | 2 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 142 | 130 | 11 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 9 | 8 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 3 | 2 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 4 | 3 | 0 |
