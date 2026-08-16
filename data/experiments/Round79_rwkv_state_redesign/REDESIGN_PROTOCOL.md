# Round79 RWKV-native redesign and ablation protocol

Date: 2026-08-14

Status: preregistration draft. No experiment may be used as formal evidence
until the remaining dataset hashes and native-server build identifier are
filled in before execution.

Normative inputs and migration are defined in `UNIFIED_MODEL_IO_SPEC.md` and
`UNIFIED_REFACTOR_PLAN.md`. The exact current baseline is recorded in
`CURRENT_MODEL_INPUT_AUDIT.md`.

## 1. Objective

Measure whether RWKV-LH improves by aligning the runtime with RWKV recurrent
state and by reducing the model's output contract, while preserving the model
as the sole semantic authority.

## 2. Fixed variants

- V0: current Round78 wide-schema prompt-replay baseline.
- V1: minimal-command protocol with typed event prompt replay.
- V2: the same minimal-command protocol with native RWKV recurrent-state
  create/resume/fork/commit/rollback/export/import.

V1 and V2 must share command grammar, Harness definitions, datasets, sampling,
thresholds and evaluator code. Only state transport may differ. If V2 is not
available, V1 may be measured as an interface ablation, but the recurrent-state
hypothesis remains untested.

## 3. Output-stability dataset

Construct a fixed snapshot set from real audits, stratified by transition:

- initial action selection;
- post-read action selection;
- post-write completion;
- exact/negative Goal constraint;
- collection member selection;
- collection completion with pending members;
- recovery after deterministic failure;
- Task repair/replacement.

Each snapshot records source round, case, request/event ID, source hash, visible
raw facts and expected structurally feasible operations. Hidden acceptance data
must not enter the model input.

Pending before execution: register the final snapshot count, inventory and
SHA-256 manifest.

## 4. Repeated sampling

For every fixed snapshot and every variant:

- 10 independent generations;
- the same deployed model build;
- temperature `0.05`, top_p `1.0`, top_k `0`;
- presence/frequency penalty `0.0`, penalty_decay `0.996`;
- one generation per transition;
- no format-repair resampling;
- fixed output-token limit registered per command grammar.

## 5. Metrics

All comparisons use the canonical command representation. No subjective
similarity judgment is allowed.

- **Protocol validity**: fraction parseable into exactly one registered command.
- **Operation agreement**: modal frequency of the exact command discriminant.
- **Action agreement**: modal frequency of exact action name conditional on
  `act`.
- **Argument agreement**: modal frequency of the canonical JSON SHA-256 of
  arguments conditional on the same action.
- **Semantic flip rate after format failure**: must be zero because no second
  semantic generation is allowed.
- **Prompt tokens per transition** and **generated tokens per transition**.
- **State replay bytes** and **native state bytes** reported separately.

Preregistered minimums for accepting the new output interface:

- protocol validity at least 0.99 over all repeated generations;
- per-snapshot operation agreement at least 0.90 for at least 95% of snapshots;
- aggregate action agreement at least 0.90 where `act` is modal;
- zero completion command when the deterministic member ledger contains a
  pending required member;
- zero semantic resampling after protocol failure.

Argument agreement is diagnostic in this phase because multiple arguments can
be semantically valid. Formal correctness remains external E2E acceptance.

## 6. E2E gates

Run in this order without changing evaluation after results are seen:

1. structural/unit/integration tests;
2. fixed output-stability snapshots;
3. fixed short7;
4. all historical same-class cases found by dataset scan;
5. fixed full90;
6. crash/resume and malformed-output fault injection.

Report Strict, External acceptance, Agent completed, FP, FN, model request
count, prompt tokens, output tokens, state transport, earliest wrong transition
and all protocol failures.

The redesign cannot close with any new false positive relative to V0. It must
also improve Strict and External acceptance on the preregistered fixed datasets;
unit tests alone are insufficient.

## 7. Native state correctness gates

- a candidate generation cannot mutate the committed session before command
  validation;
- rollback restores the exact parent state digest;
- export/import preserves the next-token logits within the server's registered
  numerical tolerance;
- crash after side effect but before state commit resumes without repeating an
  unsafe action;
- crash after state commit but before side effect resolves through the durable
  Attempt journal;
- forks cannot overwrite sibling or parent state;
- every decision record binds input state digest, output state digest, visible
  event refs, sampling parameters and command digest.

## 8. Stop conditions

Stop and diagnose without tuning the evaluator if:

- the server lacks any required native state operation;
- structured/constrained generation changes model semantics or returns server
  errors;
- a variant changes the hidden acceptance input boundary;
- a new false positive appears;
- state resume cannot be made byte/digest auditable.
