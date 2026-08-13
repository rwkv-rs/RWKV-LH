# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 54
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 15
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | FAIL | FAIL | 12 | 5 | 4 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 22 | 8 | 8 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 12 | 3 | 3 | 0 |
| E2E-B04 | basic | basic | FAIL | PASS | FAIL | 65 | 16 | 16 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 24 | 5 | 5 | 0 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 14 | 5 | 5 | 0 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 22 | 8 | 8 | 0 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 16 | 5 | 5 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 15 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | FAIL | PASS | FAIL | 51 | 15 | 15 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 13 | 4 | 4 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 28 | 7 | 7 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 38 | 12 | 12 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 22 | 9 | 9 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 26 | 6 | 6 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 23 | 7 | 7 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 12 | 4 | 4 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 18 | 10 | 7 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 69 | 30 | 30 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 10 | 2 | 2 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 37 | 11 | 11 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 18 | 7 | 7 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 6 | 6 | 1 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 12 | 6 | 3 | 0 |
| E2E-H09 | hard | hard | FAIL | PASS | FAIL | 22 | 4 | 6 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 12 | 6 | 3 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 29 | 7 | 10 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 12 | 7 | 4 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 38 | 14 | 15 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 30 | 16 | 12 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 21 | 6 | 7 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | PASS | FAIL | 19 | 6 | 7 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 14 | 5 | 5 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 10 | 2 | 2 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 32 | 12 | 12 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 28 | 10 | 10 | 0 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 27 | 7 | 7 | 0 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 10 | 4 | 3 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 18 | 6 | 6 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 13 | 5 | 4 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 6 | 6 | 1 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 10 | 4 | 3 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 9 | 5 | 2 | 0 |
| E2E-B28 | basic | basic | FAIL | FAIL | FAIL | 15 | 4 | 5 | 0 |
