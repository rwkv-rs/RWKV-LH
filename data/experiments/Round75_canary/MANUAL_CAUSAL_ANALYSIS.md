# Round75 short7 manual causal analysis

## Frozen result

- Cases: B01, B02, B10, M01, M03, M06, M12.
- Strict: `1/7` (B01).
- External: `2/7` (B01, M01).
- Agent completed: `1/7` (B01).
- False positive: `0`; false negative: `1` (M01).
- The preregistered short gate failed because B02 and B10 were not Strict. No fixed15 or full90 run was started.

This analysis was made case by case from each raw `model_trace.json`, `event_log.json`, state timeline, final workspace and isolated external check. Aggregate output was used only to locate cases; it was not used as a substitute for reading the actual transitions.

## Per-case causal chain

### E2E-B01 — Strict pass, with redundant verification Tasks

1. The literal Goal and four-Task DAG were semantically safe.
2. T1 read the initially missing `greeting.txt`; T2 wrote the exact requested bytes.
3. T3 read the correct file and established the requested content.
4. `goal_frontier_step` nevertheless added T4, which read the same unchanged file again. The second read also passed and the run finished.

Earliest defect: Goal frontier did not recognize T3 as sufficient and duplicated verification. This did not damage final quality, but it shows that completed evidence is still not projected compactly enough for the frontier decision.

### E2E-B02 — Correct answer rejected at the fixed-tool wire boundary

1. T1 and T2 read `input.txt`; RWKV observed `project=Orion` and `count=7`.
2. The T3 Task step correctly selected `write_json` and explicitly explained that the dependency supplies the required values.
3. In all three fixed-tool argument attempts, RWKV returned the exact correct parameter object: `path=report.json` and `value={project: Orion, doubled_count: 14}`.
4. The boundary rejected each response only because the already-fixed tool name was not repeated around the parameter object: `tool-call format does not contain an explicit tool name and arguments`.
5. No write entered the Harness, so external verification failed.

Earliest defect: one semantic action was split into an action-name decision and a second name-plus-arguments protocol. The second prompt had already fixed the name, yet its adapter required the model to restate it. The model-derived answer and arguments were correct; the interface discarded them.

### E2E-B10 — Real code error, unavailable command spelling, then an obsolete replan path crashes

1. T1/T2 correctly read `test_slug.py` and `slug.py`. The spacing assertion was visible.
2. T3 wrote `value.lower().replace(' ', '-').strip('-')`. This is a genuine RWKV coding error: it returns `multiple---spaces` instead of `multiple-spaces`.
3. T4 selected `pytest test_slug.py`. The isolated action environment could not resolve that command spelling, so no behavioral failure output reached recovery.
4. Recovery selected replan. Two malformed outputs were rejected; the third contained a valid explicit `propose_task_batch` call.
5. The accepted call entered `_task_batch_from_propose_call`, which invoked the already-deleted `_persist_goal_protocol_normalization` method. The run ended with `AttributeError`.
6. The isolated external `unittest` verifier independently confirmed the real spacing failure.

Earliest wrong transition: the T3 code bytes are semantically wrong despite correct test evidence. The command environment and cleanup crash are later architecture defects that prevent RWKV from observing and correcting that error. Merely fixing the crash cannot turn this case into a pass; the recovery path must also deliver a real test observation back to RWKV.

### E2E-M01 — Final workspace is correct; an evidence-only verification Task is forbidden to complete

1. T1 read all three service JSON files. T2 unnecessarily attempted to read a nonexistent summary, then wrote an incorrect provisional summary.
2. T3/T4/T5 wrote all service files correctly. T6 replaced the provisional summary with the exact requested mapping.
3. All four isolated external JSON checks passed.
4. T7 was a pure verification Task depending on T3–T6. On its first Task step, RWKV selected `complete` and cited eight existing upstream action/snapshot refs.
5. The refs were valid and the files were already correct, but the controller raised `initial Task step cannot complete without a current action observation` solely because T7 had not executed a new action.

Earliest quality-relevant defect: T2 was a bad initial plan branch, but recovery corrected it. The final false negative is caused by the controller treating “no new action in this Task” as “no evidence,” even when the Task has direct dependency evidence. This forces redundant reads and rejects a valid model completion decision.

### E2E-M03 — Harmless response metadata causes three protocol retries and zero actions

1. The initial DAG correctly starts by reading `users.json`.
2. First Task-step output selected the correct `read_file` action, but included redundant `current_attempt_id`. The exact-field check rejected the whole decision.
3. The second output again selected `read_file`, but used the prior schema name and included `attempt_id`; it was rejected.
4. The third output used the prior schema and claimed completion from a synthetic `ACTION:T1` ref, then blocked.
5. No Harness action occurred and the workspace stayed unchanged.

Earliest defect: the system uses exact payload equality as protocol validation rather than projecting the unique Task decision and auditing unrelated outer metadata. Retries then moved the model away from its initially correct action. The synthetic no-observation `ACTION:T1` ref also gives the model a misleading completion target.

### E2E-M06 — Wrong model action is amplified by a weak Task contract and echo-prone second stage

1. T1 correctly read `selection.txt` and exposed exactly `alpha.dat` and `gamma.dat`.
2. T2 was titled “Read assets directory” but used `read_files` on invented paths `assets/selection.txt` and `assets/package/manifest.json`, both missing. It then called the observation Task complete merely because the action returned a structured result.
3. T3 saw the correct T1 dependency text, but first wrote a manifest with invented MD5-shaped empty-file values instead of copying files and computing SHA256.
4. It next selected `copy_file`; the fixed-argument stage echoed an old action-ledger object and repeated `assets/selection.txt -> package/selection.txt`. The generic tool-call extractor found that embedded call and executed it twice; both attempts failed.
5. Replan responses used a bare Task array or an unrecognized `tool_name` wrapper and the run blocked. No selected asset was copied.

Earliest defect: T2's Task contract asks for directory discovery but RWKV chooses an explicit-path content reader; the postcondition is weak enough that a list of missing guesses is marked complete. T3 is then a genuine RWKV reasoning failure even though T1 evidence is present. The second-stage ledger echo and replan format failure amplify, but do not cause, the original wrong semantic choices.

### E2E-M12 — Correct action plus complete arguments is rejected because arguments belong to a different request

1. The initial DAG correctly begins by reading `math_utils.py` and `test_math_utils.py`.
2. First Task-step output selected `read_files` and supplied the exact two paths and bounded arguments.
3. The controller rejected it because the five-field Task-step schema forbids `arguments`; it intended to ask for those arguments in a second model request.
4. The second retry incorrectly returned `complete` while explaining that no file contents were available; it was rejected for empty evidence.
5. The third retry again selected `read_files` with the exact correct arguments, and was rejected for the same extra-field rule. No file was read and no repair was attempted.

Earliest defect: the architecture rejects a complete, executable RWKV action because action identity and arguments are artificially owned by two different calls. Retry-induced degradation, not lack of a correct first action, caused the terminal failure.

## Shared root causes, ordered by causal reach

1. **One Task transition still has two wire protocols.** `task_step` owns action identity, while `tool_action_commit` owns arguments. B02 loses correct bare parameters; M12 loses a complete action; M06 echoes state in the second stage. This is the largest common structural defect.
2. **Exact-field rejection is being used where a syntax projection is needed.** M03's first correct decision is rejected for an unrelated ID; M12's complete action is rejected for arguments. The format layer should identify one unambiguous decision/action and leave its semantic fields untouched, not require byte-identical outer objects.
3. **A Task may not complete from existing dependency evidence.** M01 proves that the final workspace and model judgment can both be correct while the controller forces another action solely to satisfy its own lifecycle shape.
4. **Replan has a second Task-batch protocol and a dead cleanup caller.** Initial/frontier planning use the canonical Task batch, but recovery uses a private `propose_task_batch` tool, injects the schema in the controller, then calls a deleted audit helper. B10 reaches this stale branch and crashes.
5. **Some failures remain genuine RWKV semantic failures.** B10 writes incorrect code; M06 invents paths and digest values despite visible observations. Architecture must expose better, tighter state and real command feedback, but it must not rewrite these outputs into correct answers.
6. **Task contracts can describe an effect that the chosen tool does not establish.** In M06 a result containing two missing guessed paths is accepted as “assets directory contents observed.” Deterministic action success is not the same as the Task postcondition.
7. **Goal frontier can still duplicate already-established observations.** B01 passes, but adds a second identical verification read.

## Next structural change justified by the evidence

- Replace the name-only Task step plus fixed-argument request with one canonical Task-step result containing either `complete` with evidence refs or `act` with the full untouched `TaskAction {action_type, arguments}`.
- Remove `tool_action_commit`, `propose_preselected_action`, name-only continuation state, and the `model_action` string sentinel. There must be one internal action representation.
- Let a Task complete before executing a new action when it cites valid existing dependency/current evidence. Do not expose a synthetic current-action ref when no action result exists.
- Use the same canonical Task-batch protocol for initial planning, Goal frontier and recovery. Delete the private `propose_task_batch` route and its schema injection.
- The converter may project a unique Task decision/action from common JSON shells and ignore unrelated outer metadata for audit. It must not infer a missing tool from argument values, rename a tool, change any argument, add Tasks, add evidence refs or alter the final answer.
- Keep B10/M06 classified as semantic model failures until a later RWKV call actually corrects them from real observations; interface cleanup must not manufacture that correction.
