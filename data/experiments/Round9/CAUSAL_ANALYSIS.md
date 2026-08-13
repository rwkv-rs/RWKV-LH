# Round9 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：15/90（16.67%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 15
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 10/30 | 0/30 | 0/30 | 0 | 10 |
| medium | 2/30 | 0/30 | 0/30 | 0 | 2 |
| hard | 3/30 | 0/30 | 0/30 | 0 | 3 |

## 固定诊断指标

- 模型请求：1101
- 本地输入 / 输出 token：2443147 / 312224
- 平均模型决策时延：12168.26286764706 ms
- 可配对产物 byte-5gram 平均相似度：0.802181627814
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 32
- run_blocked: 26
- external_correct_controller_not_completed: 15
- g1i_function_envelope_rejected: 4
- invalid_plan_schema: 4
- goal proposal has 6 criteria; maximum is 5: 2
- goal proposal has 8 criteria; maximum is 5: 2
- truncated_or_incomplete_json: 1
- obligation plan top-level fields must be exactly ['schema_version', 'supplemental_tasks']: 1
- invalid_failure_analysis_decision: 1
- goal proposal has 9 criteria; maximum is 5: 1
- plan_tasks_array_missing: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：1 题。
- 完整 G1i/OpenAI function 外壳被拒绝：4 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B01, E2E-B02, E2E-B04, E2E-B06, E2E-B10, E2E-B15, E2E-B19, E2E-B26, E2E-B29, E2E-B30, E2E-H04, E2E-H09, E2E-LH02, E2E-M12, E2E-M21

## 本轮 observation gate 触发情况

- Prepared：88
- Cacheable / uncacheable：85 / 3
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 32 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 5 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 5 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。

## Single-claim G1i 专项补充

- 17 题、33 claim scope、66 response；0 normalized call、66 protocol error。
- 63/66 使用未登记的 `{bind_criterion_assertion: ...}` 顶层形态；其余 3 次也是非 canonical 变体。
- 0 proof claim、0 CriterionEvidence、0 completion；External 15 不能归因于触发后完全失败的 Phase B。

完整统计见 `G1I_BINDING_ANALYSIS.md` 与 `g1i_binding_analysis.json`。
