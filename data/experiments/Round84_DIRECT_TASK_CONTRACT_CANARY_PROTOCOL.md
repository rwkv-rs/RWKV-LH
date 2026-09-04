# Round84 direct Task-contract canary preregistration

## Purpose and fixed comparison

Repeat the exact Round83 diagnostic cases after only two general interface
clarifications discovered from all four Round83 Task calls:

1. Task identity is runtime-bound and undeclared `task_id` / `scope_id` fields
   are forbidden by the selected function schema.
2. `lh_chunk_map` is a read-only large/multi-file analysis operation, not a file
   creation operation, directory reader, output verifier, or ordinary small-file
   read replacement.

No tool is selected for RWKV, and no emitted operation or parameter is edited.
The direct one-generation Task-call architecture, parser, verifier, sampling,
hidden acceptance, score, and cases remain unchanged.

Fixed cases: `E2E-B01`, `E2E-B02`, `E2E-B03`, `E2E-H04`.

## Frozen implementation and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- `rwkv_lh/model.py`: `06347065a962d5f3719da6d36a109b4892110e97aeaaaa57ce7ffd01bbd65a7a`
- `rwkv_lh/model_io.py`: `852b0220040445b5755d9f84e0fa0c4ef7583a06cef63bb6e6b0981f2c98ad4c`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- Targeted regression: `29 passed in 5.54s`
- Historical selector rejection replay: `18/24` exact raw calls accepted
  atomically; the remaining six retain real schema errors.
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786754951`
- Concurrency: `1`; max transitions: `200`; temperature: `0.05`;
  semantic resampling: `0`.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 \
  --case E2E-B02 \
  --case E2E-B03 \
  --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round84_direct_task_contract_canary \
  --max-transitions 200 \
  --concurrency 1
```

Round84 is a diagnostic canary, not an E2E-90 score. All raw calls and first
remaining failures must be inspected regardless of aggregate outcome.
