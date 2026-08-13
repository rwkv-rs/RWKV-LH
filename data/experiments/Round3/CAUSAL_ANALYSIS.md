# Round3 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：4/90（4.44%）
- Strict E2E：2/90（2.22%）
- Agent completed：11/90
- False positive / false negative：9 / 2
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 3/30 | 2/30 | 4/30 | 2 | 1 |
| medium | 0/30 | 0/30 | 6/30 | 6 | 0 |
| hard | 1/30 | 0/30 | 1/30 | 1 | 1 |

## 固定诊断指标

- 模型请求：583
- 本地输入 / 输出 token：1210874 / 208495
- 平均模型决策时延：9852.044642857143 ms
- 可配对产物 byte-5gram 平均相似度：0.773053869396
- 最终回答与 Codex 摘要平均相似度：0.032594290752（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 46
- agent_completed_external_failed: 9
- invalid_plan_schema: 7
- g1i_function_envelope_rejected: 5
- run_blocked: 4
- goal proposal has 6 criteria; maximum is 5: 3
- passed: 2
- goal proposal has 7 criteria; maximum is 5: 2
- external_correct_controller_not_completed: 2
- goal proposal has 8 criteria; maximum is 5: 2
- replan replacement task is missing: 2
- goal proposal has 9 criteria; maximum is 5: 2
- plan_tasks_array_missing: 2
- replacement_depends_on_failed_task: 1
- invalid_failure_analysis_decision: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：2 题。
- 完整 G1i/OpenAI function 外壳被拒绝：5 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B01, E2E-B06
- False positive case：E2E-B17, E2E-B25, E2E-H14, E2E-M07, E2E-M15, E2E-M21, E2E-M23, E2E-M25, E2E-M28
- False negative case：E2E-B26, E2E-H04

## 本轮 observation gate 触发情况

- Prepared：42
- Cacheable / uncacheable：42 / 0
- 首次有效 RWKV 失败记录：8
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 46 题；initial plan rejected before execution for missing direct claims。
- criterion_evidence_boundary: 9 题；agent completed while external acceptance failed。
- goal_criterion_capacity: 9 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 7 题；complete task/function objects remained under known wire envelopes。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
