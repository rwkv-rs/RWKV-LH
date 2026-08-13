# Goal-proposal concurrency diagnostic — recorder-corrected rerun

Pre-registered: 2026-08-13 Asia/Shanghai, before this replacement run's first generation request.

The scientific question, public Basic-30 panel, prompt, condition order, concurrency levels and
metrics are unchanged from
`data/experiments/engine_diagnostics/goal_concurrency_20260813/PROTOCOL.md`.

The first attempt is excluded in full because a runner-only `TempDecision.to_dict()` AttributeError
prevented raw/result persistence. Its known aggregate and unknown-data boundary are documented in
`INTERRUPTED_RECORDER_BUG.md`. No first-attempt answer is reused or selected.

## Instrumentation-only change

Replacement script SHA-256:
`7573aea9a1c6a9c801558b08e8a51a70a5ddf6dfd20001b062852c7704b96200`.

The only intended changes are recorder correctness and crash durability:

1. use `dataclasses.asdict` for `TempDecision`;
2. set `valid_goal` after result serialization succeeds;
3. before each request, persist the exact visible input manifest;
4. append and fsync every model audit event to that case's `model_trace.jsonl`;
5. atomically persist each completed case and each condition summary;
6. refuse overwrite if either aggregate or durable root already exists.

No prompt, sampling parameter, retry behavior, parser, Goal validation, task set, task order,
concurrency level or interpretation threshold changes. The non-cheating boundary from the original
protocol remains binding.

