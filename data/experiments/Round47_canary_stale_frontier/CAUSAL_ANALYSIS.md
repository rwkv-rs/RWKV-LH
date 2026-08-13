# Round47 Canary Causal Analysis

## Frozen outcome

The fixed ten-case canary produced Strict `7/10`, external acceptance `7/10`,
and agent completion `8/10`.

- Strict controls: `B06`, `B08`, `B11`, `B18`, `B21`, `B25`, `B26`.
- Correctly blocked: `B27`, `B29`.
- False positive: `B12`.

The runner canonically ordered the selected case set by catalog order rather
than CLI `--case` order. The selected set, concurrency, dataset, parameters,
and thresholds remained the preregistered ones; the generated
`RUN_PROTOCOL.json` records the actual canonical order.

The preregistered gate required `B12` not to be a false positive. The canary
therefore fails, Basic30 must not run, and Round47 is not upload-eligible.

## What the scheduler change did and did not establish

The new unit/integration coverage established the mechanical scheduler
property: if two actions are materialized from one isolated frontier snapshot,
a first side effect invalidates a later unexecuted action on the same normalized
target. Same-target write/write and write/read, disjoint targets, caller-provided
actions, checkpoint recovery, and the 31-file parallel read/summary path passed.

No `stale_frontier_action_invalidated` event occurred in this canary's `B12`.
The model produced a serial dependency chain, so the Round46 stale-parallel
failure mode was not the causal path in this sample. The scheduler change
therefore could not repair this run.

## B12 event-by-event causal chain

1. Goal parsing correctly retained the requested `count`, `sum`, `min`, and
   `max` relationship to `numbers.txt`.
2. Planning created a five-Task serial chain: read, parse, compute, write, and
   verify. This separated latent computation from observable production.
3. T1 read the complete source and observed `4, 9, -2, 9, 5`.
4. T2 used that direct observation and correctly selected
   `write_json(stats.json, {count:5,sum:25,min:-2,max:9})`.
5. T3 selected `noop` with only the text `T3: stats.json verified`. It created
   no computed value or artifact but was committed as satisfying “statistics
   are computed.”
6. T4 depended only on T3. Its action-commit capsule contained the T3 noop text
   and explicitly excluded `M-T1-A1`, `M-T2-A1`, and
   `M-T2-A1-POST-R1`—the real source and correct file snapshot.
7. With its factual inputs removed by the memory projection, RWKV selected a
   fresh wrong write `{count:5,sum:15,min:1,max:5}`. That serial side effect
   overwrote the already-correct file.
8. T4 and T5 accepted the wrong values. Criterion-local Goal decisions then
   cited mostly the source read without checking the final file relation, and
   completion amplified the error.
9. The raw final response was internally contradictory: its reasoning
   recomputed sum `25`, min `-2`, max `9`, while its displayed object mixed
   values and the workspace still contained `{5,15,1,5}`. External acceptance
   correctly rejected the run.

## Root cause and next architecture hypothesis

The first architecture fault in this sample is causal dataflow truncation, not
wire format and not concurrent scheduling. `_dependency_entries` projects only
the direct dependency's outputs. A `noop` control-flow Task can therefore sever
the observed provenance required by its descendants even though it produces no
new data.

The next isolated change should make `noop` a provenance-transparent dependency
node: include its own observation for audit and recursively carry the latest
output projection of its dependencies, under the existing fixed dependency
token budget. This is mechanical lineage propagation. It does not inspect Task
language, calculate values, choose an action, modify RWKV output, or decide
correctness. Non-noop dependencies remain direct-only so large fan-out and
aggregation contexts do not recursively explode.

The later Task/Goal false semantic commitments remain model errors and must not
be corrected by a Controller answer rule. The proposed lineage fix instead
restores the facts RWKV had already observed before asking it to decide again.
