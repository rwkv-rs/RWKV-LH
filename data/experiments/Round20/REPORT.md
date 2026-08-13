# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 1
- External acceptance passed: 17
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 32 | 6 | 6 | 0 |
| E2E-B02 | basic | basic | PASS | FAIL | FAIL | 41 | 8 | 8 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 24 | 9 | 9 | 0 |
| E2E-B04 | basic | basic | FAIL | PASS | FAIL | 30 | 7 | 9 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 58 | 26 | 26 | 0 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 41 | 8 | 8 | 0 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 28 | 10 | 11 | 0 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 27 | 4 | 4 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 13 | 1 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 17 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 27 | 11 | 11 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 16 | 4 | 5 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 40 | 14 | 10 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 28 | 6 | 6 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 69 | 32 | 32 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 17 | 3 | 3 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 19 | 5 | 5 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 12 | 4 | 4 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 17 | 9 | 6 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 92 | 32 | 32 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 10 | 2 | 2 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 35 | 10 | 10 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 22 | 5 | 6 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 9 | 6 | 2 | 0 |
| E2E-H09 | hard | hard | FAIL | PASS | FAIL | 50 | 9 | 11 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 8 | 6 | 1 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 27 | 10 | 10 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | PASS | FAIL | 69 | 23 | 23 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 45 | 20 | 21 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 105 | 24 | 24 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 9 | 11 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 57 | 24 | 25 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 16 | 6 | 6 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 15 | 5 | 5 | 0 |
| E2E-B12 | basic | basic | FAIL | PASS | FAIL | 69 | 32 | 32 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 64 | 29 | 29 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 55 | 24 | 24 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 38 | 6 | 6 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 110 | 24 | 24 | 0 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 18 | 7 | 7 | 0 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 53 | 13 | 13 | 0 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 59 | 12 | 12 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 36 | 8 | 8 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 16 | 6 | 4 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 4 | 2 | 0 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 29 | 6 | 9 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 9 | 5 | 2 | 0 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 67 | 14 | 14 | 0 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 21 | 6 | 6 | 0 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 14 | 4 | 5 | 0 |
| E2E-B28 | basic | basic | FAIL | FAIL | FAIL | 15 | 5 | 4 | 0 |
| E2E-B29 | basic | basic | FAIL | PASS | FAIL | 42 | 8 | 8 | 0 |
| E2E-B30 | basic | basic | FAIL | PASS | FAIL | 12 | 4 | 4 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 106 | 32 | 32 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 17 | 5 | 6 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 10 | 5 | 3 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 21 | 8 | 8 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 55 | 25 | 25 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 34 | 8 | 8 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 75 | 22 | 22 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 51 | 12 | 12 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 13 | 7 | 3 | 0 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 29 | 19 | 11 | 0 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 66 | 16 | 16 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 105 | 27 | 27 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 60 | 20 | 20 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 20 | 7 | 8 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 26 | 7 | 9 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 68 | 27 | 27 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 59 | 30 | 21 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 43 | 10 | 10 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 8 | 7 | 2 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 57 | 15 | 15 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 21 | 13 | 8 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 13 | 11 | 4 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 13 | 9 | 3 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 67 | 17 | 18 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 19 | 11 | 6 | 0 |
