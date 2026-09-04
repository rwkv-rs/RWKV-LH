# S53 runtime metadata parity R2 preregistration

Frozen before the R2 real-Harness rerun on 2026-08-29 (Asia/Shanghai).

## Root-cause evidence

- The first `E2E-H10` S53 real Selector logits are byte-identical to the frozen
  S52-prefix evaluation.
- After the successful first `list_directory`, the frozen long-chain prefix
  contains `complete=true,truncated=false`, while the current Harness result
  metadata contains only `truncated=false`.
- The independent Selector receives no result body. This missing bounded
  completion field is therefore the first observable input-shape divergence;
  subsequent persistent logits and the tool sequence diverge.
- The defect is global to every non-truncated `list_directory` result. It is
  not an `E2E-H10` condition and no task ID, path, expected answer, or verifier
  content may enter the implementation.

## Frozen correction

`ActionHarness._list_directory` adds `metadata.complete = not
metadata.truncated`. The existing result `output` bytes, action semantics,
Selector menu, S53 MLP parameters, Selector zero state, Executor G3 state,
sampling parameters and evaluation cases remain unchanged. RWKV raw output is
never rewritten, removed, reordered, retried invisibly, or used to alter the
selected tool.

## Fixed R2 evaluation

- Models/states: `SEL-Z0-S53` plus `EXE-G3-MULTISTAGE-STEP2000`.
- Device: local 2.9B Selector on physical GPU0 and remote 13.3B Executor on
  physical GPU0; existing product Executor port 18070 must remain healthy.
- Canary IDs, in frozen order: `E2E-B01`, `E2E-B02`, `E2E-B10`, `E2E-M03`,
  `E2E-M12`, `E2E-H10`.
- Sampling: one attempt, temperature 0.1, top-p 1.0, top-k 0; raw first output.
- Release gate: exactly 6/6 strict pass; current-architecture integrity valid;
  every generation input is request-last or exact protocol-rejection-last;
  raw-output modified/deleted count is zero.
- Only after that gate passes: live-network 2/2, retrieval-quality 9/9 hard
  gates, Full90 90/90 dispatch and integrity, with only `E2E-LH09/mock_api`
  allowed as an explicit unsupported operation.

If the fixed canary remains below 6/6, this correction is retained as the
metadata root fix but is insufficient for release. The next experiment must
use a disjoint, general multi-stage Selector dataset; the canary must not be
added to training and the gate must not be weakened.
