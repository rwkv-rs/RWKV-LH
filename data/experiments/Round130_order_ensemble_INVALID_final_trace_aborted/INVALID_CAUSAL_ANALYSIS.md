# Round130 invalid implementation smoke — Final trace audit mismatch

**Verdict: INVALID; stopped after 2 completed cases. No score is admissible.**

Both E2E-B01 and E2E-B02 completed and passed the external verifier, but the frozen output-integrity
gate reported `final_output_matches_raw_rwkv=false`. The architecture selected the canonical Final
candidate as preregistered, while the physical request order was canonical→reversed→rotated. The
runner intentionally derives `raw_rwkv_final_output` from the last parseable action-lane Final in
`model_trace.json`; that was the unselected rotated candidate, whose text differed from canonical.

This is an audit-lineage defect, not an experimental result and not a model failure. The run was
interrupted immediately, before E2E-B03 completed. No threshold, benchmark, verifier, dataset, or
scoring code was changed.

The valid implementation emits physical requests reversed→rotated→canonical while keeping the voter
roles and vote rule unchanged. If canonical is not a Final but a two-vote Final majority exists, the
last final voter in that physical order supplies the verbatim selected text. Therefore the selected
real model Final is also the last parseable Final response consumed by the frozen byte-audit gate.
