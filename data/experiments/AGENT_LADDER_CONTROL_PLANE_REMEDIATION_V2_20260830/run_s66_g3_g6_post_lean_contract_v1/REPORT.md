# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 10
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 90

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 87 | 18 | 30 | 46 |
| AGENT-LADDER-L1-DATA01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 8 | 6 | 5 | 2 |
| AGENT-LADDER-L2-CLI01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 31 | 8 | 22 | 5 |
| AGENT-LADDER-L2-REPAIR01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 10 | 5 | 7 | 1 |
| AGENT-LADDER-L3-WEB01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 13 | 5 | 2 | 12 |
| AGENT-LADDER-L3-QUEUE01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 63 | 12 | 10 | 50 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 13 | 5 | 3 | 12 |
| AGENT-LADDER-L4-TRACKER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 63 | 14 | 13 | 41 |
| AGENT-LADDER-L5-PACKAGING01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 80 | 13 | 25 | 52 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 6 | 4 | 4 | 0 |
