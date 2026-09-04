# Round70 fixed15 manual causal analysis

## Outcome

- Strict E2E: `1/15`; External: `1/15`; Agent completion: `1/15`.
- `E2E-B01` completed and passed external acceptance. Round68 and Round69 were
  both `0/15`, so the fixed review tools removed the global review-schema
  barrier, but the preregistered `6/15` canary gate was not reached.
- No full90 run and no upload are authorized by this result.

This analysis was performed by reading each case audit, request trace, exact raw
RWKV output, event tail and state/task record. The causal ledger was used only
to locate source records; it did not infer causes.

## Case-by-case earliest error and amplification

### E2E-B01 — strict pass

The Goal retained the exact filename/content/newline, `write_file` created the
artifact, `read_file` verified it, and the final RWKV output was delivered byte
unchanged. A redundant third verification Task was added during obligation
recovery, showing avoidable state expansion, but it did not change correctness.

### E2E-B02 — correct write repeatedly rejected by stale action review

T1 correctly read `input.txt`. On T2 RWKV first selected a read, rejected it,
then twice produced the exact correct `write_json(report.json,
{"project":"Orion","doubled_count":14})`. The review pass nevertheless called
the proposal a read-only action and later claimed it overwrote `input.txt`.
The proposed call occurs before a long execution capsule in the review prompt;
the weak model answered from stale nearby state rather than the exact call. The
three-round review budget then converted one bad review into a blocked run.

### E2E-B10 — contradictory evidence namespaces, then common wrapper drift

T1 correctly read both source and test files. T2 correctly observed that
`slug.py` still raised `NotImplementedError`; however, the Task draft falsely
called that an implementation and selected `T2-A1-R1`. That ref is visibly
present in CURRENT CAUSAL STATE but absent from AVAILABLE EVIDENCE, so protocol
validation rejected all three drafts. Recovery created T4. Its selected
`read_file` was emitted with a common flat action envelope and later
`review_action` was emitted as a tool-name-keyed object; the boundary rejected
the latter. Conflicting visible ref namespaces and split wire formats amplified
one semantic Task error into terminal protocol failure.

### E2E-B24 — task-local read rejected because future Goal work leaked back in

T1 listed the workspace and T2 repeatedly selected the exact `read_file(log.txt)`
needed for postcondition “File contents are observed.” All three review outputs
explicitly admitted the read satisfied that postcondition, but still returned
`revise` because later deduplication/sorting/writing remained. The action review
prompt states the Task is the boundary, yet the exact call is far before the
large Goal/capsule, so future work dominated the decision and blocked the run.

### E2E-M01 — optional safe arguments treated as causal defects

The first Task correctly selected `list_directory(services, recursive=true,
max_entries=1024)`. Review rejected it three times because recursion and a bound
were “not required,” even though they are safe and directly establish the
requested recursive JSON inventory. This is review over-constraint, not an
execution or tool-contract error; the review gate amplified it into zero
attempts for the entire case.

### E2E-M03 — Goal invention plus continuation-format collapse

The Goal invented “replace spaces with underscores” for `display_name`, which
the request never required. T1/T2 correctly listed and read `users.json`. T3
correctly read the old structure and its Task draft correctly said migration
was still open. On the next action selection, prior recovery prose dominated
the fixed selection contract: RWKV emitted `read_json` calls and
`select_action` as semantic action names instead of one selection call. The
three format failures blocked the continuation before any write. Even without
that block, the invented underscore transformation would have produced an
incorrect artifact.

### E2E-M06 — unregistered semantic action invented at the first Task

The final Goal omitted “do not copy unlisted files” and verification, and
promoted a generic caller constraint into an outcome. The first action selector
then returned invented names `read_selection_txt` / `read_selection` on all
three attempts instead of registered `read_file`. This is a genuine RWKV tool
grounding failure. The compact catalog did not keep the fixed allowed name set
near enough to the response boundary.

### E2E-M12 — selection stage mixes name and arguments, then falls into noop

T1/T2 correctly read source and tests. For the repair Task, RWKV repeatedly
returned a correct `read_file` selection plus premature `arguments`; the exact
two-field selector rejected it. It then selected `noop`, which review correctly
rejected, and finally returned to `read_file` while review hallucinated the
already observed path was missing. The split selection/argument protocol and a
model-visible `noop` escape consumed every semantic round before a write could
be proposed.

### E2E-M16 — non-pass evidence rule selects the wrong answer

The plan grouped all five primary reads and fallback reads into broad Tasks.
After reading only `primary/item_01.json`, RWKV first correctly returned that
the Task was incomplete. The protocol required `evidence_refs=[]` for every
non-pass decision, rejected the grounded non-pass with refs, then accepted a
later `pass` saying completion only “for the first file.” The same happened for
one of two fallback files. This is a direct architecture-induced false
completion: the empty-ref rule filters the semantic decision. T3 later hit
common `type+arguments` envelopes that the selected-tool boundary rejected.

### E2E-M18 — invalid initial dependency poisons recovery

Planning placed “Read digest_map.json” before any Task creates it. That read
failed as expected. Later action selection was filled with recovery/state-machine
terms such as `reselect_action` and claims that T1 should have generated the
map, although T1 only listed inputs. The initial plan lacked a RWKV audit for
producer-before-consumer and observable effects; subsequent recovery preserved
the false dependency and amplified it into unregistered action names.

### E2E-LH02 — exact correct checkpoint payload forgotten by review

T1 read all five immutable constraints. For T2 the final committed call was
`write_json(checkpoints/step01.json)` with `step:1` and the exact constraints.
Review nevertheless said the value omitted the step number. The call is correct
in the raw trace; the review decision is inconsistent with its own input and is
another recency/layout failure. Earlier attempts also show common flat inline
arguments (`path` and `value` at the call top level) being rejected before the
canonical call was reached.

### E2E-LH05 — audit repetition truncates and bypasses retry

The draft Goal was complete enough to continue. Goal audit then repeated claims
about invented “exact schemas” until `finish_reason=length`, producing no outer
JSON close. `_request_goal_audit` invokes/parses outside its retry `try` block,
so the first malformed response escaped immediately; only two total model
requests occurred. A retryable model-format failure therefore became
`not_created`.

### E2E-LH11 — pagination arguments and review evidence disagree

T1 observed only the first eight directory entries, despite its broad
postcondition claiming a list of 40. T2 prepared a valid eight-file read but did
not execute before independent T4 blocked. T4 repeatedly used a file path as the
directory `path`; review responses alternated between “valid, approve” while
returning `revise`, and “missing start_after” when it was visibly present. The
long review capsule lost exact arguments, and one blocked materialization
starved another ready read, magnifying the failure.

### E2E-H12 — runaway Goal expansion and no parse retry

The model began with the four required aggregate fields, then recursively
expanded redundant formatting/value criteria far beyond the stated 24-item
limit until `finish_reason=length`. `_request_goal_proposal` also invokes/parses
outside its retry `try` block, so no second attempt was made. One retryable
over-expansion caused `not_created` after one request.

### E2E-H13 — valid larger recovery frontier rejected by efficiency cap

The initial plan covered listing plus only the first four documents. Those five
Tasks completed. Goal evidence correctly found the checkpoint/summary criterion
unmet, and recovery repeatedly proposed a continuation batch larger than four
Tasks. The controller rejected all three solely due
`recovery task batch exceeds 4 tasks`. With efficiency explicitly out of scope,
this cap prevents the model from expressing the remaining six phases and is the
terminal cause.

## Cross-stage causal chain

1. **Goal boundary:** meta-instruction copying, ungrounded additions and runaway
   criteria enter immutable state (`B02/B24/M03/M06/H12`).
2. **Planning boundary:** broad multi-member Tasks or consumer-before-producer
   dependencies turn a reasonable first action into an impossible one-call
   postcondition (`M16/M18/LH11`).
3. **Action boundary:** allowed names/call arguments are far from the response
   end, and two common fixed-tool envelopes are rejected (`B10/M03/M12/LH02`).
4. **Review boundary:** exact proposed calls precede long state capsules, so
   review answers from stale Goal/history and rejects correct current calls
   (`B02/B24/M01/LH02/LH11`).
5. **Task evidence boundary:** duplicate ref namespaces contradict each other,
   while the empty-ref non-pass rule pressures RWKV to change a correct open
   judgment into pass (`B10/M16`).
6. **Recovery boundary:** prior recovery prose leaks into action names and the
   four-Task cap prevents complete continuation (`M03/M18/H13`).

## Next structural changes justified by the traces

1. Put a compact, exact decision packet (active postcondition, proposed call,
   tool effect) after the bounded context in action review; the model must see
   the current object immediately before its response.
2. Replace Task `replan` wording with `open` for a successful action that has not
   established the postcondition. Permit grounded evidence refs for both pass
   and open; never require an empty list based on the answer.
3. Expose one selectable evidence namespace. Remove/selectively project
   non-selectable artifact refs from the Task decision capsule.
4. Register only the two repeatedly observed fixed-tool wire forms: a fixed tool
   name as the sole object key, and a fixed selected tool name plus inline
   declared arguments. Preserve raw/normalized payloads and reject conflicts.
5. Move Goal proposal/audit invocations inside their retry loops; make audit
   output concise and retry truncation without recovering missing semantics.
6. Add an independent RWKV plan audit/final pass for producer-before-consumer,
   observed-path grounding, task granularity and complete Goal coverage.
7. Remove the model-visible `noop` escape for unmet Tasks and raise recovery
   batch/frontier limits to the existing global Task safety bound.
8. Continue executable ready Tasks when a different independent Task fails
   action materialization; retain the failure but do not discard useful
   observations.

All changes are global protocol/state fixes. None selects a correct answer,
adds task-specific data, reads hidden acceptance, or rewrites RWKV output.
