# Round46 Preregistered Protocol: Decision-Last Task Commit with Exact Format Normalization

## Frozen evidence

Active code is restored Round41. Round45 canary produced Strict `7/10`, recovered all `B21/B25/B26` verification chains, but had FP `B27/B29` and was rejected before Basic30.

In `B27`, the first RWKV Task-commit response was semantically correct:

```json
{
  "reason": "...service.conf ... contains protocol=v1...the task is not complete.",
  "decision": "replan"
}
```

It omitted only the constant `schema_version`. The current boundary rejected it and resampled. The second RWKV response changed the decision to the wrong `pass`, which downstream Goal completion amplified.

## One integrated interface change

The Task-commit boundary is registered end to end:

1. Use Round45's compact instruction: RWKV owns Task semantic verification, complete observation actions are evidence it must judge, and reason is generated before decision.
2. Register one additional common wire form only for `long-horizon.task-commit.v1`: an object whose keys are exactly `reason` and `decision`, with no `schema_version`.
3. The format converter inserts only `schema_version="long-horizon.task-commit.v1"` and retains `reason` and `decision` byte-for-byte/value-for-value.
4. Any missing-schema object with an extra/missing semantic key remains unchanged and is rejected by the existing canonical validator.
5. Raw and normalized payloads, digests, transformation name, and normalizer version are audited. No second model sample occurs when this exact form normalizes successfully.

This is one model-boundary contract: the prompt elicits reason-before-decision and the converter accepts the registered common serialization without replacing the emitted semantic decision.

## Explicit non-cheating boundaries

- The converter does not inspect reason text, action results, Task text, paths, values, or benchmark data.
- It does not select, infer, replace, or validate `decision` or `reason`.
- It adds only a constant protocol-format tag; no task, criterion, action, expected value, answer, or acceptance field is generated.
- Unknown schema spellings and all unregistered missing-schema shapes remain fail-closed.
- The Controller continues to obey RWKV's emitted decision and never interprets its reason.
- No Goal rule, extra verifier, model call, tool, or external service is added.
- Tool-call normalization remains unchanged and continues to support only its existing registered common envelopes.

## Frozen validation and gates

Offline:

- full pytest;
- LH-Control `30/30`;
- E2E catalog `90/90`;
- exact tests for missing-schema Task commit, extra/missing fields, other protocol types, raw immutability, audit trace/digests, no resampling, and unchanged reason/decision;
- existing format aliases and malicious-field regressions.

Fixed canary:

`E2E-B04`, `B06`, `B08`, `B11`, `B18`, `B21`, `B25`, `B26`, `B27`, `B29`.

Run Basic30 only if:

- FP among `B04/B27/B29` is at most `1`;
- at least `2/3` of `B21/B25/B26` are Strict;
- at least `3/4` of `B06/B08/B11/B18` are Strict;
- a normalized missing-schema response causes exactly one Task-commit model request.

Retain/upload eligibility requires Basic30 Strict greater than `17/30`, FP at most `1`, FN at most `7`, complete offline regression, and raw final RWKV output unchanged. Evaluation data, order, metrics, similarity implementation, sampling, and thresholds are frozen before execution.
