# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 6
- Case concurrency: 3
- Agent completed: 6
- External acceptance passed: 1
- Strict E2E passed: 1
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 2 | 0 | 1 | 0 |
| E2E-B02 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M03 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-H10 | hard | hard | PASS | FAIL | FAIL | 2 | 0 | 1 | 0 |
| E2E-M12 | medium | medium | PASS | FAIL | FAIL | 2 | 0 | 1 | 1 |
