# Round79 unified refactor and completion plan

Date: 2026-08-14

Status: implementation-ready plan. No phase may be marked complete without its
listed artifacts and gates.

## 1. Target outcome

Replace the current nine-role stateless prompt system with one G1i continuation
grammar over durable Goal, Task, chunk and reduce lanes. The first executable
transport is canonical prompt replay; native RWKV state is enabled only after
the server exposes and passes the same ModelSession contract.

This is one migration with temporary comparison paths, not a permanent second
agent layered over the old one. After equivalence and E2E gates, the old prompt
builders, request roles, semantic normalizers and narrative memory projections
are deleted.

## 2. Phase map

| Phase | Deliverable | Main files | Exit gate |
|---|---|---|---|
| 0. Freeze baseline | Exact prompt inventory, source/data hashes and fixed snapshots | `data/experiments/Round79_rwkv_state_redesign/`, `temp/` | Current input audit reproducible; snapshot manifest preregistered before generation |
| 1. Unify authoritative types | One action registry; Event, DecisionRecord, checkpoint, lane, chunk, result and repair schemas | `rwkv_lh/schema.py`, `rwkv_lh/harness.py`, `rwkv_lh/tool_protocol.py` | Declaration/execution parity for every action; serialization round trips; no dual schema |
| 2. Implement ModelSession | Prompt-replay transport plus native interface/capability gate | new `rwkv_lh/model_session.py`, `rwkv_lh/runtime/openai_compat.py`, `rwkv_lh/runtime/protocol.py`, settings | Byte-golden G1i transcript; candidate rollback; export/import; truthful transport reporting |
| 3. Canonical event renderer | One bootstrap and append renderer; remove request-specific prompt framing from new path | new `rwkv_lh/model_io.py`, `rwkv_lh/prompting.py`, `rwkv_lh/token_budget.py` | All new semantic calls use one dialect; exact token preflight; no silent drop/truncation |
| 4. Goal/Task loop | Coordinator and Task lanes using minimal control commands and Harness calls | `rwkv_lh/model.py`, `rwkv_lh/controller.py`, `rwkv_lh/task_graph.py`, `rwkv_lh/validation.py` | Plan/action/completion/failure/repair execute without the nine legacy roles; semantic authority tests pass |
| 5. Chunk and multi-concurrency | Token-sized descriptors, isolated worker forks, coverage ledger, stable merge/reduce tree | new `rwkv_lh/chunks.py`, `rwkv_lh/controller.py`, `rwkv_lh/harness.py`, schema | concurrency 1/N equivalence; zero gap/duplicate core coverage; crash reuse by digest |
| 6. State service | Server create/resume/fork/commit/rollback/export/import and client transport | server repository plus `rwkv_lh/runtime/openai_compat.py` | Capability probe and numerical state-resume gates pass; otherwise V2 remains blocked, not simulated |
| 7. Fixed ablation | V0 wide replay vs V1 unified replay vs V2 native state | experiment runner, frozen snapshots, Round79 records | Registered protocol-validity/agreement thresholds; no format resampling; immutable evaluator |
| 8. Full regression and removal | Same-class scan, short7, full90, faults; delete legacy path | repository-wide | No new FP; required Strict/External improvement; all project completion conditions and documentation satisfied |

The current work has completed Phase 0's input inventory and design artifacts,
but the fixed output-stability snapshot manifest is still required before Phase
0 can close. Phases 1–8 are not complete.

## 3. Detailed implementation order

### Phase 1: data and action authority

1. Add `LaneRef`, `CheckpointRef`, `ModelEvent`, `DecisionRecord`,
   `ChunkDescriptor`, `ChunkResult`, `ReduceNode` and explicit Task repair
   relation types to `rwkv_lh/schema.py`.
2. Make the Harness `ActionDefinition` the only source of action argument
   schema. Generate G1i JSON, validation, documentation and dispatch tests from
   it.
3. Audit the complete action registry, not only `write_json` and `read_json`.
   Record field-name/type/default/limit mismatches and fix them before any model
   ablation.
4. Add invariant tests for immutable Goal, append-only Attempt/result events,
   member/workset ownership and revision relationships.

### Phase 2: ModelSession and transactional generation

1. Add a transport-neutral `ModelSession`; move request audit and sampling
   binding out of request-role-specific functions.
2. Implement prompt replay as an exact canonical transcript, not a regenerated
   summary. Persist transcript digest, byte length and `static_replay_tokens`.
3. Make `generate` return candidate state. Parsing and deterministic contract
   validation occur before commit. On any failure, rollback and emit one
   failure record without a second sample.
4. Define the native transport now, but keep it disabled unless every capability
   probe passes. Do not emulate a state handle with a prompt cache.

### Phase 3: one input grammar

1. Implement the exact bootstrap/append bytes in `UNIFIED_MODEL_IO_SPEC.md`.
2. Build control definitions for Tasks, workset, completion, repair, chunk and
   reduce commands; use direct Harness tool calls for actions.
3. Replace `ContextBundle.projected()` in the new path with causally selected
   typed events. Required input that does not fit becomes a chunk/ref/error,
   never a silently dropped entry.
4. Add golden byte/token tests using the actual RWKV tokenizer. Test Unicode,
   JSON strings, empty arguments, 16k boundaries and stop suffixes.

### Phase 4: collapse request roles into lanes

1. Initial Goal coordinator emits `lh_tasks`; each ready Task forks a Task lane.
2. The Task lane chooses Harness actions, receives exact action/check events and
   emits the next action, workset delta, repair request or `lh_task_done`.
3. A failure is appended to the same Task lane. The next model command is the
   recovery decision; delete the independent failure-analysis and gap-selection
   semantics from the new path.
4. Accepted Task results return to the same Goal coordinator. The next command
   continues, repairs or finishes; delete the independent Goal-review semantics
   from the new path.
5. Final text generation forks the accepted Goal checkpoint and is unable to
   modify run state.

### Phase 5: chunk and concurrency completion

1. Replace character-first dispatch with tokenizer-based slicing while retaining
   exact byte/character ranges for reconstruction.
2. Register the full workset and all descriptors before workers start. Seal or
   cursor the set explicitly.
3. Fork independent worker lanes from one immutable parent. Execute only
   read-only or proven-disjoint domains concurrently.
4. Persist child results/artifacts and deterministic checks. Merge in stable
   source/range order; never merge hidden states.
5. When results exceed the reducer budget, build a deterministic token-bounded
   tree and persist its complete child-to-root provenance.
6. Block Task completion on open cursor/set, missing/duplicate range, pending
   member, worker failure, merge conflict or unbound reduce root.

### Phase 6: native recurrent state

The model server must expose authenticated operations with versioned capability
metadata. Required behaviors are create, append/resume, fork, candidate
generation, commit, rollback, export and import. State handles must be scoped,
immutable after fork and garbage-collected only after journal retention permits.

The client must record model/tokenizer/server build, state format version, parent
and child digests and numerical resume tolerance. Until all gates pass,
experiments report `prompt_replay`; V2 has no result.

## 4. Legacy replacement map

| Current component | New owner | Final action after gates |
|---|---|---|
| `_json_prompt`, `_json_prompt_with_context` | canonical G1i renderer | Delete |
| `task_decomposition` role | Goal coordinator `lh_tasks` | Delete role/schema |
| `task_step` six-field envelope | direct Harness/control call in Task lane | Delete envelope and semantic normalizers |
| `task_member_declaration` | Task-lane `lh_workset` delta | Delete role |
| `collection_member_action` | normal action call in same Task lane | Delete role |
| `failure_analysis` | next command after `failure_observed` | Delete role |
| `failure_recovery_gap_selection` | Goal/Task repair command | Delete role |
| `replan` role | `lh_reopen_task` / `lh_replace_task` in existing lane | Delete role |
| `goal_frontier_step` | Goal coordinator continuation | Delete reviewer prompt/schema |
| narrative `WorkingMemoryBuilder` projection | typed event selector plus content/chunk refs | Remove from semantic path; retain only compatibility diagnostics until deletion |
| final standalone prompt | fork of accepted Goal checkpoint | Replace |

Legacy code is kept only behind an experiment variant switch until V0/V1
comparisons finish. Production may select only one state machine per run; no
state or decision may cross between legacy and unified variants.

## 5. Test matrix

### Structural and contract

- all action declaration/execution pairs, including optional/default/boundary
  arguments;
- current candidate parser cannot see historical `committed_action` fields;
- single Task, nested model shape and Task batch normalize only at an explicit
  import boundary, never inside generation parsing;
- invalid/truncated output causes zero semantic resamples and exact state
  rollback;
- Task/Goal evidence binding uses visible checkpoint refs and raw observations.

### Chunk and concurrency

- ASCII, CJK, code, JSON, long line and tokenizer-expansion boundaries;
- exact byte/core coverage with overlaps excluded from completion credit;
- open cursors and late-discovered members;
- one-file, many-file, empty and changing worksets;
- concurrency 1/2/N equivalence and deterministic reduce-tree shape;
- child crash, reducer crash, partial side effect, conflict and resume.

### Semantic and E2E

- frozen transition snapshots with 10 repeats per variant;
- Round77 short7 and every repository case in the same causal classes;
- historical Round46 positive controls;
- M06 as a mandatory long-lived collection/chunk regression, not a special
  branch;
- fixed full90 with the registered evaluator, parameters and similarity method;
- FP/FN, earliest wrong transition, external state and model agreement reported
  separately.

## 6. Completion rules

A phase is not complete because code compiles or unit tests pass. It closes only
when its data inventory, source hash, command, raw output, metrics and conclusion
are recorded in `data/experiments/Round79_rwkv_state_redesign/`.

The redesign is complete only when:

1. all nine legacy semantic request roles have been removed from the accepted
   path;
2. native state is either genuinely implemented and validated or explicitly
   reported as unavailable without weakening the V1 result;
3. exact chunk/workset coverage and crash recovery pass;
4. the preregistered output-stability thresholds pass;
5. short7, all same-class cases, historical positives and full90 pass the fixed
   regression gates with no new false positive;
6. the project-level eight completion conditions in `AGENTS.md` all have
   reproducible evidence.

Until then, the truthful status is “architecture prepared / implementation or
validation incomplete,” not “real-world ready.”
