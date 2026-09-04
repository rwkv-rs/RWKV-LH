# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 5
- Case concurrency: 4
- Agent completed: 2
- External acceptance passed: 1
- Strict E2E passed: 0
- Supervisor requests: 23

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-M10 | medium | medium | FAIL | PASS | FAIL | 28 | 8 | 7 | 15 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 22 | 5 | 11 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 22 | 2 | 9 | 4 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 16 | 2 | 7 | 2 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 26 | 6 | 11 | 4 |
