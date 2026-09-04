# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 12
- External acceptance passed: 4
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 13 | 4 | 4 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 10 | 2 | 2 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 33 | 5 | 8 | 0 |
| E2E-M01 | medium | medium | PASS | FAIL | FAIL | 18 | 6 | 6 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 11 | 3 | 3 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 20 | 5 | 6 | 0 |
| E2E-H02 | hard | hard | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | PASS | FAIL | FAIL | 22 | 1 | 1 | 0 |
| E2E-LH11 | hard | long_horizon | PASS | FAIL | FAIL | 27 | 5 | 7 | 0 |
| E2E-B24 | basic | basic | PASS | FAIL | FAIL | 21 | 6 | 6 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 25 | 6 | 6 | 0 |
| E2E-M16 | medium | medium | PASS | FAIL | FAIL | 23 | 5 | 6 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 19 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | PASS | FAIL | FAIL | 35 | 5 | 11 | 0 |
| E2E-H13 | hard | hard | PASS | FAIL | FAIL | 18 | 5 | 5 | 0 |
