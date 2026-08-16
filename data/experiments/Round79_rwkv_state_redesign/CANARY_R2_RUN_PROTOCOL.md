# Round79 unified lane short7 r2 protocol

Preregistered: 2026-08-14, before r2 execution.

## Reason for a new run

The preserved first canary stopped all seven cases at the initial Goal parser.
Four raw candidates already used G1i `function/params`, but the implementation
incorrectly required its internal `name/arguments` persistence shape. The only
architecture change entering r2 is the corrected, explicit
`function/params` model wire boundary and its regression coverage. This is a new
experiment, not a resample of any failed semantic decision.

## Fixed inputs

- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Dataset/evaluator: unchanged immutable `RWKV-E2E-90` catalog and existing hidden acceptance
- Cases: `E2E-B01`, `E2E-B02`, `E2E-B10`, `E2E-M01`, `E2E-M03`, `E2E-M06`, `E2E-M12`
- Maximum transitions: 200
- Case process concurrency: 7
- Semantic sampling: temperature 0.05, top-p 1.0, top-k 0, zero semantic format resampling
- Similarity/acceptance algorithm: unchanged dataset evaluator

Command:

```bash
uv run rwkv-lh-e2e --suite all \
  --case E2E-B01 --case E2E-B02 --case E2E-B10 \
  --case E2E-M01 --case E2E-M03 --case E2E-M06 --case E2E-M12 \
  --max-transitions 200 --concurrency 7 \
  --output data/experiments/Round79_rwkv_state_redesign_canary_r2
```

## Unchanged gate

Proceed to full90 only if all are true:

- Strict at least `4/7`;
- B01, B02 and B10 are all Strict;
- false positives at most 1;
- false negatives at most 1;
- no model call uses a legacy role/dialect or semantic format resampling;
- chunk cases have exact source coverage and explicit-only child merge.

Regardless of score, preserve all prompts, raw outputs, checkpoints, events,
source manifest and earliest-error analysis. Do not modify parameters, the
evaluator or this gate after observing r2.
