# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 7
- Case concurrency: 7
- Agent completed: 1
- External acceptance passed: 2
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Repairs |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 7 | 1 | 3 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 1 | 1 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 5 | 1 | 0 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 7 | 4 | 1 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 15 | 5 | 7 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 8 | 1 | 1 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 10 | 4 | 0 | 0 |
