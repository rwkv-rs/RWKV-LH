# NET-SEL-2P9-S25 current-Harness state-tuning preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Parent and reason

`NET-SEL-2P9-S24` is the zero-learned-state candidate at the exact current
direct-Harness boundary.  It reached 95.85% train accuracy but only 40.40%
accuracy, 0.3802 macro-F1, and 0.1333 search-boundary accuracy on the frozen
balanced test split.  `connector_lookup` and `read_file` recall were both zero.
S24 is rejected and remains append-only.  It was not evaluated on S23 and is
not integrated.

S25 tests one separately numbered 2.9B Selector initial WKV state.  It starts
from the 2.9B zero state; it does not continue S1, S2, S12, S19, or an Executor
state.  The existing 13.3B Executor profile and dynamic state lane are not read,
loaded, trained, or modified.  The product architecture remains
`LongHorizonModel -> Harness`, with the 2.9B selecting the exact operation and
the 13.3B receiving only that operation's disclosed schema for argument/final
generation.

## Frozen state-tuning data

Source: S24 cases SHA-256
`0349d9df08dd3e28418b5bc15415646d50a7d38c4c3d29e489c633392dba7601`.

- training: exactly all 2,000 frozen S24 train rows, once each;
- development: all 276 frozen S24 dev rows, never used as optimizer rows;
- S24 test: all 250 rows excluded from state tuning and checkpoint selection;
- S23/ECRA: excluded from state tuning and checkpoint selection;
- prompt: byte-exact S24 `SelectorBootstrapV2 + newline + SelectorStepV2`;
- target: `\nSelectorLabelV2: <exact-class>`;
- loss: target suffix only, BOS token id 0;
- no Executor text, operation schema, arguments, result body, generated RWKV
  text, reference answer, ECRA entity, or S23 row.

The exact RWKV-PEFT tokenizer must prove prompt/target additivity and no target
truncation at context 1,216 before training.  All 25 labels must remain present
in train and dev; exact prompts and semantic families cannot cross splits.  The
S24 registered ECRA similarity maximum and source hashes remain unchanged.

## Frozen state training

- server physical GPU0 only;
- base `rwkv7-g1i-2.9b-20260805-ctx16384`, SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- RWKV-PEFT source hashes must match the already audited target-suffix/state
  implementation;
- `--peft state --op fla`, BF16, micro-batch 1, DeepSpeed stage 1,
  gradient checkpointing, context 1,216;
- exactly 2,000 optimizer steps, one shuffled epoch, seed 863;
- LR `2e-5 -> 4e-6` cosine, warmup 40;
- checkpoints at 500/1000/1500/2000; final step 2000 is selected unless its
  tensor contract is invalid;
- selected checkpoint must contain exactly 32 `blocks.*.att.time_state`
  tensors, each BF16 `[40,64,64]`, finite and nonzero, then be converted without
  transpose to the local vLLM profile format and content-addressed.

No generated state-tuning text is retained or used.  State tuning changes only
the initial WKV tensors; model weights and all raw RWKV outputs remain intact.

## Frozen Hidden + MLP comparison

After checkpoint validation, re-extract all unchanged S24 train/dev/test rows
on local GPU0 through the same two-segment serving path and current-step mean
feature protocol used by S24.  Train a new MLP with exactly the S24 head
hyperparameters and seed.  Preserve every raw 25-logit vector and raw argmax.

The state is causal only if, using the frozen S25 head on both tuned-state and
S24 zero-state features:

- at least three balanced-test decisions change;
- net exact rescues are at least three;
- no more than five formerly exact balanced-test decisions regress;
- tuned features differ from zero features on every evaluated row.

The S25 tuned candidate must also pass every S24 frozen internal gate: accuracy
and macro-F1 >= 0.90, all-class recall >= 0.75, new-operation recall >= 0.85,
and search-boundary accuracy >= 0.85.  No threshold, class mask, retry,
postprocessing, Executor fallback, or output repair is permitted.

Only after all internal and causal gates pass may the frozen candidate run once
on S23.  S23 uses its already registered historical 13.3B comparison at the
same valid current-Harness decision points.  Passing S23 permits only a bounded
live canary and full Harness regression, not deployment.

