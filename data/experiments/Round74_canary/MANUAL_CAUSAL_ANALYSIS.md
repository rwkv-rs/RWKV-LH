# Round74 short7 manual causal analysis

## Frozen result

- Cases: B01, B02, B10, M01, M03, M06, M12.
- Strict: `2/7` (B01, B02).
- External: `3/7` (B01, B02, M03).
- Agent completed: `2/7` (B01, B02).
- False positive: `0`; false negative: `1` (M03).
- Round74 short gate failed because B10 was not Strict and the required B01/B02/B10 triplet was not complete. H12/H13/LH11/LH02 and full90 were therefore not run.

The analysis below was performed request by request from each case's `model_trace.json`, `event_log.json`, `causal_ledger.json`, state timeline, final workspace and isolated external checks. Aggregate counts were used only as navigation; causal judgments come from the raw per-request payloads and observations.

## Per-case causal chain

### E2E-B01 — Strict pass, but the completion architecture amplified work

1. `goal_commit` and the initial two-Task plan preserved the request: write exact content, then read it back.
2. T1 wrote the correct 16 bytes. T2 read the exact content. Both Task commits were semantically correct.
3. T2 initially referenced a post-action memory ref that was outside the current validation registry. The same successful read was committed more than once before a valid current ref was selected.
4. Even after the requested write and read-back were complete, `goal_obligation_gap_selection` selected GC3, “verified before finishing,” as unresolved. Three protocol attempts then produced a chain T3–T7 that read the same unchanged 16-byte file five more times.
5. The case finally completed because every duplicate verification also passed, not because the criteria/obligation layer recognized the first sufficient verification efficiently.

Earliest structural defect: the goal-evidence/obligation layer did not treat the already committed T2 observation as sufficient and generated new semantic Tasks for the same fact. The final result is correct, but seven Tasks, eight Attempts and 47 model requests for one write plus one read demonstrate non-unique completion state.

### E2E-B02 — Strict pass after two avoidable wrong actions

1. Goal and initial plan were adequate: T1 reads `input.txt`; T2 creates `report.json` from the dependency.
2. T1 exposed the full text `project=Orion\ncount=7\n` to T2.
3. T2 nevertheless selected `read_json(input.txt)` twice. Both attempts deterministically failed with `JSONDecodeError`; the dependency had already provided the needed plain-text value, so neither action advanced the Task.
4. The second `failure_analysis` finally stated the correct derived values and RWKV then selected `write_json` with `{project: Orion, doubled_count: 14}`.
5. External exact-value and exact-key checks passed and the raw RWKV final output was preserved.

Earliest error: first T2 `action_name_selection` (`MR-df01ea12a25f48b7`) ignored the complete dependency observation and chose a redundant, type-incompatible read. Recovery happened to correct the model after two failures. This pass is evidence that RWKV can derive and write the correct result, but the split `open -> new action selection` loop is unnecessarily fragile.

### E2E-B10 — Goal pollution, then coding and environment errors compound

1. The user requested “run the tests.” `goal_commit` (`MR-12aa83a8847a4bf8`) changed this to “all tests pass when run with pytest.” The supplied test file is a `unittest` file, and the isolated project runtime intentionally does not contain pytest. This is the first causal error.
2. T1 and T2 correctly read both `test_slug.py` and `slug.py`. The spacing assertion was present in the T1 observation.
3. T3 received that dependency but wrote `value.lower().replace(' ', '-')`, which produces repeated/leading/trailing hyphens and fails the observed spacing test. The Task-local exact-write check proved only that the model's chosen bytes were written; it did not prove the user-level behavior.
4. T4 first reread the tests, then ran `python -m pytest`; the real observation was `No module named pytest`. RWKV next attempted `python3.13 -m pip install pytest`, which failed because that executable name is unavailable inside the sandbox.
5. Recovery converted the model-generated pytest requirement into fake environment Tasks. T5 read `test_slug.py` and then falsely committed “Python interpreter and dependencies are installed.” T6 reread the test file twice rather than running the available unittest command, after which unchanged-action stagnation exhausted the lineage budget.
6. External unittest correctly failed only the spacing case; `NotImplementedError` was removed, so the run made a real but insufficient code change.

Amplification chain: Goal rewrite added an unnecessary framework dependency -> plan encoded pytest -> correct observed test semantics were not applied in code generation -> environment failure was misdiagnosed as a missing interpreter -> recovery Tasks asserted installation from a read -> repeated reads blocked the run.

### E2E-M01 — Correct read frontier, then action-state echo and no mutation

1. Goal and initial plan preserved the requested three-file migration and summary.
2. T1 listed exactly `api.json`, `web.json`, and `worker.json`. T2/T3/T4 correctly used one initial `read_json` each; full JSON values were present once in their action contexts.
3. After T2 correctly committed `open` because a read cannot update the file, the next action selector (`MR-b495a81f741e4052`) chose `read_json` again. Its own reason says no mutation occurred, yet concludes that another identical read is the next step. The prompt already exposed `patch_json` and `write_json` effects.
4. The following fixed-argument request echoed the entire supplied action ledger/failure state around the unchanged `read_json` call. Three schema retries varied only the envelope. The transparent boundary rejected unknown semantic/state fields and T2 became blocked before any write.
5. T3 and T4 remained open after their reads; T5 could not start. No service or summary file was changed, matching the isolated external failure.

Earliest semantic error: the second T2 action selection repeated a completed idempotent read at the same workspace state. The envelope format error is downstream. A broader normalizer could extract the unchanged call, but would only execute another wrong read; format handling alone cannot fix this case.

### E2E-M03 — Correct final artifact, false negative caused by Goal and verification layers

1. `goal_commit` (`MR-2718f0daa9b4488a`) invented two requirements absent from and contrary to the request: GC9 says `users.json` must not be modified in place; GC10 requires a backup. The user explicitly requested migration of `users.json`. This is the first causal error and makes the generated Goal internally incompatible with the desired artifact.
2. Initial T1 combined “list workspace” and “read users.json” in one Task. RWKV selected `read_json` four times while repeatedly explaining that the missing operation was `list_directory`.
3. The original T2 and T3 then read the *unmigrated* file and incorrectly committed that schema v2 / all migration criteria were satisfied. These are Task-level false-positive semantic decisions.
4. The goal-obligation path duplicated old Tasks. T5 finally made the correct `write_json` change with the exact two migrated records. The isolated external verifier passed the final file.
5. Verification Tasks repeatedly read the correct current file but claimed a read cannot establish whether its visible fields meet the migration criteria. Several reads used the old 187-character length and truncated the enlarged migrated object before the final `:2}`; other reads did contain the complete object.
6. Recovery created verification Tasks depending on failed or stale Tasks and continued the same read/open loop. The run exhausted its budget and blocked despite a correct final workspace, producing FN=1.

Amplification chain: contradictory generated criteria -> combined multi-effect Task -> false Task completion on original data -> obligation duplication -> eventual correct mutation -> stale/truncated verification and invented criteria prevent completion.

### E2E-M06 — Dependency value is visible, but the action loop cannot transition from read to copy

1. Goal and initial plan correctly preserve the selected-only copy and digest-manifest contract.
2. T1 read `selection.txt` and exposed exactly `alpha.dat` and `gamma.dat`.
3. T2's first action selection ignored that dependency and read `selection.txt` again. After every successful read, RWKV correctly said no copy had occurred, but selected the same read again four times.
4. `failure_analysis` incorrectly labeled the unchanged successful observation “plausibly transient” and explicitly endorsed retrying the same action.
5. Replan recreated essentially the same abstract copy Task. T6 repeated the same read twice and then stagnated. No `copy_file`, digest, directory creation, or manifest action ever ran.

Earliest error: T2 `action_name_selection` (`MR-853815c4960e41e0`) chose a dependency read instead of a producer action. The separate completion judge knew the read was insufficient, but that conclusion did not carry into a different next action. Recovery repeated the wrong semantic state instead of changing it.

### E2E-M12 — Repeated discovery and cross-Task failure contamination prevent any repair

1. Goal is faithful. The initial plan, however, contains only two directory-list Tasks, even though the initial manifest already identifies both files and the user requires their contents and a code mutation.
2. After T1/T2 completed, goal-obligation planning selected GC1 but produced the same two directory-list Tasks as T3/T4. A later obligation request expanded this into T5–T8, again only directory listings. Eight Tasks were spent observing the same two metadata entries.
3. T5's judge began insisting that a directory containing two files did not satisfy its phrase “one source file listing page.” Four identical lists and a recovery sequence followed.
4. Replan eventually produced T9/T10 repair Tasks. Both correctly read `math_utils.py` once and correctly judged the existing implementations broken.
5. On T9's second action selection, the reason was not about `safe_divide`; it copied T5's obsolete “single source file listing page” failure. This proves a recovery-lineage failure escaped its owning Task and became the next Task's authoritative failure context.
6. T9 and T10 each reread the same unchanged source twice and then blocked. No write and no test command occurred; external unittest failed both functions.

Earliest actionable error: the first goal-obligation frontier repeated already completed discovery instead of progressing to source reads. The decisive downstream architecture bug is cross-Task failure inheritance, which displaced the current repair observation with an irrelevant parent failure.

## Shared root causes, ordered from upstream to downstream

1. **Model-generated Goal is a lossy semantic rewrite.** Two of seven cases prove material damage: B10 adds pytest; M03 adds two contradictory backup/no-in-place criteria. Because every later layer treats Goal as immutable authority, one early model error becomes more durable than the user's actual request.
2. **There is no single progress decision.** RWKV first says a Task is `open`, then receives a separate action-selection request. In M01, M06 and M12 the completion call accurately says the read is insufficient, while the next selector chooses the same read. Splitting one thought across two model samples creates direct contradictions.
3. **Failure context is verbose, duplicated and not strictly Task-local.** The compact ledger is followed by a full `TaskPostconditionOpen` object containing the same attempt, evidence and model reason. M01 echoes this envelope as output; M12 T9 receives T5's unrelated failure. The state is unique only at the outer section level, not semantically unique inside the packet.
4. **Unchanged successful reads are treated as retryable failures.** M06's failure analysis calls an identical successful observation transient. Current suppression happens after repeated execution and recovery transitions, so the model is rewarded with the same evidence several times before the system stops.
5. **Goal criteria/obligation planning is a second competing task planner.** B01 turns a completed two-step request into seven Tasks; M12 repeats discovery; M03 duplicates stale verification Tasks. It does not reliably recognize sufficient existing observations and can generate new Tasks whose dependencies point to failed or obsolete Tasks.
6. **Task-local deterministic checks can be mistaken for semantic proof.** An exact-write check proves that RWKV's chosen bytes reached disk, not that those bytes satisfy the user's behavior. B10 T3 and early M03 commits demonstrate why effect confirmation and Goal completion must remain distinct.
7. **Format echo is a symptom, not the principal cause.** M01 contains a common state-envelope echo that a bounded normalizer could unwrap without changing the action. But the embedded action is still the wrong repeated read. Expanding normalization before fixing state/action semantics would only execute bad decisions more reliably.

## Architectural direction justified by the data

- Preserve the user's request byte-for-byte as the only Goal authority. Do not ask RWKV to rewrite it into a stronger objective or invented criteria.
- Merge Task completion and next-action choice into one RWKV `task_step`: return either `complete` with evidence refs or `act` with the next registered action name and a reason. Only `act` triggers the fixed-argument boundary.
- Build the Task packet from one ordered Task-local ledger, current observations and one compact failure delta. Do not embed full validation objects or inherited recovery prose.
- Suppress execution of an unchanged idempotent action at the same workspace digest and return a deterministic duplicate/no-progress observation to RWKV; the controller still does not select the replacement.
- Replace the criteria-driven goal-obligation planner with one iterative frontier decision over the verbatim user request and completed real observations. It may either return the next minimal Task frontier or finish. It must not manufacture a second evidence ontology.
- Keep deterministic effect checks for execution integrity and safety only. Final task/goal semantics remain RWKV decisions, and the final answer remains byte-exact raw RWKV output.
- Register a bounded transparent extractor for the observed common state-envelope representation only after the unique action state is implemented; it may preserve a single embedded registered action and arguments but must reject conflicts and must never change their values.

