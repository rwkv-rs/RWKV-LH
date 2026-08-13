# Round21 → Round22 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round21 → Round22 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round21 | 90 | 90 | b6622abed360b37a6dd2389fb088e7f5e63556917a858db54725082e861385db |
| Round22 | 90 | 90 | 5dab26b4663ec340b29f3fadba8bd641c85b59ebd861c61e581e615ede981288 |

## 总体终态与根因

### Round21

状态：`{"blocked": 71, "interrupted": 11, "not_created": 8}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 25 |
| action_recovery_budget_exhausted | 19 |
| planning_contract | 11 |
| action_argument_contract | 8 |
| goal_parse_contract | 8 |
| obligation_replan_contract | 8 |
| unhandled_priority_type | 7 |
| run_interrupted_other | 2 |
| recovery_analysis_contract | 1 |
| other_model_protocol_contract | 1 |
### Round22

状态：`{"blocked": 73, "interrupted": 11, "not_created": 6}`。

| 终态根因 | 题数 |
|---|---|
| action_argument_contract | 36 |
| obligation_replan_budget_exhausted | 17 |
| action_recovery_budget_exhausted | 11 |
| unhandled_priority_type | 9 |
| goal_parse_contract | 6 |
| obligation_replan_contract | 4 |
| planning_contract | 4 |
| action_choice_contract | 1 |
| run_interrupted_other | 1 |
| recovery_analysis_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round21 | Round22 |
|---|---|---|
| run_created | 82 | 84 |
| goal_parsed | 82 | 84 |
| plan_saved | 71 | 80 |
| attempt_started | 71 | 80 |
| action_returned | 71 | 80 |
| task_completed | 69 | 75 |
| goal_obligation_capsule_prepared | 45 | 36 |
| goal_obligation_replan_started | 45 | 36 |
| witness_source_catalog_prepared | 43 | 33 |
| witness_selection_started | 43 | 33 |
| witness_selection_compiled | 29 | 17 |
| witness_intent_precommit_started | 0 | 0 |
| witness_intents_precommitted | 0 | 0 |
| witness_catalog_prepared | 29 | 17 |
| criterion_assertions_evaluated | 24 | 15 |
| witness_binding_evaluated | 24 | 15 |
| criterion_evidence_persisted | 2 | 0 |
| run_completed | 0 | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round21 | Round22 |
|---|---|---|
| action_argument_contract | 12 | 40 |
| action_choice_contract | 1 | 4 |
| action_or_validation_failed | 30 | 29 |
| action_recovery_budget_exhausted | 19 | 11 |
| obligation_gap_triggered_replan | 45 | 36 |
| obligation_replan_blocked | 25 | 17 |
| obligation_replan_contract | 10 | 6 |
| other_model_protocol_contract | 19 | 19 |
| planning_contract | 19 | 9 |
| post_action_source_catalog_reached | 43 | 33 |
| post_action_witness_selection_compiled | 29 | 17 |
| post_action_witness_selection_required | 43 | 33 |
| proof_feedback_triggered_local_revision | 24 | 15 |
| proof_passed | 2 | 0 |
| proof_rejected_other | 24 | 15 |
| proof_rejected_same_source_self_comparison | 1 | 1 |
| recovery_analysis_contract | 1 | 1 |
| rwkv_selected_same_source_for_both_sides | 1 | 1 |
| rwkv_selected_same_value_handle_for_both_sides | 1 | 1 |
| unhandled_priority_type | 7 | 9 |
| witness_catalog_reached | 29 | 17 |
| witness_handle_binding_contract | 14 | 10 |
| witness_selection_contract | 30 | 14 |

## 请求与错误放大

### Round21

聚合报告计数：`{"attempt_count": 766, "model_requests": 2636, "replan_count": 0, "task_count": 795}`。

模型请求类型：`{"failure_analysis": 53, "goal_obligation_replan": 125, "task_decomposition": 101, "tool_action": 781, "tool_choice": 774, "verification_design": 4, "witness_expected_mode": 265, "witness_handle_binding": 223, "witness_selection": 210}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_expected_mode | 118 | witness mode requires exactly schema_version and decision |
| witness_selection | 99 | expected_source_handle_id is unknown or not expected-eligible |
| task_decomposition | 28 | invalid plan schema |
| witness_selection | 24 | goal_quote must be an exact non-empty Goal substring |
| goal_obligation_replan | 18 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_handle_binding | 16 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| witness_selection | 8 | catalog_source witness binding requires exactly its committed mode fields and optional note |
| witness_handle_binding | 8 | witness binding selected an unknown handle |
| witness_handle_binding | 6 | actual witness handle changes the precommitted source kind |
| witness_handle_binding | 6 | expected witness handle is not expected-eligible |
| tool_action | 5 | action type changed after selection: expected read_json |
| witness_expected_mode | 5 | ModelProtocolError: model output does not contain a complete JSON object |
### Round22

聚合报告计数：`{"attempt_count": 535, "model_requests": 1919, "replan_count": 0, "task_count": 724}`。

模型请求类型：`{"failure_analysis": 46, "goal_obligation_replan": 86, "task_decomposition": 93, "tool_action": 579, "tool_choice": 575, "verification_design": 13, "witness_expected_mode": 154, "witness_handle_binding": 161, "witness_selection": 111}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_expected_mode | 66 | witness mode requires exactly schema_version and decision |
| witness_selection | 35 | expected_source_handle_id is unknown or not expected-eligible |
| witness_handle_binding | 22 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| tool_action | 20 | ValueError: G1i tool call has unknown fields: ['action'] |
| witness_selection | 18 | goal_quote must be an exact non-empty Goal substring |
| task_decomposition | 13 | invalid plan schema |
| goal_obligation_replan | 10 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_handle_binding | 7 | expected witness handle is not expected-eligible |
| witness_expected_mode | 7 | ModelProtocolError: model output does not contain a complete JSON object |
| witness_handle_binding | 7 | witness binding selected an unknown handle |
| witness_selection | 6 | catalog_source witness binding requires exactly its committed mode fields and optional note |
| witness_handle_binding | 5 | actual witness handle changes the precommitted source kind |

## 从后向前的关键链

### Round21

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 25 | 148 | 845 | 75 | E2E-B01, E2E-B03, E2E-B05, E2E-B06, E2E-B08, E2E-B13 |
| action_recovery_budget_exhausted | 19 | 88 | 109 | 0 | E2E-B04, E2E-B07, E2E-B09, E2E-B11, E2E-B21, E2E-B26 |
| planning_contract | 11 | 0 | 11 | 0 | E2E-H02, E2E-H05, E2E-H12, E2E-H13, E2E-H15, E2E-LH01 |
| action_argument_contract | 8 | 31 | 0 | 0 | E2E-B10, E2E-B24, E2E-H16, E2E-LH08, E2E-M02, E2E-M08 |
| goal_parse_contract | 8 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH03, E2E-LH12, E2E-M03, E2E-M06 |
| obligation_replan_contract | 8 | 119 | 60 | 1 | E2E-H06, E2E-LH09, E2E-M01, E2E-M11, E2E-M15, E2E-M23 |
| unhandled_priority_type | 7 | 40 | 41 | 5 | E2E-B02, E2E-B14, E2E-B15, E2E-B20, E2E-M04, E2E-M07 |
| run_interrupted_other | 2 | 4 | 2 | 0 | E2E-B23, E2E-LH04 |
| other_model_protocol_contract | 1 | 4 | 4 | 0 | E2E-M26 |
| recovery_analysis_contract | 1 | 2 | 1 | 0 | E2E-H18 |
### Round22

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| action_argument_contract | 36 | 150 | 5 | 0 | E2E-B03, E2E-B05, E2E-B10, E2E-B20, E2E-B21, E2E-B22 |
| obligation_replan_budget_exhausted | 17 | 88 | 544 | 51 | E2E-B02, E2E-B04, E2E-B07, E2E-B08, E2E-B13, E2E-B15 |
| action_recovery_budget_exhausted | 11 | 16 | 73 | 0 | E2E-B11, E2E-B23, E2E-H08, E2E-H10, E2E-H18, E2E-M10 |
| unhandled_priority_type | 9 | 32 | 78 | 6 | E2E-B01, E2E-B06, E2E-B14, E2E-B19, E2E-B25, E2E-B28 |
| goal_parse_contract | 6 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH12, E2E-M03, E2E-M06, E2E-M20 |
| obligation_replan_contract | 4 | 32 | 4 | 0 | E2E-B29, E2E-H04, E2E-LH04, E2E-M07 |
| planning_contract | 4 | 0 | 4 | 0 | E2E-H02, E2E-LH05, E2E-LH07, E2E-LH11 |
| action_choice_contract | 1 | 1 | 1 | 0 | E2E-B09 |
| recovery_analysis_contract | 1 | 4 | 1 | 0 | E2E-H14 |
| run_interrupted_other | 1 | 1 | 0 | 0 | E2E-H12 |

## 独立运行的结构对照

### Round21 → Round22

共有 `90` 个共同题目，其中 `30` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| action_argument_contract | action_argument_contract | 8 |
| obligation_replan_budget_exhausted | unhandled_priority_type | 7 |
| obligation_replan_budget_exhausted | action_argument_contract | 7 |
| obligation_replan_budget_exhausted | obligation_replan_budget_exhausted | 7 |
| action_recovery_budget_exhausted | obligation_replan_budget_exhausted | 6 |
| goal_parse_contract | goal_parse_contract | 6 |
| action_recovery_budget_exhausted | action_argument_contract | 6 |
| planning_contract | action_argument_contract | 6 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 5 |
| obligation_replan_contract | action_argument_contract | 5 |
| planning_contract | planning_contract | 3 |
| unhandled_priority_type | obligation_replan_budget_exhausted | 2 |
| unhandled_priority_type | action_argument_contract | 2 |
| obligation_replan_budget_exhausted | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | action_choice_contract | 1 |
| unhandled_priority_type | unhandled_priority_type | 1 |
| run_interrupted_other | action_recovery_budget_exhausted | 1 |
| obligation_replan_budget_exhausted | action_recovery_budget_exhausted | 1 |
| planning_contract | run_interrupted_other | 1 |
| obligation_replan_budget_exhausted | recovery_analysis_contract | 1 |


## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round21：transport unknown 0 题；proof pass 2 题；持久 CriterionEvidence 2 题。
- Round22：transport unknown 0 题；proof pass 0 题；持久 CriterionEvidence 0 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
