# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 43
- External acceptance passed: 24
- Strict E2E passed: 23

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 13 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 18 | 3 | 3 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 21 | 3 | 3 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 23 | 5 | 3 | 0 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 27 | 5 | 5 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 29 | 5 | 5 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 16 | 3 | 3 | 0 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 22 | 4 | 4 | 0 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 18 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 17 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | PASS | FAIL | FAIL | 23 | 4 | 4 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 13 | 5 | 3 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 17 | 3 | 3 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 38 | 7 | 7 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 20 | 5 | 4 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 34 | 5 | 5 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 30 | 5 | 5 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 26 | 5 | 5 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 30 | 5 | 5 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 12 | 5 | 1 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 21 | 5 | 3 | 0 |
| E2E-H02 | hard | hard | PASS | FAIL | FAIL | 29 | 5 | 5 | 0 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 42 | 8 | 8 | 0 |
| E2E-H04 | hard | hard | FAIL | FAIL | FAIL | 12 | 5 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 13 | 5 | 2 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 70 | 15 | 15 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 12 | 6 | 2 | 0 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 29 | 5 | 5 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 13 | 5 | 1 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 16 | 7 | 3 | 0 |
| E2E-LH01 | hard | long_horizon | PASS | FAIL | FAIL | 23 | 4 | 4 | 0 |
| E2E-LH02 | hard | long_horizon | PASS | PASS | PASS | 74 | 17 | 17 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 5 | 3 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 20 | 8 | 2 | 0 |
| E2E-LH05 | hard | long_horizon | PASS | FAIL | FAIL | 31 | 5 | 5 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 18 | 6 | 4 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 31 | 5 | 5 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 32 | 5 | 5 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 19 | 6 | 5 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 27 | 5 | 4 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 70 | 5 | 5 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 25 | 9 | 5 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 28 | 5 | 5 | 0 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 26 | 4 | 4 | 0 |
| E2E-B13 | basic | basic | PASS | PASS | PASS | 29 | 5 | 5 | 0 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 28 | 5 | 5 | 0 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 22 | 4 | 4 | 0 |
| E2E-B16 | basic | basic | PASS | PASS | PASS | 19 | 3 | 3 | 0 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 31 | 5 | 5 | 0 |
| E2E-B18 | basic | basic | FAIL | PASS | FAIL | 21 | 4 | 4 | 0 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 22 | 4 | 4 | 0 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 27 | 5 | 5 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 11 | 4 | 1 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 30 | 5 | 5 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 17 | 5 | 2 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 12 | 5 | 1 | 0 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 22 | 4 | 4 | 0 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 4 | 5 | 0 | 0 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 28 | 5 | 4 | 0 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 24 | 4 | 4 | 0 |
| E2E-B29 | basic | basic | PASS | FAIL | FAIL | 32 | 6 | 6 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 20 | 5 | 2 | 0 |
| E2E-M13 | medium | medium | PASS | FAIL | FAIL | 32 | 5 | 5 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 16 | 5 | 2 | 0 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 31 | 5 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 30 | 5 | 2 | 0 |
| E2E-M17 | medium | medium | PASS | FAIL | FAIL | 56 | 12 | 12 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 28 | 5 | 5 | 0 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 30 | 5 | 5 | 0 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 30 | 5 | 5 | 0 |
| E2E-M21 | medium | medium | PASS | FAIL | FAIL | 33 | 5 | 5 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 26 | 5 | 5 | 0 |
| E2E-M23 | medium | medium | PASS | FAIL | FAIL | 36 | 7 | 7 | 0 |
| E2E-M24 | medium | medium | PASS | FAIL | FAIL | 24 | 5 | 5 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 30 | 5 | 5 | 0 |
| E2E-M26 | medium | medium | PASS | FAIL | FAIL | 28 | 4 | 4 | 0 |
| E2E-M27 | medium | medium | PASS | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 20 | 7 | 2 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 44 | 5 | 5 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 31 | 6 | 5 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 61 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 21 | 5 | 3 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 83 | 6 | 12 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 21 | 6 | 4 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 27 | 8 | 4 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 28 | 8 | 5 | 0 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 24 | 4 | 4 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 33 | 5 | 5 | 0 |
