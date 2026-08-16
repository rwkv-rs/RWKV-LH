# Round50_full90 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：11/90（12.22%）
- Strict E2E：6/90（6.67%）
- Agent completed：14/90
- False positive / false negative：8 / 5
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 9/30 | 5/30 | 5/30 | 0 | 4 |
| medium | 2/30 | 1/30 | 7/30 | 6 | 1 |
| hard | 0/30 | 0/30 | 2/30 | 2 | 0 |

## 固定诊断指标

- 模型请求：1241
- 本地输入 / 输出 token：1677003 / 153590
- 平均模型决策时延：5327.683105022831 ms
- 可配对产物 byte-5gram 平均相似度：0.835540928862
- 最终回答与 Codex 摘要平均相似度：0.041107591148（仅诊断）

## 终止阶段与根因入口

- g1i_function_envelope_rejected: 58
- agent_completed_external_failed: 8
- run_blocked: 7
- passed: 6
- external_correct_controller_not_completed: 5
- canonical task batch requires exactly schema_version and tasks: 1
- action read_json argument path must be workspace-relative: 1
- unsupported action type: read_test_output: 1
- unsupported action type: read_csv: 1
- unsupported task batch schema: 2025-06-04: 1
- unsupported action type: read_text: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：58 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B07, E2E-B08, E2E-B15, E2E-B19, E2E-B28, E2E-M07
- False positive case：E2E-H11, E2E-LH02, E2E-M04, E2E-M06, E2E-M08, E2E-M11, E2E-M21, E2E-M29
- False negative case：E2E-B01, E2E-B17, E2E-B18, E2E-B26, E2E-M03

## 本轮 observation gate 触发情况

- Prepared：166
- Cacheable / uncacheable：158 / 8
- 首次有效 RWKV 失败记录：14
- 实际抑制：2
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 58 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 8 题；agent completed while external acceptance failed。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
