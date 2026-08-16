# Round106 Task subject-scope canary preregistration

## Fixed scope

- Cases: `E2E-LH07`, `E2E-H13`.
- Dataset, hidden acceptance, endpoint, sampling and Strict verdict remain unchanged.
- `max-transitions=200`, `concurrency=1`.
- Offline regression before execution: `107 passed`.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `82b2faf1d8d38218ae67f49d32df0cb1bc6b39418f876ec76890f1d062f0d334`
- model_io `2feae02f7b726d16e9129b296d6478b09888da73e1272684e897f057411ff210`
- controller `5038055e00fc109c79a187f22c8b24eb4178a691a5965183041708ba2bd01b2a`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-LH07 --case E2E-H13 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round106_task_subject_scope_canary \
  --max-transitions 200 --concurrency 1
```

## Registered change

- For a single Task declaring `evidence_kind=file_content_read`, every path-bound operation
  target must exactly equal its RWKV-declared `evidence_subject`.
- A conflicting action is returned to the same RWKV lane as a protocol/scope rejection;
  the action is not executed and no replacement operation or path is selected by the
  controller.
- Other evidence kinds, collection-member bindings, semantic values, artifact content,
  completion decisions and Final text are unchanged.

## Fixed evaluation

- Record Strict/Agent/External, requests, Tasks, Attempts, repairs, non-empty Final and raw
  Final equality.
- Inspect every call in both cases.
- Confirm LH07 service lanes no longer execute reads of a different service path.
- Confirm H13's checkpoint-subject phase cannot silently read corpus inputs under a
  conflicting single-subject contract; any correction/replacement must come from RWKV.
- Strict success still requires all correct migrations/checkpoints and is not implied by
  cleaner blocking or fewer calls.
