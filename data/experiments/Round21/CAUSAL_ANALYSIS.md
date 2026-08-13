# Round21 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：20/90（22.22%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 20
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 16/30 | 0/30 | 0/30 | 0 | 16 |
| medium | 2/30 | 0/30 | 0/30 | 0 | 2 |
| hard | 2/30 | 0/30 | 0/30 | 0 | 2 |

## 固定诊断指标

- 模型请求：2636
- 本地输入 / 输出 token：6461359 / 436940
- 平均模型决策时延：6544.62987012987 ms
- 可配对产物 byte-5gram 平均相似度：0.813047859732
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- run_blocked: 27
- external_correct_controller_not_completed: 20
- invalid_plan_schema: 10
- g1i_function_envelope_rejected: 7
- obligation replan requires new_tasks; only optional schema_version and reason are allowed: 7
- invalid literal for int() with base 10: 'high': 5
- goal proposal has 7 criteria; maximum is 5: 3
- goal proposal has 6 criteria; maximum is 5: 2
- goal proposal has 8 criteria; maximum is 5: 2
- fixed prompt exceeds the request-specific context budget: 2
- immutable goal and active task exceed the request-specific prompt budget: 1
- truncated_or_incomplete_json: 1
- goal proposal has 9 criteria; maximum is 5: 1
- plan_tasks_array_missing: 1
- invalid_failure_analysis_decision: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：1 题。
- 完整 G1i/OpenAI function 外壳被拒绝：7 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B01, E2E-B03, E2E-B04, E2E-B05, E2E-B07, E2E-B08, E2E-B13, E2E-B15, E2E-B16, E2E-B17, E2E-B19, E2E-B20, E2E-B22, E2E-B26, E2E-B28, E2E-B30, E2E-H04, E2E-LH02, E2E-M11, E2E-M12

## 本轮 observation gate 触发情况

- Prepared：265
- Cacheable / uncacheable：254 / 11
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_criterion_capacity: 8 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 8 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
