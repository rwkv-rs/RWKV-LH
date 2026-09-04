# Round65 preregistered protocol: direct RWKV actions and compact evidence

## Frozen baselines

- Uploaded Round46 full90: Strict `31/90`, External `32/90`, Agent `55/90`, FP `24`, FN `1`.
- Uploaded Round46 fixed 15: Strict `6/15`, External `7/15`, Agent `13/15`, FP `7`, FN `1`.
- Round64 fixed 15: Strict `1/15`, External `3/15`, Agent `1/15`, FP `0`, FN `2`.
- Round64 clean offline: LH-Control `30/30`; catalog/reference and 31-file parallel architecture regressions passed.

## Evidence-based hypothesis

Seven fixed-slice failures were directly blocked or trapped by the new Task action-class stage. The stage duplicates the concrete tool call, rejects common harmless field variants, and prevents later failure recovery from changing capability. Three externally correct or previously correct cases were then lost at the Goal boundary because direct workspace observations were presented as nested audit payloads and criterion decisions were committed only if every unresolved criterion passed in one batch.

## Preregistered structural changes

### 1. One RWKV action decision

- Delete the production Task action-class request, persisted Task class fields, Harness class filtering, temperature entry, and class-specific model prompts.
- Every action step exposes the registered Harness catalog and accepts exactly one RWKV-selected concrete action.
- Keep the immutable Attempt action record, full Task-local action ledger, deterministic action contract validation, and second-identical-action stagnation boundary.
- No Controller rule infers or substitutes a tool.

### 2. Small transparent action format layer

Register only common frozen-trace forms while preserving the raw and normalized payload plus digests:

- exact `action/arguments`, `tool/arguments`, `name/arguments`, and existing nested function-call envelopes;
- fixed spelling aliases `edit_file -> write_file` only for a full path/content call and `create_directory -> make_directory`;
- `reason`/`reasoning` and known observation metadata beside an otherwise complete call are separated as decorations;
- top-level `count` beside `replace_text.arguments` is moved into arguments only when there is no conflict;
- the exact `command + run_command=true + shell=false` envelope becomes `run_command(arguments=command)`;
- copied cursor/observation metadata beside a complete action is separated, never converted into a guessed cursor.

Unknown, conflicting, incomplete, multi-action, or copied state-capsule shapes remain rejected. The layer never changes paths, content, values, argument values, action order, or final output.

### 3. Goal size is descriptive, not a semantic filter

- Ask for a compact non-overlapping criterion set, but do not reject a valid enumerated request solely because it has more than 12 criteria.
- Increase the Goal response allowance so a 15+ item externally observable request can close its outer JSON object.
- Retain outer-object completeness and field validation.

### 4. Direct compact Goal evidence projection

- Present a post-action workspace snapshot as direct observed path/content/hash/size data, not as the serialized internal audit wrapper.
- Retain current/superseded revision labels and every exact source ref.
- Tell RWKV generically that preservation/equality criteria may require both a pre-change observation and a current observation; it must choose the refs itself.
- Remove duplicate preview fields from the model-facing source view while retaining full audit data in state/events.

### 5. Incremental RWKV-owned criterion commits

- Validate and persist each `supported` criterion binding immediately after that criterion-local RWKV call.
- If a later criterion is `insufficient`, keep the earlier RWKV-supported claims and replan only the genuinely unresolved criteria.
- Existing digest, scope, current-revision, and invalidation checks remain authoritative. A changed artifact still invalidates its affected claims.
- The Controller does not turn an insufficient result into supported or select any evidence ref.

### 6. Clear collection/copy action affordances

- Action selection receives generic guidance that range labels are not filesystem paths; exact paths must come from observed directory/file data.
- Existing workspace files must be copied with `copy_file`, not reconstructed from a filename.
- Verification Tasks should select observation/test actions; this is prompt guidance to RWKV, not a Controller capability filter.

## Explicitly retained quality structures

- One canonical internal Task/action/state schema.
- Append-only Attempt action and Task action ledger.
- Compact lossless paged `read_json`.
- Observation-driven planning and isolated parallel action proposal/execution.
- Second-identical successful-but-incomplete action stagnation boundary.
- Closed-frontier Goal evidence from real observations only.
- Raw RWKV final output delivered byte-for-byte without rewrite.

## Frozen validation and gate

- Full pytest, clean LH-Control `30/30`, catalog/reference integrity, and the 31-file parallel summarize/read architecture regression.
- Add regressions for removal of the class request, common frozen action formats, conflict rejection, snapshot unwrapping, 15+ Goal criteria, and incremental criterion persistence.
- Run the unchanged fixed 15 canary.
- Run full90 only if B01/B02/B10 are Strict, canary Strict is at least `6/15`, FP at most `3`, and FN at most `1`.
- Upload only if full90 Strict exceeds `31`, FP is at most `24`, FN is at most `1`, and all offline gates pass.

Efficiency, request count, and latency are recorded for audit but are not Round65 acceptance criteria. Quality and non-intervention take priority.
