# Round79 model input contract

Date: 2026-08-14

Status: architecture analysis retained as the input-first rationale. The
normative frozen contract and selected output grammar are now defined in
`UNIFIED_MODEL_IO_SPEC.md`.

## 1. The contract is the token sequence

RWKV is used as a continuation model. The authoritative model input is therefore
the exact ordered token prefix submitted to the tokenizer or already resident
in the native recurrent state. Names such as `GoalState`, `ContextBundle` and
`TaskNode` have no meaning to the model unless their serialized bytes form a
clear and stable continuation.

Every generation audit must record:

- input state/checkpoint digest;
- newly appended bytes and token IDs;
- full logical transcript digest;
- selected model and tokenizer version;
- sampling parameters;
- output bytes/token IDs and candidate output-state digest.

## 2. What the current implementation sends

### Task decomposition

One fresh prompt contains:

1. a long planning role and many positive/negative rules;
2. the immutable Goal and caller constraints;
3. a full current workspace manifest;
4. a compact effect catalog for every registered action;
5. an example Task batch and strict field-count instructions;
6. an open `### Assistant` JSON fence with a prefilled `{`.

It receives no prior RWKV state.

### Initial Task step

One new, independent prompt contains:

1. a different task-step role and completion rules;
2. current attempt ID;
3. usually empty deterministic checks;
4. Controller-calculated allowed decisions;
5. an evidence-ref index;
6. a reconstructed capsule containing Goal, active Task, compact action ledger,
   dependency outputs, selected evidence and latest failure;
7. the complete JSON schema for every registered action;
8. another open `### Assistant` JSON fence.

It does not continue the planning state that created the Task.

### Post-action Task step

Another fresh prompt repeats the same task-step instructions and all action
schemas, then adds:

1. the current action result and deterministic effect checks;
2. a reconstructed history of prior attempts;
3. selected memory/evidence payloads;
4. Controller-calculated decision feasibility and opaque evidence IDs.

The model must distinguish the current action from historical actions inside
serialized JSON. The distinction is not represented by a native temporal state
boundary.

### Collection Task

The current path may insert two more independent prompt roles:

- member declaration: full Task object, existing member snapshot, grounded
  workspace candidates and reconstructed observations;
- member action: Task summary, pending member objects, reconstructed
  observations and every action schema.

After each action, Task completion may be decided deterministically from the
member ledger or by yet another task-step prompt. The model does not receive one
unbroken collection trajectory.

### Failure and recovery

Failure analysis receives a fresh failure-classifier instruction, feasible
decisions, recovery capsule and latest attempt. Recovery-gap selection then
changes prompt dialect to `System: Tools / User / Assistant`, whereas most other
calls use `### User / ### Assistant`. Replan makes another fresh request with the
failure view, recovery gap, Goal/observation projection, workspace manifest and
existing Task IDs.

### Goal frontier and final answer

Goal frontier receives a fresh reviewer role plus a large capsule containing:

- immutable request and constraints;
- full current workspace manifest;
- completed Task history and member snapshots;
- up to 32 action observations / 32,000 output characters;
- an evidence registry containing checks, content and artifacts;
- plan generation.

It must output a six-field administrative object and echo exact evidence IDs.
The final answer is a separate fresh prompt containing the original request and
a verified-state rendering.

## 3. Why the current input is unsuitable

The current input is internally auditable, but it is not a stable continuation
distribution:

- the prompt dialect changes within one run;
- semantic roles change on independent calls;
- the Goal and static schemas are repeatedly injected instead of remaining in
  the prefix state;
- chronology is reconstructed as nested JSON rather than expressed as actual
  preceding turns;
- current and historical actions can share the same field names inside one
  object;
- raw facts, Controller-derived feasibility, opaque IDs and output-format rules
  compete for attention;
- the model is asked to copy administrative state that the runtime already
  owns;
- trimming can remove evidence/dependencies while leaving the role prompt and
  output contract intact.

This architecture makes output control depend on the model correctly decoding a
new ad hoc program at every call.

## 4. Required input shape

RWKV-LH will use one continuation dialect for the entire run. The selected wire
form is the locally implemented G1i-aligned continuation and must pass the
preregistered empirical stability gate; its logical structure is fixed:

```text
System: Tools: <canonical tool and control-operation definitions>
System: Protocol: <short immutable continuation rules>

User: Goal: <verbatim user request and caller constraints>
User: Initial observation: <bounded raw workspace metadata>

Assistant: <first command>
User: Function output: <typed raw event 1>
Assistant: <next command>
User: Function output: <typed raw event 2>
Assistant: <next command>
...
```

With native recurrent state, only the new `User: Function output` segment and
the next assistant boundary are appended after bootstrap. With prompt replay,
the identical canonical transcript is replayed byte-for-byte. Prompt replay is
a compatibility transport, not a different semantic prompt. Large inputs are
not appended to one unbounded lane: they use the forked chunk and bounded reduce
topology defined in `CHUNK_CONCURRENCY_DESIGN.md`.

## 5. Bootstrap input

The first and only static prefix contains:

1. canonical real-tool schemas from `ActionDefinition`;
2. canonical control-operation schemas;
3. one short rule: emit exactly one registered command after each event;
4. the verbatim Goal and caller constraints;
5. bounded initial workspace metadata clearly labelled as metadata, not file
   content.

The Goal, tools and general protocol are not repeated at later calls. There are
no benchmark-specific negative instructions and no examples whose field names
can be copied into the live decision.

## 6. Per-call appended input

### After an action

Append exactly one typed event containing:

```text
event_id
active_task_id and revision
executed command digest
raw bounded tool result
deterministic check facts
workspace delta / artifact hashes
pending workset identities, when applicable
```

Do not append a prose summary, a full historical ledger, a new role
specification, all tools again, or a list of permitted semantic decisions.

### After a protocol failure

Do not append a synthetic “format correction” instruction and do not sample
again from the parent state. Reject the candidate state and persist the failure.
The next semantic transition can occur only after an explicit recovery event.

### After Task completion or repair

Append one durable Task transition event containing the Task revision,
checkpoint-bound observation refs and new frontier. Do not ask the model to echo
the evidence registry. A repair is another typed event in the same chronology,
not a switch to a reviewer persona.

### At Goal completion

The same continuation lane emits the Goal-finish command after seeing the final
Task transition. No separate Goal-review prompt reconstructs the run. The final
user-facing answer may be generated in the same state or a clearly identified
fork whose parent checkpoint is recorded.

## 7. Raw fact and size rules

- Preserve exact user text and exact bounded tool output.
- Page large files through actions; never replace unseen content with a model or
  Controller summary.
- Append workspace deltas, not a complete manifest after every action.
- Stable identifiers are allowed in input for provenance, but the model never
  has to copy them into its command.
- Member status is derived from bound actions and checks; only newly selected
  member identities are semantic output.
- Static tool definitions appear once per native session.
- Every truncation/page boundary is explicit in the event so absence cannot be
  mistaken for completion.

## 8. Primary acceptance questions

Before evaluating E2E output, every recorded call must answer:

1. What exact new facts were appended since the preceding generation?
2. Did the model receive them in causal order?
3. Did any static instruction or schema change?
4. Was any raw fact replaced by a reconstruction or summary?
5. Did the model inherit the committed RWKV state from the preceding command?
6. Was the candidate state committed only after structural validation?
7. Could the same bytes be replayed to reproduce the logical prefix?

If these cannot be answered from the audit, the model output is not valid
evidence about RWKV long-horizon capability.
