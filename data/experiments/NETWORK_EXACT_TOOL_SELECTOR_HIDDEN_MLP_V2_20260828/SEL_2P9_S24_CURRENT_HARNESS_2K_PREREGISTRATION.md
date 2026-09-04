# NET-SEL-2P9-S24 current-Harness 2K preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Architecture boundary

S24 is registered only for the current product chain:

`LongHorizonModel -> Harness`, with one independent persistent 2.9B RWKV
Selector lane and the existing persistent 13.3B RWKV Executor lane.  The
Selector receives the immutable request, the frozen 25 name/description menu,
and the current direct-stage compact projection.  It chooses one exact class
from unmodified 25-way logits.  Only after that choice does the Executor receive
the selected operation's schema and generate its arguments or final answer.

This experiment does not introduce a Planner, atomic objectives, a replacement
Harness, an Executor fallback, generated Selector text, sampling, logit masks,
or output repair.  Selector and Executor checkpoints remain separate.  No RWKV
raw output may be edited, discarded, induced, or hidden.

## Dataset construction

The sole training source is the frozen S3 corpus with SHA-256
`34c436927c84eda252c0c835c9b4c59073bc6fd2327dcb37d17fcf90a85f3b6c`.
Its existing train/dev/test semantic-family split and labels remain unchanged:
2,000 train, 276 dev, and 250 test rows.  S23 ECRA current-Harness decision
points remain external evaluation only and may never enter training, model
selection, calibration, or threshold selection.

S3 progress is mechanically projected into a state that the current Harness can
produce:

- the immutable `task_request` and frozen menu are retained exactly;
- `stage_role` is `work`;
- `stage_objective` uses
  `rwkv-lh.current-direct-selector-stage.v1` only;
- every continuation exposes at most the latest one operation, preferring the
  last recorded failed operation when S3 contains both success and failure;
- `completed_stage_count == action_index`, and the latest action sequence is the
  same index;
- a source row with a positive action index but no observable operation is reset
  to a valid first-decision projection instead of inventing an operation;
- no operation arguments, tool schemas, full results, workspace content,
  Executor text, or expected label enter the compact state projection.

The source task request is compared with frozen ECRA120 instructions using
`utf8-byte-5gram-cosine.v1`; the maximum similarity must remain strictly below
0.75.  Exact rendered-input duplicates and semantic-family overlap across
splits must remain zero.  All 25 labels must remain represented in every split.

## Fixed feature and training protocol

- physical device: GPU0 only (`CUDA_VISIBLE_DEVICES=0`);
- local modified `vllm-rwkv` revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- 2.9B weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- batch size 1, FP16 WKV runtime, no generation and no sampling;
- zero learned Selector state for the first ablation;
- for each independent sample, process `SelectorBootstrapV2` into the same
  recurrent state, then append only `\nSelectorStepV2`;
- train from the unmodified mean of final-layer hidden vectors over the current
  step segment (`rwkv-lh.vllm-rwkv-final-hidden-mean.v1`);
- MLP: 2560 -> 256 -> 25, GELU, LayerNorm, dropout 0.2;
- seed 829, AdamW, learning rate 1e-3, weight decay 1e-3, batch 128,
  at most 60 epochs, early-stop patience 10;
- inverse-frequency class-balanced cross-entropy is fixed before extraction;
- model selection uses dev macro-F1, with dev loss only as a registered tie
  breaker; the test split is evaluated once after the head is frozen.

Feature shards are append-only and content-addressed.  The full raw 25 logits,
their digest, and the raw argmax are retained for every evaluated row.

## Frozen gates

The frozen S24 test split must achieve all of:

- exact accuracy >= 0.90;
- macro-F1 >= 0.90;
- recall of every class >= 0.75;
- recall of each of `web_search`, `connector_lookup`, `calculator`, `date_diff`,
  and `current_time` >= 0.85;
- search-boundary accuracy across `search_text`, `web_search`, and
  `connector_lookup` >= 0.85;
- every prediction has 25 finite raw logits and equals their unmodified argmax;
- generated RWKV text, sampling, postprocessing, and Executor fallback are all
  zero.

After those gates, the frozen head is evaluated once on S23 with the already
registered S23 retention gates.  Passing permits a bounded live current-Harness
canary, not deployment.  Failure does not authorize changed labels, thresholds,
fallback, or postprocessing.

## State-tuning decision

The first candidate uses zero learned Selector state.  A separate 2.9B Selector
state-tuning profile of approximately 2,000 training examples is allowed only
if the zero-state result proves a deficit under the frozen gates.  It must use a
new numbered preregistration and preserve the same head/input/output contracts.
The 13.3B Executor state is neither loaded into nor updated by this experiment.

