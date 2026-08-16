# Round83 direct Task-call canary manual causal analysis

## Result

Strict `0/4`, External `0/4`, Agent completed `0/4`. No case failed with
`lane requires lh_select_operation`; the selector state and its intermediate
event were absent.

## Per-case first causal failure

| Case | First direct Task call | First causal failure |
|---|---|---|
| B01 | `lh_chunk_map(sources=["."])` | The model selected read-only chunk analysis for a file-creation Task and supplied a directory where an existing regular UTF-8 file was required. |
| B02 | `lh_chunk_map(input.txt, task_id=T1)` | The read-only operation was plausible, but the model added undeclared `task_id`; exact schema validation rejected it before execution. |
| B03 | `lh_chunk_map(config.json, task_id=T1)` | Same extra-parameter failure as B02; no workspace mutation occurred. |
| H04 | `lh_chunk_map(inbox/untrusted.txt)` | The model selected analysis instead of creation. A child result claimed the desired output content but did not create the file; the later `lh_task_done(target_task=T1)` also violated the empty-params contract. |

The direct-call code removed the old boundary, but the first full tool-list
surface over-attracted `lh_chunk_map` and did not tell the model explicitly that
Task identity is runtime-bound. These are input-contract findings, not grounds to
accept or rewrite any emitted parameter.

