# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 1
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 5 | 1 | 3 | 0 |
| E2E-H01 | hard | hard | FAIL | FAIL | FAIL | 12 | 3 | 5 | 0 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 13 | 1 | 2 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 39 | 6 | 6 | 0 |
| E2E-LH07 | hard | long_horizon | PASS | FAIL | FAIL | 51 | 8 | 23 | 0 |
| E2E-LH09 | hard | long_horizon | PASS | FAIL | FAIL | 24 | 4 | 11 | 0 |
| E2E-B18 | basic | basic | PASS | FAIL | FAIL | 15 | 3 | 9 | 0 |
| E2E-B27 | basic | basic | FAIL | PASS | FAIL | 15 | 3 | 5 | 0 |
| E2E-M19 | medium | medium | FAIL | FAIL | FAIL | 16 | 4 | 3 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 158 | 7 | 91 | 0 |
