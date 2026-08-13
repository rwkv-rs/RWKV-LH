# Round12_engine_control_after_restart_20260813 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：12/90（13.33%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 12
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 10/30 | 0/30 | 0/30 | 0 | 10 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 1/30 | 0/30 | 0/30 | 0 | 1 |

## 固定诊断指标

- 模型请求：1292
- 本地输入 / 输出 token：2569874 / 291764
- 平均模型决策时延：7133.013343799058 ms
- 可配对产物 byte-5gram 平均相似度：0.724724165022
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- invalid expected witness source kind: 32
- external_correct_controller_not_completed: 12
- run_blocked: 9
- g1i_function_envelope_rejected: 6
- witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id']: 4
- witness intent comparison must be exact_equals: 3
- invalid_plan_schema: 3
- goal proposal has 8 criteria; maximum is 5: 3
- current action/workspace witness producer must be the active task: 2
- goal proposal has 6 criteria; maximum is 5: 2
- invalid_failure_analysis_decision: 2
- truncated_or_incomplete_json: 2
- obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks']: 2
- action type changed after selection: expected read_json: 1
- invalid literal for int() with base 10: 'high': 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：6 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B04, E2E-B06, E2E-B08, E2E-B10, E2E-B14, E2E-B15, E2E-B19, E2E-B20, E2E-B28, E2E-B30, E2E-H09, E2E-M21

## 本轮 observation gate 触发情况

- Prepared：4
- Cacheable / uncacheable：4 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_criterion_capacity: 7 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 6 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
