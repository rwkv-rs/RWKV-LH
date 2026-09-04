# Round79 unified lane short7 r2 causal analysis

Date: 2026-08-14

## Result and gate

- Strict: `0/7`
- External acceptance: `0/7`
- Agent completed: `0/7`
- Each case made one Goal-lane request; no Task or action was created.
- The preregistered full90 gate failed, so full90 was not run.

## Earliest errors

Six candidates were complete `function/params` JSON calls selecting `lh_tasks`,
but every first Task placed its own key in `after`. The validator correctly
rejected all six as `task cannot depend on itself`:

- E2E-B01
- E2E-B02
- E2E-B10
- E2E-M01
- E2E-M03
- E2E-M06

E2E-M12 selected `lh_tasks` but mixed in the `target_task` field from
`lh_replace_task` and returned incomplete JSON. It was rejected without another
generation.

## Exact input delta from the first canary

For the same B01 Goal, the frozen checkpoint transcripts differ at only one
bootstrap instruction line:

```diff
-Return only a JSON function call.
+Return only one JSON function call with exactly this shape: {"function":"<tool-name>","params":{}}
```

The tool definitions, Goal event, model, sampling and evaluator are otherwise
the same. The added empty-call exemplar successfully forced the top-level
field spelling, but it also changed the continuation distribution: six Task
batches became self-dependent and one call blended two control schemas. This
is an input-design regression in front of a base continuation model, not a
reason for the runtime to silently remove dependencies.

The original Task schema also described `after` only as an array of strings.
It did not tell the model that values must be earlier prerequisite keys, that
the first Task uses `[]`, or that self/later references are forbidden.

## Corrective change for a new experiment

- Restore the native G1i-style natural instruction without an inline JSON call
  exemplar.
- Keep one strict accepted wire object, `function/params`; state the two field
  roles in prose.
- Put `after` semantics and uniqueness in the authoritative Task JSON Schema.
- Clarify lifecycle preconditions in Goal/chunk/reduce/final control
  descriptions.
- Preserve fail-closed validation: no self-dependency deletion, alias
  normalization or semantic resampling was added.

Local verification after this change is `63 passed`; the unified control gate
is `27 passed`.
