# RWKV-LH Action State Tuning Round1 / 2K final report

Date: 2026-08-26 (Asia/Shanghai)

## Decision

Round1 completed its training, deployment, causal dev comparison, ECRA route120
A/B, RWKV-only E2E90, strong contract-graph E2E90, and local regression suite.

The state-tuning behavioral gate **failed**. The trained state is proven to be
loaded and applied to new vLLM requests, but its measured behavior is
indistinguishable from the baseline sampling-noise floor. The current project
must not be described as a production-ready proactive Harness:

- RWKV-only progressive E2E: `0/90` passed;
- strong contract-graph end-to-end: `8/90` passed, with 55 cases also affected
  by supervisor transport failures;
- ECRA variant B materially improves tool reachability, but every major routing
  gate remains below threshold.

Do not generate another broad 2K/10K task dataset from this result. The next
state round must begin with a small stage-identity canary and an explicit
training-ablation gate.

## Frozen training result

- Dataset: exactly 2,000 train stages and 200 held-out dev stages.
- Train stages: 1,200 direct and 800 selector; all 800 selector targets call
  `select_tool`.
- Loss mask: fail-closed `target_suffix`; historical Assistant spans received
  zero supervised tokens.
- Training: GPU0, zero/native initial state, ctx 2496, one 2,000-step epoch,
  LR `2e-5 -> 2e-6` cosine, BF16, seed 826.
- systemd training result: success, exit status 0, no restart.
- Loss rows: 2,000/2,000 finite; mean `0.0758835`, first-100 mean `0.231541`,
  last-100 mean `0.00150368`.
- Selected checkpoint: preregistered final step 2000, SHA-256
  `601c3c4df8c6e82918efa36d5425626eb9cffa4a0c5f0512da83aa5063e423f5`.
- Checkpoint: 61 BF16 tensors, each `64x64x64`, 15,990,784 elements, all finite
  and nonzero.
- State magnitude grows monotonically across the eight checkpoints: mean
  absolute value `0.000813472` at step 250 to `0.00127613` at step 2000;
  maximum absolute value `0.00494385` to `0.0187988`. The final checkpoint did
  not decay back toward zero.

## Deployment proof and configuration fixes

The tuned service is left active on GPU0 for inspection and continuation:

- HTTP health 200;
- systemd `active/running`, restart count 0;
- base checkpoint and SHA, adapter SHA, state SHA, fp32io16, 16K context,
  batching limits, and GPU index are pinned by the unit/preflight;
- runtime attestation contains 4 monkeypatch imports, 1 `state_loaded`, and the
  bounded maximum of 1,024 `zero_row_initialized` events;
- EngineCore loaded the selected state as runtime fp32 with shape
  `[61,64,64,64]`, mean absolute value `0.00127613`, maximum `0.0187988`;
- a two-stage real `ModelSession` request increased request-row initialization
  events by four using the same EngineCore PID and state SHA.

Three deployment defects were found and fixed before behavior was interpreted:

1. Secret preparation incorrectly depended on a stopped transient systemd
   unit. It now accepts the protected token via stdin and writes a mode-0600
   environment file without logging the value.
2. systemd stripped the inner JSON quotes from
   `--override-generation-config`; the unit now preserves valid JSON in the
   parsed argv and passes `systemd-analyze verify`.
3. Checkpoint preflight proved file integrity but not runtime use. The pinned
   adapter now emits non-secret import/load/request-initialization attestations.

These are engineering fixes and are not counted as state-tuning wins. Full
details are in `DEPLOYMENT_CONFIG_FIXES.md`.

## Primary causal dev200 result

The same dev SHA, endpoint contract, temperature 0.05, and concurrency 32 were
used for baseline and tuned runs.

| Run | Schema valid | Operation | Exact transition |
|---|---:|---:|---:|
| Frozen baseline | 61.5% | 59.0% | 16.0% |
| Tuned step-2000 | 61.5% | 58.5% | 15.5% |
| Tuned repeat/noise control | 61.5% | 59.0% | 16.0% |

Paired baseline-to-first-tuned results produced zero rescues for schema,
operation, or exact transition, with one operation/exact regression. Raw output
differences are within the same-state sampling floor:

- baseline vs tuned: 20/200 raw outputs differ;
- baseline vs tuned repeat: 23/200 differ;
- tuned vs tuned repeat: 25/200 differ.

Therefore no observed delta can be attributed to the trained state.

### Selector failure is the dominant raw model error

- Direct stages: 121 rows, schema-valid 100%, operation correct 118/121.
- Selector stages: 79 rows, schema-valid 2/79, operation correct 0/79.
- 77 selector rows raise the same original error:
  `ModelIOError: tool selection must call 'select_tool'`.
- Instead of `select_tool`, the model directly calls:
  `list_directory` 41 times, `read_file` 18, `read_json` 15, and
  `connector_lookup` 3.
- The two schema-valid selector outputs both select the wrong `web_search`
  operation.
- Prompt length is not a simple threshold explanation: the two schema-valid
  selector prompts are 1,391/1,398 RWKV tokens, while failed selector prompts
  span 1,079-2,232 tokens with median 1,335.

This is a generation-stage identity failure: the model knows valid direct-call
JSON but ignores the progressive selector boundary.

### Direct exact mismatch needs semantic separation

The frozen exact metric remains unchanged. A post-hoc diagnostic shows that
88/121 direct outputs contain every expected parameter value, while only 32 are
exact. Many mismatches only add valid schema defaults, for example
`start_byte=0`, `max_tokens=4096`, or `max_results`.

This diagnostic is not a replacement pass criterion. It prevents the next
state dataset from wasting capacity teaching omission of harmless defaults.
Canonical exactness and semantic argument binding should be reported as
separate fixed metrics in the next preregistration.

## ECRA route120 result

### Variant A: current local Harness

- duration: 475.687 seconds;
- first-tool exact: 10.0%;
- expected-sequence prefix: 9.17%;
- network decision macro-F1: 0.2857;
- required-online false-negative rate: 100%;
- web/connector macro-F1: 0;
- privacy rejection coverage: 0;
- failed/unavailable: 96/120.

### Variant B: retrieval plus deterministic actions

- duration: 692.155 seconds;
- first-tool exact: 37.5%;
- expected-sequence prefix: 36.67%;
- network decision macro-F1: 0.6419;
- required-online false-negative rate: 53.85%;
- web/connector macro-F1: 0.3237;
- privacy rejection coverage: 0;
- failed/unavailable: 66/120.

Variant B rescues 34 first-tool cases and regresses one, proving that the added
tools are reachable and useful. The remaining failure is not simply “tools are
missing”:

- public web: 18/25 first-tool exact;
- deterministic compute: 14/15 first-tool exact, but only 4/15 runs complete;
- structured connector: 1/20 first-tool exact;
- mixed local/online: 1/20 first-tool exact;
- privacy-policy rejection: 0/10 first-tool exact and 0 coverage.

The model can often choose `web_search`, calculator, date, and time tools, but
cannot reliably distinguish web search from connector lookup, enforce the
privacy Gate, or finish after a correct deterministic observation.

## E2E all90 result

### RWKV only, progressive, no supervisor

- duration from protocol/result timestamps: approximately 15 minutes 15 seconds;
- passed: 0/90;
- all 90 statuses: interrupted;
- B01, B05, and H04 pass the external result verifier but the agent fails to
  complete; each consumes 57 model requests, 22 actions, and 12 protocol
  rejections.

This is direct evidence of zero-progress/protocol loops and completion-boundary
failure, not an external backend outage.

### Strong planner/reviewer contract graph, progressive

- duration: approximately 2 hours 33 minutes;
- official end-to-end result: 8/90 passed, 82/90 failed;
- basic: 6/30; medium: 2/30; hard: 0/30;
- 315 supervisor requests, 1,029 RWKV model requests, 223 actions, and 345
  protocol rejections;
- external result verifier passed 11 cases, but only 8 reached agent completion.

The strong run is also materially contaminated by supervisor transport faults:

- 57 `supervisor_call_failed` events across 55 cases;
- HTTP 500 during contract plan: 17;
- HTTP 403 during contract plan: 33;
- HTTP 403 during contract review: 6;
- one non-transport contract-schema ValueError.

A single-concurrency M11 canary after the full run immediately reproduced HTTP
403 at `contract_plan`, proving the 403 state persists and is not caused by
case concurrency 8. The official denominator remains 90. A post-hoc diagnostic
over the 35 cases without a supervisor-call failure is 8/35 (22.9%); this is
not a substitute official score.

## Engineering regression result

- full local suite: 291/291 passed in 60.25 seconds;
- `git diff --check`: passed;
- real progressive `ModelSession` smoke: passed;
- tuned vLLM health: 200, zero restarts;
- engineering-only lease fencing, recovery, evidence truncation, deterministic
  evaluator boundaries, and HTTP lifecycle fixes remain code/test regressions
  and are not labeled as state wins.

## Required next work

### Engineering before repeating strong E2E

1. Restore/fix the strong-model API authorization or quota causing persistent
   HTTP 403. Validate with one contract-plan canary before any full rerun.
2. Retry transient 5xx with bounded backoff, but fail fast and expose a precise
   diagnostic for non-retryable 403. Do not hide 403 behind generic interrupted.
3. Resume only the 55 transport-failed case artifacts after the API is healthy;
   preserve the 35 transport-eligible results and the official original run.
4. Report supervisor transport availability separately from planner/RWKV
   behavioral scores.
5. Preserve the new vLLM config parsing and request-level state attestation
   gates for every subsequent deployment.

### State-tuning Round2 entry gate

Do not start with another broad 2K or 10K corpus. First run a small preregistered
ablation with fixed deterministic/near-deterministic canaries:

1. 400-600 high-signal selector-stage samples whose only correct outer function
   is `select_tool`; hard negatives are the observed direct calls
   (`list_directory`, `read_file`, `read_json`, `connector_lookup`).
2. 200-300 observation-to-completion/no-progress transitions that explicitly
   cover “external result already correct, now finalize” and “do not repeat the
   same low-information action”.
3. A small connector-vs-web and privacy-Gate slice; do not mix engineering
   transport failures into model labels.
4. Compare zero-state vs step-2000 continuation and short/higher-LR vs
   longer/current-LR schedules. Repository history shows both approximately
   1,848 steps at `5e-5` and 11K steps at `2e-5`; the current zero-state 2K at
   `2e-5` is not enough evidence to choose either explanation.
5. Require a causal state-effect canary before a full round: state-vs-baseline
   differences must exceed tuned-vs-tuned sampling noise and must rescue
   selector operation accuracy on a fixed holdout. A loadable checkpoint or a
   one-prompt chat smoke is not sufficient.

Only after this gate passes should the residual set be expanded and another
full route120/E2E90 cycle be run.
