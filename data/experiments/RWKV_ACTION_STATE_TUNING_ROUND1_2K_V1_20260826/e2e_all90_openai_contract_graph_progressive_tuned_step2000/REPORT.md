# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 8
- Agent completed: 8
- External acceptance passed: 11
- Strict E2E passed: 8
- Supervisor requests: 315

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 8 | 1 | 2 | 1 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 16 | 4 | 4 | 4 |
| E2E-B03 | basic | basic | FAIL | FAIL | FAIL | 20 | 4 | 5 | 5 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 49 | 7 | 7 | 29 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 11 | 1 | 3 | 1 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 32 | 6 | 9 | 5 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 11 | 4 | 3 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 10 | 1 | 3 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 23 | 4 | 6 | 5 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 20 | 4 | 5 | 5 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 28 | 6 | 6 | 10 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 24 | 6 | 6 | 6 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 21 | 4 | 6 | 3 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 33 | 6 | 8 | 8 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 36 | 8 | 9 | 9 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 47 | 6 | 2 | 38 |
| E2E-M10 | medium | medium | PASS | PASS | PASS | 30 | 6 | 9 | 3 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 42 | 6 | 4 | 28 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 26 | 4 | 0 | 24 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 33 | 7 | 2 | 25 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 31 | 7 | 9 | 6 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 36 | 6 | 9 | 9 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 39 | 7 | 10 | 9 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 32 | 6 | 8 | 8 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 21 | 6 | 7 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 10 | 2 | 3 | 0 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 37 | 6 | 6 | 18 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 20 | 5 | 5 | 5 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 22 | 4 | 6 | 4 |
| E2E-B15 | basic | basic | FAIL | FAIL | FAIL | 22 | 4 | 6 | 4 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 20 | 4 | 5 | 5 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 20 | 5 | 5 | 5 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 24 | 5 | 6 | 6 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 12 | 3 | 3 | 2 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 14 | 6 | 4 | 3 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 19 | 7 | 5 | 4 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 23 | 4 | 6 | 5 |
| E2E-B23 | basic | basic | FAIL | FAIL | FAIL | 25 | 5 | 3 | 15 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 23 | 6 | 6 | 5 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 12 | 5 | 3 | 3 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 17 | 4 | 1 | 13 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 20 | 5 | 5 | 5 |
| E2E-B28 | basic | basic | FAIL | PASS | FAIL | 10 | 4 | 3 | 1 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
