# Round63 preregistered protocol: multi-action Task continuation

## Evidence-based hypothesis

H13, LH11, H12, and M06 contain Tasks whose semantic postcondition spans several file observations or copy operations. The current executor binds a Task to one action. When the action succeeds but RWKV's Task-postcondition decision is `replan`, the runtime marks the Attempt failed and asks a separate failure-analysis request what to do. This turns normal Task progress into recovery and repeatedly loses the next action.

## One execution-state change

1. When deterministic action effects pass and a protocol-valid RWKV Task-postcondition decision is `replan`, record the action Attempt as succeeded but leave the Task pending.
2. Preserve every action result, snapshot, validation result, and the exact RWKV incomplete reason in Task-local state.
3. Reset only the executable action slot to `model_action`; the next ordinary action request is again decided entirely by RWKV with all prior Task observations visible.
4. A later RWKV Task-postcondition `pass` commits the Task. Goal-effect classification and Goal adjudication run only then.
5. Real action failures, verifier failures, protocol failures, and unsafe interrupted actions retain the existing recovery path.
6. Cap one Task at 32 successful continuation actions. Hitting the cap enters the existing failure/replan path; the Controller never declares completion.

## Non-cheating boundary

- Continuation is triggered only by deterministic effect success plus RWKV's explicit Task-local `replan` decision.
- The Controller does not choose the next action, arguments, Task, criterion, evidence, or final output.
- It does not inspect titles, paths, content, acceptance, or benchmark identity to decide continuation.
- A successful action is not a successful Task and neither is Goal completion.

## Frozen validation and gate

- Full pytest, LH-Control `30/30`, catalog `90/90`, 31-file architecture regression.
- Add regressions for two sequential reads in one Task, exact observation carry-over, event ordering, action-effect failure isolation, and the 32-step cap.
- Fixed 15 canary unchanged. Run full90 only if B01/B02 Strict, Strict at least `6/15`, FN at most `1`, FP at most `3`.
- Upload only if full90 Strict exceeds `31`, FP at most `24`, FN at most `1`, and all offline gates pass.
