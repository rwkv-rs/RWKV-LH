# NET-SEL-2P9-S16 query-state / zero-state tool-anchor preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Registered residual

S15 applied the same causal S2 learned state independently to both compact
queries and static tool descriptions.  It failed every internal gate: test
accuracy was 0.296 and the registered natural-dev accuracy was 0.5625.  The
state is causal, but applying role/function state to the immutable tool
registry changed both sides of the learned comparison and destroyed the frozen
semantic anchor.

S16 changes exactly one surface: compact task queries use the already extracted
S2-profile features, while the 25 name/description anchors reuse the frozen S5
zero-state features.  No other S15/S5 parameter, row, split, seed, optimizer,
metric, threshold or checkpoint rule changes.

## Frozen identities

- queries: 2,526 rows, SHA-256
  `7abf2078323b1dae6e65f089cd1e9fc31dc8d6d941561378ba586a8e1fd61154`;
- tuned query feature manifest SHA-256
  `aba6c9701945aa31bfb31bb53f32fad588176a2d2df7cd5a936a3bb5481fa309`;
- query profile: `selector-network-s2-v1`, state SHA-256
  `08f1b20bf49f2dd4dfa83e60a16e299d01f70b8b182a4a79f5cb28581545c69d`,
  manifest SHA-256
  `bc3824337892286afcf99864e56e762d5a31c6837e06e5d1a5f0c7576555546c`;
- tools: 25 rows, SHA-256
  `97218a227f31623136962a6506cc52a01638c98986d4089f52dca2b97a60dfca`;
- zero-state S5 tool feature manifest remains the already frozen artifact; it
  must declare no state profile, generated text count 0 and sampling count 0;
- candidate is final hidden at the last real token and the unchanged S5 shared
  description scorer, seed 839.

The product interpretation is fixed: learned profile initializes only a
run/function's causal Selector query lane.  Tool anchors are content-addressed
registry features, not dynamic lane state, and are recomputed only when the
menu description digest changes.

## Gates and disposition

All S15 pre-ECRA gates remain unchanged.  If any internal gate fails, S16 is
rejected without reading ECRA.  If all pass, the unchanged complete ECRA120 is
run once with raw 25 logits/argmax only.  No candidate may enter active routing
without ECRA, state-isolation, menu-authorization, raw-output-integrity, crash
recovery, full local regression and real 2.9B-to-13.3B handoff gates.

S16 artifacts are append-only and may not replace any prior experiment or
profile.
