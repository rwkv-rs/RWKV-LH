# Round85 full E2E-90 direct Task-call preregistration

## Purpose

Run the complete fixed RWKV-E2E-90 suite after restoring the semantics-free
call-envelope normalizer and replacing the two-generation
`lh_select_operation -> operation_selected -> selected operation` handshake with
one atomic direct registered Task call.

This run measures the entire current architecture. It does not assume the
selector fix solved completion, repetition, parameter-contract, action-selection,
recovery, timeout, or final-output problems.

## Frozen architecture and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- Dirty worktree is the architecture under test and must not change during execution.
- Complete local regression: `80 passed in 10.30s`.
- `rwkv_lh/model.py`: `06347065a962d5f3719da6d36a109b4892110e97aeaaaa57ce7ffd01bbd65a7a`
- `rwkv_lh/model_io.py`: `852b0220040445b5755d9f84e0fa0c4ef7583a06cef63bb6e6b0981f2c98ad4c`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- `rwkv_lh/controller.py`: `f9568916aeb6764ab4fe16d9ca9c6f99170783ab44be89bf4ca7a7a5f0620465`
- `rwkv_lh/harness.py`: `e3f217d0ef94f1d5ef3d5dd8d7b4cfa426bf44a563c7a2bbb39a2863907b86a8`
- Runner: `62cdfc9d3f21d2b075cbca367db9b6016b79ac144b52784d0019dee6361622c7`
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786755252`
- Forward service: active/running, `NRestarts=1`.

## Frozen dataset, evaluation and parameters

- Suite: fixed 90 cases: 30 basic, 30 medium, 30 hard.
- Maximum transitions per case: `200`.
- Case concurrency: `8`, identical to Round81.
- Sampling: fixed lane sampling, temperature `0.05`, semantic resampling `0`.
- Visible task and hidden-acceptance digests are unchanged from Round81.
- Codex reference digest:
  `947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`;
  runtime visibility remains forbidden and comparison remains post-run only.
- The independent verifier, Strict/External/Agent definitions, FP/FN calculation,
  similarity method, sandbox, and output non-intervention policy are unchanged.

Primary comparisons:

- Round81 same-parameter unified selector architecture: Strict `0/90`, External
  `10/90`, Agent `0/90`, FP `0`, FN `10`.
- Uploaded Round46 baseline: Strict `31/90`, External `32/90`, Agent `55/90`,
  FP `24`, FN `1`.

The endpoint process has restarted since Round81, so request-level stochastic
differences must be reported; they do not permit changing the score after the run.

## Frozen command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round85_full90_direct_task \
  --max-transitions 200 \
  --concurrency 8
```

After completion, all 90 cases must be traced backward manually from their final
state and grouped only after each first causal failure, downstream amplification,
workspace outcome, and false-positive/false-negative status have been inspected.
No result-dependent implementation or evaluation change is allowed during the run.
