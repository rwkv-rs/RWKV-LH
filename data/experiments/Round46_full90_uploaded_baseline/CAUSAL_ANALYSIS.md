# Round46_full90_uploaded_baseline 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：32/90（35.56%）
- Strict E2E：31/90（34.44%）
- Agent completed：55/90
- False positive / false negative：24 / 1
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 24/30 | 24/30 | 25/30 | 1 | 0 |
| medium | 5/30 | 5/30 | 17/30 | 12 | 0 |
| hard | 3/30 | 2/30 | 13/30 | 11 | 1 |

## 固定诊断指标

- 模型请求：1622
- 本地输入 / 输出 token：3502798 / 274636
- 平均模型决策时延：7013.525760397269 ms
- 可配对产物 byte-5gram 平均相似度：0.861638909388
- 最终回答与 Codex 摘要平均相似度：0.135323218639（仅诊断）

## 终止阶段与根因入口

- passed: 31
- agent_completed_external_failed: 24
- run_blocked: 12
- g1i_function_envelope_rejected: 5
- canonical task batch requires exactly schema_version and tasks: 4
- action write_json has unknown arguments: ['create_parents', 'overwrite']: 3
- truncated_or_incomplete_json: 2
- action read_file argument path must be workspace-relative: 2
- generation may have completed before the connection failed: ConnectionError: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response')): 1
- minimal task has unknown fields: ['advances_criteria', 'effect_targets', 'member_key', 'operation_kind', 'output_refs', 'phase_key', 'satisfies_criteria', 'subject_key', 'task_id']: 1
- external_correct_controller_not_completed: 1
- action read_file has unknown arguments: ['end_char']: 1
- minimal task has unknown fields: ['advances_criteria', 'dependency_outcomes', 'effect_targets', 'member_key', 'operation_kind', 'outcome_type', 'output_refs', 'phase_key', 'satisfies_criteria', 'status', 'subject_key', 'task_id']: 1
- action read_json argument path must be workspace-relative: 1
- action read_file has unknown arguments: ['cwd', 'end_char', 'end_line', 'env', 'source', 'start_line', 'timeout']: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：5 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B01, E2E-B02, E2E-B03, E2E-B05, E2E-B06, E2E-B07, E2E-B08, E2E-B09, E2E-B10, E2E-B11, E2E-B12, E2E-B13, E2E-B14, E2E-B15, E2E-B16, E2E-B17, E2E-B18, E2E-B19, E2E-B20, E2E-B21, E2E-B24, E2E-B25, E2E-B26, E2E-B28, E2E-H04, E2E-LH04, E2E-M03, E2E-M05, E2E-M12, E2E-M19, E2E-M24
- False positive case：E2E-B29, E2E-H02, E2E-H03, E2E-H08, E2E-H11, E2E-H13, E2E-H15, E2E-H17, E2E-LH01, E2E-LH05, E2E-LH09, E2E-LH11, E2E-M01, E2E-M06, E2E-M07, E2E-M08, E2E-M11, E2E-M15, E2E-M16, E2E-M17, E2E-M18, E2E-M25, E2E-M26, E2E-M29
- False negative case：E2E-LH02

## 本轮 observation gate 触发情况

- Prepared：425
- Cacheable / uncacheable：414 / 11
- 首次有效 RWKV 失败记录：21
- 实际抑制：3
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## 下一轮候选证据（不自动选方案）

- criterion_evidence_boundary: 24 题；agent completed while external acceptance failed。
- transparent_protocol_envelope_normalization: 5 题；complete task/function objects remained under known wire envelopes。
- goal_criterion_capacity: 0 题；goal proposal exceeded the fixed five-criterion contract。
- goal_obligation_planning: 0 题；initial plan rejected before execution for missing direct claims。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
