# NET-SEL-2P9-S27 current-Harness state-tuning result

Date: 2026-08-28 (Asia/Shanghai)

Decision: **rejected**. S27 is retained as an immutable experimental artifact,
but it is not enabled in the product, is not evaluated on S23, and does not
replace S23, S26, the historical 13.3B route, or any current Harness behavior.

## Architecture held fixed

- Product architecture remained the direct `LongHorizonModel -> Harness` path.
- Only the independent 2.9B exact-tool Selector lane was evaluated.
- The persistent 13.3B Executor lane, its state, prompt, generation, tool
  arguments, tool results, and Harness were not changed.
- Selector extraction invoked no generation or sampling. Every raw 25-way MLP
  logit and raw argmax is retained without masks, repairs, thresholds, retries,
  postprocessing, or Executor fallback.

## State training identity

- physical device: remote GPU0;
- frozen S26 optimizer trajectories: 2,000; dev 500 excluded from optimizer;
- S26 blind test 500 and S23 excluded from training/checkpoint selection;
- base model SHA-256:
  `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`;
- steps: 2,000, seed 887, context 1,536, state-only BF16;
- final state SHA-256:
  `92fe170270ae7871948694cc5e76ff483fb20d3162d1d14e497c128ebb6cc4f5`;
- tensor validation: exactly 32 finite, nonzero BF16 tensors shaped
  `[40,64,64]`; training-to-vLLM conversion was identity;
- final 64-loss mean: `0.000022416934370994568`.

The downloaded remote validation and full loss sequence are in
`run_s27_state_training_remote_checkpoint/`. The content-addressed candidate
profile is in
`data/models/state_profiles/network-selector-current-harness-s27-step2000-v1/`;
its registry default remains `zero`.

## Persistent current-architecture extraction

All 3,000 S26 rows were re-extracted locally on GPU0. Each row bootstrapped a
fresh S27 initial state once, replayed its zero-to-two registered historical
`SelectorStepV2` segments on the same WKV lane, and extracted only the current
step's unchanged mean hidden feature.

- tuned feature-manifest SHA-256:
  `255431f853506008b47cc4248dbcd741d91ddd164691b5da672734b7209cc26c`;
- changed feature rows versus S26 zero state: 3,000 / 3,000;
- mean absolute difference: `0.016366636380553246`;
- maximum absolute difference: `0.45081329345703125`;
- minimum per-row L2 difference: `0.7918516397476196`;
- generated Selector text: 0; sampling calls: 0.

This proves that S27 was actually loaded and affected the RWKV hidden path. It
does not by itself prove that the state improved exact-tool decisions.

## Fresh-head blind result

The fresh S27 MLP used the exact S26 architecture, parameters, split, seed 829,
and dev-only selection. Its blind S26 test result was:

- exact accuracy: `0.922` (S26 zero-state fresh head: `0.904`);
- macro-F1: `0.9207133764765141` (S26: `0.9020645751154411`);
- five-way search boundary: `0.87`;
- phase accuracy: first `0.892`, continuation-1 `0.96`, continuation-2 `0.92`;
- language accuracy: English `0.848`, Chinese `0.996`.

It failed three preregistered internal gates:

- all-class recall: `read_file` recall was `0.65` (required `>= 0.75`);
- new-operation recall: `web_search` recall was `0.75` (required `>= 0.85`);
- every-language accuracy: English was `0.848` (required `>= 0.85`).

The higher fresh-head aggregate score is therefore insufficient for
acceptance, and it also cannot isolate the effect of state from fitting a new
MLP.

## Frozen-head causal ablation

The S27 head was then held fixed and applied once to both the S26 zero-state
features and the S27 tuned-state features. Raw tuned logits replayed the saved
training output with identical argmaxes.

- zero state with the S27 head: `461/500 = 0.922`;
- tuned state with the same S27 head: `461/500 = 0.922`;
- changed test decisions: 8;
- exact rescues: 2;
- formerly exact regressions: 2;
- net rescues: 0 (required `>= 3`);
- regression count: 2 (allowed `<= 5`).

The state changed decisions, but produced no net exact benefit under the same
head. This is direct evidence that the apparent fresh-head aggregate gain is
not a causal S27-state gain on the frozen blind set.

## Final disposition

S27 fails both the internal-gate conjunction and the same-head causal net-gain
gate. Per the preregistration:

1. S23/ECRA is not run, because it is downstream of both passing gates.
2. No live canary or product integration is permitted.
3. Current product configuration, 2.9B Selector behavior, 13.3B Executor state,
   and all existing non-network Harness functions remain unchanged.
4. The result rules out this particular 2,000-row target-suffix initial-state
   profile; it does not rule out state tuning in general.

Primary machine-readable evidence:

- `run_s27_current_harness_tuned_state/FEATURE_CAUSALITY_AUDIT.json`;
- `run_s27_current_harness_tuned_state/TRAINING_SUMMARY.json`;
- `run_s27_current_harness_tuned_state/mean_head/PREDICTIONS.jsonl`;
- `run_s27_current_harness_tuned_state/mean_head/CAUSAL_ZERO_STATE_PREDICTIONS.jsonl`;
- `run_s27_current_harness_tuned_state/CAUSAL_ABLATION.json`.

## Regression verification

All commands ran in WSL with `uv` after the rejection decision and without
changing product configuration.

- focused S26/S27 dataset, vLLM state-profile, persistent state injection,
  independent Selector integration, atomic handoff, model, service, and
  protocol tests: `28 passed in 10.37s`;
- complete project suite: `489 passed, 1 warning in 99.60s`;
- the sole warning is Python 3.13's existing multiprocessing `fork()`
  deprecation warning in `tests/test_proactive.py`.

An initial focused invocation with pytest output capture enabled executed zero
tests because pytest's capture temporary file disappeared during collection.
The same fixed test list was rerun with the project's established `-s` mode and
passed 28/28; the complete suite also used `-s` and passed 489/489. This is
recorded as a test-runner/capture-path incident, not a model or Harness result.
