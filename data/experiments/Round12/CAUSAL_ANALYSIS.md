# Round12 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：11/90（12.22%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 11
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 10/30 | 0/30 | 0/30 | 0 | 10 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 0/30 | 0/30 | 0/30 | 0 | 0 |

## 固定诊断指标

- 模型请求：1436
- 本地输入 / 输出 token：2925551 / 322219
- 平均模型决策时延：18225.858956276446 ms
- 可配对产物 byte-5gram 平均相似度：0.709348468893
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- invalid expected witness source kind: 19
- run_blocked: 12
- external_correct_controller_not_completed: 11
- g1i_function_envelope_rejected: 6
- invalid_plan_schema: 6
- witness-intent fields must be exactly ['actual_source_kind', 'comparison', 'criterion_id', 'expected_goal_literal', 'expected_source_kind', 'producer_task_id', 'subject_task_id']: 5
- obligation replan top-level fields must be exactly ['schema_version', 'reason', 'new_tasks']: 5
- invalid literal for int() with base 10: 'high': 4
- goal proposal has 7 criteria; maximum is 5: 3
- truncated_or_incomplete_json: 3
- invalid_failure_analysis_decision: 2
- witness intent comparison must be exact_equals: 2
- unsupported action type: read_csv: 1
- goal proposal has 6 criteria; maximum is 5: 1
- plan_tasks_array_missing: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：6 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B03, E2E-B04, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B14, E2E-B19, E2E-B20, E2E-B30, E2E-M18

## 本轮 observation gate 触发情况

- Prepared：10
- Cacheable / uncacheable：10 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_criterion_capacity: 7 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 6 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
