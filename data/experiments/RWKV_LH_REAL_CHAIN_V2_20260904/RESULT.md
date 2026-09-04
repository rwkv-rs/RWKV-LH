# Real-chain result

Date: 2026-09-04

Run ID: `REAL-CHAIN-ZERO-STATE-V2-20260904`

Result: `blocked`; the requested `summary.json` was not created and no final answer was emitted.

## Deployment identity

- Planner: configured strong Planner through the production entry point.
- Selector model: `rwkv7-g1j-2.9b-vllm-v1`.
- Selector input: `rwkv-lh.g1j-per-stage-state-tuning.selector-intent.v2`.
- Selector State: `zero`, SHA-256 all zeros.
- Selector Head file SHA-256: `dd3a8ca6fb99eb51e60564a7f1c3125300330cbcf15bd45728fd2b87759ed57a`.
- Executor: `rwkv7-g1j-13.3b-zero-state-capability-ctx16384` with native recurrent State.

## Observed chain

1. Planner created an observation step for `orders.json`.
2. Selector voted `search_text/search_text/search_text`; Executor produced valid `search_text` parameters after one protocol retry and Harness returned two matching lines.
3. Step Auditor accepted the local observation, but Strong Stage Checker correctly detected that matching lines were insufficient for the full task.
4. Planner revised the frontier to explicitly require a complete JSON read and added the constraint `不得使用仅匹配 paid 的局部搜索结果代替完整读取`.
5. On that revised current subtask, Selector again voted `search_text/search_text/search_text` twice. Executor repeated the same valid action after one further protocol retry.
6. The Controller stopped after the third identical successful but non-progressing action with `identical_success_budget_exhausted`.

## State and protocol evidence

- First three menu-order inputs: `944 / 945 / 945` tokens.
- Revised-step inputs: `1007 / 1008 / 1008` tokens.
- The second and third selection used identical current-subtask digests and identical token counts; no token position accumulated across calls.
- Every lane recorded `fresh_initial_state_per_evaluation` and `current_subtask_only`.
- The changed Planner step produced a new input digest, proving the Planner-to-Selector current-subtask update propagated.
- All three operation handoffs were consumed by Executor without Executor changing the selected operation.
- Executor had two malformed single-JSON generations: `Expecting value: line 3 column 28 (char 54)`. Both retries remained bound to `search_text` and then executed successfully.

## Attribution

Primary failure: Selector Head domain shift. The no-training 23-class Head preserves weights trained on the prior v1/persistent input distribution and maps both the original and explicitly corrected full-JSON-read subtask to `search_text`.

Not supported as a cause by this run: Selector WKV accumulation, stale Planner-to-Selector state, menu-order instability, Executor operation reselection, Harness failure, or missing Planner repair.

Secondary defect: Executor canonical-JSON adherence remains imperfect, with two protocol rejections in three actions.

Fixture source SHA-256: `a420fa5e7e75ea0c844bac8099c53eff386706c2e05680cc432f30090f00d501`.

Repository regression after deployment metadata changes: `525 passed, 3 skipped in 41.30s`; the skips require optional local Torch.
