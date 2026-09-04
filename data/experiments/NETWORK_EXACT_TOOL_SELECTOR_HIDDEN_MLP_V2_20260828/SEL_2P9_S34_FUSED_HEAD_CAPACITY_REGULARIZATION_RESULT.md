# NET-SEL-2P9-S34 fused-head capacity regularization result

Date: 2026-08-28 (Asia/Shanghai)

Decision: **accepted by all preregistered dev and one-shot blind gates**.
The minimum-capacity `concat-h64` head is locked for product-path shadow
integration.  This acceptance does not activate S31, alter RWKV output, remove
tools, or change the 13.3B Executor.

## Locked development result

- feature: one same-forward
  `mean[2560] || last[2560]`, dimension 5,120;
- zero Selector state; compact V3; all 25 exact classes;
- `concat-h64`: S28 `750/750`; S30 dev `497/500 = 99.4%`;
  macro-F1 `0.993942`; English `247/250`; Chinese `250/250`;
- all six dev sibling boundaries: `100%`;
- all dev class recalls, stages, future distractors, retention, portable replay,
  and output-integrity gates passed;
- `concat-h128` also passed at `493/500`, but was not selected because the
  preregistered rule chooses the smallest passing head.

Locked head SHA-256:
`fe97f9eed3e96a63efb4937fc79e884399585dca1af37aa224d4477e73a3410e`.
Locked head hash:
`6e2553e41dca4a3d3402e3f99b919c2b767a23d3fc64cba0662a9744b264a41d`.
Dev selection SHA-256:
`a6d27cfdb67d8c1e785c5aab27f6804babcc8d855fb6ece299aff47ec41908e8`.

## One-shot S30 blind result

- evaluation count: exactly 1;
- exact: `493/500 = 98.6%`;
- macro-F1: `0.986073`;
- English: `244/250 = 97.6%`;
- Chinese: `249/250 = 99.6%`;
- first / continuation / completion:
  `148/153 = 96.73%`, `325/327 = 99.39%`, `20/20 = 100%`;
- future-tool distractors: `292/299 = 97.66%`;
- minimum class true positives: `18/20` (`append_file`, `write_json`);
- sibling boundaries:
  read `40/40`, search/network `60/60`, write/JSON `58/60`, copy/move
  `39/40`, check/run `39/40`, final/abstain `40/40`;
- seven errors total; all 25 raw logits and raw argmaxes are retained;
- generated text, sampling, masks, repair, threshold override, retry,
  postprocessing, and Executor fallback: 0.

Blind report SHA-256:
`8209fe1b85cb7df95b9af5a0c10e805fea94345c751d3a1b893d525c62d44582`.
Blind predictions SHA-256:
`6a09c0f7b186f695df64488c1ec967f6ae205306a0988a795e2a1e164647e7ed`.
Evaluator SHA-256:
`bbd2a2b22604db6d5965b9b5186e552358af3e05c01ebb744ab12a7df864b494`.

## Isolation qualification

The head, all logits, and the evaluator were locked before parsing any test
dataset row.  Feature shards contain no label tensor and no sample identifier
or metadata enters the MLP.  During preflight, however, the frozen feature
`sample_id` strings were found to contain human-readable class names.  The
evaluator used them only for order alignment after logits were already fixed,
so they did not affect this candidate or any prediction.  Still, future formal
datasets must use opaque content-addressed test IDs; this naming defect is
recorded rather than claiming perfect semantic label secrecy.

## Authorized next step

The passing blind result authorizes a bounded product-path change only:

1. register the V3 compact menu/task/step protocol in client and service;
2. carry mean and last from the same local vllm-rwkv forward into the one h64
   MLP;
3. preserve all 25 raw logits and raw argmax with no repair or fallback;
4. run protocol/unit regressions and a physical-GPU0 shadow canary before any
   `.env.local` activation.

The 13.3B Executor, its state, tool arguments, tool execution, and final answer
path remain untouched.
