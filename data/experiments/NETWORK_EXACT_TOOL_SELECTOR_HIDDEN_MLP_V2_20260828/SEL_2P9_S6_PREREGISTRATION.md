# NET-SEL-2P9-S6 full-coverage description head preregistration

Date: 2026-08-28 (Asia/Shanghai)

S5 is rejected before ECRA evaluation because its 24-per-class retention
training subset yielded only 0.224 accuracy on the independent 250-row
retention test, although natural dev was 175/176.  S6 keeps the exact S5 query
projection, frozen tool descriptions, zero-state 2.9B features, shared scorer,
seed and every optimization/evaluation parameter.  It changes only head
coverage data:

- all frozen v2.4 coverage rows: train/dev/test = 6000/750/750;
- all Stage3 natural rows: train/dev = 1400/176;
- combined train/dev/test = 7400/926/750.

The S2 2000-row state-tuning experiment is not expanded or reused; S6 trains
only the Hidden+MLP head.  Natural rows do not enter test.  Source family and
split isolation, exact-query duplicates, all-label coverage, query/tool token
limits, ECRA byte-5gram cosine <0.75, zero generation/sampling, class-balanced
loss, raw argmax and all S5/S3/ECRA/Harness gates remain fixed.

S6 is rejected before ECRA if the synthetic retention or natural-dev gates
fail.  A pass authorizes evaluation, not automatic product integration.
