# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 7
- Case concurrency: 7
- Agent completed: 2
- External acceptance passed: 3
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 47 | 7 | 8 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 30 | 2 | 4 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 32 | 6 | 9 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 18 | 5 | 4 | 0 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 79 | 11 | 19 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 28 | 6 | 7 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 63 | 11 | 15 | 0 |
