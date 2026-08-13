# Round5 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：12/90（13.33%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 12
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 9/30 | 0/30 | 0/30 | 0 | 9 |
| medium | 2/30 | 0/30 | 0/30 | 0 | 2 |
| hard | 1/30 | 0/30 | 0/30 | 0 | 1 |

## 固定诊断指标

- 模型请求：705
- 本地输入 / 输出 token：1398818 / 244087
- 平均模型决策时延：12107.14055636896 ms
- 可配对产物 byte-5gram 平均相似度：0.790444580016
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 41
- run_blocked: 20
- external_correct_controller_not_completed: 12
- invalid_plan_schema: 4
- goal proposal has 7 criteria; maximum is 5: 3
- goal proposal has 6 criteria; maximum is 5: 2
- plan_tasks_array_missing: 2
- g1i_function_envelope_rejected: 1
- goal proposal has 8 criteria; maximum is 5: 1
- truncated_or_incomplete_json: 1
- action type changed after selection: expected read_json: 1
- goal proposal has 14 criteria; maximum is 5: 1
- goal proposal has 9 criteria; maximum is 5: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：1 题。
- 完整 G1i/OpenAI function 外壳被拒绝：1 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B02, E2E-B04, E2E-B13, E2E-B14, E2E-B17, E2E-B22, E2E-B26, E2E-B29, E2E-B30, E2E-H04, E2E-M18, E2E-M21

## 本轮 observation gate 触发情况

- Prepared：58
- Cacheable / uncacheable：58 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 41 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 8 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 2 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

## Round5 assertion 专项补充

- 28 题、58 个 criterion assertion attempt；顶层协议有效 40、无效 18。
- 55 条实际 assertion 中无损归一化 `0/55`、proof pass `0/58`、CriterionEvidence 0。
- 首个拒绝原因为 source 不相容字段 39、联合枚举/占位 source 12、自创字段 4。
- 58 个 attempt 全是 optional `criterion_cross_check`，显式 `model_cross_check` 复用路径触发 0 次，
  因此请求变化不能归因于单调用复用。
- 详情见 `LINEAR_ASSERTION_ANALYSIS.md` 与 `linear_assertion_analysis.json`。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
