# Round1--Round11 反向因果与错误放大分析

## 结论

Round11 确实解除了同步初始 coverage 硬门：结构合法的基础计划能先执行，External 从 15 升到 18。但 Completed/Strict 仍为 0/0，请求从 983 增到 2175。错误没有消失，而是从初始计划门迁到证据所有权、proof 绑定和义务扩图的后半程。

分析覆盖 90 题×11 轮共 990 个完成审计记录。反向路径为：外部结果 → 完成门 → evidence/proof → 绑定 → 局部验证 → action → plan → Goal。`primary_stage` 只标记审计能证明的最早偏离。

## 十一轮固定结果

| 轮次 | External | Strict | Completed | FP | FN | 请求 | Prompt tokens |
|---|---:|---:|---:|---:|---:|---:|---:|
| R1 | 7/90 | 5/90 | 11/90 | 6 | 2 | 587 | 1236520 |
| R2 | 8/90 | 7/90 | 19/90 | 12 | 1 | 809 | 1732080 |
| R3 | 4/90 | 2/90 | 11/90 | 9 | 2 | 583 | 1210874 |
| R4 | 7/90 | 0/90 | 0/90 | 0 | 7 | 802 | 1738104 |
| R5 | 12/90 | 0/90 | 0/90 | 0 | 12 | 705 | 1398818 |
| R6 | 6/90 | 0/90 | 0/90 | 0 | 6 | 657 | 1318953 |
| R7 | 12/90 | 0/90 | 0/90 | 0 | 12 | 1148 | 2371055 |
| R8 | 12/90 | 0/90 | 0/90 | 0 | 12 | 1154 | 2438389 |
| R9 | 15/90 | 0/90 | 0/90 | 0 | 15 | 1101 | 2443147 |
| R10 | 15/90 | 0/90 | 0/90 | 0 | 15 | 983 | 2092687 |
| R11 | 18/90 | 0/90 | 0/90 | 0 | 18 | 2175 | 5460587 |

## 后向阶段与放大量

- 990 个题轮结果：`{"blocked_external_wrong": 847, "controller_false_negative": 102, "unsafe_completion": 27, "strict_pass": 14}`。
- 11 轮 External 全错：59 题。
- External 间歇正确：31 题。
- 曾 Strict 通过但 R11 回退：10 题。

| 最早可证实阶段 | 题轮数 | 后续结果 | 平均请求 | 偏离后请求 | 偏离后完成任务 |
|---|---:|---|---:|---:|---:|
| `plan_coverage_gate` | 359 | `{"blocked_external_wrong": 359}` | 3.429 | 2.345 | 0.0 |
| `action_arguments_or_semantics` | 189 | `{"blocked_external_wrong": 168, "unsafe_completion": 21}` | 23.169 | 14.847 | 4.646 |
| `action_coverage_omission` | 94 | `{"blocked_external_wrong": 93, "unsafe_completion": 1}` | 14.574 | 12.234 | 2.553 |
| `plan_schema_protocol_gate` | 93 | `{"blocked_external_wrong": 93}` | 3.032 | 1.989 | 0.0 |
| `goal_cardinality_gate` | 77 | `{"blocked_external_wrong": 77}` | 2.0 | 0.0 | 0.0 |
| `proof_semantics_gate` | 61 | `{"controller_false_negative": 61}` | 15.426 | 1.836 | 0.492 |
| `external_mismatch_unlocalized` | 47 | `{"blocked_external_wrong": 44, "unsafe_completion": 3}` | 20.298 | 18.021 | 5.638 |
| `binding_protocol_gate` | 16 | `{"controller_false_negative": 16}` | 26.625 | 11.875 | 3.688 |
| `none` | 14 | `{"strict_pass": 14}` | 13.5 | 0.0 | 0.0 |
| `evidence_coverage_gate` | 12 | `{"controller_false_negative": 12}` | 18.583 | 14.333 | 4.583 |
| `binding_or_claim_gate` | 9 | `{"controller_false_negative": 9}` | 25.444 | 9.222 | 2.556 |
| `plan_coverage_omission` | 7 | `{"blocked_external_wrong": 5, "unsafe_completion": 2}` | 31.714 | 29.286 | 8.857 |
| `obligation_protocol_gate` | 7 | `{"blocked_external_wrong": 7}` | 4.143 | 3.143 | 0.0 |
| `completion_gate` | 4 | `{"controller_false_negative": 4}` | 18.25 | 0.0 | 0.0 |
| `plan_protocol_gate` | 1 | `{"blocked_external_wrong": 1}` | 2.0 | 1.0 | 0.0 |

## 11 轮全错题

- basic: 6 题；`E2E-B11, E2E-B12, E2E-B18, E2E-B23, E2E-B24, E2E-B27`。
  11 轮最早阶段：`{"plan_coverage_gate": 27, "action_arguments_or_semantics": 13, "goal_cardinality_gate": 11, "action_coverage_omission": 11, "plan_schema_protocol_gate": 3, "obligation_protocol_gate": 1}`。
- medium: 26 题；`E2E-M02, E2E-M03, E2E-M04, E2E-M05, E2E-M06, E2E-M07, E2E-M08, E2E-M09, E2E-M10, E2E-M11, E2E-M13, E2E-M14, E2E-M15, E2E-M16, E2E-M17, E2E-M19, E2E-M20, E2E-M22, E2E-M23, E2E-M24, E2E-M25, E2E-M26, E2E-M27, E2E-M28, E2E-M29, E2E-M30`。
  11 轮最早阶段：`{"action_arguments_or_semantics": 100, "plan_coverage_gate": 88, "goal_cardinality_gate": 32, "action_coverage_omission": 25, "external_mismatch_unlocalized": 20, "plan_schema_protocol_gate": 17, "plan_coverage_omission": 3, "obligation_protocol_gate": 1}`。
- hard: 27 题；`E2E-H01, E2E-H02, E2E-H03, E2E-H05, E2E-H06, E2E-H07, E2E-H08, E2E-H10, E2E-H11, E2E-H12, E2E-H13, E2E-H14, E2E-H15, E2E-H16, E2E-H17, E2E-H18, E2E-LH01, E2E-LH03, E2E-LH04, E2E-LH05, E2E-LH06, E2E-LH07, E2E-LH08, E2E-LH09, E2E-LH10, E2E-LH11, E2E-LH12`。
  11 轮最早阶段：`{"plan_coverage_gate": 119, "plan_schema_protocol_gate": 59, "action_coverage_omission": 38, "action_arguments_or_semantics": 31, "goal_cardinality_gate": 29, "external_mismatch_unlocalized": 14, "plan_coverage_omission": 3, "obligation_protocol_gate": 3, "plan_protocol_gate": 1}`。

## Round11 对下一步的约束

1. 解除同步 coverage 门是对的，但不能用事后扩图代替 evidence lifecycle。
2. 下一单变量应前置 RWKV witness intent：RWKV 决定 criterion、producer/consumer、actual/expected handle 和操作符；Controller 只检查引用所有权和类型。
3. 所有原始观察都可以生成 opaque handle，不能根据隐藏验收或相似度筛选。
4. proof 失败应返回机器可读错误给同一 RWKV 做局部重绑，不应立即追加整批语义重复任务。
5. 晋级必须同时看 FP=0、External、Completed、Strict 和请求成本；只有解析率或执行步数增加不算改善。

完整的 990 条逐题记录、阶段转移、放大量和来源哈希见 `cross_round_backward_causality.json`。
