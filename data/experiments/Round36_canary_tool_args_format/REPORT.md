# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 5
- Case concurrency: 1
- Agent completed: 4
- External acceptance passed: 4
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 8 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 10 | 3 | 3 | 0 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 14 | 5 | 5 | 0 |
| E2E-B12 | basic | basic | FAIL | PASS | FAIL | 10 | 5 | 3 | 0 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 14 | 5 | 5 | 0 |
