# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 13
- Case concurrency: 4
- Agent completed: 8
- External acceptance passed: 4
- Strict E2E passed: 3
- Supervisor requests: 50

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B04 | basic | basic | PASS | PASS | PASS | 17 | 8 | 8 | 1 |
| E2E-B09 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-M10 | medium | medium | FAIL | FAIL | FAIL | 12 | 6 | 6 | 0 |
| E2E-H09 | hard | hard | PASS | PASS | PASS | 11 | 2 | 4 | 3 |
| E2E-LH04 | hard | long_horizon | FAIL | FAIL | FAIL | 14 | 7 | 7 | 0 |
| E2E-LH06 | hard | long_horizon | PASS | FAIL | FAIL | 14 | 2 | 7 | 0 |
| E2E-LH08 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| E2E-LH09 | hard | long_horizon | PASS | FAIL | FAIL | 20 | 2 | 8 | 4 |
| E2E-B22 | basic | basic | PASS | FAIL | FAIL | 9 | 2 | 4 | 1 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 6 | 1 | 4 | 0 |
| E2E-M16 | medium | medium | PASS | FAIL | FAIL | 27 | 10 | 13 | 1 |
| E2E-M24 | medium | medium | FAIL | PASS | FAIL | 16 | 5 | 9 | 1 |
| E2E-M28 | medium | medium | PASS | FAIL | FAIL | 17 | 2 | 8 | 2 |
