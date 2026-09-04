# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 7
- Case concurrency: 7
- Agent completed: 3
- External acceptance passed: 2
- Strict E2E passed: 0

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 10 | 3 | 2 | 0 |
| E2E-B02 | basic | basic | FAIL | PASS | FAIL | 10 | 4 | 2 | 0 |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 8 | 2 | 1 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 11 | 5 | 3 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 7 | 2 | 1 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 9 | 4 | 1 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 11 | 5 | 2 | 0 |
