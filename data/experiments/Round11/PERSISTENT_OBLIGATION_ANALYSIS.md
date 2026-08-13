# Round11 持久未决义务生命周期分析

## 结论

Round11 把 External 从 15/90 提高到 18/90，并保持 FP=0，但 Completed/Strict 仍是 0/0。它解决了“基础计划因未一次覆盖 criterion 而不执行”，但没有解决“任务完成如何形成可验证 evidence”。

请求从 Round10 的 983 增到 2175（×2.212614），prompt token 从 2,092,687 增到 5460587（×2.609366）。全轮有 232 次 assertion evaluation，但只有 0 次 proof event 通过，最终 VERIFIED criterion evidence 为 0。

## 固定成绩

| 难度 | External | Completed | Strict | FP | FN |
|---|---:|---:|---:|---:|---:|
| basic | 16/30 | 0/30 | 0/30 | 0 | 16 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 1/30 | 0/30 | 0/30 | 0 | 1 |

## 数据完整性与不作弊边界

- 90 题因果链完整：90/90。
- 原始文件 hash 全匹配：True。
- 未闭合模型请求：0。
- 初始 `goal_obligation_planning` 请求：0。
- 初始 direct-claim coverage 终止：0。
- Codex 标准答案与 hidden acceptance 只在 90 题完成后由本分析器读取；没有进入 RWKV prompt、parser、action、proof 或 completion。
- Controller 没有生成或选择语义答案；本轮无 completed case，因而也无可交付 final answer 可被重写。

## 从前向 funnel 看错误后移

- Goal parsed: 83/90
- Plan saved: 76/90
- 真实进入 action: 75/90
- 持久 obligation state: 76/90
- 生成 capsule / 进入 replan: 48 / 48

上轮的 coverage 早停被清零后，错误主要移到 evidence/proof 和 obligation replan。这是“可观测到更深根因”，不等于 Strict 能力已改善。

## Obligation 放大量

- Capsule: 95，token {'count': 95, 'min': 1082, 'mean': 2849.915789, 'median': 2528, 'max': 5012}，>5000 的数量 2。
- 2 个超限样本来自裁剪循环结束后才写入 `projection.capsule_tokens`；这个自描述字段又增加了 token，使 E2E-H14/E2E-M15 实际为 5005/5012。它是边界计数缺陷，不涉及语义筛选。
- Replan started/saved: 95 / 58。
- Replan 模型请求（含协议重试）: 190。
- 追加任务: 197。
- 预算耗尽 block / 协议 block: 9 / 29。
- 在 active required tasks 未完成时误触发 replan: 0。
- Capsule digest 不匹配 / 相同 digest 重复: 0 / 0。
- Projection 声明与实际列表数不一致: 0个 capsule。

## Evidence/proof 断层

- Assertion events: 232
- Binding protocol valid/invalid: 195 / 37
- Exact coverage events: 74
- Emitted claims / rejected claims: 82 / 82
- Proof-passed events: 0
- Final claims / VERIFIED evidence: 82 / 0

核心因果链是：RWKV 完成 action → 局部 verifier 可通过 → claim 在直接依赖、artifact ownership、pointer/transform 上失败 → criterion_evidence 为空 → 全部 criterion 仍 unresolved → replan 追加新任务 → 重复同样的 proof 失败。

## 18 个外部正确但未完成题

| 题 | 难度 | 最早可证实偏离 | 任务 | 请求 | claim/evidence | replan | 终止 |
|---|---|---|---:|---:|---:|---:|---|
| E2E-B01 | basic | `binding_or_claim_gate` | 6 | 28 | 0/0 | 3 | unresolved_goal_obligations |
| E2E-B02 | basic | `proof_semantics_gate` | 3 | 14 | 0/0 | 1 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B03 | basic | `proof_semantics_gate` | 6 | 27 | 3/0 | 1 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B04 | basic | `proof_semantics_gate` | 4 | 21 | 1/0 | 1 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B05 | basic | `evidence_coverage_gate` | 3 | 14 | 0/0 | 0 | recovery_lineage_budget_exhausted |
| E2E-B07 | basic | `evidence_coverage_gate` | 11 | 30 | 0/0 | 3 | unresolved_goal_obligations |
| E2E-B08 | basic | `evidence_coverage_gate` | 10 | 28 | 0/0 | 3 | unresolved_goal_obligations |
| E2E-M01 | medium | `proof_semantics_gate` | 12 | 30 | 0/0 | 1 | obligation replan has no task related to a current unresolved criterion |
| E2E-H04 | hard | `proof_semantics_gate` | 2 | 10 | 0/0 | 1 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B13 | basic | `proof_semantics_gate` | 6 | 27 | 4/0 | 1 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B14 | basic | `evidence_coverage_gate` | 10 | 26 | 0/0 | 2 | plan requires a non-empty tasks array |
| E2E-B17 | basic | `proof_semantics_gate` | 6 | 26 | 0/0 | 3 | obligation replan local ids reuse existing task ids: ['T5', 'T6'] |
| E2E-B19 | basic | `evidence_coverage_gate` | 10 | 26 | 0/0 | 2 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B20 | basic | `evidence_coverage_gate` | 5 | 14 | 0/0 | 1 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B21 | basic | `proof_semantics_gate` | 4 | 21 | 2/0 | 2 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B22 | basic | `proof_semantics_gate` | 10 | 47 | 1/0 | 3 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B25 | basic | `proof_semantics_gate` | 4 | 16 | 0/0 | 1 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B26 | basic | `proof_semantics_gate` | 4 | 20 | 0/0 | 1 | obligation replan local ids reuse existing task ids: ['T4'] |

## 90 题逐环节索引

| 题 | 结果 | 最早偏离 | plan/action/proof/obligation | 任务 | 请求 | claim/evidence | 终止 |
|---|---|---|---|---:|---:|---:|---|
| E2E-B01 | false_negative | `binding_or_claim_gate` | Y/Y/Y/Y | 6 | 28 | 0/0 | unresolved_goal_obligations |
| E2E-B02 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 3 | 14 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B03 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 6 | 27 | 3/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B04 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 4 | 21 | 1/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B05 | false_negative | `evidence_coverage_gate` | Y/Y/-/- | 3 | 14 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-B06 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 15 | 38 | 0/0 | unresolved_goal_obligations |
| E2E-B07 | false_negative | `evidence_coverage_gate` | Y/Y/-/Y | 11 | 30 | 0/0 | unresolved_goal_obligations |
| E2E-B08 | false_negative | `evidence_coverage_gate` | Y/Y/-/Y | 10 | 28 | 0/0 | unresolved_goal_obligations |
| E2E-B09 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | invalid plan schema |
| E2E-B10 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/Y/- | 4 | 16 | 0/0 | ModelProtocolError: model output does not contain a complete JSON object |
| E2E-M01 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 12 | 30 | 0/0 | obligation replan has no task related to a current unresolved criterion |
| E2E-M02 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/- | 4 | 13 | 0/0 | G1i tool call has unknown fields: ['tool_calls'] |
| E2E-M03 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 6 criteria; maximum is 5 |
| E2E-M04 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 30 | 68 | 8/0 | recovery_lineage_budget_exhausted |
| E2E-M05 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 4 | 22 | 1/0 | obligation replan local ids reuse existing task ids: ['T4'] |
| E2E-M06 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 7 criteria; maximum is 5 |
| E2E-M07 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 22 | 95 | 9/0 | unresolved_goal_obligations |
| E2E-M08 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/- | 4 | 8 | 0/0 | model output does not contain a complete JSON object |
| E2E-M09 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/Y/- | 7 | 25 | 0/0 | G1i tool call has unknown fields: ['type'] |
| E2E-M10 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/- | 5 | 12 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-H01 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 10 | 21 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-H02 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/Y/Y | 5 | 20 | 4/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-H03 | external_wrong_blocked | `plan_coverage_omission` | Y/Y/Y/Y | 22 | 85 | 11/0 | plan requires a non-empty tasks array |
| E2E-H04 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 2 | 10 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-H05 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/Y/Y | 14 | 37 | 1/0 | G1i tool call has unknown fields: ['action'] |
| E2E-H06 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 16 | 64 | 1/0 | unresolved_goal_obligations |
| E2E-H07 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 6 | 17 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-H08 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/- | 5 | 13 | 0/0 | G1i tool call has unknown fields: ['count', 'id'] |
| E2E-H09 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/- | 5 | 12 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-H10 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 7 | 8 | 0/0 | action type changed after selection: expected read_json |
| E2E-LH01 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 7 | 19 | 0/0 | G1i tool call has unknown fields: ['tool_calls'] |
| E2E-LH02 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | tasks bind unknown goal criteria: ['GC10', 'GC11', 'GC12', 'GC13', 'GC14', 'G... |
| E2E-LH03 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 7 criteria; maximum is 5 |
| E2E-LH04 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 10 | 28 | 0/0 | model output does not contain a complete JSON object |
| E2E-LH05 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | invalid plan schema |
| E2E-LH06 | external_wrong_blocked | `action_coverage_omission` | Y/Y/Y/Y | 5 | 26 | 0/0 | obligation replan local ids reuse existing task ids: ['T3', 'T4', 'T5'] |
| E2E-LH07 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 5 | 12 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-LH08 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | invalid plan schema |
| E2E-LH09 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 6 | 40 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-LH10 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 7 | 19 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-LH11 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | invalid plan schema |
| E2E-LH12 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 6 criteria; maximum is 5 |
| E2E-B11 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 5 | 15 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-B12 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 8 criteria; maximum is 5 |
| E2E-B13 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 6 | 27 | 4/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B14 | false_negative | `evidence_coverage_gate` | Y/Y/-/Y | 10 | 26 | 0/0 | plan requires a non-empty tasks array |
| E2E-B15 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 6 | 12 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-B16 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 10 | 39 | 1/0 | unresolved_goal_obligations |
| E2E-B17 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 6 | 26 | 0/0 | obligation replan local ids reuse existing task ids: ['T5', 'T6'] |
| E2E-B18 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 5 | 21 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B19 | false_negative | `evidence_coverage_gate` | Y/Y/-/Y | 10 | 26 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B20 | false_negative | `evidence_coverage_gate` | Y/Y/-/Y | 5 | 14 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B21 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 4 | 21 | 2/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B22 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 10 | 47 | 1/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B23 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 5 | 29 | 0/0 | unresolved_goal_obligations |
| E2E-B24 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 11 | 31 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B25 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 4 | 16 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-B26 | false_negative | `proof_semantics_gate` | Y/Y/Y/Y | 4 | 20 | 0/0 | obligation replan local ids reuse existing task ids: ['T4'] |
| E2E-B27 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/- | 5 | 22 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-B28 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 5 | 10 | 0/0 | unsupported action type: read_text |
| E2E-B29 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/Y/Y | 5 | 23 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-B30 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/- | 4 | 14 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M11 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 14 | 33 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M12 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/- | 5 | 19 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M13 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 5 | 10 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M14 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 4 | 12 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M15 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 14 | 58 | 4/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-M16 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 2 | 10 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M17 | external_wrong_blocked | `action_coverage_omission` | Y/Y/Y/Y | 6 | 29 | 1/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M18 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/Y | 9 | 22 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M19 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 5 | 15 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M20 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 7 criteria; maximum is 5 |
| E2E-M21 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 15 | 62 | 6/0 | obligation replan local ids reuse existing task ids: ['T10', 'T11', 'T12', 'T... |
| E2E-M22 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 15 | 53 | 1/0 | obligation replan local ids reuse existing task ids: ['T10', 'T11', 'T5', 'T6... |
| E2E-M23 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 15 | 69 | 5/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M24 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/- | 5 | 18 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M25 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/- | 6 | 18 | 0/0 | recovery_lineage_budget_exhausted |
| E2E-M26 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 9 | 32 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-M27 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 4 | 0/0 | plan requires a non-empty tasks array |
| E2E-M28 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 10 | 47 | 3/0 | unresolved_goal_obligations |
| E2E-M29 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 4 | 14 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-M30 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/- | 6 | 15 | 0/0 | G1i tool call has unknown fields: ['tool_calls'] |
| E2E-H11 | external_wrong_blocked | `goal_cardinality_gate` | -/-/-/- | 0 | 2 | 0/0 | ModelProtocolError: goal proposal has 9 criteria; maximum is 5 |
| E2E-H12 | external_wrong_blocked | `external_mismatch_unlocalized` | Y/Y/-/Y | 16 | 37 | 0/0 | ValueError: invalid literal for int() with base 10: 'high' |
| E2E-H13 | external_wrong_blocked | `plan_schema_protocol_gate` | -/-/-/- | 0 | 3 | 0/0 | invalid plan schema |
| E2E-H14 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/Y/Y | 39 | 156 | 15/0 | task requires id, title, and description |
| E2E-H15 | external_wrong_blocked | `action_coverage_omission` | Y/-/-/- | 9 | 5 | 0/0 | G1i tool call has unknown fields: ['action'] |
| E2E-H16 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 8 | 17 | 0/0 | G1i tool call has unknown fields: ['type'] |
| E2E-H17 | external_wrong_blocked | `action_arguments_or_semantics` | Y/Y/-/Y | 4 | 12 | 0/0 | obligation replan top-level fields must be exactly ['schema_version', 'reason... |
| E2E-H18 | external_wrong_blocked | `action_coverage_omission` | Y/Y/-/- | 10 | 17 | 0/0 | recovery_lineage_budget_exhausted |

## 上传门

- 检查：`{"false_positive_eq_0": true, "external_gte_15": true, "strict_gt_7": false, "completed_gt_0": false, "causal_complete_90": true}`
- 结论：`do_not_upload`。Round11 不上传，因为 Strict>7 和 Completed>0 未满足。

## 下一步结构指导

下一轮不应再增加义务预算、重复 verifier 或答案筛选规则。建议的单变量是 `rwkv_witness_intent_lifecycle.v1`：

1. RWKV 在计划/修订时显式声明 criterion 的 producer、consumer、actual source 类型、expected source 类型和 comparison；系统不自动配对。
2. 执行时为所有原始 action result、dependency artifact、goal literal 和 workspace snapshot 生成不透明 handle，不按 hidden acceptance 或相似度筛选。
3. RWKV 用简单单工具协议选 actual/expected handle 和少量 transform；Controller 只检查 handle 存在、直接依赖所有权、hash 和类型，不改 RWKV 选择。
4. Proof 失败先返回 `not_direct_dependency` / `pointer_missing` / `type_mismatch` 给同一 RWKV 做局部重绑；只有 RWKV 明确认为需要新产物时才增加任务。
5. 预注册可证伪门：FP=0，Round11 的 18 个 FN 中出现真实 completion，proof-passed/evidence >0，Strict>0，且请求不再因事后扩图翻倍。

每题的标准答案、外部 observable、artifact similarity、raw/model/protocol/state 路径和完整 causal chain 见 `persistent_obligation_analysis.json`。
