# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 10
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 68

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 33 | 6 | 22 | 1 |
| AGENT-LADDER-L1-DATA01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 57 | 6 | 16 | 36 |
| AGENT-LADDER-L2-CLI01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 37 | 7 | 17 | 12 |
| AGENT-LADDER-L2-REPAIR01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 39 | 7 | 18 | 15 |
| AGENT-LADDER-L3-WEB01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 78 | 6 | 43 | 18 |
| AGENT-LADDER-L3-QUEUE01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 83 | 6 | 26 | 48 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 60 | 6 | 19 | 36 |
| AGENT-LADDER-L4-TRACKER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 67 | 6 | 23 | 36 |
| AGENT-LADDER-L5-PACKAGING01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 127 | 10 | 43 | 72 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 80 | 8 | 35 | 37 |
