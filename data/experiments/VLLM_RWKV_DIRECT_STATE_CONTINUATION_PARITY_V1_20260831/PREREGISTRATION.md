# vllm-rwkv direct-state continuation parity preregistration

## Trigger and fixed question

The frozen S67 request-tail pooling runner failed closed on its first zero-state train row: the exact same additive token sequence produced a final-hidden maximum absolute difference of `0.59375` when the current Selector step was split into two direct-model calls. No feature shard or metric was accepted. This experiment isolates whether that drift comes from the engine's segmented execution, the CPU export/import adapter, or the FP16 WKV state profile. It does not change the failed S67 parity threshold and cannot make a release claim.

## Frozen inputs

- Dataset: `data/datasets/vllm_rwkv_direct_state_continuation_parity_v1/cases.json`, five deterministic synthetic valid-vocabulary token sequences and no labels. Its SHA-256 and the manifest SHA-256 are frozen in the runner before the first model invocation.
- Model: `data/models/rwkv7-g1i-2.9b-vllm-v1/model.safetensors`, SHA-256 `01f39dd59fc402fbe8ba49765a1997ee9dbc82427bf0ece6a4fac520e9eb8044`.
- Model config SHA-256 `05eac575fb4b9804460d379ff05349b5eec2f3f405063b51706d3a480d8ef6ad`.
- Engine revision `67f0c5996c50dca0ad779da545cb491527de988f`; frozen `rwkv7.py` SHA-256 `5d6c248281a50512ded806027ef7599513a581a33110a5a68a09a13ca175bb9b`; build-profile SHA-256 `528af12683a4eaac2fea918980011e783408b26593d9718f45d2877cd9bfffbb`.
- Physical GPU is local GPU0 UUID `GPU-7367aa85-43ac-ee32-6599-b8500f23bc48`. GPU1/2 and remote product port 18070 are excluded.
- No S67 row is opened. In particular, the retired S67 test is neither parsed nor used.

## Fixed factorial comparisons

Run zero initial state in separate clean processes for `fp16` and `fp32io16`. For each fixed token sequence:

1. Reference: one `forward_all_hidden` call over all tokens.
2. Same-device segmented: reuse the exact live CUDA state object and call the same method before/after split positions 1, `floor(T/2)`, and `T-1`, after deduplication.
3. CPU-round-trip segmented: at `floor(T/2)`, clone every state tensor to contiguous CPU storage, allocate a fresh model state, copy each tensor back without dtype conversion, then continue.

Concatenated segmented hidden rows, final hidden, final shift state, final WKV state, and elapsed state are compared to the one-piece reference. The CPU-round-trip result is also compared bitwise with the same-device midpoint result. Tokens, raw hiddens, and raw final states are saved unmodified per case/path; there is no LM-head projection, generation, sampling, filtering, repair, reordering, or truncation.

## Fixed metrics and gates

- Maximum absolute difference is computed after casting both raw tensors to float64 only for comparison.
- Cosine similarity is the float64 flattened dot product divided by the product of float64 L2 norms, with zero/zero defined as 1 and only one zero defined as 0.
- Normalized RMSE is float64 RMS(error) divided by `max(float64 RMS(reference), 1e-12)`.
- Elapsed must equal the token length exactly for every path.
- Adapter round-trip gate: CPU-round-trip and same-device midpoint raw hidden/state tensors must be bitwise equal.
- Semantic continuation gate, applied to every case and split: final-hidden max absolute difference `<=0.01`, final-hidden cosine `>=0.99999`, all-hidden normalized RMSE `<=0.001`, final-WKV normalized RMSE `<=0.001`, and final-shift normalized RMSE `<=0.001`.
- A mode is eligible only if every comparison passes. `fp32io16` may replace `fp16` for persistent state lanes only if it passes and a later fixed real-protocol latency/route-retention ablation passes. If neither mode passes, engine/state-continuation remediation is required. Thresholds are not changed after a run.

## Interpretation boundary

This diagnostic determines numerical/state transport integrity only. It does not evaluate selector accuracy, state-tuning quality, retrieval quality, Planner quality, Executor quality, or full Harness completion. A one-call suffix-pooling implementation may independently avoid introducing an artificial split for the request-tail ablation, but that does not erase a failed persistent-continuation result.
