# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 21
- Case concurrency: 4
- Agent completed: 11
- External acceptance passed: 11
- Strict E2E passed: 8
- Supervisor requests: 95

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B06 | basic | basic | PASS | PASS | PASS | 9 | 2 | 5 | 0 |
| E2E-B07 | basic | basic | PASS | PASS | PASS | 12 | 2 | 5 | 3 |
| E2E-B08 | basic | basic | FAIL | PASS | FAIL | 12 | 2 | 7 | 0 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 14 | 11 | 7 | 0 |
| E2E-M09 | medium | medium | FAIL | FAIL | FAIL | 32 | 7 | 19 | 2 |
| E2E-H08 | hard | hard | FAIL | FAIL | FAIL | 15 | 6 | 10 | 0 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 21 | 4 | 12 | 4 |
| E2E-B11 | basic | basic | PASS | PASS | PASS | 10 | 2 | 4 | 2 |
| E2E-B14 | basic | basic | PASS | PASS | PASS | 21 | 8 | 10 | 2 |
| E2E-B18 | basic | basic | FAIL | PASS | FAIL | 10 | 4 | 5 | 0 |
| E2E-B20 | basic | basic | FAIL | FAIL | FAIL | 6 | 4 | 4 | 0 |
| E2E-B21 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 11 | 2 | 5 | 2 |
| E2E-B28 | basic | basic | PASS | PASS | PASS | 8 | 2 | 4 | 0 |
| E2E-M12 | medium | medium | FAIL | PASS | FAIL | 25 | 9 | 13 | 0 |
| E2E-M19 | medium | medium | PASS | FAIL | FAIL | 13 | 8 | 8 | 0 |
| E2E-M21 | medium | medium | PASS | PASS | PASS | 15 | 2 | 6 | 5 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 12 | 2 | 5 | 3 |
| E2E-M30 | medium | medium | FAIL | FAIL | FAIL | 22 | 7 | 11 | 5 |
| E2E-H11 | hard | hard | FAIL | FAIL | FAIL | 17 | 4 | 9 | 4 |
| E2E-H17 | hard | hard | FAIL | FAIL | FAIL | 5 | 5 | 3 | 0 |
