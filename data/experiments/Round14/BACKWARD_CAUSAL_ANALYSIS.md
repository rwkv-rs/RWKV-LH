# Round14 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round14 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round14 | 90 | 90 | 69d535b3b932e41a56612c2470cc31b3d2e16517d10543cd2d4be05759044296 |

## 总体终态与根因

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

| 环节 | Round14 |
|---|---|
| run_created | 81 |
| goal_parsed | 81 |
| plan_saved | 75 |
| attempt_started | 75 |
| action_returned | 75 |
| task_completed | 72 |
| goal_obligation_capsule_prepared | 52 |
| goal_obligation_replan_started | 52 |
| witness_source_catalog_prepared | 38 |
| witness_selection_started | 38 |
| witness_selection_compiled | 19 |
| witness_intent_precommit_started | 0 |
| witness_intents_precommitted | 0 |
| witness_catalog_prepared | 19 |
| criterion_assertions_evaluated | 16 |
| witness_binding_evaluated | 16 |
| criterion_evidence_persisted | 5 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round14 |
|---|---|
| action_argument_contract | 14 |
| action_choice_contract | 2 |
| action_or_validation_failed | 30 |
| action_recovery_budget_exhausted | 9 |
| obligation_gap_triggered_replan | 52 |
| obligation_replan_blocked | 11 |
| obligation_replan_contract | 52 |
| other_model_protocol_contract | 1 |
| planning_contract | 12 |
| post_action_source_catalog_reached | 38 |
| post_action_witness_selection_compiled | 19 |
| post_action_witness_selection_required | 38 |
| proof_feedback_triggered_local_revision | 12 |
| proof_passed | 5 |
| proof_rejected_other | 12 |
| recovery_analysis_contract | 2 |
| unhandled_priority_type | 6 |
| witness_catalog_reached | 19 |
| witness_handle_binding_contract | 7 |
| witness_selection_contract | 38 |

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

## 从后向前的关键链

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

## 正式运行验证结论

本次 90 题冻结运行已完整结束。transport outcome unknown 涉及 0 题；proof 在 5 题中至少一次通过，最终持久状态在 5 题中保存了 CriterionEvidence。该结论只验证冻结的 Round14 实现，不验证运行结束后提出或实现的任何修改。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
