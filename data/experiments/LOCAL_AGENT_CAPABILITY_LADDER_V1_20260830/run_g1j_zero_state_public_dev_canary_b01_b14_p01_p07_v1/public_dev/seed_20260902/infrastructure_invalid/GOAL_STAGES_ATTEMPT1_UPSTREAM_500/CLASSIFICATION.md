# GOAL_STAGES_ATTEMPT1_UPSTREAM_500

- Classification: infrastructure-invalid; excluded from capability scoring.
- Time: 2026-09-02T12:25:47Z.
- Strong Planner requests: 1.
- Strong Planner result: HTTP 500, provider error type `new_api_error`, code `do_request_failed`.
- RWKV model requests: 0.
- Tool actions: 0.
- Hidden retries: 0.
- Cause: the upstream failed before returning any GoalPlanPatch. No Planner semantics or Agent capability was observed.
- Preservation: `RESULT.json` and `CASE/` are the unmodified run artifacts moved out of the canonical result slot.

This attempt does not change the frozen zero-State baseline score.
