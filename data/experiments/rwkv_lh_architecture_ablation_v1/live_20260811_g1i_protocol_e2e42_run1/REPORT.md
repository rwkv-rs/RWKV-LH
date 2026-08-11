# RWKV-E2E-42

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 42
- Case concurrency: 8
- Agent completed: 7
- External acceptance passed: 5
- Strict E2E passed: 5

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | FAIL | FAIL | FAIL | 7 | 3 | 1 | 0 |
| E2E-B02 | basic | PASS | PASS | PASS | 18 | 5 | 5 | 0 |
| E2E-B03 | basic | FAIL | FAIL | FAIL | 16 | 5 | 3 | 0 |
| E2E-B04 | basic | PASS | PASS | PASS | 18 | 5 | 5 | 0 |
| E2E-B05 | basic | FAIL | FAIL | FAIL | 8 | 3 | 1 | 0 |
| E2E-B06 | basic | PASS | PASS | PASS | 13 | 3 | 3 | 0 |
| E2E-B07 | basic | PASS | PASS | PASS | 39 | 7 | 11 | 0 |
| E2E-B08 | basic | FAIL | FAIL | FAIL | 5 | 4 | 0 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 13 | 2 | 3 | 0 |
| E2E-B10 | basic | PASS | PASS | PASS | 35 | 6 | 10 | 0 |
| E2E-M01 | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M02 | medium | FAIL | FAIL | FAIL | 8 | 6 | 1 | 0 |
| E2E-M03 | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M04 | medium | FAIL | FAIL | FAIL | 13 | 7 | 2 | 0 |
| E2E-M05 | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M06 | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | PASS | FAIL | FAIL | 16 | 4 | 4 | 0 |
| E2E-M08 | medium | FAIL | FAIL | FAIL | 17 | 3 | 3 | 0 |
| E2E-M09 | medium | FAIL | FAIL | FAIL | 12 | 8 | 2 | 0 |
| E2E-M10 | medium | FAIL | FAIL | FAIL | 8 | 4 | 1 | 0 |
| E2E-H01 | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H02 | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | PASS | FAIL | FAIL | 28 | 8 | 8 | 0 |
| E2E-H04 | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H05 | hard | FAIL | FAIL | FAIL | 9 | 5 | 1 | 0 |
| E2E-H06 | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H07 | hard | FAIL | FAIL | FAIL | 4 | 5 | 0 | 0 |
| E2E-H08 | hard | FAIL | FAIL | FAIL | 8 | 3 | 1 | 0 |
| E2E-H09 | hard | FAIL | FAIL | FAIL | 15 | 5 | 3 | 0 |
| E2E-H10 | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH01 | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH02 | long_horizon | FAIL | FAIL | FAIL | 8 | 21 | 1 | 0 |
| E2E-LH03 | long_horizon | FAIL | FAIL | FAIL | 10 | 5 | 2 | 0 |
| E2E-LH04 | long_horizon | FAIL | FAIL | FAIL | 17 | 5 | 3 | 0 |
| E2E-LH05 | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | long_horizon | FAIL | FAIL | FAIL | 5 | 7 | 0 | 0 |
| E2E-LH07 | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH08 | long_horizon | FAIL | FAIL | FAIL | 8 | 19 | 1 | 0 |
| E2E-LH09 | long_horizon | FAIL | FAIL | FAIL | 4 | 5 | 0 | 0 |
| E2E-LH10 | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH11 | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH12 | long_horizon | FAIL | FAIL | FAIL | 45 | 13 | 13 | 0 |
