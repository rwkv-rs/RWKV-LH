# Round1 2K post-deployment evaluation protocol

Frozen before any tuned checkpoint is deployed or evaluated.

## Primary causal comparison

Run the same 200 held-out failure-boundary prompts through the same vLLM
`/v1/completions` endpoint and sampling contract used for the frozen baseline:

- temperature 0.05, top-p 1, top-k 0;
- no request seed (unsupported by the vLLM-RWKV rapid sampler);
- progressive Controller-rendered prompts;
- 160 selector / 256 direct output-token cap;
- concurrency 32;
- same dev SHA256.

Metrics are schema-valid rate, operation accuracy, and exact transition accuracy,
overall and for all 6 clusters / 13 failure signatures. Baseline is fixed at 61.5%,
59.0%, and 16.0% respectively. No threshold or parser may be changed after seeing
tuned results.

## System regression and Harness scope

1. Actual `ModelSession` progressive selector + direct-call smoke on the tuned server.
2. Frozen ECRA route120, variant A and variant B, direct architecture. This tests
   local-vs-retrieval routing, privacy Gate, and no-live-network behavior.
3. Frozen RWKV E2E all90 without a supervisor, progressive mode, to isolate RWKV state.
4. Frozen RWKV E2E all90 with the existing strong planner/reviewer contract-graph
   architecture, progressive mode, to validate the complete active Harness.
5. Engineering-only exclusions (lease fencing, recovery, evidence truncation,
   deterministic evaluator boundaries, HTTP lifecycle) remain code/test regressions;
   they are not counted as state-tuning wins or failures.

Every run uses a new output directory under this experiment. The tuned 200-row result
is compared only with `baseline_live_dev200.json`; historical benchmark runs are
context, not substituted baselines.
