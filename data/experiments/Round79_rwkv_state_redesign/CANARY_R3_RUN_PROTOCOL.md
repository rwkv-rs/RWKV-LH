# Round79 unified lane short7 r3 protocol

Preregistered: 2026-08-14, before r3 execution.

## Reason for a new run

The preserved r2 canary showed a systemic input regression: the inline empty
`function/params` exemplar made six of seven first Tasks self-dependent, while
the authoritative Task schema had never defined `after` semantics. r3 removes
that exemplar, expresses field roles in natural G1i prose, and makes Task
dependency semantics explicit in the one schema. No output is repaired or
resampled.

## Fixed inputs

- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Dataset/evaluator: unchanged immutable `RWKV-E2E-90` catalog and hidden acceptance
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
  --output data/experiments/Round79_rwkv_state_redesign_canary_r3
```

## Unchanged gate

Proceed to full90 only if all are true:

- Strict at least `4/7`;
- B01, B02 and B10 are all Strict;
- false positives at most 1;
- false negatives at most 1;
- no model call uses a legacy role/dialect or semantic format resampling;
- chunk cases have exact source coverage and explicit-only child merge.

Preserve every prompt, raw output, checkpoint, event, source manifest and
earliest-error analysis. Do not alter parameters, evaluator or gate after r3.
