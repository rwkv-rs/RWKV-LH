# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 90
- Case concurrency: 1
- Agent completed: 22
- External acceptance passed: 27
- Strict E2E passed: 17
- Supervisor requests: 165

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 4 | 2 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 8 | 3 | 6 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 6 | 2 | 4 | 1 |
| E2E-B04 | basic | basic | FAIL | PASS | FAIL | 15 | 1 | 13 | 1 |
| E2E-B05 | basic | basic | FAIL | FAIL | FAIL | 8 | 3 | 4 | 2 |
| E2E-B06 | basic | basic | FAIL | PASS | FAIL | 17 | 1 | 4 | 12 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 7 | 3 | 4 | 1 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 8 | 3 | 5 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 6 | 2 | 5 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 15 | 1 | 13 | 1 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 201 | 1 | 191 | 9 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 13 | 1 | 12 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 5 | 2 | 3 | 1 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 10 | 3 | 7 | 1 |
| E2E-M05 | medium | medium | FAIL | PASS | FAIL | 201 | 1 | 199 | 1 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 24 | 1 | 11 | 12 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 201 | 1 | 199 | 1 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 4 | 2 | 3 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 12 | 3 | 8 | 2 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 10 | 3 | 8 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 116 | 1 | 113 | 1 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 202 | 1 | 189 | 11 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 166 | 2 | 151 | 12 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 5 | 2 | 3 | 1 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 201 | 1 | 193 | 7 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 21 | 1 | 8 | 12 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 87 | 1 | 74 | 12 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 34 | 3 | 31 | 1 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 11 | 1 | 9 | 1 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 86 | 1 | 73 | 12 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 188 | 1 | 179 | 8 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 201 | 1 | 194 | 6 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 57 | 1 | 56 | 0 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 83 | 1 | 70 | 12 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 80 | 1 | 66 | 12 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 127 | 1 | 114 | 12 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 95 | 1 | 82 | 12 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 86 | 1 | 73 | 12 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 15 | 3 | 11 | 2 |
| E2E-LH10 | hard | long_horizon | FAIL | FAIL | FAIL | 202 | 1 | 197 | 3 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 190 | 1 | 176 | 12 |
| E2E-LH12 | hard | long_horizon | FAIL | FAIL | FAIL | 155 | 1 | 142 | 12 |
| E2E-B11 | basic | basic | FAIL | FAIL | FAIL | 8 | 3 | 5 | 1 |
| E2E-B12 | basic | basic | FAIL | FAIL | FAIL | 12 | 1 | 10 | 1 |
| E2E-B13 | basic | basic | FAIL | FAIL | FAIL | 25 | 2 | 23 | 0 |
| E2E-B14 | basic | basic | PASS | FAIL | FAIL | 9 | 3 | 7 | 0 |
| E2E-B15 | basic | basic | FAIL | PASS | FAIL | 12 | 1 | 10 | 1 |
| E2E-B16 | basic | basic | FAIL | FAIL | FAIL | 21 | 3 | 17 | 2 |
| E2E-B17 | basic | basic | PASS | PASS | PASS | 5 | 2 | 4 | 0 |
| E2E-B18 | basic | basic | PASS | PASS | PASS | 8 | 3 | 5 | 1 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 7 | 3 | 5 | 0 |
| E2E-B20 | basic | basic | FAIL | PASS | FAIL | 17 | 1 | 4 | 12 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 9 | 3 | 6 | 1 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 9 | 3 | 6 | 1 |
| E2E-B23 | basic | basic | PASS | FAIL | FAIL | 9 | 3 | 7 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 166 | 2 | 152 | 12 |
| E2E-B25 | basic | basic | FAIL | FAIL | FAIL | 12 | 3 | 9 | 1 |
| E2E-B26 | basic | basic | PASS | PASS | PASS | 12 | 2 | 9 | 2 |
| E2E-B27 | basic | basic | FAIL | PASS | FAIL | 16 | 1 | 3 | 12 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 3 |
| E2E-B29 | basic | basic | FAIL | FAIL | FAIL | 9 | 3 | 5 | 2 |
| E2E-B30 | basic | basic | PASS | PASS | PASS | 6 | 2 | 5 | 0 |
| E2E-M11 | medium | medium | FAIL | PASS | FAIL | 144 | 2 | 130 | 12 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 6 | 2 | 5 | 0 |
| E2E-M13 | medium | medium | PASS | PASS | PASS | 30 | 3 | 25 | 3 |
| E2E-M14 | medium | medium | FAIL | FAIL | FAIL | 201 | 1 | 199 | 1 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 18 | 1 | 5 | 12 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 31 | 3 | 28 | 1 |
| E2E-M17 | medium | medium | FAIL | FAIL | FAIL | 21 | 1 | 19 | 1 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 8 | 2 | 5 | 2 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 10 | 3 | 6 | 2 |
| E2E-M20 | medium | medium | PASS | PASS | PASS | 8 | 2 | 5 | 2 |
| E2E-M21 | medium | medium | FAIL | FAIL | FAIL | 202 | 2 | 199 | 0 |
| E2E-M22 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 6 | 1 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 18 | 3 | 14 | 2 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 53 | 1 | 51 | 0 |
| E2E-M25 | medium | medium | FAIL | FAIL | FAIL | 11 | 3 | 7 | 2 |
| E2E-M26 | medium | medium | FAIL | FAIL | FAIL | 6 | 2 | 5 | 0 |
| E2E-M27 | medium | medium | PASS | PASS | PASS | 8 | 3 | 5 | 1 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 13 | 1 | 12 | 0 |
| E2E-M29 | medium | medium | FAIL | FAIL | FAIL | 93 | 3 | 82 | 9 |
| E2E-M30 | medium | medium | PASS | PASS | PASS | 44 | 2 | 42 | 1 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 34 | 1 | 31 | 1 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 74 | 1 | 61 | 12 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 41 | 1 | 28 | 12 |
| E2E-H14 | hard | hard | FAIL | FAIL | FAIL | 6 | 1 | 5 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 47 | 1 | 44 | 2 |
| E2E-H16 | hard | hard | FAIL | FAIL | FAIL | 18 | 1 | 5 | 12 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 204 | 2 | 201 | 0 |
| E2E-H18 | hard | hard | FAIL | FAIL | FAIL | 15 | 1 | 14 | 0 |
