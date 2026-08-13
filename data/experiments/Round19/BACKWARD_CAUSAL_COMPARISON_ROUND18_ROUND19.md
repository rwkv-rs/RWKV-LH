# Round18 → Round19 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round18 → Round19 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round18 | 90 | 90 | ad96b14e3872552dda192d2018719af866334a57ee428070489ff3bb9e2a7693 |
| Round19 | 90 | 90 | cf5afdbdaee32761e67c6311c227bea5fb097bcde386e23f771911b6c94c29c9 |

## 总体终态与根因

### Round18

状态：`{"blocked": 69, "completed": 1, "interrupted": 13, "not_created": 7}`。

| 终态根因 | 题数 |
|---|---|
| action_argument_contract | 21 |
| obligation_replan_budget_exhausted | 20 |
| obligation_replan_contract | 12 |
| action_recovery_budget_exhausted | 11 |
| unhandled_priority_type | 8 |
| goal_parse_contract | 7 |
| planning_contract | 4 |
| other_model_protocol_contract | 2 |
| proof_binding_rejection | 1 |
| witness_selection_contract | 1 |
| witness_handle_binding_contract | 1 |
| action_choice_contract | 1 |
| run_interrupted_other | 1 |
### Round19

状态：`{"blocked": 73, "interrupted": 8, "not_created": 9}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 28 |
| action_argument_contract | 15 |
| action_recovery_budget_exhausted | 15 |
| obligation_replan_contract | 10 |
| goal_parse_contract | 9 |
| unhandled_priority_type | 4 |
| planning_contract | 4 |
| recovery_analysis_contract | 3 |
| run_interrupted_other | 1 |
| action_choice_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round18 | Round19 |
|---|---|---|
| run_created | 83 | 81 |
| goal_parsed | 83 | 81 |
| plan_saved | 79 | 77 |
| attempt_started | 78 | 77 |
| action_returned | 78 | 77 |
| task_completed | 74 | 72 |
| goal_obligation_capsule_prepared | 53 | 50 |
| goal_obligation_replan_started | 53 | 50 |
| witness_source_catalog_prepared | 34 | 33 |
| witness_selection_started | 34 | 33 |
| witness_selection_compiled | 22 | 23 |
| witness_intent_precommit_started | 0 | 0 |
| witness_intents_precommitted | 0 | 0 |
| witness_catalog_prepared | 22 | 23 |
| criterion_assertions_evaluated | 17 | 21 |
| witness_binding_evaluated | 17 | 21 |
| criterion_evidence_persisted | 6 | 5 |
| run_completed | 1 | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round18 | Round19 |
|---|---|---|
| action_argument_contract | 26 | 19 |
| action_choice_contract | 3 | 3 |
| action_or_validation_failed | 30 | 36 |
| action_recovery_budget_exhausted | 11 | 15 |
| obligation_gap_triggered_replan | 53 | 50 |
| obligation_replan_blocked | 20 | 28 |
| obligation_replan_contract | 13 | 12 |
| other_model_protocol_contract | 25 | 21 |
| planning_contract | 11 | 10 |
| post_action_source_catalog_reached | 34 | 33 |
| post_action_witness_selection_compiled | 22 | 23 |
| post_action_witness_selection_required | 34 | 33 |
| proof_feedback_triggered_local_revision | 17 | 19 |
| proof_passed | 6 | 5 |
| proof_rejected_other | 17 | 19 |
| proof_rejected_same_source_self_comparison | 2 | 1 |
| recovery_analysis_contract | 0 | 3 |
| rwkv_selected_same_source_for_both_sides | 1 | 0 |
| rwkv_selected_same_value_handle_for_both_sides | 1 | 0 |
| unhandled_priority_type | 8 | 4 |
| witness_catalog_reached | 22 | 23 |
| witness_handle_binding_contract | 11 | 15 |
| witness_selection_contract | 26 | 24 |

## 请求与错误放大

### Round18

聚合报告计数：`{"attempt_count": 881, "model_requests": 2867, "replan_count": 0, "task_count": 971}`。

模型请求类型：`{"failure_analysis": 46, "final_answer": 1, "goal_obligation_replan": 136, "task_decomposition": 94, "tool_action": 923, "tool_choice": 906, "witness_expected_mode": 250, "witness_handle_binding": 150, "witness_selection": 260}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 134 | expected_source_handle_id is unknown or not expected-eligible |
| witness_expected_mode | 81 | witness mode requires exactly schema_version and decision |
| witness_selection | 52 | goal_quote must be an exact non-empty Goal substring |
| goal_obligation_replan | 24 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| task_decomposition | 15 | invalid plan schema |
| witness_handle_binding | 15 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| tool_action | 14 | action type changed after selection: expected read_json |
| tool_action | 11 | ValueError: G1i tool call has unknown fields: ['type'] |
| tool_action | 10 | action read_file argument path must be workspace-relative |
| witness_selection | 10 | catalog_source witness binding requires exactly its committed mode fields and optional note |
| witness_expected_mode | 9 | ModelProtocolError: model output does not contain a complete JSON object |
| witness_handle_binding | 7 | expected witness handle is not expected-eligible |
### Round19

聚合报告计数：`{"attempt_count": 896, "model_requests": 2937, "replan_count": 0, "task_count": 949}`。

模型请求类型：`{"failure_analysis": 81, "goal_obligation_replan": 140, "task_decomposition": 91, "tool_action": 917, "tool_choice": 915, "witness_expected_mode": 270, "witness_handle_binding": 193, "witness_selection": 225}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_expected_mode | 113 | witness mode requires exactly schema_version and decision |
| witness_selection | 99 | expected_source_handle_id is unknown or not expected-eligible |
| witness_selection | 48 | goal_quote must be an exact non-empty Goal substring |
| witness_handle_binding | 32 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| goal_obligation_replan | 20 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| task_decomposition | 14 | invalid plan schema |
| witness_handle_binding | 12 | expected witness handle is not expected-eligible |
| witness_expected_mode | 12 | ModelProtocolError: model output does not contain a complete JSON object |
| tool_action | 11 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_handle_binding | 11 | witness binding selected an unknown handle |
| tool_action | 7 | action type changed after selection: expected read_json |
| failure_analysis | 6 | failure analysis decision must be retry_same, reselect_action, or replan |

## 从后向前的关键链

### Round18

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| action_argument_contract | 21 | 92 | 10 | 0 | E2E-B08, E2E-B10, E2E-B21, E2E-B22, E2E-B24, E2E-H05 |
| obligation_replan_budget_exhausted | 20 | 118 | 900 | 60 | E2E-B01, E2E-B03, E2E-B04, E2E-B07, E2E-B14, E2E-B19 |
| obligation_replan_contract | 12 | 158 | 44 | 1 | E2E-B05, E2E-B15, E2E-B18, E2E-B20, E2E-B26, E2E-B29 |
| action_recovery_budget_exhausted | 11 | 34 | 76 | 0 | E2E-B09, E2E-B11, E2E-B27, E2E-B30, E2E-H01, E2E-H08 |
| unhandled_priority_type | 8 | 36 | 85 | 7 | E2E-B02, E2E-B06, E2E-H02, E2E-H04, E2E-H14, E2E-LH03 |
| goal_parse_contract | 7 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH12, E2E-M03, E2E-M06, E2E-M19 |
| planning_contract | 4 | 0 | 4 | 0 | E2E-H13, E2E-LH05, E2E-LH09, E2E-LH11 |
| other_model_protocol_contract | 2 | 9 | 33 | 2 | E2E-B13, E2E-M26 |
| action_choice_contract | 1 | 1 | 1 | 0 | E2E-B28 |
| proof_binding_rejection | 1 | 4 | 46 | 1 | E2E-B16 |
| run_interrupted_other | 1 | 16 | 0 | 0 | E2E-H12 |
| witness_handle_binding_contract | 1 | 9 | 16 | 0 | E2E-B23 |
| witness_selection_contract | 1 | 5 | 47 | 3 | E2E-B17 |
### Round19

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 28 | 145 | 1117 | 84 | E2E-B01, E2E-B02, E2E-B03, E2E-B06, E2E-B08, E2E-B13 |
| action_argument_contract | 15 | 91 | 0 | 0 | E2E-B05, E2E-B10, E2E-B16, E2E-B21, E2E-B24, E2E-H01 |
| action_recovery_budget_exhausted | 15 | 48 | 94 | 0 | E2E-B07, E2E-B11, E2E-B23, E2E-B30, E2E-H07, E2E-H10 |
| obligation_replan_contract | 10 | 137 | 80 | 2 | E2E-B04, E2E-B15, E2E-B18, E2E-B29, E2E-H06, E2E-LH02 |
| goal_parse_contract | 9 | 0 | 0 | 0 | E2E-B09, E2E-B12, E2E-H05, E2E-H11, E2E-LH05, E2E-LH12 |
| planning_contract | 4 | 0 | 4 | 0 | E2E-H13, E2E-LH07, E2E-LH08, E2E-LH11 |
| unhandled_priority_type | 4 | 21 | 0 | 0 | E2E-B14, E2E-H02, E2E-H04, E2E-H12 |
| recovery_analysis_contract | 3 | 11 | 3 | 0 | E2E-H16, E2E-LH01, E2E-LH03 |
| action_choice_contract | 1 | 4 | 1 | 0 | E2E-M28 |
| run_interrupted_other | 1 | 1 | 2 | 0 | E2E-LH04 |

## 独立运行的结构对照

### Round18 → Round19

共有 `90` 个共同题目，其中 `37` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| obligation_replan_budget_exhausted | obligation_replan_budget_exhausted | 12 |
| action_argument_contract | action_recovery_budget_exhausted | 7 |
| action_argument_contract | action_argument_contract | 6 |
| goal_parse_contract | goal_parse_contract | 6 |
| obligation_replan_contract | obligation_replan_contract | 5 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 4 |
| obligation_replan_contract | obligation_replan_budget_exhausted | 4 |
| unhandled_priority_type | obligation_replan_budget_exhausted | 3 |
| obligation_replan_budget_exhausted | obligation_replan_contract | 3 |
| obligation_replan_budget_exhausted | action_recovery_budget_exhausted | 3 |
| action_recovery_budget_exhausted | action_argument_contract | 3 |
| obligation_replan_contract | action_argument_contract | 2 |
| action_argument_contract | obligation_replan_budget_exhausted | 2 |
| other_model_protocol_contract | obligation_replan_budget_exhausted | 2 |
| action_recovery_budget_exhausted | obligation_replan_budget_exhausted | 2 |
| unhandled_priority_type | unhandled_priority_type | 2 |
| planning_contract | planning_contract | 2 |
| action_recovery_budget_exhausted | goal_parse_contract | 1 |
| obligation_replan_budget_exhausted | unhandled_priority_type | 1 |
| proof_binding_rejection | action_argument_contract | 1 |


## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round18：transport unknown 0 题；proof pass 6 题；持久 CriterionEvidence 6 题。
- Round19：transport unknown 0 题；proof pass 5 题；持久 CriterionEvidence 5 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
