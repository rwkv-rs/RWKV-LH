# Round106 manual causal analysis

## Fixed result

- Strict/Agent/External: `0/2` for all three verdicts.
- LH07: 34 requests, 10 Tasks, 8 Attempts, 0 repairs.
- H13: 33 requests, 7 Tasks, 15 Attempts, 0 repairs.
- Both Finals were non-empty raw RWKV output.

## LH07

1. Eight service Tasks each executed exactly one correct first read.
2. Each lane then proposed a read of the next service; every cross-subject proposal was
   rejected before Harness execution.
3. The rejection was recorded only when the accepted `act` decision was later applied as
   the next Task action. RWKV therefore received it as a protocol correction rather than
   an immediate state-inapplicable operation result.
4. RWKV corrected the path back to each Task's own service rather than choosing
   `lh_task_done`, even though the first observation satisfied the structural completion
   contract. T1 eventually entered an unchanged loop.
5. No incorrect cross-subject action executed and no graph duplication returned, but no
   discovery Task committed and no migration work was planned.

The scope invariant works; the applicability check occurs one state-machine boundary too
late for a weak model.

## H13

1. Unlike Round105, RWKV declared checkpoint phase Tasks with final
   `workspace_mutation` evidence. This is a real planning improvement attributable to the
   revised evidence contract.
2. The initial `write_json` call lacked a `value` and was rejected. RWKV then listed the
   corpus and read documents sequentially.
3. Because a workspace-mutation Task may legitimately read inputs other than its output,
   the single read-subject invariant did not apply. RWKV continued beyond phase 1's four
   documents through doc14.
4. It never issued a valid checkpoint write and then repeated reads until blocked.

The remaining phase-scope problem cannot be solved by parsing the objective and inserting
controller-chosen filenames. A future Task contract should let RWKV explicitly declare an
input/workset identity set that the runtime can enforce.

## Next registered change

Validate a proposed continuation operation at the same Task-step boundary before recording
it as `act`. Return a `task_operation_rejected` event containing completion readiness and
the option to choose `lh_task_done`; do not defer the same error to next-action application.
