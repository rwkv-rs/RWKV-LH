# Round12_engine_control_20260812 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：2/90（2.22%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 2
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 2/30 | 0/30 | 0/30 | 0 | 2 |
| medium | 0/30 | 0/30 | 0/30 | 0 | 0 |
| hard | 0/30 | 0/30 | 0/30 | 0 | 0 |

## 固定诊断指标

- 模型请求：256
- 本地输入 / 输出 token：332708 / 99791
- 平均模型决策时延：9703.445945945947 ms
- 可配对产物 byte-5gram 平均相似度：0.767622220434
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- truncated_or_incomplete_json: 39
- goal proposal has no success_criteria array: 28
- invalid_plan_schema: 16
- external_correct_controller_not_completed: 2
- invalid expected witness source kind: 2
- invalid goal proposal schema: 1
- g1i_function_envelope_rejected: 1
- witness intent comparison must be exact_equals: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：1 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B06, E2E-B16

## 本轮 observation gate 触发情况

- Prepared：1
- Cacheable / uncacheable：1 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 1 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
