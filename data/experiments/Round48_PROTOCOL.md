# Round48 Preregistered Protocol: No-op Causal Lineage Passthrough

## Frozen evidence

Round47 canary failed its gate because `E2E-B12` remained an agent-completed,
external-failed false positive. Its exact event chain was serial, so the
Round47 same-frontier invalidation path did not run.

In this `B12` sample, T1 observed all input integers and T2 correctly wrote the
requested statistics. T3 then selected `noop` and emitted only
`T3: stats.json verified`. T4's action capsule contained only that direct noop
output and explicitly excluded T1's source observation and T2's correct
post-action snapshot. RWKV then guessed wrong values and overwrote the correct
file.

The Round47 scheduler candidate is reverted before this round. Round48 starts
from the Round46 interface and changes only working-memory dependency lineage.
The Round46 wire-format converter remains syntax-only and is not modified.

## One architecture change

Treat a completed `noop` dependency as provenance-transparent:

1. Always include the direct dependency's latest output projection, unchanged.
2. If and only if that dependency's committed Harness action is exactly
   `noop`, recursively include the latest output projections of its declared
   dependencies.
3. Continue recursively through consecutive noop dependencies, stop at the
   first non-noop producer on each branch, deduplicate by memory ID, and keep a
   deterministic dependency/insertion order.
4. Pack the resulting observations under the existing fixed dependency token
   budget. Do not increase the context window or add a model request.
5. Apply the same dependency projection to action commitment, Task semantic
   commitment, recovery, and the general working-memory builder so all phases
   see one causal protocol.

This repairs dataflow only: a no-op produces no artifact or transformed value,
so it cannot replace the factual observations on which its descendants depend.

## Explicit non-cheating boundaries

- The projection does not inspect Task titles, descriptions, postconditions,
  benchmark IDs, expected answers, output correctness, or verifier results.
- It does not compute, compare, rank, filter, rewrite, or choose any semantic
  value, action, Task decision, Goal decision, or final answer.
- Every exposed byte already exists in an auditable output projection owned by
  a declared dependency ancestor.
- Non-noop dependencies remain direct-only; arbitrary historical or unrelated
  memory is not exposed.
- `noop` output remains visible and is not replaced; ancestor observations are
  appended with their original memory IDs and producer identities.
- The existing token budget, truncation algorithm, prompt templates, sampling,
  tools, validation, and acceptance remain frozen.
- The format conversion layer remains limited to registered wire syntax and a
  single canonical internal protocol; it has no role in this change.

## Frozen validation

Offline:

- full pytest;
- LH-Control `30/30`;
- E2E catalog `90/90`;
- one noop passes through one factual producer;
- consecutive noops pass through to the nearest non-noop producers;
- branching lineage is deterministic and deduplicated;
- a non-noop direct dependency does not expose its own ancestors;
- unrelated Tasks and explicit-but-undeclared snapshots remain excluded;
- cycles or missing legacy dependencies terminate safely;
- dependency token budget remains unchanged;
- action, Task-validation, recovery, and general capsules select the same
  lineage;
- the 31-file parallel read/per-file summary/aggregate regression remains
  complete and retains a parallel read frontier of at least two.

Fixed canary set (the runner's canonical catalog order is authoritative):

`E2E-B06`, `B08`, `B11`, `B12`, `B18`, `B21`, `B25`, `B26`, `B27`, `B29`.

Run Basic30 only if:

- `B12` is Strict PASS;
- FP among `B12/B29` is `0`;
- at least `2/3` of `B21/B25/B26` are Strict;
- `B27` remains correctly blocked;
- at least `3/4` of `B06/B08/B11/B18` are Strict;
- B12 T4's capsule audibly contains T2's unchanged real observation when the
  direct dependency is a noop;
- the large-code architecture regression passes.

## Retain and upload gate

Retain/upload eligibility requires Basic30 Strict greater than `23/30`, FP `0`,
FN at most `1`, complete offline regression, no large-code regression, and
byte-exact preservation of every raw final RWKV output. Dataset, selected case
set, runner ordering, metrics, similarity implementation, sampling, and
thresholds are frozen before code changes.
