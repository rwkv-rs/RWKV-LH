# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 3
- Strict E2E passed: 3
- Supervisor requests: 13

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | PASS | PASS | 19 | 5 | 9 | 2 |
| E2E-M16 | medium | medium | PASS | PASS | PASS | 14 | 4 | 8 | 0 |
