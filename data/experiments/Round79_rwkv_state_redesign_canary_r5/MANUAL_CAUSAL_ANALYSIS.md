# Round79 unified lane short7 r5 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `0/7`
- External acceptance: `0/7`
- Agent completed: `0/7`
- Every case made exactly three model requests: Goal, Task operation selection,
  and the locked operation binding.
- No action attempt was created because all binding candidates failed at the
  same candidate boundary.
- The full90 gate failed; full90 was not run.

## Locked selection worked

All observed binding calls kept the selected function. Examples include:

- B01 selected and bound `write_file` with exact greeting content/path.
- M01 selected and bound `lh_workset` with service members.
- M03 selected and bound `read_file(users.json)`.
- M06 selected and bound `lh_chunk_map(selection.txt)`.
- B02, B10 and M12 selected and bound `lh_task_done`; these semantic finish
  claims lacked evidence and must be returned to the same Task lane, not format
  normalized.

Cross-schema `task_id/scope_id` pollution from r4 disappeared. The two-stage
single-tool input therefore fixed the intended schema-choice boundary.

## Earliest common failure

Each raw binding response began with one complete valid `function/params` JSON
object and then continued with a predicted next transcript segment beginning:

```text
System: Tools: ...
```

The completion stop set covered next `User:`, next `Assistant:` and a closing
fence, but not next `System:`. The strict parser correctly reported `Extra
data`; it did not scan or truncate the candidate. Once tool scoping introduced
mid-lane System blocks, the stop boundary had to include the System role too.

## Corrective change for a new experiment

- Add `\n\nSystem:` to the generation stop suffixes. This is a decoding boundary,
  not post-generation normalization; returned candidate bytes remain exact.
- When a schema-valid `lh_task_done` lacks evidence or has pending collection
  members, append a typed `task_completion_rejected` event to the same Task
  lane. This is a new observation after a semantic claim, not a format retry or
  resample.

Local verification is `67 passed`; unified control is `31 passed`.
