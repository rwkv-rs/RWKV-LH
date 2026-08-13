# Round16 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：24/90（26.67%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 24
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 19/30 | 0/30 | 0/30 | 0 | 19 |
| medium | 2/30 | 0/30 | 0/30 | 0 | 2 |
| hard | 3/30 | 0/30 | 0/30 | 0 | 3 |

## 固定诊断指标

- 模型请求：3040
- 本地输入 / 输出 token：7610429 / 640187
- 平均模型决策时延：7630.677483443708 ms
- 可配对产物 byte-5gram 平均相似度：0.777350166103
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- run_blocked: 31
- external_correct_controller_not_completed: 24
- g1i_function_envelope_rejected: 9
- invalid_plan_schema: 7
- obligation replan requires new_tasks; only optional schema_version and reason are allowed: 4
- goal proposal has 9 criteria; maximum is 5: 3
- goal proposal has 6 criteria; maximum is 5: 2
- goal proposal has 7 criteria; maximum is 5: 2
- invalid_failure_analysis_decision: 2
- immutable goal and active task exceed the request-specific prompt budget: 1
- G1i tool call requires a non-empty name: 1
- invalid literal for int() with base 10: 'high': 1
- goal proposal has 8 criteria; maximum is 5: 1
- truncated_or_incomplete_json: 1
- task requires id, title, and description: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：9 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B01, E2E-B02, E2E-B03, E2E-B04, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B19, E2E-B20, E2E-B22, E2E-B25, E2E-B26, E2E-B30, E2E-H04, E2E-H09, E2E-LH02, E2E-M01, E2E-M12

## 本轮 observation gate 触发情况

- Prepared：373
- Cacheable / uncacheable：356 / 17
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 9 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 8 题；goal proposal exceeded the fixed five-criterion contract。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
