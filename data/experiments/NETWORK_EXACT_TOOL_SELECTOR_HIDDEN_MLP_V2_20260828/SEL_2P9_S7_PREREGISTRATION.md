# NET-SEL-2P9-S7 class/source-balanced description head

Date: 2026-08-28 (Asia/Shanghai)

S6 passes the full 750-row retention gate and scores 172/176 natural dev, but
ordinary-web is 12/16 and fails the fixed 0.80 cluster gate.  No S5/S6 ECRA
evaluation has run.

S7 reuses the exact S6 rows, features, tool descriptions, network, seed,
optimizer and gates.  It changes only training loss weights.  Every class gets
equal total mass.  Within a class, each present source kind
(`v2_4_full_coverage`, `stage3_natural`) gets equal total mass.  Thus an
example in group `(class, source)` receives weight proportional to
`1 / (number_of_sources_for_class * group_count)`, normalized to mean 1.
The same deterministic formula is applied to the dev-loss tie-breaker.

There is no resampling, new row, class/source-specific model parameter, logit
prior, threshold, output rule or ECRA feedback.  All S6 gates remain fixed.
