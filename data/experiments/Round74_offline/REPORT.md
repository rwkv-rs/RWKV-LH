# Round74 offline validation report

## Result

- Complete pytest: `447/447` passed.
- LH-Control deterministic architecture suite: `30/30` passed.
- Frozen E2E catalogs/reference plus 31-file controller fan-out/read/summary/aggregation fixture: `5/5` passed.
- Python compileall and `git diff --check`: passed.

The 31-file fixture proves that the single-agent controller can enumerate all files, dispatch bounded read/summary frontiers, preserve full observations outside compact capsules, and aggregate only after every file-local result exists. It does **not** prove that the live RWKV model can independently produce trustworthy per-file summaries or a whole-repository architecture analysis; that remains a separate real-model acceptance run.

## Round74-specific coverage

- Goal creation has one `goal_commit` semantic boundary. Invalid JSON/schema may retry, but there is no draft/audit/final resampling chain.
- Initial planning has one `task_decomposition` semantic boundary. The prompt contains the compact registered action effect catalog, including the `read_files` batch contract, and there is no plan audit.
- Action selection and fixed-argument commitment each receive one authoritative action-state packet. No extra live frontier or historical execution-capsule copy is appended.
- The current Task's complete observation appears once in evidence. Its ordered ledger retains causal identity, status, fingerprint, outcome, Task decision and workspace digest, but does not duplicate observation content, metadata or artifacts.
- Each valid action observation reaches one `task_postcondition_commit` semantic boundary; the controller does not draft or revise the RWKV completion decision.
- Regression tests explicitly preserve semantically poor but structurally valid RWKV Goal/Task decisions, proving that removal of review stages did not become controller-side semantic correction.

## Non-intervention audit

- RWKV still authors every Goal semantic field, Task, action name, action argument, Task pass/open decision, evidence selection and final answer.
- The format boundary only maps registered common representations to the one internal contract and records raw/normalized payloads. It does not add a Task, criterion, argument value, action choice or answer text.
- Full current observations are retained for model reasoning and append-only audit. Prompt deduplication removes repeated projections rather than hiding facts.
- Hidden acceptance and frozen Codex reference answers are not exposed to the model or controller.
- Final output intervention guarantees from the existing suite remain passing.

## Dataset record

- Source/version: Round74 repository tests; frozen E2E-90 catalogs/reference; versioned 31-file architecture fixture; LH-Control-30.
- Purpose: validate a single semantic spine and unique action-state projection before live RWKV canaries.
- Generation: full pytest; fresh `data/experiments/Round74_offline/lh_control_30`; frozen five-test subset; compileall; diff check.
- LH-Control result SHA-256: `8ab0e2f803da81005d2553d79f2103a56fbe680fb7ff2b7683e0ca9e2cfd3062`.

