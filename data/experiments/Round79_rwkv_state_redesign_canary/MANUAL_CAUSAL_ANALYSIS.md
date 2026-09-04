# Round79 unified lane short7 first-run causal analysis

Date: 2026-08-14

## Result

- Strict: `0/7`
- External acceptance: `0/7`
- Agent completed: `0/7`
- Every case stopped after exactly one Goal-lane model request; zero Tasks and zero attempts were created.

This run did not exercise Task execution, evidence binding, worksets, chunking or
repair. It therefore cannot be used to judge those mechanisms.

## Earliest common failure

All seven event logs end at `goal_lane_initial_frontier` with the same runtime
error:

```text
model command requires exactly name and arguments
```

The model traces show that all seven candidates selected the correct
`lh_tasks` control and produced concrete Task frontiers. Four candidates used
the actual G1i fields `function/params`:

- E2E-B01
- E2E-B02
- E2E-M01
- E2E-M06

Three used `function/arguments`:

- E2E-B10
- E2E-M03
- E2E-M12

The parser used by this run incorrectly required the internal persistence shape
`name/arguments`. Therefore even the four protocol-conforming candidates were
rejected before Task creation. The shared failure location, one-call traces and
raw candidates establish an I/O boundary defect rather than seven independent
semantic planning failures.

## Corrective change

The sole model wire form is now exactly one JSON object with keys
`function/params`. Pretty-printed JSON is accepted because whitespace inside a
JSON object is not semantic; leading/trailing bytes, aliases, envelopes, prose,
Markdown and multiple candidates remain rejected. Internal runtime records may
still serialize `name/arguments`, but that representation never appears as an
accepted model wire dialect.

`ModelSession.commit` reparses the exact candidate and compares the decoded
command. A format failure still rolls back and blocks with zero semantic
resampling.

## Verification before r2

- Full local suite: `62 passed`
- Unified control regression: `26 passed`
- Added positive coverage for pretty `function/params`
- Added negative coverage for `function/arguments` and `name/arguments`

The r2 run is a new preregistered experiment. The original output directory,
raw traces, evaluator, selected cases and gate remain unchanged.
