# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 1
- External acceptance passed: 1
- Strict E2E passed: 1
- Supervisor requests: 24

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 11 | 4 | 8 | 1 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 33 | 8 | 20 | 1 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 65 | 12 | 40 | 15 |
