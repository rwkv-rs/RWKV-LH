# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 1
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 1
- Strict E2E passed: 0
- Supervisor requests: 5

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | FAIL | PASS | FAIL | 10 | 5 | 5 | 0 |
