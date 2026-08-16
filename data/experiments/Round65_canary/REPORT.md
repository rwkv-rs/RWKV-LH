# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 5
- External acceptance passed: 5
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 10 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 13 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | PASS | FAIL | FAIL | 19 | 6 | 6 | 0 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 13 | 3 | 3 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 23 | 6 | 6 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 44 | 19 | 19 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 22 | 5 | 9 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 17 | 5 | 5 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 41 | 14 | 14 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 10 | 5 | 2 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 10 | 5 | 3 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 44 | 5 | 15 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 26 | 7 | 8 | 0 |
