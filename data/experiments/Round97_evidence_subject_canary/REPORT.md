# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 4
- Case concurrency: 1
- Agent completed: 2
- External acceptance passed: 3
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 7 | 1 | 2 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 12 | 2 | 3 | 0 |
| E2E-B03 | basic | basic | FAIL | PASS | FAIL | 15 | 3 | 4 | 0 |
| E2E-H04 | hard | hard | PASS | PASS | PASS | 7 | 1 | 2 | 0 |
