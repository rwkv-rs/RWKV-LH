# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 3

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
