# Round112 Basic-30 frontier-role quality regression preregistration

## Fixed scope

- Cases: `E2E-B01` through `E2E-B30`, exactly 30 basic cases.
- Dataset, hidden acceptance, endpoint and fixed sampling remain unchanged from Round101.
- `max-transitions=200`, `concurrency=1`.
- Historical comparison: Round101 Basic Strict `10/30`; full-suite FP `20`, FN `9`.
- Offline regression: `107 passed`; unified architecture control: `70 passed`.

## Frozen source

- schema `df5e15f6f2344aa799f1e749274e3d1576bcd9176382734a5375e8cd9d13583e`
- model `4de14b67ec074e1fc4101c34da159c8a5042ea1857530bec51112428516bc33d`
- model_io `759afd09d3c6cbf2a0a67fe00b66115cf019f25054b2f0e161b05c91c446fc06`
- controller `7388b470392824b8b72b551bf748ac6f47589526d010a1366b4f089c7c07f803`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `25a83ef1838b3e7913954aa20a431e8131e6b256584aca9cb96e7e9dc4bb2649`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Frozen architecture

- One canonical G1i Task call and simple explicit-value format normalization.
- Identical/no-progress replacement suppression, duplicate-active replacement rejection, and
  bounded supersede-chain recovery.
- Non-empty raw RWKV Final for every terminal state.
- Final-outcome evidence guidance and collection/workset progressive disclosure.
- RWKV-declared `frontier_role=prerequisite|deliverable`; prerequisite-only frontiers cannot
  commit Goal done.
- The disproved Round106 evidence-subject-as-input-scope guard is absent.

## Fixed evaluation

- Strict/Agent/External, FP, FN, requests, Tasks, Attempts and repairs.
- Non-empty Final and byte equality to raw RWKV Final.
- Inspect every case and every call; compare first deviation and amplification class with
  Round101, not only aggregate counts.
- Quality is primary. Request reduction alone does not count as improvement.
- FP must not increase in this post-Round2 regression; no result-dependent threshold changes.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 --case E2E-B02 --case E2E-B03 --case E2E-B04 --case E2E-B05 \
  --case E2E-B06 --case E2E-B07 --case E2E-B08 --case E2E-B09 --case E2E-B10 \
  --case E2E-B11 --case E2E-B12 --case E2E-B13 --case E2E-B14 --case E2E-B15 \
  --case E2E-B16 --case E2E-B17 --case E2E-B18 --case E2E-B19 --case E2E-B20 \
  --case E2E-B21 --case E2E-B22 --case E2E-B23 --case E2E-B24 --case E2E-B25 \
  --case E2E-B26 --case E2E-B27 --case E2E-B28 --case E2E-B29 --case E2E-B30 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round112_basic30_frontier_role \
  --max-transitions 200 --concurrency 1
```
