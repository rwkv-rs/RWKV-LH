# RWKV-LH unified model I/O specification

Version: `rwkv-lh.model-io.v1-draft`

Date: 2026-08-14

Status: normative design freeze for implementation and fixed ablation. The
logical protocol is fixed here. Its acceptance still requires the registered
output-stability and E2E gates; native recurrent transport is unavailable in
the current deployed server.

Normative terms `MUST`, `MUST NOT`, `SHOULD` and `MAY` are binding for the new
path.

## 1. Design invariant

Each RWKV lane MUST look like one normal continuation trajectory:

```text
bootstrap once
  -> runtime event
  -> exactly one model command
  -> exact action/result event
  -> exactly one model command
  -> ...
```

The runtime MUST NOT invent a semantic decision. The model MUST NOT be asked to
echo runtime-owned facts. Native recurrent state, when present, carries causal
continuity; the durable journal carries exact facts and crash recovery. Neither
replaces the other.

## 2. One wire dialect

All semantic calls MUST use the model's G1i-aligned tool continuation. Hash-role
JSON prompts and request-specific role prompts are forbidden in the new path.

The lane bootstrap is exactly:

````text
System: Tools: <canonical JSON array of lane-visible definitions>
Return only a JSON function call. Use "function" for the tool name and "params" for its parameters.

User: <immutable lane assignment>

Assistant: ```json
````

The model emits exactly one call:

```json
{"function":"<operation>","params":{}}
```

After deterministic validation and execution, the next append is:

````text
<canonical completed call>

User: Function output: <canonical event JSON>

Assistant: ```json
````

The call MUST be one UTF-8 JSON object with exactly `function` and `params` and
must preserve string bytes after JSON decoding. JSON-internal indentation is
allowed because the G1i base model emits it naturally; field aliases, Markdown
and prose outside the open fence are forbidden. Prompt-replay transport replays
the exact candidate bytes; native transport feeds only the new suffix into the
committed state.

Generation MUST stop before a subsequent `System:`, `User:`, `Assistant:` or
fence boundary. A role marker is continuation framing, not part of the current
candidate and is never removed by a post-generation normalizer.

The final user answer MUST use `lh_final_answer(text)` from a fork of the
checkpoint that accepted `lh_goal_done`. The runtime delivers the decoded
`text` bytes. The Final lane MUST NOT mutate the coordinator lane, and its
output cannot change Goal status.

## 3. ModelSession contract

Every transport MUST implement the same interface:

```text
bootstrap(lane_kind, assignment, visible_definitions) -> committed checkpoint
append(checkpoint, event) -> committed checkpoint
fork(checkpoint, lane_kind, assignment) -> child checkpoint
generate(checkpoint, sampling, max_output) -> candidate output + candidate checkpoint
commit(candidate checkpoint, command_digest) -> committed checkpoint
rollback(candidate checkpoint) -> original committed checkpoint
export(committed checkpoint) -> durable transport record
import(durable transport record) -> committed checkpoint
```

Two implementations are allowed during migration:

- `prompt_replay`: stores the canonical byte transcript and reconstructs the
  prompt; it MUST report that no recurrent state was used;
- `native_rwkv`: stores an opaque server state handle plus export metadata; it
  MUST support create/resume/fork/commit/rollback/export/import before it can be
  used as native-state evidence.

Caching a prompt prefix is a performance optimization and MUST NOT be reported
as recurrent-state continuity.

## 4. Lane types

Only these semantic lanes exist:

| Lane | Receives | May emit |
|---|---|---|
| Goal coordinator | Immutable Goal, Task frontier/results, repair and Goal checks | Task batch, Task repair, Goal completion |
| Task | One active Task, exact relevant events and workset state | Harness action, workset delta, Task completion, Task replacement request |
| Chunk worker | One parent checkpoint plus one exact chunk assignment | One canonical chunk result or scoped artifact proposal |
| Reduce | Stable ordered child results within a token budget | One canonical intermediate/root result |
| Final answer fork | Accepted Goal checkpoint and verified result projection | `lh_final_answer(text)` only |

There are no independent member-declaration, member-action, failure-analysis,
gap-selection, replan or Goal-review roles. Their semantics occur as the next
command in the existing Goal or Task lane after the corresponding typed event.

## 5. Command set

One generation MUST produce exactly one registered function call. Harness
actions retain their authoritative runtime schemas and names. Control commands
are:

```text
lh_select_operation(operation)
lh_tasks(tasks)
lh_workset(items, sealed)
lh_chunk_map(sources, instruction)
lh_task_done()
lh_reopen_task(target_task)
lh_replace_task(target_task, tasks)
lh_goal_done()
lh_chunk_result(result)
lh_reduce_result(result)
lh_final_answer(text)
```

The minimal Task shape is:

```json
{"key":"local-id","objective":"one immediate semantic step","done_when":"observable postcondition","after":["earlier-key-in-this-batch"]}
```

The runtime allocates global Task IDs. It MAY derive display titles, priority,
revision numbers, ready state and retry budgets. It MUST NOT derive or rewrite
`objective`, `done_when`, dependencies or repair relation.

A workset item contains only semantic identities needed by the Task:

```json
{"id":"stable-member-id","source":"optional-ref","target":"optional-ref"}
```

The runtime owns `pending`, `attempted`, `verified`, failure and artifact status;
the model does not output the full status ledger. `sealed=true` is a semantic
claim by the model and becomes a decision record. Completion is still blocked
when the durable ledger contains a required pending member.

Control commands MUST NOT contain `schema_version`, `reason`, evidence IDs,
checkpoint IDs, attempt IDs, status echoes, null placeholders or full history.
The runtime binds a command to all visible event refs and the input checkpoint.

## 6. Typed runtime events

Every model-visible update MUST be one canonical event with:

```text
event_type
event_version
event_id
scope_id
payload
content_refs
complete / truncated / continuation metadata
```

Required event classes are:

```text
goal_started
task_activated
action_result
checks_result
workset_status
chunk_assigned
chunk_result
reduce_result
task_result
repair_applied
failure_observed
budget_boundary
```

`event_id`, refs, digests, timestamps and status are runtime-owned. Payload
fields that are facts MUST be copied from the actual Harness result or durable
journal, never regenerated as prose. Model-authored semantics MUST remain
identifiable as model-authored.

Current and historical actions are separated structurally: the most recent
`action_result` is the result of the immediately preceding committed call;
older calls remain ordered events. A parser MUST inspect only the generated
candidate bytes and MUST NOT recursively scan prompt/history objects for a
current action.

## 7. Token and truncation rules

For every generation:

```text
input_budget = 16384
             - BOS_tokens
             - safety_tokens
             - maximum_output_tokens
```

For a chunk assignment:

```text
raw_chunk_budget = input_budget
                 - fixed_lane_prefix_tokens
                 - current_event_metadata_tokens
                 - boundary_carry_tokens
```

The real deployed RWKV tokenizer is authoritative. Character and byte offsets
are coverage coordinates, not capacity estimates.

The renderer MUST preflight the complete final bytes. It MUST NOT silently drop
an event, evidence record, dependency result, failure or action definition.
When required input does not fit, it MUST do one of the following before model
generation:

1. page or chunk raw content with exact coverage metadata;
2. provide an artifact/content ref and request the causally needed range;
3. reduce already canonical child results through the registered reduce tree;
4. fail the transition as `input_budget_unrepresentable`.

It MUST NOT substitute ellipsis or a prose summary unless the Task itself asks
for summarization. Every visible truncation MUST carry `complete=false`, exact
range and continuation cursor. A completion command cannot close a required
open cursor or unsealed workset.

## 8. Chunk and concurrency rules

All parallel worker lanes MUST fork the same immutable Task parent checkpoint.
Each receives one `ChunkDescriptor` containing source digest, byte/core ranges,
overlap, chunk digest, adjacent IDs and split-policy version.

Child recurrent states MUST NOT be averaged, concatenated, selected by
last-writer or committed into the parent. Children merge only through canonical
`chunk_result` events or exact artifact proposals. Results are ordered by source
identity and core range, then reduced with deterministic token-bounded fan-in.

Concurrency is allowed only for dependency-independent lanes and disjoint or
read-only mutation domains. Same-object mutations, ordered carry dependencies
and non-idempotent effects remain serial. Concurrency 1 and concurrency N MUST
produce the same descriptor set, canonical result order, reduce-tree identity
and deterministic external result.

## 9. Candidate validation and state commit

Generation is transactional:

1. generate candidate bytes and candidate state from committed checkpoint S;
2. parse only those candidate bytes;
3. validate exactly one registered operation, argument schema, scope and safety;
4. persist the candidate decision record;
5. commit the candidate state;
6. create an Attempt and execute, or apply the control transition;
7. append the exact resulting event.

If steps 2 or 3 fail, the runtime MUST rollback candidate state, persist the
protocol failure and stop that transition. It MUST NOT resample, autocomplete,
normalize semantic fields, choose a default operation or treat truncated fields
as a decision. A later retry is a new explicit event and experiment attempt,
not transparent format repair.

## 10. Evidence and completion

For every accepted command the journal records:

```text
lane_id
input checkpoint/state digest
visible event IDs and content digests
raw output bytes and command digest
output checkpoint/state digest
sampling parameters and model build
runtime validation result
```

`lh_task_done` and `lh_goal_done` are semantic decisions. The runtime binds the
visible observation/check refs automatically. Runtime guards may reject
completion when required facts are absent, a cursor/workset is open, a required
check failed, a chunk range is uncovered or a repair is unresolved. A guard may
not convert `act` into completion or decide that semantic user intent was met.

Goal input receives exact accepted Task-result events, not unverified Task
narratives. If Goal detects a false Task result it MUST emit `lh_reopen_task` or
`lh_replace_task`; the journal records `detected_by`, `target_revision`, relation
and successor refs.

## 11. Action definitions

One `ActionDefinition` registry MUST generate all of the following:

- model-visible G1i definition;
- deterministic argument validator;
- Harness dispatcher contract;
- effect/idempotency/concurrency metadata;
- audit rendering and tests.

No action may have separately handwritten model and executor schemas. The
registry MUST execute a startup consistency check. `write_json`,
`read_json.start_byte`, `read_json.max_tokens` and all future fields must have identical names, types,
defaults and limits at every layer.

Definitions are scoped inside one continuing lane. Prompt replay may physically
repeat the prefix, but metrics MUST report `static_replay_tokens` separately
from new event tokens. Task command materialization has two committed stages:
RWKV first emits `lh_select_operation(operation)` from the registry-derived
option projection; the runtime then appends `operation_selected` and exposes
only that operation's authoritative definition. RWKV binds params exactly once
and MUST emit the already selected function. A mismatch rolls back and stops;
it never resamples or replaces the committed selection. Chunk, reduce and Final
forks similarly append a one-function tool scope.

## 12. Persistence and crash recovery

The journal is the write-ahead log. Before any side effect, it stores the
accepted command, checkpoint, Attempt ID and idempotency metadata. After the
side effect, it stores raw result and post-action snapshot before appending the
model-visible result event.

On recovery, the runtime imports the last committed checkpoint and reconciles
the Attempt journal:

- accepted but not executed: execute only under registered safe semantics;
- execution outcome unknown: query/read back before any repeat;
- executed but event not appended: append the persisted exact result;
- candidate uncommitted: discard it;
- verified chunk/reduce node: reuse by digest, never regenerate silently.

Native state export/import MUST preserve registered next-token behavior within
the preregistered numerical tolerance. If it cannot, native transport fails its
gate and prompt replay remains the only truthful transport label.

## 13. Required audit metrics

Every run MUST report:

```text
state_transport and state-server build
lane/checkpoint/fork counts
new event tokens, static replay tokens and output tokens
command parse/contract validity
semantic command/action/argument agreement
chunk coverage and reduce-tree digests
protocol failures without resampling
Strict, External, Agent-completed, FP and FN
earliest wrong transition
```

No architecture claim is complete from unit tests alone. Acceptance is governed
by `REDESIGN_PROTOCOL.md` and the full project completion conditions.
