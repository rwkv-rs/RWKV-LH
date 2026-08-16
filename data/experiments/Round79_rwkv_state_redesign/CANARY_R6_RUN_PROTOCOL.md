# Round79 unified lane short7 r6 protocol

Preregistered: 2026-08-14, before r6 execution.

## Reason for a new run

r5 proved locked selection/binding but exposed a single missing next-role stop:
all seven valid binding JSON objects continued into a generated `System: Tools`
segment. r6 adds that role boundary and returns evidence-disproved Task finish
claims to their original Task lane as typed events. It does not normalize a
candidate, retry a format failure, or change a committed operation.

## Fixed inputs

- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Dataset/evaluator: unchanged immutable `RWKV-E2E-90` catalog and hidden acceptance
- Cases: `E2E-B01`, `E2E-B02`, `E2E-B10`, `E2E-M01`, `E2E-M03`, `E2E-M06`, `E2E-M12`
- Maximum transitions: 200
- Case process concurrency: 7
- Semantic sampling: temperature 0.05, top-p 1.0, top-k 0, zero format/semantic resampling
- Similarity/acceptance algorithm: unchanged dataset evaluator

Command:

```bash
uv run rwkv-lh-e2e --suite all \
  --case E2E-B01 --case E2E-B02 --case E2E-B10 \
  --case E2E-M01 --case E2E-M03 --case E2E-M06 --case E2E-M12 \
  --max-transitions 200 --concurrency 7 \
  --output data/experiments/Round79_rwkv_state_redesign_canary_r6
```

## Unchanged gate

Proceed to full90 only if all are true:

- Strict at least `4/7`;
- B01, B02 and B10 are all Strict;
- false positives at most 1;
- false negatives at most 1;
- no legacy role/dialect or semantic format resampling;
- chunk cases have exact source coverage and explicit-only child merge.

Preserve all prompts, raw candidates, checkpoints, events, source manifest and
earliest-error analysis. Do not change parameters, evaluator or gate after r6.
