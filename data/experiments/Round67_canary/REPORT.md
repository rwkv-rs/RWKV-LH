# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 4
- External acceptance passed: 5
- Strict E2E passed: 3

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 11 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 12 | 3 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 27 | 7 | 8 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 32 | 12 | 12 | 0 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 28 | 8 | 8 | 0 |
| E2E-M06 | medium | medium | PASS | FAIL | FAIL | 48 | 8 | 12 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 51 | 21 | 22 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 23 | 9 | 11 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 10 | 5 | 3 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 16 | 4 | 6 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 27 | 9 | 10 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 8 | 5 | 3 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 48 | 23 | 20 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 15 | 5 | 5 | 0 |
