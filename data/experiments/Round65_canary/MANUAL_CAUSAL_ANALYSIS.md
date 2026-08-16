# Round65 fixed-15 manual backward causal analysis

## Frozen outcome

- Strict E2E: `3/15` (`B01`, `B02`, `B10`)
- External acceptance: `5/15` (`B01`, `B02`, `B10`, `M03`, `M12`)
- Agent completed: `5/15`
- FP: `2` (`M01`, `M06`)
- FN: `2` (`M03`, `M12`)
- Offline: pytest `395/395`, LH-Control `30/30`, catalog/reference plus 31-file parallel architecture regression `4/4`.

Round65 improved the three basic producer/coding controls and removed the seven direct action-class blocks seen in Round64. It still failed the preregistered `6/15`, FP<=3, FN<=1 canary gate, so full90 was not run and this candidate is not upload-eligible.

## Case-by-case backward trace

### B01, B02, B10 — direct action architecture positive controls

All three are Strict passes. B10 is the important delta: after observing the real test failure, RWKV's full-file edit reached `write_file`, the implementation became correct, tests passed, and Goal evidence completed. This validates deletion of the Task action-class gate and the common edit/action envelope conversion.

### M01 — no pre-change reads, whole-object replacement, unsupported preservation claim

1. The plan listed `services/` but did not read any service JSON content.
2. Three parallel `write_json` calls replaced the complete objects with only `name`, `version`, and `runtime.channel`, deleting `port`, `threads`, and `theme`.
3. Task postconditions mentioned only the changed fields, so each passed.
4. Goal GC1 nevertheless claimed unrelated settings were preserved even though the catalog contained no pre-change file contents. The Agent completed and external verification exposed the loss.

The first error is selecting a whole-object replacement without source content or a preserving JSON update primitive. The FP is amplified by Goal evidence claiming a preservation comparison from post-state-only evidence.

### M03 — exact migration, clear before/after sources, direct model misread

The workspace is exact. The compact catalog showed the original source with `tags` on both records and the current source with the same `id/tags`. RWKV nevertheless stated that the original had no tags and marked GC3 insufficient. Incremental commits correctly retained GC1 and GC2, but the recovery Task-batch response copied persisted state fields and blocked.

The model-facing data is now factually correct. Remaining defects are attention over repeated source representations and an unreliable free-JSON recovery boundary.

### M06 — read is still mistaken for copy; manifest is still mistaken for files

1. T1 correctly read `selection.txt`.
2. Copy Task T2 selected another `read_file(selection.txt)`. Task adjudication falsely said a successful read established that files were copied.
3. RWKV wrote a manifest with two identical invented digests and never created `package/alpha.dat` or `package/gamma.dat`.
4. Verification Tasks again read selection/manifest rather than listing or reading package files.
5. Goal adjudication first correctly found insufficient evidence, then after another identical selection read claimed the manifest proved the package contained exactly the selected files.

This is a genuine tool/effect selection error plus two semantic false positives. The source catalog already says a manifest proves only itself; a weaker model needs clearer action-effect descriptions and a less repetitive evidence view, not Controller completion rules.

### LH02 — 15 checkpoints correct; Goal proposal invented a final field

RWKV read the real early requirements, wrote all 15 correct checkpoints, wrote the five constraints plus `generated_by`, and verified the artifacts. The final config also contained `step:15`, which external acceptance correctly rejects. The first harmful event was Goal parsing: it changed “final config preserves constraints and adds generated_by” into a criterion requiring a step number in the final config. The action faithfully implemented that invented immutable criterion. Later Goal evidence also missed an existing step11 source and attempted to plan step16+, then blocked at the recovery boundary.

This proves the user request must remain the authoritative Goal text. A model-produced criterion may group user clauses but must not add fields or operations.

### LH05 — requested outputs are planned as pre-existing inputs

The model correctly listed real shard and fallback directories and read the rules. It then planned reads of nonexistent `value_total.txt` and `reports/shard_summary.json`. Failure recovery continued reading those paths; a later write of an empty summary used a still-unregistered top-level-control form and would not have been semantically correct anyway. No shard contents were processed.

The planning prompt exposes the initial manifest, but the model still treats requested outputs as files to inspect. The prompt and recovery interface need an explicit absent-path rule: absent requested outputs require producer work, not speculative reads.

### LH11 — directory pagination works, content processing still does not

Round65 correctly paged the real `artifacts/` directory through files 1-24. The plan incorrectly called listings “inspected”, read only artifact 17, then reset the final pagination cursor. Goal GC1 falsely claimed checkpoint files existed from artifact listings, while GC10 correctly found no checkpoints. Incremental evidence preserved the false GC1 but did not complete the Goal. Recovery copied the large Goal capsule instead of returning a Task batch.

The improvement is real path/pagination handling. The remaining earliest error is conflating directory metadata with file contents; the final block is the free-JSON recovery protocol.

### B24 — source preservation fixed; RWKV's transform remains wrong

The accepted common action envelope prevented the Round64 correction from mutating `log.txt`, so source preservation now passes. RWKV repeatedly wrote a lexicographically sorted but still duplicated output. Task adjudication falsely called it deduplicated; Goal adjudication eventually detected insufficiency, then recovery copied a capsule and blocked.

This is now primarily a model transform/judgment error, not a format error. It should remain a failure until RWKV produces the correct bytes.

### M12 — code and tests correct; repeated sources cause wrong Goal identity/value claims

RWKV repaired both functions and repeatedly ran passing tests. The external workspace is correct. Initial Goal adjudication treated the superseded original implementation as decisive. After recovery, GC1/GC2 were retained incrementally, but GC3 called a `test_math_utils.py` read “the current math_utils.py” and hallucinated that the median implementation returned 4. The raw catalog identifies the action path correctly; the model confused repeated same-digest reads, current code snapshots, and several test runs.

The failure supports deterministic temporal/digest compaction: keep original and current revisions plus one representative of identical observations, with all alias refs recorded. It does not support Controller selection of a winning source or answer.

### M16 — Task description and postcondition disagree

T1 listed the root and satisfied its exact postcondition (“one workspace listing page”). Its description also said the listing would discover file contents. Task adjudication expanded the completion boundary from the postcondition to the description, returned replan twice, and failure analysis emitted a non-Task replan object that blocked. The later primary/fallback reader and producer Tasks never ran.

The persisted postcondition must be the exact Task completion boundary; title/description may not add requirements after that boundary is observed.

### M18 — useful recovery blocked by remaining call decorations

RWKV recursively listed the real files and read `inputs/a.txt`. It then tried to read the not-yet-created output, correctly diagnosed the absent precondition, and proposed creating `digest_map.json`. The proposed `write_json` used top-level fixed `overwrite/create_parents` controls and was rejected twice. The value was only `{}`, so accepting the format would not itself make the task correct, but the representation block is still a generic defect.

### H12 — multi-action ledger reaches 11 shards, then loses counting fidelity

T2 sequentially read shard01 through shard11 using the real append-only Task action flow. As the ledger exceeded its projection budget, older detail was minimized; one later Task judgment said only one shard had been read. At shard11 it incorrectly declared all 15 loaded. The aggregator then used only the latest shard totals while writing `shard_count=15`.

The earliest architecture amplification is loss of collection membership/count in the compact ledger. A bounded explicit multi-file read action would preserve all selected paths and contents in one observation and is also required by the 31-file project acceptance target.

### H13 — class block removed; observation decoration and list/content confusion remain

The run now listed all 24 corpus files several times and reached a correct `read_file(corpus/doc_24.txt)` proposal. That proposal carried an `artifacts` observation decoration and was rejected; later calls copied `tool_success`, `workspace_digest`, `tool_id`, or `truncated`, causing more boundary failures. No document batches or checkpoints were completed.

The format layer should separate this closed set of observed runtime decorations. More importantly, repeated listings cannot replace bounded file-content reads.

## Cross-case conclusions

1. **Direct concrete actions are the right base.** Removing the class gate turned all three basic controls into Strict passes and allowed long tasks to execute real reads.
2. **The next read bottleneck is collection fidelity.** H12 proves sequential multi-action progress, while its compact ledger loses exact membership. LH11/H13 prove listings alone are not contents.
3. **Goal quality has two independent problems.** LH02 shows the proposal can invent a requirement; M03/M12 show the adjudicator can misread repeated but correct sources.
4. **Free-JSON Goal recovery is a dominant final blocker.** M03, M12, B24, and LH11 copy state/capsule objects instead of producing the required five-field Task batch.
5. **FP prevention must remain semantic and RWKV-owned.** M01/M06 must not be declared correct. The architecture may expose preserving tools, explicit effects, direct paths, and compact evidence; it may not rewrite artifacts or override RWKV's final decision.
