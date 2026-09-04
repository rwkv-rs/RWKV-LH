# Round78 architecture fixes: implementation and validation log

Date: 2026-08-14

Status: superseded as the active architecture plan by
`data/experiments/Round79_rwkv_state_redesign/ARCHITECTURE_AUDIT.md`.
This record remains the immutable account of the Round78 structural fixes and
does not claim the eight defects are solved. Round78 treated the defects too
independently; Round79 reclassifies them under RWKV state continuity, model
output stability, and the boundary between semantic decisions and durable
runtime facts.

## Fixed structural paths

- Normalize nested, single-Task, Task-array, and canonical Task-batch transports without inheriting an outer schema.
- Keep current Task decisions separate from committed actions, attempts, state capsules, and other historical echoes.
- Use `ActionDefinition.required_arguments` as the shared prompt/runtime required-argument source; align `write_json` and paged JSON reads.
- Limit every semantic transition to one RWKV sample. Structural normalization is audited and never resamples the decision.
- Bind Goal finish/repair to registered evidence refs and add explicit reopen/replace relations.
- Add runtime-owned collection member sets, per-member action bindings, deterministic verified status, and downstream member evidence projection.
- Add Task-level `replan`, including local-ID scoping and repeated cacheable-failure convergence.
- Preserve prior Task checks and post-action observations across multi-action and downstream transitions.

## Validation evidence

- Related unit/integration selection: 164 passed, 1 deselected. The deselected check requires the external `normalizer` console entry point, which is unavailable in the current isolated tool environment.
- B01 focused smoke: Strict PASS and External PASS in `Round78_architecture_fixes_smoke_B01_r2`.
- B02 focused smoke: Strict PASS and External PASS in `Round78_architecture_fixes_smoke_B02_r3`.
- M06 reached External PASS for the first observed time in this investigation in both `Round78_architecture_fixes_smoke_M06_r18` and `Round78_architecture_fixes_smoke_M06_r20`; Strict remained blocked by later protocol/model-output failures.
- Fixed short7 `Round78_architecture_fixes_canary_r2`: Strict 1/7, External 3/7, FP 1, FN 2.
- Fixed short7 `Round78_architecture_fixes_canary_r3`: Strict 2/7, External 2/7, FP 0, FN 0. B01 and B02 passed both layers.
- Targeted `Round78_architecture_fixes_canary_r4_targeted`: External 1/3 and Strict 0/3. B10 and M03 were semantic false positives; M12 was an externally correct false negative.

Every runner-created directory contains `RUN_PROTOCOL.json`, source hashes, runtime doctor output, per-case audit logs, results, and a report.

## Remaining Stage 6 blockers

1. Goal/Task semantic completion is still fallible even with exact evidence binding. B10 and M03 can cite real self-consistency checks while misreading user-level negative or exact constraints.
2. An unbound collection cannot yet make a clean discovery transition when RWKV declares an open empty member set. M01 exposes this boundary.
3. RWKV can choose a valid but wrong action interface, for example `read_file` with `read_files` arguments in M06. The runtime correctly rejects this and must not silently rename the selected action.
4. Correct workspaces can still fail to close because the next RWKV transition is malformed or chooses a structurally infeasible status. M12 and some M06 runs expose this false-negative path.
5. Repetition/truncation can produce a valid `continue` decision without the required Task batch. The semantic-freeze rule correctly blocks instead of resampling or flipping it.

## Stage gate

Stage 6 can close only after a fixed canary demonstrates that the remaining changes improve both precision and recall without reintroducing false positives. Stage 7 (full repository regression, historical case matrix, fixed full90, metric comparison, and final experiment record) has not started.
