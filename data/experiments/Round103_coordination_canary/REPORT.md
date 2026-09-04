# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 5
- Case concurrency: 1
- Agent completed: 2
- External acceptance passed: 2
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-M10 | medium | medium | PASS | PASS | PASS | 11 | 2 | 5 | 1 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 9 | 1 | 3 | 0 |
| E2E-LH07 | hard | long_horizon | FAIL | FAIL | FAIL | 95 | 20 | 48 | 1 |
| E2E-B27 | basic | basic | PASS | PASS | PASS | 14 | 4 | 6 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 105 | 9 | 76 | 1 |
