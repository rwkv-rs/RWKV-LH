# Round105 structural recovery canary preregistration

## Fixed scope

- Cases: `E2E-H08`, `E2E-LH07`, `E2E-H13`.
- Dataset, hidden acceptance, endpoint, sampling, concurrency and Strict verdict are
  unchanged from Round104.
- `max-transitions=200`, `concurrency=1`.
- Offline source regression before the run: `106 passed`.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `82b2faf1d8d38218ae67f49d32df0cb1bc6b39418f876ec76890f1d062f0d334`
- model_io `012a7c0c08876689f8d93870b9fda2069d6856c531ec067a9bc5f3f527fa6997`
- controller `d1b4e1848c71ce16f9c1a5d0191e8182fdf86d32ca7d1a8b6813c9e9db04be0c`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-H08 --case E2E-LH07 --case E2E-H13 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round105_structural_recovery_canary \
  --max-transitions 200 --concurrency 1
```

## Registered changes

1. Task schema states that evidence describes the final `done_when` outcome rather than
   an intermediate read; mutation Tasks should use final mutation evidence.
2. Complete read observations explicitly state the EOF/source-size boundary and prohibit
   continuation of the same source at or beyond that boundary.
3. An unchanged-action recovery cannot replace a Task with the exact same normalized
   RWKV-declared objective, done_when, evidence kind, and evidence subject.
4. A replacement batch cannot duplicate another currently active Task or contain exact
   duplicate Task structures.
5. Deterministic unchanged replacements share a maximum three-replacement supersede-chain
   budget.
6. `lh_final_answer` is explicitly valid and required for every terminal run status.

No controller logic selects an operation, argument value, artifact content, Task semantic
field, success verdict, or Final answer.

## Fixed evaluation

- Record Strict/Agent/External, request/Task/Attempt/repair counts, non-empty Final and raw
  Final equality.
- Inspect every model call for each case and identify the first deviation and amplification
  chain relative to Round104.
- Primary architecture checks: H08 does not create an unbounded identical supersede chain;
  LH07/H13 do not append duplicate active Tasks through replacement batches; every terminal
  path still yields a non-empty response.
- Correct semantic values remain required for Strict success. Lower request count or a
  cleaner failure alone is not counted as task correctness.
