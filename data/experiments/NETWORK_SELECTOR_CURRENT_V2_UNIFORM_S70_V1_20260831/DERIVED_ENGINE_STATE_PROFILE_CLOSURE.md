# Derived-engine state-profile revision closure

Date: 2026-08-31 (Asia/Shanghai)

## Root cause

The S70 state manifests correctly bind their tensors to the unchanged 2.9B
model artifact revision `67f0c5996c50dca0ad779da545cb491527de988f`.  The validated
quality runtime is a derived engine at
`0501caa628967103490507d734f6a5efaf165794`.  The persistent extractor loaded a
state manifest using `settings.engine_revision`, so a valid artifact-bound state
was incorrectly checked against the derived runtime revision and rejected before
the first forward.

This is a global derived-runtime/state-profile integration defect.  It is not an
S70 case failure and cannot be corrected by changing the state manifest or its
tensors.

## Correction

`PersistentVLLMRWKVExtractor._load_initial_wkv_state` now passes
`settings.model_artifact_engine_revision` to the immutable state-profile loader.
The runtime engine remains pinned and attested separately by
`settings.engine_revision` plus the runtime-derivation manifest.

- previous extractor source SHA-256:
  `a01c662ae342602b9de8c8fc6c0df5c9aa508dec3dee7bb0e03fe18347bccb17`
- corrected extractor source SHA-256:
  `d7ca18fd54ca6d2a835c647ab3d7712a05132e51c1f456cf4c93dbb1f23ef465`

No model weight, state tensor, hidden feature, raw logit, generated text, engine
source, tokenizer, or runtime-derivation evidence was changed.

## Verification

- Added a regression that configures different runtime and artifact revisions and
  proves the state loader receives only the artifact revision.
- `tests/test_persistent_vllm_rwkv_state_injection.py` plus
  `tests/test_state_router_metrics.py`: `15 passed`.
- The corrected path loaded the real nonzero `S70-ST500` state under the derived
  FP32-CMix engine and completed all 2,500 frozen train/dev rows with per-forward
  state identity assertions, no sampling, and no hidden modification.  Its
  feature manifest SHA-256 is
  `6acf82ca1d05e17239e44aedcb4d4ecfb0550100a6e0dd68573f1044e5c74c5b`.
- Product service `rwkv-8222:18070` remained healthy during the correction and
  real-state validation.

The full four-state dev ablation and project-wide regression remain separate
completion gates.
