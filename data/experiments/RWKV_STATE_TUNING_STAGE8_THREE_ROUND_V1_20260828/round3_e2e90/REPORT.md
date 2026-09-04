# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 4
- Agent completed: 19
- External acceptance passed: 20
- Strict E2E passed: 17
- Supervisor requests: 385

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | FAIL | FAIL | 35 | 6 | 3 | 24 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 46 | 9 | 12 | 13 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 14 | 3 | 5 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 14 | 1 | 4 | 2 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 21 | 6 | 3 | 13 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 19 | 6 | 6 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 43 | 6 | 9 | 16 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 12 | 2 | 4 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 27 | 6 | 9 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 26 | 7 | 10 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 17 | 4 | 5 | 2 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-M05 | medium | medium | PASS | FAIL | FAIL | 25 | 4 | 7 | 4 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 42 | 12 | 13 | 3 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 34 | 5 | 3 | 24 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 45 | 6 | 7 | 26 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 17 | 6 | 6 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 12 | 2 | 3 | 2 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 28 | 6 | 10 | 1 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H09 | hard | hard | PASS | PASS | PASS | 19 | 3 | 6 | 1 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 63 | 6 | 26 | 2 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 5 | 1 | 1 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 23 | 7 | 8 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 19 | 4 | 2 | 13 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 22 | 4 | 6 | 3 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 65 | 8 | 3 | 48 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 38 | 8 | 5 | 24 |
| E2E-B15 | basic | basic | FAIL | FAIL | FAIL | 19 | 4 | 2 | 13 |
| E2E-B16 | basic | basic | PASS | PASS | PASS | 14 | 2 | 4 | 2 |
| E2E-B17 | basic | basic | FAIL | FAIL | FAIL | 32 | 6 | 2 | 24 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 15 | 5 | 1 | 12 |
| E2E-B19 | basic | basic | FAIL | FAIL | FAIL | 15 | 5 | 1 | 12 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 29 | 6 | 7 | 8 |
| E2E-B21 | basic | basic | FAIL | PASS | FAIL | 15 | 4 | 4 | 3 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 16 | 6 | 1 | 12 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 17 | 2 | 5 | 1 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 42 | 11 | 7 | 21 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 18 | 2 | 5 | 3 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 31 | 4 | 2 | 24 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 14 | 2 | 4 | 2 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 18 | 4 | 5 | 3 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 21 | 7 | 3 | 13 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 42 | 8 | 8 | 17 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 18 | 5 | 6 | 0 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 28 | 6 | 10 | 1 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 42 | 6 | 6 | 25 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 62 | 6 | 10 | 36 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 25 | 2 | 4 | 12 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 30 | 5 | 9 | 3 |
| E2E-M21 | medium | medium | PASS | PASS | PASS | 27 | 4 | 9 | 1 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 22 | 6 | 7 | 1 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 23 | 6 | 8 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 32 | 4 | 2 | 24 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 20 | 5 | 7 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 31 | 6 | 2 | 24 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 37 | 6 | 14 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 70 | 11 | 11 | 36 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 35 | 6 | 11 | 4 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 21 | 6 | 7 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 38 | 6 | 13 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
