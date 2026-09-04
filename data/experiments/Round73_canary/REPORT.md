# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 14
- Case concurrency: 8
- Agent completed: 1
- External acceptance passed: 2
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 24 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 23 | 3 | 5 | 0 |
| E2E-B10 | basic | basic | FAIL | PASS | FAIL | 39 | 4 | 6 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 25 | 5 | 4 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 41 | 4 | 8 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 27 | 5 | 5 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 62 | 14 | 11 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 7 | 0 | 0 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 32 | 5 | 5 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 35 | 5 | 6 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 39 | 10 | 9 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 6 | 0 | 0 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 87 | 19 | 19 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 57 | 6 | 14 | 0 |
