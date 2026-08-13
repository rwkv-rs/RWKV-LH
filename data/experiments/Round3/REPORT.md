# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 11
- External acceptance passed: 4
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 11 | 3 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B03 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B05 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 12 | 4 | 4 | 0 |
| E2E-B07 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B08 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 10 | 4 | 3 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M07 | medium | medium | PASS | FAIL | FAIL | 13 | 4 | 4 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 10 | 6 | 2 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 4 | 0 | 0 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 16 | 4 | 5 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 6 | 10 | 2 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 10 | 6 | 3 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 15 | 7 | 5 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 14 | 5 | 3 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 30 | 11 | 10 | 0 |
| E2E-B15 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B17 | basic | basic | PASS | FAIL | FAIL | 20 | 5 | 5 | 0 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 8 | 6 | 1 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 17 | 4 | 5 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 10 | 3 | 3 | 0 |
| E2E-B26 | basic | basic | FAIL | PASS | FAIL | 17 | 4 | 4 | 0 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B28 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 21 | 5 | 7 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 10 | 9 | 2 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 15 | 5 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 15 | 10 | 3 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 4 | 0 | 0 | 0 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M21 | medium | medium | PASS | FAIL | FAIL | 26 | 9 | 9 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M23 | medium | medium | PASS | FAIL | FAIL | 24 | 9 | 9 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M25 | medium | medium | PASS | FAIL | FAIL | 10 | 3 | 3 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 9 | 4 | 2 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M28 | medium | medium | PASS | FAIL | FAIL | 18 | 7 | 7 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H14 | hard | hard | PASS | FAIL | FAIL | 30 | 13 | 13 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 4 | 0 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
