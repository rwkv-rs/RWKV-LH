# NET-SEL-2P9-S27 current-Harness identifiable state-tuning preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Parent and architecture

S27 tests one new initial WKV state for the independent 2.9B Selector using the
corrected S26 current-Harness trajectories.  It starts from the exact 2.9B zero
state and does not continue or combine S25 or any prior Selector/Executor
profile.  The product remains `LongHorizonModel -> Harness`, with a separate
2.9B exact-tool Selector and persistent 13.3B Executor.  The Executor model,
state profile, dynamic state, prompt, output, and Harness are not read or
modified by training.

## Frozen state data

- source cases SHA-256:
  `4a01c16a2e320e7754529544ea0299e5abdd6015b0b079c78c1f7d9ab24e4465`;
- optimizer rows: exactly all 2,000 S26 train trajectories, once each;
- development: all 500 S26 dev trajectories, never optimizer rows;
- S26 blind test: all 500 rows excluded from state training and checkpoint
  selection;
- S23/ECRA: excluded from state training and checkpoint selection;
- prompt: byte-exact `SelectorBootstrapV2`, every registered historical
  `SelectorStepV2`, then the current `SelectorStepV2` in persistent order;
- target: `\nSelectorLabelV2: <exact-class>`;
- loss: target suffix only, BOS token id 0;
- context: 1,536 tokens; exact tokenizer additivity and zero target truncation
  must be proven before remote training.

No full result, parameter schema, arguments, Executor text, generated RWKV
text, S26 test row, or S23 entity may enter training.

## Frozen state training

- remote physical GPU0 only;
- base `rwkv7-g1i-2.9b-20260805-ctx16384`, SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- audited RWKV-PEFT state-only / target-suffix path;
- `--peft state --op fla`, BF16, micro-batch 1, DeepSpeed stage 1,
  gradient checkpointing, context 1,536;
- exactly 2,000 optimizer steps, one shuffled epoch, seed 887;
- LR `2e-5 -> 4e-6` cosine, warmup 40;
- save at 500/1000/1500/2000; select step 2000 unless its tensor contract is
  invalid;
- checkpoint: exactly 32 finite nonzero BF16
  `blocks.*.att.time_state` tensors shaped `[40,64,64]`, converted without
  transpose to a content-addressed local vLLM profile.

State tuning changes initial WKV tensors only.  It may not change model
weights, tool labels, MLP logits, or any original RWKV text/output.

## Frozen state/MLP evaluation

Re-extract the unchanged 3,000 S26 rows on local GPU0 with the exact S26
persistent trajectory replay and current-step mean feature.  Train a fresh MLP
with the exact S26 head parameters and seed.  Preserve all 25 raw logits and
raw argmaxes.

The tuned state is causal only if, using the frozen S27 head on both tuned-state
and S26 zero-state features:

- tuned features differ on every evaluated row;
- at least three blind-test decisions change;
- net exact rescues are at least three;
- no more than five formerly exact blind-test decisions regress.

The tuned candidate must also pass every S26 internal gate: accuracy and
macro-F1 >= 0.90, every-class recall >= 0.75, new-operation recall >= 0.85,
five-way search-boundary accuracy >= 0.85, and every phase/language subgroup
accuracy >= 0.85.  No output repair, mask, threshold, postprocessing, retry,
generated selection text, or 13.3B fallback is permitted.

Only if both internal and causal gates pass may the immutable S27 candidate run
once on S23 against the historical 13.3B route at the same 245 valid
current-Harness decision points.  Passing S23 permits only a bounded live
canary and full Harness regression, not automatic deployment.
