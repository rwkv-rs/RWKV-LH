# E2 causal-closure production-chain preregistration

Date: 2026-08-30 (Asia/Shanghai)

## Objective

Run the unchanged real Planner → 2.9B Selector → 13.3B Executor → Harness →
transaction → Reviewer chain after the independent 4-P1/3-P2 causal-closure
remediation.  E2 is a new code arm, not a state-tuning or model arm.  It never
overwrites E0/E1 and keeps the E1 Selector/Executor/Planner identities.

The fixed engineering changes under test are:

1. initial and replacement finalizers receive every completed work outcome;
2. any final-presentation obligation is independently reviewed before completion;
3. incomplete workspace provenance fails closed before public egress;
4. every exclusive atom runs in an isolated snapshot and commits only on success;
5. supervisor pending events have an explicit resolved lifecycle;
6. child action projection recovers idempotently after a half commit;
7. State Router Shadow folds the same direct + child activity projection.

The deterministic failure-injection matrix is already frozen in
`HARNESS_CAUSAL_CLOSURE_P1P2_V1_20260830` and passed 7/7 with the current code.
E2 adds real-model production-chain evidence; it does not replace those fault
injections with subjective output review.

## Frozen data and scopes

- Dataset: `rwkv_agent_capability_ladder_v1`, version V1.
- Source: `benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/`.
- Generation: `scripts/generate_agent_capability_ladder_v1.py`.
- Purpose: fixed end-to-end holdout; never training input.
- Similarity algorithm for later training attribution: `byte-5gram-cosine-v1`;
  every future train request must remain `<0.95` similar to every holdout request.

Scopes are fixed before execution:

1. `canary`, in this order:
   - `AGENT-LADDER-L1-DATA01` (historical correction reachability),
   - `AGENT-LADDER-L2-REPAIR01` (multi-file correction and command verification),
   - `AGENT-LADDER-L5-RWKV01` (real public retrieval, child evidence and finalizer).
2. `full`: the unchanged ordered Ladder10 from E0/E1.

The full scope may run only if the canary satisfies every engineering and
integrity gate below. Strict/external/completed scores are always reported but
are not an engineering canary gate.

## Frozen runtime and identities

- Planner/Reviewer: `gpt-5.4-mini`, reasoning `none`, strict JSON, no fallback,
  semantic repair attempts 2, plan/review token limits 4000/2400.
- Selector: 2.9B S66-M1 Hidden(mean+last)+Soft-MoE h64, zero state, 25 fixed classes.
- Executor: 13.3B G3 general / G6 network, task-level binding, no within-run switch.
- Executor remote physical GPU0, port 18075, local tunnel 29613.
- Selector physical GPU0, port 29621.
- Concurrency 3, max transitions 300, progressive tool disclosure.
- Product remote 18070 / local 29610 must remain running and healthy.
- No raw RWKV output mutation, deletion, truncation, reorder, hiding or replacement.

## Fixed measures and gates

Integrity gates:

- all selected cases and their audits exist in the frozen order;
- all frozen file/model/head/profile/runtime identities match;
- every RWKV raw string, UTF-8 byte count and SHA-256 is exact and
  `postprocessed=false`;
- Selector/Executor profile switches within a run equal zero;
- selection → decision → action → outcome and contract digests have zero drift;
- product 18070 is healthy before and after; experimental services are released;
- preflight full regression is exactly zero failures (current freeze: 684 passed).

Causal-closure canary gates:

- every executed finalizer dependency set covers every completed work node that
  existed before that finalizer;
- a finalizer never completes from an execution review whose graph/evidence
  identity is stale;
- every declared final-presentation obligation has a current satisfied
  `contract_final_presentation_review_committed` before `run_completed`;
- no failed/interrupted exclusive atom changes the parent workspace;
- every `action_returned` has exactly one matching `attempt_started`, and no
  attempt has duplicate starts;
- no resolved historical supervisor pending remains in the current unresolved set;
- every public network attempt has an allowed immutable policy decision, while
  any `unknown` provenance attempt is rejected before backend invocation;
- child actions seen by the parent audit equal child actions in committed atom outcomes.

The comparison algorithm is exact identity/event/byte/set equality. Thresholds
and case order cannot change after the execution freeze is created.

## Completion conditions

- Create content-addressed `E2_EXECUTION_FREEZE.json` before service startup.
- Run canary, release experimental services, then perform a read-only analysis.
- Run full only if every canary engineering/integrity gate passes.
- Run full read-only analysis and retrieval-quality follow-up without changing
  the evaluation criteria.
- Do not load a historical experiment database through `LongHorizonStore.load`.
