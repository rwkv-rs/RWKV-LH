# Round110 frontier-role canary preregistration

## Fixed scope

- Case: `E2E-LH07`.
- Dataset, hidden acceptance, endpoint, sampling and Strict verdict remain unchanged.
- `max-transitions=200`, `concurrency=1`.
- Offline regression before execution: `107 passed`.

## Frozen source

- schema `df5e15f6f2344aa799f1e749274e3d1576bcd9176382734a5375e8cd9d13583e`
- model `4de14b67ec074e1fc4101c34da159c8a5042ea1857530bec51112428516bc33d`
- model_io `759afd09d3c6cbf2a0a67fe00b66115cf019f25054b2f0e161b05c91c446fc06`
- controller `77edffdaa3734ee9b2486e1a893c238724afd1aa3c1725d037bfbad921beb43d`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `25a83ef1838b3e7913954aa20a431e8131e6b256584aca9cb96e7e9dc4bb2649`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-LH07 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round110_frontier_role_canary \
  --max-transitions 200 --concurrency 1
```

## Registered change

- Every `lh_tasks` and `lh_replace_task` call must include RWKV-selected
  `frontier_role=prerequisite|deliverable`.
- The role is persisted on every Task in the frontier and included in Goal progress.
- `lh_goal_done` is rejected after prerequisite-only completed work and the same RWKV Goal
  lane must produce the next `lh_tasks` frontier.
- Historical Task states default to deliverable for resume compatibility; no current model
  output receives a controller-generated role.
- No Goal parsing, operation/value synthesis, external-verifier visibility, completion
  substitution, or Final rewriting is introduced.

## Fixed evaluation

- Strict/Agent/External, FP/FN, requests, Tasks, Attempts, repairs, non-empty/raw-equal Final.
- Inspect every call and the raw `frontier_role` values.
- Confirm a prerequisite discovery frontier cannot alone produce Agent completed.
- Strict still requires all correct migrations, report and verifier success.
