# LOCAL_EXECUTOR_REQUEST_LAST_ABLATION_V1_20260829

## Frozen question

Does moving the one authoritative Executor request from the bootstrap payload to
the final field of the closed selected-operation payload preserve or improve the
already selected `EXE-G1-V2-STEP1250` state on the complete frozen dev480 set?

## Fixed variants

- `E0`: frozen Executor V2 prompt, request in the last bootstrap field; existing
  three repeated dev480 runs are the baseline.
- `E1`: V3 closed request-last prompt. Context and contract precede the exact
  request; the request occurs once and is the final JSON field immediately before
  `Assistant: ```json`.
- Selector bytes, labels, targets, split membership, source rows, and tool schemas
  are unchanged.

## Fixed execution

- Model: 13.3B G1i Executor.
- State: `EXE-G1-V2-STEP1250`, SHA-256
  `e967793ace2ab9dfca09ac4ce81f5af9a8cec1ebee960b207a735dda9d069ddf`.
- Device: remote physical GPU0 only.
- Set: all 480 rows, exactly one request per row, no hidden retry.
- Sampling and stop suffixes: identical to
  `scripts/evaluate_executor_state_tuning_v2_dev.py`.
- Raw response body, raw text, and token IDs are fsynced before parsing and are
  never modified, deleted, reordered, hidden, or used to trigger a retry.

## Frozen metrics and decision gate

The registered evaluator reports transport/envelope validity, schema validity,
operation correctness, canonical-call exactness, wire exactness, byte exactness,
final required-fact coverage, and p50/p95 latency.

`E1` may replace the online layout only if all 480 rows retain schema validity,
operation correctness, canonical-call exactness, and wire exactness, all 20 final
rows retain required facts, raw integrity passes, and p95 latency is no more than
115% of the median baseline p95. The metric, parser, threshold, and source set may
not be changed after the run. If `E1` fails, the layout remains the target design
but requires a separately numbered V3 state-tuning run; its failure may not be
hidden by reverting or repairing model output.
