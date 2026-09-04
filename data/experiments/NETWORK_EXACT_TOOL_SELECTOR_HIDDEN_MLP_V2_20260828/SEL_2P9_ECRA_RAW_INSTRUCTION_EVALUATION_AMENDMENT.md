# Selector ECRA raw-instruction evaluation amendment

Date: 2026-08-28 (Asia/Shanghai)

## Correction

The ECRA120 `instruction` is a complete user task.  The target architecture is:

`user task -> strong Planner -> atomic stage objective -> 2.9B Selector -> 13.3B Executor`.

Therefore, passing the complete ECRA instruction directly as a Selector stage
objective incorrectly assigns Planner work to the Selector.  It is not a valid
unit gate for replacing the legacy tool-selection path.  Earlier immutable
raw-instruction ECRA artifacts remain useful distribution-shift diagnostics,
but their `gate_pass` value is not an integration decision for the target
pipeline.

This amendment does not alter, delete, hide, repair, constrain, or regenerate
any RWKV feature, logit, argmax, generated text, result file or earlier gate.

## Frozen legacy evidence

The complete historical direct-Harness run
`RWKV_STATE_TUNING_STAGE4_TO_STAGE6_V1_20260827/stage4_balanced_boundary/ecra_route120_B_child`
contains 120 real executions and records:

- first-tool exact: 100/120;
- local-only: 26/30;
- deterministic-compute: 15/15;
- public-web-required: 22/25;
- structured-connector: 11/20;
- mixed-local-online: 17/20;
- privacy-policy-rejection: 9/10.

The legacy route is not perfect, but its already-correct decisions are a
retention baseline rather than empty capability that a new Selector may discard.

## Correct evaluation layers

1. Selector unit quality uses frozen atomic stage objectives and the exact
   names/descriptions visible at selection time.  S20/S21's independent
   train/dev/test splits serve this layer.
2. Replacement quality is paired on the same frozen post-Planner handoff:
   compare the new Selector with legacy decisions only where the legacy route
   completed and selected the correct first tool.
3. Networking increment is measured separately on atomic external-observation
   stages: network vs defer, then `web_search` vs `connector_lookup`, with local
   false takeover and privacy egress both explicit.
4. ECRA120 remains the full-Harness regression: the strong Planner must first
   produce source-neutral atomic objectives, the Selector sees only those
   objectives plus descriptions, and the 13.3B Executor receives only the
   selected tool's schema and target.

No candidate is integrated until layers 2-4 use the real handoff and pass their
preregistered paired gates.  Direct ECRA raw-instruction scoring cannot be used
to tune a head or state.
