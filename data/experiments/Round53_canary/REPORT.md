# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 12
- Case concurrency: 8
- Agent completed: 8
- External acceptance passed: 2
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 13 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 18 | 3 | 3 | 0 |
| E2E-B04 | basic | basic | PASS | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 29 | 5 | 5 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 25 | 5 | 2 | 0 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-LH09 | hard | long_horizon | PASS | FAIL | FAIL | 38 | 6 | 7 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 56 | 5 | 5 | 0 |
| E2E-B29 | basic | basic | PASS | FAIL | FAIL | 26 | 5 | 5 | 0 |
| E2E-B30 | basic | basic | PASS | FAIL | FAIL | 22 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 24 | 5 | 3 | 0 |
| E2E-H15 | hard | hard | FAIL | FAIL | FAIL | 11 | 8 | 0 | 0 |
