# Round53_full90 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：24/90（26.67%）
- Strict E2E：23/90（25.56%）
- Agent completed：43/90
- False positive / false negative：20 / 1
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 21/30 | 20/30 | 21/30 | 1 | 1 |
| medium | 2/30 | 2/30 | 15/30 | 13 | 0 |
| hard | 1/30 | 1/30 | 7/30 | 6 | 0 |

## 固定诊断指标

- 模型请求：2448
- 本地输入 / 输出 token：4168126 / 333817
- 平均模型决策时延：6257.695319148937 ms
- 可配对产物 byte-5gram 平均相似度：0.871413443491
- 最终回答与 Codex 摘要平均相似度：0.118250872002（仅诊断）

## 终止阶段与根因入口

- RWKV action reviewer rejected all three complete candidates: 30
- passed: 23
- agent_completed_external_failed: 20
- g1i_function_envelope_rejected: 5
- truncated_or_incomplete_json: 2
- action read_file has unknown arguments: ['end_char']: 2
- canonical task batch requires exactly schema_version and tasks: 1
- minimal task has unknown fields: ['effect_targets', 'member_key', 'operation_kind', 'satisfies_criteria']: 1
- action read_file argument path must be workspace-relative: 1
- run_blocked: 1
- action write_file argument path must be workspace-relative: 1
- external_correct_controller_not_completed: 1
- unsupported action type: write_directory: 1
- action write_json has unknown arguments: ['create_parents', 'overwrite']: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：5 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B01, E2E-B02, E2E-B03, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B10, E2E-B11, E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B17, E2E-B19, E2E-B20, E2E-B25, E2E-B28, E2E-LH02, E2E-M03, E2E-M07
- False positive case：E2E-B29, E2E-H02, E2E-H03, E2E-H08, E2E-H17, E2E-LH01, E2E-LH05, E2E-M01, E2E-M08, E2E-M13, E2E-M15, E2E-M17, E2E-M18, E2E-M19, E2E-M21, E2E-M23, E2E-M24, E2E-M26, E2E-M27, E2E-M29
- False negative case：E2E-B18

## 本轮 observation gate 触发情况

- Prepared：365
- Cacheable / uncacheable：361 / 4
- 首次有效 RWKV 失败记录：18
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- criterion_evidence_boundary: 20 题；agent completed while external acceptance failed。
- transparent_protocol_envelope_normalization: 5 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
