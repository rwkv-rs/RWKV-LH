# Round79 unified lane implementation log

Date: 2026-08-14

Status: local architecture implementation complete; final preregistered r8 canary failed the acceptance gate, so full90 was not run and the architecture is not yet release-ready.

## Scope implemented

- Replaced all semantic model calls with one G1i continuation in `model_io.py`; the single wire object is `{function, params}` and JSON-internal indentation is preserved.
- Added transactional prompt-replay `ModelSession` with bootstrap, append, fork, generate, commit, rollback, export and import. Native transport remains capability-gated because the deployed endpoint does not expose a verified recurrent-state API.
- Persisted independent Goal, Task, chunk, reduce and final checkpoint heads in `long-horizon.run.v12`.
- Deleted the old role prompt/normalizer modules: `memory.py`, `prompting.py`, `temp_policy.py` and `tool_protocol.py`; deleted their role-specific tests.
- Replaced planner/reviewer/failure/member/replan entry points with the next command on the original Goal or Task lane.
- Added runtime-owned workset status and explicit `lh_reopen_task` / `lh_replace_task` repair relations.
- Bound `lh_goal_done` to the union of exact evidence from every current active completed Task revision. Reopened/superseded revisions are excluded.
- Made `ActionDefinition` the single declaration/default/validation/execution registry. Removed the old `read_files` interface.
- Replaced character cursors with tokenizer-bounded `start_byte + max_tokens` reads carrying exact UTF-8 byte ranges, source/chunk hashes and continuation cursors.
- Added `lh_chunk_map`: all chunk lanes fork one committed Task checkpoint, generation is concurrent, and the runtime merges only explicit `lh_chunk_result` payloads. Stable reduce lanes consume only explicit child results.
- Format failures rollback and block with zero semantic resampling.
- Removed the free-text decoder exception; Final also emits one canonical `lh_final_answer(text)` G1i call from the accepted Goal checkpoint.

## Local fixed regression

Input audit after lane scoping:

- Final r8 B01 Goal bootstrap: 759 RWKV tokens; definitions are Goal frontier/repair/completion controls only. The checkpoint binds `E-GOAL-START`.
- Final r8 B01 Task selection bootstrap: 456 RWKV tokens. A minimal local selection fixture is 337 tokens; its `write_file` binding checkpoint is 596 tokens.
- Goal and Task bootstrap independently. Chunk workers fork the one committed Task checkpoint; Final forks the checkpoint that committed `lh_goal_done`.

These counts are fixture evidence, not a fixed production constant; every real request is preflighted with the deployed tokenizer.

Command:

```bash
uv run pytest -s -q
```

Result after unified rejection, duplicate-failure suppression and compact tool scoping: **71 passed**.
The narrower `rwkv-lh-control` gate records **35 passed** in
`LOCAL_REGRESSION.json`.

After r4 exposed cross-schema pollution, Task input was narrowed without adding
a role: the same Task lane commits `lh_select_operation`, then receives only
the selected ActionDefinition for one params-binding continuation. A selection
cannot be changed during binding. After eliminating duplicated definitions,
empty fixture inputs are 337 tokens for selection and 596 tokens for
`write_file` binding.

Current covered combinations include:

- exact ModelSession transcript, fork isolation, rollback and export/import;
- strict candidate-only parsing and lane command scoping;
- ActionDefinition schema/default/execution parity;
- tokenizer byte coverage, UTF-8 cursors and deterministic reduce packing;
- Goal → Task → Harness → checks → Task commit → Goal evidence → final;
- malformed initial Goal output with one call and no resampling;
- sealed two-file workset with member-by-member verification;
- concurrent multi-chunk fork parent identity and explicit-only merge;
- evidence accumulation over multiple Goal frontiers;
- false completion reopened as Task revision 2 with revision-1 evidence invalidated.

The local suite is an architecture regression only. It does not satisfy the project completion gate until the frozen canary/full90, boundary/exception/history regressions and preregistered similarity metrics pass.

## Remaining acceptance work

1. Design and preregister a general lane rollover/compaction protocol. Compact tool scopes delayed overflow, but r8 B02/M03 still reached 15,979/15,341 input tokens; no evidence was silently dropped.
2. Improve base-model operation-selection stability on a separate fixed dataset. r8 sometimes skipped `lh_select_operation` or emitted an unknown enum value; these candidates correctly failed closed.
3. Re-run a newly registered broad canary only after those general changes. Do not tune further on short7.
4. Run full90 and large-code-31 only after the new canary gate passes.
5. Probe the deployed server for a real recurrent-state API. Do not enable `NativeRWKVModelSession` without create/resume/fork/commit/rollback/export/import evidence.
