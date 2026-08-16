# Round77 preregistration: feasible Task decisions and one visible schema

## Baseline

Round76 short7 is Strict `0/7`, External `0/7`, Agent `0/7`, FP `0`, FN `0`. Manual evidence is frozen in `Round76_canary/MANUAL_CAUSAL_ANALYSIS.md`.

## R77-1: expose only feasible decision types

- Build `allowed_decisions` only from structural state.
- When the evidence registry is empty, allowed decisions is exactly `[act]`.
- When at least one real dependency/current evidence ref exists, allowed decisions is `[complete, act]`.
- RWKV still selects the action type, every argument, evidence refs and completion decision within that feasible set. The controller does not infer an action or accept an unknown ref.
- This rule is task-independent and does not read hidden acceptance, expected values or answer content.

## R77-2: one schema version in the Task-step request

- Remove the presentation-only `schema_version` field from the compact Task causal ledger.
- Keep the full append-only persisted state unchanged; only the prompt projection loses the redundant label.
- Do not accept `long-horizon.task-action-ledger.v1` as a Task-step alias and do not rewrite it to v2.

## R77-3: keep the Round76 single transition

- `complete` still carries evidence refs and `action=null`.
- `act` still carries one complete untouched `TaskAction {action_type, arguments}`.
- No name-only selector, fixed-argument call, model-action sentinel or private replan Task tool returns.

## Offline and online gates

- Tests prove an evidence-empty Task prompt permits only `act`, dependency evidence permits both decisions, and no causal-ledger schema appears in the Task-step prompt.
- Repeat pytest, compile, diff check, LH-Control30 and E2E90 validate-only.
- Repeat the fixed short7. Continue only at Strict `>=4/7`, with B01/B02/B10 all Strict, FP `<=1`, FN `<=1`.
- Full90 upload gate remains Strict `>31`, External `>=32`, FP `<24`, FN `<=1`.
