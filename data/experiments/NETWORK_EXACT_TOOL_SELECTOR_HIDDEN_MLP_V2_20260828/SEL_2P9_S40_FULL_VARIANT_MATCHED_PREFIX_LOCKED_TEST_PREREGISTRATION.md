# SEL-2P9-S40 full-variant matched-prefix locked test preregistration

## Status and claim boundary

S39 selected the first and smallest preregistered candidate, `concat-h64`, on
train/dev only. It achieved 839/857 S39 prefix decisions (97.90%, macro F1
98.20%) and 750/750 S28 retention decisions on dev; every preregistered
subgroup gate passed. S40 is the one-shot source-heldout test of that locked
Head. The S39 test source pool has zero source-ID overlap with train and dev.

Dataset construction and contract validation necessarily established test
counts and labels, but no S39 test Head prediction or metric has been computed,
and no test row has participated in training, normalization, capacity choice,
early stopping, threshold choice, or any other selection. No S40 result may be
used to retune this Head or add a test-specific rule.

## Frozen identities

- Dev selection:
  `data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s39_full_variant_matched_prefix_head_dev_selection/DEV_SELECTION.json`
- Dev selection SHA-256:
  `d1261c8c19b2b16644c52c58e0124a9860d0bc86f554c60afa5b602f97022571`
- Locked Head:
  `data/experiments/NETWORK_EXACT_TOOL_SELECTOR_HIDDEN_MLP_V2_20260828/run_s39_full_variant_matched_prefix_head_dev_selection/candidates/concat-h64/selector_head.json`
- Head file SHA-256:
  `e2c4ffa85bb98637f8ba3dd2caf5789b732f2bb43ebc9b19bc4242e0ff3063dd`
- Head hash:
  `73ecba1dcd84a2b8005d486b71fad210b1aab2f9981e8e04b2b7c90846ade7a7`
- Portable model hash:
  `479f6f1f1ee740003e8cd76036a8b580c1151d7084e83a43018dd73eba8b641a`
- S39 dataset SHA-256:
  `b85ff487cd0902743ede4299c651f3af4a5fa92f0a1240edb3e89b68b7ac0dab`
- S39 feature manifest SHA-256:
  `b56e5cefab701128f7217bdecb00f2c1bd64b9505b8be61d9e55a1fc78c13481`
- S28 dataset SHA-256:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
- S28 feature manifest SHA-256:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
- Model weights SHA-256:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`
- Feature: same-forward `[mean, last]` concat, dimension 5120, protocol
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`.
- State: explicit native zero state. No state-tuned profile is active.
- Ordered output labels: the unchanged 25 canonical classes.

## Frozen evaluation sets

1. All and only 857 S39 `test` prefix rows: 500 source-heldout
   trajectories, 357 history positions, and 500 current positions. The fixed
   matched-depth schedule is identical in policy to train/dev, and every split
   allows all six contract variants inside its own isolated source pool.
2. All and only 750 S28 `test` rows, balanced at 30 rows for each canonical
   class, as the retention check that the complete Harness tool space remains.

Before parsing any test JSON label, the evaluator must validate every frozen
file identity, Head identity, feature-shard digest, protocol, shape, finiteness,
opaque ID, and split order. It must support a label-free preflight. On the
one-shot run it must create an immutable `EVALUATION_STARTED.json` before label
parsing and must refuse to replace any existing S40 output.

## Frozen inference and metrics

- Use the locked Head's stored mean/std and weights; never recompute
  normalization from test data.
- Use the production `TorchNetworkSelectorHead` float32 forward. Preserve all
  25 raw logits and deterministic raw argmax. Fixed portable replay must have
  equal argmax and maximum absolute logit difference at most 0.005.
- Do not apply temperature to argmax, generate text, sample, postprocess,
  normalize labels, repair errors, retry, fall back, execute tools, or call the
  13.3B Executor.
- Exact label equality is the correctness metric. Report accuracy, macro F1,
  per-class precision/recall/F1/support, confusion, S39 history/current,
  language, positions 0/1/2, and the six frozen sibling boundaries. Report S28
  total and every-class retention.
- No additional RWKV forward is permitted in S40. The frozen cache is evaluated
  first; the real local GPU0 product service is a separate canary only after all
  S40 gates pass.

## Acceptance gates

S40 passes only if every gate passes:

1. exact counts are S39 857 = 357 history + 500 current and S28 750;
2. S39 accuracy and 25-class macro F1 are each at least 0.96;
3. S39 history and current accuracy are each at least 0.96;
4. both S39 languages and every present position are at least 0.95;
5. every supported S39 class has recall at least 0.90;
6. all six sibling-boundary groups are at least 0.95;
7. S28 retention accuracy and macro F1 are each at least 0.99, and every one of
   its 25 classes has a nonzero true positive;
8. all raw logits are finite, unmodified, and exactly 25-wide; portable replay
   meets the fixed 0.005/equal-argmax bound;
9. test rows are not used for training, selection, or normalization;
   generation, sampling, postprocessing, retries, fallback, extra RWKV
   forwards, tool execution, and Executor calls are all zero.

## Decision rule

- Pass: unlock one real local GPU0 V3 product canary using this exact Head and
  zero state. `.env.local` remains unchanged until the canary itself passes.
- Fail: keep product activation locked and record the result without tuning or
  adding exceptions against S40 errors.
