# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 6
- Agent completed: 56
- External acceptance passed: 39
- Strict E2E passed: 36
- Supervisor requests: 757

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 4 | 2 | 3 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 29 | 10 | 21 | 1 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 5 | 2 | 3 | 1 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 20 | 5 | 18 | 1 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 26 | 15 | 10 | 2 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 11 | 4 | 9 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 6 | 3 | 3 | 1 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 10 | 3 | 7 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 15 | 4 | 12 | 2 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 112 | 22 | 109 | 2 |
| E2E-M01 | medium | medium | PASS | PASS | PASS | 44 | 8 | 41 | 2 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 200 | 32 | 190 | 10 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 18 | 8 | 14 | 2 |
| E2E-M04 | medium | medium | PASS | PASS | PASS | 22 | 6 | 17 | 4 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 8 | 3 | 5 | 1 |
| E2E-M06 | medium | medium | PASS | PASS | PASS | 21 | 5 | 19 | 1 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 9 | 3 | 7 | 1 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 12 | 5 | 8 | 0 |
| E2E-M09 | medium | medium | PASS | PASS | PASS | 22 | 6 | 20 | 1 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 3 | 2 | 2 | 1 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 200 | 58 | 199 | 1 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 6 | 2 | 6 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 48 | 13 | 42 | 6 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 2 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 75 | 14 | 69 | 6 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 57 | 11 | 47 | 9 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 120 | 20 | 104 | 12 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 38 | 15 | 32 | 3 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 8 | 3 | 5 | 1 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 85 | 13 | 73 | 12 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 154 | 34 | 148 | 6 |
| E2E-LH02 | hard | long_horizon | PASS | FAIL | FAIL | 31 | 7 | 27 | 3 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 32 | 7 | 28 | 2 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 11 | 3 | 9 | 1 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 191 | 45 | 188 | 3 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 15 | 6 | 9 | 2 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 76 | 13 | 71 | 5 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | PASS | FAIL | FAIL | 24 | 10 | 20 | 0 |
| E2E-LH10 | hard | long_horizon | PASS | FAIL | FAIL | 38 | 9 | 35 | 2 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 98 | 18 | 83 | 12 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 9 | 3 | 6 | 1 |
| E2E-B12 | basic | basic | PASS | PASS | PASS | 29 | 12 | 27 | 1 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 27 | 10 | 18 | 0 |
| E2E-B14 | basic | basic | PASS | FAIL | FAIL | 10 | 4 | 5 | 4 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 18 | 6 | 16 | 1 |
| E2E-B16 | basic | basic | PASS | PASS | PASS | 13 | 5 | 9 | 2 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 8 | 3 | 5 | 1 |
| E2E-B18 | basic | basic | PASS | PASS | PASS | 10 | 4 | 6 | 1 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 3 | 2 | 2 | 0 |
| E2E-B20 | basic | basic | PASS | PASS | PASS | 7 | 2 | 5 | 1 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 10 | 5 | 7 | 2 |
| E2E-B22 | basic | basic | PASS | PASS | PASS | 10 | 4 | 6 | 1 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 6 | 2 | 4 | 1 |
| E2E-B24 | basic | basic | PASS | PASS | PASS | 17 | 6 | 11 | 1 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 19 | 6 | 12 | 2 |
| E2E-B26 | basic | basic | PASS | PASS | PASS | 27 | 6 | 24 | 2 |
| E2E-B27 | basic | basic | PASS | FAIL | FAIL | 26 | 10 | 17 | 2 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 7 | 3 | 5 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 15 | 6 | 12 | 2 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 7 | 3 | 6 | 0 |
| E2E-M11 | medium | medium | FAIL | PASS | FAIL | 73 | 14 | 65 | 6 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 18 | 4 | 16 | 1 |
| E2E-M13 | medium | medium | PASS | FAIL | FAIL | 40 | 18 | 39 | 0 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 22 | 5 | 21 | 1 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 7 | 2 |
| E2E-M16 | medium | medium | PASS | FAIL | FAIL | 23 | 6 | 19 | 1 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 11 | 3 | 8 | 3 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 6 | 2 | 5 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 5 | 3 | 3 | 2 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 11 | 3 | 9 | 1 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 98 | 19 | 90 | 3 |
| E2E-M22 | medium | medium | PASS | PASS | PASS | 11 | 4 | 8 | 1 |
| E2E-M23 | medium | medium | PASS | FAIL | FAIL | 10 | 3 | 9 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 101 | 21 | 100 | 1 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M26 | medium | medium | PASS | FAIL | FAIL | 16 | 5 | 12 | 0 |
| E2E-M27 | medium | medium | PASS | PASS | PASS | 12 | 4 | 8 | 1 |
| E2E-M28 | medium | medium | PASS | FAIL | FAIL | 83 | 16 | 80 | 1 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 21 | 8 | 15 | 0 |
| E2E-M30 | medium | medium | FAIL | PASS | FAIL | 6 | 2 | 6 | 0 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 99 | 18 | 91 | 7 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 3 | 2 | 1 | 2 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 44 | 8 | 36 | 8 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 48 | 9 | 43 | 4 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 61 | 10 | 54 | 7 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 9 | 3 | 7 | 2 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 12 | 4 | 8 | 2 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 20 | 4 | 18 | 2 |
