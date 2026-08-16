# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 30
- Case concurrency: 1
- Agent completed: 30
- External acceptance passed: 21
- Strict E2E passed: 21

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 3 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 10 | 8 | 1 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 4 | 2 | 1 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 4 | 2 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 38 | 33 | 4 |
| E2E-B11 | basic | basic | PASS | FAIL | FAIL | 4 | 2 | 1 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B13 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B14 | basic | basic | PASS | FAIL | FAIL | 6 | 4 | 1 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 4 | 3 | 0 |
| E2E-B16 | basic | basic | PASS | FAIL | FAIL | 5 | 3 | 1 |
| E2E-B17 | basic | basic | PASS | FAIL | FAIL | 5 | 3 | 1 |
| E2E-B18 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 4 | 2 | 1 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 7 | 5 | 1 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 5 | 3 | 1 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 4 | 3 | 0 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 6 | 4 | 1 |
| E2E-B24 | basic | basic | PASS | FAIL | FAIL | 4 | 2 | 1 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 5 | 4 | 0 |
| E2E-B26 | basic | basic | PASS | PASS | PASS | 10 | 8 | 1 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 4 | 2 | 1 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 4 | 2 | 1 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 8 | 5 | 2 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 6 | 5 | 0 |
