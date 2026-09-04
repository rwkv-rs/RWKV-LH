# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 23

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-DATA01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 60 | 6 | 27 | 24 |
| AGENT-LADDER-L2-REPAIR01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 100 | 9 | 40 | 42 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 66 | 8 | 32 | 24 |
