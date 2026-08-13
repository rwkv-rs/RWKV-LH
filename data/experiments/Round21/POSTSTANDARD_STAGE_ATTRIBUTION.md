# Round21 标准答案后逐环节归因

## 边界

Post-run only. This joins frozen external acceptance/reference observations to the already frozen lifecycle analysis. It never participates in RWKV generation, witness selection, proof, completion, or final-output delivery. Mutation attribution is an explicit inference from matching action-selected target paths and external-check paths.

## 总体结果

- External 正确/错误：20 / 70。
- Strict / Completed / FP / FN：0 / 0 / 0 / 20。
- 20 个 External 正确案例被 controller completion 边界阻断。

## 正确案例为什么没有完成

| 环节 | External 正确题到达数 | External 错误题到达数 |
|---|---:|---:|
| run_created | 20 | 62 |
| goal_parsed | 20 | 62 |
| plan_saved | 20 | 51 |
| action_returned | 20 | 51 |
| task_completed | 20 | 49 |
| witness_selection_started | 17 | 26 |
| witness_selection_compiled | 13 | 16 |
| criterion_assertions_evaluated | 12 | 12 |
| witness_binding_evaluated | 12 | 12 |
| criterion_evidence_persisted | 0 | 0 |
| run_completed | 0 | 0 |

20 个正确案例中只有到达独立证据并覆盖全部 Goal criterion 的案例才有资格完成。本轮有 0 个案例走到 run_completed；其余正确产物主要被 witness/证明/义务恢复漏斗阻断。

## 错误案例从哪里开始

下表是后验归因入口。`rwkv_producer_mutation` 只在冻结的 RWKV action_selected 对外部检查目标执行可直接判定为错误的 write_json 时记入；其余按生命周期终态层归类。

| 归因层 | 题数 |
|---|---:|
| rwkv_producer_mutation | 27 |
| rwkv_action_or_recovery | 21 |
| controller_completion_false_negative | 20 |
| planning_protocol | 11 |
| goal_protocol | 8 |
| obligation_recovery | 2 |
| runtime_or_recovery | 1 |

## 来源独立性规则

规则共在 19 题拒绝 123 次：External 正确题为 E2E-B01, E2E-B04, E2E-B08, E2E-B15, E2E-B16, E2E-B19, E2E-B22, E2E-B26, E2E-B28, E2E-LH02；External 错误题为 E2E-B06, E2E-B14, E2E-B18, E2E-B25, E2E-H08, E2E-M04, E2E-M15, E2E-M17, E2E-M22。

危险的模型写入同目标证明通过为 0；只读同目标证明通过 2 条。来源拒绝是否对应正确或错误产物，以上述 External 分组为准。

## 假阳性证明链

假阳性题：无；其中只读同目标断言 0 条。

A read-only snapshot is not an independent expected source when both proof sides descend from the same current workspace target. Exact equality can then prove snapshot consistency while failing to entail the Goal criterion.

## 正确值被后续覆盖

可直接从 write_json 与 json_equals 目标比对确认的案例：E2E-B02, E2E-B18, E2E-M28。这些题由 RWKV 先写入外部目标，后续 RWKV 写操作覆盖；只读验证和证据重试可能继续放大该生产错误。

## 逐题证据

完整 90 题的 failed check、匹配目标写操作、首个错误写入、到达环节、终态根因、证明/证据次数、来源拒绝和 obligation 放大量见 `poststandard_stage_attribution.json`。
