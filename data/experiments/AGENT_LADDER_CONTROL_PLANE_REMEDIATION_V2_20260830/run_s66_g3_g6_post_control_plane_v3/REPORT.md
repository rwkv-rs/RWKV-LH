# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 10
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 82

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 39 | 10 | 22 | 1 |
| AGENT-LADDER-L1-DATA01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 25 | 12 | 14 | 1 |
| AGENT-LADDER-L2-CLI01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 19 | 6 | 14 | 0 |
| AGENT-LADDER-L2-REPAIR01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 32 | 6 | 21 | 5 |
| AGENT-LADDER-L3-WEB01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 27 | 7 | 16 | 5 |
| AGENT-LADDER-L3-QUEUE01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 49 | 6 | 14 | 35 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 101 | 15 | 38 | 58 |
| AGENT-LADDER-L4-TRACKER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 77 | 8 | 17 | 45 |
| AGENT-LADDER-L5-PACKAGING01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 26 | 6 | 9 | 13 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 11 | 6 | 8 | 0 |
