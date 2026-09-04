# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 4
- Agent completed: 17
- External acceptance passed: 35
- Strict E2E passed: 14
- Supervisor requests: 373

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 6 | 1 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 14 | 3 | 7 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 10 | 1 | 4 | 2 |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 16 | 3 | 8 | 2 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 10 | 3 | 5 | 0 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 24 | 3 | 13 | 2 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 24 | 6 | 13 | 3 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 21 | 3 | 12 | 2 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 25 | 3 | 12 | 2 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 13 | 2 | 7 | 2 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 11 | 7 | 5 | 1 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 17 | 7 | 10 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 10 | 2 | 5 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M09 | medium | medium | FAIL | PASS | FAIL | 75 | 17 | 40 | 12 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 12 | 6 | 6 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 57 | 9 | 27 | 8 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 6 | 1 | 3 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 15 | 7 | 8 | 2 |
| E2E-H09 | hard | hard | FAIL | PASS | FAIL | 14 | 8 | 6 | 2 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 23 | 9 | 13 | 2 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B11 | basic | basic | FAIL | PASS | FAIL | 27 | 5 | 8 | 13 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 18 | 6 | 7 | 4 |
| E2E-B14 | basic | basic | FAIL | FAIL | FAIL | 51 | 9 | 22 | 15 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 16 | 3 | 7 | 2 |
| E2E-B16 | basic | basic | FAIL | PASS | FAIL | 13 | 7 | 6 | 1 |
| E2E-B17 | basic | basic | FAIL | PASS | FAIL | 17 | 4 | 7 | 3 |
| E2E-B18 | basic | basic | FAIL | PASS | FAIL | 15 | 3 | 8 | 0 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 14 | 3 | 7 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 22 | 4 | 13 | 0 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 14 | 6 | 7 | 0 |
| E2E-B23 | basic | basic | FAIL | PASS | FAIL | 16 | 6 | 8 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 12 | 2 | 5 | 2 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B27 | basic | basic | FAIL | PASS | FAIL | 18 | 3 | 9 | 2 |
| E2E-B28 | basic | basic | FAIL | PASS | FAIL | 11 | 7 | 5 | 1 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 18 | 7 | 11 | 0 |
| E2E-B30 | basic | basic | FAIL | PASS | FAIL | 20 | 3 | 10 | 1 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 19 | 3 | 10 | 1 |
| E2E-M13 | medium | medium | PASS | PASS | PASS | 32 | 9 | 8 | 17 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-M19 | medium | medium | PASS | PASS | PASS | 14 | 7 | 6 | 3 |
| E2E-M20 | medium | medium | FAIL | PASS | FAIL | 36 | 7 | 16 | 4 |
| E2E-M21 | medium | medium | FAIL | PASS | FAIL | 41 | 15 | 21 | 5 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 19 | 9 | 9 | 4 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 30 | 9 | 9 | 15 |
| E2E-M25 | medium | medium | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 19 | 7 | 8 | 4 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 14 | 6 | 7 | 0 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 16 | 6 | 7 | 2 |
| E2E-M30 | medium | medium | FAIL | PASS | FAIL | 36 | 12 | 20 | 4 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 67 | 7 | 22 | 28 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 27 | 9 | 14 | 4 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
