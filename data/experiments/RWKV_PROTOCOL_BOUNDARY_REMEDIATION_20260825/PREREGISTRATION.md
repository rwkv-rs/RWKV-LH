# RWKV protocol-boundary remediation preregistration

- Date: 2026-08-25
- Source: code-review findings supplied by the user against the current
  `chase/hybrid-product-v1` working tree.
- Version: `rwkv-protocol-boundary-remediation.v1`
- Purpose: verify deterministic rollover visibility, exact external-evidence
  request binding, and complete `text_template` ordering/multiplicity semantics.
- Dataset: repository unit and integration fixtures only; no generated or
  externally sourced evaluation data is used.
- Generation method: hand-authored deterministic regression cases derived from
  the four reported failure scenarios.
- File summary: this directory contains the preregistered protocol and the
  post-run result record; implementation and fixtures remain in their normal
  source/test paths.

## Fixed evaluation protocol

1. Run focused tests for model session/controller rollover, retrieval harness and
   kernel, and typed contract evaluation.
2. Run the complete repository test suite with pytest capture disabled.
3. Run `git diff --check` and compile the changed Python modules.

The registered comparison algorithm is exact structural equality of expected
events, digests, envelope bindings, verdict booleans and exception classes.
The acceptance threshold is `1.0`: every registered assertion and every full-suite
test must pass; no partial credit, subjective similarity or post-run threshold
change is permitted.

## Registered edge cases

- A progressive retry whose rejection event itself triggers rollover.
- Prompt and native-state rollover retaining exact rejection error, rejected
  arguments and selected operation.
- An internally valid route envelope placed under another request digest.
- Execute and recovery backends returning an envelope for different arguments.
- Ordered templates with zero or multiple sort keys.
- Unordered templates whose values are prefixes/substrings of one another.
- Duplicate template rows requiring distinct non-overlapping occurrences.
