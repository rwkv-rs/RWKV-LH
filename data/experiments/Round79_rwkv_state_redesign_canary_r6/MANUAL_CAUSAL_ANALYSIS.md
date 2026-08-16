# Round79 unified lane short7 r6 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `1/7` (`E2E-B02`)
- External acceptance: `2/7` (`E2E-B01`, `E2E-B02`)
- B01 had the correct accepted workspace but remained blocked.
- No run was interrupted and no format failure was resampled.
- The fixed full90 gate failed; full90 was not run.

This is the first Round79 canary to execute real Harness actions and complete a
case. The missing `System:` stop boundary is therefore fixed.

## Per-class findings

### Successful state path

B02 rejected an initial evidence-free `lh_task_done`, continued in the same
Task lane, chunk-read `input.txt`, wrote the exact derived JSON, committed Task
and Goal evidence, and returned `lh_final_answer`. This validates the intended
Goal → Task selection/binding → chunk → action/check → Task → Goal → Final
combination on the deployed RWKV.

### Successful steps incorrectly consumed retry budget

B01 wrote the exact greeting and read it back, then incorrectly selected
`read_json(greeting.txt)`. That was its first failed action, but the controller
used `len(task.attempt_ids) == 3` as the retry count, counting two prior
successful steps. It blocked as `task_attempt_budget_exhausted` even though the
workspace already passed external acceptance.

M03 shows the same structural flaw more strongly: six successful Task steps
preceded one failed `make_directory(users.json)`, and total steps were treated
as failure attempts.

### Schema-valid but state-inapplicable operations blocked the run

- B10 declared an empty workset after a rejected finish.
- M01 verified one collection member, then selected an action that did not bind
  any remaining pending member.
- M12 selected `lh_replace_task` for a Task that was not an active completed
  repair target.

These commands passed G1i and their operation schemas. Their failure is a
runtime-state observation and belongs back on the original Task lane; treating
it as a terminal model protocol error loses the explicit repair relationship.

M06 emitted `lh_task_done` with an extra `evidence` field. This is a true schema
failure and remains fail-closed; it is not included in semantic rejection.

## Corrective change for a new experiment

- Retry exhaustion now counts only FAILED/BLOCKED/INTERRUPTED attempts; it also
  records total successful Task steps separately.
- Empty workset, unbound collection action and state-inapplicable Task repair
  emit `task_operation_rejected` with exact workset/runtime facts and continue
  in the same Task lane.
- Parser/schema errors still rollback and stop with zero resampling.

Local verification is `69 passed`; unified control is `33 passed`.
