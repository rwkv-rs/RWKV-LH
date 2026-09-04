# Round79 unified lane short7 r3 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `0/7`
- External acceptance: `0/7`
- Agent completed: `0/7`
- The full90 gate failed; full90 was not run.

Unlike r1/r2, all seven cases passed Goal parsing and created Tasks. No initial
Task had a self-dependency. This confirms that removing the inline empty-call
exemplar and defining `after` semantics fixed the prior common boundary.

## Next exposed boundary

- B01 selected `lh_chunk_map` with `T1` as a source. The missing path raised a
  raw `FileNotFoundError`, so status became `interrupted` instead of a typed
  fail-closed protocol block.
- B02 emitted `lh_task_done` directly after `task_activated` and copied the
  activation event into params. Exact empty-params validation rejected it.
- B10, M01, M03, M06 and M12 entered chunk mapping. Their chunk workers forked
  the correct committed Task checkpoint and received exact chunk text, but
  emitted the parent function `lh_chunk_map` again. Lane validation rejected it
  because a chunk lane permits only `lh_chunk_result`.

The chunk assignment carried an event type and descriptor but did not state the
only permitted next function. Since the child inherits the parent continuation,
the most recent accepted semantic pattern was `lh_chunk_map`; the base model
continued that pattern. This is a lane-transition input defect, not evidence
that hidden child state should be merged or that the output should be repaired.

The Task tool list also placed abstract controls before concrete Harness
actions, making `lh_chunk_map` the first broadly relevant option even for small
write/read Tasks. Array order is input for a continuation model and cannot be
treated as semantically neutral.

## Corrective change for a new experiment

- Every chunk, reduce and final assignment now includes one explicit
  `required_next_function` runtime fact.
- Concrete Harness ActionDefinitions appear before lifecycle/child controls in
  Task bootstrap input.
- `lh_chunk_map` is explicitly read-only; `sources` are existing UTF-8 file
  paths, never Task keys.
- `lh_task_done` is explicitly forbidden directly after `task_activated` and
  requires visible result/check events with empty params.
- Missing/invalid chunk sources become typed `ModelProtocolError` blocks; they
  cannot escape as interrupted runs.

No candidate alias, semantic correction or resampling was added. Local
verification is `65 passed`; the unified control gate is `29 passed`.
