# Identical successful-observation loop guard v1 protocol — 2026-08-26

## Root cause under test

Direct mode records a stable observation fingerprint and repeat count for successful
actions, but only repeated failed observations consume a terminal budget. A model can
therefore execute a byte-identical read-only action until the global transition budget
is exhausted.

## Single variable

For an idempotent, read-only action whose exact observation fingerprint repeats three
times while the workspace digest remains unchanged, stop accepting more work actions
and enter the existing terminal-answer path with reason
`identical_success_budget_exhausted`. Do not rewrite, infer, or repair the model's
arguments or final answer.

## Frozen checks and thresholds

- Two identical successful observations remain allowed and both repeat counts remain
  visible to RWKV.
- A third identical successful read-only observation enters the terminal path before a
  fourth work action can execute.
- Different output, different arguments that change the exact observation, workspace
  change, failure handling, and mutating actions retain existing behavior.
- Targeted controller tests and the full regression suite must pass.
