# NET-SEL-2P9-S25 current-Harness state-tuning result

Date: 2026-08-28 (Asia/Shanghai)

## Disposition

Rejected.  The S25 Selector state and MLP are audit artifacts only.  They are
not integrated into the product, were not evaluated on S23/ECRA, and cannot
activate an old 13.3B selection fallback.  The product architecture remains
`LongHorizonModel -> Harness`: an independent 2.9B exact-tool Selector and the
existing 13.3B Executor retain separate persistent runtime states.

## Frozen identities

- unchanged S24 cases SHA-256:
  `0349d9df08dd3e28418b5bc15415646d50a7d38c4c3d29e489c633392dba7601`;
- selected 2.9B state profile:
  `selector-current-harness-s25-step2000-v1`;
- state tensor SHA-256:
  `339d6b44517b632835123345b5ffc65594a5c485f3e72356a835e5e56d6a6108`;
- profile registry SHA-256:
  `df03a71042917a9e5ac457d17760afafec064072f9f7106b2e1e9741defe0f61`;
- tuned feature manifest SHA-256:
  `48c91af8457fb26cf7eeb1030afb734e12468992e84399a02bda2340536c4af2`;
- training summary SHA-256:
  `38cf91f21c9d0175ad097f8273ab110445a523dc4c5bd8d367f6d0434182f2e7`;
- report SHA-256:
  `97427d077148be66435130dc01241b9be116ede5b0b422df37a4c0ec989d6e9b`;
- head file SHA-256:
  `ea69b7eb1aedc52d114d797c89abf0539c21f765202750e9f739a55dbea97b2e`;
- head hash:
  `bdd0b2d2b2120f0eff30a52ef2f0cbd189a55c76211b584f43398523f6e18640`;
- state causality report SHA-256:
  `dc8d37e1f41841db88807b2b25eb449d0bef0f8c872af473647a3ea14600b4e9`;
- physical device for local feature extraction: GPU0.

Remote training completed exactly 2,000 registered optimizer steps.  The
selected checkpoint contains 32 finite, nonzero BF16
`blocks.*.att.time_state` tensors of shape `[40,64,64]` and was converted to
the local vLLM state layout without transpose.  Local extraction used the same
bootstrap-then-step persistent-state path and current-step mean feature as S24.

No RWKV text was generated, no sampler ran, all 25 raw logits and raw argmaxes
were preserved, and no output repair, threshold, class mask, postprocessing,
retry, or Executor fallback was used.

## Metrics

| split | accuracy | macro-F1 | search boundary |
|---|---:|---:|---:|
| train | 0.9655 | 0.9439 | 0.9553 |
| dev | 0.8225 | 0.5872 | 0.8696 |
| balanced test | 0.4080 | 0.3867 | 0.1333 |

The tuned state changed the hidden representation on all 2,526 rows
(6,466,509 elements, mean absolute difference 0.01706, maximum 0.35316), so
state injection is causal and operational.  With the frozen S25 head applied
to both feature sets, however, only 12 of 250 balanced-test decisions changed:
three exact rescues and four exact regressions, for a net effect of -1.  The
registered internal quality gates and the minimum +3 net-rescue state gate
both failed.

## Root-cause evidence and next admissible correction

This failure is not evidence against the current Selector/Executor split and
is not an ECRA comparison.  A post-run architecture audit found that S24/S25
are unsuitable as a product-quality gate for two independent reasons:

1. the 2,000-row training split assigns only 24 examples to each of 17
   operations while concentrating 1,225 rows in `read_file`,
   `connector_lookup`, and `web_search`;
2. its 600 class-retention rows were labelled from a legacy explicit
   `stage_objective`.  S24 correctly removed that field to match the current
   generic `CurrentDirectStageV1`, but retained the old label even where the
   remaining high-level request did not identify a unique next operation.
   The complete 250-row balanced test is made from those retention fixtures.

There is also an offline serving mismatch: every S24/S25 feature row was
bootstrapped independently.  The real service bootstraps only the first
selection in a run and advances every continuation from the prior Selector WKV
state.  Consequently the balanced test was neither input-label identifiable
nor an exact replay of the persistent Selector lane.  Its 0.408 score and the
state net effect of -1 remain valid records of the frozen experiment, but they
must not be interpreted as product accuracy.

The next admissible correction must keep the current Harness boundary, the
2.9B/13.3B split, current-step mean hidden feature, MLP architecture, state
separation, raw-output contract, and fixed evaluation rules unchanged.  It
must instead build exactly 2,000 current-request-identifiable training decision
points with all 25 labels, family-isolated development/test data, and explicit
prior Selector steps for every continuation.  Offline extraction must replay
those steps through the same persistent WKV lane as the service.  A new blind
holdout is required because the S24 test has already been observed.  Only after
that corrected internal gate passes may the candidate be compared against the
historical 13.3B route at the same valid S23 decision points.
