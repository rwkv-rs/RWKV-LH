# Round10 因果分析

本报告只在模型运行结束后读取隐藏验收与冻结的 Codex 标准答案，不参与 RWKV 决策。

## 固定主指标

- External acceptance：15/90（16.67%）
- Strict E2E：0/90（0.00%）
- Agent completed：0/90
- False positive / false negative：0 / 15
- 因果链完整：90/90

| 难度 | External | Strict | Agent completed | FP | FN |
| --- | ---: | ---: | ---: | ---: | ---: |
| basic | 13/30 | 0/30 | 0/30 | 0 | 13 |
| medium | 1/30 | 0/30 | 0/30 | 0 | 1 |
| hard | 1/30 | 0/30 | 0/30 | 0 | 1 |

## 固定诊断指标

- 模型请求：983
- 本地输入 / 输出 token：2092687 / 262600
- 平均模型决策时延：8802.00829015544 ms
- 可配对产物 byte-5gram 平均相似度：0.804105592579
- 最终回答与 Codex 摘要平均相似度：0.0（仅诊断）

## 终止阶段与根因入口

- plan_missing_direct_criterion_claims: 30
- run_blocked: 25
- external_correct_controller_not_completed: 15
- invalid_plan_schema: 5
- g1i_function_envelope_rejected: 4
- goal proposal has 6 criteria; maximum is 5: 3
- goal proposal has 7 criteria; maximum is 5: 2
- invalid_failure_analysis_decision: 2
- plan_tasks_array_missing: 1
- obligation plan top-level fields must be exactly ['schema_version', 'supplemental_tasks']: 1
- truncated_or_incomplete_json: 1
- goal proposal has 8 criteria; maximum is 5: 1

## 透明格式层发现

- 完整 tasks 位于 `task_graph.tasks` 但被拒绝：1 题。
- 完整 G1i/OpenAI function 外壳被拒绝：4 题。
- 这些只支持字节可审计、语义对象不变的协议归一；不支持规则补答案、补 criterion 或选择候选。

## 完成边界

- Strict pass case：
- False positive case：
- False negative case：E2E-B01, E2E-B03, E2E-B04, E2E-B05, E2E-B07, E2E-B10, E2E-B13, E2E-B16, E2E-B19, E2E-B20, E2E-B22, E2E-B26, E2E-B28, E2E-H04, E2E-M12

## 本轮 observation gate 触发情况

- Prepared：87
- Cacheable / uncacheable：81 / 6
- 首次有效 RWKV 失败记录：0
- 实际抑制：0
- 只有实际抑制数可归因于不变失败观察 gate；若为 0，不得把总请求变化解释成该 gate 的收益。

## Canonical G1i 单变量结果

- 15 个 case 的 33 个 claim scope 发起 51 次 binding 请求；Round9 为 66 次。
- 50/51 响应通过透明 `schema_validation_only`，input/normalized payload 等值且 transformations 为空；Round9 为 0。
- 87 个 assertion evaluation 中 69 个 binding-valid、18 个 binding-invalid；产生 13 个 exact-coverage 单 claim。
- 13 个单 claim 全部未通过确定性 proof：9 个引用非直接依赖，4 个 JSON Pointer 没有以 `/` 开头。
- VERIFIED CriterionEvidence 仍为 0，External 与 Round9 同为 15/90，Strict/Completed 仍为 0。

因此 canonical framing 有真实协议收益，但没有端到端收益，Round10 不满足上传门槛。完整统计见
`CANONICAL_G1I_ANALYSIS.md` 与 `canonical_g1i_analysis.json`。

## 十轮反向因果结果

固定 90 题跨 Round1--Round10 的 900 个题轮记录显示：359 个停在完整 `satisfies_criteria` 覆盖硬门，
86 个停在计划 schema/外壳，70 个停在 Goal 最多 5 条条件；进入动作后另有 159 个最早可证实偏离在动作
参数/语义。十轮 External 全错题为 62 题，曾 Strict 后到 Round10 回退为 10 题。

Round11 优先候选应是把同步完整覆盖拒绝/自动 supplemental planning 替换为持久化 unresolved-obligation
lifecycle；结构合法基础计划先执行，遗漏条件进入由权威状态生成的 capsule，之后仍由 RWKV修改/追加计划。
Controller 不生成任务、criterion、producer、expected 或 proof 引用。完整逐题因果链、阶段转移与偏离后放大量见
`CROSS_ROUND_BACKWARD_CAUSALITY.md` 与 `cross_round_backward_causality.json`。

## 下一轮候选证据（不自动选方案）

- goal_obligation_planning: 30 题；initial plan rejected before execution for missing direct claims。
- goal_criterion_capacity: 6 题；goal proposal exceeded the fixed five-criterion contract。
- transparent_protocol_envelope_normalization: 5 题；complete task/function objects remained under known wire envelopes。
- criterion_evidence_boundary: 0 题；agent completed while external acceptance failed。

下一轮单变量必须另行预注册；本分析器不利用隐藏验收或标准答案自动选择结构。
