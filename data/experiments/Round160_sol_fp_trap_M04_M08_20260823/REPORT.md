# RWKV-E2E-90

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 2
- Case concurrency: 2
- Agent completed: 2
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 8

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| E2E-M04 | medium | medium | PASS | FAIL | FAIL | 17 | 2 | 8 | 1 |
| E2E-M08 | medium | medium | PASS | FAIL | FAIL | 26 | 6 | 12 | 2 |
