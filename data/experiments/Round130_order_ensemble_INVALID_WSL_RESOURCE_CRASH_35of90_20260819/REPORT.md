# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 35
- Case concurrency: 5
- Agent completed: 26
- External acceptance passed: 14
- Strict E2E passed: 14

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 283 | 101 | 3 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 559 | 197 | 3 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 5 | 2 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 17 | 4 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 26 | 3 | 2 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 103 | 32 | 4 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 11 | 3 | 1 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 26 | 8 | 1 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 17 | 5 | 1 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 41 | 12 | 2 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M09 | medium | medium | PASS | FAIL | FAIL | 79 | 27 | 1 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 20 | 7 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 81 | 28 | 1 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 347 | 189 | 11 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 8 | 1 | 2 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 1 | 0 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 26 | 9 | 0 |
| E2E-H07 | hard | hard | PASS | FAIL | FAIL | 44 | 13 | 2 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 538 | 199 | 1 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 11 | 4 | 0 |
| E2E-H10 | hard | hard | PASS | PASS | PASS | 23 | 8 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 475 | 199 | 1 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 527 | 190 | 10 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 474 | 167 | 5 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 344 | 127 | 12 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 41 | 12 | 2 |
