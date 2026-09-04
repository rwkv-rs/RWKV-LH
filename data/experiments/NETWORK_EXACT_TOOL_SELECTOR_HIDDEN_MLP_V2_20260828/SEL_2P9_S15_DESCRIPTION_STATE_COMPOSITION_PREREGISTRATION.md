# NET-SEL-2P9-S15 description-head + function-state composition preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Question and boundary

S5 proved that a 2,000-row compact query plus frozen tool-description scorer
can generalize to the registered natural clusters, but its zero-state
full-coverage retention was insufficient.  The corrected S2 audit proved that
the already trained 2,000-step Selector state is causal, but its fixed
class-specific head failed ECRA.  S15 tests exactly one new composition:

`NET-SEL-2P9-S2 state + S5 description-conditioned shared scorer`.

This is a function-scoped Selector-state ablation.  It does not train another
state, change RWKV weights, alter capability projection, let the strong Planner
name a concrete tool, or route the candidate into the product.

## Frozen identities

- query rows: exactly 2,526 (train/dev/test = 2,000/276/250), SHA-256
  `7abf2078323b1dae6e65f089cd1e9fc31dc8d6d941561378ba586a8e1fd61154`;
- tool descriptions: exactly 25, SHA-256
  `97218a227f31623136962a6506cc52a01638c98986d4089f52dca2b97a60dfca`;
- learned initial state: `selector-network-s2-v1`, state SHA-256
  `08f1b20bf49f2dd4dfa83e60a16e299d01f70b8b182a4a79f5cb28581545c69d`;
- profile manifest SHA-256
  `bc3824337892286afcf99864e56e762d5a31c6837e06e5d1a5f0c7576555546c`;
- base: pinned local G1i 2.9B vLLM artifact and engine revision
  `67f0c5996c50dca0ad779da545cb491527de988f`;
- complete ECRA120 remains an untouched external holdout until every internal
  gate passes.

## Frozen feature and head candidate

- initialize every independent query/tool-description extraction from the
  registered S2 learned state;
- batch 1, FP16 WKV, final hidden at the last real input token only;
- no hidden mean, WKV-statistic, prefix, threshold or pooling sweep;
- use the unchanged S5 shared query/tool scorer architecture and seed 839;
- inverse train-class-frequency cross-entropy, AdamW, LR `1e-3`, weight decay
  `1e-3`, batch 64, maximum 100 epochs, cosine schedule, clip 1.0, patience 15;
- best epoch by dev macro-F1 and weighted dev loss tie-breaker;
- raw 25 scores and deterministic raw argmax only;
- generated RWKV text and sampling calls must both equal zero.

The state is immutable initial function knowledge.  A later product lane, if
authorized, must keep one causal dynamic Selector state rooted in this profile;
it may not reload S2 between individual tool decisions or import Executor
state.

## Fixed gates

Before ECRA120:

- test accuracy and macro-F1 >= 0.90;
- every class recall >= 0.75;
- `web_search`, `connector_lookup`, calculator/date/time recall >= 0.85;
- registered boundary accuracy >= 0.85;
- natural dev overall >= 0.90 and every registered cluster >= 0.80;
- exact model/profile/menu/data identity; finite features/logits; state profile
  present on every feature shard;
- generated text = 0 and sampling invocations = 0.

If all internal gates pass, run the unchanged complete ECRA120 exact-first-tool
evaluation.  Its acceptance gates remain those registered by S2, including
privacy/local network false positives, required-online false negatives and
web/connector macro-F1.  Passing ECRA authorizes only Harness-shadow wiring;
full local tests, raw-output integrity, state isolation, crash recovery and a
real 2.9B-to-13.3B handoff canary must pass before active integration.

Any failed gate rejects S15.  Its number and artifacts remain append-only and
must not overwrite S2, S5, S8, S11, S12, S13 or S14.
