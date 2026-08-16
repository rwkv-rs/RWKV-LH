# Round76 preregistration: one complete Task transition

## Evidence and objective

Round75 short7 produced Strict `1/7`, External `2/7`, Agent `1/7`, FP `0`, FN `1`. The frozen per-case causal analysis is in `Round75_canary/MANUAL_CAUSAL_ANALYSIS.md`.

Round76 removes the remaining dual action and dual recovery protocols. The quality hypothesis is that RWKV should make one complete Task transition instead of having one answer split across mutually exclusive request schemas.

## R76-1: one canonical Task-step result

- The only internal result is: decision, reason, evidence refs, and either no action (`complete`) or one complete `TaskAction {action_type, arguments}` (`act`).
- `act` requires both the RWKV-selected registered action type and its untouched complete arguments in the same model response.
- Delete the name-only `next_action_name`, `tool_action_commit`, `propose_preselected_action`, and fixed-action argument request from the production path.
- A continuation action returned after a real observation is stored directly and is the next action executed. The controller does not resample, select, repair or fill its parameters.
- Delete the `model_action` string sentinel; an unmaterialized Task has an empty current action.

## R76-2: simple Task-step format projection

- The boundary recursively searches a JSON payload for one unambiguous Task decision and, for `act`, one unambiguous explicit tool identity plus arguments object.
- Outer metadata such as task/attempt IDs is retained in the raw audit but does not become part of the canonical Task step.
- The converter is syntax-only: no argument-schema matching to infer a tool, no renaming, no argument movement/deletion, no evidence generation, and no semantic selection.
- Conflicting decisions/calls, a missing explicit tool identity, non-object arguments, unknown evidence refs or invalid action arguments are rejected.
- No compatibility runtime for the old Task-step schema is retained after migration.

## R76-3: completion from existing evidence

- An initial Task step may return `complete` when it cites valid dependency or Task-local evidence already present in its registry.
- When there is no current action result, the registry does not expose a synthetic `ACTION:<task>` ref.
- The controller records a no-new-action Task completion and its cited refs. It does not create an Attempt, artifact or observation and does not decide completion itself.
- The unchanged-duplicate invariant remains: a duplicate observation cannot reverse the preceding incomplete judgment into complete.

## R76-4: one Task-batch protocol

- Initial planning, Goal continuation and recovery all request the same `long-horizon.task-batch.v1` envelope and use the same normalizer/validator.
- Delete the private `propose_task_batch` G1i tool, controller-added Task schema, and obsolete normalization callback.
- Recovery still receives the failed observation and RWKV-selected recovery gap; only its wire representation changes.

## R76-5: expose the installed project command runtime

- A bare executable selected by RWKV is resolved against the normal system PATH and then the current project Python runtime `bin` directory.
- Python console scripts from that runtime execute through the same project interpreter inside the existing bubblewrap mount; the requested argv and resolved argv are both audited.
- This is executable resolution only. The controller does not replace a command with another test framework, add arguments, install packages, or treat command success as Task completion.
- Regression proves an installed runtime command is reachable and an unknown command still fails closed.

## Explicit non-goals

- Do not change RWKV-written source, JSON values, paths, action types, arguments, evidence refs or final answer.
- Do not infer a tool from argument names or hidden acceptance data.
- Do not add case/path/value special cases, answer ranking, MCP, subagents or external model decisions.
- Do not count a deterministic action-effect check as proof of the Task or Goal.
- B10 and M06 must remain failures if RWKV never emits a real correcting action.

## Offline checks

- Converter tests cover harmless outer metadata, full Task action, conflicts, missing tool identity and argument preservation.
- Controller tests prove: no fixed-argument model request; a continuation executes the exact RWKV action; dependency evidence may complete without an Attempt; no-observation Tasks cannot cite a synthetic action ref.
- Recovery tests prove all Task batches use one schema and no `propose_task_batch` request exists.
- Full pytest, compileall, diff check, LH-Control `30/30`, E2E catalog `90/90` validate-only.

## Online order and gates

1. Run the same fixed short7: B01, B02, B10, M01, M03, M06, M12.
2. Manually inspect every case from raw requests, observations and final workspace.
3. Continue only at Strict `>=4/7`, B01/B02/B10 all Strict, FP `<=1`, FN `<=1`.
4. Then run H12, H13, LH11 and LH02; fixed15 gate remains Strict `>=6/15`, FP `<=3`, FN `<=1`.
5. Full90 upload gate remains Strict `>31`, External `>=32`, FP `<24`, FN `<=1`.

Best uploaded baseline remains commit `14d864d71bf670b479a33f4fdb63b4772b69d3c8`: Strict `31/90`, External `32/90`, Agent `55/90`, FP `24`, FN `1`.
