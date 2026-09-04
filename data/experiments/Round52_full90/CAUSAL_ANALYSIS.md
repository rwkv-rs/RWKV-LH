# Round52_full90 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：3/90（3.33%）
- Strict E2E：3/90（3.33%）
- Agent completed：17/90
- False positive / false negative：14 / 0
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 2/30 | 2/30 | 7/30 | 5 | 0 |
| medium | 0/30 | 0/30 | 3/30 | 3 | 0 |
| hard | 1/30 | 1/30 | 7/30 | 6 | 0 |

## 固定诊断指标

- 模型请求：892
- 本地输入 / 输出 token：1574691 / 201307
- 平均模型决策时延：7851.005720823799 ms
- 可配对产物 byte-5gram 平均相似度：0.754448200314
- 最终回答与 Codex 摘要平均相似度：0.048262692651（仅诊断）

## 终止阶段与根因入口

- agent_completed_external_failed: 14
- canonical task batch requires exactly schema_version and tasks: 5
- g1i_function_envelope_rejected: 4
- run_blocked: 4
- passed: 3
- initial frontier tasks must all use empty dependencies: ['update_config', 'verify_config']: 2
- action read_file has unknown arguments: ['end_char']: 2
- causal frontier exceeds 8 immediately-ready entry tasks: 2
- action read_file argument path must be workspace-relative: 2
- action read_json argument path must be workspace-relative: 1
- initial frontier tasks must all use empty dependencies: ['remove_deprecated', 'verify_absent', 'verify_order_and_text']: 1
- initial frontier tasks must all use empty dependencies: ['write_endpoint']: 1
- initial frontier tasks must all use empty dependencies: ['compute-sha256', 'verify-digest', 'write-manifest']: 1
- initial frontier tasks must all use empty dependencies: ['calculate_stats', 'check_stats', 'verify_stats', 'write_stats']: 1
- initial frontier tasks must all use empty dependencies: ['run_tests', 'write_slug']: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：4 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B01, E2E-B27, E2E-H04
- False positive case：E2E-B04, E2E-B06, E2E-B11, E2E-B17, E2E-B29, E2E-H01, E2E-H03, E2E-H09, E2E-H12, E2E-H14, E2E-LH09, E2E-M15, E2E-M21, E2E-M23
- False negative case：

## 本轮 observation gate 触发情况

- Prepared：154
- Cacheable / uncacheable：146 / 8
- 首次有效 RWKV 失败记录：14
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- criterion_evidence_boundary: 14 题；agent completed while external acceptance failed。
- transparent_protocol_envelope_normalization: 4 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
