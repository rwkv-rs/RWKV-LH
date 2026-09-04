# NET-SEL-2P9-S21 mean-description ablation preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Hypothesis

S20 kept the 2.9B query and each tool description in separate forwards and used
the final real-token hidden.  With identical tool targets but unseen outer
frames, accuracy fell from 0.8765 train to 0.66 dev and 0.49 test.  The fixed
last-token feature is therefore a plausible format-sensitive bottleneck.

S21 is one representation ablation.  It reuses the already extracted arithmetic
mean of all real-token final-layer hiddens for both query and tool descriptions.
It does not add a model call, generation, state, threshold, calibration, retry,
postprocessor, deterministic router, class-specific parameters or ECRA row.

## Frozen identities and parameters

- query dataset: S20 `queries.jsonl`, SHA-256
  `8e4d3dfa285a17259722468716e81eeeb39cc961e628f0fdf19a7935a2972e50`;
- query features: S20 accepted zero-state cache, 3,000 rows;
- tool descriptions: S5 frozen 25 rows, SHA-256
  `97218a227f31623136962a6506cc52a01638c98986d4089f52dca2b97a60dfca`;
- tool features: S5 accepted zero-state cache;
- feature protocol: `rwkv-lh.vllm-rwkv-final-hidden-mean.v1` for both sides;
- split: train/dev/test = 2,000/500/500, unchanged;
- scorer: shared description-conditioned `2560 -> 128` projections, one
  `512 -> 64 -> 1` pair scorer, no class-specific scorer parameters;
- optimizer/epochs/batch/dropout and loss: unchanged from S20;
- seed: 867;
- raw 25-logit argmax only; temperature fixed to 1.0;
- generated RWKV text and sampling invocations: zero.

## Gates

Dev and test are both required to satisfy, independently:

- accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- `web_search`, `connector_lookup`, `calculator`, `date_diff`, and
  `current_time` recall >= 0.85;
- registered boundary accuracy >= 0.85.

The fixed ECRA120 seen-regression set remains unread unless both internal splits
pass.  Failure rejects S21 without changing the product Selector or active
Harness.  Passing only permits an immutable ECRA evaluation; it does not permit
integration.
