# Round104 discovery/observability canary preregistration

## Fixed scope

- Cases: `E2E-H08`, `E2E-LH07`, `E2E-H13`.
- Round103 first deviations under test: missing explicit EOF/source-size facts;
  mutation planning before referenced rule/data contents were visible; oversized
  operation inputs and dependency memories in recovery capsules; stable Task
  loops with no Goal replacement exit.
- Dataset, hidden verifier, Strict verdict, endpoint and sampling are unchanged.
- `max-transitions=200`, `concurrency=1`. No source, dataset, threshold or verdict
  changes after execution starts.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `cfed075d52cf73ef4ee42ff3aa6fa4fe51fdef41a2768e87847931d8d1f7bfae`
- model_io `1d6b340434e8fd85390815ff10a3cfa8b7143907c5302bb4ad63d432ee99d77c`
- controller `adafc94395551a0b846a9d42a7c72d880dbd0015d9e7ff7a5d94fb5906cedcd9`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- Offline regression: `105 passed`.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-H08 --case E2E-LH07 --case E2E-H13 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round104_discovery_observability_canary \
  --max-transitions 200 --concurrency 1
```

## Fixed evaluation

- Record Strict/Agent/External, FP/FN, requests, Tasks, Attempts, repairs and
  non-empty raw-equal Final.
- Inspect every call and compare the first deviation/amplification chain with
  Round103 for the same case.
- Check discovery is RWKV-proposed, not controller-inserted; all normalized
  task ids, operations and values must exist in raw RWKV output.
