# SEL-2P9-S37 prefix-closed locked test regression preregistration

## Status and claim boundary

S36 selected the first and smallest preregistered candidate, `concat-h64`, on
train/dev only.  It achieved 751/765 S36 prefix decisions (98.17%, macro F1
98.36%) and 750/750 S28 retention decisions on dev, with every registered
subgroup gate passing.  S37 evaluates the locked Head on test only.

S37 is a fixed confirmatory regression, not a blind claim: S35 already exposed
aggregate and per-class S30 test behavior for the former Head.  No S37 test
result may be used to choose capacity, loss weights, features, state, or
thresholds.

## Frozen identities

- Dev selection:
  `data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s36_prefix_closed_head_dev_selection/DEV_SELECTION.json`
- Dev selection SHA-256:
  `a75f55d3e97c84275fc6f16d834b85bcebe528304958085941f49e8218b70e02`
- Locked Head:
  `data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s36_prefix_closed_head_dev_selection/candidates/concat-h64/selector_head.json`
- Head file SHA-256:
  `c35c5e4301b6d0e814c54540fbe909e350603dc3894e07a83b5a9738a25162c2`
- Head hash:
  `c68c7ce8b630591fd8a222963eb4c03a39966bd09347e5df3951198e3bdbc134`
- Portable model hash:
  `10fc04d0509accd9d5cabbb29cd68128b8faa0395017c49e465d2ca92ddb3ab8`
- S36 dataset SHA-256:
  `e837eee8772ce3cfb9d34f2492d8a6bffed78b5b158969bc39f75fd1931c1ca5`
- S36 feature manifest SHA-256:
  `1fb08fef225340e90c97c84fc0570cbdc46ea95571d48f32393c51f832d1be29`
- S28 dataset SHA-256:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
- S28 feature manifest SHA-256:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
- Model weights SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Feature: same-forward `[mean, last]` concat, dimension 5120, protocol
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`.
- State: explicit native zero state.  No state-tuned profile is active.
- Ordered output labels: the unchanged 25 canonical classes.

## Frozen evaluation sets

1. All and only 995 S36 `test` prefix rows: 500 trajectories, 495 history
   positions, and 500 current positions.  This is the same deployment closure
   audited by S35, now represented by opaque S36 prefix IDs.
2. All and only 750 S28 `test` rows, balanced at 30 rows for each canonical
   class, as the hard retention check that other Harness functions did not
   disappear.

Before parsing any test JSON row, the evaluator must validate all file, Head,
feature-shard, protocol, shape, finiteness, opaque-ID, and split identities and
write an immutable `EVALUATION_STARTED.json` containing its own hash.  It must
refuse to replace any existing S37 output.

## Frozen inference and metrics

- Use the locked Head's stored feature mean/std and weights.  Do not recompute
  normalization from test data.
- Compute the exact MLP float32 forward and retain all 25 raw logits and their
  deterministic raw argmax.  Portable dependency-light replay on fixed rows
  must have equal argmax and maximum absolute logit difference at most 0.005.
- Do not apply temperature to argmax, generate text, sample, postprocess,
  normalize labels, repair errors, retry, fall back, execute tools, or call the
  Executor.
- Exact label equality is the only correctness metric.
- Report accuracy, macro F1, per-class precision/recall/F1/support, confusion,
  S36 history/current, language, positions 0/1/2, and the six frozen sibling
  boundaries; report S28 total and every-class retention.
- No additional RWKV forward is permitted; S37 evaluates the frozen feature
  cache and then requires a separate real GPU0 product canary.

## Acceptance gates

S37 passes only if all gates pass:

1. exact counts are S36 995 = 495 history + 500 current and S28 750;
2. S36 accuracy and 25-class macro F1 are each at least 0.96;
3. S36 history and current accuracy are each at least 0.96;
4. both S36 languages and each present position are at least 0.95;
5. each supported S36 class has recall at least 0.90;
6. all six sibling-boundary groups are at least 0.95;
7. S28 retention accuracy and macro F1 are each at least 0.99, and every one of
   its 25 classes has nonzero true positives;
8. all raw logits are finite, unmodified, and exactly 25-wide; portable replay
   meets the fixed 0.005/equal-argmax bound;
9. test rows are not used for training/selection/normalization; generation,
   sampling, postprocessing, retries, fallback, extra RWKV forwards, tool
   execution, and Executor calls are all zero.

## Decision rule

- Pass: unlock one real local GPU0 V3 product canary using this exact Head and
  zero state.  `.env.local` remains unchanged until that canary passes.
- Fail: keep product activation locked and record the failure.  Do not tune or
  add exceptions against S37 test errors.
