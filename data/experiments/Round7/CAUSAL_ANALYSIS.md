# Round7 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：12/90（13.33%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 12
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 7/30 | 0/30 | 0/30 | 0 | 7 |
| medium | 2/30 | 0/30 | 0/30 | 0 | 2 |
| hard | 3/30 | 0/30 | 0/30 | 0 | 3 |

## 固定诊断指标

- 模型请求：1148
- 本地输入 / 输出 token：2371055 / 278774
- 平均模型决策时延：8875.89884649512 ms
- 可配对产物 byte-5gram 平均相似度：0.724004499854
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- run_blocked: 28
- plan_missing_direct_criterion_claims: 24
- external_correct_controller_not_completed: 12
- invalid_plan_schema: 6
- g1i_function_envelope_rejected: 6
- goal proposal has 6 criteria; maximum is 5: 3
- invalid_failure_analysis_decision: 2
- goal proposal has 7 criteria; maximum is 5: 2
- goal proposal has 8 criteria; maximum is 5: 2
- action read_file argument path must be workspace-relative: 1
- supplemental tasks repeat existing local ids: ['verify_normalized_name_txt', 'write_normalized_name_txt']: 1
- truncated_or_incomplete_json: 1
- G1i tool call requires a non-empty name: 1
- goal proposal has 9 criteria; maximum is 5: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：6 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B04, E2E-B05, E2E-B06, E2E-B13, E2E-B15, E2E-B21, E2E-B26, E2E-H04, E2E-H09, E2E-LH02, E2E-M12, E2E-M21

## 本轮 observation gate 触发情况

- Prepared：108
- Cacheable / uncacheable：101 / 7
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 24 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 8 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 6 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。

## Goal obligation 专项补充

- 76/90 形成 obligation ledger：36 个无缺口，40 个有缺口。
- 40 个非空 ledger 触发 69 次 supplemental 请求；15 个扩图接受、25 个最终阻断。
- 15 个 accepted case 新增 44 个 task，执行 94 个 action，只有 3 个 External pass，完成仍为 0。
- 新增 task 中 15 个标题、19 个描述与 base task 完全相同，说明主要副作用是重复工作和请求放大。
- 仅 obligation lane 的返回请求输入为 252,486 local tokens；全轮请求从 Round6 的 657 增至 1148。
- criterion binding 另有 53 次错误来自把输入合同元数据复制为输出字段；下一轮若处理此项，只能改变协议呈现，
  不能在 parser 删除字段或替 RWKV 选择 operator/evidence。

完整统计见 `GOAL_OBLIGATION_ANALYSIS.md` 与 `goal_obligation_analysis.json`。
