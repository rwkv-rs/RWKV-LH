# Round79 RWKV interface capability probe

Date: 2026-08-14

Status: preregistered capability probe; this is not an E2E result and does not claim an architecture improvement.

## Purpose

Determine which model-server capabilities are actually available before redesigning RWKV-LH around them. The probe separates three mechanisms that must not be conflated:

1. a resumable RWKV recurrent-state handle;
2. prompt/prefix caching;
3. constrained structured output.

The eight Round77 symptoms are not optimization targets in this probe. They remain downstream observations for later fixed-dataset ablation.

## Fixed environment

- Project: `/home/chase/GitHub/RWKV-LH`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Backend profile: `vllm-rwkv-rapid`
- Model endpoint: the authenticated endpoint configured by `RWKV_BASE_URL`; credentials are never recorded.
- Runtime capability source: authenticated `/v1/capabilities` plus the authenticated OpenAPI path inventory.

## Hypotheses and checks

- H1: the deployed server has no explicit create/resume/fork/commit/rollback/export/import recurrent-state API. Accept H1 only if both `/v1/capabilities` and the OpenAPI path/schema inventory expose no such handle.
- H2: prompt-cache fields, if present, are transport/performance features and will not be recorded as recurrent state.
- H3: the server advertises JSON-schema or grammar-constrained output. One minimal discriminated-command request will check whether the advertised contract is executable on the deployed RWKV model.

## Minimal command schema

The probe output is one of three branches, selected by `op`:

- `act`: `op`, `tool`, `args`;
- `task_done`: `op` only;
- `replan`: `op` only.

The single probe prompt requests `act` with `read_file` and `{"path":"input.txt"}`. Semantic quality is not scored; only HTTP success, parseability, schema conformance, finish reason, token usage, and returned byte length are recorded.

## Fixed sampling

- temperature: `0.05`
- top_p: `1.0`
- top_k: `0`
- presence_penalty: `0.0`
- frequency_penalty: `0.0`
- penalty_decay: `0.996`
- max_tokens: `120`
- one request only; no retry after a syntactically valid server response and no semantic resampling.

## Generation

Run from WSL with:

```text
uv run python /home/chase/GitHub/RWKV-LH/temp/probe_round79_rwkv_server_capabilities.py
```

The script prints a credential-free JSON record. The captured result is stored beside this protocol after the probe. Source hashes and OpenAPI-derived facts are included in that record.

