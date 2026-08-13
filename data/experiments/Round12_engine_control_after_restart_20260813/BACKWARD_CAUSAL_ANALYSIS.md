# Round12 新推理引擎对照：从终态向前的因果分析

## 分析边界

这是一份完整 90 题、非架构计分的推理引擎对照分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round12 架构分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round12_engine_control_after_restart_20260813 | 90 | 90 | 344f7cbec46b87ba2820e4579fca2388ade890c9fbf5b6bbab14d297b8c7de51 |

## 总体终态与根因

### Round12_engine_control_after_restart_20260813

状态：`{"blocked": 75, "interrupted": 8, "not_created": 7}`。

| 终态根因 | 题数 |
|---|---|
| witness_intent_contract | 47 |
| action_argument_contract | 9 |
| action_recovery_budget_exhausted | 7 |
| goal_parse_contract | 7 |
| obligation_replan_contract | 6 |
| unhandled_priority_type | 5 |
| run_blocked_other | 3 |
| planning_contract | 3 |
| recovery_analysis_contract | 2 |
| action_choice_contract | 1 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round12_engine_control_after_restart_20260813 |
|---|---|
| run_created | 83 |
| goal_parsed | 83 |
| plan_saved | 80 |
| attempt_started | 77 |
| action_returned | 77 |
| task_completed | 73 |
| goal_obligation_capsule_prepared | 15 |
| goal_obligation_replan_started | 15 |
| witness_intent_precommit_started | 48 |
| witness_intents_precommitted | 4 |
| witness_catalog_prepared | 4 |
| criterion_assertions_evaluated | 2 |
| witness_binding_evaluated | 2 |
| criterion_evidence_committed | 0 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round12_engine_control_after_restart_20260813 |
|---|---|
| action_argument_contract | 11 |
| action_choice_contract | 3 |
| action_or_validation_failed | 17 |
| action_recovery_budget_exhausted | 7 |
| intent_actual_expected_same_kind_without_goal_literal | 3 |
| obligation_gap_triggered_replan | 15 |
| obligation_replan_blocked | 3 |
| obligation_replan_contract | 15 |
| planning_contract | 11 |
| proof_feedback_triggered_local_revision | 1 |
| proof_rejected_other | 2 |
| recovery_analysis_contract | 2 |
| unhandled_priority_type | 5 |
| witness_catalog_reached | 4 |
| witness_handle_binding_contract | 1 |
| witness_intent_contract | 48 |
| witness_intent_required | 48 |
| witness_intent_revision_contract | 1 |

## 请求与错误放大

### Round12_engine_control_after_restart_20260813

聚合报告计数：`{"attempt_count": 388, "model_requests": 1292, "replan_count": 0, "task_count": 595}`。

模型请求类型：`{"failure_analysis": 30, "goal_obligation_replan": 58, "task_decomposition": 94, "tool_action": 449, "tool_choice": 448, "witness_handle_binding": 5, "witness_intent_precommit": 99, "witness_intent_revision": 2, "witness_validation": 6}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| witness_intent_precommit | 67 | invalid expected witness source kind |
| goal_obligation_replan | 34 | obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks'] |
| task_decomposition | 14 | invalid plan schema |
| witness_intent_precommit | 9 | witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id'] |
| witness_intent_precommit | 7 | current action/workspace witness producer must be the active task |
| witness_intent_precommit | 6 | witness intent comparison must be exact_equals |
| tool_action | 4 | action type changed after selection: expected read_json |
| failure_analysis | 4 | failure analysis decision must be retry_same, reselect_action, or replan |
| tool_choice | 3 | unsupported action type: read_csv |
| witness_intent_precommit | 3 | non-goal expected witness must use empty expected_goal_literal |
| tool_action | 3 | ValueError: G1i tool call has unknown fields: ['type'] |
| witness_handle_binding | 2 | witness binding fields must be exactly ['actual_handle_id', 'criterion_id', 'expected_handle_id', 'intent_id'] |

## 从后向前的关键链

### Round12_engine_control_after_restart_20260813

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| witness_intent_contract | 47 | 132 | 55 | 0 | E2E-B01, E2E-B02, E2E-B03, E2E-B04, E2E-B05, E2E-B07 |
| action_argument_contract | 9 | 32 | 1 | 0 | E2E-B09, E2E-B24, E2E-H07, E2E-H13, E2E-H15, E2E-LH06 |
| action_recovery_budget_exhausted | 7 | 21 | 46 | 0 | E2E-B11, E2E-B21, E2E-B23, E2E-B27, E2E-H10, E2E-H16 |
| goal_parse_contract | 7 | 0 | 0 | 0 | E2E-B12, E2E-H03, E2E-H11, E2E-LH12, E2E-M03, E2E-M06 |
| obligation_replan_contract | 6 | 29 | 21 | 3 | E2E-B08, E2E-B14, E2E-B15, E2E-M14, E2E-M18, E2E-M27 |
| unhandled_priority_type | 5 | 31 | 84 | 4 | E2E-B06, E2E-B19, E2E-B28, E2E-H06, E2E-H09 |
| planning_contract | 3 | 0 | 3 | 0 | E2E-H02, E2E-LH05, E2E-LH11 |
| run_blocked_other | 3 | 58 | 0 | 0 | E2E-B20, E2E-H17, E2E-M08 |
| recovery_analysis_contract | 2 | 5 | 2 | 0 | E2E-LH03, E2E-M12 |
| action_choice_contract | 1 | 2 | 1 | 0 | E2E-M15 |

## 推理引擎对照结论边界

本次 90 题使用冻结 Round12 核心，但运行于更新后的推理引擎。该分析可定位新引擎运行的最早生命周期断点与后续放大，不能把差异归因为 Agent 架构提升，也不能替代单独的并发/解码诊断。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
