# Round12 中断样本：从终态向前的因果分析

## 分析边界

这是一份非计分、非正式实验分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。各中断目录彼此独立，未合并、未补跑、未用于形成 Round12 分数。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round13 | 90 | 90 | 7ddce9e175ea2e192f546c2856c7a8f7aa419099b2f200d9f1e23e30a33a37e7 |

## 总体终态与根因

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

## 环节漏斗（到达该环节的题数）

| 环节 | Round13 |
|---|---|
| run_created | 85 |
| goal_parsed | 85 |
| plan_saved | 81 |
| attempt_started | 80 |
| action_returned | 80 |
| task_completed | 73 |
| goal_obligation_capsule_prepared | 54 |
| goal_obligation_replan_started | 54 |
| witness_source_catalog_prepared | 34 |
| witness_selection_started | 34 |
| witness_selection_compiled | 1 |
| witness_intent_precommit_started | 0 |
| witness_intents_precommitted | 0 |
| witness_catalog_prepared | 1 |
| criterion_assertions_evaluated | 1 |
| witness_binding_evaluated | 1 |
| criterion_evidence_committed | 0 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round13 |
|---|---|
| action_argument_contract | 18 |
| action_choice_contract | 3 |
| action_or_validation_failed | 30 |
| action_recovery_budget_exhausted | 11 |
| obligation_gap_triggered_replan | 54 |
| obligation_replan_blocked | 10 |
| obligation_replan_contract | 54 |
| planning_contract | 6 |
| post_action_source_catalog_reached | 34 |
| post_action_witness_selection_compiled | 1 |
| post_action_witness_selection_required | 34 |
| proof_feedback_triggered_local_revision | 1 |
| proof_rejected_other | 1 |
| recovery_analysis_contract | 3 |
| unhandled_priority_type | 8 |
| witness_catalog_reached | 1 |
| witness_handle_binding_contract | 1 |
| witness_selection_contract | 33 |

## 请求与错误放大

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

## 从后向前的关键链

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

## 当前正式运行的验证方式

中断样本只用于预登记待正式运行验证的机制：① transport outcome unknown 是否归零；② witness intent 合约是否仍是主要断点；③到达 binding 的题目是否由 proof 给出可追溯判断；④ obligation replan 是否放大请求与恢复预算。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
