# Round18 completed-case provenance analysis

Post-run and score-independent. Uses only the persisted Goal/task/evidence lifecycle and visible workspace users.json/active_users.json. It does not read external checks, verifier failure, or reference answers.

## Result

Round18's only internally completed case is E2E-B17. Its persisted output does not match the value deterministically derived from the visible workspace input:

- Visible-input derivation: `{"active_count": 2, "active_names": ["Ada", "Zoe"]}`
- Persisted output: `{"active_count": 3, "active_names": ["Alice", "Bob", "Charlie"]}`

## Backward causal chain

1. **visible_input_read** — users.json contains active Zoe and Ada, inactive Lin; deterministic derivation is Ada/Zoe and count 2.
2. **producer_correct_then_overwritten** — T2 wrote the visible-input-derived value, but T3 overwrote the same target with Alice/Bob/Charlie and count 3.
3. **wrong_value_reinforced** — T5 rewrote the same T3 value to active_users.json.
4. **expected_source_binding** — RWKV committed catalog_source and selected T3/T5 dependency artifacts from active_users.json as expected evidence for later reads of active_users.json.
5. **proof_independence_gap** — Proof source IDs/types differed, but all five accepted B17 assertions compared the current target with a prior snapshot of that same model-written target.
6. **obligation_amplification** — Those consistency proofs persisted evidence for GC1-GC4 and mechanically reduced unresolved criteria to empty.
7. **false_completion_precondition** — Completion consumed full criterion coverage without a proof anchored to immutable users.json semantics, so the wrong target became internally self-consistent and completable.

## Global scope

The same risky lineage occurred in 6 cases and 13 accepted assertions. E2E-B17 alone happened to cover every Goal criterion, so it reached completion.

## Root cause

The witness catalog/proof independence rule distinguishes opaque source IDs and source types but does not track semantic provenance equivalence for artifacts and reads of the same model-written workspace target. It therefore treats self-consistency as independent Goal correctness.

The correct next change is a generic provenance-independence rule at witness eligibility/proof validation: a prior artifact and a later read of the same model-written workspace target must not form an actual/expected pair for Goal correctness. This is not a B17 blacklist and does not choose an answer for RWKV.
