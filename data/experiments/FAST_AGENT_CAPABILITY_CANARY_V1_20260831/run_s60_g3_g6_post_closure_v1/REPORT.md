# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 21

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 38 | 4 | 10 | 24 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 66 | 6 | 24 | 36 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 138 | 11 | 39 | 84 |
