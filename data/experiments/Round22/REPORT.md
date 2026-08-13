# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 19
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 18 | 3 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 40 | 6 | 6 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 16 | 5 | 4 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 166 | 28 | 28 | 0 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 21 | 23 | 6 | 0 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 37 | 6 | 6 | 0 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 41 | 7 | 7 | 0 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 40 | 9 | 10 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 9 | 5 | 2 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 14 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 19 | 6 | 6 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 17 | 4 | 5 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 16 | 7 | 6 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 2 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 31 | 9 | 9 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 10 | 6 | 2 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 16 | 9 | 6 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 14 | 6 | 4 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 12 | 9 | 4 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 86 | 40 | 40 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 9 | 2 | 2 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 10 | 5 | 3 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 14 | 9 | 5 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 12 | 6 | 3 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 14 | 6 | 5 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 9 | 5 | 2 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 12 | 7 | 3 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 14 | 7 | 5 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 9 | 18 | 2 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 20 | 10 | 5 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 47 | 14 | 15 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 15 | 6 | 6 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 20 | 10 | 7 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 61 | 20 | 21 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 13 | 6 | 4 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 14 | 5 | 5 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 47 | 11 | 11 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 13 | 3 | 3 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 16 | 3 | 3 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 32 | 8 | 8 | 0 |
| E2E-B17 | basic | basic | FAIL | PASS | FAIL | 37 | 9 | 9 | 0 |
| E2E-B18 | basic | basic | FAIL | PASS | FAIL | 49 | 10 | 10 | 0 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 13 | 5 | 5 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 11 | 4 | 3 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 9 | 9 | 1 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 11 | 4 | 2 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 12 | 5 | 4 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 9 | 4 | 2 | 0 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 17 | 4 | 4 | 0 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 69 | 11 | 11 | 0 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 37 | 16 | 16 | 0 |
| E2E-B28 | basic | basic | FAIL | PASS | FAIL | 20 | 4 | 4 | 0 |
| E2E-B29 | basic | basic | FAIL | PASS | FAIL | 36 | 7 | 7 | 0 |
| E2E-B30 | basic | basic | FAIL | PASS | FAIL | 13 | 4 | 4 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 27 | 14 | 11 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 16 | 5 | 4 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 10 | 6 | 3 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 25 | 10 | 10 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 21 | 14 | 8 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 33 | 14 | 12 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 13 | 15 | 4 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 12 | 8 | 4 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 12 | 8 | 3 | 0 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M21 | medium | medium | FAIL | PASS | FAIL | 48 | 14 | 14 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 15 | 8 | 5 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 17 | 9 | 6 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 14 | 5 | 5 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 26 | 5 | 5 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 16 | 9 | 6 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 32 | 13 | 13 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 10 | 5 | 3 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 36 | 30 | 15 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 10 | 7 | 3 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 8 | 7 | 2 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 10 | 11 | 3 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 14 | 10 | 5 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 13 | 11 | 4 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 17 | 8 | 6 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 50 | 16 | 16 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 14 | 10 | 5 | 0 |
