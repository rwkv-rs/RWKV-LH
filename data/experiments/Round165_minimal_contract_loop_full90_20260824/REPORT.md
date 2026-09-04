# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 4
- Agent completed: 22
- External acceptance passed: 22
- Strict E2E passed: 19
- Supervisor requests: 325

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 6 | 1 | 3 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 4 | 6 | 1 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 13 | 4 | 5 | 4 |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 21 | 3 | 11 | 2 |
| E2E-B05 | basic | basic | FAIL | PASS | FAIL | 14 | 6 | 7 | 2 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 9 | 2 | 5 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 12 | 2 | 6 | 2 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 11 | 2 | 6 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 3 | 4 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 30 | 10 | 18 | 2 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 14 | 2 | 8 | 2 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M05 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 10 | 2 | 5 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M09 | medium | medium | FAIL | PASS | FAIL | 46 | 12 | 23 | 9 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 8 | 5 | 4 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 28 | 8 | 14 | 3 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-H04 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 27 | 7 | 9 | 13 |
| E2E-H09 | hard | hard | PASS | PASS | PASS | 15 | 5 | 7 | 2 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 4 | 2 | 1 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B12 | basic | basic | PASS | FAIL | FAIL | 8 | 2 | 4 | 0 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 10 | 4 | 4 | 3 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 12 | 3 | 7 | 0 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 13 | 4 | 6 | 2 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 6 | 5 | 3 | 1 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 13 | 5 | 7 | 0 |
| E2E-B18 | basic | basic | FAIL | FAIL | FAIL | 5 | 4 | 3 | 0 |
| E2E-B19 | basic | basic | PASS | PASS | PASS | 7 | 2 | 4 | 0 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 11 | 5 | 6 | 1 |
| E2E-B21 | basic | basic | FAIL | FAIL | FAIL | 15 | 6 | 9 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 15 | 6 | 8 | 0 |
| E2E-B23 | basic | basic | PASS | PASS | PASS | 10 | 2 | 5 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 15 | 8 | 8 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 21 | 6 | 10 | 3 |
| E2E-B26 | basic | basic | FAIL | FAIL | FAIL | 48 | 10 | 27 | 3 |
| E2E-B27 | basic | basic | FAIL | FAIL | FAIL | 5 | 5 | 3 | 0 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B29 | basic | basic | PASS | PASS | PASS | 13 | 2 | 8 | 0 |
| E2E-B30 | basic | basic | FAIL | FAIL | FAIL | 16 | 7 | 9 | 1 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 17 | 6 | 10 | 1 |
| E2E-M13 | medium | medium | FAIL | FAIL | FAIL | 16 | 6 | 9 | 1 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 8 | 4 | 5 | 0 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 0 | 4 | 0 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 26 | 6 | 10 | 9 |
| E2E-M20 | medium | medium | FAIL | FAIL | FAIL | 15 | 7 | 9 | 0 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 22 | 6 | 13 | 4 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 16 | 6 | 9 | 2 |
| E2E-M25 | medium | medium | PASS | PASS | PASS | 10 | 2 | 5 | 1 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 11 | 6 | 6 | 1 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 11 | 2 | 5 | 1 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 21 | 4 | 12 | 3 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 16 | 8 | 8 | 1 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 19 | 7 | 11 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
