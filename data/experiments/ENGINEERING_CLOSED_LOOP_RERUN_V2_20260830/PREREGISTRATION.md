# Engineering-closed real Harness rerun V2 preregistration

Date: 2026-08-30 (Asia/Shanghai)

## Objective

Measure the real Planner → 2.9B Selector → 13.3B Executor → Harness →
transaction → Reviewer chain after removing identified engineering suppression.
This run establishes the zero-new-state baseline that subsequent numbered state
ablations must beat.  It does not alter, repair, truncate, replace, hide, or
reorder any RWKV output.

The code changes under test are systemic only:

1. one immutable `AtomExecutionContract`/digest and exact
   selection→decision→action→outcome bindings across all stages;
2. one Harness-derived `ContractProgress` authority for budgets, write-root
   coverage and completion;
3. bounded dependency handoffs using the same canonical model-result projection;
4. Reviewer capsules that retain bounded external evidence plus the complete
   durable-result digest;
5. the immutable Goal retrieval policy as the sole Planner-menu,
   Selector-eligibility, provenance, execution and recovery authority.

No deterministic component chooses a replacement operation or writes Executor
arguments.  The Selector still selects the operation from untouched raw logits;
the Executor still owns arguments and `final_answer` content.

## Frozen data and metric

- Dataset: `rwkv_agent_capability_ladder_v1`, version V1.
- Source: `benchmarks/rwkv_e2e/rwkv_agent_capability_ladder_v1/`.
- Cases: the same fixed 10 cases and order used by Atom Execution Closed Loop V1.
- Purpose: real end-to-end holdout; never training input.
- Generation: `scripts/generate_agent_capability_ladder_v1.py`.
- Similarity algorithm: `byte-5gram-cosine-v1`.
- Any state-tuning row created later must have maximum request similarity `<0.95`
  against every holdout request.
- Acceptance, external verifier, task order, runtime parameters and thresholds
  are frozen before this run and may not be changed after results are observed.

## Frozen runtime

- Planner/Reviewer: `gpt-5.4-mini`, reasoning `none`, strict JSON, no fallback,
  plan/review maximum tokens `4000/2400`.
- Selector: 2.9B S66-M1 Hidden(mean+last)+Soft-MoE h64, zero state, fixed 25
  class order, complete raw logits retained.
- Executor: 13.3B task-level G3 for offline and G6 for network cases; no
  within-run profile switch.
- Remote Executor physical GPU0, experimental port `18075`, local tunnel
  `29613`.
- Local Selector physical GPU0, port `29621`.
- Concurrency 3, max transitions 300, progressive disclosure.
- Product service `18070` must remain healthy and must not be stopped or
  replaced.

## Single frozen baseline arm

Arm `E0` uses the current production engineering closure with the unchanged
zero Selector state and unchanged G3/G6 Executor states.  It is compared to the
immutable V1 B arm only for attribution; it is not retrospectively inserted
into the old A/B experiment.

## Fixed outputs and measures

Primary:

1. strict pass / 10;
2. external verifier pass / 10;
3. agent completed / 10;
4. contiguous capability ceiling.

Process/integrity:

- Planner failures and correction loops;
- Selector call/operation counts, eligible margins and ABSTAIN;
- offline `web_search`/`connector_lookup` eligible, selected and executed counts;
- accepted/rejected Executor decisions and fixed rejection categories;
- mutate atoms with successful path mutation, workspace change and all-root
  coverage;
- transaction-integrity and InputBudget errors;
- dependency handoff characters and Reviewer evidence retention;
- exact selection/decision/action/outcome and contract-digest drift;
- raw output string/UTF-8/SHA integrity and postprocessed=false;
- per-run Selector/Executor state/profile switches;
- product `18070` health before and after.

## Pre-registered gates

The E0 run is valid only if all 10 audits exist, frozen identities and task order
match, raw integrity is 100%, contract/binding drift is zero, state/profile
switches are zero, and product `18070` remains healthy.

Engineering closure is confirmed only if:

- offline network eligible/selected/executed counts are all zero;
- InputBudget errors caused by dependency handoff projection are zero;
- every large external result that contains evidence retains at least one
  bounded evidence source in the Reviewer capsule;
- no historical regression test fails.

Strict/external/completed scores are reported exactly even if zero.  A safety
rejection, mask, or counterfactual is never counted as an end-to-end pass.

State tuning remains required when valid E0 still shows either of these model
residuals:

- 2.9B chooses a semantically inapplicable operation while an applicable
  operation is eligible (especially JSON mutation for non-JSON artifacts), or
  low-margin/deadline-nonmutation behavior remains material;
- 13.3B produces invalid JSON/schema/arguments or completes an action without
  satisfying the atom's semantic artifact requirement.

Subsequent state experiments must use separate numbered Selector and Executor
states and a fixed factorial attribution.  No per-stage state proliferation is
allowed without an observed improvement that survives the fixed holdout.

## Completion conditions

- `uv run pytest -q`: all tests pass before execution.
- E0 full run and a strict read-only analysis are recorded in this directory.
- All output and source hashes are recorded.
- Experimental services are released after the run; product service is retained.
- No historical experiment database is opened through `LongHorizonStore.load`.
