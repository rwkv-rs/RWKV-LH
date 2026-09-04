# FP32 CMix source implementation validation protocol

The minimal ablation `fp32_cmix_dense` passed 5/5 determinism and adapter
gates. The T1-unfused variant produced identical registered metrics, so it is
rejected as unnecessary. The source implementation is isolated in engine
worktree `data/runtime/engines/vllm-rwkv-quality-fp32-cmix-v1`, branch
`chase/fp32-cmix-quality-v1`, commit
`0501caa628967103490507d734f6a5efaf165794`.

Frozen source identities:

- `vllm/model_executor/models/rwkv7.py` SHA-256
  `a1f6282e3c65a0bc7e05d01a27eccf6e50fd79a5225c6001de9dbf95c97dfc75`.
- `tests/model_executor/models/test_rwkv7.py` SHA-256
  `5719c7d2869d6966e923cc4da3f4fdd8d1a1b904f68ed9165c6872218ff0f58b`.
- Binary build profile is unchanged at SHA-256
  `528af12683a4eaac2fea918980011e783408b26593d9718f45d2877cd9bfffbb`;
  the fix is Python dispatch only and reuses the already validated kernels.
- The implementation changes only two short-row conditions: FP16 atomic
  sparse CMix remains enabled when `allow_fp16_accumulation=True`, while
  `fp32io16` falls through to its existing dense FP32-accumulation path.

Before the real-model run, the full engine model unit file must report all 171
tests passed. The real-model validation repeats the exact five-case,
one-piece/two-same-device/one-CPU-round-trip sequence in `fp32io16`, without a
runtime monkeypatch. Every raw token, hidden, shift, WKV, and elapsed tensor
must be bitwise identical to the accepted monkeypatch ablation artifact
`run_fp32_cmix_dense` (result SHA-256
`a08db6af34c9a4f2a6714d4bd14c0abc1b437644dcff7abb7b52ae2d18077f2d`).
Repeated-path and adapter bitwise gates remain 5/5; elapsed and finiteness
remain exact. No S67 row, label, generation, sampling, or product service is
used. A mismatch rejects the source implementation and does not permit product
adoption.
