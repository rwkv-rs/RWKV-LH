# RWKV-E2E-30

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 1
- Case concurrency: 1
- Agent completed: 1
- External acceptance passed: 1
- Strict E2E passed: 1
- Supervisor requests: 2

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B02 | basic | basic | PASS | PASS | PASS | 10 | 2 | 3 | 0 |
