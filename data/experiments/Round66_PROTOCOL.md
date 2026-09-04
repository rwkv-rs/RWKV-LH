# Round66 preregistered protocol: collection reads, preserving updates, and constrained recovery

## Frozen baselines

- Uploaded Round46 full90: Strict `31/90`, External `32/90`, Agent `55/90`, FP `24`, FN `1`.
- Uploaded Round46 fixed 15: Strict `6/15`, External `7/15`, Agent `13/15`, FP `7`, FN `1`.
- Round65 fixed 15: Strict `3/15`, External `5/15`, Agent `5/15`, FP `2`, FN `2`.
- Round65 offline: pytest `395/395`, LH-Control `30/30`, catalog/reference and 31-file parallel architecture regression `4/4`.

## Preregistered structural changes

### 1. Normal tools for real collection and preserving work

- Add `read_files(paths, max_chars_per_file, max_total_chars)` for an explicit RWKV-selected path list. It returns every selected path with content, digest, per-file completeness, and observed artifacts; it never discovers or selects files itself.
- Add `patch_json(path, updates)` using explicit top-level key updates supplied by RWKV. Unspecified fields are preserved; nested objects are replaced only when RWKV supplies that key. It does not infer values or hidden expected output.
- Tool descriptions state their real effects: list/read actions never create, copy, or modify; `copy_file` is the exact-byte duplication action; `write_json` replaces a whole JSON value; `patch_json` preserves unspecified top-level fields.

### 2. Preserve collection membership in Task state

- The Task ledger retains every attempted action name and exact selected path(s), even when older content/reason detail is compacted.
- Collection Tasks should prefer one explicit `read_files` observation when all exact paths are already visible.
- No Controller count is used to declare the Task complete; RWKV still judges the Task postcondition from the lossless membership ledger.

### 3. Postcondition is the exact Task boundary

- Task adjudication must not add requirements from title/description after the persisted postcondition is established.
- A read/list action cannot be described as creating/copying/modifying or as observing file contents that it did not return.
- Planning guidance forbids reading a requested output absent from the initial/current manifest; producer work or a later frontier is required.

### 4. Deterministic evidence compaction, not evidence selection

- In the model-facing Goal view, identical observations of the same workspace digest are represented once with `equivalent_observation_refs`.
- Preserve the oldest observed revision and current revision of each path, all non-equivalent revisions, successful command observations, and all raw records in audit/state.
- Add deterministic same-path revision chains. No source is ranked by criterion text, expected value, or hidden acceptance.

### 5. G1i-constrained Task-batch recovery

- `goal_obligation_replan` uses one fixed G1i function schema whose only semantic payload is the existing five-field Task array.
- The boundary adds only the fixed Task-batch schema tag; it never creates a Task or Task field.
- Initial planning remains unchanged for the first experiment so the recovery interface can be isolated.

### 6. Goal proposal remains grounded in the user request

- Strengthen grouping: one criterion per requested outcome/artifact group, not separate criteria for its fields, counts, ordering, existence, and verification views.
- Every criterion must state only requirements present in the immutable user request. In particular, a field required in checkpoint files may not be propagated to a final file unless the user also requires it there.
- No hard criterion-count cap is restored.

### 7. Complete the common decoration boundary

- Separate the frozen observed fields `artifacts`, `task_id`, `attempt_id`, `execution_id`, `tool_id`, `tool_success`, and `workspace_digest` only when an otherwise complete single action exists.
- Separate list/read observation fields such as `truncated` and `next_cursor`; lift top-level fixed write controls only by the registered tool's exact representation rule.
- Unknown, conflicting, state-capsule, incomplete, or multi-action forms remain rejected.

## Non-intervention boundary

RWKV still chooses every Task, exact path list, JSON update, copy source/destination, action, criterion decision, evidence ref, and final answer. The Controller/Harness may execute the selected primitive, preserve unspecified JSON fields by that primitive's documented semantics, validate schema/scope, and compact identical observations. It may not calculate benchmark answers, select files from a directory, infer a desired field/value, override a model decision, or rewrite final output.

## Frozen validation and gate

- Full pytest, clean LH-Control `30/30`, catalog/reference integrity, and 31-file parallel read/summarize architecture regression.
- Add tests for multi-file exact reads and limits, JSON patch preservation, collection membership surviving ledger compaction, postcondition precedence, deterministic evidence dedupe/revision chains, G1i Task-batch recovery, and all added format conversions/conflicts.
- Run the unchanged fixed 15 canary.
- Run full90 only at Strict >=`6/15`, FP <=`3`, FN <=`1`, with B01/B02/B10 Strict.
- Upload only if full90 Strict >`31/90`, FP <=`24`, FN <=`1`, and all offline gates pass.

Latency and request count are audit-only. No Round66 decision is based on efficiency.
