# Round113 compact end-to-end chain preregistration

## Status

`preregistered_implementation_not_run`

This protocol is frozen before the Round113 source changes. It is based on the
case-by-case evidence in `Round112_basic30_frontier_role/MANUAL_CAUSAL_ANALYSIS.md`,
not on post-change benchmark outcomes.

## Fixed diagnosis

- Round101 Basic-30: Strict `10/30`, TP/FN/FP/TN = `10/7/6/7`.
- Round112 Basic-30: Strict `6/30`, TP/FN/FP/TN = `6/6/9/9`.
- `frontier_role` created FNs after RWKV had already produced correct artifacts and
  did not prevent false completion of incorrect deliverables.
- Ordinary read/transform/write/verify work is split too early, so a weak model can
  stall in a discovery Task or lose observations when it omits an `after` ref.
- Goal history remains similar enough to the `lh_tasks` command schema to be echoed
  into repeated frontiers.
- Generic read/parse evidence does not make RWKV compare every visible output value
  with every Goal clause before completion.
- Every Round112 terminal run returned non-empty text, but one delivered a truncated
  protocol wrapper instead of a readable answer.

## Frozen implementation scope

1. Remove `frontier_role` and `goal_role` from the only live Task protocol, state,
   persistence and completion path. Do not keep a second compatibility structure.
2. Change planning guidance to prefer the smallest end-to-end Task frontier. A Task
   may inspect inputs, mutate outputs and verify them. Discovery-only Tasks are for
   genuinely unknown collection scope, not ordinary small file or coding work.
3. Add a deterministic, chronological, bounded projection of recent completed Task
   observations to Task lanes. It may expose only already recorded observations and
   must not infer relevance, expected values or answers.
4. Rename Goal history fields so they are structurally distinct from Task proposal
   fields. Reject a newly proposed Task whose exact normalized Task structure matches
   a completed active Task while the complete workspace digest is unchanged. The
   rejection must allow RWKV to choose either different work or Goal completion.
5. Add exactly one RWKV-owned completion review: the first `lh_goal_done` displays a
   compact review event; RWKV must independently confirm `lh_goal_done` or create
   repair work. The controller may validate references and state only; it may not
   decide semantic correctness.
6. Pass Final facts as a compact structured object and cap Final generation. Deliver
   valid `lh_final_answer.text` byte-for-byte. Audit invalid raw output but return a
   clearly marked non-semantic runtime status fallback instead of truncated protocol.
7. Keep the existing simple common format conversion layer. Do not add answer rules,
   hidden-acceptance checks, business-value coercion or artifact rewriting.

## Frozen data and parameters

- Basic cases: exactly `E2E-B01` through `E2E-B30`.
- Extension task digest:
  `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b`.
- Extension acceptance digest:
  `395e1651f52259de7e56a63476504891f136edd2d4dd5a8263064077741ede12`.
- Core task digest:
  `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c`.
- Endpoint/model/sampling: unchanged from Round112.
- Full Basic run: `max-transitions=200`, `concurrency=1`.
- Focused canary, before full Basic: B01, B02, B04, B10, B11, B14, B15,
  B18, B22, B23, B25, B27, B29, B30.
- Offline suite and LH-Control use their existing fixed inputs and exact pass/fail
  algorithms. No threshold or acceptance changes are permitted after a run starts.

## Fixed evaluation

Primary:

- Strict E2E, TP/FN/FP/TN and actual external passes.
- FP must be lower than Round112 `9` and must not exceed Round101 `6` before the
  change is considered a quality improvement.
- Strict Basic must exceed Round112 `6/30`; compare against Round101 `10/30`.

Secondary:

- Every terminal state has non-empty user-facing output.
- Every valid RWKV Final is delivered byte-for-byte.
- Invalid/truncated raw Final remains auditable and its fallback never changes status.
- Repeated-frontier events, Task count, Attempt count and model requests are reported,
  but lower cost cannot compensate for lower quality.
- Inspect every focused case and every model call. Full-run aggregation cannot replace
  manual causal inspection.

## Required regression order

1. Targeted unit tests for the removed role field, chronological observation capsule,
   unchanged-frontier rejection, completion review/resume, and terminal fallback.
2. Complete offline test suite.
3. LH-Control full fixed suite.
4. Round113 focused canary.
5. Only if the focused causal result is non-regressive, run Basic-30.
6. Full E2E-90, boundary, exception and history-recovery regressions remain required
   before declaring the architecture solved.

## Anti-cheating boundary

The model owns Task contents, operation choice, operation arguments, artifact bytes,
completion decision and valid Final answer. The controller may preserve state, expose
observations, validate protocol shape, suppress exact no-progress replay and report
runtime status. It must never use hidden acceptance or controller-generated business
values to make RWKV appear correct.
