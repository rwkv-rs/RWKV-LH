# E1 reachable-correction engineering closure preregistration

Date: 2026-08-30 (Asia/Shanghai)

## Objective

Verify that the real Planner → 2.9B Selector → 13.3B Executor → Harness →
transaction → Reviewer chain no longer accepts a correction graph that can
never become schedulable.  This is an engineering-closure rerun, not a new
model or state arm.  Selector and Executor model/state identities remain the
same as E0.

The observed E0 failure mechanism is frozen before E1:

- a correction node could depend on an existing node whose terminal status was
  `failed`, `interrupted`, or otherwise non-completed;
- `_contract_ready_nodes` only admits dependencies with status `completed`;
- the accepted correction therefore had no future state in which it could run;
- the Reviewer saw unchanged evidence until repeated-correction or stagnation
  termination.

E1 exposes the authoritative existing-node status in the compact correction
request and applies one shared Planner-adapter/Controller invariant: a new
correction node may depend on an existing node only when that node is already
`completed`.  Invalid Planner JSON is retained in the strong-model audit,
rejected, and fed to the bounded semantic-repair call.  No dependency is
rewritten and no node, operation, Executor argument, result, or RWKV output is
invented by deterministic code.

## Frozen data

- Dataset: `rwkv_agent_capability_ladder_v1`, version V1.
- Source: `benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/`.
- Generation: `scripts/generate_agent_capability_ladder_v1.py`.
- Purpose: fixed real end-to-end holdout; never training input.
- Source integrity: tasks, hidden acceptance, manifest, generator and verifier
  are hashed in `E1_EXECUTION_FREEZE.json`.
- Similarity algorithm for later training attribution:
  `byte-5gram-cosine-v1`, with maximum request similarity `<0.95` against every
  holdout request.

Two scopes are frozen:

1. `canary`: `AGENT-LADDER-L1-DATA01`, then
   `AGENT-LADDER-L2-REPAIR01`.  These are the two E0 cases whose accepted
   correction roots depended on interrupted existing nodes.
2. `full`: the original ordered Ladder10 used by E0.

The full scope may run only after the canary output passes the reachability and
integrity gates below.  No threshold or metric may be changed after either
scope starts.

## Frozen runtime

- Planner/Reviewer: `gpt-5.4-mini`, reasoning `none`, strict JSON, no fallback,
  semantic-repair attempts `2`, plan/review maximum tokens `4000/2400`.
- Selector: 2.9B S66-M1 Hidden(mean+last)+Soft-MoE h64, zero state, fixed 25
  class order, raw logits retained.
- Executor: 13.3B task-level G3 offline and G6 network; no within-run profile
  switch.
- Remote Executor physical GPU0, experimental port `18075`, local tunnel
  `29613`.
- Local Selector physical GPU0, port `29621`.
- Concurrency 3, maximum transitions 300, progressive disclosure.
- Product service remote port `18070` / local tunnel `29610` must remain healthy
  and must not be stopped or replaced.

## Fixed measures and gates

Integrity gates for both scopes:

- every selected case has an audit;
- selected case order and all frozen identities match;
- every RWKV raw output string, UTF-8 byte count and SHA-256 are exact and
  `postprocessed=false`;
- no Selector/Executor state or profile switch occurs within a run;
- selection→decision→action→outcome and contract digests have zero drift;
- product `18070` is healthy before and after;
- all preflight regression tests pass.

Reachability gates for the canary:

- no accepted correction node depends on a non-completed existing node;
- no correction patch has zero initially ready nodes solely because of an old
  non-completed dependency;
- no correction root remains pending after all its reachable predecessors are
  terminal;
- any `can never become ready` semantic rejection is followed by an accepted
  repair response within the frozen repair budget;
- strict/external/completed results are always reported, but are not required
  to pass this engineering gate because model residuals remain a separate
  attribution target.

The full run reports the same primary/process metrics as E0.  Improvement is
not inferred from strict score alone: E1 first has to remove the frozen
unreachable-scheduler mechanism while preserving raw outputs and old tests.

## Completion conditions

- Preflight: `env TMPDIR=/tmp TEMP=/tmp TMP=/tmp uv run pytest -q`.
- Canary and its strict read-only analysis are recorded before full execution.
- If canary gates fail, the full scope is not run.
- Full output and strict read-only analysis are content-addressed.
- Experimental services are released after every scope; product service stays
  running.
- No historical experiment database is opened through
  `LongHorizonStore.load`.

