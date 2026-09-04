# G9 multi-profile request identity fail-closed hardening

Date: 2026-08-30. This change was made while G9 training was running and before
any G9 checkpoint or multi-profile inference.

## Root cause

`RWKV7InitialStateProfiles.load()` correctly pinned the manifest, model and
state bytes, but `resolve_request_profile()` still resolved a request without
`rwkv_state_profile`/`rwkv_state_profile_sha256` to the manifest's native zero
default. In a multi-profile service this makes a missing delivery identity look
like a valid zero-state request, so the intended task-level state can be lost
silently.

## Systemic correction

- A profile registry loaded from a manifest now records
  `requires_explicit_request_profile=True`.
- Such a registry rejects a missing pair before profile resolution/state use.
- An explicit `zero` + 64-zero digest remains valid.
- A zero-only runtime without a manifest preserves legacy implicit native-zero
  behavior, so ordinary single-profile services are not changed.
- No model response, token, sampling value, prompt, weight or state tensor is
  rewritten by this change.

Frozen source identities after the change:

- `rwkv_lh/inference/vllm_rwkv_state_profiles_v1.py` SHA-256
  `a9a1d7dd26aabcd0eecf748885407ed8d6c935632e4c4342fd02c0c76b70342a`;
- `tests/test_vllm_rwkv_state_profiles_v1.py` SHA-256
  `58a5928cd5ca259528c9eb15941fd21e45cc44cfe08cb10b98bc2dca991c2461`.

Validation command (WSL, `uv`, project-local temporary directory):

```text
TMPDIR=/home/chase/GitHub/RWKV-LH/temp/pytest-tmp-g9-profile uv run pytest -q -s \
  tests/test_vllm_rwkv_state_profiles_v1.py tests/test_executor_profiles.py \
  tests/test_openai_compat_runtime.py
```

Result: `38 passed`. The isolated Stage-C engine overlay independently carries
the same pre-allocation rejection and has its own engine-level tests.
