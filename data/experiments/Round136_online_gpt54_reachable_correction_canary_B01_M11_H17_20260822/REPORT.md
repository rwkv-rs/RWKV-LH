# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 2
- External acceptance passed: 2
- Strict E2E passed: 1
- Supervisor requests: 13

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | PASS | PASS | PASS | 4 | 2 | 3 | 0 |
| E2E-M11 | medium | medium | FAIL | PASS | FAIL | 23 | 2 | 11 | 12 |
| E2E-H17 | hard | hard | PASS | FAIL | FAIL | 25 | 9 | 17 | 1 |
