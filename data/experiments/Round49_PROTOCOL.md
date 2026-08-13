# Round49 Preregistered Protocol: Authoritative Observation-Driven Frontiers

## Frozen multi-case evidence

Round47 and Round48 supplied two different sampled plans for the same fixed
cases, but their failure chains share one protocol contradiction: planning text
says “only the next executable causal frontier,” while the accepted Task-batch
grammar permits arbitrary local dependency chains whose downstream inputs have
not been observed.

- `B12` Round47 preplanned read → parse → compute → write → verify. A correct
  early write was later overwritten by a downstream Task whose direct factual
  input had been replaced by shallow control text.
- `B08` preplanned compute/write plus a separate verify Task. Production was
  externally correct, but the later verifier selected/reselected incompatible
  reads and blocked.
- `B26` preplanned three correct writes plus a verify Task. The final Task kept
  selecting a mutating write instead of observing the already-correct file set.
- `B27` preplanned replacement, two verification Tasks, and a final write. The
  final Task reconstructed stale partial content and reintroduced bad values.
- `B29` preplanned copy, manifest, and two verify Tasks. Verification selected
  another mutation and never compared the unequal source/backup observations.

Round47's scheduler and Round48's noop-lineage candidates are reverted. The
starting code is the Round46 interface with offline `364/364`. The format
converter remains syntax-only and is not changed.

## One architecture change

Make the existing observation-driven planning contract authoritative:

1. An initial Task batch may contain only Tasks immediately executable from the
   current persisted state. It may not contain a dependency on another local ID
   in the same response.
2. A Goal-obligation extension may depend on active completed existing Tasks,
   but never on another new local ID in that response.
3. A failure replan follows the same rule: propose only the immediately
   executable replacement frontier, not a speculative downstream chain.
4. After that frontier executes and its real action observations are persisted,
   the existing Goal-obligation loop asks RWKV for the next frontier if Goal
   evidence is still unresolved.
5. Retain up to eight independent ready Tasks, parallel isolated RWKV action
   proposals, and parallel Harness-declared read-only execution. Large project
   file reads therefore remain parallel; only unobserved future stages are
   delayed.
6. Both the LongHorizonModel protocol validator and Controller proposal trust
   boundary reject a batch containing non-ready local-chain Tasks. The whole
   batch fails closed; the Controller never deletes or partially accepts Tasks.

Across successive accepted batches, the persistent TaskGraph still records all
dependencies and full history. This removes speculative future commitments, not
long-horizon state.

## Explicit non-cheating boundaries

- The rule uses only Task IDs, declared dependency edges, active/completed
  status, and batch generation identity.
- It does not inspect titles, descriptions, postconditions, paths, content,
  benchmark IDs, answers, verifier outcomes, or whether a Task would be useful.
- It never creates, edits, orders, ranks, filters, or completes a Task. A batch
  is accepted whole or rejected whole; RWKV must return a new batch.
- It never selects tools, arguments, values, Task decisions, Goal decisions, or
  final output.
- No external verifier, answer comparison, hidden acceptance, extra model, or
  service enters the Agent loop.
- Wire-format normalization retains its sole role: registered common syntax to
  one canonical internal representation with semantic values unchanged.

## Frozen offline validation

- full pytest;
- LH-Control `30/30`;
- E2E catalog `90/90`;
- initial local dependency chain rejected and retried without mutation;
- obligation local dependency chain rejected and retried;
- replan local dependency chain rejected and retried;
- existing completed dependencies accepted;
- unknown, inactive, failed, or pending existing dependencies rejected;
- up to eight independent Tasks accepted; nine rejected;
- Controller trust boundary rejects a custom-model chained proposal as a whole;
- persisted graph across successive frontier generations retains stable global
  IDs and dependencies;
- independent read-only Tasks still materialize and execute concurrently;
- the 31-file project test completes discovery, parallel read batches,
  per-file summaries, and final aggregation, with maximum newly proposed local
  dependency depth zero and an observed read frontier of at least two.

## Fixed real canary

The runner's canonical catalog order is authoritative:

`E2E-B06`, `B08`, `B11`, `B12`, `B18`, `B21`, `B25`, `B26`, `B27`, `B29`.

Run Basic30 only if:

- every accepted real Task batch has local dependency depth zero;
- at least `3/4` of `B06/B08/B11/B18` are Strict;
- at least `2/3` of `B21/B25/B26` are Strict;
- FP among `B12/B27/B29` is at most `1`;
- at least `2/3` of `B12/B27/B29` are either Strict or correctly blocked;
- the 31-file architecture regression passes.

## Retain and upload gate

Retain/upload eligibility requires Basic30 Strict greater than Round46's
`23/30`, FP at most `1`, FN at most `1`, complete offline regression, no
large-code regression, and byte-exact preservation of raw RWKV final outputs.
Dataset, selected set, canonical runner order, metrics, similarity
implementation, sampling, and thresholds are frozen before code changes.
