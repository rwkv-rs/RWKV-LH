# NET-SEL-2P9-S31 true-trajectory Selector state-tuning preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Question and fixed architecture

S31 tests whether one task-specific initial WKV state can improve the independent
2.9B exact-tool Selector on production-shaped multi-step trajectories after the
S30 zero-state candidate reached `486/500 = 0.972` development accuracy but
failed the preregistered English, per-class-recall, and sibling-boundary gates.

The architecture remains the current direct `LongHorizonModel -> Harness` path:

- the 2.9B Selector receives only the compact V3 menu, literal task, registered
  progress, and current stage, and returns one of all 25 exact classes;
- the persistent 13.3B Executor remains solely responsible for arguments,
  execution use, observations, continuation, and the final user-facing answer;
- the Executor model, prompt, dynamic state, state profile, generation, raw
  output, Harness, tool implementations, and tool registry are not training
  inputs and are not modified;
- no class is removed, masked, merged, thresholded, repaired, retried, or sent
  to a 13.3B fallback.

S31 starts from the exact zero state. It does not continue, add, average, or
compose S25, S27, an Executor state, or any earlier state profile. Passing S31
would authorize at most one Selector state, not one state per tool or stage.

## Frozen optimizer data

- source: all and only the 2,000 `train` rows in
  `rwkv_lh_network_selector_true_trajectory_s30_v1`;
- source cases SHA-256:
  `5b4225389787ba2c55e4f6dc9aace19c9a89d6d35bccf6793e8218be9a002305`;
- exact balance: 80 rows for each of all 25 classes and 1,000 rows for each of
  English and Chinese;
- prompt: byte-exact `SelectorMenuV3 + SelectorTaskV3`, then zero to two
  historical `SelectorStepV3` segments, then the current `SelectorStepV3`, in
  the same persistent order used by S30 and product projection;
- target: `\nSelectorLabelV3: <exact-class>`;
- loss: target suffix only, BOS token id 0;
- context: 1,536 tokens; exact tokenizer additivity and zero target truncation
  must be proven before training.

The 500 S30 dev rows are exported only for identity and evaluation checks and
are never optimizer rows. The 500 S30 blind rows, all S28 dev/test labels,
S23/ECRA rows, historical route errors, and live Harness traces are excluded
from state optimization and checkpoint selection. No tool arguments, schemas,
full results, evidence bodies, Executor text, or generated RWKV text may enter
state training.

## Frozen state training

- server physical GPU0 only;
- base `rwkv7-g1i-2.9b-20260805-ctx16384`, SHA-256
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- audited RWKV-PEFT state-only and target-suffix path;
- `--peft state --op fla`, BF16, micro-batch 1, DeepSpeed stage 1,
  gradient checkpointing, context 1,536;
- exactly 2,000 optimizer steps, one shuffled epoch, seed 1031;
- learning rate `2e-5 -> 4e-6` cosine, warmup 40;
- save 500/1000/1500/2000 for audit, but select exactly step 2000 unless its
  tensor contract is invalid; an invalid final checkpoint rejects S31 rather
  than selecting a different step post hoc;
- valid state: exactly 32 finite nonzero BF16 `blocks.*.att.time_state`
  tensors shaped `[40,64,64]`, converted without transpose to one
  content-addressed local vLLM profile.

Only initial WKV tensors may change. Base weights, tokenizer, hidden extraction,
MLP logits, class order, and every original RWKV output remain untouched.

## Frozen development ablation

The only feature view is the already selected current-step mean hidden state
`rwkv-lh.vllm-rwkv-final-hidden-mean.v1`; the MLP hidden width is fixed at 512.
Extraction uses local physical GPU0, batch 1, one bootstrap followed by exact
persistent history and current-step replay. It invokes neither generation nor
sampling.

For both S28 capability-retention data and S30 true-trajectory data, only train
and dev rows are re-extracted under the S31 state. Test rows remain unread.
A fresh S31 head uses the exact S30 recipe: S28+S30 balanced train rows, seed
1030, GELU, LayerNorm, dropout 0.15, AdamW, class-balanced cross entropy,
learning rate `8e-4`, weight decay `1e-3`, batch 128, at most 80 epochs, cosine
schedule, patience 12, and dev-only epoch selection.

The tuned state is separately identifiable only if the already frozen S30
`mean-h512` zero-state head, without refitting, shows all of the following on
the same S30 dev rows:

- tuned features differ from zero-state features on every row;
- at least three raw-argmax decisions change;
- exact rescues minus exact regressions are at least `+1`;
- no more than three formerly exact decisions regress;
- English exact count does not decrease;
- S28 dev exact count decreases by no more than two.

The fresh S31 head must then pass every gate simultaneously:

- S30 dev accuracy and macro-F1 are each at least `0.97`;
- English and Chinese S30 dev accuracy are each at least `0.96`;
- every S30 class recall is at least `0.90`;
- every registered S30 sibling-boundary accuracy is at least `0.95`;
- first, continuation, and completion stage-group accuracy are each at least
  `0.95`;
- future-tool-distractor accuracy is at least `0.95`;
- S28 dev retention accuracy and macro-F1 are each at least `0.99`;
- test-label access, generation, sampling, masking, repair, postprocessing,
  retry, and 13.3B fallback counts are all zero.

Failure of either the fixed-head causal conjunction or the fresh-head gate
conjunction rejects S31 and leaves the product on its current configuration.

## Locked blind and product rule

Only after every development and causal gate passes is one immutable S31
candidate allowed one blind evaluation over the frozen S30 test rows, while
also checking S28 test retention. The blind gates are the same metric
thresholds as development. Raw 25-way logits and argmaxes must be preserved.

Only a passing blind result permits a bounded current-Harness shadow canary and
full regression suite. Product activation still requires the canary and all
Harness regressions to pass. S23/ECRA is reference-only and cannot replace the
current-architecture trajectory, blind, or Harness gates. No result in S31
authorizes changes to the 13.3B Executor or deployment of multiple states.
