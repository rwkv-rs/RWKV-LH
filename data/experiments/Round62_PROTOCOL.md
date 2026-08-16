# Round62 preregistered protocol: criterion-local Task effect and evidence scope

## Evidence-based hypothesis

Round61's single Task-effect response asks RWKV to classify every Goal criterion at once. The fixed 15 traces show all-ID copying, omission of the exact final criterion, semantic changes after a `reasoning` key format rejection, and fixed-criterion adjudication contaminated by the complete original Goal text exposed through the GOAL source.

## One protocol-boundary change

1. After a Task is successfully committed, ask RWKV once per immutable criterion. Each request contains exactly one fixed criterion and returns exactly `reason` plus `relation=unrelated|advances|satisfies`.
2. The fixed criterion ID is request scope and is never selected, generated, substituted, or ranked by the Controller. `satisfies` mechanically implies `advances`; only RWKV's relation supplies semantics.
3. A malformed response for one criterion records a blocked relation for that criterion only. It does not erase valid independent RWKV responses for other criteria and does not create a relation.
4. The criterion-local Goal evidence prompt continues to contain the complete real source catalog, but its GOAL source projection contains only the already-fixed immutable criterion description. It does not expose unrelated parts of the original request as if they were part of this criterion.
5. State explicitly that a manifest/index/list/summary proves only its own observed content; referenced objects or complete collections require their own observations.
6. Transparently normalize the common key spelling `reasoning` to `reason` only when `reason` is absent. The string value is preserved exactly, raw and normalized payloads are both audited, and no relation or criterion ID is generated.

## Non-cheating boundary

- No rule reads acceptance, benchmark IDs, expected answers, action names, paths, or values to select a relation.
- The Controller never changes a RWKV relation, final output, action, Task, criterion, or evidence ref.
- Per-criterion calls are independent semantic decisions by RWKV. Aggregation is a lossless projection of those decisions.
- Goal adjudication remains independent; a Task relation alone never completes a criterion.

## Frozen validation and gate

- Offline: full pytest, LH-Control `30/30`, catalog `90/90`, and the 31-file architecture regression.
- Fixed 15 cases and order remain unchanged.
- Run full E2E-90 only if B01 and B02 are Strict, Strict is at least `6/15`, FN at most `1`, and FP at most `3`.
- Upload only if full90 Strict is greater than `31`, FP at most `24`, FN at most `1`, with all offline gates passing.
