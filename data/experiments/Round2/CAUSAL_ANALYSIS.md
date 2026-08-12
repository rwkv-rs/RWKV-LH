# Round2 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：8/90（8.89%）
- Strict E2E：7/90（7.78%）
- Agent completed：19/90
- False positive / false negative：12 / 1
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 6/30 | 5/30 | 6/30 | 1 | 1 |
| medium | 1/30 | 1/30 | 9/30 | 8 | 0 |
| hard | 1/30 | 1/30 | 4/30 | 3 | 0 |

## 固定诊断指标

- 模型请求：809
- 本地输入 / 输出 token：1732080 / 234621
- 平均模型决策时延：8497.821656050955 ms
- 可配对产物 byte-5gram 平均相似度：0.748657038267
- 最终回答与 Codex 摘要平均相似度：0.057318216783（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 43
- agent_completed_external_failed: 12
- passed: 7
- goal proposal has 6 criteria; maximum is 5: 6
- run_blocked: 6
- g1i_function_envelope_rejected: 4
- invalid_plan_schema: 2
- task verify_project_field has unknown dependencies: ['read_report_json']: 1
- G1i tool call requires a non-empty name: 1
- tasks bind unknown goal criteria: ['GC10', 'GC11', 'GC12', 'GC13', 'GC14', 'GC15', 'GC5', 'GC6', 'GC7', 'GC8', 'GC9']: 1
- replan replacement task is missing: 1
- goal proposal has 8 criteria; maximum is 5: 1
- external_correct_controller_not_completed: 1
- goal proposal has 7 criteria; maximum is 5: 1
- action choice did not select a concrete Harness action: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：0 题。
- 完整 G1i/OpenAI function 外壳被拒绝：4 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：E2E-B01, E2E-B03, E2E-B17, E2E-B19, E2E-B29, E2E-H04, E2E-M21
- False positive case：E2E-B25, E2E-H02, E2E-H09, E2E-H12, E2E-M01, E2E-M04, E2E-M07, E2E-M15, E2E-M16, E2E-M17, E2E-M22, E2E-M25
- False negative case：E2E-B14

## Round2 预注册单变量

采用 `transparent_protocol_envelope_normalization`：只把完整的 `task_graph.tasks`、`function_call`、`type=function + function` 和 `function + arguments` 外壳映射为现有规范对象，同时保留归一前后 payload。不得补任务、补 criterion、补参数或改最终回答。
criterion 缺失声明和 external false positive 属于独立问题，本轮不一起修改。
