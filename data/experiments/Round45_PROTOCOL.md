# Round45 Preregistered Protocol: RWKV Owns Task Verification

## Frozen baseline and diagnosis

The active code is the fully restored Round41 baseline: Basic30 Strict `17/30`, External `24/30`, FP `3`, FN `7`. Round44 was rejected and reverted.

Repeated cases (`B06`, `B21`, `B25`, `B26`, `B29`) show one shared Task-stage failure. A read/list action returns complete evidence, but RWKV says that the action “only read/listed” and demands another verification step. Recovery then recreates the same impossible verification Task. Conversely, in `B27`, RWKV's reason explicitly states that forbidden `protocol=v1` remains but it emitted `decision=pass` before generating that reason.

The Harness is an execution/observation layer. It is not a semantic judge. The existing `task_postcondition_commit` RWKV call is the semantic verifier, but its prompt does not make this ownership sufficiently compact and it asks for decision before reason in the dominant generated form.

## Single registered change

Replace only the Task postcondition instruction with a compact verification-ownership contract:

1. RWKV is the verifier for the active Task.
2. It must compare the already returned action evidence directly with the persisted Task postcondition.
3. A complete `read_file`, `read_json`, `list_directory`, or command result is evidence; RWKV must not reject solely because the Harness action did not itself emit a semantic verdict.
4. It must reject when the displayed evidence is incomplete, contradictory, wrong, or leaves a required condition unmet.
5. It writes the reason before the decision, so its final pass/replan commitment follows its own evidence analysis.

The response keeps the existing three semantic fields and values: `schema_version`, `reason`, `decision`. The parser accepts the same object semantics and does not reinterpret the reason or override the decision. This round changes no planner output, action selection, validation result, Controller transition, Goal evidence logic, source catalog, recovery budget, or final output.

## Explicit boundaries

- No deterministic rule reads the reason, task text, path, value, or action output to select pass/replan.
- No second verifier/model request is added.
- No benchmark answer or external acceptance data enters the run.
- The RWKV response is not modified; the Controller uses its emitted decision as before.
- `tool_protocol.py` and the format conversion layer are untouched. They remain limited to registered common wire forms and do no verification.
- No task/case/tool-specific exception is allowed.

## Fixed validation and gates

Offline before online:

- full pytest;
- LH-Control `30/30`;
- E2E catalog `90/90`;
- prompt boundary test proving RWKV is named as verifier, observation actions are evidence, reason precedes decision in the instruction, and no Controller reason interpretation exists.

Fixed online canary:

`E2E-B04`, `B06`, `B08`, `B11`, `B18`, `B21`, `B25`, `B26`, `B27`, `B29`.

- Known Round41 FP checks: `B04`, `B27`, `B29`.
- Known observation/verification recovery checks: `B21`, `B25`, `B26`.
- Correct controls: `B06`, `B08`, `B11`, `B18`.

Run Basic30 only if:

- canary FP is at most `1/3`;
- at least `2/3` of `B21/B25/B26` are Strict;
- at least `3/4` of `B06/B08/B11/B18` are Strict.

Retain/upload eligibility requires Basic30 Strict greater than `17/30`, FP at most `1`, FN at most `7`, all offline regressions passing, and byte-identical raw RWKV final output. Evaluation code, data, ordering, sampling, and thresholds are frozen before online execution.
