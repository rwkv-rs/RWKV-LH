# Round1 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：7/90（7.78%）
- Strict E2E：5/90（5.56%）
- Agent completed：11/90
- False positive / false negative：6 / 2
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 5/30 | 3/30 | 4/30 | 1 | 2 |
| medium | 1/30 | 1/30 | 2/30 | 1 | 0 |
| hard | 1/30 | 1/30 | 5/30 | 4 | 0 |

## 固定诊断指标

- 模型请求：587
- 本地输入 / 输出 token：1236520 / 236804
- 平均模型决策时延：10703.476274165203 ms
- 可配对产物 byte-5gram 平均相似度：0.82064592198
- 最终回答与 Codex 摘要平均相似度：0.032017806036（仅诊断）

## 终止阶段与根因入口

- plan_tasks_array_missing: 30
- plan_missing_direct_criterion_claims: 22
- agent_completed_external_failed: 6
- passed: 5
- g1i_function_envelope_rejected: 4
- invalid_plan_schema: 4
- g1i_function_call_envelope_rejected: 3
- run_blocked: 3
- g1i_typed_function_envelope_rejected: 3
- replacement_depends_on_failed_task: 2
- goal proposal has 6 criteria; maximum is 5: 2
- goal proposal has 7 criteria; maximum is 5: 2
- external_correct_controller_not_completed: 2
- goal proposal has 9 criteria; maximum is 5: 1
- goal proposal has 8 criteria; maximum is 5: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：30 题。
- 完整 G1i/OpenAI function 外壳被拒绝：10 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B03, E2E-B28, E2E-B29, E2E-H04, E2E-M12
- False positive case：E2E-B25, E2E-H03, E2E-H12, E2E-H14, E2E-H17, E2E-M30
- False negative case：E2E-B22, E2E-B26

## 本轮 observation gate 触发情况

- Prepared：0
- Cacheable / uncacheable：0 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 40 题；complete task/function objects remained under known wire envelopes。
- goal_obligation_planning: 22 题；initial plan rejected before execution for missing direct claims。
- criterion_evidence_boundary: 6 题；agent completed while external acceptance failed。
- goal_criterion_capacity: 6 题；goal proposal exceeded the fixed five-criterion contract。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
