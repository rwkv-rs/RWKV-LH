# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 1
- External acceptance passed: 1
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 44 | 3 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 18 | 3 | 1 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 29 | 4 | 2 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 13 | 5 | 0 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 26 | 4 | 3 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 7 | 5 | 0 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 21 | 18 | 1 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 27 | 16 | 1 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 19 | 6 | 1 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 26 | 5 | 2 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 27 | 5 | 3 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 36 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 1 | 0 | 0 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 41 | 5 | 5 | 0 |
