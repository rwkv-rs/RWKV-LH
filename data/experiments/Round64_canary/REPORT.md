# RWKV-E2E-90

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 15
- Case concurrency: 8
- Agent completed: 1
- External acceptance passed: 3
- Strict E2E passed: 1

| Task | Group | Native level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 14 | 3 | 3 | 0 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 12 | 3 | 4 | 0 |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 16 | 5 | 5 | 0 |
| E2E-M01 | medium | medium | FAIL | FAIL | FAIL | 64 | 15 | 15 | 0 |
| E2E-M03 | medium | medium | FAIL | PASS | FAIL | 26 | 5 | 5 | 0 |
| E2E-M06 | medium | medium | FAIL | FAIL | FAIL | 33 | 6 | 8 | 0 |
| E2E-LH02 | hard | long_horizon | FAIL | FAIL | FAIL | 2 | 0 | 0 | 0 |
| E2E-LH05 | hard | long_horizon | FAIL | FAIL | FAIL | 26 | 5 | 7 | 0 |
| E2E-LH11 | hard | long_horizon | FAIL | FAIL | FAIL | 25 | 5 | 5 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 26 | 5 | 6 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 26 | 10 | 5 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 10 | 5 | 1 | 0 |
| E2E-M18 | medium | medium | FAIL | FAIL | FAIL | 15 | 5 | 2 | 0 |
| E2E-H12 | hard | hard | FAIL | FAIL | FAIL | 8 | 5 | 1 | 0 |
| E2E-H13 | hard | hard | FAIL | FAIL | FAIL | 5 | 21 | 0 | 0 |
