# Round12 新推理引擎对照：从终态向前的因果分析

## 分析边界

这是一份完整 90 题、非架构计分的推理引擎对照分析。它只使用运行生命周期、模型协议、动作、Goal obligation、witness、proof 与持久状态事件；没有读取标准答案、外部验收结果或 verifier 观察。它不改变 Round12 架构分数，也不参与模型决策。

显式排除字段：`passed`, `external_passed`, `external_checks`, `user_request`, `final_output`, `runner_observations`, `verifier_failure`, `reference answer / standard answer (not present in this analyzer)`。

## 数据源

| 运行 | results 行 | audit 行 | results SHA-256 |
|---|---|---|---|
| Round12_engine_control_20260812 | 90 | 90 | 71a504911be278064d7a68afa866300acc07284ed94fc834b3d6ba445f1643d1 |

## 总体终态与根因

### Round12_engine_control_20260812

状态：`{"blocked": 29, "not_created": 61}`。

| 终态根因 | 题数 |
|---|---|
| goal_parse_contract | 61 |
| planning_contract | 20 |
| witness_intent_contract | 5 |
| action_choice_contract | 2 |
| action_argument_contract | 2 |

## 环节漏斗（到达该环节的题数）

| 环节 | Round12_engine_control_20260812 |
|---|---|
| run_created | 29 |
| goal_parsed | 29 |
| plan_saved | 9 |
| attempt_started | 7 |
| action_returned | 7 |
| task_completed | 7 |
| goal_obligation_capsule_prepared | 0 |
| goal_obligation_replan_started | 0 |
| witness_intent_precommit_started | 5 |
| witness_intents_precommitted | 1 |
| witness_catalog_prepared | 1 |
| criterion_assertions_evaluated | 0 |
| witness_binding_evaluated | 0 |
| criterion_evidence_committed | 0 |
| run_completed | 0 |

## 终态之前已经出现的机制（可重叠）

| 诊断机制（题数，可重叠） | Round12_engine_control_20260812 |
|---|---|
| action_argument_contract | 3 |
| action_choice_contract | 2 |
| intent_actual_expected_same_kind_without_goal_literal | 1 |
| planning_contract | 21 |
| witness_catalog_reached | 1 |
| witness_intent_contract | 5 |
| witness_intent_required | 5 |
| witness_source_selection_contract | 1 |

## 请求与错误放大

### Round12_engine_control_20260812

聚合报告计数：`{"attempt_count": 19, "model_requests": 256, "replan_count": 0, "task_count": 52}`。

模型请求类型：`{"task_decomposition": 48, "tool_action": 27, "tool_choice": 30, "witness_intent_precommit": 12, "witness_validation": 2}`。

| 请求环节 | 次数 | 错误 |
|---|---|---|
| task_decomposition | 35 | invalid plan schema |
| witness_intent_precommit | 6 | invalid expected witness source kind |
| task_decomposition | 4 | ModelProtocolError: model output does not contain a complete JSON object |
| tool_choice | 2 | ModelProtocolError: model output does not contain a complete JSON object |
| witness_intent_precommit | 2 | witness-intent top-level fields must be exactly ['schema_version', 'witness_intents'] |
| witness_validation | 2 | pass must select sources for every intent exactly once |
| witness_intent_precommit | 2 | witness intent comparison must be exact_equals |
| tool_choice | 1 | unsupported action type: required |
| tool_choice | 1 | action choice did not select a concrete Harness action |
| tool_action | 1 | action read_file argument path must be workspace-relative |
| tool_action | 1 | ValueError: G1i tool call has unknown fields: ['id', 'timestamp', 'type', 'user_id'] |
| witness_intent_precommit | 1 | non-goal expected witness must use empty expected_goal_literal |

## 从后向前的关键链

### Round12_engine_control_20260812

| 最早可归因环节 | 题数 | 此前已完成任务 | 之后模型请求 | 之后 replan | 样例 |
|---|---|---|---|---|---|
| goal_parse_contract | 61 | 0 | 0 | 0 | E2E-B04, E2E-B07, E2E-B09, E2E-B10, E2E-B11, E2E-B12 |
| planning_contract | 20 | 0 | 18 | 0 | E2E-B02, E2E-B03, E2E-B05, E2E-B17, E2E-B29, E2E-B30 |
| witness_intent_contract | 5 | 13 | 11 | 0 | E2E-B06, E2E-B16, E2E-B27, E2E-H18, E2E-M17 |
| action_argument_contract | 2 | 3 | 0 | 0 | E2E-H08, E2E-LH06 |
| action_choice_contract | 2 | 2 | 2 | 0 | E2E-B01, E2E-B08 |

## 推理引擎对照结论边界

本次 90 题使用冻结 Round12 核心，但运行于更新后的推理引擎。该分析可定位新引擎运行的最早生命周期断点与后续放大，不能把差异归因为 Agent 架构提升，也不能替代单独的并发/解码诊断。

完整逐题前驱、终端触发、事件链尾部、放大量和状态投影见配套 JSON。
