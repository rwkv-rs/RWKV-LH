# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 15
- Case concurrency: 4
- Agent completed: 5
- External acceptance passed: 2
- Strict E2E passed: 1
- Supervisor requests: 74

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-B10 | basic | basic | FAIL | FAIL | FAIL | 23 | 3 | 11 | 2 |
| E2E-M04 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M05 | medium | medium | PASS | PASS | PASS | 13 | 7 | 6 | 1 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 20 | 9 | 8 | 5 |
| E2E-LH06 | hard | long_horizon | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-B13 | basic | basic | FAIL | PASS | FAIL | 16 | 6 | 7 | 3 |
| E2E-B21 | basic | basic | PASS | FAIL | FAIL | 22 | 9 | 12 | 0 |
| E2E-B22 | basic | basic | FAIL | FAIL | FAIL | 14 | 6 | 7 | 0 |
| E2E-B24 | basic | basic | FAIL | FAIL | FAIL | 29 | 3 | 15 | 5 |
| E2E-B25 | basic | basic | PASS | FAIL | FAIL | 10 | 2 | 5 | 1 |
| E2E-M15 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M23 | medium | medium | FAIL | FAIL | FAIL | 0 | 2 | 0 | 0 |
| E2E-M24 | medium | medium | FAIL | FAIL | FAIL | 34 | 6 | 10 | 16 |
| E2E-M27 | medium | medium | FAIL | FAIL | FAIL | 14 | 6 | 7 | 0 |
| E2E-M29 | medium | medium | PASS | FAIL | FAIL | 26 | 9 | 11 | 5 |
