# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 31
- Case concurrency: 8
- Agent completed: 31
- External acceptance passed: 4
- Strict E2E passed: 4
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 2 | 0 | 1 | 0 |
| E2E-B02 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-B03 | basic | basic | PASS | PASS | PASS | 2 | 0 | 1 | 0 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-B05 | basic | basic | PASS | PASS | PASS | 2 | 0 | 1 | 0 |
| E2E-B06 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-B07 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-B08 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-B09 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M01 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M02 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M05 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M07 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M09 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-H01 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H02 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-H03 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 2 | 0 | 1 | 0 |
| E2E-H05 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H06 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H07 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
| E2E-H08 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H09 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H10 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-LH01 | hard | long_horizon | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
