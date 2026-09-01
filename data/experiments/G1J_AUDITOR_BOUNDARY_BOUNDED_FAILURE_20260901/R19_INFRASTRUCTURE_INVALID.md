# R19 infrastructure-invalid result

Date: 2026-09-02. R19 retained the fixed L2 data, G1J weights, all-zero role
profiles, sampling, and 120-transition budget. The initial Controller-validated
GoalPlan was reused. G1J then completed `A00001=list_directory` and
`A00002=read_file(verify_project.py)` before the revised Stage Checker request.

The new evidence projection reduced the request from R18's `input_chars=19006`
to `input_chars=5734`. Both HTTP attempts still returned 429. The directly
reviewable records are:

- `audit.json.supervisor_trace[1]`: `phase=goal_stage_review`,
  `input_chars=5734`;
- `audit.json.supervisor_trace[2:4]`: HTTP attempts 1 and 2;
- `audit.json.supervisor_trace[4]`: `error_category=rate_limit`,
  `http_status=429`;
- `results.json.results[0].supervisor_failure`: one unresolved retryable Strong
  request and no terminal RWKV answer.

Therefore request bloat was a real engineering issue but is not the cause of
the current 429. The earliest failed layer in R19 is Strong relay
infrastructure. Both actions and their Auditor boundaries occurred before that
failure; no event after the failed Strong boundary is eligible for model
capability scoring or State Tune extraction.
