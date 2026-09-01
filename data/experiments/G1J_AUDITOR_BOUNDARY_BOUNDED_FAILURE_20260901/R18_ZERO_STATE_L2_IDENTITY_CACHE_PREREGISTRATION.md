# R18 zero-State L2 identity-normalized cache rerun preregistration

Date: 2026-09-02. R18 reruns only `AGENT-LADDER-L2-CLI01` after the Strong
structured-response cache key stopped treating random run, audit, review, and
rejected-patch identifiers as semantic request material.

The task dataset, prompts, G1J weights, all three `zero` RWKV profiles,
`concurrency=1`, `max_transitions=120`, sampling parameters, metrics, and
thresholds remain unchanged. The initial GoalPlan and first StageReview repair
may use only responses that were previously accepted by the Controller. The
repair response was re-keyed only after its complete generated `GoalPlanPatch`
matched the durable committed R14 patch and applied successfully to the current
R17 plan boundary. Any new Strong request must still be generated live and pass
the full Controller validation before it can enter the cache.

HTTP 429/500, tunnel failure, or model-service interruption remains an
infrastructure-invalid outcome. Results are written to
`run_g1j_zero_state_v7_compatibility_r18_l2_identity_cache`; prior runs are not
overwritten.
