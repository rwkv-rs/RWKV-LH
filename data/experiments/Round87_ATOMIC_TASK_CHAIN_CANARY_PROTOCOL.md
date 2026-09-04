# Round87 atomic Task-call chain correction canary preregistration

## Purpose

Verify the second chain-level repair derived from manual inspection of every
Round86 model call. This is not score tuning. The controller does not provide,
select, rewrite, or rank any operation, operation argument, task answer, expected
value, criterion, or completion decision.

The fixed diagnostic cases remain `E2E-B01`, `E2E-B02`, `E2E-B03`, and
`E2E-H04`, so changes can be attributed to the registered architecture changes.

## Frozen architecture differences from Round86

1. The one Task wrapper retains `task_id` and `operation`, but its nested payload
   is named `operation_args`. This removes the structural ambiguity between the
   call envelope's `arguments` and the operation's arguments without changing any
   semantic value.
2. Model-facing events omit runtime routing identifiers (`event_id`, `scope_id`,
   and event version). Durable state and audit records retain those identifiers.
   The model therefore sees task semantics rather than internal routing fields.
3. An identical cache-safe action on an unchanged workspace is rejected before an
   Attempt is created and before any verifier is called. RWKV receives the prior
   visible observation and must choose completion or a different operation. Three
   repeated correction observations are allowed before a stable-loop block.
4. Rollover attempt projections expose only the step state, operation input,
   bounded result, checks, evidence references, and error. They no longer copy the
   complete nested runtime object back into the Task lane.
5. After a successful mutating action, Task completion requires a later successful
   read-only observation. This is independent evidence, not an interpretation of
   the natural-language criterion and not an automatic completion decision.

All other Round86 properties remain frozen: one atomic Task tool, a fixed compact
operation catalog, exact active `task_id` validation, semantics-free envelope alias
normalization, proposal/runtime separation, same-lane protocol correction, an
eight-task frontier, and unchanged sampling.

## Frozen implementation and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- `rwkv_lh/schema.py`: `bf3baec36a407006ac7ff5b0317d8c7d1b99420aa44bfa1f357df6fcd5ff83c8`
- `rwkv_lh/model.py`: `36eccc365b9a8ebff2b388e0e91b6619849636cefea56b4657af7ef90828f0ea`
- `rwkv_lh/model_io.py`: `c21d5209b20d67fe72ef0585039fc738f1976943529904b4d57abf3278992ff7`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- `rwkv_lh/controller.py`: `fd52486e11de3c97dcd13e7143d7d3517b05da21e1868dd4c113785d68873b27`
- `rwkv_lh/harness.py`: `e3f217d0ef94f1d5ef3d5dd8d7b4cfa426bf44a563c7a2bbb39a2863907b86a8`
- Runner: `62cdfc9d3f21d2b075cbca367db9b6016b79ac144b52784d0019dee6361622c7`
- Regression: `83 passed`
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786758572`
- Concurrency: `1`; max transitions: `200`; fixed model sampling unchanged.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 \
  --case E2E-B02 \
  --case E2E-B03 \
  --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round87_atomic_task_chain_canary \
  --max-transitions 200 \
  --concurrency 1
```

## Fixed evaluation

- Inspect every raw Goal, Task, and Final call, including rejected calls.
- Record first Task operation, protocol correction, executed and suppressed
  actions, Agent completion, external acceptance, Strict E2E, FP, and FN.
- Confirm whether runtime identifiers recur in model output and whether an
  unchanged action creates an Attempt.
- H04 may not be Agent-complete without a post-mutation read-only observation.
- No code or evaluation changes are allowed before this canary completes.
