# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 55
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 9
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | FAIL | FAIL | 8 | 4 | 1 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 10 | 3 | 2 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 36 | 14 | 14 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 6 | 7 | 0 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 12 | 4 | 4 | 0 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 12 | 5 | 3 | 0 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 10 | 4 | 2 | 0 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 12 | 4 | 4 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 12 | 2 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 12 | 4 | 3 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 12 | 4 | 3 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 12 | 4 | 3 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 14 | 5 | 4 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 18 | 7 | 4 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 20 | 6 | 6 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 14 | 9 | 4 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 16 | 6 | 6 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 6 | 6 | 0 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 16 | 7 | 5 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 16 | 10 | 5 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 21 | 8 | 7 | 0 |
| E2E-H04 | hard | hard | FAIL | FAIL | FAIL | 8 | 2 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 32 | 14 | 14 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 8 | 5 | 1 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 10 | 3 | 2 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 10 | 8 | 2 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 8 | 7 | 1 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 11 | 9 | 3 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 44 | 20 | 20 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 12 | 6 | 4 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 6 | 10 | 0 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 30 | 14 | 12 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 30 | 11 | 12 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 11 | 7 | 2 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 14 | 5 | 5 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 7 | 5 | 0 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 13 | 9 | 4 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 20 | 8 | 8 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 38 | 16 | 16 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 19 | 4 | 4 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 10 | 2 | 1 | 0 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 16 | 6 | 5 | 0 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 21 | 8 | 7 | 0 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 10 | 3 | 2 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 12 | 5 | 4 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 10 | 3 | 3 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 4 | 5 | 0 | 0 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 5 | 3 | 1 | 0 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 4 | 4 | 0 | 0 |
