# NET-SEL-2P9-S13-COMPACT preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Trigger and hypothesis

S11 leaves 12 compact-natural Gate false takeovers. S12 changes hidden values
but rescues none and adds one privacy failure. Inspection of the complete
related S11 data path shows that its 600-row Stage3 supplement is dominated by
long synthetic semantic-family boilerplate; its local-first concept is correct
but its length and surface distribution do not match compact local Harness
requests. S13 tests this data-coverage root cause without state tuning.

Immutable experiment ID: `NET-SEL-2P9-S13-COMPACT`. Selector state is zero.
`NET-SEL-2P9-S12-GATE` remains rejected and `NET-EXE-13P3-N0` is unchanged.

## Fixed dataset

Exactly 2,000 rows:

- all 1,354 S10 rows;
- all 46 S11 deterministic coverage rows;
- exactly 600 newly generated compact-natural rows, replacing the 600 long
  Stage3 supplement rows rather than increasing data volume.

The compact supplement is fixed at train 520/dev 80 and contains:

- compact local-only DEFER: 120 (104/16);
- deterministic clock/date/arithmetic DEFER: 120 (104/16);
- compact local-first-then-online DEFER: 180 (156/24);
- privacy/local-first DEFER: 60 (52/8);
- direct public web: 60 (52/8);
- direct structured connector: 60 (52/8).

S10 test remains the unchanged 205-row test. Semantic families may not cross
splits. Exact rendered duplicates and contradictory inputs are forbidden.
ECRA120 is contamination-only: exact overlap must be zero and the unchanged
UTF-8 byte-5gram cosine maximum must be below the exclusive 0.75 threshold.

## Fixed model and gates

Use the same one zero-state 2.9B forward, last/mean candidates, two 256-hidden
MLPs, seed 841, optimizer, early stopping, raw argmax, split metrics and
candidate-selection rule as S11. No threshold, schema, tool result, historical
assistant output, generated RWKV text or sampling is allowed.

Internal S11 gates remain unchanged. The complete ECRA120 gates also remain
unchanged: public web >=23/25, connector >=18/20, no more than 10% required
online non-takeover, web/connector macro-F1 >=0.90, and zero network takeovers
for every local, deterministic, mixed-local-first and privacy row.

Relative to S11, the candidate must rescue all 12 registered false takeovers,
introduce zero new false takeovers and regress zero required-online exact cases.
Passing ECRA permits full historical Harness and live-retrieval regression; it
does not by itself authorize runtime integration.

