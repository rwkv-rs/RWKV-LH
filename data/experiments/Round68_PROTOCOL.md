# Round68 preregistered protocol: quality-first RWKV review pipeline

## Frozen baselines

- Uploaded Round46 full90: Strict `31/90`, External `32/90`, Agent `55/90`,
  FP `24`, FN `1`.
- Uploaded Round46 fixed15: Strict `6/15`, External `7/15`, Agent `13/15`,
  FP `7`, FN `1`.
- Round67 fixed15: Strict `3/15`, External `5/15`, Agent `4/15`, FP `1`,
  FN `2`.
- Round67 offline: pytest `416/416`, LH-Control `30/30`, frozen catalog and
  31-file architecture checks `5/5`.

The manual causal source is
`data/experiments/Round67_canary/MANUAL_CAUSAL_ANALYSIS.md`.

## Objective

Increase correctness by stopping an erroneous state transition before later
prompts treat it as authoritative history. Request count, latency, output-token
count and parallel speed are recorded but have no pass/fail threshold in this
round.

All semantic choices remain RWKV choices. A review response may cause RWKV to
revise its own proposal; controller code may validate protocol, references,
scope, action metadata and observed effects, but may not choose a preferred
Goal, action, evidence decision, recovery gap, artifact value or final answer.

## Preregistered changes

### 1. One three-stage Goal path

Replace the one-pass Goal parse path with one production path:

1. RWKV produces a structurally valid draft Goal.
2. A fresh focused RWKV request audits that exact draft only against the
   immutable user request and caller constraints. It reports approve/revise and
   concrete omissions, inventions and redundancies.
3. A fresh RWKV request always submits the final complete Goal after seeing the
   original request, draft and audit. The controller accepts only this final
   proposal.

Draft and final use the same strict closed schema. No invalid field is coerced,
and controller code never applies audit edits. Protocol retries may request a
new full RWKV response. The accepted Goal records the draft, audit and final
request ids for provenance.

### 2. Progressive, reviewed action commitment

Replace the single request containing every tool schema with one action path:

1. RWKV selects exactly one registered action name from a compact catalog of
   names, observable effects and read/write properties.
2. Only the selected action's exact schema is shown; RWKV supplies all arguments.
3. A fresh focused RWKV request reviews the complete call against the active
   Task, immutable Goal, exact observed paths/values and tool effect. It returns
   approve/revise with a concrete reason.
4. On revise, RWKV repeats selection and arguments with the review attached.
   Up to three semantic rounds are allowed. No controller fallback action exists.

The action that executes is always the last RWKV-approved call. Format
normalization may convert only registered wire envelopes and never changes the
tool name or arguments.

### 3. Evidence-bound, reviewed Task commit

Replace the three-field Task commit with a closed decision containing reason,
decision and `evidence_refs`. RWKV must select non-empty existing references for
pass; replan uses an empty list. The available registry explicitly distinguishes
action result, post-action target snapshot, dependency observation and
deterministic effect check.

A second focused RWKV request reviews the draft commit and emits the final
decision and refs. The controller checks only that refs exist in the displayed
registry and remain byte/digest-identical. It does not infer whether those refs
are semantically sufficient. Both draft and final are audited.

### 4. Reviewed Goal-criterion evidence

After RWKV chooses supported/insufficient and source bindings for one criterion,
a fresh RWKV request receives the fixed criterion, complete source catalog and
draft decision. It must emit the final supported/insufficient decision and
binding. The existing causal-source and independent-expected-source validators
apply to the final response only. This targets current/original revision
confusion without controller-side answer selection.

### 5. Per-path batch observation

`read_files` continues to read only the exact model-selected paths. One missing,
non-file, unreadable or invalid UTF-8 selection no longer discards other selected
observations. It returns one ordered record per requested path with
`status=ok|missing|not_file|invalid_utf8`, exact relative path, and content/digest
fields only when observed. Overall action success means the batch operation
returned the complete per-path record set; per-path status remains data for RWKV.

No path is discovered, substituted or inferred by the Harness. The format is a
general observation primitive, not a task-specific recovery rule.

### 6. RWKV-selected recovery gap before Task generation

Failure and Goal-obligation recovery first ask RWKV to select exactly one gap:
the earliest unresolved Goal obligation or a specific falsely completed/failed
predecessor that must be repaired. The response contains a stable existing
criterion/task id when one exists and a textual gap statement. A second RWKV
request proposes up to four Tasks only for that selected gap.

The controller validates ids and the Task-batch schema but does not choose,
truncate, reorder or rewrite the gap or Tasks. Protocol correction gets up to
three attempts because efficiency is not a constraint.

### 7. Recovery and frontier control without semantic substitution

- Remove the rule that changes `retry_same` or `reselect_action` to `replan`
  after repeated failures. The same-failure facts remain visible to RWKV.
- An unsafe blind retry of a non-idempotent action is rejected as a safety
  boundary and returned to RWKV for a new decision; the controller does not
  substitute `reselect_action`.
- Exhausted retry budget routes to a fresh RWKV recovery decision with only
  feasible choices shown, rather than rewriting a returned choice.
- Materialize/execute a side-effecting frontier Task before proposing another
  independent side-effect Task. Read-only actions may still be proposed and
  executed in parallel, preserving the large-project parallel-read acceptance
  target while preventing later writes from being proposed against a stale
  pre-effect snapshot.

## Explicit non-changes

- No hidden benchmark answer, grader output or external acceptance result enters
  any model prompt or runtime decision.
- No semantic allowlist maps task wording to tools, paths, values or answers.
- No majority vote, controller ranking, answer repair, output field insertion,
  Task truncation or criterion merge is added.
- The final user-facing answer remains unchanged RWKV output.
- MCP, external service plugins, multi-model routing and subagents remain out of
  scope.

## Frozen validation

Offline:

- full pytest;
- clean LH-Control `30/30`;
- frozen action catalog/reference regressions;
- 31-file parallel summarize/read architecture regression;
- new Goal draft/audit/final provenance tests;
- new action revise/approve and no-controller-fallback tests;
- new Task/criterion final-review evidence-reference tests;
- per-path batch read mixed-status, traversal and duplicate-path tests;
- recovery gap identity, invalid-id, predecessor-repair and no-semantic-override
  tests;
- serial side-effect proposal and parallel read-only frontier tests.

Live:

- run the unchanged fixed15 canary only after all offline gates pass;
- run full90 only at Strict >= `6/15`, FP <= `3`, FN <= `1`, with B01/B02/B10
  Strict;
- upload only if full90 Strict > `31/90`, FP <= `24`, FN <= `1`, and every
  offline gate passes.

External acceptance, Agent completion, request count and latency remain reported
for diagnosis, but only correctness/safety gates decide promotion.
