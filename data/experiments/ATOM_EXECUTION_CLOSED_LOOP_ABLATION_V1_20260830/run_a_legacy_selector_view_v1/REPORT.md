# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, Harness contract, and bounded supervisor plan/review feedback. The supervisor does not receive hidden external acceptance and cannot execute actions.

- Cases run: 10
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 73

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 61 | 6 | 8 | 48 |
| AGENT-LADDER-L1-DATA01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 79 | 10 | 18 | 52 |
| AGENT-LADDER-L2-CLI01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 135 | 14 | 40 | 75 |
| AGENT-LADDER-L2-REPAIR01 | basic | tier2_small_workflow | FAIL | FAIL | FAIL | 111 | 6 | 29 | 72 |
| AGENT-LADDER-L3-WEB01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 92 | 4 | 11 | 82 |
| AGENT-LADDER-L3-QUEUE01 | medium | tier3_cross_file | FAIL | FAIL | FAIL | 33 | 7 | 7 | 27 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 107 | 6 | 14 | 76 |
| AGENT-LADDER-L4-TRACKER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 65 | 6 | 23 | 38 |
| AGENT-LADDER-L5-PACKAGING01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 5 | 4 | 3 | 1 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 47 | 10 | 21 | 25 |
