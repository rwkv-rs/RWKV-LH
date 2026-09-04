# Round79 unified lane short7 r8 final causal analysis

Date: 2026-08-14

## Result and terminal decision

- Strict: `0/7`
- External acceptance: `1/7` (`E2E-B01`)
- Agent completed: `0/7`
- No legacy role/dialect and no semantic/format resampling were observed.
- The unchanged gate failed, so full90 was not run.
- By the preregistered terminal condition, no further Round79 change is made
  around these seven cases.

## Earliest final errors

| Case | Final earliest boundary |
|---|---|
| B01 | After one successful write, selection stage emitted direct `lh_task_done` instead of `lh_select_operation`; workspace nevertheless passed external acceptance. |
| B02 | A 12-step Task lane reached 15,979 input tokens; limit was 15,151 for a 1,200-token output reserve. |
| B10 | Selection emitted unknown operation `lh_replace_text`. |
| M01 | After one successful action, selection stage emitted direct `read_json` instead of `lh_select_operation`. |
| M03 | Task T3 reached 15,341 input tokens after 14 attempts; limit was 15,151. |
| M06 | Three actual failures exhausted the failure-only retry budget; final failure was `read_file` on a non-regular path. |
| M12 | Selection emitted unknown operation `lh_replace_text`. |

## What the redesign established

- One strict candidate parser reads only current bytes and accepts one
  `function/params` object.
- Format failure rolls back and stops with zero resampling.
- Goal, Task, chunk, reduce and final checkpoints are independent durable lane
  heads; child chunks fork one Task parent and merge explicit results only.
- Runtime owns execution, checks, workset member status, evidence, artifacts and
  checkpoints.
- Locked Task selection/binding removed the r4 cross-schema `task_id/scope_id`
  pollution in r5/r6 and cannot change a committed operation during binding.
- B02 completed Strict in r6 through Goal → rejected finish → chunk → write →
  checks → Task → Goal evidence → Final.
- B01 reached an externally correct workspace in r6-r8.

## What remains unproven or failed

1. Prompt-replay Task lanes still grow beyond 16k on long trajectories. The
   runtime fails closed and preserves exact evidence, but it lacks a registered
   lane rollover/compaction relation that keeps all needed evidence visible.
2. The deployed base model does not yet stably obey the two-stage selector on
   every call: it can skip selection or hallucinate a near-name.
3. Schema-invalid finish calls are correctly rejected, but this means output
   stability is still below the real-use gate.
4. M06 multi-file completion remains unproven in real E2E, despite local
   structured workset regressions passing.
5. Native recurrent RWKV state remains unavailable from the deployed endpoint;
   all continuity evidence is prompt replay.

Round79 therefore completes the architectural replacement and local regression
stage, not project acceptance. Full90, large-code-31 and release readiness must
remain pending.
