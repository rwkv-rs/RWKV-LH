# Round79 unified lane short7 r7 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `1/7` (`E2E-B02`)
- External acceptance: `2/7` (`E2E-B01`, `E2E-B02`)
- No interruption and no semantic/format resampling.
- The full90 gate failed; full90 was not run.

The score is unchanged from r6, although several cases continued farther. This
run is used to separate remaining deterministic architecture defects from true
schema-invalid model commands.

## Deterministic defects

- B01 correctly wrote/read the greeting, then selected the same known-failing
  `read_json(greeting.txt)` until three failed attempts were consumed. The
  failure event was visible, but the runtime re-executed an identical read-only
  failure instead of returning a no-progress rejection to the same lane.
- M01 rejected an unbound collection action during initial materialization, but
  the same condition arising as the next action after a successful member step
  still terminally blocked. The state relation had two inconsistent paths.
- M03 reached 15,224 input tokens after eight steps. Evidence was not silently
  dropped, but the transcript repeated the complete operation option
  descriptions and duplicated each selected definition in both the event and
  the newest System tool scope.
- M12 selected `lh_replace_task` for an active pending Task. The operation
  description permits false/infeasible Task replacement, while TaskGraph only
  permitted replacing a completed Task; `_apply_goal_repair` also added the new
  Task before this late precondition failed, leaving a partial mutation.

## Model schema failures retained fail-closed

- B10 emitted `lh_task_done` with non-empty params.
- M06 completed its Task but emitted `lh_goal_done` with non-empty params.

These are actual schema failures. They are not normalized, stripped or retried.

## Corrective change for the final canary

- Route collection member mismatch from both materialization and Task-step
  continuation through one `task_operation_rejected` relation.
- Suppress exact repetition of the immediately preceding failed read-only or
  idempotent operation and return that fact to the same lane.
- Permit explicit replacement of any active false/infeasible Task; prevalidate
  repair state before adding replacement nodes.
- Make operation selection a compact enum and remove the duplicate definition
  from `operation_selected`. Exact events, commands, refs and checkpoints remain
  durable; only repeated schema prose is removed.

Fixture Task selection dropped from 820 to 337 tokens and `write_file` binding
from 1,201 to 596 tokens. Local verification is `71 passed`; unified control is
`35 passed`.
