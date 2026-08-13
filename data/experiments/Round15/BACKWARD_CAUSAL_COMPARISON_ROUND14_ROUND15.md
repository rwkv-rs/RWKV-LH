# Round14 → Round15 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round14 → Round15 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round14 | 90 | 90 | 69d535b3b932e41a56612c2470cc31b3d2e16517d10543cd2d4be05759044296 |
| Round15 | 90 | 90 | 24e724116aef9862092329a4603dc3b82fff01c34484481d41cabd67effad610 |

## 总体终态与根因

### Round14

状态：`{"blocked": 71, "interrupted": 10, "not_created": 9}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_contract | 29 |
| action_argument_contract | 14 |
| obligation_replan_budget_exhausted | 11 |
| action_recovery_budget_exhausted | 9 |
| goal_parse_contract | 9 |
| unhandled_priority_type | 6 |
| planning_contract | 6 |
| recovery_analysis_contract | 2 |
| proof_binding_rejection | 1 |
| witness_selection_contract | 1 |
| action_choice_contract | 1 |
| other_model_protocol_contract | 1 |
### Round15

状态：`{"blocked": 74, "interrupted": 9, "not_created": 7}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 27 |
| action_argument_contract | 14 |
| obligation_replan_contract | 13 |
| action_recovery_budget_exhausted | 13 |
| goal_parse_contract | 7 |
| planning_contract | 6 |
| unhandled_priority_type | 4 |
| proof_binding_rejection | 2 |
| witness_selection_contract | 2 |
| recovery_analysis_contract | 1 |
| action_choice_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round14 | Round15 |
|---|---|---|
| run_created | 81 | 83 |
| goal_parsed | 81 | 83 |
| plan_saved | 75 | 77 |
| attempt_started | 75 | 77 |
| action_returned | 75 | 77 |
| task_completed | 72 | 73 |
| goal_obligation_capsule_prepared | 52 | 53 |
| goal_obligation_replan_started | 52 | 53 |
| witness_source_catalog_prepared | 38 | 42 |
| witness_selection_started | 38 | 42 |
| witness_selection_compiled | 19 | 20 |
| witness_intent_precommit_started | 0 | 0 |
| witness_intents_precommitted | 0 | 0 |
| witness_catalog_prepared | 19 | 20 |
| criterion_assertions_evaluated | 16 | 18 |
| witness_binding_evaluated | 16 | 18 |
| criterion_evidence_persisted | 5 | 5 |
| run_completed | 0 | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round14 | Round15 |
|---|---|---|
| action_argument_contract | 14 | 18 |
| action_choice_contract | 2 | 7 |
| action_or_validation_failed | 30 | 31 |
| action_recovery_budget_exhausted | 9 | 13 |
| obligation_gap_triggered_replan | 52 | 53 |
| obligation_replan_blocked | 11 | 27 |
| obligation_replan_contract | 52 | 14 |
| other_model_protocol_contract | 1 | 0 |
| planning_contract | 12 | 15 |
| post_action_source_catalog_reached | 38 | 42 |
| post_action_witness_selection_compiled | 19 | 20 |
| post_action_witness_selection_required | 38 | 42 |
| proof_feedback_triggered_local_revision | 12 | 17 |
| proof_passed | 5 | 5 |
| proof_rejected_other | 12 | 17 |
| proof_rejected_same_source_self_comparison | 0 | 1 |
| recovery_analysis_contract | 2 | 3 |
| unhandled_priority_type | 6 | 4 |
| witness_catalog_reached | 19 | 20 |
| witness_handle_binding_contract | 7 | 5 |
| witness_selection_contract | 38 | 42 |

## 请求与错误放大

### Round14

聚合报告计数：`{"attempt_count": 683, "model_requests": 2441, "replan_count": 0, "task_count": 724}`。

模型请求类型：`{"failure_analysis": 52, "goal_obligation_replan": 204, "replan": 2, "task_decomposition": 93, "tool_action": 696, "tool_choice": 699, "witness_handle_binding": 84, "witness_selection": 507}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 206 | expected_source_handle_id is unknown or not expected-eligible |
| witness_selection | 164 | catalog expected source requires empty expected_goal_literal |
| goal_obligation_replan | 127 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| witness_selection | 79 | goal_quote must be an exact non-empty Goal substring |
| task_decomposition | 18 | invalid plan schema |
| witness_handle_binding | 14 | expected witness handle is not expected-eligible |
| witness_selection | 12 | witness selection item requires criterion/source IDs and expected_goal_literal; only optional note is allowed |
| tool_action | 8 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_handle_binding | 6 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| witness_selection | 4 | pass must select one witness pair per claimed criterion |
| failure_analysis | 4 | failure analysis decision must be retry_same, reselect_action, or replan |
| witness_selection | 4 | actual_source_handle_id is unknown or not actual-eligible |
### Round15

聚合报告计数：`{"attempt_count": 898, "model_requests": 3179, "replan_count": 0, "task_count": 948}`。

模型请求类型：`{"failure_analysis": 61, "goal_obligation_replan": 146, "task_decomposition": 98, "tool_action": 919, "tool_choice": 924, "verification_design": 17, "witness_handle_binding": 183, "witness_selection": 729}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 279 | expected_source_handle_id is unknown or not expected-eligible |
| witness_selection | 211 | catalog expected source requires empty expected_goal_literal |
| witness_selection | 126 | goal_quote must be an exact non-empty Goal substring |
| goal_obligation_replan | 26 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_selection | 26 | witness selection item requires criterion/source IDs and expected_goal_literal; only optional note is allowed |
| task_decomposition | 16 | invalid plan schema |
| tool_choice | 11 | unsupported action type: read_text |
| witness_selection | 10 | witness selection requires schema_version, decision, and witness_selections; only optional reason is allowed |
| witness_handle_binding | 9 | witness binding selected an unknown handle |
| witness_handle_binding | 8 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| tool_action | 7 | action type changed after selection: expected read_json |
| witness_selection | 6 | pass must select one witness pair per claimed criterion |

## 从后向前的关键链

### Round14

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_contract | 29 | 217 | 399 | 17 | E2E-B02, E2E-B06, E2E-B07, E2E-B13, E2E-B14, E2E-B15 |
| action_argument_contract | 14 | 67 | 0 | 0 | E2E-B05, E2E-B10, E2E-H08, E2E-H09, E2E-H10, E2E-H15 |
| obligation_replan_budget_exhausted | 11 | 50 | 324 | 33 | E2E-B01, E2E-B20, E2E-B23, E2E-B25, E2E-B26, E2E-B28 |
| action_recovery_budget_exhausted | 9 | 32 | 54 | 0 | E2E-B04, E2E-B11, E2E-B16, E2E-B21, E2E-H01, E2E-H18 |
| goal_parse_contract | 9 | 0 | 0 | 0 | E2E-B09, E2E-B12, E2E-H11, E2E-LH03, E2E-LH12, E2E-M03 |
| planning_contract | 6 | 0 | 6 | 0 | E2E-H12, E2E-H13, E2E-H14, E2E-LH05, E2E-LH09, E2E-LH11 |
| unhandled_priority_type | 6 | 29 | 54 | 7 | E2E-B03, E2E-B08, E2E-B19, E2E-B27, E2E-H02, E2E-M14 |
| recovery_analysis_contract | 2 | 7 | 2 | 0 | E2E-H07, E2E-M12 |
| action_choice_contract | 1 | 1 | 1 | 0 | E2E-M18 |
| other_model_protocol_contract | 1 | 2 | 1 | 0 | E2E-M19 |
| proof_binding_rejection | 1 | 9 | 8 | 1 | E2E-H17 |
| witness_selection_contract | 1 | 3 | 15 | 1 | E2E-LH04 |
### Round15

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 27 | 155 | 1189 | 81 | E2E-B01, E2E-B02, E2E-B06, E2E-B07, E2E-B08, E2E-B09 |
| action_argument_contract | 14 | 68 | 1 | 0 | E2E-B10, E2E-B19, E2E-B24, E2E-B30, E2E-H07, E2E-H10 |
| action_recovery_budget_exhausted | 13 | 50 | 96 | 1 | E2E-B04, E2E-B05, E2E-B11, E2E-B21, E2E-B27, E2E-B28 |
| obligation_replan_contract | 13 | 180 | 13 | 0 | E2E-B03, E2E-B14, E2E-B17, E2E-H06, E2E-LH02, E2E-LH06 |
| goal_parse_contract | 7 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH12, E2E-M03, E2E-M06, E2E-M13 |
| planning_contract | 6 | 0 | 6 | 0 | E2E-B23, E2E-H05, E2E-LH01, E2E-LH05, E2E-LH11, E2E-M27 |
| unhandled_priority_type | 4 | 23 | 12 | 2 | E2E-H02, E2E-H12, E2E-LH03, E2E-M01 |
| proof_binding_rejection | 2 | 6 | 24 | 0 | E2E-H04, E2E-M08 |
| witness_selection_contract | 2 | 4 | 41 | 3 | E2E-LH04, E2E-M26 |
| action_choice_contract | 1 | 7 | 5 | 0 | E2E-M25 |
| recovery_analysis_contract | 1 | 2 | 1 | 0 | E2E-H18 |

## 独立运行的结构对照

### Round14 → Round15

共有 `90` 个共同题目，其中 `36` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| obligation_replan_contract | obligation_replan_budget_exhausted | 11 |
| obligation_replan_contract | obligation_replan_contract | 10 |
| obligation_replan_budget_exhausted | obligation_replan_budget_exhausted | 6 |
| goal_parse_contract | goal_parse_contract | 6 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 5 |
| action_argument_contract | action_recovery_budget_exhausted | 5 |
| action_argument_contract | action_argument_contract | 5 |
| obligation_replan_contract | action_argument_contract | 3 |
| planning_contract | obligation_replan_budget_exhausted | 3 |
| unhandled_priority_type | obligation_replan_budget_exhausted | 2 |
| obligation_replan_budget_exhausted | proof_binding_rejection | 2 |
| obligation_replan_contract | planning_contract | 2 |
| action_argument_contract | obligation_replan_budget_exhausted | 2 |
| planning_contract | planning_contract | 2 |
| unhandled_priority_type | obligation_replan_contract | 1 |
| goal_parse_contract | obligation_replan_budget_exhausted | 1 |
| action_recovery_budget_exhausted | obligation_replan_budget_exhausted | 1 |
| unhandled_priority_type | action_argument_contract | 1 |
| obligation_replan_budget_exhausted | planning_contract | 1 |
| unhandled_priority_type | action_recovery_budget_exhausted | 1 |


## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round14：transport unknown 0 题；proof pass 5 题；持久 CriterionEvidence 5 题。
- Round15：transport unknown 0 题；proof pass 5 题；持久 CriterionEvidence 5 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
