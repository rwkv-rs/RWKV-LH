# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 2
- External acceptance passed: 2
- Strict E2E passed: 1
- Supervisor requests: 15

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-M10 | medium | medium | PASS | PASS | PASS | 16 | 6 | 7 | 4 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 21 | 2 | 9 | 3 |
| E2E-M15 | medium | medium | FAIL | PASS | FAIL | 46 | 7 | 9 | 26 |
