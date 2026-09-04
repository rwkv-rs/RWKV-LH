# Round64 preregistered protocol: single-owner semantics and bounded Task execution

## Frozen baselines

- Uploaded Round46 full90: Strict `31/90`, External `32/90`, Agent `55/90`, FP `24`, FN `1`.
- The fixed 15-case slice of uploaded Round46: Strict `6/15`, External `7/15`, Agent `13/15`, FP `7`, FN `1`.
- Round63 fixed canary: Strict `2/15`, External `3/15`, Agent `4/15`, FP `2`, FN `1`.

## Evidence-based hypothesis

Round63 manual analysis found that the post-Task all-criterion classifier duplicated Goal adjudication and frequently contradicted it. In LH02 it produced 306 Task/criterion relation calls, while the actual execution defect was a verification Task selecting a mutating action. M06/M18 show later Goal calls overturning earlier correct insufficiency without new evidence. B10/M03/B24 show independent model-boundary and read-interface failures.

## Preregistered structural changes

### 1. One semantic owner per layer

- Task postcondition adjudication decides only whether the active Task is complete.
- Remove the post-completion `Task × every Goal criterion` classification path from runtime execution.
- Goal criteria are adjudicated only from the complete closed-frontier provenance catalog.
- No Controller rule assigns a Task to a criterion or declares Goal evidence.

### 2. RWKV-owned Task action class

- Before a Task's first concrete action, RWKV commits exactly one local action class: `observe`, `mutate`, `copy`, `execute`, or `mixed`.
- The Controller records the raw decision and mechanically exposes only compatible registered actions.
- The Controller does not infer the class from title, path, benchmark identity, hidden acceptance, or content.
- A later action outside the RWKV-selected class is a protocol failure; the Controller does not substitute an action.

### 3. One append-only Task action ledger

- Action selection and Task-postcondition adjudication receive the same ordered Task-local ledger.
- Each entry contains only persisted action name, arguments, result ref, observed target/path, completeness metadata, and observed content.
- Prior Task observations are never replaced by the newest action.

### 4. Unchanged-observation stagnation boundary

- If a successful-but-Task-incomplete continuation repeats the same action fingerprint under the same workspace digest and same RWKV incomplete-decision fingerprint, it has added no evidence.
- On the second identical state, stop normal continuation and enter the existing RWKV failure/replan channel.
- Do not choose a replacement action, rollback or alter an artifact, declare the Task complete, or change RWKV output.
- Retain the absolute 32-successful-action cap for non-identical progress.

### 5. Lossless model boundary and structured reads

- `read_json` returns compact lossless JSON when the source fits the requested/source byte bound; pretty-print expansion may not cause silent truncation.
- Truncated structured reads expose deterministic completeness/cursor metadata and may not be treated as a complete source observation.
- Register only common transparent action formats observed in frozen traces: flat `{action,...arguments}`, known observation metadata copied beside/inside an action call, and `write_json` copies of fixed `overwrite=true/create_parents=true` controls.
- Register common Task-batch envelopes that contain all five semantic Task fields. Known persisted state-only fields may be projected away; no Task field or value may be invented.
- JSON extraction must not recover a nested object from an incomplete outer object.

### 6. Bounded Goal proposal

- Request the smallest non-overlapping externally verifiable criterion set, with an explicit maximum of 12.
- A truncated/malformed Goal object receives one compact correction request; nested criterion fragments are never accepted as the Goal.

## Non-cheating boundary

- All semantic classes, actions, arguments, Tasks, criteria, evidence refs, and final output remain RWKV decisions.
- The Controller may validate equality, membership in a fixed protocol enum, action-definition compatibility, digests, and unchanged state.
- It may not infer the right action from text, filter candidate answers by acceptance, synthesize missing values, rewrite RWKV's final output, or restore an artifact to a preferred value.

## Frozen validation and gate

- Full pytest, LH-Control `30/30`, catalog `90/90`, and 31-file parallel architecture regression.
- Add regressions for read-only Task action exposure, mixed Task multi-action execution, exact Task ledger history, unchanged-action stagnation, compact JSON reads, registered format conversions, and incomplete-outer-JSON rejection.
- Run the unchanged fixed 15 canary.
- Run full90 only if B01/B02/B10 are Strict, canary Strict is at least `6/15`, FP at most `3`, and FN at most `1`.
- Upload only if full90 Strict exceeds `31`, FP is at most `24`, FN is at most `1`, and all offline gates pass.
