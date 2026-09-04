# Round68 fixed-15 manual causal analysis

## Outcome

- Strict E2E: `0/15`.
- External acceptance: `0/15`.
- Agent completion: `0/15`.
- `14/15` cases failed before run creation.
- `E2E-M03` created a run but blocked before its first Harness action.

The canary gate failed, so full90 is not run and no code is uploaded.

## Case-by-case first harmful transition

The following 14 cases have the same complete causal chain:

| Case | Draft Goal | Goal audit output | Terminal effect |
| --- | --- | --- | --- |
| E2E-B01 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-B02 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-B10 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-M01 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-M06 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-LH02 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-LH05 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-LH11 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-B24 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-M12 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-M16 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-M18 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-H12 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |
| E2E-H13 | structurally parsed | schema echoed as `long-horizon.goal-proposal.v1` three times | run not created |

Every audit object otherwise contained exactly the requested semantic fields
`decision`, `reason`, `omissions`, `inventions`, and `redundancies`. Across all
14 cases there were 42 identical schema-family echoes. The first harmful event
is therefore a review-specific format boundary that rejects a stable common RWKV
wire spelling. Asking the same correction three times cannot improve it because
the prompt continues to anchor the immediately preceding Goal schema.

### E2E-M03 — two review-layer failures

M03 happened to emit `audit.v1` first and the canonical Goal-audit schema on the
second attempt, so it reached planning. The Goal review nevertheless worsened
the draft: it falsely claimed the explicit `enabled`/`disabled` mapping was not
in the user request and changed it to a “generic rule”. The draft also invented
underscore replacement for `display_name`; the audit did not detect that error.

The first action path then correctly selected `read_json` for the Task
postcondition “users.json content is observed” and supplied the real path. The
action reviewer emitted `rwkv-lh.task-action-ledger.v1` on all three protocol
attempts, so the call never executed. Its reasons also overreached from the
active read Task to the eventual migration Goal: it said the valid read should
instead perform the later write. Thus M03 exposes both review schema anchoring
and an over-broad review scope.

## Root cause

Round68's quality idea is sound but the review interface is not yet weak-model
compatible:

1. The review prompt displays a typed proposal with its protocol schema, and
   RWKV copies that schema into the review envelope.
2. The format boundary treats the stable copied schema as a semantic failure,
   even though all review semantic fields are intact.
3. The Goal reviewer sees protocol keys and criterion records as if they were
   proposed user requirements, causing false “invention” findings.
4. The action reviewer compares an atomic Task against the whole future Goal,
   so it can reject a correct causal read because it does not perform a later
   write.

This is not evidence that multiple RWKV passes inherently reduce quality. It is
evidence that each pass must receive a projection and decision boundary matched
to exactly one responsibility.

## Next direction

- Register only the three observed review-schema echoes as typed format aliases;
  preserve and audit the raw value, and change no semantic field.
- Show Goal audit a semantic projection (`objective`, caller/model constraints,
  observable outcome descriptions) rather than the proposal's protocol schema,
  ids and required flags.
- Tell Goal finalization that exact literal mappings in the immutable request
  may not be generalized by an audit.
- Make action review judge only the active Task postcondition and immediate tool
  effect. The immutable Goal remains provenance but may not add future work to
  the current Task boundary.
- Retain draft/final RWKV ownership; do not use controller rules to approve a
  Goal or action.
