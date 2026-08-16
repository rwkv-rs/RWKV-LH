# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 3
- External acceptance passed: 4
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 19 | 3 | 3 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 27 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 64 | 4 | 4 | 0 |
| E2E-M01 | medium | medium | FAIL | PASS | FAIL | 63 | 9 | 9 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 8 | 3 | 1 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 52 | 5 | 5 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 381 | 21 | 21 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 50 | 5 | 6 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 31 | 5 | 7 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 12 | 6 | 1 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 85 | 6 | 7 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 122 | 5 | 6 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 55 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 7 | 5 | 1 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 74 | 6 | 13 | 0 |
