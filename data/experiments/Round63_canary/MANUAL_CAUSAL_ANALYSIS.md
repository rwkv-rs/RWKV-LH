# Round63 fixed-15 manual causal analysis

## Frozen outcome

- Strict E2E: `2/15` (`B02`, `M12`)
- External acceptance: `3/15` (`B01`, `B02`, `M12`)
- Agent completed: `4/15` (`B02`, `M06`, `M12`, `M18`)
- FP: `2` (`M06`, `M18`)
- FN: `1` (`B01`)
- Offline gates: pytest `385/385`, LH-Control `30/30`, catalog `90/90`
- Round62 comparison: Strict unchanged at `2`; FN improved `2 -> 1`; FP regressed `1 -> 2`; external acceptance regressed `4 -> 3`.

The preregistered canary gate failed. Full90 was not run, and this candidate is not upload-eligible.

## Case-by-case causal trace

### E2E-B01 — external correct, Agent blocked

1. RWKV correctly wrote and then completely read `greeting.txt`; external acceptance passed.
2. The Task-to-Goal relation calls nevertheless labeled both exact write/read observations only `advances`.
3. Goal adjudication then incorrectly stated that the post-action snapshot did not contain content and that a read observation could not prove file existence.
4. Goal-obligation replan returned full persisted Task objects. The strict five-field Task parser rejected their known state-only fields, so the run blocked.

The first harmful error is semantic over-conservatism in Task-to-Goal classification. The final block is a separate boundary-format failure. The same real observations were sufficient before both failures.

### E2E-B02 — clean Strict pass

RWKV read `input.txt`, derived the real values, wrote the exact two-key JSON, read it back, and committed sufficient provenance. This is the desired compact chain: source observation, derived write, current read verification, then Goal completion.

### E2E-B10 — no run created

1. RWKV expanded a two-test coding task into a very long list of speculative edge-case criteria.
2. Both goal responses exhausted the output budget before the outer JSON object closed.
3. The JSON extractor selected the first complete nested criterion object from the truncated response.
4. Goal validation then reported that the parsed object had no `success_criteria` array.

The failure requires three parts together: unbounded Goal decomposition, response truncation, and a parser that accepts an inner object after an incomplete outer object. No tool or Task was reached.

### E2E-B24 — action-boundary format block

RWKV correctly read `log.txt`. On the next action it copied observation metadata (`end_char`, `start_line`, `truncated`) into `read_file` arguments. Those keys are known observation fields, not semantic action arguments, but the boundary rejected the action. The plan itself also split an in-memory transform into vague intermediate Tasks whose postconditions imply modifying the source despite the requirement to preserve it.

### E2E-M01 — destructive whole-object rewrite after incomplete observation

RWKV listed the three service files but never read their contents. It then used whole-object `write_json` actions containing only `name`, `version`, and `runtime.channel`, deleting `port`, `threads`, and `theme`. The summary was correct, but every transformed service lost unrelated settings. The current tool surface offers overwrite but no model-selected JSON patch/update operation, and no persisted causal dependency requires a preservation transform to consume a full source observation.

### E2E-M03 — `read_json` interface truncation precedes format failure

1. The source file is 188 bytes. RWKV selected `max_chars=188`, a reasonable value from the visible file size.
2. `read_json` pretty-printed the parsed value to 336 characters and then truncated at 188, leaving half of the second record unseen.
3. RWKV invented records/fields from the partial observation. Its first write call used the correct tool envelope but included unsupported `write_json` arguments; the retry used a common flat `{action,path,value}` envelope and was rejected.

Even perfect format normalization would not make the generated migration correct because the interface had already hidden source data. `read_json` size semantics are the earliest defect.

### E2E-M06 — read evidence repeatedly treated as copy evidence

1. The Task “copy listed files” selected `read_file(selection.txt)` instead of `copy_file`.
2. Task postcondition adjudication said the successful read established the copy postcondition.
3. Task-to-Goal classification sometimes correctly said no copy was observed, but also emitted `satisfies` for the same read.
4. Goal adjudication initially rejected the evidence, then later treated another read of `selection.txt` as proof of package contents and treated the manifest as proof of copied files/digests.
5. The Agent completed with only `package/manifest.json`; neither selected file existed.

The controller did not invent the answer, but its duplicated semantic stages allowed a later RWKV decision to overturn an earlier correct insufficiency decision without new causal evidence.

### E2E-M12 — Strict pass with unsafe intermediate claims

RWKV read source and tests, wrote the repaired module, and ran the tests successfully. The final test output directly supported all requirements, so the result was correct. However, the earlier test-file read was already labeled as satisfying implementation behavior before the implementation changed. The pass demonstrates that a strong final verifier can recover the chain, not that every intermediate Goal claim was sound.

### E2E-M16 — good local recovery, malformed frontier recovery

1. Initial planning created only five read Tasks and omitted `recovered.json` creation.
2. The missing primary for item 04 was handled correctly: failure analysis selected fallback and the Task completed.
3. With all initial Tasks complete and all Goal criteria unresolved, goal-obligation replan was required.
4. The first replan response emitted a `task_batch` wrapper containing speculative items 06–10 and state-only fields. The retry echoed a goal-obligation capsule instead of a canonical Task batch. The boundary blocked.

The architecture successfully handled a local missing-file branch but could not cross from discovery frontier to producer frontier.

### E2E-M18 — partial collection becomes FP

1. Recursive listing correctly exposed `a.txt`, `b.json`, and `nested/c.txt`.
2. RWKV read only `a.txt`, then wrote a one-entry map using the wrong `inputs/` key prefix.
3. Task-to-Goal classification explicitly recognized that GC4 was incomplete.
4. Final Goal adjudication later claimed the same one-entry map covered every recursive input and claimed the Goal supplied the expected bytes. It ignored the earlier directory observation showing three files.

This is a direct contradiction between two RWKV semantic passes over different projections. The criterion evidence catalog lacks an append-only working set that keeps all RWKV-labeled partial observations visible until final adjudication.

### E2E-LH02 — correct artifact produced, then verification destroyed it

1. T1–T17 correctly read the immutable requirements, wrote all 15 valid checkpoints, and wrote a correct `final/config.json` including `step`, all constraints, and `generated_by`.
2. Verification Task T18 selected a write to `final/config.json` rather than a read of checkpoints. RWKV's Task-postcondition call correctly said the action was unrelated and returned `replan`.
3. Round63 scheduled 31 continuations. RWKV repeated the exact same write under the exact same observation and incomplete reason until the 32-action cap.
4. Replan added verification Tasks T19/T20. T20 again chose writes and overwrote the previously correct final config three times, ultimately removing `generated_by`.
5. Every completed Task was also compared with all 18 Goal criteria: 504 model requests, 54 attempts, and a final database larger than 1 GB.

The first model error was choosing a mutating action for a verification Task. The controller amplified it because Tasks have no model-declared read/write capability boundary and because identical successful-but-irrelevant actions are allowed to repeat 32 times. The final external failure was caused after the correct result already existed.

### E2E-LH05 — nonexistent inspection Tasks dominate recovery

Initial planning listed real shard/fallback directories and read real recovery rules, but also invented `workspace_summary.json` and pre-existing `REPORT.md` inspection Tasks. Failure analysis repeatedly labeled their absence as transient/action-selection problems, changed nonexistent paths, and never replanned the invalid Tasks into shard processing/output production. The run ended on an absolute/non-workspace-relative path protocol block without reading shard contents or creating reports.

### E2E-LH11 — range labels become literal paths

The five planned phase titles used pseudo-paths such as `artifacts/001-008.txt`. Action selection treated those labels as literal filesystem paths. Some recovery attempts switched to listing the real `artifacts/` directory, but Task postcondition adjudication rejected the listing as not being “one source file listing page”; continuation then repeated directory listing. No artifact contents, phase checkpoints, or summary were produced.

### E2E-H12 — first shard extrapolated to all shards

RWKV listed 15 shards but read only shard 01. It then wrote `item_count=2`, `value_total=2`, and first-shard category totals while setting `shard_count=15`. Task-to-Goal classification correctly recognized most totals as incomplete until the final read, where it incorrectly marked several as satisfied. Goal adjudication kept GC2/GC3 insufficient but falsely supported GC4/GC6/GC7, then malformed the recovery Task batch and blocked. The run avoided an FP only because at least one criterion remained unresolved.

### E2E-H13 — multi-action reads work, Task validation history does not

Round63 was genuinely exercised here. It read most four-document phases through successive actions and carried prior observations into later action-selection capsules. However, Task-postcondition validation saw only the newest action rather than the complete Task action history. It therefore reported already-read files as missing; that wrong reason was persisted into the next action context and caused duplicate reads. Some phases passed early, one wrote a literal placeholder `checkpoints/phaseNN.json`, and no valid phase checkpoint or final summary was produced. Goal-obligation replan then failed the canonical batch boundary.

## Cross-case architecture findings

### P0 — make Task execution a typed, model-owned contract

The five-field natural-language Task is too weak to constrain later action selection. Add a compact RWKV-declared execution contract at the Task boundary, at minimum:

- access mode: `read_only` or `mutating`;
- effect class: observe/create/update/copy/execute/verify;
- exact Task-local target set or an explicit bounded collection scope.

The Controller may mechanically enforce consistency between this model-owned contract and ActionDefinition capabilities. It must not derive the contract from benchmark text or choose a replacement action. This would prevent verification Tasks from overwriting correct artifacts and reject `read_file` as the committed effect for a copy Task without changing RWKV's answer.

### P0 — Task validation must consume the full Task-local action ledger

The action selector already receives prior observations for the current Task, but Task-postcondition validation does not consistently receive the same complete ledger. Use one append-only Task action capsule for both selection and validation: ordered action, target, result ref, content-complete flag, and the exact prior incomplete reason. This directly addresses H13's duplicate/missing-file confusion.

### P0 — stop unchanged successful-but-irrelevant action loops

When action fingerprint, workspace digest, Task-postcondition decision, and failure fingerprint are unchanged, a second identical continuation has added no evidence. Record stagnation and enter the existing RWKV failure/replan channel. Do not choose a new action and do not declare completion. This is protocol/state handling, not semantic answer correction.

### P0 — remove interface-induced partial observations

- `read_json(max_chars=N)` must not expand an N-byte source into a larger pretty representation and silently truncate it.
- Return compact lossless JSON when it fits the requested/source bound, or expose deterministic pagination with an explicit continuation cursor.
- A truncated structured value must never be presented as sufficient input for a transform Task.

### P1 — add minimal transparent format normalization

Normalize only pre-registered common shapes while preserving every semantic value and auditing raw/normalized payloads:

- flat `{action, ...arguments}` to `{name: action, arguments: {...}}`;
- known observation metadata accidentally copied into action arguments is separated, not interpreted;
- known persisted Task state fields may be projected back to the canonical five-field Task batch during replan;
- an incomplete outer JSON object must not fall back to a complete nested object.

Normalization must not repair paths, values, criteria, actions, Tasks, or answers.

### P1 — preserve partial criterion evidence instead of re-deciding it away

Maintain an append-only per-criterion working set of exact refs that RWKV labeled `advances` or `satisfies`. Final adjudication receives the complete working set plus current source revisions. A later call may change the relation only with a new observation or an explicit contradiction record; it must not silently turn a one-file observation into a complete collection.

### P1 — expose lossless transformation and bounded collection tools

Add normal agent actions that RWKV must explicitly choose:

- JSON field patch/update that preserves unspecified fields;
- bounded multi-file read returning a path-to-content mapping and per-file completeness metadata.

These tools do not calculate hidden answers or select files. They reduce whole-object rewrite loss and let weak models execute collection Tasks without encoding every file as a separate plan node.

## Round63 decision

Keep the multi-action Task state concept, but do not upload the current implementation. Its valid H13 behavior proves the missing state transition was real; LH02 proves the unrestricted form amplifies repeated and destructive actions. The next candidate must combine multi-action continuation with typed Task capability, full Task-local validation history, and unchanged-observation stagnation handling before another fixed canary.
