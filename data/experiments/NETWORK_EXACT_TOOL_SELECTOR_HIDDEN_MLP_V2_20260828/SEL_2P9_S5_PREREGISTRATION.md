# NET-SEL-2P9-S5 description-conditioned Selector preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Motivation and boundary

S3/S4 prove that a fixed 25-class MLP can reach perfect in-distribution scores
while failing ECRA120 after target leakage is removed.  S5 changes the head to
score the request against the actual frozen tool names/descriptions.  It does
not use schemas, arguments, results, Executor text, ECRA rows, generated RWKV
text, rules, postprocessing, constrained decoding, or RWKV weight changes.

## Frozen input projection

Source is S3 cases SHA-256
`34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c`.
Each request becomes canonical `SelectorQueryV3` containing one non-duplicated
task/objective string, `role=work`, and compact causal progress.  Failure
cluster and the 25-tool menu are absent from every per-request RWKV input.

Each of the 25 frozen v2 names/descriptions becomes one canonical
`ToolDescriptionV3`.  These descriptions are extracted once and shared across
requests.  The class order and menu digest remain the authoritative v2 values.
Any description change invalidates the artifact and requires retraining.

Train/dev/test counts, labels, families and ECRA similarity gates remain those
of S3.  Exact query duplicates and split-family overlap must be zero.  Query
and description files, source, generator, protocol and manifest are SHA-pinned.

## Frozen features and head

- frozen 2.9B base, zero initial state, pinned local vLLM-RWKV revision;
- batch 1, FP16 WKV, last real-token hidden only;
- no generation, sampling, pooling selection, state tuning, or state reuse;
- query and tool vectors each use per-vector layer normalization;
- separate learned linear projections `2560 -> 128`, GELU, then LayerNorm;
- for every request/tool pair concatenate `q`, `t`, `q*t`, and `abs(q-t)`;
- shared scorer `512 -> 64 -> 1`, GELU and dropout 0.1;
- no per-class bias or class-specific output weights;
- inverse train-class-frequency cross-entropy;
- seed 839, AdamW, LR 1e-3, weight decay 1e-3, batch 64, maximum 100 epochs,
  cosine schedule, gradient clip 1.0, patience 15;
- best epoch by dev macro-F1, with weighted dev loss as fixed tie-breaker;
- raw 25 scores and deterministic raw argmax only.

## Frozen gates

The S3 synthetic retention, 176-row natural dev cluster, and ECRA120 gates are
unchanged.  Additionally:

- tool order/name/description digest must match the live frozen menu;
- query maximum token count must be <= 256 and at least 4x lower than the S3
  maximum 1348;
- description maximum token count must be <= 64;
- no class-specific scorer parameter may exist;
- query/tool extraction generation and sampling counts must be zero.

Passing S5 authorizes only a guarded zero-state Selector integration.  S2
state remains rejected.  Function-scoped state tuning and 13.3B network state
tuning require separate later protocols.
