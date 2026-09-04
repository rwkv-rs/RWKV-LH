# NET-SEL-2P9-S4 class-balanced head preregistration

Date: 2026-08-28 (Asia/Shanghai)

S4 uses the already frozen S3 role-normalized dataset and already extracted
zero-state features.  It changes one training parameter only: cross-entropy
uses inverse train-class-frequency weights
`N / (25 * count[class])`.  The same weights are used for the dev loss
tie-breaker.  Data, splits, features, model, last-hidden selection, MLP shape,
seed, optimizer, epochs, patience, raw argmax, ECRA120 evaluator and every S3
acceptance gate remain unchanged.

This ablation is registered after S3 predicted `connector_lookup` 108/120 due
to the unweighted 2K train distribution (for example connector 474 and
read-file 556 versus 24 for many ordinary tools).  No resampling, threshold,
logit prior correction, rule override, calibration-based class selection, or
ECRA row enters training.  S4 is rejected if any frozen S3 gate fails.
