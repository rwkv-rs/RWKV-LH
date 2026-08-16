# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 30
- Case concurrency: 1
- Agent completed: 15
- External acceptance passed: 12
- Strict E2E passed: 6

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 11 | 1 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | FAIL | FAIL | 24 | 3 | 10 | 1 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 14 | 4 | 5 | 0 |
| E2E-B04 | basic | basic | FAIL | PASS | FAIL | 71 | 4 | 12 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 11 | 1 | 3 | 0 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 19 | 3 | 7 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 12 | 2 | 3 | 0 |
| E2E-B08 | basic | basic | PASS | FAIL | FAIL | 21 | 3 | 10 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 15 | 2 | 2 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 13 | 4 | 2 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 53 | 14 | 18 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 16 | 2 | 2 | 0 |
| E2E-B13 | basic | basic | PASS | PASS | PASS | 47 | 13 | 16 | 0 |
| E2E-B14 | basic | basic | PASS | FAIL | FAIL | 12 | 3 | 4 | 0 |
| E2E-B15 | basic | basic | PASS | FAIL | FAIL | 10 | 2 | 4 | 0 |
| E2E-B16 | basic | basic | PASS | FAIL | FAIL | 51 | 10 | 19 | 0 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 17 | 4 | 6 | 0 |
| E2E-B18 | basic | basic | PASS | FAIL | FAIL | 17 | 3 | 6 | 0 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 97 | 3 | 70 | 1 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 15 | 2 | 3 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 15 | 2 | 2 | 0 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 10 | 2 | 4 | 0 |
| E2E-B23 | basic | basic | PASS | FAIL | FAIL | 13 | 3 | 6 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 17 | 2 | 3 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 15 | 3 | 6 | 0 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 62 | 5 | 26 | 1 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 53 | 14 | 14 | 0 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 109 | 3 | 71 | 1 |
| E2E-B29 | basic | basic | FAIL | PASS | FAIL | 64 | 15 | 25 | 0 |
| E2E-B30 | basic | basic | FAIL | PASS | FAIL | 23 | 6 | 10 | 1 |
