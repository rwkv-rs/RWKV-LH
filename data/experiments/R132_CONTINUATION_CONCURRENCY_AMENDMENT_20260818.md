# R132 program continuation — concurrency amendment

**Recorded:** 2026-08-18, before issuing any continuation-run model request.

## Owner directive

Continue the program through R132. The forwarding path has been changed to support high concurrency,
and its concurrency experiment has already been completed. Use that evidence to finish the paused
run before proceeding to the remaining program decisions.

## Evidence available before the run

- `G1I_CONCURRENCY_STABILITY_20260818_round130_pause.json` measured sustained concurrency **32**:
  160/160 successful requests, 0 failures, success rate 1.0.
- The transparent SSH forward was reconstructed with the same endpoint mapping used by the frozen
  protocols. `/v1/models` returned `rwkv7-g1i-13.3b-20260805-ctx16384`, and a real completion request
  returned a valid OpenAI-compatible response before the continuation run.
- `Round130_source_manifest.json --check` passed with 49 checked entries and 0 mismatches.
- Offline gates passed: 114 tests, compileall clean, RWKV-E2E catalog valid at 90/90.

## Continuation decision

The earlier `Round130_order_ensemble_full90` directory was a **paused 61/90 attempt** and is not
scored as the official Round130 result. The owner subsequently directed that this partial directory
be deleted after its identity (`concurrency=5`, 61 results) and separation from the active output were
verified. The benchmark runner has no in-place result resume and mixing the old case concurrency with
a new value would weaken reproducibility. Therefore the valid continuation is a fresh source-frozen
full-90:

- output: `data/experiments/Round130_order_ensemble_full90_concurrency10`
- case concurrency: **10**
- K=3 physical candidate requests per active decision
- maximum simultaneous model requests: **30**, below the demonstrated stable limit of 32
- model, source, suite, sampling, max transitions, scoring, thresholds, and all red lines remain
  unchanged from `Round130_ORDER_SHUFFLED_SELF_CONSISTENCY_PROTOCOL.md`

The concurrency change is transport scheduling only. It does not alter prompt bytes, model sampling
parameters, candidate aggregation, external acceptance, or scoring. Model protocol errors, timeouts,
interrupted cases, and wrong answers remain valid outcomes; only an auditable forwarding or endpoint
failure may invalidate the run.

After the full-90, apply the original Round130 KEEP/REVERT gates and update the R132 ingredient ledger.

## Concurrency-10 infrastructure verdict

The concurrency-10 continuation was stopped at 32/90 and marked **INVALID** before any score was
used. Four case audits contain `model_transport_failure`; E2E-LH05 accumulated 16
`RWKVOutcomeUnknownError` events caused by HTTP `ReadTimeout` and terminated with status `failed`.
The SSH unit remained active with `NRestarts=0`, so the failure boundary is the heavy E2E HTTP request
load, not a tunnel-process restart. The concurrency-32 diagnostic used only 96 output tokens and did
not represent growing long-horizon prompts with 1400/1800-token generation limits.

Before issuing the successor run's first model request, the continuation setting is therefore frozen
back to the original Round130 **case concurrency 5** (at most 15 physical K=3 requests). All source,
model, sampling, suite, scoring, thresholds, and red lines remain unchanged. The invalid artifacts are
preserved at `Round130_order_ensemble_INVALID_concurrency10_transport_timeout_32of90/`. The successor
output is `data/experiments/Round130_order_ensemble_full90_concurrency5_official`.
