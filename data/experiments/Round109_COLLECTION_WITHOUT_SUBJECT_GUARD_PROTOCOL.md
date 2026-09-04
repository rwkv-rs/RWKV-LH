# Round109 collection guidance without subject guard preregistration

## Fixed scope

- Case: `E2E-LH07`.
- Dataset, hidden acceptance, endpoint, sampling and Strict verdict remain unchanged.
- `max-transitions=200`, `concurrency=1`.
- Offline regression before execution: `106 passed`.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `abba32fcf1a4d335918b0691353aacae1ba04e313005fc45d1928b8bc5013fdf`
- model_io `fadbaed3622d25ac6024cb5070dcd77fb8cb4728624aebd983f56bdccb64c732`
- controller `a4eccea3fac754f45429defced7184ba60d933b9e2935a75aa874aabb1a28d47`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-LH07 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round109_collection_without_subject_guard \
  --max-transitions 200 --concurrency 1
```

## Registered change

- Remove the Round106/107 action-target equals evidence-subject guard and its tests because
  Round108 disproved the assumption that final evidence subject is the Task's complete input
  scope.
- Retain collection/workset progressive disclosure, inline generic operation-rejection
  readiness, identical-replacement suppression, duplicate-active-Task rejection, shared
  replacement-chain budget, EOF facts and all interface normalization.
- No controller-selected Task grouping, input path, member, operation, value, completion or
  Final is introduced.

## Fixed evaluation

- Strict/Agent/External, requests, Tasks, Attempts, repairs, non-empty/raw-equal Final.
- Inspect every call, especially the initial Goal topology and whether list/workset/read
  operations execute.
- Compare against Round108's 1 Task/0 Attempt protocol failure and Round107's 11 Task/8
  Attempt partial discovery.
- Only complete correct migration counts as Strict success.
