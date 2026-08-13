# Interrupted diagnostic: recorder defect

This directory's first diagnostic attempt is invalid and must not be used for concurrency
comparison.

## What happened

After the excluded warm-up and all 30 concurrency-1 cases returned, the runner printed:

```json
{"total":30,"valid_goal":28,"invalid_goal":2,"model_requests":32,"model_returns":32,"transport_failures":0,"error_counts":{"AttributeError: 'TempDecision' object has no attribute 'to_dict'":28,"ModelProtocolError: goal proposal has 8 criteria; maximum is 5":1,"ModelProtocolError: goal proposal has 9 criteria; maximum is 5":1}}
```

The 28 apparent `valid_goal` cases had actually passed `LongHorizonModel.parse_goal`; the diagnostic
runner then called a nonexistent `TempDecision.to_dict()` method. Because it assigned the success
label before that call, its in-memory row simultaneously said valid and contained an AttributeError.
This is a diagnostic-recorder defect, not an RWKV error.

The main process had begun the concurrency-2 phase when it was manually interrupted to avoid
collecting more unusable rows. The original runner wrote its aggregate only at normal process exit,
so no `results.json` or raw trace survived this interruption. The terminal output above is the only
recoverable aggregate. The exact concurrency-2 partial request count is unknown.

## Resolution and non-selection statement

No model response was chosen, repaired, rescored or reused. The attempt is excluded in full rather
than retaining the favorable concurrency-1 rows. The replacement runner:

- serializes `TempDecision` with `dataclasses.asdict`;
- assigns `valid_goal` only after serialization succeeds;
- fsyncs each prompt/raw/parser event to per-case JSONL as it occurs;
- atomically writes every case result immediately;
- refuses to overwrite an existing output directory.

The replacement run uses a new directory and a new pre-registration. Repetition is necessary to
repair missing instrumentation, not to improve or select RWKV answers.

