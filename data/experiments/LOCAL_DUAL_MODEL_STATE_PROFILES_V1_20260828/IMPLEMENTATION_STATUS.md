# Local Dual-Model State Profiles v1 — implementation status

> 2026-08-29 更新：本文是 V1 历史快照，其中“没有真实 Selector/产品 handoff”等结论已经
> 被 S39–S50 实现与验收取代。当前 25 类 Selector、23 个可执行工具、联网状态和 V2
> state-tuning 计划以 `docs/CURRENT_STATUS.zh-CN.md`、`docs/CURRENT_HANDOFF.zh-CN.md` 和
> `data/experiments/LOCAL_DUAL_MODEL_STATE_ABLATION_V2_20260829/PROTOCOL.md` 为准。V1 原始
> 预注册不改写，以保留实验历史。

## Recorded identity

- Date: 2026-08-28 (Asia/Shanghai)
- RWKV-LH workspace: `/home/chase/GitHub/RWKV-LH`
- Local engine workspace: `/home/chase/GitHub/vllm-rwkv`
- Engine base commit: `67f0c5996c50dca0ad779da545cb491527de988f`
- Current uncommitted engine diff SHA-256: `81faf0f7d45de58c6d733231e0f6d66909f491d58394d01a57c0c909bf79c42e`
- Protocol SHA-256: `7bcae7a20fd7ef3eb81db476c8e5b4f85a9af100a56d9d85ecf489e4489b2520`
- 2.9B base bytes: `5896273469`
- 2.9B base SHA-256: `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`
- 13.3B base SHA-256: `5d97772ba04a81bdaeba90e1d6d306c70560bf4f784522be61cdcade69e30562`

The RWKV-LH worktree already contained extensive unrelated user changes and experiment artifacts before this implementation. They were preserved. The engine worktree was clean at the recorded base commit before the three files below were modified.

## Implemented

### Local vllm-rwkv

- Added an immutable startup manifest for multiple RWKV-PEFT `time_state` profiles.
- Manifest and every profile require explicit SHA-256 pins.
- Model artifact/revision, exact layer keys, BF16 dtype, finite/non-zero values, shape, PP layer range and TP head range are checked before serving.
- A request selects only a registered profile ID and matching SHA through `vllm_xargs`; file paths cannot enter through the request.
- Selection and digest verification occur before a recurrent state row is allocated.
- The service default is forced to `zero`; tuned profiles cannot be applied silently.
- State rows initialize from the selected profile while shift state and elapsed remain zero.
- Request ownership records the selected profile.
- Recurrent prefix-cache identity now includes profile ID and profile SHA, preventing cross-profile reuse.

Changed engine files:

- `vllm/envs.py`
- `vllm/v1/worker/gpu/model_states/rwkv.py`
- `tests/model_executor/models/test_rwkv7.py`

### RWKV-LH

- Added application-side state profile ID/SHA configuration and sends both values to vllm-rwkv.
- Enabled token-ID return by default for environment-loaded local deployment settings; direct dataclass construction remains backward compatible.
- Added explicit `selector` and `executor` lane heads while retaining old action-lane snapshot compatibility.
- Model checkpoints retain state profile identity.
- Every candidate exposes an immutable `rwkv-lh.raw-generation.v1` record with raw text, UTF-8 SHA-256/byte count, raw token IDs, finish reason, response/model identity, sampling and state-profile identity.
- Non-string output and invalid token IDs are rejected instead of coerced or rewritten.
- Accepted and rejected model events both retain the raw generation record.
- Added a frozen 20-class exact-tool Selector input contract. It exposes only task/stage facts, compact causal progress, and tool names/descriptions; parameter schemas, arguments, results, and Executor reasoning are excluded.
- Split Selector rendering into one lane bootstrap plus ordered causal step appends so training can reproduce persistent run-local recurrent state instead of reloading the profile per row.
- Added a fail-closed candidate dataset builder with controller/Harness/verifier provenance, immutable raw-output bytes/SHA, family split, class-conditional 5-gram deduplication, retained cross-label state-boundary contrasts, and complete unfiltered trajectories.
- Added a separate stateful Selector client contract. It carries only Selector bootstrap/step bytes, validates the pinned 2.9B model/head/profile identities, advances an opaque Selector state ref/digest, and materializes a `ModelLaneKind.SELECTOR` checkpoint independent of the 13.3B Executor checkpoint.
- Added immutable `rwkv-lh.exact-tool-selector-output.v1` raw records containing all 20 logits, fixed class order, logits SHA, selected argmax, confidence, model/head/profile identity and state checkpoint identity. This path produces no generated tool-call text.
- Added atomic `exact_tool_selection_committed` / `exact_tool_selection_consumed` causal records. An unconsumed selection survives recovery and cannot be silently replaced; the handoff binds Selector state, Executor parent, both base/profile identities, tool-definition digest, menu digest and input projection digest.
- Added a deterministic exact-tool coverage fixture generator. It makes no model calls, emits no training rows, preselects all family splits before inference, validates every ordinary action against the live Harness schema, and fails if the registered class-local similarity audit would remove any fixture family.

## Selector dataset candidate inventory

- Dataset path: `data/datasets/rwkv_lh_exact_tool_selector_v1`
- Dataset manifest SHA-256: `a2d78fcefecabdbe4a9638fc2112580e9d69994053f40ef307c11cc33f0c9a38`
- Coverage SHA-256: `522cdfa3a9a82fee5f2613c315381f4fe826a23853f1ce2f8e191c381ce4b9fa`
- Status: `candidate_unfrozen`; `training_authorized=false`; no train/dev/test files emitted.
- Strict atom-graph and pre-ensemble direct-action rows are handled by separate fail-closed source adapters. Direct rows require an exact request/decision/raw-generation/action join, reject order-ensemble selection, and require `controller_semantic_fields_generated=false`.
- Auditable rows before dedup: 1772; after class-conditional dedup: 1002 across 49 unique task families.
- Retained cross-label near neighbors: 557; these are causal progress boundaries, not duplicates.
- Recovered nonzero coverage for `bind_evidence`, `remove_line`, and `run_command` without remapping legacy labels.
- Current labels with zero rows: `ABSTAIN`, `append_file`, `delete_file`, `move_file`, `search_text`.
- Fixed test minimum is 30 per class. Current test counts fail this gate for every class; the builder's `--freeze` mode was verified to refuse output.

## Frozen coverage collection plan

- Plan path: `data/datasets/rwkv_lh_exact_tool_coverage_v1`
- Manifest SHA-256: `81fab68dd3668d28c7d4e752d202a13d90f4582a3ed21c8df1837f614eee2e01`
- Cases SHA-256: `665705b6fe24f415bae2383128968786c128364ae6ef46562b53bd06534f1cd8`
- Generator SHA-256: `342886d2bebc225d7da4be6fbe0b80c7447135d2d75248daad0b0298a7df00e8`
- Protocol SHA-256: `60803518b448d0a165371a4c69161aa825c7494756a42af0e94b5336a2b15103`
- 6000 fixture families are fixed: each of the 20 classes has train/dev/test = 240/30/30; all 6000 family IDs and Selector projections are unique.
- 5400 ordinary operation contracts pass the current Harness schema. The remaining 600 are 300 completed `final_answer` boundaries plus 300 mechanical `ABSTAIN` boundaries; `ABSTAIN` does not fabricate an Executor request or raw output.
- Registered `utf8-byte-5gram-cosine.v1` at threshold `0.95` retains 6000/6000. The maximum same-label similarity is `0.908844765343`.
- This artifact is a frozen collection plan only. `model_calls=0`, `raw_rwkv_outputs=0`, `training_rows=0`; it has not been inserted into the existing candidate pool.

## Remote Selector inventory

- Read-only inventory: `data/experiments/LOCAL_DUAL_MODEL_STATE_PROFILES_V1_20260828/REMOTE_SELECTOR_INVENTORY_20260828.json`.
- Server `rwkv-260304` contains the frozen G1i 2.9B base at the expected 5,896,273,469 bytes and SHA-256 `ac1ae23d0e65c1d35ba523eacd81a2a4dacb7b886479909bbff34f312e766320`.
- No compatible 2.9B exact-20-class MLP head, Selector state, or profile manifest was found.
- The active 2.9B service was occupied by an unrelated ReproBench run and was neither used nor modified.
- The server's old seven-operation selector dataset and Round71 `web_search` replan datasets were rejected as formal exact-tool sources. In particular, `web_search` was not relabeled as the local `search_text` operation.
- No remote file or service was changed, and no RWKV output was modified, removed, repaired, ranked, or replaced.
- Fresh coverage collection is preregistered in `SELECTOR_COVERAGE_COLLECTION_V1.md`: its 6000-case fixture plan is now frozen, while the 40-case contract preflight, one-tool 13.3B execution and formal collection have not started. Mechanical `ABSTAIN` explicitly has no fabricated output.

## Verification completed

- vllm-rwkv targeted formatting/lint:
  - `ruff-check`: passed
  - `ruff-format`: passed
- vllm-rwkv complete RWKV7 model suite:
  - `175 passed`, `14` upstream Torch deprecation warnings, `39.28s`
- RWKV-LH focused runtime/session/controller/router suite after final changes:
  - `99 passed`, `18.15s`
- RWKV-LH full suite before the final strict token-ID validation addition:
  - `397 passed`, `77.74s`
- `compileall` and `git diff --check`: passed
- Exact-tool Selector protocol/dataset/coverage-plan/stateful-client/atomic-handoff tests: `18 passed`.
- Exact-tool focused Ruff check: passed.
- Existing state/controller/session/runtime focused regression after the new handoff projection: `98 passed`.

## Not implemented / not claimed

- No 2.9B exact-tool selector state, MLP head or training-authorized frozen exact-tool dataset exists yet. The current candidate inventory is intentionally blocked by coverage gates.
- The preregistered coverage fixture generator has run and frozen the collection plan, but the runner, 40-case preflight and 6000-case model collection have not run. No fixture placeholder was inserted into the candidate or training pools.
- No Hidden-vs-WKV selector feature ablation has run.
- No real Selector service or Selector→Executor `selection_id` handoff has been enabled in the product path. The fail-closed client and durable handoff contract exist, but no fake head/profile is substituted.
- No durable recurrent create/resume/fork/commit/rollback/export/import server API exists yet; current OpenAI serving remains prompt replay.
- No real-model single-profile parity, mixed-profile concurrency, canary, Full90 or performance sweep has run.
- The modified engine has not been committed, copied into the managed runtime, deployed, or used to restart any service.
- Therefore the dual-model architecture is not marked complete or production-ready.

## Final full-suite result

- Earlier profile/raw-output foundation checkpoint: `398 passed`, `77.41s`.
- Current complete suite after exact-tool data, stateful client and atomic handoff additions: `413 passed`, `49.25s`.
- Current suite after the strict pre-ensemble direct-action source adapter and remote inventory: `414 passed`, `82.65s` (pytest capture disabled because the WSL temporary capture file disappeared during the first invocation; the complete no-capture rerun passed).
- Current suite after freezing and validating the 6000-family coverage collection plan: `416 passed`, `78.81s` (pytest capture disabled).
