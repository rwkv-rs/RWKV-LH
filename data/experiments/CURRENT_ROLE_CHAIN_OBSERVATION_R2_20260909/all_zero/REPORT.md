# RWKV-LH-REAL-PROJECT-DEV-V1

The Strong Model is the required Planner and emits GoalPlanPatch. The 2.9B Selector decides one exact tool, one persistent 13.3B RWKV Executor State fills parameters and executes, and an isolated RWKV Auditor reviews each boundary; no Strong Reviewer is called.

- Cases run: 3
- Case concurrency: 3
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 5

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| RP-API-01 | project | project | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
| RP-API-02 | project | project | FAIL | FAIL | FAIL | 0 | 3 | 0 | 0 |
| RP-MAINT-01 | project | project | FAIL | FAIL | FAIL | 0 | 1 | 0 | 0 |
