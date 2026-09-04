# Round69 preregistered protocol: review projections and typed schema echoes

## Frozen evidence

- Uploaded full90 baseline remains Round46 Strict `31/90`, External `32/90`,
  Agent `55/90`, FP `24`, FN `1`.
- Round68 offline: pytest `423/423`, LH-Control `30/30`, frozen subset `5/5`.
- Round68 fixed15: Strict `0/15`; 14 run-creation failures and one pre-action
  block. Manual source:
  `data/experiments/Round68_canary/MANUAL_CAUSAL_ANALYSIS.md`.

## Preregistered changes

### 1. Closed review-schema normalization

At the uniquely fixed Goal-audit boundary, register only
`long-horizon.goal-proposal.v1` and `audit.v1` as aliases of
`long-horizon.goal-audit.v1`. At the uniquely fixed action-review boundary,
register only `rwkv-lh.task-action-ledger.v1` as an alias of
`long-horizon.action-review.v1`.

Normalization changes only the schema string. Raw and normalized payloads and
digests are audited. Unknown schemas, unknown fields and invalid semantic values
remain rejected. No decision or reason is changed.

### 2. Semantic Goal review projection

Goal audit and finalization receive the draft as exactly objective, constraints
and ordered observable-outcome descriptions. Proposal schema, criterion ids and
the `required` transport flag are omitted from the review projection so they
cannot be mistaken for user requirements. The complete raw draft remains in the
out-of-run model audit, and the final accepted Goal is still a fresh full RWKV
proposal.

Prompts explicitly state that exact literal mappings, values, field names and
formats present in the immutable request must not be generalized or removed by
an audit. The audit is advisory; final semantics remain RWKV-generated.

### 3. Task-local action review

Action review judges only whether the proposed call is executable now and
whether its immediate observable effect establishes or advances the exact active
Task postcondition. The future Goal may clarify provenance but may not add later
Tasks/effects to this atomic review. A correct discovery/read Task must not be
rejected because it does not perform a downstream write.

## Non-intervention boundary

No Goal field, action, argument, evidence decision or final answer is inserted,
removed or rewritten by controller code. The changes are a closed wire-schema
mapping and a deterministic projection of already RWKV-generated fields. Hidden
acceptance and frozen reference answers remain unavailable during generation.

## Frozen validation and gate

- Full pytest, clean LH-Control `30/30`, frozen subset `5/5`, compilation and
  diff check.
- Add exact alias audit tests, unknown-schema rejection tests, semantic Goal
  projection tests and Task-local action-review prompt tests.
- Run unchanged fixed15.
- Run full90 only at Strict >= `6/15`, FP <= `3`, FN <= `1`, with B01/B02/B10
  Strict.
- Upload only if full90 Strict > `31/90`, FP <= `24`, FN <= `1`, and all offline
  gates pass.

Efficiency remains audit-only.
