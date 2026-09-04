# Round67 fixed-15 manual causal analysis

## Outcome

- Strict E2E: `3/15`.
- External acceptance: `5/15`.
- Agent completion: `4/15`.
- False positives: `1` (`E2E-M06`).
- False negatives: `2` (`E2E-M03`, `E2E-M12`).

This misses the preregistered canary gate of Strict >= `6/15`, FP <= `3`,
FN <= `1`, with B01/B02/B10 Strict. The three controls passed, but aggregate
Strict and FN did not. Full90 is therefore not run and this working tree is not
uploaded.

## Case-by-case causal chain

### E2E-B01 — Strict pass

RWKV preserved the exact greeting contract, used `write_file`, read the result
back, and supported the Goal criteria with current evidence. This remains the
positive control for a short, direct write/read task.

### E2E-B02 — Strict pass

RWKV read the real input, derived the requested values, wrote the correct report,
and verified it. Goal, Task, action, effect checks, criterion evidence and final
state remained aligned.

### E2E-B10 — Strict pass with a false evidence rejection

The implementation and real tests were correct. On the first Goal evidence pass,
however, RWKV claimed a passing test had failed and caused duplicate rewrite/test
Tasks. A later pass recognized the same test evidence and completed. The final
result is correct, but this control proves that current evidence interpretation
can hallucinate even when the artifact and verifier are both unambiguous.

### E2E-M01 — lost unrelated fields, then incomplete recovery

RWKV read all service files, but selected full-value `write_json` for the web and
worker objects while omitting `theme` and `threads`. Because `write_json` replaces
the whole object, those unrelated fields were deleted; only the API object kept
its unrelated `port`. The summary itself was correct.

A later verification Task read only the summary. Failure replan successfully used
the new fixed `propose_task_batch` boundary, and a later Task read the now-current
files, but its semantic commit did not detect the already-lost fields. A final
action used a common call-plus-execution-metadata envelope that the closed format
normalizer still rejected. The first harmful event is the destructive tool choice;
the semantic commit and remaining format gap amplify it. A generic safety boundary
should distinguish creating/replacing a JSON file from preserving updates rather
than silently allowing omissions to delete existing object fields.

### E2E-M03 — external pass, agent blocked (false negative)

RWKV migrated `users.json` correctly. The Goal was split into eight redundant
criteria. Criterion GC3 first treated the original pre-migration read as current
authority and rejected a complete current read despite the recorded revision
chain. After repeated producer work it supported GC3, but GC4 then refused to
combine original and current observations to judge the requested `fullname` to
`display_name` derivation.

The fixed bare-arguments recovery form worked earlier in the run. Later recovery
responses copied persisted Task records and exceeded the four-Task contract, so
the boundary correctly rejected them. The root failure is RWKV's before/after
evidence interpretation; repeated correct production and terminal recovery width
are downstream effects.

### E2E-M06 — agent pass, external fail (false positive)

The inspection Task read `selection.txt` but its Task commit falsely claimed that
the selected source files had been established. During copying, RWKV read both
sources but wrote only `package/alpha.dat`; `gamma.dat` was never copied. It then
wrote a manifest and treated that manifest as proof of package contents. Goal
evidence repeated the same substitution and marked every criterion supported.

`copy_file` was registered, but RWKV never selected it. The first harmful event is
an action/effect mismatch; the decisive architecture defect is that Task and Goal
semantic commits can cite prose or a manifest as proof of a filesystem effect
without binding the decision to an observation that actually contains the target.

### E2E-LH02 — an invented Goal schema propagated to the artifact

All 15 checkpoint files were correct and the event-count requirement passed.
During Goal construction, RWKV invented a requirement that `final/config.json`
contain `step` plus a nested `constraints` object. The user instead required the
early constraint fields preserved at top level plus `generated_by`. RWKV then
faithfully wrote its incorrect Goal schema, so external acceptance failed.

Later verification repeatedly read only the first checkpoint and eventually
produced malformed output. Strict structural Goal validation cannot catch a
well-typed but invented semantic requirement. The first harmful event is an
unreviewed Goal interpretation, and every later layer consistently amplifies it.

### E2E-LH05 — batch observation aborted and the model guessed the aggregate

The initial plan was speculative. A `read_files` call selected all 20 primary
paths, but the tool aborted the whole call at the first missing file instead of
returning the successful and failed observations per path. RWKV then tried 19
paths, still missed the actual invalid/missing primaries and required fallback
replacements, and its Task commit nevertheless claimed all shards were covered.

RWKV wrote an early wrong summary (`primary=18`, `recovered=2`, `value=420`) with
wrong source/hash structure and never created `REPORT.md`. Recovery then focused
on nonexistent fallback paths. The first infrastructure amplifier is all-or-
nothing batch reading; the semantic roots are speculative discovery and an
ungrounded Task commit. Batch observation should expose per-selected-path success,
missing, invalid-text and exact digest facts without deciding what they mean.

### E2E-LH11 — invented paths and repeated the same failed action

The initial plan invented `artifacts/001-008`-style paths before listing the real
`artifacts/` directory. The action selector called `list_directory` on the same
nonexistent path three times. Failure analysis stated that the path did not exist
and still recommended the identical path. No checkpoints or final artifact were
created.

The failure starts at causal discovery: a phase label was converted into a path
without observation. The full action catalog and one-pass action choice did not
focus this model on the required first operation, and recovery did not make its
own diagnosis constrain its next selection.

### E2E-B24 — malformed semantics passed strict types, then a predecessor became irreparable

The Goal objective copied the system instruction about normalizing a long-running
task, and its constraints copied prompt text. The criteria happened to describe
the requested transform, so strict type/field validation accepted the object.

A producer Task whose postcondition required `sorted.log` selected `read_file` on
the source. Task commit declared pass even though no output effect occurred. The
next verifier repeatedly read the missing target. Failure analysis recognized
that the producer had failed, but selected the current verifier again; the graph
had no explicit operation for reopening and repairing the falsely completed
predecessor. The chain is semantic Goal corruption, ungrounded Task commit, then
recovery topology that cannot repair the origin of the dependency failure.

### E2E-M12 — external pass, agent blocked (false negative)

RWKV repaired the implementation correctly and the real tests passed. Two
dependency-independent Tasks selected writes to the same target from isolated
state snapshots. Durable Harness execution was serialized, so this run did not
contain simultaneous writes, but the second proposal was made without seeing the
first proposal/effect and could have overwritten it with conflicting content.

Goal evidence then hallucinated that current `safe_divide` returned `b/a` although
the current source was `a/b`, creating four unnecessary recovery Tasks. A later
verification command called `safe_divide(10, 0)` without catching the expected
`ValueError`, guaranteeing exit code 1. Failure analysis hallucinated a median
type problem and repeated the same bad check. `execution_capsule` normalization
worked here. The root is current-source misreading plus weak self-test design;
same-target scheduling and repeated-action recovery are structural risk
amplifiers.

### E2E-M16 — strict Goal rejection exposed runaway criterion generation

No run was created. The first Goal proposal expanded the simple ids 01-05 request
into dozens of duplicated criteria until output truncation. The correction did
the same. The strict parser correctly refused to manufacture or truncate a Goal,
but the architecture had no quality recovery beyond asking for the same full
object again. This needs a focused RWKV Goal audit/revision sequence, not schema
coercion or controller-selected criteria.

### E2E-M18 — invented files survived its own failure diagnosis

The first Task required discovering real inputs, but the action selector chose
`read_files` for invented `input/file1.txt` through `file3.txt` instead of listing
the directory. It repeated the same nonexistent paths three times even after
failure analysis explicitly said to inspect the actual workspace. No output was
written. This shares the LH11 root: one-pass action selection is not causally
grounded in observed paths, and failure prose is not bound to the next action.

### E2E-H12 — all source data was visible, but RWKV performed a wrong mental aggregate

RWKV listed and read all 15 shards. The producer action prompt contained the full
source data, including values 1-15 and the shared record. RWKV nevertheless chose
`write_file` and mentally produced `item_count=150`, `value_total=1050`, category
totals of 105, and the wrong key `categories_total`. The correct totals were not
computed by a command or other observable transformation, and Task commit passed
the wrong artifact.

Recovery first proposed eight Tasks and was correctly rejected by the four-Task
contract. Its correction invented shard16-19 despite the immutable Goal and
history both showing exactly 15 shards, then read missing shard16. The first
semantic failure is choosing unsupported mental computation instead of an
executable computation; unfocused gap recovery then extends a completed input
range.

### E2E-H13 — a useful prefix was observed, then recovery could not express the next frontier

RWKV correctly listed 24 documents and read docs01-04. It did not create the
phase01 checkpoint. Goal evidence correctly reported checkpoints absent.
Recovery then proposed docs05-09 as five Tasks, violating the registered maximum
of four; its correction again returned five persisted Tasks and was rejected.

The maximum exposed an over-wide response but did not improve the model's next
decision. The chain begins with failing to convert the first four observations
into their checkpoint, followed by gap selection that ignores the four-item
frontier and cannot correct itself.

## Cross-case causal structure

The recurring failure is not one tool or one benchmark feature. It is a chain in
which an early model mistake becomes accepted state and later prompts treat that
state as fact:

1. **Goal semantic grounding is missing.** Strict syntax catches wrong types but
   not prompt copying (B24), invented schemas (LH02), redundant expansion
   (M03/M06), or runaway criteria (M16).
2. **Discovery is not a required causal frontier.** The planner/action selector
   turns phase labels into paths or invents filenames before observing the
   workspace (LH05/LH11/M18).
3. **Task completion is not bound to direct evidence/effects.** A read can be
   declared to prove a write/copy, and a manifest can be declared to prove target
   contents (B24/M06/LH05/H12).
4. **Current and historical evidence are not reliably distinguished by RWKV.**
   Complete current sources are read as stale, truncated, or containing old code
   (B10/M03/M12).
5. **Recovery starts from the amplified state instead of rechecking the first bad
   transition.** It repeats the failed verifier, invents the next range, or cannot
   repair a falsely completed predecessor (B24/H12/H13).
6. **Observation and scheduling still expose avoidable structural hazards.**
   `read_files` loses partial facts on one missing path (LH05), same-target writes
   may run concurrently (M12), and one common execution-metadata envelope remains
   outside the closed normalizer (M01).

## Quality-first direction

Efficiency, request count and latency are audit data only for the next round.
The architecture should spend additional RWKV passes where they can stop an
incorrect state transition:

- draft Goal, then ask RWKV to audit it only against the immutable original
  request, then let RWKV issue the final full Goal;
- let RWKV select one action name from a compact effect catalog, then expose only
  that tool's argument schema, and let RWKV audit the complete proposed call
  against observed paths and the active Task before execution;
- require Task commits to select existing action/effect/evidence references and
  run a focused RWKV postcondition review; controller code validates reference
  existence and integrity but never changes pass/replan;
- return per-path records from multi-file observations so one missing file does
  not erase successful observations;
- before recovery Task generation, ask RWKV to identify one earliest unresolved
  obligation or invalid predecessor, then generate only the next executable
  frontier for that RWKV-selected gap;
- prevent concurrent execution of actions whose declared effect targets overlap,
  as a generic serialization property rather than a semantic choice;
- remove controller rules that replace a valid RWKV recovery decision with a
  different semantic decision. Safety may reject an unsafe retry, but it must ask
  RWKV to decide again rather than substitute controller intent.

Every accepted Goal field, Task, action, path, value, evidence judgment, recovery
gap and final answer remains RWKV-generated. The controller may preserve raw
state, validate closed protocols, expose exact observations, enforce scope and
serialize conflicting effects; it may not rank, repair, truncate, merge, or
reinterpret RWKV's semantic output.
