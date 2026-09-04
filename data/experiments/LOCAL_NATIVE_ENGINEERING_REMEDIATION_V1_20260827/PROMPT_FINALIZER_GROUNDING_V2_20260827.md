# Strong Planner prompt and finalizer grounding remediation

Date: 2026-08-27

## Motivation

The fixed E2E-B02 canary previously produced the correct workspace artifact but
an incorrect user-visible answer. The accepted `report.json` contained
`{"doubled_count":14,"project":"Orion"}`, while the frozen finalizer used zero
actions and invented `{"project":"example_project","doubled_count":4}`.

The failure had two coupled causes:

1. The strong Planner prompt assigned initial-finalizer structure to the model
   while the Controller also treated it as a structural lifecycle node.
2. Capability projection and atom execution permitted a v2 finalizer to finish
   with zero observations even though the prompt said it read the current
   workspace.

## Remediation

- Reordered and shortened the contract-plan system prompt into explicit
  authority, patch state, obligations, assertions, work-node, network/evidence,
  and final-check sections.
- Removed the contradictory instruction forbidding all request-text reuse;
  predicates and objectives may now preserve only the exact literals they
  govern, while request/request_clauses remain Controller-owned.
- Initial and correction structured-output schemas allow only `role=work`.
- The adapter deterministically appends the single frozen initial finalizer
  after the Planner supplies valid work; this emits
  `supervisor_contract_plan_normalized`.
- Projected finalizers now require `minimum_actions=1` and receive their declared
  action budget instead of a forced zero-action ceiling.
- Added regressions for schema ownership, synthesized-finalizer projection, and
  rejection of a premature final answer before a current-workspace observation.

## Fixed comparison protocol

- Suite/case: RWKV-E2E-30 / E2E-B02
- RWKV model: `rwkv7-g1i-13.3b-rwkv-lh-stage7-step1500-bos-ctx2496`
- Architecture: `strong-planner-reviewer-rwkv-contract-graph.v2`
- Tool disclosure: progressive
- Max transitions: 60
- Concurrency: 1
- Sampling: temperature 0.05, top_p 1.0, top_k 0
- Old run: `strong_planner_canary_post_auth/run_e2e_b02_retry1`
- New run: `strong_planner_canary_post_auth/run_e2e_b02_prompt_grounding_v2`

The primary Planner request encountered an upstream HTTP 500 after its configured
retries; the registered fallback `gpt-5.6-sol` produced the accepted plan. Review
used `gpt-5.6-terra`. This transport/model difference is retained in the trace and
means token-usage changes are descriptive, not a model-quality ablation.

## Results

| Metric | Before | After |
| --- | ---: | ---: |
| Strict E2E | PASS | PASS |
| External acceptance | PASS | PASS |
| Finalizer actions | 0 | 1 (`read_json`) |
| Final output grounded in accepted artifact | No | Yes |
| Final output values | `example_project`, `4` | `Orion`, `14` |
| Planner prompt tokens reported by provider | 7021 | 6196 |
| Total RWKV actions | 3 | 8 |

The grounding defect is resolved: the finalizer read the current `report.json`
and its exact candidate was returned without Controller rewriting. Full project
regression completed with `379 passed in 80.83s`; targeted Planner/projection/
atom regression completed with `43 passed`, plus four focused checks passed.

## Remaining trace defects

The canary is correct but not action-efficient:

- The investigate atom made a second, premature `read_json(report.json)` call
  after already observing `input.txt`; the missing-file result was unnecessary.
- The mutation atom issued the same successful `write_json` three times. The
  first write changed the workspace; the next two were no-op repeats.
- Total RWKV actions therefore increased from 3 to 8. This is a worker
  stop-after-success/action-selection defect, not a finalizer grounding defect,
  and should become a focused state-tuning contrast cluster plus a runtime
  no-progress guard evaluation.

These defects remain open and are not hidden by the passing external verifier.

## Data provenance and digests

- Old audit source: fixed historical E2E-B02 canary, SHA-256
  `c91114a1047a3d227bda43da622a91b2e3de4b22dfe0ae5a6adfd3538114ec18`.
- New audit source: fixed post-remediation E2E-B02 canary, SHA-256
  `225866022637f78f495bccad81892bb9001edac551f81a22ccc1bd168352e0f8`.
- New results summary SHA-256:
  `68e01971d43351e951ce133d1149ed012a1dcd608c136e0f3b2b7cdee7ddfc9f`.
- New accepted `report.json` SHA-256:
  `3baac0ac00268de139e4decd3c9972f67822f948965ea6b153500559231bc713`.
- Generation method: the benchmark runner created an isolated workspace from
  the registered E2E-B02 fixture, executed the pinned architecture and settings,
  recorded model/supervisor traces, then ran the suite's hidden external
  acceptance after execution.
