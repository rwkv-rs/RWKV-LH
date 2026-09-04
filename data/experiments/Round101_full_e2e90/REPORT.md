# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 4
- Agent completed: 32
- External acceptance passed: 21
- Strict E2E passed: 12

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 7 | 1 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 2 | 4 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 12 | 3 | 5 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 50 | 4 | 11 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 15 | 3 | 5 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 16 | 3 | 8 | 0 |
| E2E-B07 | basic | basic | PASS | FAIL | FAIL | 13 | 3 | 5 | 0 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 13 | 3 | 6 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 12 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 54 | 4 | 9 | 0 |
| E2E-M01 | medium | medium | FAIL | PASS | FAIL | 81 | 5 | 61 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 11 | 3 | 2 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 54 | 3 | 10 | 0 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 161 | 7 | 26 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 7 | 3 | 1 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 12 | 4 | 8 | 0 |
| E2E-M07 | medium | medium | PASS | FAIL | FAIL | 17 | 3 | 9 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 13 | 3 | 5 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 32 | 4 | 11 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 8 | 1 | 1 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 19 | 3 | 4 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 40 | 1 | 21 | 0 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 43 | 6 | 13 | 0 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 7 | 1 | 2 | 0 |
| E2E-H05 | hard | hard | PASS | FAIL | FAIL | 32 | 3 | 20 | 0 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 14 | 1 | 10 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 13 | 6 | 3 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 12 | 1 | 2 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 14 | 4 | 6 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 23 | 6 | 9 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 25 | 4 | 6 | 0 |
| E2E-LH02 | hard | long_horizon | PASS | FAIL | FAIL | 9 | 1 | 2 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 4 | 11 | 0 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 9 | 1 | 5 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 28 | 4 | 13 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 18 | 6 | 4 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 7 | 0 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 3 | 9 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 15 | 4 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 22 | 5 | 6 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 167 | 8 | 138 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 6 | 1 | 3 | 0 |
| E2E-B11 | basic | basic | PASS | FAIL | FAIL | 11 | 2 | 6 | 0 |
| E2E-B12 | basic | basic | FAIL | PASS | FAIL | 14 | 2 | 6 | 0 |
| E2E-B13 | basic | basic | PASS | PASS | PASS | 15 | 3 | 6 | 0 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 18 | 4 | 8 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 31 | 3 | 6 | 0 |
| E2E-B16 | basic | basic | PASS | FAIL | FAIL | 14 | 3 | 5 | 0 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 19 | 4 | 9 | 0 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 22 | 2 | 6 | 0 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 54 | 4 | 35 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 30 | 2 | 9 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 9 | 3 | 2 | 0 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 7 | 1 | 3 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 9 | 4 | 2 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 13 | 5 | 5 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 66 | 4 | 14 | 0 |
| E2E-B26 | basic | basic | FAIL | PASS | FAIL | 116 | 4 | 12 | 0 |
| E2E-B27 | basic | basic | PASS | FAIL | FAIL | 15 | 1 | 3 | 0 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 12 | 3 | 6 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 12 | 2 | 4 | 0 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 7 | 1 | 3 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 46 | 4 | 22 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 10 | 3 | 6 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 2 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 10 | 3 | 1 | 0 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 16 | 2 | 7 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 24 | 6 | 5 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 23 | 4 | 15 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 11 | 1 | 6 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 11 | 2 | 2 | 0 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 8 | 1 | 2 | 0 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 34 | 5 | 13 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 18 | 5 | 12 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 36 | 4 | 21 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 5 | 3 | 3 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 28 | 3 | 2 | 0 |
| E2E-M26 | medium | medium | PASS | FAIL | FAIL | 22 | 4 | 8 | 0 |
| E2E-M27 | medium | medium | PASS | FAIL | FAIL | 12 | 2 | 4 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 9 | 6 | 5 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 9 | 1 | 5 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 12 | 5 | 2 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 14 | 5 | 3 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 6 | 0 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 34 | 7 | 15 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 54 | 3 | 10 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 9 | 7 | 4 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 24 | 7 | 6 | 0 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 9 | 1 | 4 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 13 | 6 | 4 | 0 |
