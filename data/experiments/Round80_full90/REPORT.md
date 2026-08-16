# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 31
- Case concurrency: 8
- Agent completed: 0
- External acceptance passed: 5
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 15 | 1 | 5 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 26 | 1 | 12 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 8 | 1 | 2 | 0 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 34 | 4 | 1 | 0 |
| E2E-B05 | basic | basic | FAIL | FAIL | FAIL | 15 | 1 | 5 | 0 |
| E2E-B06 | basic | basic | FAIL | FAIL | FAIL | 33 | 3 | 2 | 0 |
| E2E-B07 | basic | basic | FAIL | PASS | FAIL | 26 | 2 | 12 | 0 |
| E2E-B08 | basic | basic | FAIL | FAIL | FAIL | 25 | 1 | 11 | 0 |
| E2E-B09 | basic | basic | FAIL | FAIL | FAIL | 11 | 1 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 9 | 1 | 0 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 1 | 0 |
| E2E-M02 | medium | medium | FAIL | FAIL | FAIL | 9 | 3 | 2 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 22 | 10 | 6 | 0 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 1 | 0 |
| E2E-M05 | medium | medium | FAIL | PASS | FAIL | 21 | 3 | 7 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 4 | 1 | 0 | 0 |
| E2E-M07 | medium | medium | FAIL | FAIL | FAIL | 4 | 1 | 1 | 0 |
| E2E-M08 | medium | medium | FAIL | FAIL | FAIL | 40 | 2 | 1 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 26 | 4 | 12 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 11 | 1 | 3 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 24 | 4 | 11 | 0 |
| E2E-H03 | hard | hard | FAIL | FAIL | FAIL | 28 | 6 | 11 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 4 | 1 | 1 | 0 |
| E2E-H06 | hard | hard | FAIL | FAIL | FAIL | 4 | 3 | 1 | 0 |
| E2E-H07 | hard | hard | FAIL | FAIL | FAIL | 4 | 1 | 0 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 7 | 1 | 0 | 0 |
| E2E-H09 | hard | hard | FAIL | FAIL | FAIL | 26 | 6 | 12 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 4 | 5 | 1 | 0 |
| E2E-LH01 | hard | long_horizon | FAIL | FAIL | FAIL | 3 | 6 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 16 | 12 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 36 | 2 | 1 | 0 |
