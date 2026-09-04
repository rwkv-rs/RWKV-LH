# RWKV-LH-AGENT-CAPABILITY-LADDER-V1

The Strong Model is the required Planner and emits GoalPlanPatch. The 2.9B Selector decides one exact tool, one persistent 13.3B RWKV Executor State fills parameters and executes, and an isolated RWKV Auditor reviews each boundary; no Strong Reviewer is called.

- Cases run: 1
- Case concurrency: 1
- Agent completed: 0
- External acceptance passed: 0
- Strict E2E passed: 0
- Supervisor requests: 1

| Task | Group | Native level | Agent | External | Strict | RWKV requests | Supervisor requests | Actions | Protocol rejects |
| --- | --- | --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| AGENT-LADDER-L1-FIX01 | basic | tier1_closed_loop | FAIL | FAIL | FAIL | 120 | 1 | 120 | 0 |
