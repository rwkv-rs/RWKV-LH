# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

RWKV receives only the user goal, isolated workspace, generic constraints, and the Harness contract. Task Graphs, actions, repair paths, and external acceptance are not provided to the model.

- Cases run: 3
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 0

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 12 | 0 | 0 | 12 |
| AGENT-LADDER-L4-LEDGER01 | hard | tier4_medium_project | FAIL | FAIL | FAIL | 147 | 0 | 10 | 61 |
| AGENT-LADDER-L5-RWKV01 | hard | tier5_networked_project | FAIL | FAIL | FAIL | 12 | 0 | 0 | 12 |
