# NET-SEL-2P9-S8 bounded natural-source weighting

Date: 2026-08-28 (Asia/Shanghai)

S6 uses count-proportional mixing inside each balanced class and misses the
ordinary-web dev gate by one row.  S7 makes sources exactly equal and causes
broad retention/natural regressions.  Neither was evaluated on ECRA.

S8 is the single fixed intermediate ablation: keep S6 inverse-class weights and
multiply every `stage3_natural` train/dev row by 2.0; coverage rows remain 1.0.
Normalize by the selected batch weight sum.  No cluster-specific multiplier is
allowed.  All other S6 parameters and gates remain unchanged.  If S8 fails any
pre-ECRA gate, no further source-weight sweep is permitted in this experiment.
