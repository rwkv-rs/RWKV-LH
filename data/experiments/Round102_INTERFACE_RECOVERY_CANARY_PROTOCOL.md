# Round102 interface/recovery canary preregistration

## Fixed scope

- Cases: `E2E-B18`, `E2E-B27`, `E2E-M10`, `E2E-M19`, `E2E-H01`,
  `E2E-H08`, `E2E-H13`, `E2E-LH06`, `E2E-LH07`, `E2E-LH09`.
- These cases were selected before execution from the completed Round101 manual
  causal ledger. They cover explicit argument aliases, single-key envelopes,
  exact EOF, transient retry, direct `task_ref`, and extension verification.
- Dataset, external verifier, Strict verdict, sampling and endpoint are unchanged.
- `max-transitions=200`, `concurrency=1`.
- The run must not modify source, data, thresholds or verdict logic after it starts.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `03d6c0eab5e7d00fdb7b12192019a99e0437c1041ff87a05fff9426d531ed6dd`
- model_io `b7026db912cb73c926379b3ae7d3d1c68ddcbc93fb0266d62a36978225063d93`
- controller `94b91b0036825e3e200b98769e5c2588a1703ac7a8307f08b154093efb93064d`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- Offline regression: `101 passed`.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B18 --case E2E-B27 --case E2E-M10 --case E2E-M19 \
  --case E2E-H01 --case E2E-H08 --case E2E-H13 \
  --case E2E-LH06 --case E2E-LH07 --case E2E-LH09 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round102_interface_recovery_canary \
  --max-transitions 200 --concurrency 1
```

## Fixed evaluation

- Record Strict/Agent/External, FP/FN, request count and non-empty Final for all ten.
- Inspect every call for each case; compare the first deviation and amplification
  chain against Round101, not only the aggregate score.
- Confirm normalization audit contains the original and normalized payload and
  `controller_semantic_fields_generated=false`.
- A converted call is valid only when every operation, task identity and business
  value was explicit in the raw RWKV payload.
