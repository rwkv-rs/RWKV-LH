# Round67 preregistered protocol: immutable recovery and one Task-batch boundary

## Frozen baselines

- Uploaded Round46 full90: Strict `31/90`, External `32/90`, Agent `55/90`,
  FP `24`, FN `1`.
- Uploaded Round46 fixed15: Strict `6/15`, External `7/15`, Agent `13/15`,
  FP `7`, FN `1`.
- Round66 fixed15: Strict `4/15`, External `6/15`, Agent `4/15`, FP `0`, FN `2`.
- Round66 offline: pytest `408/408`, LH-Control `30/30`, frozen catalog/reference
  and 31-file parallel architecture regression `4/4`.

## Causal evidence

The manual source is `data/experiments/Round66_canary/MANUAL_CAUSAL_ANALYSIS.md`.
Round67 addresses only directly repeated structural failures before adding an
RWKV self-review stage:

- recovery omitted the immutable original request (M16);
- malformed Goal types were accepted (B24);
- Goal recovery and failure replan used inconsistent Task-batch transports
  (M03, M06, LH05, H12, H13);
- recovery batches truncated or repeated too much work (LH05, H12, H13);
- an otherwise complete action carried a copied `execution_capsule` decoration
  (M12, M16, M18).

## Preregistered changes

### 1. Immutable Goal capsule

Every Goal-obligation recovery capsule includes an immutable Goal block with the
exact original request, objective, constraints, complete success criteria and
digest. This block is never removed by bounded projection. The existing
unresolved criterion list remains a separate current-state projection.

### 2. Strict Goal proposal protocol

Goal proposal must contain exactly `schema_version`, `objective`, `constraints`,
and `success_criteria`; schema must be exact; objective must be a non-empty
string; constraints must be strings; and every criterion must contain exactly a
non-empty string `id`, non-empty string `description`, and boolean `required`.
No string/list/object is coerced into another type. A malformed proposal gets the
existing one correction attempt. No criterion is added, removed, merged, or
rewritten by controller code.

An RWKV semantic grounding reviewer is deliberately deferred so this strict
protocol change can be measured independently.

### 3. One G1i Task-batch transport

Both `goal_obligation_replan` and failure `replan` use the same fixed
`propose_task_batch` G1i tool. Its only semantic argument is the existing array
of exact five-field Tasks. The boundary adds the fixed Task-batch schema tag and
the controller still derives only the failed-task supersede mapping.

When this one tool is already uniquely fixed, exact bare `{tasks:[...]}` is a
registered wire form. It is wrapped with the fixed tool name, fully audited, and
then passed through the existing Task record projection. No Task or Task field
is generated.

### 4. Small iterative recovery frontier

Goal recovery and failure replan accept at most four Tasks total per response,
enforced in the displayed JSON schema and canonical validator. The existing
Goal recovery budget of 64 remains unchanged. This reduces truncation and makes
each round causally depend on actual observations rather than a speculative long
plan. It is a structure bound, not semantic Task selection.

### 5. Closed execution-capsule decoration

An otherwise complete single tool call may carry one top-level
`execution_capsule` object. The format boundary validates it is an object,
separates it without reading or applying any field, preserves the raw payload in
audit, and passes the unchanged name/arguments call onward. Unknown, non-object,
conflicting, incomplete, and multi-call forms remain rejected.

## Non-intervention boundary

RWKV still chooses every Goal field, Task, dependency, postcondition, action,
path, value, evidence decision and final answer. The changes preserve immutable
input, reject invalid types, constrain transport size, and normalize registered
wire representation only. They do not rank candidate answers, inspect hidden
acceptance, infer expected values, or alter RWKV's final output.

## Frozen validation and gate

- Full pytest, clean LH-Control `30/30`, frozen catalog/reference checks, and the
  31-file parallel summarize/read architecture regression.
- Run the unchanged fixed15 canary.
- Run full90 only at Strict >= `6/15`, FP <= `3`, FN <= `1`, with B01/B02/B10
  Strict.
- Upload only if full90 Strict > `31/90`, FP <= `24`, FN <= `1`, and every
  offline gate passes.

Latency and request count remain audit-only.
