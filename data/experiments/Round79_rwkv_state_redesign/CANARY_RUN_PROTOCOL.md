# Round79 unified lane short7 protocol

Preregistered: 2026-08-14, before execution.

## Fixed inputs

- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Dataset/evaluator: existing immutable `RWKV-E2E-90` catalog and hidden acceptance loaded by `rwkv-lh-e2e`
- Cases: `E2E-B01`, `E2E-B02`, `E2E-B10`, `E2E-M01`, `E2E-M03`, `E2E-M06`, `E2E-M12`
- Maximum transitions: 200
- Case process concurrency: 7
- Semantic sampling: unified fixed lane policy in source; no format resampling
- Similarity/acceptance algorithm: unchanged evaluator registered by the dataset; no post-run threshold changes

Command:

```bash
uv run rwkv-lh-e2e --suite all \
  --case E2E-B01 --case E2E-B02 --case E2E-B10 \
  --case E2E-M01 --case E2E-M03 --case E2E-M06 --case E2E-M12 \
  --max-transitions 200 --concurrency 7 \
  --output data/experiments/Round79_rwkv_state_redesign_canary
```

## Gate

Proceed to full90 only if all are true:

- Strict at least `4/7`;
- B01, B02 and B10 are all Strict;
- false positives at most 1;
- false negatives at most 1;
- no model call uses a legacy role/dialect or semantic format resampling;
- chunk cases have exact source coverage and explicit-only child merge.

Regardless of score, preserve all prompts, raw outputs, checkpoints, events, source manifest and earliest-error analysis. Do not alter the evaluator after observing results.
