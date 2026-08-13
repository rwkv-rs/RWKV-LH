# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 5
- Case concurrency: 1
- Agent completed: 4
- External acceptance passed: 4
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 3 | 3 | 0 |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 16 | 5 | 5 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 12 | 3 | 3 | 0 |
| E2E-B25 | basic | basic | PASS | PASS | PASS | 16 | 4 | 4 | 0 |
| E2E-B29 | basic | basic | PASS | FAIL | FAIL | 14 | 4 | 4 | 0 |
