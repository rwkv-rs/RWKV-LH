# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 5
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 5
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 14 | 5 | 5 | 0 |
| E2E-B15 | basic | basic | PASS | PASS | PASS | 12 | 4 | 4 | 0 |
| E2E-B21 | basic | basic | FAIL | PASS | FAIL | 13 | 4 | 4 | 0 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 16 | 4 | 5 | 0 |
| E2E-B30 | basic | basic | FAIL | PASS | FAIL | 13 | 4 | 4 | 0 |
