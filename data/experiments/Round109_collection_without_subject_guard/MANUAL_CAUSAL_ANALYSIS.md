# Round109 manual causal analysis

## Fixed result

- Agent completed: pass; external acceptance: fail; Strict: fail.
- 19 model requests, 1 Task, 10 Attempts, 0 repairs.
- Final was non-empty raw RWKV output.

## Chain

1. RWKV created one `collection_listing` Task for `services/`, exactly matching the
   disclosed collection topology.
2. It listed and read all eight actual service files without graph duplication or protocol
   blocking. The discovery Task completed.
3. At the Goal boundary, RWKV selected `lh_goal_done` instead of creating migration,
   report, and verifier Tasks. The controller accepted the empty completion command because
   required graph Tasks and evidence existed.
4. The Final response explicitly said only discovery completed and mutations/report/verifier
   were not executed, contradicting the persisted `completed` status.

## Root cause

Current frontier completion is structurally distinguishable from Goal completion in the
prompt, but `lh_goal_done {}` carries no persistent commitment about whether the frontier
was merely preparatory. The same RWKV can therefore make inconsistent Goal and Final
decisions, producing a false positive.

## Next registered change

Make RWKV declare each proposed frontier as `prerequisite` or `deliverable`. Persist that
role on its Tasks. Reject `lh_goal_done` when no active completed deliverable Task exists;
require another RWKV `lh_tasks` call. The controller neither parses the Goal nor assigns the
role.
