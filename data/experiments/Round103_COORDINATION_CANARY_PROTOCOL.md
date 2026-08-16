# Round103 coordination canary preregistration

## Fixed scope

- Cases: `E2E-M10`, `E2E-B27`, `E2E-H08`, `E2E-LH07`, `E2E-H13`.
- Fixed causes under test from Round102: exhausted Task handoff to Goal replanning;
  completion from committed dependency evidence; explicit
  `operation_id/operation_arguments`; 9..16 Task frontiers; compact protocol
  recovery and Goal/Final evidence projection.
- Dataset, hidden external verifier, Strict verdict, sampling and endpoint remain
  unchanged. External acceptance is never shown to RWKV.
- `max-transitions=200`, `concurrency=1`; source and verdict logic remain frozen
  after execution starts.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `03d6c0eab5e7d00fdb7b12192019a99e0437c1041ff87a05fff9426d531ed6dd`
- model_io `6c630d7f54c97c655316b9ab387ec858b01d08fb11cbdf38f8eadd40099b4d88`
- controller `87d09b27c2f3b7a70a9f929e4eda1a40fdefa2aa5372e59c8f2fa8a66a5ae40b`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- Offline regression: `103 passed`.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-M10 --case E2E-B27 --case E2E-H08 \
  --case E2E-LH07 --case E2E-H13 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round103_coordination_canary \
  --max-transitions 200 --concurrency 1
```

## Fixed evaluation

- Report Strict/Agent/External, FP/FN, requests, Tasks, Attempts and non-empty
  raw-equal Final for every case.
- Manually inspect every RWKV call, normalized call, Task/Attempt transition and
  final workspace. Compare first deviation and downstream amplification with
  the same case in Round102.
- Count a normalization as valid only when every semantic value was explicit in
  the raw RWKV payload and the audit states
  `controller_semantic_fields_generated=false`.
