# Round12 中断样本：从终态向前的因果分析

## 分析边界

这是一份非计分、非正式实验分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。两个中断目录彼此独立，未合并、未补跑、未用于形成 Round12 分数。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round12_interrupted_network_20260812T103554Z | 63 | 87 | 2e9e8c320e308fa9d92405d5e7321dfa960b80959c96d2b4860c86cf3a158cf0 |
| Round12_interrupted_network_20260812T110102Z | 55 | 71 | e5b04a64b918aeb346fcfce3c28f86469517bdccfc01be89761d686611893fb5 |
| Round12_interrupted_network_20260812T113505Z | 39 | 55 | 546ef44afa50b3215f6f37153d398d05eba42a6a664ad5e236467a5bbb0a0e94 |
| Round12_interrupted_network_20260812T120354Z | 40 | 61 | 3fa8972c3296dfa2411eb2492fe4cc3f86bdac339120cff231acddbfce7c5a19 |
| Round12_interrupted_network_20260812T123422Z | 43 | 59 | 608017bc833990f026cb2ddb1bd9d9135cc59779c66064857b08d7715f11a20e |

## 总体终态与根因

### Round12_interrupted_network_20260812T103554Z

状态：`{"blocked": 31, "interrupted": 29, "missing_result": 24, "not_created": 3}`。

| 终态根因 | 题数 |
|---|---|
| transport_outcome_unknown | 29 |
| no_result_or_incomplete | 22 |
| witness_intent_contract | 16 |
| obligation_replan_contract | 8 |
| action_recovery_budget_exhausted | 5 |
| goal_parse_contract | 2 |
| manual_interruption | 2 |
| planning_contract | 1 |
| action_argument_contract | 1 |
| unhandled_priority_type | 1 |
### Round12_interrupted_network_20260812T110102Z

状态：`{"blocked": 47, "interrupted": 5, "missing_result": 16, "not_created": 3}`。

| 终态根因 | 题数 |
|---|---|
| witness_intent_contract | 27 |
| no_result_or_incomplete | 12 |
| obligation_replan_contract | 7 |
| action_recovery_budget_exhausted | 6 |
| transport_outcome_unknown | 4 |
| manual_interruption | 4 |
| planning_contract | 3 |
| action_argument_contract | 3 |
| goal_parse_contract | 3 |
| unhandled_priority_type | 1 |
| run_blocked_other | 1 |
### Round12_interrupted_network_20260812T113505Z

状态：`{"blocked": 29, "interrupted": 7, "missing_result": 16, "not_created": 3}`。

| 终态根因 | 题数 |
|---|---|
| witness_intent_contract | 16 |
| no_result_or_incomplete | 13 |
| transport_outcome_unknown | 6 |
| obligation_replan_contract | 4 |
| run_blocked_other | 3 |
| action_recovery_budget_exhausted | 3 |
| action_argument_contract | 3 |
| goal_parse_contract | 3 |
| manual_interruption | 3 |
| recovery_analysis_contract | 1 |
### Round12_interrupted_network_20260812T120354Z

状态：`{"blocked": 26, "interrupted": 12, "missing_result": 21, "not_created": 2}`。

| 终态根因 | 题数 |
|---|---|
| no_result_or_incomplete | 15 |
| transport_outcome_unknown | 15 |
| witness_intent_contract | 10 |
| action_recovery_budget_exhausted | 5 |
| action_argument_contract | 5 |
| planning_contract | 3 |
| obligation_replan_contract | 2 |
| manual_interruption | 2 |
| goal_parse_contract | 2 |
| run_blocked_other | 1 |
| recovery_analysis_contract | 1 |
### Round12_interrupted_network_20260812T123422Z

状态：`{"blocked": 32, "interrupted": 8, "missing_result": 16, "not_created": 3}`。

| 终态根因 | 题数 |
|---|---|
| witness_intent_contract | 19 |
| no_result_or_incomplete | 15 |
| transport_outcome_unknown | 6 |
| planning_contract | 5 |
| obligation_replan_contract | 3 |
| action_recovery_budget_exhausted | 3 |
| goal_parse_contract | 3 |
| unhandled_priority_type | 1 |
| run_blocked_other | 1 |
| action_argument_contract | 1 |
| recovery_analysis_contract | 1 |
| manual_interruption | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round12_interrupted_network_20260812T103554Z | Round12_interrupted_network_20260812T110102Z | Round12_interrupted_network_20260812T113505Z | Round12_interrupted_network_20260812T120354Z | Round12_interrupted_network_20260812T123422Z |
|---|---|---|---|---|---|
| run_created | 62 | 56 | 39 | 44 | 41 |
| goal_parsed | 62 | 56 | 39 | 44 | 41 |
| plan_saved | 37 | 51 | 32 | 31 | 33 |
| attempt_started | 30 | 45 | 31 | 24 | 28 |
| action_returned | 30 | 45 | 31 | 24 | 28 |
| task_completed | 30 | 42 | 31 | 20 | 28 |
| goal_obligation_capsule_prepared | 9 | 11 | 9 | 5 | 6 |
| goal_obligation_replan_started | 9 | 11 | 9 | 5 | 6 |
| witness_intent_precommit_started | 16 | 28 | 17 | 10 | 19 |
| witness_intents_precommitted | 1 | 2 | 3 | 1 | 0 |
| witness_catalog_prepared | 1 | 2 | 3 | 1 | 0 |
| criterion_assertions_evaluated | 0 | 1 | 3 | 1 | 0 |
| witness_binding_evaluated | 0 | 1 | 3 | 1 | 0 |
| criterion_evidence_committed | 0 | 0 | 0 | 0 | 0 |
| run_completed | 0 | 0 | 0 | 0 | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round12_interrupted_network_20260812T103554Z | Round12_interrupted_network_20260812T110102Z | Round12_interrupted_network_20260812T113505Z | Round12_interrupted_network_20260812T120354Z | Round12_interrupted_network_20260812T123422Z |
|---|---|---|---|---|---|
| action_argument_contract | 2 | 6 | 5 | 6 | 1 |
| action_choice_contract | 1 | 2 | 3 | 1 | 0 |
| action_or_validation_failed | 6 | 9 | 7 | 10 | 8 |
| action_recovery_budget_exhausted | 5 | 6 | 3 | 5 | 3 |
| intent_actual_expected_same_kind_without_goal_literal | 0 | 1 | 1 | 0 | 0 |
| obligation_gap_triggered_replan | 9 | 11 | 9 | 5 | 6 |
| obligation_replan_blocked | 0 | 1 | 3 | 1 | 1 |
| obligation_replan_contract | 9 | 10 | 9 | 5 | 6 |
| planning_contract | 4 | 7 | 3 | 4 | 7 |
| proof_feedback_triggered_local_revision | 0 | 1 | 2 | 0 | 0 |
| proof_rejected_other | 0 | 1 | 3 | 1 | 0 |
| proof_rejected_same_source_self_comparison | 0 | 1 | 1 | 0 | 0 |
| recovery_analysis_contract | 0 | 0 | 1 | 1 | 1 |
| rwkv_selected_same_source_for_both_sides | 0 | 1 | 1 | 0 | 0 |
| rwkv_selected_same_value_handle_for_both_sides | 0 | 1 | 1 | 0 | 0 |
| transport_outcome_unknown | 28 | 4 | 6 | 15 | 6 |
| unhandled_priority_type | 1 | 1 | 0 | 0 | 1 |
| witness_catalog_reached | 1 | 2 | 3 | 1 | 0 |
| witness_handle_binding_contract | 0 | 1 | 2 | 1 | 0 |
| witness_intent_contract | 16 | 28 | 17 | 10 | 19 |
| witness_intent_required | 16 | 28 | 17 | 10 | 19 |
| witness_intent_revision_contract | 0 | 1 | 2 | 1 | 0 |
| witness_source_selection_contract | 1 | 0 | 2 | 1 | 0 |

## 请求与错误放大

### Round12_interrupted_network_20260812T103554Z

聚合报告计数：`{"attempt_count": 145, "model_requests": 531, "replan_count": 0, "task_count": 250}`。

模型请求类型：`{"failure_analysis": 11, "goal_obligation_replan": 22, "task_decomposition": 66, "tool_action": 163, "tool_choice": 168, "witness_intent_precommit": 34, "witness_validation": 2}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 20 | invalid expected witness source kind |
| goal_obligation_replan | 18 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| witness_intent_precommit | 5 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| task_decomposition | 5 | invalid plan schema |
| witness_intent_precommit | 4 | witness intent comparison must be exact_equals |
| witness_intent_precommit | 2 | witness-intent top-level fields must be exactly ['schema_version', 'witness_intents'] |
| witness_validation | 2 | pass must select sources for every intent exactly once |
| tool_choice | 1 | unsupported action type: read_directory |
| goal_obligation_replan | 1 | obligation replan local ids reuse existing task ids: ['T1', 'T2', 'T3', 'T4', 'T5', 'T6', 'T7', 'T8'] |
| tool_action | 1 | ValueError: G1i tool call has unknown fields: ['action'] |
| witness_intent_precommit | 1 | non-goal expected witness must use empty expected_goal_literal |
| witness_intent_precommit | 1 | current action/workspace witness producer must be the active task |
### Round12_interrupted_network_20260812T110102Z

聚合报告计数：`{"attempt_count": 217, "model_requests": 733, "replan_count": 0, "task_count": 325}`。

模型请求类型：`{"failure_analysis": 16, "goal_obligation_replan": 31, "task_decomposition": 63, "tool_action": 259, "tool_choice": 257, "verification_design": 1, "witness_handle_binding": 3, "witness_intent_precommit": 57, "witness_intent_revision": 2, "witness_validation": 3}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 39 | invalid expected witness source kind |
| goal_obligation_replan | 19 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| task_decomposition | 10 | invalid plan schema |
| witness_intent_precommit | 8 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 4 | goal-literal witness quote must be an exact non-empty Goal substring |
| tool_action | 3 | action type changed after selection: expected read_json |
| witness_intent_precommit | 3 | non-goal expected witness must use empty expected_goal_literal |
| tool_action | 3 | action read_file argument path must be workspace-relative |
| tool_choice | 2 | unsupported action type: read_text |
| witness_intent_revision | 2 | witness-intent top-level fields must be exactly ['schema_version', 'witness_intents'] |
| goal_obligation_replan | 1 | plan requires a non-empty tasks array |
| goal_obligation_replan | 1 | obligation replan local ids reuse existing task ids: ['T1', 'T3', 'T5'] |
### Round12_interrupted_network_20260812T113505Z

聚合报告计数：`{"attempt_count": 142, "model_requests": 511, "replan_count": 0, "task_count": 242}`。

模型请求类型：`{"failure_analysis": 11, "goal_obligation_replan": 36, "task_decomposition": 42, "tool_action": 168, "tool_choice": 171, "witness_handle_binding": 4, "witness_intent_precommit": 39, "witness_intent_revision": 4, "witness_validation": 8}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 22 | invalid expected witness source kind |
| goal_obligation_replan | 22 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| witness_intent_precommit | 4 | witness intent comparison must be exact_equals |
| witness_intent_revision | 4 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 4 | goal-literal witness quote must be an exact non-empty Goal substring |
| task_decomposition | 3 | invalid plan schema |
| tool_choice | 2 | unsupported action type: read_text |
| tool_action | 2 | action type changed after selection: expected read_json |
| failure_analysis | 2 | failure analysis decision must be retry_same, reselect_action, or replan |
| tool_action | 2 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_intent_precommit | 2 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 2 | current action/workspace witness producer must be the active task |
### Round12_interrupted_network_20260812T120354Z

聚合报告计数：`{"attempt_count": 103, "model_requests": 401, "replan_count": 0, "task_count": 222}`。

模型请求类型：`{"failure_analysis": 15, "goal_obligation_replan": 18, "task_decomposition": 48, "tool_action": 123, "tool_choice": 126, "witness_handle_binding": 2, "witness_intent_precommit": 26, "witness_intent_revision": 2, "witness_validation": 4}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 16 | invalid expected witness source kind |
| goal_obligation_replan | 11 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| task_decomposition | 5 | invalid plan schema |
| witness_intent_precommit | 4 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 3 | current action/workspace witness producer must be the active task |
| task_decomposition | 2 | plan requires a non-empty tasks array |
| witness_handle_binding | 2 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| witness_intent_revision | 2 | invalid expected witness source kind |
| witness_validation | 2 | pass must select sources for every intent exactly once |
| tool_action | 2 | action read_file argument path must be workspace-relative |
| failure_analysis | 1 | ModelProtocolError: model output does not contain a complete JSON object |
| tool_action | 1 | ValueError: G1i tool call has unknown fields: ['action'] |
### Round12_interrupted_network_20260812T123422Z

聚合报告计数：`{"attempt_count": 128, "model_requests": 467, "replan_count": 0, "task_count": 215}`。

模型请求类型：`{"failure_analysis": 12, "goal_obligation_replan": 20, "task_decomposition": 48, "tool_action": 148, "tool_choice": 151, "verification_design": 4, "witness_intent_precommit": 38}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 25 | invalid expected witness source kind |
| goal_obligation_replan | 13 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| task_decomposition | 10 | invalid plan schema |
| witness_intent_precommit | 4 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 4 | witness intent comparison must be exact_equals |
| witness_intent_precommit | 3 | goal-literal witness quote must be an exact non-empty Goal substring |
| failure_analysis | 2 | failure analysis decision must be retry_same, reselect_action, or replan |
| witness_intent_precommit | 1 | current action/workspace witness producer must be the active task |
| witness_intent_precommit | 1 | witness-intent top-level fields must be exactly ['schema_version', 'witness_intents'] |
| tool_action | 1 | ValueError: G1i tool call has unknown fields: ['tool'] |
| task_decomposition | 1 | tasks bind unknown goal criteria: ['GC10', 'GC11', 'GC12', 'GC13', 'GC14', 'GC15', 'GC16', 'GC17', 'GC18', 'GC19', 'GC5', 'GC6', 'GC7', 'GC8', 'GC9'] |
| task_decomposition | 1 | tasks bind unknown goal criteria: ['GC10', 'GC11', 'GC12', 'GC13', 'GC14', 'GC15', 'GC16', 'GC17', 'GC5', 'GC6', 'GC7', 'GC8', 'GC9'] |

## 从后向前的关键链

### Round12_interrupted_network_20260812T103554Z

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| transport_outcome_unknown | 29 | 12 | 0 | 0 | E2E-B11, E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16 |
| no_result_or_incomplete | 22 | 0 | 0 | 0 | E2E-H11, E2E-H12, E2E-H13, E2E-H14, E2E-H15, E2E-M12 |
| witness_intent_contract | 16 | 40 | 22 | 0 | E2E-B01, E2E-B04, E2E-B05, E2E-B10, E2E-H04, E2E-H08 |
| obligation_replan_contract | 8 | 43 | 16 | 1 | E2E-B02, E2E-B03, E2E-B06, E2E-B07, E2E-B08, E2E-H03 |
| action_recovery_budget_exhausted | 5 | 18 | 31 | 0 | E2E-H01, E2E-H07, E2E-H10, E2E-M07, E2E-M10 |
| goal_parse_contract | 2 | 0 | 0 | 0 | E2E-B09, E2E-M06 |
| manual_interruption | 2 | 0 | 0 | 0 | E2E-B26, E2E-M14 |
| action_argument_contract | 1 | 0 | 0 | 0 | E2E-H05 |
| planning_contract | 1 | 0 | 1 | 0 | E2E-H02 |
| unhandled_priority_type | 1 | 7 | 10 | 1 | E2E-LH01 |
### Round12_interrupted_network_20260812T110102Z

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| witness_intent_contract | 27 | 79 | 27 | 0 | E2E-B01, E2E-B02, E2E-B04, E2E-B06, E2E-B07, E2E-B10 |
| no_result_or_incomplete | 12 | 0 | 0 | 0 | E2E-B28, E2E-B29, E2E-B30, E2E-M11, E2E-M12, E2E-M13 |
| obligation_replan_contract | 7 | 53 | 39 | 3 | E2E-B03, E2E-B05, E2E-B08, E2E-B13, E2E-B14, E2E-H06 |
| action_recovery_budget_exhausted | 6 | 6 | 41 | 0 | E2E-B09, E2E-B12, E2E-B21, E2E-B23, E2E-LH10, E2E-M10 |
| manual_interruption | 4 | 5 | 0 | 0 | E2E-B20, E2E-B22, E2E-B27, E2E-LH11 |
| transport_outcome_unknown | 4 | 5 | 0 | 0 | E2E-B15, E2E-B24, E2E-B25, E2E-B26 |
| action_argument_contract | 3 | 12 | 1 | 0 | E2E-H10, E2E-LH01, E2E-LH08 |
| goal_parse_contract | 3 | 0 | 0 | 0 | E2E-LH03, E2E-LH12, E2E-M06 |
| planning_contract | 3 | 0 | 3 | 0 | E2E-H02, E2E-H05, E2E-LH05 |
| run_blocked_other | 1 | 6 | 0 | 0 | E2E-M05 |
| unhandled_priority_type | 1 | 20 | 0 | 0 | E2E-LH02 |
### Round12_interrupted_network_20260812T113505Z

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| witness_intent_contract | 16 | 29 | 26 | 0 | E2E-B01, E2E-B02, E2E-B03, E2E-B04, E2E-B10, E2E-H04 |
| no_result_or_incomplete | 13 | 0 | 0 | 0 | E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B17 |
| transport_outcome_unknown | 6 | 23 | 0 | 0 | E2E-B11, E2E-H03, E2E-LH08, E2E-LH09, E2E-LH10, E2E-LH11 |
| obligation_replan_contract | 4 | 21 | 14 | 1 | E2E-B06, E2E-H05, E2E-H08, E2E-M05 |
| action_argument_contract | 3 | 9 | 0 | 0 | E2E-H02, E2E-H10, E2E-LH01 |
| action_recovery_budget_exhausted | 3 | 5 | 21 | 0 | E2E-B09, E2E-H07, E2E-M10 |
| goal_parse_contract | 3 | 0 | 0 | 0 | E2E-LH03, E2E-M03, E2E-M06 |
| manual_interruption | 3 | 1 | 8 | 1 | E2E-LH04, E2E-LH05, E2E-LH07 |
| run_blocked_other | 3 | 33 | 0 | 0 | E2E-B05, E2E-B07, E2E-B08 |
| recovery_analysis_contract | 1 | 4 | 1 | 0 | E2E-H01 |
### Round12_interrupted_network_20260812T120354Z

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| no_result_or_incomplete | 15 | 0 | 0 | 0 | E2E-B11, E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16 |
| transport_outcome_unknown | 15 | 11 | 0 | 0 | E2E-B27, E2E-B28, E2E-B30, E2E-H03, E2E-H10, E2E-LH01 |
| witness_intent_contract | 10 | 27 | 34 | 2 | E2E-B01, E2E-B04, E2E-B06, E2E-B07, E2E-B10, E2E-H04 |
| action_argument_contract | 5 | 12 | 5 | 0 | E2E-H05, E2E-H07, E2E-M02, E2E-M08, E2E-M09 |
| action_recovery_budget_exhausted | 5 | 1 | 26 | 0 | E2E-B02, E2E-H06, E2E-H08, E2E-H09, E2E-M10 |
| planning_contract | 3 | 0 | 3 | 0 | E2E-B09, E2E-H02, E2E-LH05 |
| goal_parse_contract | 2 | 0 | 0 | 0 | E2E-M03, E2E-M06 |
| manual_interruption | 2 | 0 | 0 | 0 | E2E-LH07, E2E-LH08 |
| obligation_replan_contract | 2 | 9 | 10 | 1 | E2E-B03, E2E-B08 |
| recovery_analysis_contract | 1 | 4 | 0 | 0 | E2E-H01 |
| run_blocked_other | 1 | 13 | 0 | 0 | E2E-B05 |
### Round12_interrupted_network_20260812T123422Z

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| witness_intent_contract | 19 | 40 | 19 | 0 | E2E-B01, E2E-B03, E2E-B06, E2E-B09, E2E-B10, E2E-H04 |
| no_result_or_incomplete | 15 | 0 | 0 | 0 | E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B17, E2E-B18 |
| transport_outcome_unknown | 6 | 31 | 0 | 0 | E2E-B11, E2E-B12, E2E-H03, E2E-LH08, E2E-LH09, E2E-LH10 |
| planning_contract | 5 | 0 | 5 | 0 | E2E-H02, E2E-H05, E2E-LH02, E2E-LH05, E2E-LH07 |
| action_recovery_budget_exhausted | 3 | 11 | 18 | 0 | E2E-H01, E2E-H07, E2E-H10 |
| goal_parse_contract | 3 | 0 | 0 | 0 | E2E-LH12, E2E-M03, E2E-M06 |
| obligation_replan_contract | 3 | 11 | 11 | 1 | E2E-B04, E2E-B07, E2E-B08 |
| action_argument_contract | 1 | 5 | 0 | 0 | E2E-LH01 |
| manual_interruption | 1 | 0 | 0 | 0 | E2E-LH11 |
| recovery_analysis_contract | 1 | 2 | 1 | 0 | E2E-LH03 |
| run_blocked_other | 1 | 8 | 0 | 0 | E2E-B05 |
| unhandled_priority_type | 1 | 3 | 0 | 0 | E2E-B02 |

## 两次中断样本的结构对照

### Round12_interrupted_network_20260812T103554Z → Round12_interrupted_network_20260812T110102Z

共有 `71` 个共同题目，其中 `27` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | witness_intent_contract | 12 |
| transport_outcome_unknown | witness_intent_contract | 7 |
| no_result_or_incomplete | no_result_or_incomplete | 6 |
| obligation_replan_contract | witness_intent_contract | 5 |
| transport_outcome_unknown | no_result_or_incomplete | 5 |
| transport_outcome_unknown | action_recovery_budget_exhausted | 4 |
| transport_outcome_unknown | manual_interruption | 4 |
| obligation_replan_contract | obligation_replan_contract | 3 |
| transport_outcome_unknown | transport_outcome_unknown | 3 |
| action_recovery_budget_exhausted | witness_intent_contract | 3 |
| witness_intent_contract | obligation_replan_contract | 2 |
| transport_outcome_unknown | obligation_replan_contract | 2 |
| goal_parse_contract | action_recovery_budget_exhausted | 1 |
| manual_interruption | transport_outcome_unknown | 1 |
| planning_contract | planning_contract | 1 |
| action_argument_contract | planning_contract | 1 |
| action_recovery_budget_exhausted | action_argument_contract | 1 |
| unhandled_priority_type | action_argument_contract | 1 |
| transport_outcome_unknown | unhandled_priority_type | 1 |
| witness_intent_contract | goal_parse_contract | 1 |

### Round12_interrupted_network_20260812T103554Z → Round12_interrupted_network_20260812T113505Z

共有 `55` 个共同题目，其中 `19` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| transport_outcome_unknown | no_result_or_incomplete | 13 |
| witness_intent_contract | witness_intent_contract | 10 |
| transport_outcome_unknown | transport_outcome_unknown | 5 |
| obligation_replan_contract | witness_intent_contract | 4 |
| obligation_replan_contract | run_blocked_other | 2 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 2 |
| witness_intent_contract | obligation_replan_contract | 2 |
| witness_intent_contract | goal_parse_contract | 2 |
| transport_outcome_unknown | manual_interruption | 2 |
| witness_intent_contract | run_blocked_other | 1 |
| obligation_replan_contract | obligation_replan_contract | 1 |
| goal_parse_contract | action_recovery_budget_exhausted | 1 |
| action_recovery_budget_exhausted | recovery_analysis_contract | 1 |
| planning_contract | action_argument_contract | 1 |
| obligation_replan_contract | transport_outcome_unknown | 1 |
| action_argument_contract | obligation_replan_contract | 1 |
| action_recovery_budget_exhausted | action_argument_contract | 1 |
| unhandled_priority_type | action_argument_contract | 1 |
| transport_outcome_unknown | witness_intent_contract | 1 |
| witness_intent_contract | manual_interruption | 1 |

### Round12_interrupted_network_20260812T103554Z → Round12_interrupted_network_20260812T120354Z

共有 `61` 个共同题目，其中 `23` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| transport_outcome_unknown | no_result_or_incomplete | 14 |
| transport_outcome_unknown | transport_outcome_unknown | 9 |
| witness_intent_contract | witness_intent_contract | 7 |
| witness_intent_contract | action_argument_contract | 3 |
| obligation_replan_contract | action_recovery_budget_exhausted | 2 |
| obligation_replan_contract | obligation_replan_contract | 2 |
| obligation_replan_contract | witness_intent_contract | 2 |
| obligation_replan_contract | transport_outcome_unknown | 2 |
| witness_intent_contract | action_recovery_budget_exhausted | 2 |
| witness_intent_contract | transport_outcome_unknown | 2 |
| transport_outcome_unknown | manual_interruption | 2 |
| witness_intent_contract | run_blocked_other | 1 |
| goal_parse_contract | planning_contract | 1 |
| action_recovery_budget_exhausted | recovery_analysis_contract | 1 |
| planning_contract | planning_contract | 1 |
| action_argument_contract | action_argument_contract | 1 |
| action_recovery_budget_exhausted | action_argument_contract | 1 |
| action_recovery_budget_exhausted | transport_outcome_unknown | 1 |
| unhandled_priority_type | transport_outcome_unknown | 1 |
| transport_outcome_unknown | planning_contract | 1 |

### Round12_interrupted_network_20260812T103554Z → Round12_interrupted_network_20260812T123422Z

共有 `59` 个共同题目，其中 `24` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| transport_outcome_unknown | no_result_or_incomplete | 14 |
| witness_intent_contract | witness_intent_contract | 12 |
| transport_outcome_unknown | transport_outcome_unknown | 5 |
| obligation_replan_contract | witness_intent_contract | 4 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 3 |
| transport_outcome_unknown | planning_contract | 3 |
| obligation_replan_contract | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | witness_intent_contract | 2 |
| obligation_replan_contract | unhandled_priority_type | 1 |
| witness_intent_contract | obligation_replan_contract | 1 |
| witness_intent_contract | run_blocked_other | 1 |
| goal_parse_contract | witness_intent_contract | 1 |
| manual_interruption | no_result_or_incomplete | 1 |
| planning_contract | planning_contract | 1 |
| obligation_replan_contract | transport_outcome_unknown | 1 |
| action_argument_contract | planning_contract | 1 |
| unhandled_priority_type | action_argument_contract | 1 |
| witness_intent_contract | recovery_analysis_contract | 1 |
| transport_outcome_unknown | manual_interruption | 1 |
| transport_outcome_unknown | goal_parse_contract | 1 |

### Round12_interrupted_network_20260812T110102Z → Round12_interrupted_network_20260812T113505Z

共有 `55` 个共同题目，其中 `18` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | witness_intent_contract | 12 |
| witness_intent_contract | no_result_or_incomplete | 4 |
| obligation_replan_contract | witness_intent_contract | 3 |
| witness_intent_contract | transport_outcome_unknown | 3 |
| action_recovery_budget_exhausted | no_result_or_incomplete | 3 |
| obligation_replan_contract | run_blocked_other | 2 |
| witness_intent_contract | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 2 |
| obligation_replan_contract | no_result_or_incomplete | 2 |
| manual_interruption | no_result_or_incomplete | 2 |
| action_argument_contract | action_argument_contract | 2 |
| goal_parse_contract | goal_parse_contract | 2 |
| witness_intent_contract | manual_interruption | 2 |
| witness_intent_contract | run_blocked_other | 1 |
| transport_outcome_unknown | no_result_or_incomplete | 1 |
| witness_intent_contract | recovery_analysis_contract | 1 |
| planning_contract | action_argument_contract | 1 |
| planning_contract | obligation_replan_contract | 1 |
| witness_intent_contract | action_recovery_budget_exhausted | 1 |
| unhandled_priority_type | witness_intent_contract | 1 |

### Round12_interrupted_network_20260812T110102Z → Round12_interrupted_network_20260812T120354Z

共有 `61` 个共同题目，其中 `16` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | witness_intent_contract | 9 |
| witness_intent_contract | no_result_or_incomplete | 5 |
| witness_intent_contract | transport_outcome_unknown | 4 |
| witness_intent_contract | action_recovery_budget_exhausted | 3 |
| action_recovery_budget_exhausted | no_result_or_incomplete | 3 |
| no_result_or_incomplete | transport_outcome_unknown | 3 |
| witness_intent_contract | action_argument_contract | 3 |
| obligation_replan_contract | obligation_replan_contract | 2 |
| obligation_replan_contract | no_result_or_incomplete | 2 |
| transport_outcome_unknown | no_result_or_incomplete | 2 |
| manual_interruption | no_result_or_incomplete | 2 |
| manual_interruption | transport_outcome_unknown | 2 |
| planning_contract | planning_contract | 2 |
| action_argument_contract | transport_outcome_unknown | 2 |
| goal_parse_contract | transport_outcome_unknown | 2 |
| obligation_replan_contract | run_blocked_other | 1 |
| action_recovery_budget_exhausted | planning_contract | 1 |
| witness_intent_contract | recovery_analysis_contract | 1 |
| planning_contract | action_argument_contract | 1 |
| obligation_replan_contract | action_recovery_budget_exhausted | 1 |

### Round12_interrupted_network_20260812T110102Z → Round12_interrupted_network_20260812T123422Z

共有 `59` 个共同题目，其中 `21` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | witness_intent_contract | 13 |
| transport_outcome_unknown | no_result_or_incomplete | 4 |
| witness_intent_contract | no_result_or_incomplete | 4 |
| obligation_replan_contract | witness_intent_contract | 3 |
| witness_intent_contract | transport_outcome_unknown | 3 |
| manual_interruption | no_result_or_incomplete | 3 |
| planning_contract | planning_contract | 3 |
| witness_intent_contract | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | witness_intent_contract | 2 |
| action_recovery_budget_exhausted | transport_outcome_unknown | 2 |
| obligation_replan_contract | no_result_or_incomplete | 2 |
| action_recovery_budget_exhausted | no_result_or_incomplete | 2 |
| witness_intent_contract | action_recovery_budget_exhausted | 2 |
| goal_parse_contract | goal_parse_contract | 2 |
| witness_intent_contract | unhandled_priority_type | 1 |
| obligation_replan_contract | run_blocked_other | 1 |
| obligation_replan_contract | obligation_replan_contract | 1 |
| action_argument_contract | action_recovery_budget_exhausted | 1 |
| action_argument_contract | action_argument_contract | 1 |
| unhandled_priority_type | planning_contract | 1 |

### Round12_interrupted_network_20260812T113505Z → Round12_interrupted_network_20260812T120354Z

共有 `55` 个共同题目，其中 `29` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| no_result_or_incomplete | no_result_or_incomplete | 12 |
| witness_intent_contract | witness_intent_contract | 7 |
| transport_outcome_unknown | transport_outcome_unknown | 4 |
| witness_intent_contract | action_recovery_budget_exhausted | 3 |
| witness_intent_contract | action_argument_contract | 3 |
| obligation_replan_contract | witness_intent_contract | 2 |
| action_argument_contract | transport_outcome_unknown | 2 |
| witness_intent_contract | transport_outcome_unknown | 2 |
| goal_parse_contract | goal_parse_contract | 2 |
| witness_intent_contract | obligation_replan_contract | 1 |
| run_blocked_other | run_blocked_other | 1 |
| run_blocked_other | witness_intent_contract | 1 |
| run_blocked_other | obligation_replan_contract | 1 |
| action_recovery_budget_exhausted | planning_contract | 1 |
| transport_outcome_unknown | no_result_or_incomplete | 1 |
| recovery_analysis_contract | recovery_analysis_contract | 1 |
| action_argument_contract | planning_contract | 1 |
| obligation_replan_contract | action_argument_contract | 1 |
| action_recovery_budget_exhausted | action_argument_contract | 1 |
| obligation_replan_contract | action_recovery_budget_exhausted | 1 |

### Round12_interrupted_network_20260812T113505Z → Round12_interrupted_network_20260812T123422Z

共有 `55` 个共同题目，其中 `34` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | witness_intent_contract | 13 |
| no_result_or_incomplete | no_result_or_incomplete | 11 |
| transport_outcome_unknown | transport_outcome_unknown | 5 |
| obligation_replan_contract | witness_intent_contract | 3 |
| run_blocked_other | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | witness_intent_contract | 2 |
| manual_interruption | planning_contract | 2 |
| goal_parse_contract | goal_parse_contract | 2 |
| witness_intent_contract | unhandled_priority_type | 1 |
| witness_intent_contract | obligation_replan_contract | 1 |
| run_blocked_other | run_blocked_other | 1 |
| no_result_or_incomplete | transport_outcome_unknown | 1 |
| recovery_analysis_contract | action_recovery_budget_exhausted | 1 |
| action_argument_contract | planning_contract | 1 |
| obligation_replan_contract | planning_contract | 1 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 1 |
| action_argument_contract | action_recovery_budget_exhausted | 1 |
| action_argument_contract | action_argument_contract | 1 |
| witness_intent_contract | planning_contract | 1 |
| goal_parse_contract | recovery_analysis_contract | 1 |

### Round12_interrupted_network_20260812T120354Z → Round12_interrupted_network_20260812T123422Z

共有 `57` 个共同题目，其中 `29` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| no_result_or_incomplete | no_result_or_incomplete | 12 |
| witness_intent_contract | witness_intent_contract | 8 |
| action_recovery_budget_exhausted | witness_intent_contract | 4 |
| transport_outcome_unknown | transport_outcome_unknown | 3 |
| action_argument_contract | witness_intent_contract | 3 |
| witness_intent_contract | obligation_replan_contract | 2 |
| no_result_or_incomplete | transport_outcome_unknown | 2 |
| planning_contract | planning_contract | 2 |
| transport_outcome_unknown | witness_intent_contract | 2 |
| goal_parse_contract | goal_parse_contract | 2 |
| action_recovery_budget_exhausted | unhandled_priority_type | 1 |
| obligation_replan_contract | witness_intent_contract | 1 |
| run_blocked_other | run_blocked_other | 1 |
| obligation_replan_contract | obligation_replan_contract | 1 |
| planning_contract | witness_intent_contract | 1 |
| transport_outcome_unknown | no_result_or_incomplete | 1 |
| recovery_analysis_contract | action_recovery_budget_exhausted | 1 |
| action_argument_contract | planning_contract | 1 |
| action_argument_contract | action_recovery_budget_exhausted | 1 |
| transport_outcome_unknown | action_recovery_budget_exhausted | 1 |


## 当前正式运行的验证方式

当前 Round12 第三次运行保持实现冻结。完成后将用同一脚本独立分析，再验证：① transport outcome unknown 是否归零；② witness intent 合约阻断是否仍是主要早期断点；③到达 binding 的题目是被确定性 proof 正确拒绝还是能形成可追溯证据；④ obligation replan 是否在前序任务成功后继续放大请求与恢复预算。代码冻结后启动的这次运行可以验证上述机制假设，但不能验证运行期间后来提出的代码修改。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
