# State profile injection root cause and corrected S2 result

Date: 2026-08-28 (Asia/Shanghai)

## Root cause

`PersistentVLLMRWKVExtractor.extract_hidden_pair()` created its recurrent
state by calling `model.zero_state()` directly. That path bypassed the
profile-aware `_new_state()` method and therefore ignored every pinned tuned
initial WKV state during Hidden+MLP feature extraction. The registered profile,
manifest and SHA-256 still appeared in metadata, so configuration inspection
alone could not detect the defect.

Before correction, the complete 2,526-row S2 causality audit reported bitwise
identical tuned/zero `last` and `mean` features and zero changed raw logits.
This is direct evidence that the profile was not entering the forward pass,
not evidence that state tuning was ineffective.

## Systemic correction

Fresh feature extraction now calls `_new_state(batch_size)`, the same immutable
profile-aware initialization boundary used by other fresh model paths. It does
not alter tokenization, prompt bytes, hidden values after the model forward,
sampling, generated text or RWKV output. A regression test fails if
`extract_hidden_pair()` returns to the direct zero-state path and separately
checks exact tuned-state replication across a batch.

Relevant code and test:

- `rwkv_lh/inference/vllm_rwkv.py`;
- `tests/test_persistent_vllm_rwkv_state_injection.py`.

## Corrected causal evidence

The unchanged S2 profile and unchanged 2,526 rows were re-extracted after the
fix. Compared with zero state:

- all 2,526 rows changed in both feature protocols;
- `last`: 6,399,956 changed elements, mean absolute difference
  0.0563421516, maximum 2.1875;
- `mean`: 6,466,537 changed elements, mean absolute difference
  0.0162724112, maximum 0.4969711;
- the same frozen tuned head changed raw logits on all 2,526 rows, with mean
  absolute difference 0.0996041 and maximum 1.4789134;
- generated RWKV text and sampling invocations remained zero.

Evidence:
`run_s2_tuned_profilefix/STATE_FEATURE_CAUSALITY_AUDIT.json`.

## S2 disposition

The corrected profile is causal but S2 remains rejected. Its full ECRA120
result improves the web/connector macro-F1 only from the recorded zero-state
ablation 0.3152174 to 0.3492908, while local and privacy false takeovers remain
large and connector exact is only 2/20. A causal state change is not sufficient
for deployment; it must satisfy the frozen task metric and complete Harness
regression. S2 is retained as negative experimental evidence and is not routed
at runtime.

