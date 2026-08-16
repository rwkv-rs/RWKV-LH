# Round79: RWKV capability and interface architecture audit

Date: 2026-08-14

Status: design gate. No architecture improvement or E2E completion is claimed.

The exact 218-call input inventory is in `CURRENT_MODEL_INPUT_AUDIT.md`. The
normative unified contract and file-level execution plan are in
`UNIFIED_MODEL_IO_SPEC.md` and `UNIFIED_REFACTOR_PLAN.md`.

## 1. Correction to the Round78 framing

The eight Round77 failures are observations, not eight independent architecture
centres. Round78 fixed several real deterministic defects, but then continued
to add request types, prompt rules and normalization paths around individual
failures. That direction underweighted two system-wide causes:

1. the deployed model interface does not carry RWKV recurrent state between
   semantic transitions;
2. the current protocol asks a 13.3B RWKV model to repeatedly reproduce a wide
   administrative schema under long, duplicated prompts.

The corrected design must account for model capability and output stability.
It must also exploit RWKV's state-passing architecture instead of treating the
model as a stateless JSON generator. Deterministic interface mismatches remain
runtime defects and must not be excused as model weakness.

## 2. Local evidence

### 2.1 No RWKV state reaches the current execution chain

`ModelInvoker.invoke_text` ultimately calls only
`text_completion(prompt, max_tokens, stop)`. The current completion request has
no state handle, parent checkpoint or commit/rollback identity. The deployed
server returns HTTP 404 for authenticated `/v1/capabilities`, and its 17-path
OpenAPI inventory contains no state/resume/fork/commit/rollback/export/import
path.

All audited rounds therefore report:

```text
source = prompt_replay_fallback
create/resume/fork/commit/rollback/export/import = false
```

Prompt or prefix caching is not evidence of model-state continuity. It can
reduce compute while preserving exactly the same stateless request semantics.

### 2.2 One semantic trajectory is fragmented across independent calls

The current production path can invoke:

```text
task_decomposition
task_step
task_member_declaration
collection_member_action
failure_analysis
failure_recovery_gap_selection
replan
goal_frontier_step
final_answer
```

These calls do not resume one cognitive state. Each independently receives a
fresh role prompt plus projections of Goal, Task, history, evidence and tool
schemas. For example, the Round78 M06 r3 path made eight independent model
requests: one decomposition, two task steps, two member declarations and three
member-action calls. The model had to reconstruct the same semantic trajectory
at every boundary.

### 2.3 Prompt and output proportions show interface overload

The fixed audit over Round77 and Round78 r2/r3/r4 contains 218 model requests.
The most frequent paths are:

| Request | Count | Mean input tokens | Median | Max | Mean output chars |
|---|---:|---:|---:|---:|---:|
| `task_step` | 131 | 4,117.1 | 3,753 | 10,310 | 518.5 |
| `collection_member_action` | 10 | 4,043.6 | 4,053 | 5,023 | 386.6 |
| `task_decomposition` | 24 | 2,306.9 | 2,304.5 | 2,485 | 1,411.0 |
| `goal_frontier_step` | 25 | 2,667.0 | 1,737 | 7,449 | 1,800.6 |

The model commonly reads thousands of tokens to emit a few hundred characters.
The prompt repeats the complete registered action schema even when the needed
transition is only one action or one completion bit. This load consumes model
capacity without adding task evidence.

### 2.4 Instability crosses cases and rounds

The same fixed cases change outcome while the recurrent-state capability remains
absent:

- B02 changes from externally correct but blocked to Strict PASS;
- M12 alternates between externally correct and incorrect while always blocked;
- B10 and M03 alternate between blocked and false-positive completion;
- M06 sometimes reaches the correct external workspace but fails a later
  protocol transition.

This cross-round variability is incompatible with a purely case-local root
cause. It is consistent with semantic reconstruction and output instability at
every stateless boundary. It does not prove that recurrent state alone will
solve the cases; that requires a fixed ablation.

### 2.5 Advertised constrained output is not currently usable

The server OpenAPI schema advertises `structured_outputs` and `response_format`,
but the preregistered single JSON-schema request returned HTTP 500 with no model
output. The capability is therefore unavailable in the current deployment
until the server failure is diagnosed and a fixed probe passes. A declared
request field cannot be treated as an executable capability.

## 3. Three system roots

### R1. RWKV state discontinuity

The model is architecturally recurrent, but the deployed RWKV-LH path discards
the recurrent state after every completion. Long-horizon memory is rebuilt as
text by the Controller. This loses the state trajectory that distinguishes an
RWKV-native loop from generic prompt replay.

### R2. Semantic/output contract overload

The protocol splits planning, action selection, member selection, failure
classification and completion into different roles with different wide JSON
schemas. The model must emit schema versions, evidence IDs, member ledgers,
null fields and reasons that the runtime either already knows or can bind
deterministically. Format failure and semantic decision are therefore coupled.

### R3. Semantic decision and durable fact boundaries are mixed

The runtime should own raw facts: actions actually executed, observations,
artifact revisions, deterministic checks, member status and checkpoint
identity. RWKV should own semantic choices: what to do, whether the observed
Task is satisfied, whether to revise the plan, and whether the Goal is
satisfied. Asking RWKV to echo runtime facts creates drift; letting the runtime
invent semantic choices would hide model capability. Both are wrong.

## 4. Reclassification of the eight observations

| Observation | Primary root | Required treatment |
|---|---|---|
| Nested/single Task cannot enter Task batch | R2 | One minimal discriminated wire grammar; transport shape must not define semantics |
| Current and historical actions are confused | R1 + R2 | Append-only typed events in one state lane; never recursively search an undifferentiated prompt object |
| `write_json` declaration/execution mismatch | R3 | One runtime action definition is the only schema source; this is a deterministic code defect |
| Goal loses precise checks/post-action content | R3 | Durable raw observations and decision checkpoint binding; do not ask Goal to reconstruct evidence prose |
| Format failure resamples semantics | R2 | Candidate state commit only after syntax validation; rollback/block on format failure, never semantic resample |
| Multi-file Task loses remaining members | R3 | Runtime-owned workset facts and per-member action bindings; RWKV emits only member-selection deltas |
| Repeated generation damages a correct decision | R1 + R2 | One generation per state transition; constrained decoding when genuinely supported |
| False Task completion has no repair relation | R3 | Explicit durable transition relation (`reopen`/`replace`) bound to the detecting checkpoint |

The table is a causal routing guide, not a claim that the model is blameless.
Model semantic errors and model output errors must be measured separately.

## 5. Industry references and local adaptation

The official RWKV repository describes RWKV as an RNN whose next position uses
the prior hidden state, and its inference example explicitly passes `state`
between `model.forward` calls. RWKV-7 is also documented as having a relatively
small state. This supports a state-handle design, but it does not specify the
RWKV-LH workflow or prove better E2E accuracy:
[RWKV-LM README](https://github.com/BlinkDL/RWKV-LM/blob/main/README.md).

LangGraph's official design guidance separates raw durable state from prompt
formatting and uses checkpoints for recovery. That supports RWKV-LH's external
Execution Journal, but RWKV-LH must not copy LangGraph's generic node topology:
[Thinking in LangGraph](https://docs.langchain.com/oss/python/langgraph/thinking-in-langgraph),
[Persistence](https://docs.langchain.com/oss/python/langgraph/persistence).

The local conclusion is therefore not “adopt an industry framework.” It is:
use a small RWKV-native cognitive state beside a raw, durable execution journal,
with an explicit boundary between the two.

## 6. Target architecture

The primary contract is the exact token prefix presented to RWKV, not the
Python state schema. `MODEL_INPUT_CONTRACT.md` defines that prefix and its
append-only continuation rules. Output syntax is subordinate to this input
contract.

### 6.1 Two state layers

**RWKV Cognitive Session**

- opaque native recurrent-state handle;
- one Goal lane and task-scoped forks where isolation is needed;
- typed event append, generate, fork, commit, rollback, export and import;
- a candidate generation state is committed only after the command is
  structurally accepted.

**Execution Journal**

- immutable Goal and constraints;
- Task/workset definitions and revision relations;
- Attempt and action fingerprints;
- raw tool results and post-action snapshots;
- deterministic checks and artifact revisions;
- member pending/verified status;
- decision records that bind the model command to its input state checkpoint
  and the exact observation refs visible at that checkpoint.

The Cognitive Session is not the database. The Execution Journal is not a
second semantic model.

### 6.2 One minimal command grammar

Every semantic transition emits one discriminated command. The wire protocol
must not require `schema_version`, `reason`, evidence refs, null placeholders or
the full member ledger on every generation.

Implemented wire form:

```json
{"function":"<registered-action-or-control>","params":{}}
```

`function` selects a Harness action or lane control; `params` is validated by
that operation's sole registered JSON Schema. Real actions retain their
authoritative Harness schemas. Control operations are protocol operations, not
fake filesystem tools. No `name/arguments`, nested call envelope, prose or
Markdown variant is accepted on the wire.

When `lh_task_done` or `lh_goal_done` is emitted, the runtime creates the
evidence binding from the model's input checkpoint. The model does not copy
opaque evidence IDs, and the Controller does not decide semantic completeness.

### 6.3 Continuous transition

```text
checkpoint S_n
  -> append one typed observation/event
  -> generate one candidate command and candidate state S_n+1
  -> validate only syntax, tool contract and scope
  -> commit S_n+1 and execute, or rollback/block
```

There is no second semantic sample for format correction. A recovery decision
is a later explicit transition after a real failure event, not a replacement
sample for the rejected command.

### 6.4 Compatibility tier

Until the model server exposes native recurrent-state operations, RWKV-LH may
retain a prompt-replay compatibility tier for development. It must:

- use the same minimal command semantics;
- replay typed raw events, not reconstructed narrative state;
- report `state_transport=prompt_replay` in every experiment;
- never be used as evidence that RWKV recurrent state was exploited.

## 7. What remains valid from Round78

Keep:

- immutable literal Goal;
- single authoritative action definition and pre-side-effect contract checks;
- append-only Attempt/observation/artifact records;
- semantic freeze: one sample per transition;
- runtime-owned member completion status;
- evidence/checkpoint provenance and explicit repair relations.

Reassess or remove after the minimal protocol exists:

- independent member-declaration and member-action roles;
- independent failure-analysis and recovery-gap roles;
- Goal reviewer prompts that reserialize the whole state;
- normalizers that move/drop/insert administrative fields;
- prompt rules added to repair individual benchmark outcomes;
- model-authored full member snapshots and opaque evidence-ID echoing.

## 8. Phase gate

The next implementation phase may start only after a protocol is preregistered
for:

1. native state-server operations and crash recovery;
2. minimal command syntax/output stability;
3. exact separation of model semantic agreement from format validity;
4. prompt-replay versus recurrent-state ablation on fixed snapshots;
5. unchanged short7/full90 external acceptance and anti-cheating boundaries.

## 9. Source inventory

| Source | Version/use | SHA-256 |
|---|---|---|
| `Round77_canary/MANUAL_CAUSAL_ANALYSIS.md` | Per-case causal source | `716051f89749e05f28ed80448bb404d816431203ea830621097152614d54a2ed` |
| `Round78_architecture_fixes_canary_r3/runtime_doctor.json` | Deployed capability evidence | `c9f305b7e97b2af5682ae1625f8d3858e81601224ff8819ca7213489d9556938` |
| `temp/analyze_round78_rwkv_interface_global.py` | Fixed cross-round aggregation | `3292f6fc44164a988ac59b988982152bf5b4d6d2b7fb5661a9079f3915360ad7` |
| `Round79_rwkv_state_redesign/CAPABILITY_PROBE_PROTOCOL.md` | Preregistered server probe | `644370a05a8f36a6b4d3064e1699eee10ba192ab42b45824ec39c36754e60a2c` |
| `Round79_rwkv_state_redesign/CAPABILITY_PROBE_RESULT.json` | Captured sanitized probe result | `d89233c70f9c33deb4bf46e4d4c175e84deac4e34d134b8deabd3c042d3e345c` |

Cross-round aggregation command:

```text
uv run python /home/chase/GitHub/RWKV-LH/temp/analyze_round78_rwkv_interface_global.py
```
