# Round17 → Round18 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round17 → Round18 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round17 | 90 | 90 | be14cf2cf636707d8001198e8dd095d506cd8a01b2fa019812b7bebb5cffb52b |
| Round18 | 90 | 90 | ad96b14e3872552dda192d2018719af866334a57ee428070489ff3bb9e2a7693 |

## 总体终态与根因

### Round17

状态：`{"blocked": 73, "interrupted": 10, "not_created": 7}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 29 |
| action_argument_contract | 15 |
| action_recovery_budget_exhausted | 13 |
| obligation_replan_contract | 12 |
| goal_parse_contract | 7 |
| recovery_analysis_contract | 5 |
| unhandled_priority_type | 4 |
| planning_contract | 4 |
| witness_selection_contract | 1 |
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

## 环节漏斗（到达该环节的题数）

| 环节 | Round17 | Round18 |
|---|---|---|
| run_created | 83 | 83 |
| goal_parsed | 83 | 83 |
| plan_saved | 79 | 79 |
| attempt_started | 79 | 78 |
| action_returned | 79 | 78 |
| task_completed | 75 | 74 |
| goal_obligation_capsule_prepared | 53 | 53 |
| goal_obligation_replan_started | 53 | 53 |
| witness_source_catalog_prepared | 39 | 34 |
| witness_selection_started | 39 | 34 |
| witness_selection_compiled | 4 | 22 |
| witness_intent_precommit_started | 0 | 0 |
| witness_intents_precommitted | 0 | 0 |
| witness_catalog_prepared | 4 | 22 |
| criterion_assertions_evaluated | 3 | 17 |
| witness_binding_evaluated | 3 | 17 |
| criterion_evidence_persisted | 1 | 6 |
| run_completed | 0 | 1 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round17 | Round18 |
|---|---|---|
| action_argument_contract | 17 | 26 |
| action_choice_contract | 1 | 3 |
| action_or_validation_failed | 33 | 30 |
| action_recovery_budget_exhausted | 13 | 11 |
| obligation_gap_triggered_replan | 53 | 53 |
| obligation_replan_blocked | 29 | 20 |
| obligation_replan_contract | 13 | 13 |
| other_model_protocol_contract | 0 | 25 |
| planning_contract | 11 | 11 |
| post_action_source_catalog_reached | 39 | 34 |
| post_action_witness_selection_compiled | 4 | 22 |
| post_action_witness_selection_required | 39 | 34 |
| proof_feedback_triggered_local_revision | 3 | 17 |
| proof_passed | 1 | 6 |
| proof_rejected_other | 3 | 17 |
| proof_rejected_same_source_self_comparison | 1 | 2 |
| recovery_analysis_contract | 5 | 0 |
| rwkv_selected_same_source_for_both_sides | 0 | 1 |
| rwkv_selected_same_value_handle_for_both_sides | 0 | 1 |
| unhandled_priority_type | 4 | 8 |
| witness_catalog_reached | 4 | 22 |
| witness_handle_binding_contract | 0 | 11 |
| witness_selection_contract | 39 | 26 |

## 请求与错误放大

### Round17

聚合报告计数：`{"attempt_count": 903, "model_requests": 2937, "replan_count": 0, "task_count": 988}`。

模型请求类型：`{"failure_analysis": 57, "goal_obligation_replan": 146, "task_decomposition": 94, "tool_action": 920, "tool_choice": 918, "verification_design": 5, "witness_handle_binding": 40, "witness_selection": 657}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 348 | catalog_source mode requires exactly criterion_id, actual_source_handle_id, expected_mode, expected_source_handle_id, and optional note |
| witness_selection | 187 | expected_mode must be catalog_source or goal_literal |
| witness_selection | 34 | witness selection requires schema_version, decision, and witness_selections; only optional reason is allowed |
| witness_selection | 30 | witness selection item requires criterion_id, actual_source_handle_id, and expected_mode; only mode-specific fields and optional note are allowed |
| goal_obligation_replan | 24 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_selection | 15 | expected_source_handle_id is unknown or not expected-eligible |
| task_decomposition | 15 | invalid plan schema |
| witness_selection | 14 | goal_quote must be an exact non-empty Goal substring |
| failure_analysis | 10 | failure analysis decision must be retry_same, reselect_action, or replan |
| witness_selection | 8 | actual_source_handle_id is unknown or not actual-eligible |
| tool_action | 7 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_selection | 4 | pass must select one witness pair per claimed criterion |
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

## 从后向前的关键链

### Round17

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 29 | 149 | 994 | 87 | E2E-B01, E2E-B02, E2E-B04, E2E-B05, E2E-B06, E2E-B07 |
| action_argument_contract | 15 | 80 | 1 | 0 | E2E-B10, E2E-B24, E2E-H02, E2E-H03, E2E-H10, E2E-H13 |
| action_recovery_budget_exhausted | 13 | 49 | 77 | 0 | E2E-B11, E2E-B16, E2E-B21, E2E-B27, E2E-H01, E2E-H07 |
| obligation_replan_contract | 12 | 152 | 152 | 2 | E2E-B03, E2E-B13, E2E-B14, E2E-B23, E2E-H05, E2E-H06 |
| goal_parse_contract | 7 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH03, E2E-LH12, E2E-M03, E2E-M06 |
| recovery_analysis_contract | 5 | 23 | 5 | 0 | E2E-H16, E2E-H18, E2E-LH10, E2E-M16, E2E-M24 |
| planning_contract | 4 | 0 | 4 | 0 | E2E-H14, E2E-LH05, E2E-LH07, E2E-LH11 |
| unhandled_priority_type | 4 | 15 | 104 | 4 | E2E-B30, E2E-H04, E2E-LH01, E2E-M26 |
| witness_selection_contract | 1 | 15 | 25 | 1 | E2E-H12 |
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

## 独立运行的结构对照

### Round17 → Round18

共有 `90` 个共同题目，其中 `35` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| obligation_replan_budget_exhausted | obligation_replan_budget_exhausted | 11 |
| action_argument_contract | action_argument_contract | 10 |
| obligation_replan_budget_exhausted | obligation_replan_contract | 9 |
| obligation_replan_contract | obligation_replan_budget_exhausted | 6 |
| goal_parse_contract | goal_parse_contract | 6 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 5 |
| action_recovery_budget_exhausted | action_argument_contract | 4 |
| obligation_replan_contract | action_argument_contract | 3 |
| obligation_replan_budget_exhausted | unhandled_priority_type | 2 |
| obligation_replan_budget_exhausted | action_argument_contract | 2 |
| obligation_replan_budget_exhausted | action_recovery_budget_exhausted | 2 |
| unhandled_priority_type | action_recovery_budget_exhausted | 2 |
| action_argument_contract | obligation_replan_contract | 2 |
| action_recovery_budget_exhausted | obligation_replan_budget_exhausted | 2 |
| recovery_analysis_contract | action_argument_contract | 2 |
| planning_contract | planning_contract | 2 |
| recovery_analysis_contract | action_recovery_budget_exhausted | 2 |
| obligation_replan_contract | other_model_protocol_contract | 1 |
| action_recovery_budget_exhausted | proof_binding_rejection | 1 |
| obligation_replan_budget_exhausted | witness_selection_contract | 1 |


## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round17：transport unknown 0 题；proof pass 1 题；持久 CriterionEvidence 1 题。
- Round18：transport unknown 0 题；proof pass 6 题；持久 CriterionEvidence 6 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
