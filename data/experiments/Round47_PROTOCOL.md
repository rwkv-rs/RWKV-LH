# Round47 Preregistered Protocol: Same-Frontier Stale Action Invalidation

## Frozen evidence

Round46 Basic30 produced Strict `23/30`, external acceptance `23/30`, agent
completion `25/30`, FP `2`, and FN `0`. It is not upload-eligible because its
preregistered FP ceiling was `1`.

`E2E-B12` exposed a scheduler defect independent of RWKV answer quality. Two
ready Tasks selected actions from the same isolated state snapshot. Both later
targeted `stats.json`: T1 selected the correct write and T2 selected an
incorrect write. The Harness serialized side effects, but the Controller kept
T2's already-materialized action after T1 changed the target. T2 therefore
overwrote T1 using a decision made against stale state.

Round46's compact Task-commit contract and exact registered wire-format
normalization are the starting interface for this round. The format converter
continues to perform only syntax-level conversion to the one internal protocol;
it has no role in concurrency, semantic validation, answer selection, or Goal
acceptance.

## One architecture change

Add optimistic-concurrency invalidation at the ready-frontier scheduler:

1. Record which unresolved actions were newly materialized from one isolated
   frontier snapshot.
2. If the first serially executed action is Harness-declared as a side effect,
   compare its declared target with only the later actions newly materialized
   from that same snapshot.
3. For an overlapping target, discard the not-yet-executed stale action and its
   action-local completion criteria, restore the Task to `model_action`, and
   persist a complete invalidation event.
4. On the next Controller transition, ask RWKV to select a fresh action from the
   new persisted state. The Controller does not select or edit the replacement.
5. Do not invalidate preconfigured actions, actions materialized in an earlier
   transition, or disjoint targets. Preserve concurrent execution of independent
   Harness-declared read-only actions.

Target comparison is mechanical workspace-path identity. Invalidation applies
whether the preceding side-effect attempt reports success or failure because an
unknown/partial side effect can still change the target.

## Explicit non-cheating boundaries

- No action argument, file content, expected value, answer, Task decision, or
  Goal decision is inferred or rewritten.
- The discarded action is never converted into another concrete action. Only
  RWKV may produce its replacement in a later request.
- The scheduler does not inspect benchmark identifiers, natural-language Task
  text, action output, verifier results, or whether an answer is correct.
- Conflict detection uses only action metadata already required for safe
  scheduling: Harness side-effect declaration, materialization generation, and
  normalized target path.
- No deterministic content comparison, answer filter, external verifier, extra
  model, or service is introduced.
- The Round46 format converter remains limited to registered common wire forms
  and one canonical downstream protocol; it is not extended in this round.

## Frozen validation

Offline regression:

- full pytest;
- LH-Control catalog `30/30`;
- E2E catalog `90/90`;
- same-target write/write invalidation;
- write/read invalidation on the same target;
- disjoint actions remain materialized;
- preconfigured actions are not invalidated;
- failed/unknown side effects still invalidate a same-snapshot conflict;
- invalidation event and checkpoint serialization preserve the discarded raw
  action and state transition without selecting a replacement;
- the 31-file project fan-out test still performs parallel read batches and
  completes per-file summaries before aggregation.

Fixed canary, in frozen order:

`E2E-B12`, `B29`, `B21`, `B25`, `B26`, `B27`, `B06`, `B08`, `B11`, `B18`.

Run Basic30 only if:

- `B12` is not a false positive;
- FP among `B12/B29` is at most `1`;
- at least `2/3` of `B21/B25/B26` are Strict;
- `B27` remains correctly blocked;
- at least `3/4` of `B06/B08/B11/B18` are Strict;
- the large-code parallel-summary architecture test passes.

## Retain and upload gate

Retain/upload eligibility requires all of the following:

- Basic30 Strict greater than Round46's `23/30`;
- FP at most `1` and FN at most `1`;
- `B12` is not a false positive;
- no regression in the fixed controls or large-code parallel-summary path;
- complete offline regression;
- raw final RWKV outputs and all semantic fields remain unchanged by
  infrastructure.

Evaluation data, order, sampling parameters, metrics, similarity
implementation, thresholds, and the fixed canary are frozen before code changes.
