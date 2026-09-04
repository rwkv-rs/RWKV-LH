# Round104 manual causal analysis

## Fixed result

- Strict E2E: `0/3`; Agent completed: `0/3`; external acceptance: `0/3`.
- Every terminal response was non-empty and byte-identical to raw RWKV output.
- The failures therefore concern task execution and completion quality, not answer suppression.

## E2E-H08

1. **First deviation — Goal planning.** RWKV combined reading `events.txt`, producing
   `ledger.json`, and idempotency verification into one Task, but declared
   `file_content_read` evidence for `ledger.json`. The evidence class described an
   intermediate/read observation rather than the required final mutation.
2. **Correct observation.** `T1-A1` returned all 30 source bytes, including all five
   event lines, with `complete=true`, `eof=true`, and `source_size_bytes=30`.
3. **Model error after observation.** RWKV requested `start_byte=30`, received a valid
   empty exact-EOF observation, then requested `start_byte=60`, which was outside the
   source. It never proposed `write_json`.
4. **Architecture amplification.** The unchanged-action gate returned the Task to the
   Goal lane, but every `lh_replace_task` repeated the same Task structure. Fourteen
   replacements reset Task-local recovery state, producing 15 Tasks and 134 requests.
5. **Terminal result.** No `ledger.json` existed. The non-empty Final correctly reported
   a blocked run, but could not satisfy the task.

Root cause ownership: the first wrong Task/evidence choice and read-after-EOF decisions
were RWKV outputs; accepting structurally identical replacements without a shared
supersede-chain budget was a controller/graph defect.

## E2E-LH07

1. **First deviation — incomplete discovery frontier.** RWKV created per-file read Tasks
   for the services plus rule/verifier reads, but no mutation, report, or command
   verification Task. It also invented `services/service-09.json`, although the request
   says eight services and the workspace contains `service-01` through `service-08`.
2. **Partial progress.** Only the reads for service 01, service 02, and
   `migration_rules.md` committed. No service JSON file was mutated.
3. **Architecture amplification.** When a read Task stalled, RWKV replacement batches
   restated the failed Task and several already-active later reads. The replacement
   transaction superseded only the first proposed Task but appended every remaining
   duplicate, expanding the graph from 10 to 54 Tasks.
4. **Protocol degradation.** As the Goal lane accumulated repeated graph projections,
   outputs increasingly copied displayed state objects instead of the registered call
   shape. Recovery calls consumed 230 requests without reaching mutation work.
5. **Terminal result.** All eight migrations, the report, and the verifier failed.
   Final remained non-empty, but its text described Final-call recovery rather than a
   useful workspace outcome.

Root cause ownership: the incomplete frontier, invented ninth service, and lack of
mutation plan were RWKV errors; allowing a replacement batch to duplicate active Tasks
and reset recovery state was an architecture defect that magnified them.

## E2E-H13

1. **Planning defect.** Each phase Task combined four reads and one checkpoint write but
   declared `file_content_read` evidence for the output checkpoint instead of final
   workspace-mutation evidence.
2. **Correct source observations.** For phase 1, RWKV observed all four files. In
   particular, `doc_02.txt` returned `PRIORITY: yes` and `signal-02`.
3. **First semantic deviation.** RWKV nevertheless wrote
   `{"phase": 1, "priority_filenames": []}`. This wrong empty list came directly from
   RWKV; no converter or controller changed the value.
4. **Premature completion.** After reading the just-written checkpoint, RWKV selected
   `lh_task_done`. Structural evidence checks established only that the file was readable;
   they could not establish that the natural-language value was correct. The Task was
   committed and the bad checkpoint became an authoritative dependency.
5. **Amplification in phase 2.** RWKV read only part of phase 2 and repeatedly wrote the
   same empty-list checkpoint. Replacement batches duplicated the existing summary Task
   and rewired dependencies inconsistently, after which the run blocked.
6. **Terminal result.** Two wrong checkpoints existed; four checkpoints and the final
   summary were missing. Final was non-empty and accurately reported partial progress.

Root cause ownership: the wrong empty lists are RWKV semantic errors. Evidence-type
mismatch, structural-only completion readiness, and duplicate replacement transactions
made the errors look more committed and prevented productive recovery. The controller
must not repair the list values itself.

## Cross-case remediation derived from the chains

1. Make Task evidence describe the final `done_when` outcome, not an intermediate read.
2. Expose EOF as an explicit transition boundary: no continuation at or beyond the
   displayed source size.
3. Reject exact no-progress replacements after deterministic unchanged loops.
4. Reject replacement batches that restate any currently active Task.
5. Carry a bounded recovery budget across the immutable supersede chain.
6. Require a non-empty RWKV Final for every terminal status, while keeping completion
   status and Final text separate and never rewriting either into success.

These changes control state/protocol quality only. They do not infer service migrations,
priority filenames, ledger values, tool arguments, or final answers for RWKV.
