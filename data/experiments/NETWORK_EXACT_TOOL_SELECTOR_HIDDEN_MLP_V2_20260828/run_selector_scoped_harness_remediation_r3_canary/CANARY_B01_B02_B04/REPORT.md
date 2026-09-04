# RWKV-E2E-30

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 1
- Strict E2E passed: 0
- Supervisor requests: 18

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B01 | basic | basic | FAIL | PASS | FAIL | 42 | 3 | 2 | 36 |
| E2E-B02 | basic | basic | FAIL | FAIL | FAIL | 34 | 7 | 5 | 24 |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 31 | 8 | 15 | 4 |
