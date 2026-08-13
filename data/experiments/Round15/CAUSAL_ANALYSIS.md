# Round15 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：19/90（21.11%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 19
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 16/30 | 0/30 | 0/30 | 0 | 16 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 2/30 | 0/30 | 0/30 | 0 | 2 |

## 固定诊断指标

- 模型请求：3179
- 本地输入 / 输出 token：7981487 / 589516
- 平均模型决策时延：7155.600632911392 ms
- 可配对产物 byte-5gram 平均相似度：0.725293693205
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- run_blocked: 26
- external_correct_controller_not_completed: 19
- obligation replan requires new_tasks; only optional schema_version and reason are allowed: 11
- g1i_function_envelope_rejected: 9
- invalid literal for int() with base 10: 'high': 4
- invalid_plan_schema: 4
- goal proposal has 6 criteria; maximum is 5: 2
- invalid_failure_analysis_decision: 2
- truncated_or_incomplete_json: 2
- fixed prompt exceeds the request-specific context budget: 2
- goal proposal has 7 criteria; maximum is 5: 2
- goal proposal has 8 criteria; maximum is 5: 2
- action run_command argument cwd must be workspace-relative: 1
- task T2 has unknown dependencies: ["{'task_id': 'T1', 'condition': 'T1.result.is_valid_json == false'}"]: 1
- unsupported action type: read_text: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：1 题。
- 完整 G1i/OpenAI function 外壳被拒绝：9 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B01, E2E-B02, E2E-B03, E2E-B04, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B13, E2E-B15, E2E-B18, E2E-B19, E2E-B20, E2E-B26, E2E-B30, E2E-H04, E2E-LH10, E2E-M12

## 本轮 observation gate 触发情况

- Prepared：373
- Cacheable / uncacheable：347 / 26
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- transparent_protocol_envelope_normalization: 10 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 7 题；goal proposal exceeded the fixed five-criterion contract。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
