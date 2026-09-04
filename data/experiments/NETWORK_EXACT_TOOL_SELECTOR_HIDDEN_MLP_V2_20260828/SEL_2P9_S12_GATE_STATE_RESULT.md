# NET-SEL-2P9-S12-GATE result

Date: 2026-08-28 (Asia/Shanghai)

## Decision

S12 is causal but rejected. The function-scoped state is preserved under its
immutable number and SHA-256 for evidence; it is not enabled in runtime and
does not replace any existing Harness or Executor state.

## Training and checkpoint validation

- rows: train 1,467, dev 275; ECRA120 and S11 test excluded;
- base: zero initial state, 2.9B, 32 trainable `time_state` tensors;
- selected checkpoint: preregistered final step 1,467;
- selected vLLM state SHA-256:
  `8069eb808115a7677ebd67b13de1b5f6e1a45bdb060baf4a7a7ac120e3994400`;
- 32 BF16 tensors of `[40,64,64]`, 5,242,880/5,242,880 nonzero,
  all finite;
- training and vLLM tensor values are equal for steps 489, 978 and 1,467;
- first-64 loss mean 3.5886230, last-64 mean 0.0001018727.

Evidence: `run_s12_gate_state/training/FINAL_CHECKPOINT_VALIDATION.json`.

## Fixed one-forward ablation

All 2,000 S11 rows were re-extracted under the corrected S12 profile. The same
S11 topology, split, seed, optimizer, raw argmax and feature selection were
used. Internal train/dev/test and all registered natural clusters are 1.0.

The complete ECRA120 result nevertheless fails:

- old false takeovers rescued: 0/12 (required >=8);
- new false takeovers: 1 privacy row (required 0);
- local/deterministic/mixed false takeovers remain 3/3/6;
- public web remains 25/25; structured connector remains 18/20;
- web/connector macro-F1 falls from S11 0.8385965 to 0.8310345.

All 120 raw-logit pairs change, proving causal state injection. Only one final
decision changes, and it is the new privacy failure. Applying the S12 state to
the frozen S11 head gives the same decision result, so retraining the MLP is
not the root cause of the failure.

Evidence:

- `run_s12_gate_state_head/TRAINING_REPORT.json`;
- `run_s12_gate_state_head/ECRA120_HIERARCHICAL_REGRESSION.json`;
- `run_s12_gate_state/S11_FROZEN_HEAD_S12_STATE_ECRA120.json`.

## Root cause and next action

S12 trained on the same S11 information already available to the MLP. The
dominant S11 local-first supplement is long synthetic prose, whereas the
remaining ECRA failures are compact natural local, clock/date and local-first
requests. A fixed initial state can move the hidden space but cannot add the
missing compact boundary coverage. The next numbered ablation therefore fixes
data coverage under zero Selector state before considering another state.

