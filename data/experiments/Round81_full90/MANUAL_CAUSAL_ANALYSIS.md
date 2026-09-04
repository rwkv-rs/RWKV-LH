# Round81 full90 manual causal analysis

## Frozen result

Round81 is a same-source repeat of `Round80_full90_r2` after the forwarded model service restarted.

| Metric | Round81 | Round80 r2 | Uploaded Round46 best |
|---|---:|---:|---:|
| Strict E2E | 0/90 | 0/90 | 31/90 |
| External acceptance | 10/90 | 10/90 | 32/90 |
| Agent completed | 0/90 | 1/90 | 55/90 |
| False positive | 0 | 1 | 24 |
| False negative | 10 | 10 | 1 |
| Model requests | 1533 | 1719 | 1622 |

Difficulty distribution for Round81 external acceptance is basic `7/30`, medium `2/30`, hard `1/30`; no long-horizon case passed externally. All ten externally correct cases were false negatives because the Agent completed none.

This is not an improvement and must not replace or be uploaded over the Round46 checkpoint. FP=0 is not positive evidence here: no run reached Agent completion, so the architecture had almost no opportunity to produce an FP.

## Run integrity

- The generated run protocol records the fixed 90 cases, `max_transitions=200`, concurrency `8`, temperature `0.05`, and zero semantic resampling.
- Before the run, all 56 source-manifest entries from Round80 r2 were rehashed: changed `0`, missing `0`.
- Local regression before the run was `77 passed in 14.99s`.
- All 90 cases contain non-empty `audit.json`, `event_log.json`, `model_trace.json`, and compressed state timeline artifacts.
- All 90 audits record that acceptance paths were absent from model traces and that the isolated verifier used a read-only workspace snapshot without mounting the repository.
- The frozen Codex reference digest remains `947a4b495951374b4d83a1029a2e3196e98c277e2c5d815919bdc58bf482d89b`; it was used only after model execution through the independent acceptance checks.
- No RWKV final output was rewritten. There were no non-empty delivered final outputs because no Agent run completed.

## Comparison with the frozen standard answers

External acceptance is the authoritative observable comparison with each frozen Codex reference. Ten final workspaces matched every referenced acceptance check:

| Case | Frozen standard answer summary | Why Strict still failed |
|---|---|---|
| B01 | Exact greeting plus one newline | Direct correct `lh_task_done` rejected while selector was expected. |
| B03 | Preserve config fields and apply exact feature changes | Model used top-level `arguments` instead of `params`. |
| B09 | Exact row count, total and average statistics | Task completed, then Goal request timed out after 300 seconds. |
| B13 | Preserve unrelated config and update deployment/retries | Model used `arguments` instead of `params`. |
| B18 | Exact subtotal, discount and total | Model used `arguments` instead of `params`. |
| B20 | Correct `is_even` implementation and passing tests | Model selected the unregistered spelling `lh_replace_text`. |
| B26 | Exact three-file output tree | Later model output was empty. |
| M05 | Exact ordered implementation plan | Correct workspace survived, but later invalid JSON reads exhausted Task attempts. |
| M20 | Correct parser behavior and passing tests | Model returned `params:{params:{}}` for `lh_task_done`. |
| H04 | Correct scoped file and no scope violation | Direct correct `lh_task_done` rejected while selector was expected. |

The remaining 80 workspaces failed at least one standard observable and therefore remain incorrect regardless of the Agent status.

Round80 and Round81 have the same total External `10/90`, but only eight exact-pass cases overlap. Round80-only passes were B07 and B15; Round81-only passes were B09 and B20. This `8/12` union overlap shows meaningful run-to-run instability even though the aggregate count is unchanged.

## Terminal-cause census

Every case was traced backward from its last fatal state event. Counts below are mutually exclusive and cover all 90 cases.

### Protocol boundary: 71 cases

| Terminal error family | Cases | Count |
|---|---|---:|
| Noncanonical top-level object instead of exactly `function+params` | `function+arguments` in 19 cases; one event echo in LH06 | 20 |
| Direct registered action/control while `lh_select_operation` was expected | read_file 9, read_json 7, task_done 2, write_json 2, replace_task 1, write_file 1, chunk_map 1 | 23 |
| Selected unregistered `lh_replace_text` rather than advertised `replace_text` | B10, B20, B30, H08, LH10, M12, M24 | 7 |
| Non-empty/nested params for an empty-params completion control | goal_done 3, task_done 1 | 4 |
| Truncated/unterminated or empty JSON | unterminated 7, empty 2 | 9 |
| Invalid `write_json` contract | missing value 2, absolute path 1 | 3 |
| Chunk/rollover/custom-action contract failures | missing chunk source 2, insufficient lossless chunk budget 1, oversized Goal rollover 1, missing mock verifier 1 | 5 |

The 19 `function+arguments` cases were B03, B04, B13, B18, B25, B27, B28, H05, H09, H11, LH02, LH07, M03, M09, M14, M15, M17, M21 and M28. LH06 instead echoed the latest `task_operation_rejected` event object; that output is not a tool-call format and should remain rejected. The first four rows account for `54/90` cases. They are primarily mismatches between the model-visible surface protocol and the one internal representation, not hidden-answer or verifier failures.

### Task attempt budget exhausted: 16 cases

Eleven of these cases repeatedly used JSON parsing on non-JSON or already-corrupted text. Other cases repeatedly selected an end-of-file continuation, read a directory as a file, read nonexistent producer outputs, or failed to recover from the injected transient failure. These contain genuine RWKV action-selection/recovery errors. The runtime correctly left them visible rather than manufacturing an answer.

M05 is the important exception: its final workspace already matched the standard answer, but the Task lane continued into invalid `read_json` actions until the attempt budget ended. It is another completion-state false negative rather than a wrong final artifact.

### Outcome unknown/timeouts: 3 cases

B09, LH03 and LH04 ended with a 300-second read timeout. B09 had already completed its Task and matched external acceptance before the Goal request timed out. The same timeout class appeared in Round80 r2, so concurrency `8` against this endpoint remains an environmental/runtime correctness risk. Frozen results are not adjusted after the fact.

## B01 end-to-end causal chain

1. The Goal lane emitted a valid one-Task plan.
2. The Task lane selected `write_file` through `lh_select_operation`.
3. It emitted exact `write_file` parameters; the Harness wrote the correct bytes.
4. Deterministic validation and the post-action snapshot both succeeded.
5. RWKV then emitted `lh_task_done({task_id:T1})`, correctly expressing that the active Task was complete.
6. `LongHorizonModel.next_task_command` always starts another two-call operation-selection handshake after an event. It therefore required `lh_select_operation` at this point and rejected the direct completion control.
7. The candidate was rolled back without semantic resampling, the run became blocked, and the independent verifier still passed the workspace.

The no-resampling rollback is correct anti-cheating behavior. The defect is that an already complete model command must first be restated as `lh_select_operation(operation=lh_task_done)` and then generated a second time as `lh_task_done`. B09 shows that RWKV sometimes follows this redundant two-call sequence; B01/H04 show that it often emits the semantically complete command directly.

## Architecture findings

### 1. The simple format-conversion boundary is absent

`model_io.parse_model_command` explicitly performs “no history scan, recovery or normalization” and requires the raw JSON keys to be exactly `function` and `params`. Nineteen cases used the common G1i/OpenAI spelling `function + arguments`, preserving the same tool identity and argument object, and were blocked. LH06's event echo is a separate semantic failure and must not be converted into a call.

This contradicts the previously established requirement for one small transport converter. A converter does not need a format whitelist or answer rules. It only needs to map an unambiguous model-emitted call envelope to the internal `function+params` structure while preserving the function name and every parameter byte/value for audit.

### 2. Operation selection and parameter binding are unnecessarily split across two generations

Every Task step first exposes only `lh_select_operation`, then performs another model request exposing the selected schema. After every action result, the cycle repeats even when RWKV already emits a complete registered operation/control with its parameters.

This caused 23 terminal failures and adds another opportunity for the model to change or corrupt its intent. Accepting one complete direct registered call as an atomic operation-selection-and-binding commit would preserve, rather than alter, RWKV's decision. Ambiguous or conflicting calls must still block.

### 3. The unit-test client masks the production failure

`tests/test_unified_controller.py::SequenceClient.text_completion` detects when a selector prompt is visible and automatically wraps the test's intended direct call as `lh_select_operation(operation=<intended name>)`. Production RWKV receives no such wrapper. Therefore the 77 passing tests prove the controller works with a client that supplies the missing selection step; they do not test the raw behavior that failed B01/B02 and 21 other cases.

The next regression must feed the exact raw direct calls observed in Round81 through the production model-I/O path without test-client assistance.

### 4. Visible naming encourages prefix generalization

The same selector enum mixes prefixed controls (`lh_workset`, `lh_chunk_map`, `lh_task_done`) with unprefixed Harness actions (`replace_text`, `write_file`, `read_file`). Seven independent cases selected `lh_replace_text`, a systematic prefix generalization. This is RWKV's emitted identity and must not be silently renamed after selection, but the surface naming scheme can be made internally consistent before generation.

### 5. Completion controls discard evidence structure

`lh_goal_done` and `lh_task_done` accept only an empty object. Three Goal outputs instead supplied exact evidence/output refs and an observation digest; M20 nested the empty params object. Discarding extra evidence in a converter would be wrong. The architecture must decide whether completion is genuinely evidence-bound and expose one schema consistent with that decision.

### 6. Some failures remain genuine model capability failures

The format and lane fixes would not make the other 80 workspaces correct. Repeated JSON parsing of plain text, reads of nonexistent outputs, invalid collection members, truncated generations and wrong write content remain RWKV decisions. They should be addressed only after the common protocol losses are removed, using their real action observations for same-lane correction.

## Recommended validation order for the user-authored change

1. Add a transparent, audited call-envelope converter and replay all 19 `function+arguments` failures plus nested empty-params cases offline; assert unchanged function identity and unchanged params payload, while the LH06 event echo remains rejected.
2. Exercise raw direct registered operations at a selector checkpoint; verify one atomic commit without an extra semantic generation and without changing the action.
3. Remove the `SequenceClient` auto-wrapper from the relevant integration test path and add B01's exact four raw outputs as a regression.
4. Resolve the mixed operation namespace and completion-evidence contract without aliases that secretly choose another action.
5. Run targeted B01, B03, H04, M20 and B20, then the fixed short set, then full90 with the same frozen acceptance and comparison rules.
6. Treat endpoint concurrency/timeout as a separate ablation; do not change concurrency in the middle of a score comparison.

No implementation was modified during this analysis.
