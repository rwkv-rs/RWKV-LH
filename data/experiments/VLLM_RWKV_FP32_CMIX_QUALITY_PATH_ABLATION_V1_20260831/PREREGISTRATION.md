# vllm-rwkv FP32 CMix quality-path ablation preregistration

## Trigger and root hypothesis

The registered direct-state continuation experiment rejected both `fp16` and `fp32io16`. Its raw outputs show that two executions of the same short segmented path disagree beginning at layer 1 while layer-0 recurrent state is equal; midpoint executions become bitwise stable once both segments exceed the short-row CMix path. Static engine inspection found that `cmix_sparse_spmv_relu_one_kernel` accumulates FFN tiles into an FP16 output with unordered `atomicAdd`, and `RWKV7ForCausalLM.cmix_from_mixed` selects this path even when `fp32io16` declares `allow_fp16_accumulation=False` and `gemm_accumulation_policy="fp32"`.

The fixed hypothesis is that bypassing the FP16 atomic CMix short-row paths under the existing `fp32io16` profile restores repeated-path determinism. This is an isolated runtime path ablation before any engine/product change.

## Frozen inputs and variants

- Reuse the five no-label synthetic token sequences from `vllm-rwkv-direct-state-continuation-parity-v1`: cases SHA-256 `2bea618ac9d4ce73a324628c5c3485f5a3b07c6b30324ae458c355bfc2356c60`, manifest SHA-256 `1c6519bb9466f989f8efcb00bdf2b69c8d6b0c3c311bcd63705d955a6bb3a2c2`.
- Model/engine/GPU are identical to the parent experiment: weights SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`, engine revision `67f0c5996c50dca0ad779da545cb491527de988f`, local GPU0 UUID `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`.
- WKV mode is fixed to `fp32io16`.
- Variant `fp32_cmix_dense`: before inference set the imported engine module's `CMIX_NOFC_MAX_ROWS=0` and `CMIX_NOFC_ROW20_MAX_T=0`. No model tensor, WKV kernel, token, hidden, or state is changed.
- Variant `fp32_cmix_dense_unfused_t1`: apply the same change and also set `LN1_TMIX_FUSE=False` to test whether the remaining T=1-only fusion explains one-piece versus 1+1 drift.
- Run variants in separate clean processes. The parent `fp32io16` result SHA-256 `b02fedcb8b7c507d1f726e4e360011fd1e17721830cf038ada7e9df48671b434` is immutable baseline evidence and is not rerun.

## Fixed comparisons and gates

For every case, preserve a one-piece reference and execute each midpoint segmented path twice from fresh zero state with the same live-CUDA-state behavior. Execute a third midpoint path with an exact CPU state round-trip. Preserve every raw token, hidden tensor, and final state tensor unmodified.

- Determinism gate: the two same-device midpoint paths must be bitwise equal for tokens, all hidden rows, shift state, WKV state, and elapsed state in all five cases.
- Adapter gate: the CPU-round-trip midpoint path must be bitwise equal to the first same-device midpoint path in all cases.
- Every elapsed state must equal the full token length; all floating outputs must be finite.
- Parent semantic metrics and thresholds are repeated without alteration: final-hidden max absolute difference `<=0.01`, final-hidden cosine `>=0.99999`, all-hidden normalized RMSE `<=0.001`, WKV normalized RMSE `<=0.001`, shift normalized RMSE `<=0.001`. They diagnose boundary invariance but do not veto a determinism-only engine fix because the real request-tail remediation will not add a boundary.
- Select the minimal variant: `fp32_cmix_dense` is preferred if it passes determinism and adapter gates; the T1-unfused variant is considered only if the first variant fails either gate or if it alone materially closes the 1+1 semantic threshold without regressing longer cases.

No S67 row, label, locked test, generated RWKV text, LM-head output, or sampling is used. No current engine or product configuration changes until a minimal source fix and its regression/performance validation pass.
