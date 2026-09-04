# Round86 atomic Task-call full-chain canary preregistration

## Purpose

Test the general chain repair derived from the complete Round85 90-case manual
analysis. This is not a score-tuning run and no case-specific operation, argument,
answer, criterion, or completion decision is supplied by the controller.

Fixed comparison cases are the same diagnostic canary used in Round83/Round84:
`E2E-B01`, `E2E-B02`, `E2E-B03`, `E2E-H04`.

## Frozen architecture under test

1. Task lane exposes exactly one `lh_task_call` schema. Its params contain
   `task_id`, `operation`, and `arguments`; operation selection and complete
   arguments are emitted atomically by RWKV in the same generation.
2. The Task event contains a compact fixed operation catalog rather than twenty
   competing top-level tool schemas. No controller rule selects or filters an
   operation from the goal.
3. The runtime validates `task_id` against the active Task; it never deletes,
   moves, fills, or rewrites it.
4. Call-envelope normalization only maps one name alias and one argument-container
   alias, now including `parameters`; parameter values are unchanged.
5. Task/Goal runtime rows are structurally distinct from Task proposal objects.
6. Protocol-invalid Task, Goal, and Final calls are returned to their same lane
   with the exact error under a fixed recovery budget. Raw rejected output remains
   audited. The controller does not synthesize a replacement operation.
7. Deterministic idempotent actions store a stable post-action workspace digest.
   An identical action on an unchanged cache-safe workspace is not executed again;
   RWKV still chooses the next operation or completion call.
8. A Task frontier is limited to eight tasks per batch; later causal batches remain
   available through the Goal lane.

## Frozen implementation and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- `rwkv_lh/model.py`: `d74a19dcfc048b79936e12763ed1b5028b614403b0df465d06165918ef66d59e`
- `rwkv_lh/model_io.py`: `4766a61f48a0b1440fc39e1000adcd2aa257322d4e4220e6e0868e40e18d21c4`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- `rwkv_lh/controller.py`: `7e6dd8358eae1a211e55573ee1a93b0cfebaa5ec6290f1b743a349de2b7cb6a5`
- `rwkv_lh/harness.py`: `e3f217d0ef94f1d5ef3d5dd8d7b4cfa426bf44a563c7a2bbb39a2863907b86a8`
- Runner: `62cdfc9d3f21d2b075cbca367db9b6016b79ac144b52784d0019dee6361622c7`
- Regression: `83 passed`
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786757409`
- Concurrency: `1`; max transitions: `200`; fixed model sampling remains unchanged.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 \
  --case E2E-B02 \
  --case E2E-B03 \
  --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round86_atomic_task_chain_canary \
  --max-transitions 200 \
  --concurrency 1
```

## Fixed evaluation

- Inspect every raw Goal and Task call, not only aggregate acceptance.
- Record first Task operation distribution, protocol corrections, executed actions,
  Agent completion, external acceptance, Strict E2E, FP and FN.
- Compare against Round83/Round84 and Round85 full-run causal classes.
- No code or evaluation changes are allowed until this canary finishes.

