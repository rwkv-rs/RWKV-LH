# Round79 unified lane short7 r4 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `0/7`
- External acceptance: `0/7`
- Agent completed: `0/7`
- All failures were typed `blocked`; the r3 raw `FileNotFoundError` interruption
  boundary is fixed.
- The full90 gate failed and full90 was not run.

## Confirmed progress

B02 and M06 chunk workers emitted valid `lh_chunk_result` from forked chunk
lanes. The explicit `required_next_function` and one-function child scope fixed
the r3 repetition of parent `lh_chunk_map` calls.

## New common failure class

Task bootstrap still exposed every full Harness/control schema in one call.
The candidates selected broadly sensible operations, but mixed current runtime
identity or another schema into their calls:

- B10 and M12 added top-level `task_id` beside `function/params`.
- M01 added top-level `scope_id`.
- M03 added `task_id` inside `lh_chunk_map.params`.
- B02 correctly reached `lh_task_done` after an explicit chunk result but added
  `task_id` to its required-empty params.
- B01 used read-only `lh_chunk_map` with directory `.` for a write Task.
- M06 read the selected filenames correctly, then used `lh_chunk_map` on
  directory `assets/` for a copy operation.

The validator correctly rejected all of these without normalization or retry.
This matches the local Round36 finding that simultaneous full schemas cause a
weak base model to copy fields across tools. More prose did not remove the
class; the next architecture must reduce the actual visible choice surface.

## Corrective change for a new experiment

Task action materialization now stays in the same Task lane but has two distinct
committed commands:

1. The model sees only `lh_select_operation` with registry-derived named
   options and commits one operation.
2. Runtime appends `operation_selected` and exposes only that operation's sole
   ActionDefinition. The model binds params once and must emit the locked
   function.

The second call is not a semantic resample: it cannot change the selected
operation, and any mismatch/format error rolls back and blocks. Harness
declaration, validation, defaults and execution still come from the same
ActionDefinition. Chunk/reduce/final forks also receive a latest one-function
scope.

Local regression is `66 passed`, unified control `30 passed`, with a new
regression proving parameter binding cannot replace a committed selection.
