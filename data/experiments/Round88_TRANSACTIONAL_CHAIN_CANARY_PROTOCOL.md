# Round88 transactional full-chain canary preregistration

## Purpose

Verify the chain-level causes established by manual inspection of every Round87
call. The fixed cases remain `E2E-B01`, `E2E-B02`, `E2E-B03`, and `E2E-H04`.
No controller rule selects, filters, ranks, fills, or rewrites an RWKV operation,
operation value, task answer, expected result, criterion, or completion decision.

## Frozen differences from Round87

1. A schema-valid candidate that is later rejected by runtime applicability,
   unchanged-observation, workset, or completion-evidence checks is removed from
   the authoritative lane head. The exact raw candidate and immutable checkpoint
   remain audited; the rejection event follows its exact input checkpoint.
2. The interface layer recognizes only two general executable equivalences:
   optional `null` is treated as omitted before registry defaults, while required
   null remains untouched; `lh_task_done`/`lh_goal_done` function names are the
   entire void-control decision, so extra annotation params are audited but not
   interpreted. No value is created from task meaning or acceptance data.
3. Action results, failures, and Goal progress use bounded model-facing
   observation projections instead of nested RunState/Attempt storage records.
   Complete cursor reads explicitly expose `observation_complete` and a null next
   cursor; authority and audit storage remain lossless.
4. Run status and user response are independent. Completed, blocked, and
   interrupted runs all enter an RWKV Final lane. A transport-level availability
   fallback is explicitly marked and cannot satisfy Strict E2E.
5. Chunk and reduce children correct their own protocol failures in their own
   lane; accepted siblings are neither regenerated nor merged as hidden state.
6. Workset deltas are staged atomically, and an accepted side-effect proposal
   deferred behind a read-only frontier is retained rather than discarded.

All prior properties remain frozen: one `lh_task_call`, explicit active `task_id`,
atomic operation plus `operation_args`, fixed operation catalog, proposal/runtime
separation, independent post-mutation observation, stable workspace digest, and
pre-Attempt duplicate suppression.

## Frozen implementation and runtime

- Branch: `chase/g1i-tool-protocol`
- Base commit: `14d864d71bf670b479a33f4fdb63b4772b69d3c8`
- `rwkv_lh/schema.py`: `bf3baec36a407006ac7ff5b0317d8c7d1b99420aa44bfa1f357df6fcd5ff83c8`
- `rwkv_lh/model.py`: `24b17788129873b3ca0106e81f08848990b5c94f471cb82c6f0ea109c4885b43`
- `rwkv_lh/model_io.py`: `ceb43f24372e8e18df9379c8d69abbcd68b4cb689fceaab31fb088a4865db3d3`
- `rwkv_lh/model_session.py`: `f4c9a6a3dfa3dda1d816d1b1066770ff1a253b26519962ee12f051ccfb93f45c`
- `rwkv_lh/controller.py`: `6fb18010f378d7ddbb757795b6677e2325581d4ab1a2d839e520faea2a2ccb0e`
- `rwkv_lh/harness.py`: `691e610af6d4a3dbcc558bfdd97570933b736c5ce98240d5c8985423063a2021`
- Runner: `2df02384a83fc3a3eba25a19e57fa881a3b27f18bf6e4aa293edf3b0bead6960`
- Focused transactional tests: `42 passed`
- Complete offline regression: `87 passed`
- Endpoint: `http://127.0.0.1:29610/v1`
- Model: `rwkv7-g1i-13.3b-20260805-ctx16384`
- Model service created: `1786759662`
- Concurrency: `1`; max transitions: `200`; model sampling unchanged.

## Command

```bash
uv run python /home/chase/GitHub/RWKV-LH/scripts/run_rwkv_e2e_benchmark.py \
  --suite all \
  --case E2E-B01 \
  --case E2E-B02 \
  --case E2E-B03 \
  --case E2E-H04 \
  --output /home/chase/GitHub/RWKV-LH/data/experiments/Round88_transactional_chain_canary \
  --max-transitions 200 \
  --concurrency 1
```

## Fixed evaluation

- Inspect every raw Goal, Task, Final, rejected, and rewound call.
- Record Agent, External, Strict, FP/FN, attempts, suppressed actions, response
  non-emptiness, and whether delivered output is exact RWKV Final text.
- Verify rejected Task candidates do not occur in the next checkpoint transcript.
- B01/H04 external success must not be lost; H04 must retain post-write read.
- No code or evaluator changes are permitted until this canary completes.
