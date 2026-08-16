# Round64 fixed-15 manual backward causal analysis

## Frozen outcome

- Strict E2E: `1/15` (`B01`)
- External acceptance: `3/15` (`B01`, `M03`, `M12`)
- Agent completed: `1/15` (`B01`)
- FP: `0`
- FN: `2` (`M03`, `M12`)
- Offline gates: pytest passed, clean LH-Control `30/30`, catalog/reference and 31-file parallel architecture regressions passed.
- The preregistered canary gate failed. Full90 was not run and Round64 is not upload-eligible.

This analysis follows each failure backward from the final external state to the first harmful decision. A case is not attributed to the last visible exception when an earlier interface or state transition made that exception likely.

## Case-by-case causal trace

### E2E-B01 — clean positive control

RWKV planned an inspect/create/verify chain, read the input, wrote the exact file, read the current file back, and selected sufficient Goal sources. The Controller did not add a semantic decision. This is the desired chain: real source observation -> RWKV action -> immutable Attempt/action record -> current workspace observation -> Goal evidence.

### E2E-B02 — usable class decision rejected, wrong correction traps actions

1. RWKV read `input.txt` correctly.
2. For the producer Task it returned the semantically usable class `mixed`, but also returned `reasoning` and `action_class_reason`.
3. The exact-two-field class parser rejected that result. The correction changed the class to `observe`.
4. The class gate then exposed only observation tools. RWKV repeatedly selected `read_json(input.txt)` for a key/value text file, received JSON errors, and blocked without creating the requested report.

The first harmful event is not the later JSON error. It is the redundant action-class protocol discarding a usable RWKV decision, then persisting a wrong correction that excludes producer tools.

### E2E-B10 — correct code edit cannot cross a prior execute class

1. RWKV inspected the code and tests, then ran the tests and observed the real `NotImplementedError`.
2. Failure analysis explicitly said to edit `slug.py`.
3. RWKV produced a complete correct implementation using the common `edit_file`/full-content shape.
4. The boundary rejected the common spelling and top-level call controls. Even if normalized, the prior `execute` class would have rejected the write.
5. Correction returned to test execution and the run blocked.

The model reached the correct repair. The architecture made a Task's recovery capability immutable before the failure was known and did not accept a common full-file edit representation.

### E2E-M01 — false-negative recovery corrupts already-correct artifacts

The initial chain read the service files and produced correct service updates and a correct summary while preserving unrelated fields. A late Goal evidence false negative caused a broad obligation replan. The recovery Tasks rewrote the service objects without `port`, `threads`, or `theme`, so the final workspace was worse than the earlier workspace.

The final corruption is a downstream amplification of unclear Goal-source presentation and all-or-nothing criterion collection. The recovery actions are still RWKV actions; the Controller did not rewrite them, but it unnecessarily made all criteria unresolved after one insufficient decision.

### E2E-M03 — correct workspace, preservation comparison missed, then broad replan fails

1. RWKV read the original JSON, wrote the exact migration, read it back, and produced the correct final workspace.
2. GC1-GC3 were supported. For the preservation criterion, RWKV said the original observations did not establish the final state even though both the pre-change source and the current post-change source were in the catalog.
3. The catalog did not clearly tell the model that preservation/equality may require a before-and-after source pair.
4. Because criterion decisions were collected atomically, the single insufficient result discarded the already supported criteria and reopened all obligations.
5. The replan copied persisted Task/capsule forms, failed the Task-batch boundary, and blocked. External acceptance remained correct, yielding an FN.

### E2E-M06 — genuine action-selection error remains visible

RWKV read the selection but did not use `copy_file`. In recovery it invented `alpha.dat content` and wrote only one selected file; it never produced the exact selected package and manifest. Goal adjudication correctly remained insufficient, eliminating Round63's FP.

This is a real RWKV planning/action weakness, not a case to mark complete. The action surface should make the explicit copy primitive clearer and the prompt should state that copying an existing workspace file uses `copy_file`, without the Controller choosing a file, argument, or answer.

### E2E-LH02 — valid enumerated Goal rejected by a hard size rule

RWKV twice returned a complete Goal proposal that preserved the 15 checkpoint requirements plus final/read requirements. The hard `success_criteria <= 12` rule rejected it before planning. The limit converted a valid long-horizon request into a protocol failure and must not be used as a semantic filter.

### E2E-LH05 — observation-only plan meets a nonexistent directory and cannot recover

1. The initial Task graph contained only inspection Tasks and no shard processor or report producer.
2. Listing real `shards/`, `fallback/`, and the recovery rules succeeded.
3. Listing nonexistent `reports/` failed. RWKV failure analysis explicitly proposed creating the directory.
4. The Task had already been bound to `observe`; the create action could not be expressed. The model then emitted a no-op with a reason field, retried the same listing, and blocked.

The initial model plan was incomplete. The architecture then amplified a recoverable missing-directory observation into a dead end by freezing a narrower capability than the recovery needed.

### E2E-LH11 — range labels become literal paths; common correction shape is rejected

The plan used phase labels such as `artifacts/009-016.txt`. Action selection treated them as literal paths. Failure analysis for one phase correctly switched to listing the real `artifacts/` directory, but six common `{"action":"list_directory","arguments":...}` calls were rejected. No file content, checkpoint, or summary was produced.

The model's range/path confusion is real. The boundary then prevented the one correct recovery call from executing. Action prompting should explicitly distinguish a Task range label from an observed exact workspace path.

### E2E-B24 — format rejection redirects correction into the immutable source

1. RWKV read the original log.
2. Its first producer call used the common `action/arguments` form and wrote a still-duplicated intermediate `sorted.log`; the boundary rejected the call before execution.
3. The correction switched tools and executed `remove_line` on `log.txt`, violating the preservation requirement.
4. Later writes made `sorted.log` exact, but the source was already damaged.
5. Goal adjudication also falsely described the correct sorted output as not deduplicated, and the broad replan failed.

The final external failure is caused by the RWKV correction mutating the source, but the correction was triggered by a representation-only rejection. Accepting the common envelope would have preserved the opportunity to reject the intermediate result semantically without touching `log.txt`.

### E2E-M12 — correct code and passing tests obscured by nested audit payload

RWKV read the source/tests, wrote the correct implementation, and ran passing tests. The current workspace snapshot and test result were both present. Goal adjudication nevertheless hallucinated that the current snapshot still contained the old multiplication implementation. The source catalog presented a post-action snapshot as a nested audit JSON object rather than direct file content, while also retaining an older superseded source. The resulting false negative opened recovery Tasks and eventually blocked on copied command/argument metadata. External acceptance remained correct.

The data was correct; the model-facing projection was unnecessarily indirect. Post-action snapshots should be unwrapped into direct path/content/hash observations and visibly marked current or superseded.

### E2E-M16 — correct read action blocked by wrong class

The plan sensibly separated inspection, primary reads, fallback reads, recovery, and verification. For “Read fallback JSON files”, the action-class call incorrectly returned `mutate`. RWKV then selected the correct `read_file(fallback/item_02.json)` twice, but the class gate rejected it before any Attempt. The run blocked with only the initial directory listing completed.

This is direct evidence that the class stage adds an independent failure probability while contributing no information that is not already present in the concrete RWKV tool call.

### E2E-M18 — correct nested read blocked by wrong class

Recursive listing exposed the real files. For `inputs/nested/c.txt`, RWKV incorrectly classified the read Task as `mutate`, then twice selected the correct `read_file` action. The class gate rejected both. The initial plan also omitted `a.txt` and the producer in its first frontier, but the run never reached the normal observation-driven next frontier because of the class block.

### E2E-H12 — correct correction still fails the class micro-protocol

After listing all 15 shards, the class call for “Read all 15 shard files” first returned invalid `unbound`. Its correction correctly returned `observe` but used `reasoning` instead of the required `reason`. The class parser blocked before a single shard read. No aggregate could be produced.

### E2E-H13 — complete 21-Task plan blocked before the first action

RWKV produced a detailed six-phase plan with reads, six checkpoints, a summary, and verification Tasks. Before action execution, the class call for T3 returned `unbound` twice and the whole run blocked with zero Attempts. The plan contains a separate later risk (`checkpoint/` vs requested `checkpoints/`), but that semantic issue was never exercised because the redundant class contract failed first.

## Cross-case causal groups

| First harmful layer | Cases | Downstream amplification |
| --- | --- | --- |
| Redundant Task action-class decision | B02, B10, LH05, M16, M18, H12, H13 | Correct actions excluded; recoverable failures become permanent; parallel frontier stops before Attempts |
| Incomplete common-format boundary | B10, LH11, B24, M01, M03, M06, M12, M18 | Representation retry changes the tool or repeats stale actions; correct recovery calls never execute |
| Goal source projection / atomic criterion collection | M01, M03, M12 | One false negative discards earlier supported criteria, opens a broad replan, and may damage an already-correct workspace |
| Hard Goal criterion count | LH02 | Valid task rejected before planning |
| Genuine RWKV semantic action weakness | M06; parts of LH05, LH11, B24 | Wrong copy/edit/path decisions remain visible and must be improved through clearer tools, state, and prompts rather than Controller correction |

## Architecture conclusion

Round64's append-only Task action ledger, immutable Attempt action, compact lossless `read_json`, stagnation boundary, single Goal semantic owner, and parallel isolated action proposals remain useful. The action-class gate does not: it is a second low-reliability model decision that filters the concrete RWKV decision, exactly the failure mode the non-cheating requirement warned about.

The next structure should therefore have one RWKV semantic action decision per step, one canonical internal action object, a small audited conversion layer for common wire representations, direct evidence projections, and incremental persistence of RWKV-supported Goal criteria. No Controller rule may choose an action, source ref, task, expected value, criterion result, or final output.
