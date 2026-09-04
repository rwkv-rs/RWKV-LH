# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 13
- Case concurrency: 4
- Agent completed: 7
- External acceptance passed: 4
- Strict E2E passed: 4
- Supervisor requests: 37

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 13 | 2 | 6 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-M10 | medium | medium | PASS | FAIL | FAIL | 23 | 6 | 7 | 4 |
| E2E-H09 | hard | hard | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-LH04 | hard | long_horizon | PASS | FAIL | FAIL | 20 | 6 | 7 | 1 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-B22 | basic | basic | PASS | PASS | PASS | 16 | 2 | 4 | 2 |
| E2E-M15 | medium | medium | PASS | FAIL | FAIL | 13 | 2 | 6 | 1 |
| E2E-M16 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 41 | 10 | 17 | 7 |
| E2E-M28 | medium | medium | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
