# RWKV-LH ablation: separated_progress_and_goal_satisfaction

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 10
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 5
- Strict E2E passed: 3

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | FAIL | FAIL | FAIL | 3 | 0 | 0 | 0 |
| E2E-B02 | basic | PASS | PASS | PASS | 12 | 2 | 2 | 0 |
| E2E-B03 | basic | FAIL | FAIL | FAIL | 31 | 4 | 6 | 0 |
| E2E-B04 | basic | FAIL | FAIL | FAIL | 10 | 9 | 1 | 0 |
| E2E-B05 | basic | PASS | PASS | PASS | 28 | 5 | 6 | 0 |
| E2E-B06 | basic | PASS | PASS | PASS | 17 | 3 | 3 | 0 |
| E2E-B07 | basic | FAIL | FAIL | FAIL | 11 | 5 | 1 | 0 |
| E2E-B08 | basic | FAIL | PASS | FAIL | 25 | 4 | 4 | 0 |
| E2E-B09 | basic | FAIL | FAIL | FAIL | 22 | 9 | 4 | 0 |
| E2E-B10 | basic | FAIL | PASS | FAIL | 32 | 7 | 6 | 0 |
