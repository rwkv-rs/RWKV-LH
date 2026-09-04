# Round46 Uploaded Baseline: Manual Backward Causal Analysis

## Purpose and method

This document is the human, case-by-case analysis of the complete real-RWKV
E2E-90 run produced from uploaded commit
`14d864d71bf670b479a33f4fdb63b4772b69d3c8`. The generated
`CAUSAL_ANALYSIS.md` is used only as a navigation and integrity index. It does
not replace manual inspection of the request, frozen Codex reference, external
checks, raw RWKV responses, normalized protocol payloads, executed actions,
Task postcondition decisions, Goal evidence decisions, and final answer.

For each incorrect case the analysis proceeds backward from external truth,
then identifies:

1. the first point at which the model-owned state diverged from the request;
2. every later layer that detected, preserved, or amplified that divergence;
3. whether protocol normalization changed semantics;
4. the architecture boundary implicated by the evidence.

No benchmark answer, criterion, path, value, tool, or decision is inferred or
inserted by this analysis. The fixed external checks remain the authority for
Strict correctness.

## Frozen aggregate result

| Group | Strict | External | Agent completed | False positive | False negative |
|---|---:|---:|---:|---:|---:|
| Basic | 24/30 | 24/30 | 25/30 | 1 | 0 |
| Medium | 5/30 | 5/30 | 17/30 | 12 | 0 |
| Hard | 2/30 | 3/30 | 13/30 | 11 | 1 |
| Total | 31/90 | 32/90 | 55/90 | 24 | 1 |

The Basic-only score therefore materially understates the architecture defect.
The central quality problem is not merely failure to act: 24 runs declared the
Goal complete while the frozen external checks still failed.

## Manually inspected false positives

### E2E-B29 — lossy value transfer, then two independent equality hallucinations

- **External truth:** `backup/manifest.txt` was exact, but
  `backup/source.txt` did not equal `source.txt`.
- **First divergence:** T1 read the exact 27-character source
  (`"immutable payload\nline two\n"`). For T2, whose explicit Task was to copy
  that content, RWKV selected `write_file` and emitted only `"line two"`.
  This is a model-owned action/value error. The registered `copy_file` action
  was available.
- **Task amplification:** after the write returned only `"file written"`, the
  T2 postcondition response asserted that the destination contained the same
  content. T5 later read the actual eight-character destination and again
  asserted it matched the source. Thus the later observation did not correct
  the original loss.
- **Goal amplification:** GC4 bound the eight-character T5 observation as
  `actual_ref` and the 27-character T1 observation as `expected_ref`, then RWKV
  returned `pass`. The evidence identities were distinct and the observable
  payloads contradicted the decision.
- **Protocol boundary:** only registered aliases such as `tool` to `name` and
  `args` to `arguments` were normalized. The path and truncated content were
  byte-preserved. The format layer did not create the error.
- **Architecture implication:** progressive tool disclosure may improve the
  choice of `copy_file`, but Task and Goal evidence decisions must also learn
  to consume the observed values rather than equating action success or shared
  intent with artifact equality.

### E2E-M01 — incomplete plan omitted the requested mutation

- **External truth:** all three service JSON files retained their old versions
  and channels; the summary contained only the worker.
- **First divergence:** the initial RWKV decomposition planned listing and
  reading the files plus writing a summary, but created no Task that updated
  any service file. The Goal was already unreachable before action selection.
- **Action amplification:** a Task titled as reading `web` selected
  `read_json services/api.json` again, and the summary action wrote only the
  worker entry.
- **Task amplification:** generic postcondition decisions marked these partial
  observations and the incomplete summary as sufficient.
- **Goal/final amplification:** Goal evidence accepted the directory listing
  and incomplete summary. The final RWKV reasoning itself cited old values
  such as API `1.2/beta` and worker `1.4.1/edge`, yet announced that all files
  were updated.
- **Protocol boundary:** normalization changed syntax only and generated no
  semantic field.
- **Architecture implication:** this case begins at decomposition, so a tool
  selection change alone cannot fix it. Goal coverage must remain visible
  through planning, execution, and evidence binding.

### E2E-M06 — correct plan, wrong mutation tool, manifest used as proxy for artifacts

- **External truth:** neither selected source file was copied into `package/`;
  only the digest manifest existed.
- **First divergence:** T1 correctly read `selection.txt`. T2 explicitly asked
  to copy the selected files, but RWKV selected `write_file` on
  `package/manifest.json` instead of executing `copy_file` for the sources.
- **Task amplification:** the postcondition declared that only the listed files
  had been copied even though its observation established only a manifest
  write. T3 rewrote the same manifest and was also accepted.
- **Goal amplification:** Goal evidence treated the manifest snapshot as proof
  that the referenced files existed and had the required bytes.
- **Protocol boundary:** a later invalid extra-argument response was corrected
  under the existing single-schema correction path, but that could not repair
  the absent copies. Normalization did not invent the selected tool.
- **Architecture implication:** this is a direct target for RWKV-owned
  progressive tool disclosure, plus a separate evidence-ownership defect:
  metadata describing an artifact is not evidence that the artifact exists.

### E2E-M07 — nested structure flattened after correct tool selection

- **External truth:** the result placed `cache` and `trace` at the top level;
  the required nested `features` object was absent.
- **First divergence:** RWKV correctly read both input objects and selected
  `write_json`, but emitted a semantically flattened merged value.
- **Task amplification:** a second write preserved the same wrong value; a
  later read returned that exact flattened object and the Task verifier called
  it correct.
- **Goal amplification:** all Goal criteria passed despite evidence containing
  no `features` object.
- **Protocol boundary:** syntax normalization preserved the emitted JSON value.
- **Architecture implication:** the tool name is not the bottleneck here. The
  architecture needs tighter observation-to-argument state transfer and Goal
  comparison that can reject a structurally different observed value.

### E2E-M08 — wrong tool followed by literal-template and ordering errors

- **External truth:** the Markdown had blank-line differences, emitted literal
  `name` labels, ordered `worker` before `web`, and did not match the specified
  exact format.
- **First divergence:** after correctly reading `metrics.json`, RWKV selected
  `write_json` for a Markdown output Task. A later health-check Task also wrote
  JSON to the Markdown path.
- **Action-content amplification:** the final `write_file` call interpreted
  `- name: status ...` as literal text rather than a field template and did not
  sort services by service name.
- **Task amplification:** an intermediate read exposed the serialized JSON and
  the final post-action snapshot exposed the exact malformed Markdown, but both
  were judged to satisfy the Task.
- **Goal amplification:** Goal evidence passed the malformed artifact.
- **Protocol boundary:** normalization preserved all semantic strings and
  ordering. It was not the source of the formatting error.
- **Architecture implication:** progressive disclosure can remove the early
  JSON/Markdown tool confusion, but exact-format quality still depends on
  carrying source rows into the write arguments and comparing observed output
  with the requested invariant.

### E2E-M11 — decomposition reduced a migration to inspection

- **External truth:** none of the four services was migrated and the summary
  contained unrelated service names and ports.
- **First divergence:** decomposition created four read-only inspection Tasks
  and one Task to inspect a summary that did not yet exist. It omitted every
  requested service mutation and omitted creation of the requested summary.
- **Recovery amplification:** the attempted read of the absent summary failed.
  RWKV correctly diagnosed that it had to create the file, but then wrote an
  unrelated `auth/billing/catalog/checkout` example with ports 8080--8083,
  even though the four preceding observations contained
  `api/auth/jobs/web` and ports 8000--8003.
- **Goal/final amplification:** the Goal accepted an old service observation
  (`schema_version=1`, non-stable channel) and the unrelated summary. Final
  reasoning noticed the initial values yet announced migration success.
- **Architecture implication:** the first defect is Goal-to-plan coverage; the
  recovery defect is failure to carry the four observed values into a later
  write. Tool disclosure alone cannot restore omitted mutation Tasks.

### E2E-M15 — output synthesized before source reads

- **External truth:** byte totals happened to be correct, but the output used
  the wrong top-level key, paths were relative to the workspace instead of
  `docs/`, and two line counts were wrong.
- **First divergence:** decomposition described listing and reading files but
  omitted an explicit create-and-verify index Task. After the recursive listing
  exposed only paths and byte sizes, RWKV used inspection Tasks T2--T4 to write
  the index before it had read two of the three file contents.
- **Value amplification:** it guessed `line_count=1` for every file, used
  `entries` rather than `files`, and copied `docs/`-prefixed paths. Repeated
  writes preserved that guessed object.
- **Task/Goal amplification:** Task decisions called the guessed counts exact;
  five Goal criteria bound only the directory listing, not the created index.
- **Architecture implication:** selecting an observation tool for each read
  Task may stop premature writes, but planning also needs an explicit synthesis
  Task and the synthesis must depend on all complete file observations.

### E2E-M16 — fallback discovery succeeded locally but no synthesis Task existed

- **External truth:** `recovered.json` was never created.
- **First divergence:** decomposition created only five primary-file read
  Tasks. It omitted fallback Tasks, the required ordered aggregation, the
  sources map, and creation/verification of `recovered.json`.
- **Recovery behavior:** action recovery did reach `fallback/item_04.json` for
  an invalid primary, showing that a local failure could be repaired. That
  recovery did not add the globally omitted output transition.
- **Goal amplification:** the run completed after observations only, with no
  output artifact that could support the requested result.
- **Architecture implication:** local action recovery cannot repair a
  globally incomplete graph. Goal coverage and graph extension must remain
  RWKV-owned but must be explicitly revisited after discoveries.

### E2E-M17 — mutation arguments guessed without reading package contents

- **External truth:** all three dependency lists were wrong and unrelated
  `version` fields remained; the derived matrix consequently encoded the wrong
  graph.
- **First divergence:** decomposition scheduled one directory listing followed
  directly by three mutation Tasks. No Task read any package JSON before a
  preservation-sensitive update.
- **Value amplification:** RWKV guessed package contents and dependency lists,
  then wrote those guesses with the correct `write_json` tool. The matrix was
  consistently derived from the newly corrupted package values.
- **Task/Goal amplification:** postcondition and Goal decisions treated the
  self-consistent mutated files and matrix as proof that original dependencies
  had been preserved.
- **Architecture implication:** this is an observation-provenance problem,
  not a tool-name problem: fields advertised as preserved must come from a
  complete source observation rather than model prior or neighboring artifacts.

### E2E-M18 — digest task collapsed into creating an empty manifest

- **External truth:** `digest_map.json` was `{}`; all three recursive inputs
  and digests were absent.
- **First divergence:** decomposition listed `inputs/` but created no Tasks to
  read or hash its discovered files and no Task to synthesize the digest map.
  Instead it created multiple Tasks that attempted to inspect an output that
  did not exist.
- **Recovery amplification:** after that read failed, RWKV changed the action
  to `write_file` and created `{}`. Subsequent reads established only that this
  empty object was valid JSON.
- **Goal amplification:** the run treated existence and parseability of the
  empty map as satisfaction of byte-exact digest criteria.
- **Architecture implication:** output existence is not content coverage.
  Recursive discovery must feed bounded per-file observation Tasks and their
  complete results into a later RWKV synthesis step.

### E2E-M25 — correct source observed, final ordering invariant lost

- **External truth:** the 1.2.0 entries were not sorted by type and the file had
  one extra trailing newline.
- **First divergence:** an early Task intended to read a nonexistent output
  instead wrote a large unrelated example. After the real `changes.json` was
  available, later RWKV calls used the correct final tool but retained
  `fix` before `add` for version 1.2.0.
- **Task/Goal amplification:** the final read exposed the exact incorrect order
  and newline count, yet the verification Task and Goal accepted it.
- **Architecture implication:** progressive disclosure can reduce the earlier
  read/write confusion; it cannot implement the requested sort. The invariant
  must be retained in the synthesis capsule and checked against the observed
  output by RWKV.

### E2E-M26 — validation output omitted at decomposition

- **External truth:** `validation.json` did not exist.
- **First divergence:** decomposition produced five generic inspection Tasks
  and no validation/synthesis/write/verify Task. It also mislabeled several
  descriptions and postconditions as source listings.
- **Action amplification:** T2 listed the directory instead of reading
  `schema.json`; T3 read `schema.json` despite being titled as inspection of
  `validation.json`. The records and schema were therefore never joined in a
  model-owned validation step.
- **Goal amplification:** the run completed from observations although no
  result artifact existed.
- **Architecture implication:** the graph needs explicit output obligations
  and dependency coverage; tool selection is only a secondary defect here.

### E2E-M29 — correct observations and tool, wrong output schema

- **External truth:** translations were flattened into the top-level object,
  the required `translations` object was absent, and `bye` was missing from
  `missing_keys`.
- **First divergence:** T1 and T2 correctly read both source objects, and T3
  correctly selected `write_json`; the RWKV-emitted value itself used the
  wrong schema and computed an incomplete missing-key set.
- **Task/Goal amplification:** T4 read the exact wrong object, after which both
  the Task verifier and Goal evidence passed it.
- **Architecture implication:** this is a pure observed-values-to-structured-
  argument error followed by false certification. It is outside Round50's
  tool-name hypothesis.

### E2E-H02 — complete input traversal without an aggregate transition

- **External truth:** `aggregate.json` did not exist.
- **First divergence:** decomposition correctly listed and read all four
  shards but omitted the aggregation, write, and verification Tasks.
- **Goal amplification:** the run completed from the four observations even
  though there was no aggregate artifact.
- **Architecture implication:** discovery/read fan-out must feed an explicit
  reduce-and-write continuation. Successful reads alone cannot resolve an
  output-producing Goal.

### E2E-H03 — path and observed-value loss at the first pipeline stage

- **External truth:** none of the required `stages/stageN.txt` files existed.
- **First divergence:** decomposition itself dropped the `stages/` directory
  from every stage path. After T1 read the seed value, the first write emitted
  literal `seed.txt|1` rather than the observed seed content and wrote it to
  root `stage1.txt`.
- **Chain amplification:** every later stage appended to that wrong literal
  and wrong path. The final verification Task wrote a self-authored PASS report
  instead of reading the six artifacts.
- **Architecture implication:** dependency topology was retained, but path and
  value provenance were not. Downstream dependency chains magnify a single
  early argument error unless each stage observes or faithfully carries its
  predecessor artifact.

### E2E-H08 — uniqueness requirement converted into per-id frequency schema

- **External truth:** resume idempotency passed, but the ledger schema and
  meaning were wrong: RWKV produced per-id counts instead of `event_ids` plus
  the count of unique ids.
- **First divergence:** the source was read correctly and `write_json` was the
  correct tool; the synthesized value misinterpreted the requested `count`
  field and introduced an unrequested `events` structure.
- **Task/Goal amplification:** the exact wrong JSON was read back and accepted.
- **Architecture implication:** runtime resume semantics are sound in this
  case. The remaining defect is semantic synthesis and comparison, not
  persistence or tool selection.

### E2E-H11 — repair Goal reduced to five read-only Tasks

- **External truth:** `pipeline.py` remained broken, the verifier still failed
  at normalization, and `release.json` was absent.
- **First divergence:** decomposition contained only reads (including duplicate
  reads mislabeled as manifest and Goal specification), with no edit, command,
  staged verifier, artifact generation, or final verification Task.
- **Goal amplification:** all reads completed and the Goal was certified despite
  no mutation or verifier execution.
- **Architecture implication:** coding tasks require an iterative
  observe-edit-run-observe continuation. A static read-only graph cannot
  satisfy a repair Goal.

### E2E-H13 — a 24-file phased Goal collapsed to four individual reads

- **External truth:** no phase checkpoint and no summary existed.
- **First divergence:** decomposition represented only directory listing and
  reads of documents 01--04. It omitted the remaining 20 reads, all six phase
  writes, final summary, and verification.
- **Goal amplification:** the run completed from a partial first-phase
  observation.
- **Architecture implication:** a Task described as a batch cannot be fulfilled
  by one single-file action. Runtime discovery needs RWKV-owned graph expansion
  or a continuation that materializes one bounded Task per discovered member.

### E2E-H15 — project implementation proceeded without requirements or tests

- **External truth:** the actual `event_report/` stubs remained unchanged,
  tests failed, the report was unrelated to `example.txt`, and five manifest
  digests were the empty-file digest.
- **First divergence:** decomposition began directly with implementation and
  omitted reads of `REQUIREMENTS.md`, tests, existing package paths, and input.
  The actions then wrote root-level `parser.py`, `analyzer.py`, and
  `reporter.py` rather than the required package modules.
- **Tool amplification:** the Task titled `Run tests` selected `write_file` and
  fabricated a report instead of executing the verifier. Later outputs and
  documentation were based on an unrelated imagined event schema.
- **Evidence amplification:** the digest manifest used guessed empty-file
  hashes without digest observations, while every Task and Goal check passed.
- **Architecture implication:** this combines missing prerequisite observation,
  wrong paths, wrong action selection, fabricated test success, and fabricated
  digests. Progressive tool disclosure targets only the `Run tests` action;
  coding quality also needs actual verifier feedback to drive subsequent edits.

### E2E-H17 — unique-entry semantics misread, then verification mutated output

- **External truth:** resume behavior passed, but the ledger was a JSON string
  containing an array of per-id aggregates instead of the required object.
- **First divergence:** after a correct source read, RWKV interpreted “one entry
  per unique event id” as grouping duplicate amounts and emitted per-entry
  `count`/`total_amount`, rather than keeping the first-seen event and adding
  global count/total fields.
- **Verification amplification:** a later Task intended to verify resume safety
  selected `write_json` and supplied the already serialized array as a string,
  changing the artifact from an array to a JSON string.
- **Goal amplification:** the mutated output was accepted.
- **Architecture implication:** verification Tasks must select observation
  actions, but the initial semantic aggregation error remains a separate model
  synthesis problem.

### E2E-LH01 — staged repair reduced to inspection and fake artifact recovery

- **External truth:** no verifier command ran, the source remained broken, and
  `release/release.json` was absent.
- **First divergence:** decomposition included only workspace/source/verifier/
  input/output inspection Tasks. It omitted all edits and staged verifier runs.
- **Recovery amplification:** reading the absent release artifact failed; RWKV
  recovered by writing an unrelated `release.json` at the workspace root.
- **Goal amplification:** the run accepted the read-only state and wrong-path
  artifact as completion.
- **Architecture implication:** like H11, this requires iterative planning from
  real verifier observations. Recovery must not turn an absent expected output
  into arbitrary content merely to make a read Task succeed.

### E2E-LH05 — 20-member resilient traversal stopped after directory metadata

- **External truth:** neither report existed.
- **First divergence:** decomposition contained directory/rules/workspace
  inspection and a single shard read. It omitted the other 19 primary/fallback
  selections, byte digests, aggregation, both outputs, and verification.
- **Action/recovery behavior:** even directory pagination required recovery,
  but the resulting listings never became per-shard work.
- **Goal amplification:** a partial observation of shard 01 was accepted for a
  complete 20-shard obligation.
- **Architecture implication:** this is the same missing discovery-to-fan-out-
  to-reduce chain as H13, with additional fallback and exact-byte provenance.

### E2E-LH09 — API workflow repeatedly selected create and collapsed four phases

- **External truth:** create's required transient failure occurred, but three
  duplicate conflicts accumulated; update/finalize never occurred and no
  result file existed.
- **First divergence:** T1 was an inspection Task but selected `mock_api create`.
  T2 was meant to read the workflow yet selected create again. T3 created again.
  Only T4 correctly queried.
- **Graph/action amplification:** T5 combined update, deliberate replay, and
  finalize in one Task even though one materialized action cannot perform those
  three calls; RWKV selected create once more and interpreted its duplicate as
  the requested update replay.
- **Goal amplification:** the state `name=initial`, version 1, unfinalized was
  nevertheless accepted.
- **Architecture implication:** this is the strongest direct Round50 target,
  but it also proves the graph needs one explicit Task/action per API phase and
  must carry observed API state between them.

### E2E-LH11 — phase descriptions were mistaken for executable batch reads

- **External truth:** none of five checkpoints and no memory summary existed.
- **First divergence:** decomposition created five list Tasks and five Tasks
  described as reading eight files each, but each materialized action can read
  only one file. It also omitted every checkpoint and summary write.
- **Pagination/action amplification:** each list reused `start_after=null`, so
  later phases repeatedly listed the first page; multiple read Tasks returned
  artifact 001 or 002 instead of their advertised ranges.
- **Goal amplification:** eleven attempts were enough to satisfy the runtime
  count check, but the run certified no actual phased coverage.
- **Architecture implication:** natural-language batch labels are not state.
  The architecture needs cursor-bearing discovery, member-level Tasks, phase
  aggregation, and checkpoint commits that survive context refresh.

## Manually inspected false negative

### E2E-LH02 — externally perfect artifacts rejected by an ambiguous evidence ID

- **External truth:** all 15 checkpoints and `final/config.json` were exactly
  correct; all external checks passed.
- **Successful execution:** RWKV correctly carried the five early constraints
  into every checkpoint and final output across 18 Tasks.
- **First divergence:** for GC16, the criterion-local catalog exposed the
  post-action snapshot as `M-T16-A1-POST-R1`, while current causal state also
  advertised Task output ref `M-T16-A1`. RWKV selected `M-T16-A1` twice. That
  ref is semantically tied to the same successful T16 action but was outside
  the criterion's exact allow-list, so both responses were rejected.
- **System amplification:** one invalid local ref discarded the already
  collected passes for GC1 and GC10--GC15 and blocked the complete provenance
  commit for all 19 criteria. The ensuing Goal replan included the full large
  capsule, echoed the capsule instead of a Task batch, hit the output length
  limit twice, and blocked the run.
- **Protocol boundary:** this was not a format alias or a changed decision. It
  was an interface ambiguity between two visible IDs for the same attempt plus
  all-or-nothing evidence commit and an oversized fallback.
- **Architecture implication:** a future round should present only eligible
  criterion-local refs (or one canonical artifact ref per observation), commit
  independent criterion decisions incrementally, and avoid replaying the whole
  capsule when a single ref is invalid. None of those changes may substitute a
  controller-selected ref for RWKV's decision.

## Manually inspected safe failures

These cases did not falsely report success, but they still identify quality
losses. A safe block is preferable to a false positive; it is not a completed
agent task.

### Basic safe failures

| Case | First divergence | Later behavior and architectural meaning |
|---|---|---|
| E2E-B04 | A directory-creation Task selected `write_file`, creating a file named `archive/2026`; the copy Task later wrote only the manifest. | Task-level RWKV checking correctly noticed that the copy had not occurred and blocked. The safety gate worked, but the action catalog/tool-selection interface made a basic directory/copy operation fail. |
| E2E-B22 | RWKV wrote ordinary bullets instead of unchecked `- [ ]` items. | A newline-check Task selected `append_file` and added a second newline. Task checks passed, but Goal evidence ultimately rejected the exact malformed artifact. This is argument formatting plus a verification-as-mutation error. |
| E2E-B23 | Invalid primary JSON was treated as failure of the “observe validity” Task rather than the expected condition selecting the fallback. | Backup JSON was read successfully, but dependency blocking prevented selection and output Tasks. Conditional observations need explicit valid/invalid outcomes that can satisfy discovery without declaring the whole Task failed. |
| E2E-B27 | `replace_text` changed only the first occurrence because RWKV did not request replacement of all matches. | The verification call mixed unsupported `end_char` into `read_file` and protocol-blocked. The run safely stopped with two old occurrences remaining. |
| E2E-B30 | A Task titled “run the test” selected `write_file` and rewrote `test_names.py`, removing its import; the final test Task only read the test file. | `names.py` itself was implemented correctly, but tests were damaged and never executed. Goal blocking prevented a false claim. This is a strong observation/execution tool-selection failure. |

### Medium safe failures

| Case | First divergence | Later behavior and architectural meaning |
|---|---|---|
| E2E-M02 | The very first Goal parse expanded a small request into an unbounded repetitive list of invented test constraints. | Generation hit the 1600-token limit without a complete JSON object, and no run state was created. Goal normalization needs compactness and bounded correction, not controller-authored criteria. |
| E2E-M04 | After three correct source reads, the Markdown write emitted `create_parents` and `overwrite` outside the tool arguments object. | The strict protocol correctly rejected the malformed call, but the correct JSON action remained pending and no outputs materialized. This is a tool-call schema presentation problem. |
| E2E-M09 | Decomposition never scheduled replacement of imports/calls in `src/consumer.py`; it only changed `src/api.py`. | Real unittest output exposed the stale `old_api` import. Recovery reran the failing command rather than adding the missing consumer edit, then blocked. Verifier feedback was observed but did not drive graph repair. |
| E2E-M10 | A read-manifest Task selected the desired output write and repeatedly encountered the injected transient failure. | All attempts remained attached to the wrong Task; no `replan_applied` event occurred, so dependent creation/verification Tasks blocked. Recovery policy did not turn repeated transient evidence into the required plan decision. |
| E2E-M13 | RWKV repeatedly guessed wrong revenue totals and the wrong `by_region` schema after reading the CSV. | A later checker incorrectly claimed already sorted keys were unsorted, then recovery ended on an incomplete JSON response. Blocking was safe, but neither computation nor diagnostic attribution was accurate. |
| E2E-M14 | Correct `release.json` was opportunistically written during a sort Task. | A redundant JSON-write Task mixed `write_file` arguments into `write_json` and blocked before Markdown creation. Single-schema argument disclosure directly targets this cross-tool mixing. |
| E2E-M20 | RWKV produced a plausible `parse_records` implementation. | The re-run-test Task selected `write_json` on `parser.py` and replaced the code with a JSON string, so imports failed. A verification action mutated and destroyed the artifact it was meant to test. |
| E2E-M21 | Decomposition was entirely read-only and attempted to inspect `merged_users.json` before creating it. | Three retries kept reading the absent output; the two valid source observations were never synthesized. Missing-output recovery failed to introduce the omitted write transition. |
| E2E-M22 | Decomposition read all three inputs but omitted result synthesis and creation. | The only result Task tried to read a non-workspace-relative path and protocol-blocked. Complete observations were stranded because no reduce/write Task existed. |
| E2E-M23 | Decomposition misread the build plan as a request for `dist/tree.txt`, an undeclared artifact, and omitted the three declared files. | Manifest paths were not lexically sorted and a verification response used unsupported top-level `action`; protocol blocking prevented a false completion. The primary defect predates tool selection. |
| E2E-M27 | Correct inputs and tool produced a valid topological order but violated the alphabetical tie-break (`web` before `docs`). | The final read exposed the exact order and Goal evidence rejected it. This is a useful true-negative: the Goal layer caught a subtle semantic error that Task completion missed. |
| E2E-M28 | The move Task selected `write_json` and wrote a report instead of moving files. | The report also used `logs/`-prefixed names. A later archive listing failed and the run blocked. Tool choice is upstream; coverage also requires one move per selected file. |
| E2E-M30 | The config-migration Task selected `write_json` on the report, leaving `config.json` unchanged. | The report used string versions and a different rename schema; the verifier Task then mixed write schemas and blocked without running the verifier. This combines wrong target/tool semantics and argument-schema interference. |

### Hard and long-horizon safe failures

| Case | First divergence | Later behavior and architectural meaning |
|---|---|---|
| E2E-H01 | Decomposition scheduled only five inspection Tasks and omitted implementation, tests, example generation, and verification. | The model connection dropped during the first Task's postcondition call, causing an outcome-unknown interruption. The transport failure is real, but the frozen graph was already insufficient before it occurred. |
| E2E-H05 | One Task claimed it would read the first two lines of every corpus document although one action can read only one file. | A subsequent response used unsupported top-level `action` and protocol-blocked. The graph needed member-level fan-out before filtering and aggregation. |
| E2E-H06 | All three environment migrations were semantically correct. | RWKV chose report key `migrated_environments` instead of required `migrated`; verification Tasks redundantly rewrote artifacts. Goal rejection safely caught this single-schema error after otherwise strong multi-file execution. |
| E2E-H07 | The Task titled “Run unittest discovery” selected `write_file` and fabricated `VERIFIED.txt` without running tests. | The real queue code remained broken; the edit response then contained unsupported `reasoning`/`tool` fields and blocked. This is execution-tool confusion followed by protocol failure. |
| E2E-H09 | Decomposition encoded primary and fallback as parallel branches, but made final verification depend on both; missing primary was treated as a terminal failed dependency. | The valid backup branch was ready but never executed after the primary blocked. Conditional fallback requires a resolved-selection node, not an AND dependency on success of both alternatives. |
| E2E-H10 | A reasoning-only “compute totals” Task was inserted between complete input reads and output writes. | RWKV could only materialize Harness actions and repeatedly reread `policy.json`; Task checking correctly said no totals were computed and blocked all outputs. Computation should occur in the RWKV write commitment or produce an explicit observable state, not an unactionable Task. |
| E2E-H12 | A single Task claimed to read all 15 shards. | Three attempts read only individual shards; the Task checker correctly refused to equate one member with the whole set and exhausted recovery. This is direct evidence that batch prose must become member-level Tasks. |
| E2E-H14 | After reading only the root manifest, an inspection Task selected `write_json` and fabricated paths/counts from an unrelated catalog pattern. | The eventual data-read response mixed `read_file` and command arguments and protocol-blocked. Recursive discovery must be observation-driven before synthesis. |
| E2E-H16 | Baseline observation read only `capacity.json`, not `runtime.json`; applying changes updated only capacity. | “Run invariant check” repeatedly read policy and was accepted locally; rollback wrote only `compensation.json` rather than rolling back config files. A later protocol error stopped the run. Each state mutation and verifier command needs its own observable action. |
| E2E-H18 | Decomposition ordered validator repair and execution before creating either release input, and omitted product/report/digest Tasks entirely. | The validator command failed three times on absent outputs; recovery repeated it rather than extending/reordering the graph. Real verifier feedback did not cause producer correction. |
| E2E-LH03 | Root manifest was read, then a recursive-discovery Task immediately wrote a fabricated global index without opening any referenced manifest or data file. | Repeated guessed writes were followed by cross-tool argument mixing and a safe block. This is discovery-to-fan-out failure plus schema interference. |
| E2E-LH06 | The graph guessed approved/draft/untrusted filenames before reading the authority policy and did not include directory discovery. | Guessed or non-relative paths failed, but no scope violation occurred. The safety boundary held; staged planning from the policy observation did not. |
| E2E-LH07 | Listing eight service filenames was treated as sufficient input for an upgrade; no service JSON was read. | Upgrade and special-migration Tasks repeatedly wrote only a malformed report, and the real compatibility command exposed untouched services. Recovery reran the verifier instead of producing per-service edits. |
| E2E-LH08 | Decomposition stopped after five inspection Tasks; the Task claiming to read three configs read only `a.json`. | No requested changes, invariant command, compensation, or report Tasks existed. The run blocked safely, but the entire mutation/feedback loop was absent. |
| E2E-LH10 | Decomposition framed absent deliverables and test output as files to read, omitted source repair, real test execution, documentation generation, and hashing. | Multi-file inspection was packed into one action-incompatible Task; attempted reads/writes of absent files and guessed paths blocked within five attempts. The 35-action budget was not the limiting factor. |
| E2E-LH12 | The graph read only `REQUIREMENTS.md`, not the existing package tree, tests, or example input, then wrote implementations at workspace root rather than `mini_project/`. | The test Task used a nonexistent absolute Python executable and retried it; real tests still hit package stubs. Downstream docs/report/digests stayed dependency-blocked. |

## Cross-case causal synthesis

The full failure set supports the following architecture conclusions. A case
may appear in more than one row because upstream and amplification defects are
independent.

| Boundary | Repeated evidence | Consequence |
|---|---|---|
| Goal/plan coverage | M01, M11, M16, M18, M21, M22, M26, H02, H11, H13, LH01, LH05, LH08 and others omit required mutation or output Tasks. | The Goal is unreachable before tools are chosen. |
| Task/action cardinality | H05, H12, H13, LH05, LH11 and LH10 describe many files in one Task while one Harness action handles one member. | Partial observations are mistaken for batch progress or safely deadlock. |
| Unactionable reasoning Tasks | H10 and several “parse/sort/calculate/check” Tasks have no observable effect compatible with one Harness call. | RWKV selects an arbitrary read/write action, creating tool/postcondition conflict. |
| Tool-name and schema interference | B04, B30, M04, M06, M08, M14, M20, M28, M30, H07, H14, LH03, LH09. | Wrong actions mutate the wrong artifact; mixed arguments cause avoidable protocol blocks. This is Round50's isolated target. |
| Observation-to-argument transfer | B29, M07, M08, M11, M17, H03 and others lose, flatten, guess, or replace observed values. | Correct reads do not reliably constrain later writes. |
| Conditional/recovery structure | B23, M10, M21, H09, H18 and LH09 either treat expected failure as terminal, retry an unchanged wrong action, or fail to add producer work. | The run cannot exploit real failure observations. |
| Task postcondition quality | Many false positives accept action success as content success; several safe failures correctly reject it (B04, H10, H12). | The same layer is sometimes protective and sometimes an amplifier, indicating inconsistent evidence use rather than a universally over-strict or over-lenient gate. |
| Goal evidence quality | All 24 false positives reached Goal completion despite failed external truth; M27 and H06 show useful rejection; LH02 rejects perfect outputs due ref ambiguity. | Goal verification needs a simpler canonical evidence interface and stronger observed-value reasoning, not deterministic answer rules. |
| Verifier feedback loop | M09, H11, H15, H18, LH01, LH07 and LH12 do not turn real command failure into targeted producer correction. | Coding-agent quality remains low even when the verifier exposes the exact next defect. |
| Protocol/transport robustness | M02 repeats until truncation, LH02's large replan truncates, H01 loses a request on disconnect. | Compact correction and outcome recovery matter for quality, independent of latency. |

### What Round50 can and cannot establish

The two-phase RWKV-owned tool protocol is justified because wrong tool names
and cross-tool argument mixing occur across all difficulty groups. It remains a
clean experiment: RWKV chooses the name, then RWKV emits arguments against only
that selected schema. No controller rule selects or changes the action.

It cannot be described as a general fix. Even a perfect Round50 result at the
tool boundary leaves plan coverage, member-level fan-out, conditional graph
semantics, value transfer, verifier-driven correction, and evidence
certification untouched. The complete E2E-90 quality result is therefore the
only valid retention signal.

## Interim cross-case finding

These first five false positives already disprove a single-cause explanation.
The observed chain has four separable failure boundaries:

1. decomposition can omit required state transitions (M01);
2. action selection can choose a mutation that cannot satisfy the Task (M06,
   M08, B29);
3. action arguments can lose or reshape correctly observed values even when the
   tool class is correct (B29, M07, M08);
4. Task and Goal decisions can certify claims contradicted by their own bound
   evidence (all five cases).

Round50 changes only boundary 2. It remains worth testing because it is a
repeated upstream failure and may prevent downstream damage, but the full-90
result—not the Basic subgroup—must decide whether it improves total quality.
Later rounds must address boundaries 1, 3, and 4 without letting controller
rules choose answers or overrule RWKV.
