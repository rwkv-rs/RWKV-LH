# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 37
- Case concurrency: 5
- Agent completed: 24
- External acceptance passed: 13
- Strict E2E passed: 12

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 5 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 246 | 85 | 4 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 565 | 190 | 10 |
| E2E-B05 | basic | basic | PASS | FAIL | FAIL | 5 | 2 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 22 | 4 | 1 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 14 | 4 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 97 | 30 | 3 |
| E2E-M02 | medium | medium | PASS | PASS | PASS | 14 | 5 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 32 | 11 | 0 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 23 | 7 | 1 |
| E2E-M06 | medium | medium | FAIL | PASS | FAIL | 59 | 8 | 12 |
| E2E-M07 | medium | medium | PASS | PASS | PASS | 11 | 4 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 0 |
| E2E-M09 | medium | medium | PASS | FAIL | FAIL | 26 | 7 | 1 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 67 | 24 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 47 | 15 | 1 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 307 | 163 | 12 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 8 | 1 | 2 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 1 | 0 |
| E2E-H05 | hard | hard | FAIL | FAIL | FAIL | 375 | 193 | 7 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 29 | 10 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 38 | 12 | 1 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 535 | 198 | 2 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 14 | 4 | 1 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 62 | 21 | 1 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 475 | 199 | 1 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 479 | 197 | 3 |
| E2E-LH03 | hard | long_horizon | FAIL | FAIL | FAIL | 547 | 194 | 6 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 11 | 3 | 1 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 41 | 12 | 2 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 258 | 97 | 12 |
| E2E-LH08 | hard | long_horizon | PASS | FAIL | FAIL | 38 | 12 | 1 |
