# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 3
- External acceptance passed: 2
- Strict E2E passed: 2
- Supervisor requests: 17

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 8 | 4 | 4 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | PASS | PASS | 20 | 7 | 11 | 0 |
| E2E-M16 | medium | medium | PASS | FAIL | FAIL | 17 | 6 | 12 | 0 |
