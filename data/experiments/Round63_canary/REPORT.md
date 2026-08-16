# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 4
- External acceptance passed: 3
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 14 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 27 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 48 | 6 | 6 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 22 | 4 | 2 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 53 | 5 | 5 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 504 | 20 | 54 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 46 | 5 | 7 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 42 | 5 | 15 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 11 | 5 | 1 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 66 | 5 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 45 | 5 | 6 | 0 |
| E2E-M18 | medium | medium | PASS | FAIL | FAIL | 53 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 80 | 5 | 5 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 95 | 6 | 28 | 0 |
