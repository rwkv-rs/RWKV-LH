# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 4
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 2
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 7 | 1 | 1 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 8 | 1 | 2 | 0 |
| E2E-B03 | basic | basic | FAIL | FAIL | FAIL | 7 | 3 | 2 | 0 |
| E2E-H04 | hard | hard | FAIL | PASS | FAIL | 11 | 1 | 2 | 0 |
