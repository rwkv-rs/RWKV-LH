# Round51_full90 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：22/90（24.44%）
- Strict E2E：17/90（18.89%）
- Agent completed：39/90
- False positive / false negative：22 / 5
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 20/30 | 15/30 | 18/30 | 3 | 5 |
| medium | 1/30 | 1/30 | 13/30 | 12 | 0 |
| hard | 1/30 | 1/30 | 8/30 | 7 | 0 |

## 固定诊断指标

- 模型请求：1930
- 本地输入 / 输出 token：2996119 / 223346
- 平均模型决策时延：5181.160146061555 ms
- 可配对产物 byte-5gram 平均相似度：0.850794180403
- 最终回答与 Codex 摘要平均相似度：0.109339968277（仅诊断）

## 终止阶段与根因入口

- agent_completed_external_failed: 22
- g1i_function_envelope_rejected: 19
- passed: 17
- run_blocked: 12
- external_correct_controller_not_completed: 5
- canonical task batch requires exactly schema_version and tasks: 5
- unsupported action type: read_text: 4
- truncated_or_incomplete_json: 1
- unsupported action type: reselect_action: 1
- RWKV tool-name selection arguments must be exactly empty: 1
- action read_file argument path must be workspace-relative: 1
- action read_json argument path must be workspace-relative: 1
- unsupported action type: read_dir: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：19 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B02, E2E-B03, E2E-B08, E2E-B11, E2E-B12, E2E-B13, E2E-B15, E2E-B18, E2E-B19, E2E-B21, E2E-B23, E2E-B25, E2E-B26, E2E-B28, E2E-B29, E2E-H04, E2E-M01
- False positive case：E2E-B04, E2E-B22, E2E-B24, E2E-H06, E2E-H08, E2E-H11, E2E-H12, E2E-H17, E2E-LH01, E2E-LH10, E2E-M04, E2E-M06, E2E-M07, E2E-M08, E2E-M11, E2E-M14, E2E-M15, E2E-M16, E2E-M22, E2E-M23, E2E-M26, E2E-M27
- False negative case：E2E-B01, E2E-B05, E2E-B06, E2E-B07, E2E-B17

## 本轮 observation gate 触发情况

- Prepared：371
- Cacheable / uncacheable：349 / 22
- 首次有效 RWKV 失败记录：15
- 实际抑制：3
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- criterion_evidence_boundary: 22 题；agent completed while external acceptance failed。
- transparent_protocol_envelope_normalization: 19 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
