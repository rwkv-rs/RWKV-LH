# NET-SEL-2P9-S33 mean-last fusion zero-state head preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Decision being tested

S30 established that the current-step mean hidden view retains the compact
task well enough for `486/500` S30 dev decisions, while the last hidden view
alone is substantially weaker.  S32 then rejected simple source reweighting:
both registered weights remained at exactly `486/500`, with persistent errors
concentrated in English ordered-workflow continuations and nearby local-file
classes.  The frozen extractor already records mean and last from the same
current RWKV forward.  S33 tests whether one MLP needs their joint
representation: mean for the task distributed over the compact step, last for
the latest progress boundary.

The architecture remains the current direct
`LongHorizonModel -> Harness` architecture.  The independent 2.9B Selector
returns one of all 25 exact classes.  The persistent 13.3B Executor alone owns
arguments, tool execution, observations, continuation, and summary.  S33 does
not add or invoke a Planner, keyword route, tool mask, retry, output repair,
generated Selector text, Executor fallback, or an additional RWKV call.

## Frozen inputs and fusion protocol

S33 reuses the exact S28/S30 datasets, zero-state feature shards, labels,
split isolation, seed, optimization settings, and dev gates from S30.  Frozen
identities are:

- S28 dataset:
  `a993900649ae0943053df141d03c0e615b297864083f7893b49ae83391b98922`;
- S30 dataset:
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`;
- S28 feature manifest:
  `a048d5cd580fc50b4af525b0f6a9c90ad44120ce6d81b56e7a981970e10548ef`;
- S30 feature manifest:
  `65b26ce5f2908ee9415b6bc74fc064c91e33ca1ff5c99207651770b2e877bacd`;
- compact V3 protocol:
  `976309b22a2d4328500fe9f69ff24d550704f0857024929fcc9396073c4e0508`;
- unchanged 2.9B model weights:
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
- vllm-rwkv revision:
  `67f0c5996c50dca0ad779da545cb491527de988f`.

The new derived feature protocol is
`rwkv-lh.vllm-rwkv-final-hidden-mean-last-concat.v1`.  For each row it is the
ordered vector `mean[0:2560] || last[0:2560]`, with total dimension 5,120.
Both source vectors must come from the same frozen shard row and the manifests
must assert `one_current_forward_for_both_views=true`.  Concatenation is a
deterministic feature projection, not a second inference.  Feature mean/std is
fit once on the unweighted 8,000-row combined train set, independently over
all 5,120 dimensions.

Only S28/S30 train and dev rows may be parsed.  Both test splits must be
skipped before JSON parsing.  Test labels, test metrics, generated RWKV text,
and sampling are forbidden during development.

## Fixed candidate family

Training remains from scratch with seed `1030`, GELU(tanh), LayerNorm, dropout
`0.15`, class-balanced cross entropy with all-one weights, maximum 80 epochs,
batch 128, AdamW LR `8e-4`, weight decay `1e-3`, cosine schedule, gradient clip
1.0, patience 12, and the unchanged S30 best-epoch ordering.  Source weights
are restored to exactly S28=`1`, S30=`1`; S32 weights may not be reused.

Exactly two candidates are registered:

1. `concat-h256`, which approximately holds the first-layer parameter budget
   equal to a mean-only h512 head;
2. `concat-h512`, which holds hidden width equal to the strongest S30 head.

No other fusion order, pooling, width, source weight, seed, state, feature,
dataset, prompt, loss, threshold, or epoch limit may be tried in S33.  The
minimum-change selection rule chooses `concat-h256` if it passes every gate;
only if it fails may `concat-h512` be chosen.  A passing h512 cannot replace a
passing h256 because it has a higher score.

## Development gates

Each candidate must independently satisfy:

- S30 accuracy and macro-F1 each `>=0.97`;
- S28 retention accuracy and macro-F1 each `>=0.99`;
- every S30 class recall `>=0.90`;
- English and Chinese S30 accuracy each `>=0.96`;
- first, continuation, and completion stage accuracy each `>=0.95`;
- future-tool-distractor accuracy `>=0.95`;
- each sibling boundary accuracy `>=0.95`:
  `read_file/read_json`,
  `search_text/web_search/connector_lookup`,
  `write_file/write_json/patch_json`,
  `copy_file/move_file`,
  `check_command/run_command`, and
  `final_answer/ABSTAIN`;
- a dependency-light replay of the serialized single MLP preserves raw
  argmax and has maximum absolute logit difference `<=0.005`;
- test-label access, test metrics, generated text, sampling, masking,
  postprocessing, retry, and Executor fallback remain zero.

The derived protocol is not added to the production loader or service during
development.  Its artifact is replayed by the content-addressed S33 evaluator.
Production support is permitted only after the locked head passes blind.

## One-shot blind lock

Only a selected, content-addressed head unlocks one S30 blind evaluation.  The
one-shot gates remain:

- exact accuracy and macro-F1 each `>=0.96`;
- every-label true positives `>=18/20`;
- English and Chinese each `>=0.95`;
- first, continuation, and completion groups each `>=0.94`;
- future-tool-distractor rows and every sibling boundary each `>=0.95`.

All 25 raw logits and the raw argmax must be retained.  Temperature cannot
change argmax.  Any mask, repair, threshold override, retry, generated output,
sampling, or 13.3B fallback rejects the run.

Passing blind would authorize the smallest production change needed to carry
the two views from the same local vllm-rwkv forward into one MLP, followed by
full regression and a bounded GPU0 shadow canary.  It does not activate S31,
alter Selector inputs, remove tools, or change the 13.3B Executor.
