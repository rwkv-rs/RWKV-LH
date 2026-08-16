# Round79 unified lane short7 r4 protocol

Preregistered: 2026-08-14, before r4 execution.

## Reason for a new run

r3 passed Goal/Task-batch creation in all seven cases and exposed one common
child-lane transition defect: forked chunk workers repeated the parent
`lh_chunk_map` because the assignment did not explicitly scope the next
function. r4 adds typed next-function scope to child assignments, orders
concrete actions before lifecycle controls, and aligns chunk source declaration
with typed failure handling. No output correction or resampling is introduced.

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
  --output data/experiments/Round79_rwkv_state_redesign_canary_r4
```

## Unchanged gate

Proceed to full90 only if all are true:

- Strict at least `4/7`;
- B01, B02 and B10 are all Strict;
- false positives at most 1;
- false negatives at most 1;
- no model call uses a legacy role/dialect or semantic format resampling;
- chunk cases have exact source coverage and explicit-only child merge.

Preserve prompts, candidates, checkpoints, events, source manifest and
earliest-error analysis. Do not change parameters, evaluator or gate after r4.
