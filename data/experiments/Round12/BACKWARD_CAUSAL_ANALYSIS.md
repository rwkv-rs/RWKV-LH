# Round12 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round12 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round12 | 90 | 90 | 85e2759678a27c57f61739d896c77513fc19e985dfb19fcbe9f04dcc899d1a30 |

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

## 环节漏斗（到达该环节的题数）

| 环节 | Round12 |
|---|---|
| run_created | 83 |
| goal_parsed | 83 |
| plan_saved | 77 |
| attempt_started | 76 |
| action_returned | 76 |
| task_completed | 74 |
| goal_obligation_capsule_prepared | 26 |
| goal_obligation_replan_started | 26 |
| witness_intent_precommit_started | 32 |
| witness_intents_precommitted | 6 |
| witness_catalog_prepared | 6 |
| criterion_assertions_evaluated | 3 |
| witness_binding_evaluated | 3 |
| criterion_evidence_committed | 0 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round12 |
|---|---|
| action_argument_contract | 13 |
| action_choice_contract | 5 |
| action_or_validation_failed | 22 |
| action_recovery_budget_exhausted | 10 |
| intent_actual_expected_same_kind_without_goal_literal | 3 |
| obligation_gap_triggered_replan | 26 |
| obligation_replan_blocked | 4 |
| obligation_replan_contract | 26 |
| planning_contract | 14 |
| proof_feedback_triggered_local_revision | 2 |
| proof_rejected_other | 3 |
| proof_rejected_same_source_self_comparison | 1 |
| recovery_analysis_contract | 2 |
| rwkv_selected_same_source_for_both_sides | 1 |
| rwkv_selected_same_value_handle_for_both_sides | 1 |
| unhandled_priority_type | 7 |
| witness_catalog_reached | 6 |
| witness_handle_binding_contract | 1 |
| witness_intent_contract | 32 |
| witness_intent_required | 32 |
| witness_intent_revision_contract | 1 |
| witness_source_selection_contract | 4 |

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

## 正式运行验证结论

本次 90 题冻结运行已完整结束。transport outcome unknown 为 0；witness intent 合约仍是最大终态断点；只有少数题到达 binding，且 proof 全部拒绝；obligation replan 在前序任务完成后继续放大请求。该结论只验证冻结的 Round12 实现，不验证运行结束后提出或实现的任何修改。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
