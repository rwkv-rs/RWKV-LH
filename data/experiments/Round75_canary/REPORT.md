# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 7
- Case concurrency: 7
- Agent completed: 1
- External acceptance passed: 2
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 18 | 4 | 4 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 11 | 4 | 2 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 18 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | FAIL | PASS | FAIL | 26 | 7 | 7 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 4 | 3 | 0 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 20 | 5 | 5 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 4 | 4 | 0 | 0 |
