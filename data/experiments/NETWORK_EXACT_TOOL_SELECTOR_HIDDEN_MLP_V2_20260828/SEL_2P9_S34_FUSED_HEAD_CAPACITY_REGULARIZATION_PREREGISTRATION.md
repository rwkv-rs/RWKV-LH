# NET-SEL-2P9-S34 fused-head capacity regularization preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Objective and causal hypothesis

S33 established that one same-forward `mean || last` feature improves S30 dev
from `486/500` to `491/500` or `492/500` while retaining S28.  The smaller
h256 head passed more robustness gates than h512: it passed both languages,
all stages, all six sibling boundaries, and every condition except one
per-class recall (`file_digest=17/20`).  The h512 head gained one aggregate
decision but also failed `read_file` recall and the read sibling boundary.

S34 tests only the bounded capacity-regularization hypothesis: a smaller
single MLP may generalize ordered paraphrases more uniformly and eliminate the
remaining class-local overfit.  It does not alter input text, feature fusion,
data, loss, source weights, state, RWKV calls, labels, thresholds, or Executor
behavior.

The current direct `LongHorizonModel -> Harness` architecture remains fixed.
The independent 2.9B Selector chooses one of all 25 exact classes; the
persistent 13.3B Executor alone handles arguments, execution, observations,
continuation, and final summary.

## Frozen identity

- compact V3 protocol SHA-256:
  `976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508`;
- S28/S30 datasets:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`
  and
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`;
- S28/S30 frozen feature manifests:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`
  and
  `65b26ce5f2908ee9415b6bc74fc064c91e33ca1ff5c99207651770b2e877bacd`;
- unchanged 2.9B weights:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- vllm-rwkv revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- zero initial state, physical GPU0, batch-1 persistent history extraction;
- derived feature protocol
  `rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`, exact order
  `mean[2560] || last[2560]`, with both views from the same current forward.

S34 reuses the unweighted combined 8,000-row train-set normalization and
source weights S28=`1`, S30=`1`.  Only train/dev rows may be parsed.  Both test
splits must be skipped before JSON parsing; no test label, test metric,
generated RWKV output, or sampling call is allowed during development.

## Exactly registered candidates

All settings remain seed `1030`, GELU(tanh), LayerNorm, dropout `0.15`,
class-balanced cross entropy with all-one class weights, maximum 80 epochs,
batch 128, AdamW LR `8e-4`, weight decay `1e-3`, cosine schedule, gradient clip
1.0, patience 12, and unchanged S30 best-epoch ordering.

Exactly two widths are registered:

1. `concat-h64`;
2. `concat-h128`.

No h32, h192, alternate seed, dropout, loss, source weight, pooling, state,
data addition, or prompt change may be tried in S34.  Selection is
minimum-capacity: choose h64 if it passes every gate; only if h64 fails may
h128 be chosen.  A passing h128 cannot replace a passing h64 for a higher
score.

## Development and blind gates

Each candidate must independently satisfy the unchanged dev conjunction:

- S30 accuracy and macro-F1 each `>=0.97`;
- S28 accuracy and macro-F1 each `>=0.99`;
- every S30 class recall `>=0.90`;
- English and Chinese each `>=0.96`;
- first, continuation, and completion stages each `>=0.95`;
- future-tool-distractor rows `>=0.95`;
- all six sibling boundaries each `>=0.95`;
- serialized dependency-light replay preserves raw argmax with maximum
  absolute logit difference `<=0.005`;
- same-forward fusion is proven, with zero test-label access, generated text,
  sampling, masking, postprocessing, retry, or Executor fallback.

Only a content-addressed passing head unlocks one S30 blind evaluation.  Blind
requires accuracy/macro-F1 each `>=0.96`, every-label true positives `>=18/20`,
both languages `>=0.95`, all stages `>=0.94`, and future-distractor plus all
sibling boundaries `>=0.95`.  All 25 raw logits and unmodified raw argmaxes
must be retained.

The fusion protocol remains experiment-local until blind passes.  Passing
blind authorizes only the smallest necessary loader/service support, full
regression, and bounded GPU0 shadow canary; it does not activate S31, delete
tools, modify RWKV output, or change the 13.3B Executor.
