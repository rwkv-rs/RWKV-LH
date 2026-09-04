# NET-SEL-2P9-S30 true-trajectory zero-state >=96% preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Objective

Test whether the current 2.9B zero-state Hidden+MLP Selector can exceed 96%
without state tuning once its data matches the real persistent Harness lane.
The architecture remains `LongHorizonModel -> Harness`: the 2.9B model emits
one of all 25 exact classes, while the 13.3B Executor alone binds arguments,
executes, interprets observations, continues, and summarizes.

S30 may not add a Planner, model call, keyword route, class mask, threshold
override, retry, generated selection text, output repair, tool deletion, or
13.3B selection fallback.  Selector and Executor states remain separate.

## Root-cause-controlled data

S28's 749/750 blind result established the compact 25-class boundary, but its
generator supervised only an independently constructed endpoint from each
trajectory.  It did not supervise the earlier choice when the immutable task
also named later tools, and completion examples literally stated that no tool
remained.  On S23 this produced future-tool jumps and only 7/99 completed-run
`final_answer` choices.

S30 freezes exactly 3000 new current-Harness decision points:

- train/dev/blind test: `2000/500/500`;
- every label: exactly `80/20/20` rows per split;
- every label/split: English and Chinese exactly balanced;
- every row records a complete immutable natural task sequence, zero to two
  exact prior Selector steps, the current label, and zero to two future
  operation mentions;
- for non-control labels, at least half of first-step rows contain a distinct
  future tool so choosing a salient later tool is an explicit negative;
- every history step is rendered and replayed in order on the same persistent
  WKV lane and its registered historical label is audited;
- each continuation progress delta is produced by the production
  `build_network_selector_input` parent-index semantics and contains exactly
  the newly completed/failed action;
- `final_answer` rows occur only after one or two completed executable actions;
  their task never says “select final_answer”, “no tool remains”, or an
  equivalent classifier hint;
- `ABSTAIN` rows use genuinely ambiguous, unsupported, unsafe, or unobservable
  next-operation contracts and are never substituted for execution failures;
- task, lexical, entity, and trajectory families are disjoint across splits;
- ECRA120 is used only for fixed UTF-8 byte-5gram cosine leakage auditing, not
  as a label or text source; maximum similarity must be below `0.75`.

All rows keep only the literal task, names/descriptions, bounded stage fact,
and progress.  Parameter schemas, arguments, full results, Executor text,
workspace listings, hidden labels, and generated RWKV text are forbidden.

## Zero-state retention training

To prevent the online/trajectory fix from deleting other Harness abilities,
each candidate trains from scratch on the union of:

- all 6000 frozen S28 training rows and their already frozen features;
- all 2000 S30 training rows and newly extracted features.

Candidate selection uses both frozen dev sets but never either test set.  S28
dev (750) is a capability-retention gate; S30 dev (500) is the true-trajectory
gate.  The S28/S30 features must use the same compact V3 protocol, unchanged
2.9B weights, physical GPU0, batch 1, zero initial state, exact persistent
history replay, and one current forward returning mean and last views without
generation or sampling.

Candidates remain `mean/last x hidden 256/512`, using seed `1030`, GELU(tanh),
LayerNorm, dropout `0.15`, class-balanced cross entropy, maximum 80 epochs,
batch 128, AdamW LR `8e-4`, weight decay `1e-3`, cosine schedule, clipping 1.0,
and patience 12.  `CUBLAS_WORKSPACE_CONFIG=:4096:8` is required.

Candidate ordering among candidates that pass every dev gate is:

1. highest S30 dev macro-F1;
2. highest S30 dev accuracy;
3. highest S28 retention dev macro-F1;
4. lowest summed S28+S30 dev cross-entropy;
5. smaller hidden dimension;
6. mean before last.

Dev unlock requires simultaneously:

- S30 accuracy and macro-F1 each `>=0.97`;
- S28 retention accuracy and macro-F1 each `>=0.99`;
- every S30 label recall `>=0.90`;
- both S30 languages `>=0.96`;
- S30 first, continuation, and completed/final groups each `>=0.95`;
- S30 rows with a future-tool distractor `>=0.95`;
- each registered sibling boundary `>=0.95`.

If no zero-state candidate passes, S30 stops before blind evaluation.  A
learned Selector state would require a separately preregistered ablation; it
may not be introduced to rescue this run post hoc.

## One-shot blind gates

The locked candidate may evaluate the 500 S30 blind rows exactly once:

- exact accuracy `>=0.96` (at least 480/500);
- macro-F1 `>=0.96`;
- every-label true positives `>=18/20`;
- English and Chinese each `>=0.95`;
- first, continuation, and completed/final groups each `>=0.94`;
- future-tool-distractor rows `>=0.95`;
- each sibling boundary `>=0.95`:
  `read_file/read_json`,
  `search_text/web_search/connector_lookup`,
  `write_file/write_json/patch_json`,
  `copy_file/move_file`,
  `check_command/run_command`, and
  `final_answer/ABSTAIN`.

All 25 raw logits and raw argmaxes must be retained.  Temperature may be stored
for calibration but cannot change argmax.  Any mask, postprocessing, retry,
generated output, sampling, or Executor fallback rejects the run.

Passing S30 permits regression evaluation on already-consumed datasets and a
bounded product-path canary; it does not by itself prove full Harness quality
or authorize deleting the historical 13.3B route.
