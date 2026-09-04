# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 6
- Agent completed: 57
- External acceptance passed: 43
- Strict E2E passed: 41
- Supervisor requests: 521

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 4 | 3 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 8 | 5 | 2 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 7 | 4 | 3 | 1 |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 8 | 5 | 4 | 0 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 7 | 4 | 3 | 1 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B09 | basic | basic | FAIL | PASS | FAIL | 19 | 11 | 5 | 6 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 22 | 9 | 11 | 2 |
| E2E-M01 | medium | medium | PASS | PASS | PASS | 20 | 4 | 11 | 1 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 12 | 5 | 6 | 1 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 8 | 6 | 4 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 20 | 9 | 10 | 1 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 19 | 10 | 9 | 1 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 2 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 8 | 5 | 4 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 16 | 8 | 8 | 0 |
| E2E-M09 | medium | medium | PASS | PASS | PASS | 16 | 5 | 8 | 1 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 13 | 7 | 6 | 1 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 20 | 8 | 10 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 29 | 10 | 15 | 3 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 6 | 5 | 3 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 32 | 5 | 15 | 5 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 27 | 10 | 10 | 8 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 6 | 5 | 3 | 0 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 8 | 5 | 4 | 0 |
| E2E-H10 | hard | hard | PASS | PASS | PASS | 18 | 7 | 7 | 4 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 31 | 8 | 10 | 11 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 49 | 10 | 25 | 4 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 8 | 5 | 4 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 16 | 4 | 8 | 1 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 47 | 11 | 23 | 7 |
| E2E-LH08 | hard | long_horizon | PASS | FAIL | FAIL | 36 | 8 | 18 | 5 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 4 | 1 | 0 |
| E2E-LH10 | hard | long_horizon | PASS | PASS | PASS | 21 | 6 | 9 | 2 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 10 | 2 | 6 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 1 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 7 | 4 | 3 | 1 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 10 | 6 | 4 | 2 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 9 | 4 | 4 | 1 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B16 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 1 |
| E2E-B18 | basic | basic | PASS | PASS | PASS | 19 | 10 | 7 | 5 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 11 | 6 | 6 | 0 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 8 | 5 | 4 | 0 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 6 | 4 | 3 | 0 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 0 |
| E2E-B24 | basic | basic | PASS | PASS | PASS | 9 | 5 | 5 | 0 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 16 | 9 | 6 | 4 |
| E2E-B26 | basic | basic | PASS | PASS | PASS | 20 | 6 | 10 | 0 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 7 | 4 | 3 | 1 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 6 | 4 | 3 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 18 | 5 | 10 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 25 | 9 | 9 | 7 |
| E2E-M11 | medium | medium | PASS | PASS | PASS | 23 | 5 | 13 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 12 | 6 | 5 | 1 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 7 | 5 | 3 | 1 |
| E2E-M14 | medium | medium | PASS | FAIL | FAIL | 17 | 8 | 6 | 3 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 11 | 4 | 5 | 1 |
| E2E-M16 | medium | medium | PASS | PASS | PASS | 13 | 4 | 8 | 0 |
| E2E-M17 | medium | medium | PASS | PASS | PASS | 16 | 5 | 8 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 10 | 4 | 5 | 0 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 9 | 5 | 4 | 1 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 13 | 5 | 6 | 2 |
| E2E-M21 | medium | medium | PASS | PASS | PASS | 8 | 4 | 4 | 0 |
| E2E-M22 | medium | medium | PASS | PASS | PASS | 10 | 5 | 5 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 24 | 11 | 10 | 4 |
| E2E-M24 | medium | medium | FAIL | PASS | FAIL | 35 | 13 | 11 | 14 |
| E2E-M25 | medium | medium | PASS | FAIL | FAIL | 6 | 4 | 3 | 0 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 35 | 11 | 12 | 14 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 18 | 13 | 9 | 1 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 14 | 5 | 6 | 2 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 11 | 5 | 5 | 1 |
| E2E-M30 | medium | medium | PASS | PASS | PASS | 15 | 6 | 6 | 2 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 24 | 8 | 11 | 2 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 33 | 8 | 22 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 30 | 3 | 24 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 27 | 9 | 16 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 55 | 7 | 13 | 30 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 17 | 4 | 9 | 0 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 6 | 4 | 3 | 0 |
| E2E-H18 | hard | hard | PASS | FAIL | FAIL | 27 | 7 | 12 | 5 |
