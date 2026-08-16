# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 2
- External acceptance passed: 3
- Strict E2E passed: 2

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 11 | 2 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 13 | 2 | 2 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 17 | 5 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 16 | 4 | 4 | 0 |
| E2E-M03 | medium | medium | FAIL | FAIL | FAIL | 1 | 0 | 0 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 42 | 18 | 18 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 5 | 8 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 5 | 10 | 0 |
| E2E-B24 | basic | basic | FAIL | PASS | FAIL | 16 | 5 | 5 | 0 |
| E2E-M12 | medium | medium | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 17 | 5 | 6 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 30 | 6 | 6 | 0 |
