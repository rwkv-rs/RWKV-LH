# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 4
- Agent completed: 43
- External acceptance passed: 38
- Strict E2E passed: 34
- Supervisor requests: 344

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 6 | 2 | 3 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 9 | 2 | 4 | 1 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 9 | 3 | 4 | 1 |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 16 | 7 | 8 | 0 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 13 | 2 | 6 | 2 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 11 | 2 | 5 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 24 | 6 | 11 | 2 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 18 | 2 | 9 | 2 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 9 | 2 | 4 | 1 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 18 | 2 | 9 | 0 |
| E2E-M05 | medium | medium | FAIL | PASS | FAIL | 41 | 16 | 19 | 3 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 10 | 2 | 5 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 14 | 2 | 5 | 4 |
| E2E-M09 | medium | medium | PASS | PASS | PASS | 31 | 6 | 13 | 5 |
| E2E-M10 | medium | medium | PASS | PASS | PASS | 14 | 6 | 7 | 2 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 54 | 10 | 26 | 2 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 14 | 6 | 7 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 18 | 8 | 8 | 2 |
| E2E-H09 | hard | hard | PASS | PASS | PASS | 12 | 2 | 5 | 2 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 101 | 14 | 37 | 30 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 84 | 17 | 38 | 22 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 24 | 9 | 12 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 21 | 2 | 9 | 3 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | PASS | FAIL | 32 | 6 | 13 | 6 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 16 | 6 | 7 | 2 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 14 | 6 | 7 | 0 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 11 | 2 | 4 | 3 |
| E2E-B16 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B18 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 11 | 2 | 4 | 3 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 12 | 2 | 5 | 2 |
| E2E-B21 | basic | basic | FAIL | PASS | FAIL | 12 | 8 | 5 | 2 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 14 | 6 | 7 | 0 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 11 | 2 | 5 | 1 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 28 | 10 | 14 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 12 | 2 | 5 | 2 |
| E2E-B26 | basic | basic | PASS | PASS | PASS | 26 | 6 | 12 | 2 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 11 | 2 | 5 | 1 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 8 | 3 | 4 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 17 | 2 | 8 | 1 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 28 | 11 | 13 | 2 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 20 | 6 | 9 | 2 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 16 | 7 | 8 | 0 |
| E2E-M14 | medium | medium | PASS | FAIL | FAIL | 14 | 2 | 6 | 3 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 2 | 1 | 1 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 14 | 2 | 6 | 2 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 12 | 2 | 4 | 4 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 23 | 8 | 9 | 5 |
| E2E-M21 | medium | medium | PASS | PASS | PASS | 11 | 2 | 5 | 1 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 8 | 3 | 3 | 2 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 36 | 8 | 17 | 2 |
| E2E-M25 | medium | medium | PASS | PASS | PASS | 16 | 6 | 6 | 4 |
| E2E-M26 | medium | medium | PASS | FAIL | FAIL | 17 | 6 | 7 | 3 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 18 | 6 | 9 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 34 | 12 | 13 | 8 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 46 | 8 | 17 | 12 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 60 | 8 | 23 | 14 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 26 | 7 | 13 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
