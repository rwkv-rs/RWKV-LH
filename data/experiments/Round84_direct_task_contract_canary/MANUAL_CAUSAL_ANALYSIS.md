# Round84 direct Task-contract canary manual causal analysis

## Result

Strict `0/4`, External `2/4`, Agent completed `0/4`.

The model endpoint restarted between Round83 and Round84, so the aggregate is
diagnostic rather than a controlled performance claim. Raw calls are still useful
for locating the next boundary.

## Per-case causal chain

### E2E-B01

1. RWKV directly emitted a valid `write_file` with the exact required bytes.
2. Harness execution and external acceptance both passed.
3. Instead of `lh_task_done({})`, RWKV emitted the same no-op `replace_text`
   repeatedly; 23 actions were executed in total.
4. The terminal call used normalized `function+arguments`, but its explicit
   `lh_task_done` params contained `source_task_id` and `target_task_id`; the empty
   completion contract correctly rejected it.

### E2E-B02

RWKV again chose `lh_chunk_map` for the ordinary small-file read and added
undeclared `task_id`. It was rejected before execution. The explicit assignment
contract did not eliminate this model behavior.

### E2E-B03

The same `lh_chunk_map(..., task_id=T1)` contract error occurred before reading or
modifying `config.json`.

### E2E-H04

1. RWKV directly emitted the exact safe scoped `write_file`; external acceptance passed.
2. It then repeated an identical no-op `replace_text` until 23 actions existed.
3. Its terminal `lh_workset` used an `arguments` envelope that normalized safely,
   but the payload was a copied `members/set_status` state projection rather than
   the declared `items/sealed` command schema, so it remained rejected.

## Finding

The selector defect is removed: correct direct calls now execute atomically, and
the runtime no longer asks RWKV to restate the same decision in a second
generation. Historical Round81 replay accepts 18 of the 24 selector-boundary raw
events under the current exact contracts; the other six retain independent real
schema errors.

This does not solve completion and repetition. B01/H04 expose a new downstream
amplifier: once the artifact is already correct, the Task lane can repeatedly
execute an identical successful no-op instead of reaching a valid empty-params
completion. B02/B03 expose persistent extra runtime-binding fields. Neither
should be hidden in the format normalizer.
