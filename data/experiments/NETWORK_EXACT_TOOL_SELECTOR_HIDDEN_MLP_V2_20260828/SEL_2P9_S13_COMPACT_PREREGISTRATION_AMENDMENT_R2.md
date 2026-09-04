# NET-SEL-2P9-S13-COMPACT R2 evaluator amendment

Date: 2026-08-28 (Asia/Shanghai)

The first S13 internal report is retained and external ECRA evaluation has not
been run. It reports 22/22 deterministic-retention rows correct but fails the
legacy S11 check named `deterministic_retention_eq_6_of_6`, which compares the
new exact count to the old dataset's literal six rows. This is an evaluator
cardinality defect caused by changing the preregistered dataset while retaining
an S11-specific constant; it is not a model metric failure.

R2 changes no data, feature, model, seed, optimizer, candidate selection,
threshold or external gate. It replaces the literal-six check with “all rows in
the deterministic-retention dev cluster are exact” and additionally requires
all rows in the new compact-local-only dev cluster to be exact when that cluster
exists. The deterministic rerun must reproduce the same selected head SHA-256
as R1 before ECRA evaluation is permitted. R1 remains invalid as an evaluator
run and is never a deployment candidate.

