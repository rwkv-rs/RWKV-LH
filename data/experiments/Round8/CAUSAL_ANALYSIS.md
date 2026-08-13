# Round8 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：12/90（13.33%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 12
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 8/30 | 0/30 | 0/30 | 0 | 8 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 3/30 | 0/30 | 0/30 | 0 | 3 |

## 固定诊断指标

- 模型请求：1154
- 本地输入 / 输出 token：2438389 / 287500
- 平均模型决策时延：13444.058875219684 ms
- 可配对产物 byte-5gram 平均相似度：0.814509555642
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 27
- run_blocked: 27
- external_correct_controller_not_completed: 12
- g1i_function_envelope_rejected: 4
- invalid_plan_schema: 4
- goal proposal has 6 criteria; maximum is 5: 2
- goal proposal has 7 criteria; maximum is 5: 2
- truncated_or_incomplete_json: 2
- supplemental tasks repeat existing local ids: ['verify_combined']: 1
- invalid obligation plan schema: 1
- supplemental tasks repeat existing local ids: ['T2', 'T3', 'T4']: 1
- invalid_failure_analysis_decision: 1
- generation may have completed before the connection failed: ReadTimeout: HTTPConnectionPool(host='127.0.0.1', port=29613): Read timed out. (read timeout=300.0): 1
- goal proposal has 8 criteria; maximum is 5: 1
- action type changed after selection: expected read_json: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：4 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B05, E2E-B09, E2E-B13, E2E-B19, E2E-B20, E2E-B22, E2E-B26, E2E-B28, E2E-H04, E2E-H09, E2E-LH02, E2E-M21

## 本轮 observation gate 触发情况

- Prepared：106
- Cacheable / uncacheable：105 / 1
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 27 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 6 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 4 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。

## Binding contract 专项补充

- Phase B：19 题、45 event、88 response、75 contract error、13 accepted response。
- accepted response rate 从 Round7 的 8/79（10.13%）升至 13/88（14.77%）。
- 最常见 exact binding-field 错误从 53 降至 29；45 个审计行协议均不含四个 input-only metadata key。
- 13 个合法 event 形成 15 条 assertion，全部 proof rejected；0 VERIFIED、0 CriterionEvidence、0 completion。
- 主要 proof 根因是 9 条非 direct-dependency ref、5 条无效 JSON pointer/Goal quote。

完整统计见 `BINDING_CONTRACT_ANALYSIS.md` 与 `binding_contract_analysis.json`。
