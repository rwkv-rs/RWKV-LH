# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 10
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 4 | 1 | 1 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 4 | 1 | 1 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 30 | 3 | 13 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 38 | 4 | 1 | 0 |
| E2E-B05 | basic | basic | FAIL | FAIL | FAIL | 15 | 1 | 5 | 0 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 7 | 4 | 2 | 0 |
| E2E-B07 | basic | basic | FAIL | FAIL | FAIL | 14 | 2 | 4 | 0 |
| E2E-B08 | basic | basic | FAIL | FAIL | FAIL | 15 | 1 | 5 | 0 |
| E2E-B09 | basic | basic | FAIL | PASS | FAIL | 10 | 1 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 7 | 1 | 0 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 1 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 29 | 6 | 10 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 35 | 10 | 14 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 1 | 0 |
| E2E-M05 | medium | medium | FAIL | PASS | FAIL | 21 | 3 | 7 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 15 | 1 | 4 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 4 | 1 | 1 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 40 | 3 | 1 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 26 | 4 | 12 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 11 | 1 | 3 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 19 | 4 | 9 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 79 | 21 | 28 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 28 | 6 | 11 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 4 | 1 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 25 | 29 | 11 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 24 | 3 | 9 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 4 | 1 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 7 | 1 | 0 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 26 | 6 | 12 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 4 | 6 | 1 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 6 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 16 | 12 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 1 | 0 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 14 | 2 | 5 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 2 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 38 | 6 | 1 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 7 | 12 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 4 | 8 | 1 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 5 | 4 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 9 | 3 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 5 | 5 | 1 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 6 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 15 | 2 | 5 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 15 | 2 | 5 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 30 | 3 | 13 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 4 | 2 | 1 | 0 |
| E2E-B15 | basic | basic | FAIL | FAIL | FAIL | 4 | 1 | 1 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 10 | 3 | 3 | 0 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 38 | 1 | 1 | 0 |
| E2E-B18 | basic | basic | FAIL | PASS | FAIL | 40 | 4 | 16 | 0 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 15 | 1 | 5 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 16 | 2 | 2 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 3 | 3 | 0 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 8 | 1 | 2 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 27 | 4 | 9 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 19 | 4 | 9 | 0 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 35 | 2 | 13 | 0 |
| E2E-B26 | basic | basic | FAIL | PASS | FAIL | 14 | 3 | 4 | 0 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 26 | 3 | 12 | 0 |
| E2E-B28 | basic | basic | FAIL | FAIL | FAIL | 26 | 1 | 12 | 0 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 5 | 2 | 1 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 9 | 1 | 0 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 1 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 0 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 11 | 4 | 3 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 40 | 3 | 17 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 25 | 1 | 11 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 31 | 5 | 9 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 42 | 3 | 15 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 5 | 1 | 0 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 35 | 2 | 1 | 0 |
| E2E-M20 | medium | medium | FAIL | PASS | FAIL | 7 | 1 | 2 | 0 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 24 | 1 | 11 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 4 | 5 | 1 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 45 | 4 | 18 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 7 | 1 | 0 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 29 | 6 | 10 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 4 | 3 | 1 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 14 | 2 | 4 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 12 | 7 | 5 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 4 | 1 | 1 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 4 | 5 | 1 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 38 | 7 | 1 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 10 | 16 | 3 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 3 | 7 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 38 | 4 | 1 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 4 | 5 | 1 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 25 | 10 | 11 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 7 | 1 | 1 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 4 | 5 | 1 | 0 |
