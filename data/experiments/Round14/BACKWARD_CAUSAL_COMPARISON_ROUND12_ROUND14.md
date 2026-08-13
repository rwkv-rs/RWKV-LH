# Round12 → Round13 → Round14 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round12 → Round13 → Round14 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round12 | 90 | 90 | 85e2759678a27c57f61739d896c77513fc19e985dfb19fcbe9f04dcc899d1a30 |
| Round13 | 90 | 90 | 7ddce9e175ea2e192f546c2856c7a8f7aa419099b2f200d9f1e23e30a33a37e7 |
| Round14 | 90 | 90 | 69d535b3b932e41a56612c2470cc31b3d2e16517d10543cd2d4be05759044296 |

## 总体终态与根因

### Round12

状态：`{"blocked": 74, "interrupted": 9, "not_created": 7}`。

| 终态根因 | 题数 |
|---|---|
| witness_intent_contract | 30 |
| obligation_replan_contract | 13 |
| action_recovery_budget_exhausted | 10 |
| action_argument_contract | 9 |
| unhandled_priority_type | 7 |
| goal_parse_contract | 7 |
| planning_contract | 6 |
| run_blocked_other | 4 |
| action_choice_contract | 2 |
| recovery_analysis_contract | 2 |
### Round13

状态：`{"blocked": 74, "interrupted": 11, "not_created": 5}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_contract | 34 |
| action_argument_contract | 14 |
| action_recovery_budget_exhausted | 11 |
| run_blocked_other | 10 |
| unhandled_priority_type | 8 |
| goal_parse_contract | 5 |
| planning_contract | 4 |
| recovery_analysis_contract | 3 |
| action_choice_contract | 1 |
### Round14

状态：`{"blocked": 71, "interrupted": 10, "not_created": 9}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_contract | 29 |
| action_argument_contract | 14 |
| run_blocked_other | 11 |
| action_recovery_budget_exhausted | 9 |
| goal_parse_contract | 9 |
| unhandled_priority_type | 6 |
| planning_contract | 6 |
| recovery_analysis_contract | 2 |
| proof_binding_rejection | 1 |
| witness_selection_contract | 1 |
| action_choice_contract | 1 |
| other_model_protocol_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round12 | Round13 | Round14 |
|---|---|---|---|
| run_created | 83 | 85 | 81 |
| goal_parsed | 83 | 85 | 81 |
| plan_saved | 77 | 81 | 75 |
| attempt_started | 76 | 80 | 75 |
| action_returned | 76 | 80 | 75 |
| task_completed | 74 | 73 | 72 |
| goal_obligation_capsule_prepared | 26 | 54 | 52 |
| goal_obligation_replan_started | 26 | 54 | 52 |
| witness_source_catalog_prepared | 0 | 34 | 38 |
| witness_selection_started | 0 | 34 | 38 |
| witness_selection_compiled | 0 | 1 | 19 |
| witness_intent_precommit_started | 32 | 0 | 0 |
| witness_intents_precommitted | 6 | 0 | 0 |
| witness_catalog_prepared | 6 | 1 | 19 |
| criterion_assertions_evaluated | 3 | 1 | 16 |
| witness_binding_evaluated | 3 | 1 | 16 |
| criterion_evidence_persisted | 0 | 0 | 5 |
| run_completed | 0 | 0 | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round12 | Round13 | Round14 |
|---|---|---|---|
| action_argument_contract | 13 | 18 | 14 |
| action_choice_contract | 5 | 3 | 2 |
| action_or_validation_failed | 22 | 30 | 30 |
| action_recovery_budget_exhausted | 10 | 11 | 9 |
| intent_actual_expected_same_kind_without_goal_literal | 3 | 0 | 0 |
| obligation_gap_triggered_replan | 26 | 54 | 52 |
| obligation_replan_blocked | 4 | 10 | 11 |
| obligation_replan_contract | 26 | 54 | 52 |
| other_model_protocol_contract | 0 | 0 | 1 |
| planning_contract | 14 | 6 | 12 |
| post_action_source_catalog_reached | 0 | 34 | 38 |
| post_action_witness_selection_compiled | 0 | 1 | 19 |
| post_action_witness_selection_required | 0 | 34 | 38 |
| proof_feedback_triggered_local_revision | 2 | 1 | 12 |
| proof_passed | 0 | 0 | 5 |
| proof_rejected_other | 3 | 1 | 12 |
| proof_rejected_same_source_self_comparison | 1 | 0 | 0 |
| recovery_analysis_contract | 2 | 3 | 2 |
| rwkv_selected_same_source_for_both_sides | 1 | 0 | 0 |
| rwkv_selected_same_value_handle_for_both_sides | 1 | 0 | 0 |
| unhandled_priority_type | 7 | 8 | 6 |
| witness_catalog_reached | 6 | 1 | 19 |
| witness_handle_binding_contract | 1 | 1 | 7 |
| witness_intent_contract | 32 | 0 | 0 |
| witness_intent_required | 32 | 0 | 0 |
| witness_intent_revision_contract | 1 | 0 | 0 |
| witness_selection_contract | 0 | 33 | 38 |
| witness_source_selection_contract | 4 | 0 | 0 |

## 请求与错误放大

### Round12

聚合报告计数：`{"attempt_count": 456, "model_requests": 1436, "replan_count": 0, "task_count": 575}`。

模型请求类型：`{"failure_analysis": 35, "goal_obligation_replan": 78, "task_decomposition": 97, "tool_action": 502, "tool_choice": 504, "witness_handle_binding": 7, "witness_intent_precommit": 79, "witness_intent_revision": 12, "witness_validation": 21}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| goal_obligation_replan | 48 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| witness_intent_precommit | 38 | invalid expected witness source kind |
| task_decomposition | 20 | invalid plan schema |
| witness_intent_precommit | 9 | non-goal expected witness must use empty expected_goal_literal |
| witness_intent_precommit | 9 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| tool_choice | 7 | unsupported action type: read_csv |
| tool_action | 6 | action type changed after selection: expected read_json |
| witness_intent_revision | 6 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 5 | witness intent comparison must be exact_equals |
| tool_action | 4 | ValueError: G1i tool call has unknown fields: ['type'] |
| failure_analysis | 4 | failure analysis decision must be retry_same, reselect_action, or replan |
| witness_validation | 3 | revise_intent/replan witness decision must not select sources |
### Round13

聚合报告计数：`{"attempt_count": 638, "model_requests": 2126, "replan_count": 0, "task_count": 698}`。

模型请求类型：`{"failure_analysis": 52, "goal_obligation_replan": 194, "task_decomposition": 91, "tool_action": 656, "tool_choice": 655, "verification_design": 5, "witness_handle_binding": 20, "witness_selection": 355}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 209 | witness selection fields must be exactly ['decision', 'reason', 'schema_version', 'witness_selections'] |
| goal_obligation_replan | 128 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| witness_selection | 98 | goal_quote must be an exact non-empty Goal substring |
| witness_selection | 22 | Goal expected source requires exactly goal_quote and value |
| task_decomposition | 10 | invalid plan schema |
| witness_selection | 7 | pass must select one witness pair per claimed criterion |
| tool_action | 6 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_selection | 6 | catalog expected source requires empty expected_goal_literal |
| failure_analysis | 4 | failure analysis decision must be retry_same, reselect_action, or replan |
| tool_choice | 3 | unsupported action type: read_csv |
| tool_action | 3 | action type changed after selection: expected read_json |
| witness_selection | 3 | expected_source_handle_id is unknown or not expected-eligible |
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

## 从后向前的关键链

### Round12

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| witness_intent_contract | 30 | 123 | 55 | 1 | E2E-B04, E2E-B10, E2E-B16, E2E-B17, E2E-B18, E2E-B20 |
| obligation_replan_contract | 13 | 85 | 45 | 3 | E2E-B03, E2E-B07, E2E-B08, E2E-B15, E2E-H08, E2E-LH02 |
| action_recovery_budget_exhausted | 10 | 18 | 65 | 0 | E2E-B01, E2E-B11, E2E-B21, E2E-H09, E2E-H10, E2E-LH01 |
| action_argument_contract | 9 | 36 | 1 | 0 | E2E-B13, E2E-B22, E2E-H16, E2E-H18, E2E-LH04, E2E-LH08 |
| goal_parse_contract | 7 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH12, E2E-M03, E2E-M06, E2E-M20 |
| unhandled_priority_type | 7 | 35 | 28 | 3 | E2E-B02, E2E-B14, E2E-B19, E2E-B30, E2E-H17, E2E-M14 |
| planning_contract | 6 | 0 | 6 | 0 | E2E-H05, E2E-H13, E2E-LH05, E2E-LH07, E2E-LH09, E2E-LH11 |
| run_blocked_other | 4 | 79 | 0 | 0 | E2E-B05, E2E-B06, E2E-H03, E2E-M21 |
| action_choice_contract | 2 | 2 | 2 | 0 | E2E-B09, E2E-B28 |
| recovery_analysis_contract | 2 | 5 | 2 | 0 | E2E-M02, E2E-M12 |
### Round13

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_contract | 34 | 206 | 260 | 14 | E2E-B02, E2E-B03, E2E-B06, E2E-B08, E2E-B14, E2E-B15 |
| action_argument_contract | 14 | 63 | 0 | 0 | E2E-B10, E2E-B24, E2E-H02, E2E-H05, E2E-H15, E2E-H16 |
| action_recovery_budget_exhausted | 11 | 23 | 73 | 0 | E2E-B01, E2E-B09, E2E-B27, E2E-H01, E2E-H07, E2E-H08 |
| run_blocked_other | 10 | 143 | 0 | 0 | E2E-B04, E2E-B05, E2E-B13, E2E-B16, E2E-B18, E2E-LH09 |
| unhandled_priority_type | 8 | 48 | 138 | 7 | E2E-B07, E2E-B19, E2E-B22, E2E-B26, E2E-B30, E2E-H12 |
| goal_parse_contract | 5 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-M03, E2E-M06, E2E-M20 |
| planning_contract | 4 | 0 | 4 | 0 | E2E-H13, E2E-LH05, E2E-LH08, E2E-LH11 |
| recovery_analysis_contract | 3 | 4 | 2 | 0 | E2E-B11, E2E-M08, E2E-M13 |
| action_choice_contract | 1 | 1 | 1 | 0 | E2E-B28 |
### Round14

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_contract | 29 | 217 | 399 | 17 | E2E-B02, E2E-B06, E2E-B07, E2E-B13, E2E-B14, E2E-B15 |
| action_argument_contract | 14 | 67 | 0 | 0 | E2E-B05, E2E-B10, E2E-H08, E2E-H09, E2E-H10, E2E-H15 |
| run_blocked_other | 11 | 132 | 0 | 0 | E2E-B01, E2E-B20, E2E-B23, E2E-B25, E2E-B26, E2E-B28 |
| action_recovery_budget_exhausted | 9 | 32 | 54 | 0 | E2E-B04, E2E-B11, E2E-B16, E2E-B21, E2E-H01, E2E-H18 |
| goal_parse_contract | 9 | 0 | 0 | 0 | E2E-B09, E2E-B12, E2E-H11, E2E-LH03, E2E-LH12, E2E-M03 |
| planning_contract | 6 | 0 | 6 | 0 | E2E-H12, E2E-H13, E2E-H14, E2E-LH05, E2E-LH09, E2E-LH11 |
| unhandled_priority_type | 6 | 29 | 54 | 7 | E2E-B03, E2E-B08, E2E-B19, E2E-B27, E2E-H02, E2E-M14 |
| recovery_analysis_contract | 2 | 7 | 2 | 0 | E2E-H07, E2E-M12 |
| action_choice_contract | 1 | 1 | 1 | 0 | E2E-M18 |
| other_model_protocol_contract | 1 | 2 | 1 | 0 | E2E-M19 |
| proof_binding_rejection | 1 | 9 | 8 | 1 | E2E-H17 |
| witness_selection_contract | 1 | 3 | 15 | 1 | E2E-LH04 |

## 独立运行的结构对照

### Round12 → Round13

共有 `90` 个共同题目，其中 `26` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | obligation_replan_contract | 13 |
| obligation_replan_contract | obligation_replan_contract | 8 |
| witness_intent_contract | action_argument_contract | 6 |
| witness_intent_contract | run_blocked_other | 5 |
| goal_parse_contract | goal_parse_contract | 5 |
| unhandled_priority_type | obligation_replan_contract | 4 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 3 |
| run_blocked_other | obligation_replan_contract | 3 |
| witness_intent_contract | action_recovery_budget_exhausted | 3 |
| planning_contract | planning_contract | 3 |
| action_argument_contract | action_argument_contract | 3 |
| obligation_replan_contract | unhandled_priority_type | 2 |
| action_recovery_budget_exhausted | recovery_analysis_contract | 2 |
| unhandled_priority_type | unhandled_priority_type | 2 |
| action_recovery_budget_exhausted | obligation_replan_contract | 2 |
| witness_intent_contract | unhandled_priority_type | 2 |
| action_recovery_budget_exhausted | action_argument_contract | 2 |
| action_argument_contract | obligation_replan_contract | 2 |
| run_blocked_other | run_blocked_other | 1 |
| action_choice_contract | action_recovery_budget_exhausted | 1 |

### Round12 → Round14

共有 `90` 个共同题目，其中 `26` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| witness_intent_contract | obligation_replan_contract | 11 |
| obligation_replan_contract | obligation_replan_contract | 7 |
| goal_parse_contract | goal_parse_contract | 7 |
| witness_intent_contract | run_blocked_other | 7 |
| witness_intent_contract | action_argument_contract | 4 |
| action_argument_contract | obligation_replan_contract | 4 |
| action_recovery_budget_exhausted | action_argument_contract | 4 |
| planning_contract | planning_contract | 4 |
| unhandled_priority_type | obligation_replan_contract | 3 |
| witness_intent_contract | action_recovery_budget_exhausted | 3 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 3 |
| action_argument_contract | action_recovery_budget_exhausted | 3 |
| obligation_replan_contract | unhandled_priority_type | 2 |
| run_blocked_other | obligation_replan_contract | 2 |
| unhandled_priority_type | unhandled_priority_type | 2 |
| witness_intent_contract | unhandled_priority_type | 2 |
| obligation_replan_contract | action_argument_contract | 2 |
| witness_intent_contract | planning_contract | 2 |
| action_recovery_budget_exhausted | run_blocked_other | 1 |
| run_blocked_other | action_argument_contract | 1 |

### Round13 → Round14

共有 `90` 个共同题目，其中 `34` 个终态根因类别相同。由于采样终止点和网络状态不同，这只能判断结构复现，不能判断正确率升降。

| 前一运行根因 | 后一运行根因 | 题数 |
|---|---|---|
| obligation_replan_contract | obligation_replan_contract | 16 |
| action_argument_contract | action_argument_contract | 6 |
| goal_parse_contract | goal_parse_contract | 5 |
| obligation_replan_contract | run_blocked_other | 5 |
| unhandled_priority_type | obligation_replan_contract | 4 |
| run_blocked_other | obligation_replan_contract | 4 |
| action_argument_contract | obligation_replan_contract | 4 |
| obligation_replan_contract | action_argument_contract | 4 |
| action_recovery_budget_exhausted | action_argument_contract | 3 |
| planning_contract | planning_contract | 3 |
| obligation_replan_contract | unhandled_priority_type | 2 |
| run_blocked_other | action_recovery_budget_exhausted | 2 |
| action_recovery_budget_exhausted | goal_parse_contract | 2 |
| recovery_analysis_contract | action_recovery_budget_exhausted | 2 |
| unhandled_priority_type | run_blocked_other | 2 |
| action_recovery_budget_exhausted | action_recovery_budget_exhausted | 2 |
| action_recovery_budget_exhausted | recovery_analysis_contract | 2 |
| action_argument_contract | action_recovery_budget_exhausted | 2 |
| obligation_replan_contract | goal_parse_contract | 2 |
| action_recovery_budget_exhausted | run_blocked_other | 1 |


## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round12：transport unknown 0 题；proof pass 0 题；持久 CriterionEvidence 0 题。
- Round13：transport unknown 0 题；proof pass 0 题；持久 CriterionEvidence 0 题。
- Round14：transport unknown 0 题；proof pass 5 题；持久 CriterionEvidence 5 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
