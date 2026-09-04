# NET-SEL-2P9-S14-OBJECTIVE-GATE result

Date: 2026-08-28 (Asia/Shanghai)

## Decision

S14 is rejected. It is retained as a representation ablation and is not wired
to runtime.

The implementation extracts the full-input mean and causal objective-prefix
mean from one profile-aware RWKV forward. Across the fixed 2,000 rows, complete
input length is 162–205 tokens and prefix length is 21–64 tokens. Generated
RWKV text and sampling remain zero. The registered concat candidate wins the
internal selection and reaches 1.0 on held-out S13 Gate test and every dev
cluster. The pure prefix candidate fails the internal test threshold and is not
externally selected.

The selected concat candidate keeps the frozen S11 Tool head but fails ECRA:

- public web 23/25, structured connector 16/20;
- local/deterministic/mixed/privacy takeovers 0/2/8/1;
- web/connector macro-F1 0.8108831;
- seven S11 false takeovers rescued, six new false takeovers introduced;
- four formerly exact required-online rows regress.

Evidence:

- `run_s14_objective_gate/TRAINING_REPORT.json`;
- `run_s14_objective_gate/ECRA120_OBJECTIVE_GATE_REGRESSION.json`.

Together with the S11 last-hidden diagnostic (required-online non-takeover
60%), this rules out changing only the fixed pooling surface as a sufficient
remedy. The safe deployment candidate remains none; S11 is the strongest
diagnostic baseline but its 12 false takeovers keep automatic network takeover
disabled.

