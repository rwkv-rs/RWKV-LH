# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 2
- External acceptance passed: 3
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | FAIL | 5 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | FAIL | 11 | 4 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 17 | 6 | 0 |
