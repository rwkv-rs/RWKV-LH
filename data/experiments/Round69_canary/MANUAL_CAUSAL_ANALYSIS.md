# Round69 fixed-15 manual causal analysis

## Outcome

- Strict/External/Agent: `0/15`.
- All 15 cases failed before run creation.
- Eleven cases parsed a Goal draft and then exhausted Goal-audit retries.
- Four cases (`B10`, `B24`, `M18`, `H12`) produced a truncated/incomplete Goal
  draft before audit.

## Manual findings

The semantic Goal projection removed the Round68 schema-copy anchor exactly as
intended. It also exposed the deeper protocol defect: among parsed audit objects,
RWKV emitted schema versions `1.0` 25 times, `1.0.0` three times, numeric `2`
once, and null four times. The other five semantic audit fields remained present.

Therefore the failure is not another small alias omission. The weak model does
not treat an abstract review version tag as stable task information. Adding all
observed values to an alias table would create an open-ended coercion rule and
would repeat the same failure on the next spelling.

The four draft failures are separate: their full Goal object was truncated before
the new review path. They remain evidence for a later bounded Goal-construction
improvement, but they cannot be diagnosed through action/task layers in this run.

## Decision

Replace both review JSON envelopes with fixed G1i review tools whose arguments
contain only semantic decisions. The stage already fixes the review protocol, so
a model-generated schema tag carries no information. Exact bare arguments are
allowed only because one review tool is uniquely fixed and the raw form is fully
audited. This removes format burden without approving, editing or selecting a
semantic result.
