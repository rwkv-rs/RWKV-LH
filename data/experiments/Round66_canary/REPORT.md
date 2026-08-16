# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 4
- External acceptance passed: 6
- Strict E2E passed: 4

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 10 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 20 | 5 | 5 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 23 | 6 | 6 | 0 |
| E2E-M01 | medium | medium | PASS | PASS | PASS | 31 | 10 | 10 | 0 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 21 | 5 | 5 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 19 | 5 | 5 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 43 | 18 | 18 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 27 | 8 | 10 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 32 | 10 | 10 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 35 | 12 | 10 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 20 | 13 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 58 | 10 | 21 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 9 | 5 | 3 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 38 | 16 | 16 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 18 | 6 | 6 | 0 |
