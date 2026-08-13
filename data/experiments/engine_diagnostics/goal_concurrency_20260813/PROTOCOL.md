# Goal-proposal concurrency diagnostic pre-registration

Pre-registered: 2026-08-13 Asia/Shanghai, before any generation request to the restarted endpoint
`http://127.0.0.1:29610/v1`.

## Trigger and question

The unchanged Round12 core produced only `2/90` external passes after the previous engine update,
versus `11/90` under the older engine. `61/90` cases failed before Goal creation. A single local-UI
request had previously produced valid Goal, plan and actions. The user has now restarted the engine
and forwarded a new local endpoint on port `29610`.

This diagnostic asks one narrow question: **does Goal-proposal protocol validity degrade as client
concurrency rises on the restarted engine?** It does not test task execution or Agent quality.

## Fixed inputs and execution

- Public visible task text only: `E2E-B01` through `E2E-B30`, in numeric order.
- Source task hashes:
  - core30 `tasks.json`: `0bf73c9a86bd014f5a94e5686ffe744bbef6c560f4227e37d0b753b900481c4c`
  - extension48 `tasks.json`: `384d52b5395dbcb31947dbfd1cfe63167ccbe68ed8b03e675fddc32ffd25ec7b`
- Workspace string is always `/workspace`; the diagnostic neither creates nor reads workspace files.
- Caller constraints are the four fixed E2E generic constraints.
- Product code path is unchanged `LongHorizonModel.parse_goal`, including its existing maximum of
  two attempts and its existing sampling policy.
- One excluded warm-up uses B01 and is fully recorded.
- Scored diagnostic conditions run all 30 tasks once at max client concurrency `1`, `2`, `4`, and
  `8`, in that condition order. Every outcome is retained; there is no best-of-N selection.
- Script:
  `temp/diagnose_goal_parse_concurrency_after_restart_20260813.py`, SHA-256
  `61641c15c775fb965570608e417b2129d89880e0fb214a030c8576cec5aa884d`.
- Runtime fingerprint file SHA-256:
  `6a7cc74ea62d2816ff5565a3d68ff77ce7ccbb74fa5cff55219a80df2b7699ee`.

## Recorded data

For the warm-up and each case/condition, preserve:

- exact user request, constraints and workspace string;
- every full prompt and request ID;
- every raw response, visible projection, finish reason, local token count and SHA-256;
- parsed payload or protocol error;
- final Goal projection when valid;
- request/return/transport-failure counts and wall duration;
- endpoint/model/runtime health and visible-source hashes.

Output schema: `rwkv-lh.goal-concurrency-diagnostic.v1`.

## Metrics and interpretation fixed before results

Primary metric per concurrency: valid Goal count out of 30.

Secondary metrics: invalid-error distribution, requests per case, incomplete-JSON rate, transport
failure rate, finish-reason distribution, response length and condition duration.

- If concurrency 1 is substantially healthier than 8 on the same fixed panel, treat engine request
  isolation/batching as the leading cause and do not modify Agent schema to hide it.
- If all levels are similarly poor, concurrency is not sufficient to explain the regression; inspect
  decoding, tokenizer/BOS, stop sequences, prefix continuation and model-serving configuration.
- If all levels are healthy, the restart likely removed the prior defect; confirm with a new unchanged
  Round12 E2E-90 engine control before Round13.

This is an association diagnostic, not proof of a specific engine implementation defect. One sample
per task/condition does not estimate all stochastic variance.

## Non-cheating boundary

- No acceptance file, verifier, Codex reference or expected answer is opened.
- No tool/action, workspace mutation, external score or final answer exists in this diagnostic.
- Malformed JSON is not repaired beyond the existing frozen product path.
- Results are never selected, rewritten or rerun merely because they are wrong.
- This diagnostic cannot satisfy a GitHub architecture promotion gate.

