# Round107 inline applicability canary preregistration

## Fixed scope

- Case: `E2E-LH07`.
- Dataset, hidden acceptance, endpoint, sampling and Strict verdict remain unchanged.
- `max-transitions=200`, `concurrency=1`.
- Offline regression before execution: `107 passed`.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `82b2faf1d8d38218ae67f49d32df0cb1bc6b39418f876ec76890f1d062f0d334`
- model_io `2feae02f7b726d16e9129b296d6478b09888da73e1272684e897f057411ff210`
- controller `82f1d3ff01ce44c07255415ab0a46383ce4651a8107bf9b295b8bd32b94a5a15`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-LH07 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round107_inline_applicability_canary \
  --max-transitions 200 --concurrency 1
```

## Registered change

- Validate single-subject applicability immediately after normalizing RWKV's proposed next
  Task operation, before it is recorded as an accepted `act` transition.
- A rejected operation event includes deterministic completion readiness and explicitly
  permits RWKV to choose `lh_task_done` when visible evidence establishes done_when.
- The controller does not complete the Task, choose a corrected operation, or modify any
  RWKV path/value.

## Fixed evaluation

- Strict/Agent/External, requests, Tasks, Attempts, repairs, non-empty/raw-equal Final.
- Inspect every call. Confirm no cross-subject Harness action executes.
- Determine whether RWKV chooses `lh_task_done`, a valid repair, or another repetition after
  the inline rejection. Only Strict external success counts as task correctness.
