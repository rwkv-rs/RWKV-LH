# R19 zero-State stage-repair and evidence-projection preregistration

Date: 2026-09-02. R19 reruns only `AGENT-LADDER-L2-CLI01` after two generic
Stage Checker boundary fixes:

1. a repair patch must replace or discard current frontier work when such a
   frontier exists; appending only later work is rejected by the Controller;
2. the Stage Checker receives only the Harness action records accepted as
   evidence for that stage, with a larger per-result bound for exact read facts.

The task dataset, prompts outside these registered role-contract changes, G1J
weights, all three `zero` RWKV profiles, `concurrency=1`,
`max_transitions=120`, sampling parameters, metrics, and thresholds are
unchanged. Cache keys include the revised prompts, so old StageReview and
correction responses cannot be reused under the new contract. Any new Strong
response still requires complete local and Controller validation before it may
enter the cache.

HTTP 429/500, tunnel failure, or model-service interruption remains an
infrastructure-invalid outcome. Results are written to
`run_g1j_zero_state_v7_compatibility_r19_l2_stage_boundary`; prior runs are not
overwritten.
