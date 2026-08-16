# Round68 offline validation report

## Result

- Complete production/unit/integration collection: `423/423` passed.
- LH-Control deterministic architecture regression: `30/30` passed.
- Frozen E2E catalogs/reference plus the 31-file parallel summarize/read
  architecture regression: `5/5` passed.
- Python compileall and `git diff --check`: passed.

The first LH-Control execution found one obsolete `LH-M04` fixture response: it
still emitted the old three-field Task commit. The fixture was updated to use the
same four-field evidence-bound contract as production. `LH-M04` then passed alone
and the complete suite passed from a fresh output directory. The prior generated
failed/rerun directory was moved intact to
`temp/round68_lh_control_30_failed_rerun`; no experiment input or acceptance
criterion was changed.

## Round68-specific coverage

- Goal construction has one production path: RWKV draft, focused RWKV audit and
  full RWKV final proposal. Only the final proposal creates `GoalState`.
- Action commitment has one production path: compact RWKV action-name selection,
  one selected schema for arguments, and focused RWKV approve/revise. A revise
  response triggers a new RWKV semantic round; controller code has no fallback
  action.
- Task postcondition draft and final decisions bind pass to non-empty existing
  action/effect/memory references. The final reviewer can reverse the draft.
- Goal-criterion evidence has draft and final RWKV stages. The final response is
  the only response whose causal/independence bindings become authoritative.
- `read_files` returns one ordered status record for every exact selected path;
  missing, non-file and invalid UTF-8 records do not discard successful reads.
- Goal-obligation and failed-Task recovery both bind the next Task batch to one
  RWKV-selected existing criterion/task/predecessor gap. Invalid ids are rejected
  and corrected by RWKV.
- Controller-side repeated-failure, non-idempotent-retry and exhausted-budget
  decision substitution is removed. Feasible choices are exposed before the
  production RWKV decision; an infeasible adapter decision is rejected without
  choosing a replacement.
- Model action proposals are serial until one side effect or a read-only prefix
  is known. Read-only Harness calls still execute concurrently; the 31-file
  fan-out/summary/aggregation regression passes.
- Transparent protocol boundary is version `v7`; the evidence-bound Task commit
  missing-schema form is closed over exactly reason, decision and evidence_refs.

## Non-intervention audit

RWKV still owns every Goal field, Task, selected recovery gap, action name,
argument, value, evidence decision, source binding and final answer. Controller
code validates closed schemas, id/reference existence, workspace scope, tool
effect metadata, attempt safety and serialization. It does not generate, rank,
merge, truncate, repair or replace semantic model output.

No hidden acceptance result, frozen Codex answer or benchmark score is visible to
generation. Request count and latency are recorded but are not Round68 gates.

## Dataset record

- Source: repository test suite, frozen benchmark catalogs and LH-Control-30 at
  the Round68 working tree.
- Version: `Round68`, preregistered in
  `data/experiments/Round68_PROTOCOL.md` before implementation/live execution.
- Purpose: verify the quality-first RWKV review pipeline, evidence binding,
  per-path observation and non-substituting recovery before live fixed15.
- Generation: complete pytest, `scripts/run_lh_control_benchmark.py --output
  data/experiments/Round68_offline/lh_control_30`, frozen five-test subset,
  compileall and diff whitespace validation.
- Detailed LH-Control records are under `lh_control_30/`.
