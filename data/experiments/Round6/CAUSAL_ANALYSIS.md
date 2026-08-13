# Round6 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：6/90（6.67%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 6
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 5/30 | 0/30 | 0/30 | 0 | 5 |
| medium | 0/30 | 0/30 | 0/30 | 0 | 0 |
| hard | 1/30 | 0/30 | 0/30 | 0 | 1 |

## 固定诊断指标

- 模型请求：657
- 本地输入 / 输出 token：1318953 / 229225
- 平均模型决策时延：10225.782472613459 ms
- 可配对产物 byte-5gram 平均相似度：0.811535490599
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 49
- run_blocked: 16
- external_correct_controller_not_completed: 6
- invalid_plan_schema: 6
- goal proposal has 6 criteria; maximum is 5: 3
- goal proposal has 8 criteria; maximum is 5: 2
- goal proposal has 7 criteria; maximum is 5: 2
- g1i_function_envelope_rejected: 1
- action type changed after selection: expected read_json: 1
- tasks bind unknown goal criteria: ["{'criterion_id': 'GC1', 'description': 'Checkpoint file checkpoints/step01.json exists and contains step number 1 and the constraints object.'}", "{'criterion_id': 'GC2', 'description': 'Checkpoint file checkpoints/step15.json exists and contains step number 15 and the constraints object.'}", "{'criterion_id': 'GC3', 'description': 'Final configuration file final/config.json exists and preserves every early constraint exactly and adds generated_by=RWKV-LH.'}", "{'criterion_id': 'GC4', 'description': 'All checkpoint files and final configuration file have been verified to exist and contain the correct content.'}"]: 1
- truncated_or_incomplete_json: 1
- task T2 has unknown dependencies: ["{'task_id': 'T1', 'output_key': 'is_valid_json', 'expected_value': True}"]: 1
- unsupported action type: sort_files_by_relative_path: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：1 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B03, E2E-B04, E2E-B07, E2E-B26, E2E-B29, E2E-H04

## 本轮 observation gate 触发情况

- Prepared：53
- Cacheable / uncacheable：53 / 0
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 49 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 7 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 1 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

## Phase A / Phase B / proof 专项补充

- 20 题、53 个 assertion event：semantic pass 27、replan 26。
- Phase A 79 请求、52 contract-error event；Phase B 51 请求、46 contract-error event。
- 5 个 event 完成 binding，共 7 条 assertion，但 proof pass 0：6 条不是 direct dependency，1 条两侧同源。
- verified claim、CriterionEvidence 与 Agent completion 均为 0；详见
  `OPERATOR_ASSERTION_ANALYSIS.md` / `operator_assertion_analysis.json`。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
