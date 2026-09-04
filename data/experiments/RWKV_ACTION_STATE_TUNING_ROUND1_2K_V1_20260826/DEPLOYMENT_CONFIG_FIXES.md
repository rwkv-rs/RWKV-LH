# Round1 deployment configuration fixes

Date: 2026-08-26 (Asia/Shanghai)

This record covers deployment faults only. None is counted as a state-tuning
behavioral improvement.

## 1. Secret recovery depended on a transient baseline unit

### Original error

`prepare_remote_rwkv_lh_tuned_vllm_env.py` aborted with:

```text
cannot recover the local vLLM API key from the baseline unit
```

### Root cause

The preparer treated a stopped transient systemd unit as the durable source of
the vLLM API token. systemd removed the transient unit after it was stopped, so
the source disappeared before tuned deployment.

### Fix

- Added fail-closed `--api-key-stdin` support.
- The token is streamed from the existing local protected environment to the
  remote preparer through stdin; it is not placed in argv or printed.
- Unit-based recovery remains only as a compatibility fallback.
- The generated remote environment is atomically replaced with mode `0600`.

### Verification

The preparer reported the selected state path/SHA, served model, `mode=0o600`,
and `api_key=<redacted>`. Only environment key names were subsequently listed.

## 2. systemd stripped JSON quotes from the vLLM argument

### Original error

The first tuned vLLM process exited with status 2:

```text
argument --override-generation-config: Value {temperature:0.1} cannot be converted
```

### Root cause

The unit contained:

```text
--override-generation-config={"temperature":0.1}
```

systemd used the double quotes for argument grouping and passed the invalid
literal `{temperature:0.1}` to vLLM.

### Fix

The complete JSON value is enclosed in single quotes in the unit so its inner
double quotes survive systemd parsing:

```text
--override-generation-config='{"temperature":0.1}'
```

### Verification

- `systemd-analyze --user verify` passed.
- `systemctl show -p ExecStart` showed the parsed argv value as valid JSON.
- vLLM logged `override_generation_config: {'temperature': 0.1}` and reached
  HTTP `/health` 200 with zero restarts.

## 3. State preflight proved file integrity but not runtime use

### Original gap

The original preflight verified the state checkpoint and adapter hashes, but a
successful server start did not prove that EngineCore imported the monkeypatch,
loaded the state, or used it to initialize new request rows.

### Fix

- Pinned adapter SHA-256:
  `853df387c2ea587819e24bdba95e450eec7f2a5fff8d069f0b4764639d914644`.
- Added a mode-`0600` JSONL runtime attestation file.
- Recorded bounded, non-secret events for `monkeypatch_installed`,
  `state_loaded`, and `zero_row_initialized`.
- The unit clears the exact attestation file before each start so stale events
  cannot satisfy a later deployment check.

### Verification

EngineCore attested the preregistered final checkpoint SHA-256
`601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5`,
runtime shape `[61, 64, 64, 64]`, fp32 runtime WKV state, mean absolute value
approximately `0.00127613`, and maximum absolute value `0.0187988`.

One two-stage progressive `ModelSession` smoke then increased
`zero_row_initialized` by four events, all from the same EngineCore PID and
state SHA. This proves request-level state initialization rather than only file
availability.

## Stable deployment contract for subsequent rounds

Subsequent state-tuning deployments must preserve all of the following:

- base checkpoint path and SHA;
- final selected state path and SHA;
- adapter path and SHA;
- GPU0, `fp32io16`, max model length 16384, batched-token and sequence limits;
- valid systemd-parsed JSON argv;
- protected API-token injection through stdin/environment file;
- preflight success, HTTP health 200, zero restart count;
- runtime `state_loaded` plus request-level `zero_row_initialized` attestation.

A run that lacks any of these checks is a deployment/configuration failure and
must not be interpreted as a state-tuning behavioral result.
