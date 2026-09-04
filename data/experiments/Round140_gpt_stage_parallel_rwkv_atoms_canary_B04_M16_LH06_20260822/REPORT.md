# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 2
- External acceptance passed: 1
- Strict E2E passed: 1
- Supervisor requests: 18

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 10 | 3 | 7 | 1 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 146 | 12 | 125 | 13 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 25 | 3 | 12 | 12 |
