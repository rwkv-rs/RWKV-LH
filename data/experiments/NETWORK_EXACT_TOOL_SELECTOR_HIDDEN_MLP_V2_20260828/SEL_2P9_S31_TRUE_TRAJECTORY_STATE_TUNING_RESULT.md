# NET-SEL-2P9-S31 true-trajectory Selector state-tuning result

Date: 2026-08-28 (Asia/Shanghai)

Decision: **rejected by the preregistered fixed-head causal conjunction**.
The immutable S31 state and all evidence are retained, but the state is not
product-active, no fresh S31 head is trained, no S30 blind label is read, and
no client, service, Harness, `.env.local`, or 13.3B Executor behavior is
changed by S31.

## Architecture and training identity

- architecture: current direct `LongHorizonModel -> Harness` with an
  independent 2.9B exact-tool Selector and persistent 13.3B Executor;
- changed component: one 2.9B Selector initial WKV state only;
- parent state: exact zero; no S25/S27/Executor state was continued or mixed;
- optimizer data: exactly 2,000 frozen S30 true trajectories, 80 for every one
  of all 25 classes, English/Chinese 1,000/1,000;
- S30 dev/test, S28, S23/ECRA, live Harness traces, tool arguments, Executor
  text, parameter schemas, and full results were excluded from optimization;
- server physical GPU0, 2,000 steps, seed 1031, context 1,536, target-suffix
  state-only BF16 training;
- base model SHA-256:
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- selected preregistered step-2000 vLLM state SHA-256:
  `1d7ab37e2ef3a87a6ff8e6792ed426f4c84694902ada62b60d15c16a6a8ce853`;
- tensor contract: 32 finite, nonzero BF16 tensors shaped `[40,64,64]`,
  5,242,880 total elements; training-to-vLLM tensor values were exactly equal;
- full loss rows: 2,000, all finite; final-64 mean `0.021942496299743652`;
- generated RWKV text: zero; model weights changed: false.

The content-addressed profile is stored under
`data/models/state_profiles/network-selector-true-trajectory-s31-step2000-v1/`.
Its registry default remains `zero`. Remote validation, the complete loss
sequence, preflight, training log, and conversion sidecar are retained in
`run_s31_state_training_remote_checkpoint/`.

## Fixed-head causal evaluation

The already frozen S30 zero-state `mean-h512` head was replayed without
refitting on both zero-state and S31-state dev features. Its zero-state replay
matched all 1,250 prior raw argmaxes exactly. Extraction used local physical
GPU0, persistent compact V3 trajectories, the unchanged current-step mean
feature, and no generation or sampling.

- S28/S30 dev features changed: `1,250/1,250`;
- S30 changed features: `500/500`;
- minimum / mean / maximum per-row L2 difference:
  `0.7425299 / 0.9967520 / 1.6905438`;
- mean / maximum absolute difference: `0.01469055 / 0.45098877`;
- S30 zero-state exact: `486/500 = 0.972`;
- S30 tuned-state exact: `487/500 = 0.974`;
- raw decisions changed: `1`;
- exact rescues / regressions / net: `1 / 0 / +1`;
- the sole change rescued
  `NETSEL-S30-DEV-FILE_DIGEST-EN-000` from `copy_file` to `file_digest`;
- English exact: `237 -> 238` of 250;
- S28 retention exact: `746 -> 746` of 750.

The state therefore has a real, positive effect. It nevertheless fails the
preregistered `at least three S30 decisions changed` gate: only one raw argmax
changed. Aggregate `97.4%` cannot override that failed conjunction or establish
that this state is sufficiently influential for product use.

## Data-access and output integrity

- S28 train 6,000 and S30 train 2,000 rows were skipped for this causal stage;
- S28 test 750 and S30 test 500 rows were skipped before JSON parsing;
- test labels accessed: 0; test metrics computed: false;
- generated text calls: 0; sampling calls: 0;
- masking, repair, thresholding, retry, postprocessing, and 13.3B fallback: 0;
- all 25 raw logits and raw argmaxes are retained in
  `run_s31_true_trajectory_fixed_head_causality/FIXED_HEAD_DEV_PREDICTIONS.jsonl`.

Primary machine-readable report SHA-256:
`cba3d0d8de088978d2f1a863a78cf38528cce824060ee7cadbf285469b898eaf`.

## Disposition

Per the preregistration, the failed fixed-head conjunction stops S31 before
fresh-head fitting, S30 blind evaluation, S23/ECRA, live canary, or product
activation. The result rules out this single S31 state as a sufficient fix; it
does not justify multiple states and does not rule out state tuning generally.
The next independent experiment must address the remaining data/head weighting
defect under a new preregistration, with S30 blind labels still sealed.
