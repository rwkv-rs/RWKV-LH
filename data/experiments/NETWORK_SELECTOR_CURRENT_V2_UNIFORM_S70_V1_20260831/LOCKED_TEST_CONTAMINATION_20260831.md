# S70 locked-test contamination record

Date: 2026-08-31 (Asia/Shanghai)

## Event

After the preregistered S70 zero and all four numbered state candidates had
already failed the frozen dev gate, a local field-structure inspection parsed
the first S70 `test` JSON row.  The command printed its field names and row
metadata, including its label and requirement.  No model forward, head
training, metric calculation, candidate selection, or source edit used that
row.

The earlier S70 run records remain truthful for their own executions: every
feature/head runner skipped all 500 test rows before JSON parsing and the dev
comparison selected no candidate.  This later inspection nevertheless means
the S70 locked split is no longer blind for any future experiment.

## Disposition

- S70 remains rejected solely by its frozen dev result SHA-256
  `0e90ae8fdbb7e9b76e2f1559624dd6abe533bbed4008f9cf3b5ef742db4cf6bc`.
- The complete S70 locked split is quarantined and must never be used for model,
  state, head, calibration, threshold, or release decisions.
- No S70 test file, row, label, hidden output, or result is deleted, modified,
  reordered, hidden, or replaced.
- A successor experiment must generate and seal a wholly new locked split
  before any feature extraction or training, then skip it before JSON parsing.
- S70's dev-only failure analysis remains valid because its runner parsed 500
  dev rows and skipped all 500 test rows before JSON parsing.

This record is additive audit evidence and must remain with the experiment.
