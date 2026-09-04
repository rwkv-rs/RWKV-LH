# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 1
- Strict E2E passed: 0
- Supervisor requests: 5

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 14 | 1 | 1 | 12 |
| E2E-M11 | medium | medium | FAIL | FAIL | FAIL | 18 | 2 | 3 | 12 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 22 | 2 | 5 | 12 |
