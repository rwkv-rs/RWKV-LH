# RWKV-LH ablation: no_model_failure_analysis

This suite gives RWKV only a user goal, an isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, replan paths, and external acceptance are not provided to the model.

- Cases run: 1
- Case concurrency: 1
- Agent completed: 1
- External acceptance passed: 1
- Strict E2E passed: 1

| Task | Level | Agent | External | Strict | Model requests | Tasks | Attempts | Replans |
| --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | PASS | PASS | PASS | 21 | 4 | 5 | 0 |
