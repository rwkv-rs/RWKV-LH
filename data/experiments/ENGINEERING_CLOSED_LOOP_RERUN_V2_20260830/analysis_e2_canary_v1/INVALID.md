# Invalidated analysis

This first immutable analysis output is retained for audit only and must not be
used for release decisions.  The analyzer grouped every typed policy rejection
under the more specific `unknown` provenance branch even though provenance
labels are intentionally not persisted, and it reported but did not gate all
frozen Planner/Selector/Executor identities.  The source run and its RWKV raw
outputs were not changed.  The corrected, stricter output is
`analysis_e2_canary_v2_strict`.
