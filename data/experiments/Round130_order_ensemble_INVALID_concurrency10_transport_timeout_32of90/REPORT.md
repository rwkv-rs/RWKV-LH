# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 32
- Case concurrency: 10
- Agent completed: 24
- External acceptance passed: 13
- Strict E2E passed: 13

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 116 | 43 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 35 | 11 | 1 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 97 | 30 | 3 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 11 | 3 | 1 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 32 | 9 | 2 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 38 | 11 | 2 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M09 | medium | medium | PASS | FAIL | FAIL | 155 | 55 | 1 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 20 | 7 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 47 | 15 | 1 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 8 | 1 | 2 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 38 | 10 | 1 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 65 | 20 | 1 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 14 | 4 | 1 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 62 | 21 | 1 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 475 | 199 | 1 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 71 | 9 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 41 | 12 | 2 |
