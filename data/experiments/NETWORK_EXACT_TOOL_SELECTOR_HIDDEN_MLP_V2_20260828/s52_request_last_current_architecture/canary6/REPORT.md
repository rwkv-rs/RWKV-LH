# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 6
- Case concurrency: 3
- Agent completed: 6
- External acceptance passed: 4
- Strict E2E passed: 4
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 6 | 0 | 5 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 5 | 0 | 3 | 1 |
| E2E-B10 | basic | basic | PASS | FAIL | FAIL | 7 | 0 | 6 | 0 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 5 | 0 | 4 | 0 |
| E2E-H10 | hard | hard | PASS | FAIL | FAIL | 5 | 0 | 4 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 6 | 0 | 5 | 0 |
