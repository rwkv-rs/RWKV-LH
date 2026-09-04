# NET-SEL-2P9-S9 network-function takeover preregistration

Date: 2026-08-28 (Asia/Shanghai)

## Hypothesis and immutable input

The S8 broad 25-tool replacement is rejected because it regresses retained
local classes, while its natural network boundary set is 176/176.  S9 tests a
different deployment boundary without retraining or changing S8 logits: the
2.9B description-conditioned Selector may take over only the two network
functions.  All non-network proposals remain on the existing 13.3B path.

The only head input is the immutable S8 artifact with SHA-256
`36728736ce539039f5af132872edbf0f179aa66112ce57dbf16a578cf2586c23`.
No ECRA row has been evaluated by this artifact before this preregistration.

## Frozen projection and policy

- Dataset: ECRA route120, SHA-256
  `7bff832c2668136655272d06ee9545a65094552c7fd4fc14c3d301acae37fa1a`.
- Query: `SelectorQueryV3` with objective equal to the instruction, role
  `work`, and zero `NetworkSelectorProgress`; task is omitted because it is
  equal to objective.
- 2.9B input contains no parameter schemas, Executor state/text, tool results,
  workspace listing, ECRA category, or expected label.
- Feature: final-layer last hidden, raw zero initial state, maximum 384 tokens.
- Decision: preserve all 25 raw logits and take raw argmax with frozen label
  order.  No probability, threshold, rule, keyword, retry, generated RWKV text,
  or post-hoc correction is allowed.
- Takeover: true if and only if raw argmax is `web_search` or
  `connector_lookup`.  Otherwise S9 returns `defer` and cannot change the
  current Executor selection/output/state.

## Fixed pre-integration gates

All checks must pass:

1. public-web exact >= 23/25;
2. structured-connector exact >= 18/20;
3. required-online non-takeover rate <= 0.10;
4. web/connector macro-F1 >= 0.90;
5. network takeovers in local-only == 0/30;
6. network takeovers in deterministic-compute == 0/15;
7. network takeovers in mixed-local-online == 0/20;
8. network takeovers in privacy-policy-rejection == 0/10;
9. generated RWKV text count == 0 and sampling invocation count == 0;
10. all 120 raw-logit vectors and their SHA-256 digests are retained.

Failure rejects S9 without product integration.  Success permits only the two
network functions to enter product integration and Harness regression.  It
does not approve a broad 25-tool replacement or any state-tuned profile.

## Function state boundary after a pass

The first learned candidates are separately numbered
`NET-SEL-2P9-S10-web_search` and
`NET-SEL-2P9-S11-connector_lookup`.  Each may use at most 2,000 training rows
for the first fixed ablation.  Their immutable learned profile and append-only
dynamic lane are isolated by model, role, function, run, parent digest, profile
ID, profile SHA-256, and manifest SHA-256.  Zero remains the service default.

