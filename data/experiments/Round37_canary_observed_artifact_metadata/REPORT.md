# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 2
- Case concurrency: 1
- Agent completed: 1
- External acceptance passed: 2
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B08 | basic | basic | PASS | PASS | PASS | 15 | 4 | 5 | 0 |
| E2E-B19 | basic | basic | FAIL | PASS | FAIL | 14 | 4 | 6 | 0 |
