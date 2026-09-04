# Round108 collection discovery canary preregistration

## Fixed scope

- Case: `E2E-LH07`.
- Dataset, hidden acceptance, endpoint, sampling and Strict verdict remain unchanged.
- `max-transitions=200`, `concurrency=1`.
- Offline regression before execution: `107 passed`.

## Frozen source

- schema `49eebf20e95169ff22d24cc895a20d5e4a2252465bd98361f47a699654d29763`
- model `abba32fcf1a4d335918b0691353aacae1ba04e313005fc45d1928b8bc5013fdf`
- model_io `ec424a87a371af453a86687f363fe39ec4321c1289a378fa974c03f07c5bfafa`
- controller `82f1d3ff01ce44c07255415ab0a46383ce4651a8107bf9b295b8bd32b94a5a15`
- harness `832139947b687c2e5f9de5c8db0e958dd2329457e2c54e986481be1f27d7a544`
- chunks `6d1018e921708ac6d410dcd21925f4c5d81ee284f4b83e32a7d767c60b95b29c`
- task_graph `517cd37e978d6e6fc8284e3f83e76539d785625dc880eee44304963c667b1f45`
- runner `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all --case E2E-LH07 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round108_collection_discovery_canary \
  --max-transitions 200 --concurrency 1
```

## Registered change

- No runtime transition or verifier logic changes after Round107.
- Existing `collection_listing`/`lh_workset` capability is disclosed more directly: for the
  same operation over multiple files in one directory, RWKV is asked to create one
  collection Task, list the directory, and declare the exact sealed workset instead of
  creating one independent Task per member.
- RWKV still selects whether to use collection mode and supplies every member identity,
  operation, argument, Task, mutation value, completion decision, and Final answer.

## Fixed evaluation

- Strict/Agent/External, requests, Tasks, Attempts, repairs, non-empty/raw-equal Final.
- Inspect every call and record whether the initial Goal frontier uses a collection Task.
- If collection mode is selected, verify the workset identities come verbatim from RWKV and
  each executed action binds a declared pending member.
- Only correct migrations, report and verifier success count as Strict correctness.
