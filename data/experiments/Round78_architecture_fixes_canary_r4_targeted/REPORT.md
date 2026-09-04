# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 2
- External acceptance passed: 1
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 10 | 4 | 3 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 8 | 3 | 2 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 10 | 5 | 4 | 0 |
