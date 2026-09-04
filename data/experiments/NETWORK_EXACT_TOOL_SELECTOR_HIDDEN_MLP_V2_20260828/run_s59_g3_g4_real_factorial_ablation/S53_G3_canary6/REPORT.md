# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 6
- Case concurrency: 3
- Agent completed: 5
- External acceptance passed: 5
- Strict E2E passed: 5
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 3 | 0 | 2 | 0 |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 4 | 0 | 3 | 0 |
| E2E-B10 | basic | basic | PASS | PASS | PASS | 12 | 0 | 7 | 4 |
| E2E-M03 | medium | medium | PASS | PASS | PASS | 3 | 0 | 2 | 0 |
| E2E-H10 | hard | hard | FAIL | FAIL | FAIL | 8 | 0 | 7 | 0 |
| E2E-M12 | medium | medium | PASS | PASS | PASS | 6 | 0 | 5 | 0 |
