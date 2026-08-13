# Round20 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round20 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round20 | 90 | 90 | 79d903f2e5da5f244f7734db6bf76ec0ce1674b34346ea729b9d8ecda9af7184 |

## 总体终态与根因

### Round20

状态：`{"blocked": 76, "completed": 1, "interrupted": 8, "not_created": 5}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 27 |
| action_recovery_budget_exhausted | 16 |
| action_argument_contract | 15 |
| obligation_replan_contract | 10 |
| planning_contract | 7 |
| unhandled_priority_type | 6 |
| goal_parse_contract | 5 |
| witness_handle_binding_contract | 1 |
| run_interrupted_other | 1 |
| recovery_analysis_contract | 1 |
| action_choice_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round20 |
|---|---|
| run_created | 85 |
| goal_parsed | 85 |
| plan_saved | 78 |
| attempt_started | 77 |
| action_returned | 77 |
| task_completed | 74 |
| goal_obligation_capsule_prepared | 48 |
| goal_obligation_replan_started | 48 |
| witness_source_catalog_prepared | 41 |
| witness_selection_started | 41 |
| witness_selection_compiled | 28 |
| witness_intent_precommit_started | 0 |
| witness_intents_precommitted | 0 |
| witness_catalog_prepared | 28 |
| criterion_assertions_evaluated | 25 |
| witness_binding_evaluated | 25 |
| criterion_evidence_persisted | 6 |
| run_completed | 1 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round20 |
|---|---|
| action_argument_contract | 18 |
| action_choice_contract | 6 |
| action_or_validation_failed | 30 |
| action_recovery_budget_exhausted | 16 |
| obligation_gap_triggered_replan | 48 |
| obligation_replan_blocked | 27 |
| obligation_replan_contract | 14 |
| other_model_protocol_contract | 23 |
| planning_contract | 14 |
| post_action_source_catalog_reached | 41 |
| post_action_witness_selection_compiled | 28 |
| post_action_witness_selection_required | 41 |
| proof_feedback_triggered_local_revision | 23 |
| proof_passed | 6 |
| proof_rejected_other | 23 |
| proof_rejected_same_source_self_comparison | 1 |
| recovery_analysis_contract | 1 |
| rwkv_selected_same_source_for_both_sides | 1 |
| rwkv_selected_same_value_handle_for_both_sides | 1 |
| unhandled_priority_type | 6 |
| witness_catalog_reached | 28 |
| witness_handle_binding_contract | 15 |
| witness_selection_contract | 33 |

## 请求与错误放大

### Round20

聚合报告计数：`{"attempt_count": 894, "model_requests": 2960, "replan_count": 0, "task_count": 947}`。

模型请求类型：`{"failure_analysis": 59, "final_answer": 1, "goal_obligation_replan": 140, "task_decomposition": 99, "tool_action": 914, "tool_choice": 917, "verification_design": 3, "witness_expected_mode": 281, "witness_handle_binding": 155, "witness_selection": 291}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 132 | expected_source_handle_id is unknown or not expected-eligible |
| witness_expected_mode | 107 | witness mode requires exactly schema_version and decision |
| witness_selection | 79 | goal_quote must be an exact non-empty Goal substring |
| goal_obligation_replan | 22 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_handle_binding | 21 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |
| witness_selection | 20 | catalog_source witness binding requires exactly its committed mode fields and optional note |
| task_decomposition | 19 | invalid plan schema |
| witness_handle_binding | 6 | witness handle binding fields must be exactly ['schema_version', 'witness_bindings'] |
| tool_choice | 5 | unsupported action type: read_text |
| tool_action | 5 | ValueError: G1i tool call has unknown fields: ['type'] |
| tool_action | 4 | action type changed after selection: expected read_json |
| tool_action | 4 | ModelProtocolError: model output does not contain a complete JSON object |

## 从后向前的关键链

### Round20

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 27 | 162 | 1116 | 81 | E2E-B05, E2E-B07, E2E-B08, E2E-B12, E2E-B15, E2E-B16 |
| action_recovery_budget_exhausted | 16 | 48 | 125 | 0 | E2E-B04, E2E-B09, E2E-B11, E2E-B21, E2E-B23, E2E-B27 |
| action_argument_contract | 15 | 63 | 32 | 1 | E2E-B10, E2E-B22, E2E-B24, E2E-H08, E2E-H10, E2E-H13 |
| obligation_replan_contract | 10 | 160 | 10 | 0 | E2E-B03, E2E-B13, E2E-B14, E2E-B30, E2E-H06, E2E-LH02 |
| planning_contract | 7 | 0 | 7 | 0 | E2E-H02, E2E-H05, E2E-H14, E2E-LH05, E2E-LH08, E2E-LH11 |
| unhandled_priority_type | 6 | 25 | 76 | 7 | E2E-B01, E2E-B06, E2E-B26, E2E-H04, E2E-H12, E2E-M08 |
| goal_parse_contract | 5 | 0 | 0 | 0 | E2E-H11, E2E-LH03, E2E-LH12, E2E-M03, E2E-M06 |
| action_choice_contract | 1 | 2 | 1 | 0 | E2E-M30 |
| recovery_analysis_contract | 1 | 4 | 1 | 0 | E2E-H01 |
| run_interrupted_other | 1 | 6 | 0 | 0 | E2E-B17 |
| witness_handle_binding_contract | 1 | 3 | 28 | 3 | E2E-B02 |

## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round20：transport unknown 0 题；proof pass 6 题；持久 CriterionEvidence 6 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
