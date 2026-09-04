# Round72 offline validation report

## Result

- Complete pytest: `447/447` passed.
- LH-Control deterministic architecture suite: `30/30` passed.
- Frozen E2E catalogs/reference plus 31-file parallel summarize/read regression: `5/5` passed.
- Python compileall and `git diff --check`: passed.

## Round72-specific coverage

- Protocol normalizer is `transparent-protocol-boundary.v11`.
- A uniquely fixed tool accepts equal duplicate identity fields, identity plus only declared inline arguments, and the fixed `review_action` scalar-decision form. Conflicting identity, missing required fields and unknown inline fields remain rejected.
- `continuation_cursor` and `observation_ref` are separated only as closed string/null observation decorations.
- `read_text` is a closed action-name representation of `read_file`; the selected path and all arguments remain RWKV output and unchanged.
- Task commit registers the current Attempt ID and its persisted Artifact IDs together with ACTION/CHECK/Memory refs. Historical and unknown refs are not generated or accepted.
- Task commit draft is historical input to the final reviewer. The current Task, current action result, current effect checks and complete registered-ref list are repeated after the bounded history at the response boundary.
- Action selection and argument commitment repeat the current Task and fixed catalog/action after historical context and prior review text.
- Goal audit starts at 3200 output tokens and retries at 2600 rather than decreasing to the Round71 truncating 900/700 limits.
- Initial and obligation Task batches accept 9 and 32 immediately-ready Tasks; 33 remains rejected by the shared 32-Task batch bound.

## Non-intervention audit

- The controller does not choose or rank an action, evidence ref, Task decision, Goal field or final answer.
- Every normalization is a closed representation conversion with raw/normalized payloads, digests and transformation names.
- The live frontier repeats persisted state; it does not add expected values, missing Tasks, criteria, action arguments or answers.
- No external model, hidden-state classifier, Router, free-text summary fact source, hidden acceptance or Codex reference answer was used during generation.

## Dataset record

- Source/version: Round72 repository tests; frozen E2E-90 catalogs/reference; 31-file architecture fixture; LH-Control-30.
- Purpose: validate the unified fixed interface, one evidence registry, live-frontier ordering, Goal audit quality capacity and 32-Task structural capacity before live fixed15.
- Generation: full pytest; fresh `data/experiments/Round72_offline/lh_control_30`; frozen five-test subset; compileall; diff check.
- LH-Control result SHA-256: `8472b4ceb0d1e4010f12f6a64a485c794efa63efe2bfb544119ff88ada208324`.
- External design sources and fixed commits are recorded separately in `data/experiments/Round72_REFERENCE_ANALYSIS.md`; no upstream code was copied.
