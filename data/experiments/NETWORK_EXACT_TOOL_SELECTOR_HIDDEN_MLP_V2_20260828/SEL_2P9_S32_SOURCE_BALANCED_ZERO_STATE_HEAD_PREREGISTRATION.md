# NET-SEL-2P9-S32 source-balanced zero-state head preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Decision being tested

S32 tests one narrowly defined explanation for the remaining route errors: the
S30 head was trained on 6,000 synthetic-capability S28 rows and only 2,000
natural true-trajectory S30 rows.  Both sources are individually balanced over
all 25 exact classes, so the existing class-balanced loss leaves S28 with 75%
of the training-row mass.  S30 dev reached `486/500`, but failed the English,
`read_file`, and `read_file/read_json` gates.  S31 then proved that its learned
state changes hidden features but changes only one fixed-head decision.  S32
therefore changes the head's **source contribution only**, before considering
another state.

The architecture remains the current direct
`LongHorizonModel -> Harness` architecture: an independent 2.9B Selector emits
one of all 25 exact classes, and the persistent 13.3B Executor alone binds
arguments, executes tools, observes results, continues, and summarizes.  S32
does not add a Planner, keyword router, tool mask, retry, output repair,
generated Selector text, 13.3B selection fallback, or any extra model call.

## Frozen inputs and single independent variable

S32 reuses, without re-extraction:

- S28 dataset SHA-256
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`;
- S30 dataset SHA-256
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`;
- S28 zero-state feature manifest SHA-256
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`;
- S30 zero-state feature manifest SHA-256
  `65b26ce5f2908ee9415b6bc74fc064c91e33ca1ff5c99207651770b2e877bacd`;
- compact V3 protocol SHA-256
  `976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508`;
- unchanged 2.9B model weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- vllm-rwkv revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- physical GPU0, batch-1, zero initial state, persistent history replay, and
  current-step mean hidden feature protocol
  `rwkv-lh.vllm-rwkv-final-hidden-mean.v1`.

Only S28/S30 train and dev rows may be parsed.  Both test splits must still be
skipped before JSON parsing.  The two frozen feature caches contain no labels;
no test label, test metric, generated RWKV output, or sampling call is allowed
during S32 development.

The architecture is fixed to the already selected S30 `mean-h512` MLP.  It is
trained from scratch with the same seed `1030`, unweighted combined-train
feature mean/std, GELU(tanh), LayerNorm, dropout `0.15`, maximum 80 epochs,
batch 128, AdamW LR `8e-4`, weight decay `1e-3`, cosine schedule, gradient clip
1.0, patience 12, and the unchanged S30 best-epoch ordering.  Because each
source is exactly class-balanced, the existing combined class weights remain
all ones.

The only independent variable is the S30 per-sample loss multiplier.  For a
minibatch, unreduced cross entropy is multiplied by source weight and divided
by the sum of source weights in that minibatch.  S28 weight is always `1`.
Exactly two candidates are registered:

1. `s30w3`: S30 weight `3`, giving equal aggregate source mass
   (`6000 : 2000*3`);
2. `s30w5`: S30 weight `5`, giving a bounded natural-trajectory emphasis
   (`6000 : 2000*5`).

No other weight, feature view, width, seed, state, dataset, prompt, epoch
limit, or threshold may be tried in S32.  The existing unweighted S30 head
(file SHA-256
`26c3eb50d399106f3967742154e31cfaf5663bdbcb5489695dd5ce12e7cb7ef6`)
is the frozen weight-1 reference and is not a third trainable candidate.

## Development gates and deterministic selection

Each candidate must independently satisfy the unchanged S30 gates:

- S30 accuracy and macro-F1 each `>=0.97`;
- S28 retention accuracy and macro-F1 each `>=0.99`;
- every S30 label recall `>=0.90`;
- English and Chinese S30 accuracy each `>=0.96`;
- first, continuation, and completion stage accuracy each `>=0.95`;
- future-tool-distractor accuracy `>=0.95`;
- each registered sibling boundary accuracy `>=0.95`:
  `read_file/read_json`,
  `search_text/web_search/connector_lookup`,
  `write_file/write_json/patch_json`,
  `copy_file/move_file`,
  `check_command/run_command`, and
  `final_answer/ABSTAIN`;
- portable JSON-head replay preserves raw argmax and has maximum absolute
  logit difference `<=0.005`;
- test-label access, generated output, sampling, masking, postprocessing,
  retry, and Executor fallback all remain zero.

Selection is deliberately minimum-change rather than metric-maximizing:
choose `s30w3` if it passes every gate; otherwise choose `s30w5` only if it
passes every gate; otherwise reject S32.  A passing `s30w5` cannot replace a
passing `s30w3` merely because its score is higher.

## Blind lock

Only a selected and content-addressed head unlocks one S30 blind evaluation.
The one-shot blind gates remain exactly those preregistered for S30:

- exact accuracy and macro-F1 each `>=0.96`;
- every-label true positives `>=18/20`;
- English and Chinese each `>=0.95`;
- first, continuation, and completion groups each `>=0.94`;
- future-tool-distractor rows and every sibling boundary each `>=0.95`.

All 25 raw logits and the raw argmax must be retained.  Temperature may be
stored but cannot change the argmax.  Any mask, repair, threshold override,
retry, generated output, sampling, or 13.3B fallback rejects the run.

Passing S32 only authorizes regression evaluation and a bounded shadow canary
after the V3 client/service protocol is synchronized.  It does not activate
the S31 state, alter `.env.local`, delete any tool, modify the 13.3B Executor,
or establish full Harness quality by itself.
