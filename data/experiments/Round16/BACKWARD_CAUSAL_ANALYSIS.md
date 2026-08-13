# Round16 正式运行：从终态向前的因果分析

## 分析边界

这是一份正式运行的生命周期因果分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round16 分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round16 | 90 | 90 | ac49ff3baf17938ae6aa747e61fc193c6bbff835265b1d990b73a5bde5d92c73 |

## 总体终态与根因

### Round16

状态：`{"blocked": 75, "interrupted": 7, "not_created": 8}`。

| 终态根因 | 题数 |
|---|---|
| obligation_replan_budget_exhausted | 38 |
| action_recovery_budget_exhausted | 13 |
| action_argument_contract | 11 |
| goal_parse_contract | 8 |
| planning_contract | 8 |
| obligation_replan_contract | 6 |
| unhandled_priority_type | 4 |
| recovery_analysis_contract | 2 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round16 |
|---|---|
| run_created | 82 |
| goal_parsed | 82 |
| plan_saved | 75 |
| attempt_started | 75 |
| action_returned | 75 |
| task_completed | 71 |
| goal_obligation_capsule_prepared | 52 |
| goal_obligation_replan_started | 52 |
| witness_source_catalog_prepared | 40 |
| witness_selection_started | 40 |
| witness_selection_compiled | 4 |
| witness_intent_precommit_started | 0 |
| witness_intents_precommitted | 0 |
| witness_catalog_prepared | 4 |
| criterion_assertions_evaluated | 3 |
| witness_binding_evaluated | 3 |
| criterion_evidence_persisted | 1 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round16 |
|---|---|
| action_argument_contract | 13 |
| action_choice_contract | 2 |
| action_or_validation_failed | 27 |
| action_recovery_budget_exhausted | 13 |
| obligation_gap_triggered_replan | 52 |
| obligation_replan_blocked | 38 |
| obligation_replan_contract | 9 |
| planning_contract | 13 |
| post_action_source_catalog_reached | 40 |
| post_action_witness_selection_compiled | 4 |
| post_action_witness_selection_required | 40 |
| proof_feedback_triggered_local_revision | 2 |
| proof_passed | 1 |
| proof_rejected_other | 2 |
| recovery_analysis_contract | 2 |
| unhandled_priority_type | 4 |
| witness_catalog_reached | 4 |
| witness_handle_binding_contract | 3 |
| witness_selection_contract | 39 |

## 请求与错误放大

### Round16

聚合报告计数：`{"attempt_count": 935, "model_requests": 3040, "replan_count": 0, "task_count": 967}`。

模型请求类型：`{"failure_analysis": 46, "goal_obligation_replan": 148, "task_decomposition": 95, "tool_action": 948, "tool_choice": 946, "verification_design": 5, "witness_handle_binding": 24, "witness_selection": 726}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_selection | 460 | expected witness kind must be catalog_source or goal_literal |
| witness_selection | 105 | goal_quote must be an exact non-empty Goal substring |
| witness_selection | 50 | witness selection item requires criterion_id, actual_source_handle_id, and expected; only optional note is allowed |
| witness_selection | 31 | catalog expected witness requires exactly kind and source_handle_id |
| witness_selection | 30 | witness selection requires schema_version, decision, and witness_selections; only optional reason is allowed |
| task_decomposition | 20 | invalid plan schema |
| witness_selection | 20 | pass must select one witness pair per claimed criterion |
| witness_selection | 13 | ModelProtocolError: model output does not contain a complete JSON object |
| goal_obligation_replan | 13 | obligation replan requires new_tasks; only optional schema_version and reason are allowed |
| witness_selection | 4 | expected_source_handle_id is unknown or not expected-eligible |
| tool_action | 4 | action type changed after selection: expected read_json |
| tool_action | 4 | ValueError: G1i tool call has unknown fields: ['type'] |

## 从后向前的关键链

### Round16

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| obligation_replan_budget_exhausted | 38 | 189 | 1461 | 114 | E2E-B01, E2E-B03, E2E-B04, E2E-B06, E2E-B07, E2E-B08 |
| action_recovery_budget_exhausted | 13 | 32 | 80 | 0 | E2E-B05, E2E-B11, E2E-B21, E2E-B23, E2E-B26, E2E-H01 |
| action_argument_contract | 11 | 62 | 0 | 0 | E2E-B10, E2E-B24, E2E-H07, E2E-H10, E2E-H16, E2E-H17 |
| goal_parse_contract | 8 | 0 | 0 | 0 | E2E-B12, E2E-H11, E2E-LH12, E2E-M03, E2E-M06, E2E-M18 |
| planning_contract | 8 | 0 | 50 | 0 | E2E-H02, E2E-H12, E2E-H13, E2E-H18, E2E-LH05, E2E-LH06 |
| obligation_replan_contract | 6 | 88 | 6 | 0 | E2E-H06, E2E-LH02, E2E-LH08, E2E-M11, E2E-M15, E2E-M28 |
| unhandled_priority_type | 4 | 21 | 53 | 5 | E2E-B02, E2E-B14, E2E-B20, E2E-LH03 |
| recovery_analysis_contract | 2 | 18 | 2 | 0 | E2E-B28, E2E-M23 |

## 正式运行验证结论

所有列出的 90 题冻结运行均已完整结束。逐轮的 transport unknown、proof pass 与持久 CriterionEvidence 如下；这些结论只验证各轮冻结实现，不验证运行结束后提出或实现的任何修改。

- Round16：transport unknown 0 题；proof pass 1 题；持久 CriterionEvidence 1 题。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
