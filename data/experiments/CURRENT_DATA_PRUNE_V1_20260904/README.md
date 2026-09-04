# Current Data Prune V1

## Registration

- Date: 2026-09-04 (Asia/Shanghai)
- Purpose: remove obsolete dataset copies and bulky raw outputs from retired
  architectures while preserving the current `rwkv-stateful-goal-loop.v4`
  datasets, artifacts, preregistrations, results, and curated regression
  evidence.
- Recovery branch:
  `chase/data-archive-pre-v4-prune-20260904`
- Recovery commit:
  `29a1e308658b92f979191c4b02fa3e1f274a6b73`
- Cleanup execution HEAD subsequently advanced independently to
  `4d31f894592c9d50b34c941a82c123357048f1a9`; the archived data remains
  reachable from the recovery branch.
- StateTune: not generated, modified, selected, or deleted.

## Removed scope

The scoped cleanup selected 116 directories containing 2,986 tracked files
and 434,107,216 bytes before removal:

1. Four datasets with no references from current source, tests, scripts, or
   benchmarks:
   - `data/datasets/rwkv_g1i_online_tool_dialog_v1`
   - `data/datasets/rwkv_g1i_tool_prompt_v1`
   - `data/datasets/rwkv_lh_e2e_v1`
   - `data/datasets/rwkv_lh_large_code_31_v1`
2. Direct child run-output directories under `Round0` through `Round49`.
   Round-level protocols, results, reports, causal analyses, and source
   manifests at the experiment root were retained.
3. Direct child raw-run directories under
   `data/experiments/rwkv_lh_architecture_ablation_v1`.
   Root-level comparison and architecture-analysis files were retained.
4. `data/experiments/engine_diagnostics/goal_concurrency_20260813_rerun1`.
5. Two Git-ignored verifier-private/workspace artifact directories under the
   already recorded `full_chain_gpt56_rerun_twice` runs, totaling 592,899
   bytes.
6. Seventy empty dataset directories left behind when their tracked README
   stubs were removed by the prior architecture cleanup.

The cleanup did not select any path under the current
`RWKV_LH_G1J_SELECTOR_HEAD_V2_20260904` experiment, any 2026-09-04 Executor
input-contract evidence, or the curated Round119-Round132 evidence.

## Rationale and dependency audit

- `rwkv_lh_e2e_v1` was a historical G1i evaluation copy. Four catalogs were
  byte-identical to files under `benchmarks/`; its `lh_control_30` file was
  stale at schema v1 while the authoritative benchmark is schema v2.
- The two G1i prompt datasets only supported retired protocol comparisons.
- `rwkv_lh_large_code_31_v1` was a frozen source snapshot from commit
  `fef3a3b3`, not a current runtime or regression input.
- A repository search excluding `data/` found zero references to all four
  removed dataset IDs.
- Current runtime/verification dependencies were retained, including
  `rwkv_e2e_90_v1`, `rwkv_lh_g1j_selector_persistent_head_v2`, the native
  `search_text` fixtures, and the deployed Selector Head artifact.

## Validation

- Scoped target validation: 116/116 targets resolved below `data/`; zero
  current-v4 experiment targets selected.
- `git diff --cached --check`: passed.
- Full `pytest` was attempted but collection was blocked because the current
  development environment does not have the optional `torch` dependency.
  The three blocked modules were:
  - `tests/test_network_exact_tool_selector_service.py`
  - `tests/test_persistent_vllm_rwkv_state_injection.py`
  - `tests/test_vllm_rwkv_state_profiles_v1.py`
- All remaining tests: `533 passed in 42.12s`.
- `uv run rwkv-lh-e2e --suite all --validate-only`:
  `RWKV-E2E-90`, 90/90 catalog entries valid.
- Post-cleanup `data/` size: 107,777,916 bytes at the validation point.

## Recovery

Removed tracked evidence can be inspected or restored from
`chase/data-archive-pre-v4-prune-20260904`. Git-ignored verifier-private and
workspace artifacts were intentionally deleted and are not present on that
branch.
