# S67 one-forward request-tail pooling ablation preregistration

## Trigger and fixed question

The V1 request-tail experiment failed closed before its first shard because it
introduced a second recurrent-state boundary inside the current Selector step.
The independent continuation diagnosis rejected arbitrary one-piece/segmented
numerical equivalence and identified an FP16 atomic short-row quality-path bug;
the minimal FP32 engine source fix is validated separately. The production
Selector trajectory, however, already has one authoritative boundary per
Harness step. This V2 experiment asks only whether request-tail pooling helps
classification when the current step is advanced exactly once, preserving the
existing trajectory and final state byte-for-byte/tensor-for-tensor.

## Frozen inputs and isolation

- S67 cases SHA-256 `0401966e7633c77cb3950019857324f23a625cc9a290b13c80804001400fd859`;
  manifest SHA-256 `0707bd65c64a4a96dd484085abc79c8b5ec199426bb777408ef2671e6be8ea46`.
- Use train 2000 and dev 500 only. The retired S67 test 500 is skipped before
  JSON parsing and contributes no feature, label, prediction, or metric.
- Model weights SHA-256
  `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`;
  frozen engine revision `67f0c5996c50dca0ad779da545cb491527de988f`;
  local physical GPU0 UUID `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`.
- One-forward implementation `rwkv_lh/inference/vllm_rwkv.py` SHA-256
  `c1cd6619340af695e30ded9e908dc0ae20b35f680b7b686d7ecc373f21c872ff`;
  focused unit suite: 8 passed.
- Evaluate zero state followed by ST500, ST1000, ST1500, and ST2000 in this
  fixed order. No state may be selected from train loss.

## Fixed feature and causal parity

- The full current text is `"\n" + step` and contains the exact marker
  `,"complete_requirement":"` once. The suffix begins immediately after the
  marker.
- Tokenize the full text once. Separately tokenize its prefix (with the same
  continuation/BOS contract) and suffix (without BOS) only to prove
  `full_token_ids == prefix_token_ids + suffix_token_ids`; reject otherwise.
- Execute exactly one `forward_all_hidden(full_token_ids, state)` call. Pool
  only hidden rows `[len(prefix_token_ids):]` into float32 suffix mean and
  suffix last, then concatenate them. Do not split, replay, drop, or alter any
  state update or token.
- From the same immutable parent state, run the already registered whole-step
  `advance_hidden_views` path once as an independent parity reference; it is
  not fed back into the candidate trajectory. The candidate suffix-last must
  also match the previously frozen whole-step last feature. Candidate and
  independent-reference final hidden and all three exported state tensors
  require bitwise equality; elapsed/token count require exact equality. Raw
  candidate suffix hidden views are preserved unmodified.

## Fixed head and gates

- Head: Linear(5120,128), GELU-tanh, LayerNorm, dropout 0.05, Linear(128,25).
- Train-only mean/std; seed 1067; AdamW `1e-3`; weight decay `1e-4`; batch 256;
  cosine schedule; at most 160 epochs; patience 30; gradient norm 1.0.
- Gates remain dev accuracy `>=0.96`, supported macro-F1 `>=0.96`, and minimum
  supported-label recall `>=0.90`. Raw selected head logits are preserved; no
  rule mask, family route, threshold route, repair, postprocessing, generated
  RWKV text, or sampling is allowed.
- Stop at the first eligible state for later retention/full-dev validation;
  otherwise run all five candidates and reject the feature/state family.

This is train/dev diagnostic evidence only. Even an eligible candidate cannot
enter product use before a frozen unique candidate, full retention gates,
artifact/service parity, an independently generated S68 locked test, and real
Harness canaries. The old S67 test remains permanently ineligible.
